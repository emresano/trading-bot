# backtest/run_family.py
"""Strateji-ailesi backtest sürücüsü (P1 üretim portu, tasarım çerçevesi #1/#4).

config'ten strateji ailesini seçer (family_registry) ve koşar. `regime_core` için
S1b mutabakatını (REGIME_CORE_S1B.md referansı) üretir: mühürlü kabul kriterleri
A (67 anahtarlama tarihi birebir) ve B (CAGR ±0.5 / maxDD ±1.0 / Sharpe ±0.05).

DEMİR KURAL: bu sürücü v7.1-golden yolunu (backtest/engine.py::run_backtest)
DEĞİŞTİRMEZ — ten_gate ailesi onu yalnızca delege eder.

Kullanım:
  python -m backtest.run_family --config config/regime_core.yaml \
      --out runtime/regime_core_prod --reconcile-s1b runtime/regime_core_s1b
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from strategy.family_registry import build_family, family_id_from_config

TRADING_DAYS_PER_YEAR = 252

# Mühürlü tolerans (P1 kriter B — koşum öncesi sabitlendi)
TOL_CAGR_PTS = 0.5
TOL_MAXDD_PTS = 1.0
TOL_SHARPE = 0.05


def compute_summary(equity_curve: pd.Series) -> dict:
    if equity_curve.empty or len(equity_curve) < 2:
        return {"total_return": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    cagr = float((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0
    drawdown = equity_curve / equity_curve.cummax() - 1
    max_dd = float(drawdown.min())
    daily_returns = equity_curve.pct_change().dropna()
    sharpe = (float(daily_returns.mean() / daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
              if daily_returns.std() > 0 else 0.0)
    return {"total_return": total_return, "cagr": cagr, "max_drawdown": max_dd, "sharpe": sharpe}


def _load_regime_core_ctx(cfg_dict: dict, freeze_file: Optional[Path]) -> dict:
    from data.cleaning import load_and_clean_universe
    from strategy.regime_core import RegimeCoreParams, RegimeCoreBreaker

    snapshot_dir = Path(cfg_dict["backtest"]["snapshot"])
    start = cfg_dict["backtest"]["start"]

    def _load_daily_raw(s: str) -> pd.DataFrame:
        return pd.read_parquet(snapshot_dir / f"{s}.parquet").loc[start:]

    cleaned, _ghost = load_and_clean_universe(cfg_dict["symbols"], _load_daily_raw)
    closes = {s: df["close"] for s, df in cleaned.items()}

    cash_rate = None
    cy = cfg_dict.get("cash_yield")
    if cy and cy.get("enabled"):
        cash_rate = pd.read_parquet(cy["aux_snapshot"])["rate_pct"] / 100.0

    reg = cfg_dict["regime"]
    params = RegimeCoreParams(
        symbols=cfg_dict["symbols"], ma_period=reg["ma_period"], band_pct=reg["band_pct"],
        confirm_days=reg["confirm_days"], commission_bps=cfg_dict["costs"]["commission_bps"],
        slippage_bps=cfg_dict["costs"]["slippage_bps"], initial_equity=cfg_dict["initial_equity"],
    )
    alarms: list[dict] = []
    breaker = RegimeCoreBreaker(freeze_file=freeze_file, alarm_hook=alarms.append)
    return {"closes": closes, "params": params, "cash_rate": cash_rate,
            "breaker": breaker, "_alarms": alarms}


def reconcile_with_s1b(equity_curve: pd.Series, switches: list, s1b_dir: Path) -> dict:
    """Mühürlü kriter A + B mutabakatı (REGIME_CORE_S1B.md referansı)."""
    # A: anahtarlama tarihleri birebir
    prod_switches = [(pd.Timestamp(s.date), s.action) for s in switches]
    s1b_df = pd.read_csv(s1b_dir / "switches_main.csv")
    s1b_switches = [(pd.Timestamp(d), a) for d, a in zip(s1b_df["date"], s1b_df["action"])]
    a_identical = prod_switches == s1b_switches

    # B: metrik mutabakatı
    prod = compute_summary(equity_curve)
    s1b_summary = json.loads((s1b_dir / "summary.json").read_text())["main_run"]["summary"]
    d_cagr = abs(prod["cagr"] - s1b_summary["cagr"]) * 100
    d_maxdd = abs(prod["max_drawdown"] - s1b_summary["max_drawdown"]) * 100
    d_sharpe = abs(prod["sharpe"] - s1b_summary["sharpe"])
    b_pass = (d_cagr <= TOL_CAGR_PTS and d_maxdd <= TOL_MAXDD_PTS and d_sharpe <= TOL_SHARPE)

    return {
        "A_switch_dates_identical": a_identical,
        "A_prod_switch_count": len(prod_switches),
        "A_s1b_switch_count": len(s1b_switches),
        "B_prod_metrics": prod,
        "B_s1b_metrics": s1b_summary,
        "B_delta_cagr_pts": d_cagr, "B_delta_maxdd_pts": d_maxdd, "B_delta_sharpe": d_sharpe,
        "B_pass": b_pass,
        "B_tolerances": {"cagr_pts": TOL_CAGR_PTS, "maxdd_pts": TOL_MAXDD_PTS, "sharpe": TOL_SHARPE},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Strateji-ailesi backtest sürücüsü (P1)")
    parser.add_argument("--config", default="config/regime_core.yaml")
    parser.add_argument("--out", default="runtime/regime_core_prod")
    parser.add_argument("--reconcile-s1b", default="runtime/regime_core_s1b",
                        help="S1b referans dizini (switches_main.csv + summary.json)")
    args = parser.parse_args()

    cfg_dict = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    family_id = family_id_from_config(cfg_dict)
    family = build_family(family_id)
    print(f"Strateji ailesi: {family_id}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if family_id != "regime_core":
        raise SystemExit(f"Bu sürücü şu an yalnızca regime_core mutabakatı üretir "
                         f"(ten_gate için backtest.cli kullanın). Seçilen: {family_id}")

    freeze_file = out_dir / "FREEZE_TRIPPED"
    if freeze_file.exists():
        freeze_file.unlink()  # izole backtest koşumu için temiz başla
    ctx = _load_regime_core_ctx(cfg_dict, freeze_file)
    result = family.run(ctx)

    # çıktılar
    result.equity_curve.to_csv(out_dir / "equity_curve_main.csv")
    pd.DataFrame(result.events).to_csv(out_dir / "switches_main.csv", index=False)
    pd.DataFrame(result.extra["breaker_events"]).to_csv(out_dir / "breaker_events.csv", index=False)

    recon = reconcile_with_s1b(result.equity_curve, result.extra["switches"], Path(args.reconcile_s1b))
    summary = compute_summary(result.equity_curve)
    output = {
        "family_id": family_id,
        "summary": summary,
        "n_switches": len(result.extra["switches"]),
        "breaker": {
            "freeze_trips": result.extra["freeze_trips"],
            "enters_blocked_by_freeze": result.extra["enters_blocked_by_freeze"],
            "alarm_trips": result.extra["alarm_trips"],
            "alarm_thresholds": {"alarm_pct": 0.25, "freeze_pct": 0.40},
        },
        "reconciliation_s1b": recon,
    }
    (out_dir / "summary.json").write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(json.dumps(output, indent=2, default=str))
    print(f"\nYazıldı: {out_dir / 'summary.json'}")


if __name__ == "__main__":
    main()

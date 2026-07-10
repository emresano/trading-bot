# tools/run_d5_bist.py
"""D5-BIST CHALLENGER sürücüsü — "D1 + fırsat-maliyeti (faiz) kapısı".

STATUS.md KALICI KAYIT 23. **Offline araştırma spike'ı; üretim DEĞİL; HÜKÜM YOK.**

Bu commit'te dosya YALNIZCA **benchmark tarafını** içerir: D1'in (S1b) frozen
veriyle deterministik yeniden üretimi + `runtime/regime_core_s1b/summary.json`
kayıtlarıyla **bit-bit doğrulanması** + mühürlenecek eşiklerin yazılması.
Kapının kendisi (`backtest/regime_core_gated.py`) bu commit'te **HENÜZ YOKTUR** —
commit sırası, tasarımın sonuca göre seçilmediğinin kanıtıdır (E4 §4 / D2US §5 /
D4US §5 emsali).

İzolasyon: `mode: paper` + TÜM canlı bot modülleri + S1/S1b/E4/D2US/D4US araçları
+ TÜM snapshot'lar DOKUNULMAZ. `backtest/regime_core.py` ve
`tools/run_regime_core.py` YALNIZ **import** edilir (yeniden yazılmaz → drift
imkânsız). `config/regime_core.yaml` SALT-OKUNUR.

Kullanım:
  python -m tools.run_d5_bist --baseline-only    # D1 baseline üret + S1b'ye karşı doğrula
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from backtest.regime_core import RegimeCoreConfig, run_regime_core
from tools.run_regime_core import (
    compute_monthly_returns,
    compute_summary,
    gen_walk_forward_windows,
    load_cash_rate,
    load_closes,
    monte_carlo_monthly,
    monthly_sharpe,
)

D5_CFG_PATH = Path("config/d5_bist.yaml")
S1B_SUMMARY_PATH = Path("runtime/regime_core_s1b/summary.json")

# S1b'nin kayıtlı metriklerinin bit-bit yeniden üretilmesi için tolerans.
# 0.0 = BİREBİR aynı float. (Aynı frozen veri + aynı fonksiyonlar → sapma olmamalı.)
BIT_EXACT_TOL = 0.0


# --------------------------------------------------------------------------- config


def load_d5_config(path: str | Path = D5_CFG_PATH) -> dict:
    """`config/d5_bist.yaml`'ı yükler ve `inherit_from` ile işaret edilen D1
    config'ini (SALT-OKUNUR) altına serer. D1'in mühürlü sabitleri (symbols,
    regime.N/b/M, costs, initial_equity, backtest.snapshot, walk_forward,
    monte_carlo, cash_yield) **kopyalanmaz, devralınır** → N/b/M=200/0.01/3'ün
    aynen kaldığı yapısal garanti (elle senkronizasyon hatası imkânsız).

    D5'e özgü anahtarlar (gate, neighborhood, ...) devralınan değerleri EZER."""
    d5 = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    parent_path = d5.get("inherit_from")
    if not parent_path:
        return d5
    parent = yaml.safe_load(Path(parent_path).read_text(encoding="utf-8"))
    merged = {**parent, **{k: v for k, v in d5.items() if k != "inherit_from"}}
    merged["_inherited_from"] = parent_path
    return merged


def core_config_from(cfg: dict) -> RegimeCoreConfig:
    """D1'in MÜHÜRLÜ RegimeCoreConfig'i — devralınan değerlerden birebir kurulur."""
    reg = cfg["regime"]
    return RegimeCoreConfig(
        symbols=cfg["symbols"],
        ma_period=reg["ma_period"],
        band_pct=reg["band_pct"],
        confirm_days=reg["confirm_days"],
        commission_bps=cfg["costs"]["commission_bps"],
        slippage_bps=cfg["costs"]["slippage_bps"],
        initial_equity=cfg["initial_equity"],
    )


def load_universe(cfg: dict) -> tuple[dict[str, pd.Series], list[dict], pd.Series]:
    """S1b'nin frozen snapshot'ı + S1b'nin tarihsel TRY_ON_RATE serisi — AYNEN.
    Yeni indirme YOK (D1 baseline'ıyla bit-bit kıyaslanabilirlik şartı)."""
    closes, ghost_log = load_closes(cfg)
    cash_rate = load_cash_rate(cfg)
    if cash_rate is None:
        raise RuntimeError(
            "D5 kapısı TRY_ON_RATE serisini ZORUNLU kılar; config/regime_core.yaml "
            "cash_yield bloğu devre dışı görünüyor."
        )
    return closes, ghost_log, cash_rate


# ------------------------------------------------------------------ OOS / MC yardımı


def oos_from_reruns(
    closes: dict[str, pd.Series],
    cfg: dict,
    core_cfg: RegimeCoreConfig,
    cash_rate: pd.Series,
    runner,
    **runner_kwargs,
) -> dict:
    """S1b sürücüsüyle (tools/run_regime_core.py::main) **AYNI** walk-forward OOS
    yöntemi: her (test_start, test_end] penceresinde motoru `date_range` ile
    yeniden koş, aylık getirileri biriktir → birleşik OOS aylık-Sharpe + OOS maxDD.
    Parametre optimizasyonu YOK (N/b/M her pencerede AYNEN).

    `runner`: `run_regime_core` (D1) veya `run_regime_core_gated` (D5). İki aile de
    AYNI OOS makinesinden geçer → kıyas adil."""
    wf = cfg["walk_forward"]
    windows = gen_walk_forward_windows(
        closes[cfg["symbols"][0]].index, wf["train_months"], wf["test_months"], wf["step_months"]
    )
    oos_monthly: list[float] = []
    window_rows: list[dict] = []
    for _train_start, _train_end, test_start, test_end in windows:
        res = runner(closes, core_cfg, date_range=(test_start, test_end), cash_rate=cash_rate,
                     **runner_kwargs)
        m_ret = compute_monthly_returns(res.equity_curve)
        oos_monthly.extend(m_ret.tolist())
        window_rows.append({
            "test_start": str(test_start.date()), "test_end": str(test_end.date()),
            "test_switch_count": len(res.switches),
        })

    ser = pd.Series(oos_monthly)
    eq = (1 + ser).cumprod()
    return {
        "n_windows": len(windows),
        "oos_n_months": len(ser),
        "oos_monthly_sharpe": monthly_sharpe(ser),
        "oos_max_dd": float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0,
        "_windows": window_rows,
    }


def mc_from_curve(equity_curve: pd.Series, cfg: dict) -> dict:
    """Aylık permütasyon Monte Carlo — S1b/E4/D2US/D4US ile AYNI fonksiyon
    (`tools.run_regime_core.monte_carlo_monthly`), seed config'ten (42)."""
    mc = cfg["monte_carlo"]
    monthly = compute_monthly_returns(equity_curve)
    return monte_carlo_monthly(monthly.to_numpy(), mc["runs"], mc["random_seed"])


# ---------------------------------------------------------------- D1 baseline (benchmark)


def reproduce_d1_baseline(cfg: dict, closes: dict[str, pd.Series], cash_rate: pd.Series) -> dict:
    """**Mühürlenecek eşiklerin kaynağı.** D1'i (S1b: nakit-getirili, N/b/M mühürlü)
    aynı frozen veriyle deterministik olarak yeniden üretir ve tam metrik setini
    döndürür. Strateji kodu YOK — bu yalnızca `backtest/regime_core.py`nin
    (DEĞİŞTİRİLMEMİŞ S1/S1b simülatörü) yeniden çağrılmasıdır."""
    core_cfg = core_config_from(cfg)
    res = run_regime_core(closes, core_cfg, cash_rate=cash_rate)
    summary = compute_summary(res.equity_curve)
    oos = oos_from_reruns(closes, cfg, core_cfg, cash_rate, run_regime_core)
    return {
        "summary": summary,
        "n_switches": len(res.switches),
        "oos": {k: v for k, v in oos.items() if not k.startswith("_")},
        "monte_carlo_monthly": mc_from_curve(res.equity_curve, cfg),
        "equity_start": str(res.equity_curve.index[0]),
        "equity_end": str(res.equity_curve.index[-1]),
        "n_days": int(len(res.equity_curve)),
        "first_switch": {"date": str(res.switches[0].date.date()), "action": res.switches[0].action}
        if res.switches else None,
    }


def verify_against_s1b(baseline: dict) -> dict:
    """D1 yeniden üretiminin S1b KAYITLARIYLA **bit-bit** aynı olduğunu doğrular.
    Eşleşmezse mühürleme DURUR (RuntimeError) — eşik, kanıtlanmamış bir sayı
    üzerine mühürlenemez."""
    if not S1B_SUMMARY_PATH.exists():
        raise RuntimeError(f"S1b kaydı bulunamadı: {S1B_SUMMARY_PATH}")
    ref = json.loads(S1B_SUMMARY_PATH.read_text(encoding="utf-8"))

    checks: list[dict] = []
    for key in ("total_return", "cagr", "max_drawdown", "sharpe"):
        got, exp = baseline["summary"][key], ref["main_run"]["summary"][key]
        checks.append({"field": f"summary.{key}", "reproduced": got, "s1b_record": exp,
                       "delta": got - exp, "bit_exact": got == exp})
    pairs = [
        ("oos.oos_monthly_sharpe", baseline["oos"]["oos_monthly_sharpe"],
         ref["walk_forward"]["oos_monthly_sharpe_strategy"]),
        ("oos.oos_max_dd", baseline["oos"]["oos_max_dd"], ref["walk_forward"]["oos_max_dd_strategy"]),
        ("oos.n_windows", float(baseline["oos"]["n_windows"]), float(ref["walk_forward"]["n_windows"])),
        ("monte_carlo.dd_p5", baseline["monte_carlo_monthly"]["dd_p5"],
         ref["monte_carlo_monthly"]["dd_p5"]),
        ("n_switches", float(baseline["n_switches"]), float(ref["main_run"]["n_switches"])),
    ]
    for field, got, exp in pairs:
        checks.append({"field": field, "reproduced": got, "s1b_record": exp,
                       "delta": got - exp, "bit_exact": got == exp})

    failed = [c for c in checks if not c["bit_exact"]]
    if failed:
        raise RuntimeError(
            "D1 baseline S1b kayıtlarıyla bit-bit eşleşmedi — mühürleme DURDURULDU:\n"
            + json.dumps(failed, indent=2)
        )
    return {"all_bit_exact": True, "n_checks": len(checks), "checks": checks}


# ------------------------------------------------------------------------------- CLI


def run_baseline(cfg: dict) -> dict:
    closes, ghost_log, cash_rate = load_universe(cfg)
    print(f"evren: {len(cfg['symbols'])} sembol · snapshot: {cfg['backtest']['snapshot']}")
    print(f"N/b/M (devralındı: {cfg['_inherited_from']}): "
          f"{cfg['regime']['ma_period']}/{cfg['regime']['band_pct']}/{cfg['regime']['confirm_days']}")
    print(f"TRY_ON_RATE: {len(cash_rate)} gözlem, {cash_rate.index[0].date()} → {cash_rate.index[-1].date()}")

    baseline = reproduce_d1_baseline(cfg, closes, cash_rate)
    verification = verify_against_s1b(baseline)

    print("\n=== D1 BASELINE (mühürlenecek eşikler) ===")
    print(json.dumps({"summary": baseline["summary"], "oos": baseline["oos"],
                      "n_switches": baseline["n_switches"]}, indent=2))
    print(f"\n=== S1b bit-bit doğrulaması: {verification['n_checks']}/{verification['n_checks']} "
          f"BİREBİR (tolerans={BIT_EXACT_TOL}) ===")

    out = {
        "role": "BENCHMARK — D1 (S1b, nakit-getirili). D5'in yenmesi gereken eşik.",
        "sealed_at": "koşumdan ÖNCE (backtest/regime_core_gated.py henüz yok)",
        "config": {
            "inherited_from": cfg["_inherited_from"],
            "regime": cfg["regime"], "costs": cfg["costs"],
            "initial_equity": cfg["initial_equity"], "snapshot": cfg["backtest"]["snapshot"],
            "cash_yield": cfg["cash_yield"], "walk_forward": cfg["walk_forward"],
            "monte_carlo": cfg["monte_carlo"],
        },
        "ghost_bars_removed": [{"symbol": g["symbol"], "date": str(g["date"])} for g in ghost_log],
        "d1_baseline": baseline,
        "s1b_bit_exact_verification": verification,
    }
    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline_sealed.json").write_text(json.dumps(out, indent=2, default=str),
                                                  encoding="utf-8")
    print(f"\nYazıldı: {out_dir / 'baseline_sealed.json'}")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="D5-BIST challenger sürücüsü")
    p.add_argument("--baseline-only", action="store_true",
                   help="Yalnızca D1 baseline'ını yeniden üret + S1b'ye karşı bit-bit doğrula "
                        "(mühürleme girdisi; strateji koşumu YOK).")
    args = p.parse_args()

    cfg = load_d5_config()
    if args.baseline_only:
        run_baseline(cfg)
        return
    raise SystemExit(
        "Bu commit'te yalnızca --baseline-only desteklenir: D5 kapısı "
        "(backtest/regime_core_gated.py) mühürden SONRAKİ commit'te eklenir."
    )


if __name__ == "__main__":
    main()

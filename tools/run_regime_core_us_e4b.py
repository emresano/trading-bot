# tools/run_regime_core_us_e4b.py
"""EXPANSION E4b — D1-US NAKİT BACAĞI ölçüm-tamamlama sürücüsü (S1→S1b emsali).

Tek davranış değişikliği = **nakit tahakkuku** (US 3-aylık T-bill, DGS3MO, 50bp
haircut). E4 (%0) ve E4b (faizli) koşumlarını YAN YANA üretir → faizin izole
katkısını ayrıştırır. Mühürlü tabloyu (E4_CRITERIA.md, referans=SEPET, DEĞİŞMEZ)
E4b (faizli) sayılarıyla MEKANİK doldurur.

Benchmark (sepet/SPY) ve sealed-değerlendirme kodu E4 sürücüsünden İTHAL edilir
(drift imkânsız). İstatistikler run_regime_core.py'den (S1b özdeşliği).

Regresyon: %0 koşumu (cash_rate=None), E4 headline sayılarını bayt-bayt yeniden
üretir (tek-değişiklik izolasyonu) — ayrıca tests/test_e4b_us.py.

Canlı bot modüllerine / config/config.yaml / config/regime_core.yaml'a DOKUNMAZ.

Kullanım:  python -m tools.run_regime_core_us_e4b
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import pandas as pd

from backtest.regime_core import RegimeCoreConfig, compute_cash_only_curve
from backtest.regime_core_us import run_regime_core_costmodel
from costs.us_equities import us_cost_model_from_config
from tools.e4_common import compute_benchmarks, load_us_closes, load_us_config
from tools.run_regime_core import (
    compute_monthly_returns,
    compute_summary,
    find_drawdown_episodes,
    gen_walk_forward_windows,
    monthly_sharpe,
    monte_carlo_monthly,
)
from tools.run_regime_core_us import BIST_D1_USD_CONTEXT, _core_cfg, evaluate_sealed

OUT_DIR = Path("runtime/e4/regime_core_us_e4b")


def load_us_cash_rate(cfg: dict) -> tuple[pd.Series, float]:
    cy = cfg["cash_yield"]
    rate = pd.read_parquet(cy["aux_snapshot"])["rate_pct"] / 100.0
    haircut = cy["haircut_bps"] / 1e4
    return rate, haircut


def _oos(closes, core, cost_model, windows, cash_rate, haircut) -> dict:
    oos_monthly: list[float] = []
    for _ts, _te, test_start, test_end in windows:
        rw = run_regime_core_costmodel(closes, core, cost_model,
                                       date_range=(test_start, test_end),
                                       cash_rate=cash_rate, haircut=haircut)
        oos_monthly.extend(compute_monthly_returns(rw.equity_curve).tolist())
    ser = pd.Series(oos_monthly)
    eq = (1 + ser).cumprod()
    return {"n_windows": len(windows), "oos_monthly_sharpe": monthly_sharpe(ser),
            "oos_max_dd": float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0,
            "oos_n_months": len(ser)}


def _days_in_cash_pct(regime_on: pd.Series, equity_index: pd.DatetimeIndex) -> float:
    """t+1 yürütmede in_position[i] = regime_on[i-1]. Nakitte olunan gün oranı."""
    in_pos = regime_on.shift(1).fillna(False).reindex(equity_index).fillna(False)
    return float((~in_pos.astype(bool)).mean() * 100.0)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_us_config()
    core = _core_cfg(cfg)
    cost_model = us_cost_model_from_config(cfg["costs"])
    closes, ghost = load_us_closes(cfg)
    cash_rate, haircut = load_us_cash_rate(cfg)
    print(f"US cash: DGS3MO, haircut={haircut*1e4:.0f}bps, aux={cfg['cash_yield']['aux_snapshot']}")

    # --- Ana: %0 (E4 baseline) vs faizli (E4b) ---
    res0 = run_regime_core_costmodel(closes, core, cost_model, cash_rate=None)
    resY = run_regime_core_costmodel(closes, core, cost_model, cash_rate=cash_rate, haircut=haircut)
    s0, sY = compute_summary(res0.equity_curve), compute_summary(resY.equity_curve)
    monthlyY = compute_monthly_returns(resY.equity_curve)

    # Tek-değişiklik izolasyonu: anahtarlama tarihleri AYNI (nakit sinyali etkilemez).
    sw0 = [(s.date, s.action) for s in res0.switches]
    swY = [(s.date, s.action) for s in resY.switches]
    switches_identical = sw0 == swY
    days_cash = _days_in_cash_pct(resY.regime_on, resY.equity_curve.index)

    # --- Ayrıştırma (faizin izole katkısı) ---
    decomposition = {
        "days_in_cash_pct": days_cash,
        "e4_zero": s0, "e4b_yield": sY,
        "delta": {k: sY[k] - s0[k] for k in ("total_return", "cagr", "max_drawdown", "sharpe")},
        "switches_identical_0_vs_yield": switches_identical,
        "n_switches": len(resY.switches),
    }

    # --- 'Sadece nakit, US-faizli' bilgilendirici eğri (S1b (b) emsali) ---
    cash_only_yield = compute_cash_only_curve(resY.equity_curve.index, cash_rate,
                                              core.initial_equity, haircut=haircut)
    cash_only_summary = compute_summary(cash_only_yield)

    # --- MC (faizli, S1b yöntemi) ---
    mc = cfg["monte_carlo"]
    mc_result = monte_carlo_monthly(monthlyY.to_numpy(), mc["runs"], mc["random_seed"])

    # --- OOS (faizli) ---
    wf = cfg["walk_forward"]
    windows = gen_walk_forward_windows(closes[cfg["symbols"][0]].index,
                                       wf["train_months"], wf["test_months"], wf["step_months"])
    oos_yield = _oos(closes, core, cost_model, windows, cash_rate, haircut)

    # --- Cliff grid (faizli) — criterion 4 sağlamlık, faizli teyit ---
    grid = cfg["cliff_grid"]
    grid_rows = []
    for n, b, m in product(grid["ma_period"], grid["band_pct"], grid["confirm_days"]):
        gcfg = RegimeCoreConfig(symbols=cfg["symbols"], ma_period=n, band_pct=b, confirm_days=m,
                                commission_bps=core.commission_bps, slippage_bps=core.slippage_bps,
                                initial_equity=core.initial_equity)
        rg = run_regime_core_costmodel(closes, gcfg, cost_model, cash_rate=cash_rate, haircut=haircut)
        sg = compute_summary(rg.equity_curve)
        grid_rows.append({"ma_period": n, "band_pct": b, "confirm_days": m, "sharpe": sg["sharpe"],
                          "max_drawdown": sg["max_drawdown"], "cagr": sg["cagr"], "n_switches": len(rg.switches)})
    pd.DataFrame(grid_rows).to_csv(OUT_DIR / "cliff_grid.csv", index=False)

    # --- Benchmark (E4 ile AYNI kaynak; nakitten bağımsız) + mühürlü tablo ---
    bench = compute_benchmarks(cfg)
    sealed = evaluate_sealed(sY, oos_yield, bench)

    episodes10 = find_drawdown_episodes(resY.equity_curve, min_depth=0.10)

    print("\n=== AYRIŞTIRMA (faizin izole katkısı) ===")
    print(json.dumps(decomposition, indent=2, default=str))
    print("\n=== MÜHÜRLÜ TABLO — E4b faizli (mekanik) ===")
    print(json.dumps(sealed, indent=2, default=str))
    print("\nMC(faizli):", json.dumps(mc_result), "\nOOS(faizli):", json.dumps(oos_yield))

    output = {
        "run": "D1-US E4b (nakit tahakkuku: DGS3MO 3-aylık T-bill, 50bp haircut)",
        "single_change": "nakit tahakkuku (cash_rate) — sinyal/switch/maliyet AYNI",
        "cash_source": {"series": "DGS3MO", "haircut_bps": haircut * 1e4,
                        "aux_snapshot": cfg["cash_yield"]["aux_snapshot"]},
        "decomposition": decomposition,
        "cash_only_with_yield_informational": cash_only_summary,
        "monte_carlo_monthly": mc_result,
        "walk_forward_oos_strategy": oos_yield,
        "benchmarks": {"basket_buy_hold": bench["basket_buy_hold"], "basket_oos": bench["basket_oos"],
                       "spy_buy_hold": bench["spy_buy_hold"], "spy_oos": bench["spy_oos"]},
        "sealed_criteria_mechanical_e4b": sealed,
        "drawdown_episodes_10pct_count": len(episodes10),
        "bist_d1_usd_context": BIST_D1_USD_CONTEXT,
        "data_provenance": {"universe_snapshot": cfg["backtest"]["snapshot"],
                            "us_rate_snapshot": cfg["cash_yield"]["aux_snapshot"],
                            "spy_snapshot": bench["spy_snapshot"]},
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    resY.equity_curve.to_csv(OUT_DIR / "equity_curve_yield.csv")
    print(f"\nYazildi: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()

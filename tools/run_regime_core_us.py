# tools/run_regime_core_us.py
"""EXPANSION E4 (US adil test) — D1-US spike SÜRÜCÜSÜ (item 4).

`backtest/regime_core_us.py` (CostModel-farkında D1 döngüsü) + `tools/e4_common.py`
(benchmark) üzerine kurulur. Koşumlar: A (ana), OOS (walk-forward, param.
optimizasyonu YOK), MC (aylık getiri permütasyonu, S1b yöntemi), D (uçurum
grid'i — SAĞLAMLIK, seçim değil). Sonuçları MÜHÜRLÜ kriterlere MEKANİK uygular.

İstatistik fonksiyonları `tools/run_regime_core.py`'den (S1b özdeşliği). Nakit
bacağı = %0 (madde 1 kararı → cash_rate=None). Çıktı: runtime/e4/regime_core_us/.

Canlı bot modüllerine / config/config.yaml / config/regime_core.yaml'a DOKUNMAZ.

Kullanım:  python -m tools.run_regime_core_us
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import pandas as pd

from backtest.regime_core import RegimeCoreConfig
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

OUT_DIR = Path("runtime/e4/regime_core_us")

# S1b bağlam satırı (REGIME_CORE_S1B.md (f) — BİLGİLENDİRİCİ, mühürlü değil).
BIST_D1_USD_CONTEXT = {
    "strategy_usd_sharpe": 0.435, "basket_usd_sharpe": 0.577,
    "strategy_usd_cagr": 0.0870, "basket_usd_cagr": 0.1515,
    "strategy_usd_maxdd": -0.6703, "basket_usd_maxdd": -0.7506,
    "note": "BIST-D1 (S1b) USD terimde: filtre Sharpe'ı sepetin ALTINDA (USD).",
}


def _core_cfg(cfg: dict) -> RegimeCoreConfig:
    reg, c = cfg["regime"], cfg["costs"]
    return RegimeCoreConfig(
        symbols=cfg["symbols"], ma_period=reg["ma_period"], band_pct=reg["band_pct"],
        confirm_days=reg["confirm_days"], commission_bps=c["commission_bps"],
        slippage_bps=c["slippage_bps"], initial_equity=cfg["initial_equity"],
    )


def evaluate_sealed(strategy: dict, oos_strategy: dict, bench: dict) -> dict:
    """MÜHÜRLÜ 4 kriteri MEKANİK uygular (E4_CRITERIA.md). Referans = sepet.
    Hüküm YOK — yalnız PASS/FAIL üretir."""
    basket = bench["basket_buy_hold"]
    basket_oos = bench["basket_oos"]
    c1_thr = basket["sharpe"]
    c2_thr = basket["max_drawdown"] / 2.0           # işaretli (negatif); strateji ≥ bu olmalı
    c3a_thr = basket_oos["oos_monthly_sharpe"]
    c3b_thr = basket_oos["oos_max_dd"] / 2.0

    c1 = strategy["sharpe"] > c1_thr
    c2 = strategy["max_drawdown"] >= c2_thr          # derinlik ≤ yarısı  ⇔ maxDD ≥ eşik
    c3a = oos_strategy["oos_monthly_sharpe"] > c3a_thr
    c3b = oos_strategy["oos_max_dd"] >= c3b_thr
    all_pass = c1 and c2 and c3a and c3b
    return {
        "criterion_1_sharpe": {"threshold": c1_thr, "strategy": strategy["sharpe"], "pass": bool(c1)},
        "criterion_2_maxdd": {"threshold_signed": c2_thr, "threshold_depth_pct": abs(c2_thr) * 100,
                              "strategy": strategy["max_drawdown"], "pass": bool(c2)},
        "criterion_3a_oos_sharpe": {"threshold": c3a_thr, "strategy": oos_strategy["oos_monthly_sharpe"],
                                    "pass": bool(c3a)},
        "criterion_3b_oos_maxdd": {"threshold_signed": c3b_thr, "threshold_depth_pct": abs(c3b_thr) * 100,
                                   "strategy": oos_strategy["oos_max_dd"], "pass": bool(c3b)},
        "all_4_pass": bool(all_pass),
        "rule": "4/4 geçerse US-kabul ADAYI; herhangi biri kalırsa reddedilir. Karar kullanıcının/baş danışmanın.",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_us_config()
    core = _core_cfg(cfg)
    cost_model = us_cost_model_from_config(cfg["costs"])
    closes, ghost = load_us_closes(cfg)

    # --- Benchmark (e4_common — mühürle AYNI kaynak) + self-check ---
    bench = compute_benchmarks(cfg)

    # --- Koşum A: ana ---
    print("=== D1-US Koşum A: ana (cash=0%) ===")
    result_a = run_regime_core_costmodel(closes, core, cost_model, cash_rate=None)
    summary_a = compute_summary(result_a.equity_curve)
    monthly_a = compute_monthly_returns(result_a.equity_curve)
    print(json.dumps(summary_a, indent=2), "switches:", len(result_a.switches))

    result_a.equity_curve.to_csv(OUT_DIR / "equity_curve_main.csv")
    pd.DataFrame([{"date": s.date, "action": s.action, "equity_before": s.equity_before,
                   "equity_after": s.equity_after} for s in result_a.switches]).to_csv(
        OUT_DIR / "switches_main.csv", index=False)

    # --- Koşum C: Monte Carlo (aylık getiri permütasyonu, S1b yöntemi) ---
    mc = cfg["monte_carlo"]
    mc_result = monte_carlo_monthly(monthly_a.to_numpy(), mc["runs"], mc["random_seed"])
    print("MC:", json.dumps(mc_result, indent=2))

    # --- Koşum B: Walk-forward OOS (strateji tarafı; param opt YOK) ---
    wf = cfg["walk_forward"]
    windows = gen_walk_forward_windows(closes[cfg["symbols"][0]].index,
                                       wf["train_months"], wf["test_months"], wf["step_months"])
    oos_strategy_monthly: list[float] = []
    window_rows = []
    for _ts, _te, test_start, test_end in windows:
        rw = run_regime_core_costmodel(closes, core, cost_model,
                                       date_range=(test_start, test_end), cash_rate=None)
        oos_strategy_monthly.extend(compute_monthly_returns(rw.equity_curve).tolist())
        window_rows.append({"test_start": str(test_start.date()), "test_end": str(test_end.date()),
                            "test_switches": len(rw.switches)})
    oos_ser = pd.Series(oos_strategy_monthly)
    oos_eq = (1 + oos_ser).cumprod()
    oos_strategy = {
        "n_windows": len(windows),
        "oos_monthly_sharpe": monthly_sharpe(oos_ser),
        "oos_max_dd": float((oos_eq / oos_eq.cummax() - 1).min()) if len(oos_eq) else 0.0,
        "oos_n_months": len(oos_ser),
    }
    pd.DataFrame(window_rows).to_csv(OUT_DIR / "walk_forward_windows.csv", index=False)
    print("OOS strateji:", json.dumps(oos_strategy, indent=2))

    # --- Koşum D: uçurum grid'i (SAĞLAMLIK, seçim DEĞİL) ---
    grid = cfg["cliff_grid"]
    grid_rows = []
    for n, b, m in product(grid["ma_period"], grid["band_pct"], grid["confirm_days"]):
        gcfg = RegimeCoreConfig(symbols=cfg["symbols"], ma_period=n, band_pct=b, confirm_days=m,
                                commission_bps=core.commission_bps, slippage_bps=core.slippage_bps,
                                initial_equity=core.initial_equity)
        rg = run_regime_core_costmodel(closes, gcfg, cost_model, cash_rate=None)
        sg = compute_summary(rg.equity_curve)
        grid_rows.append({"ma_period": n, "band_pct": b, "confirm_days": m, "sharpe": sg["sharpe"],
                          "max_drawdown": sg["max_drawdown"], "cagr": sg["cagr"], "n_switches": len(rg.switches)})
    pd.DataFrame(grid_rows).to_csv(OUT_DIR / "cliff_grid.csv", index=False)

    # --- Drawdown epizotları ---
    episodes5 = find_drawdown_episodes(result_a.equity_curve)[:5]
    episodes10 = find_drawdown_episodes(result_a.equity_curve, min_depth=0.10)

    # --- MÜHÜRLÜ kriterlerin MEKANİK uygulaması ---
    sealed = evaluate_sealed(summary_a, oos_strategy, bench)
    print("\n=== MÜHÜRLÜ TABLO (mekanik) ===")
    print(json.dumps(sealed, indent=2))

    output = {
        "run": "D1-US (regime_core, US CostModel, cash=0% muhafazakar)",
        "cash_leg": "0% (madde 1 karari; cash_rate=None)",
        "params_sealed": {"ma_period": core.ma_period, "band_pct": core.band_pct, "confirm_days": core.confirm_days},
        "cost_model": {"model_id": cost_model.model_id, "commission_bps": cfg["costs"]["commission_bps"],
                       "sec_fee_bps": cfg["costs"]["sec_fee_bps"], "taf_per_share": cfg["costs"]["taf_per_share"],
                       "slippage_bps": cfg["costs"]["slippage_bps"]},
        "main_run": {"summary": summary_a, "n_switches": len(result_a.switches),
                     "ghost_bars_removed": len(ghost), "composite_fill_log": len(result_a.composite_fill_log)},
        "benchmarks": {"basket_buy_hold": bench["basket_buy_hold"], "basket_oos": bench["basket_oos"],
                       "spy_buy_hold": bench["spy_buy_hold"], "spy_oos": bench["spy_oos"]},
        "monte_carlo_monthly": mc_result,
        "walk_forward_oos_strategy": oos_strategy,
        "sealed_criteria_mechanical": sealed,
        "drawdown_episodes_top5": [{"peak": str(e["peak_date"]), "trough": str(e["trough_date"]),
                                    "recovery": str(e["recovery_date"]), "depth": e["depth"]} for e in episodes5],
        "drawdown_episodes_10pct_count": len(episodes10),
        "bist_d1_usd_context": BIST_D1_USD_CONTEXT,
        "data_provenance": {"universe_snapshot": cfg["backtest"]["snapshot"],
                            "spy_snapshot": bench["spy_snapshot"],
                            "composite_start": bench["composite_start"], "composite_end": bench["composite_end"],
                            "n_days": bench["n_days"]},
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nYazildi: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()

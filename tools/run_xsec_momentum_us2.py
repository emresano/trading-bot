# tools/run_xsec_momentum_us2.py
"""D2US-S1 — KESİTSEL MOMENTUM (D2-US) spike SÜRÜCÜSÜ (item 4).

`backtest/xsec_momentum.py` (bağımsız simülatör) + `tools/e4_common.py` (benchmark,
E4 ile AYNI kaynak → drift imkânsız) + `tools/run_regime_core.py` istatistikleri
(S1b özdeşliği) üzerine kurulur. Mühürlü tasarımı (config/momentum_us2.yaml +
D2US_CRITERIA.md) MEKANİK uygular; kriter eşiklerini ESNETMEZ, bileşen SEÇMEZ.

Koşumlar: (A) ana koşum → mühürlü tablo; OOS (39 pencere, param opt YOK); MC
(S1b yöntemi, seed=42). ZORUNLU ek analizler: (a) momentum-crash epizotları (2009/
2020 dip-dönüşleri); (b) yıllık turnover + maliyet sürüklemesi (bps/yıl); (c)
ABLASYON (yalın→+FIP→+kapı→+vol) BİLGİ-only; (d) komşuluk (formation/N/vol) gözlemsel.

Çıktı: runtime/d2us/momentum_us2/. Canlı bot / S1/S1b/E4 araçları / config/config.yaml
/ config/regime_core*.yaml'a DOKUNMAZ.

Kullanım:  python -m tools.run_xsec_momentum_us2
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from backtest.xsec_momentum import XSecMomentumConfig, run_xsec_momentum
from costs.us_equities import UsEquitiesCostModel, us_cost_model_from_config
from tools.e4_common import compute_benchmarks, load_us_closes
from tools.run_regime_core import (
    compute_monthly_returns,
    compute_summary,
    find_drawdown_episodes,
    gen_walk_forward_windows,
    monthly_sharpe,
    monte_carlo_monthly,
)

CFG_PATH = Path("config/momentum_us2.yaml")
OUT_DIR = Path("runtime/d2us/momentum_us2")

# E4b D1-US bağlamı (BİLGİLENDİRİCİ — mühürlü değil; D2 ayrı ailedir).
D1_US_CONTEXT = {
    "note": "D1-US (E4b, regime_core) US-referansta mühürlü tabloda 1/4 → KESİN RED "
            "(KALICI KAYIT 16). D2-US AYRI aile; kıyas yalnız bilgilendirici.",
    "d1_us_e4b_cagr": 0.0860, "d1_us_e4b_sharpe": 0.758, "d1_us_e4b_maxdd": -0.2311,
}


def load_cfg() -> dict:
    return yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))


def build_xsec_cfg(cfg: dict, **overrides) -> XSecMomentumConfig:
    """Mühürlü design bloğundan XSecMomentumConfig. `overrides` YALNIZCA ablasyon
    (item 4c) / komşuluk (item 4d) BİLGİ koşumları için — mühürlü koşumda boş."""
    d, vt = cfg["design"], cfg["design"]["vol_target"]
    base = dict(
        symbols=cfg["symbols"], formation_months=d["formation_months"],
        skip_months=d["skip_months"], preselect_top=d["preselect_top"],
        final_n=d["final_n"], target_vol=vt["target_vol"],
        vol_window_days=vt["realized_window_days"], max_leverage=vt["max_leverage"],
        initial_equity=cfg["initial_equity"],
        abs_gate_haircut=d["abs_momentum_gate"]["haircut_bps"] / 1e4,
    )
    base.update(overrides)
    return XSecMomentumConfig(**base)


def evaluate_sealed_d2(strategy: dict, oos_strategy: dict, bench: dict) -> dict:
    """MÜHÜRLÜ 4 kriteri MEKANİK uygular (D2US_CRITERIA.md §3, referans=sepet).
    (1) Sharpe>sepet; (2) CAGR>sepet; (3a) OOS Sharpe>sepet OOS; (3b) tam-dönem
    |maxDD|≤sepet |maxDD|. Hüküm YOK — yalnız PASS/FAIL."""
    b, b_oos = bench["basket_buy_hold"], bench["basket_oos"]
    c1 = strategy["sharpe"] > b["sharpe"]
    c2 = strategy["cagr"] > b["cagr"]
    c3a = oos_strategy["oos_monthly_sharpe"] > b_oos["oos_monthly_sharpe"]
    c3b = strategy["max_drawdown"] >= b["max_drawdown"]   # derinlik ≤ sepet ⇔ maxDD ≥ sepet
    return {
        "criterion_1_sharpe": {"threshold": b["sharpe"], "strategy": strategy["sharpe"], "pass": bool(c1)},
        "criterion_2_cagr": {"threshold": b["cagr"], "strategy": strategy["cagr"], "pass": bool(c2)},
        "criterion_3a_oos_sharpe": {"threshold": b_oos["oos_monthly_sharpe"],
                                    "strategy": oos_strategy["oos_monthly_sharpe"], "pass": bool(c3a)},
        "criterion_3b_maxdd_fullperiod": {"threshold_signed": b["max_drawdown"],
                                          "threshold_depth_pct": abs(b["max_drawdown"]) * 100,
                                          "strategy": strategy["max_drawdown"], "pass": bool(c3b)},
        "all_4_pass": bool(c1 and c2 and c3a and c3b),
        "rule": "1+2+3a+3b TAMAMI geçerse US-kabul ADAYI; biri kalırsa red (dar-fark yok). "
                "Karar kullanıcının/baş danışmanın.",
    }


def window_stats(equity: pd.Series, basket: pd.Series, rebals, start: str, end: str) -> dict:
    """Bir tarih penceresinde strateji vs sepet getirisi + strateji davranışı."""
    s = equity.loc[start:end]
    b = basket.loc[start:end]
    seg_rebals = [r for r in rebals if str(start) <= str(r.signal_date.date()) <= str(end)]
    exps = [r.exposure for r in seg_rebals]
    cashslots = [r.n_cash_slots for r in seg_rebals]
    dd = float((s / s.cummax() - 1).min()) if len(s) > 1 else 0.0
    return {
        "window": f"{start}..{end}",
        "strategy_return": float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0,
        "basket_return": float(b.iloc[-1] / b.iloc[0] - 1) if len(b) > 1 else 0.0,
        "strategy_maxdd_in_window": dd,
        "n_rebalances": len(seg_rebals),
        "mean_exposure": float(np.mean(exps)) if exps else None,
        "min_exposure": float(np.min(exps)) if exps else None,
        "mean_cash_slots": float(np.mean(cashslots)) if cashslots else None,
        "max_cash_slots": int(np.max(cashslots)) if cashslots else None,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_cfg()
    xcfg = build_xsec_cfg(cfg)
    cost_model = us_cost_model_from_config(cfg["costs"])
    closes, ghost = load_us_closes(cfg)
    cash_rate = pd.read_parquet(cfg["cash_yield"]["aux_snapshot"])["rate_pct"] / 100.0
    cashleg_haircut = cfg["cash_yield"]["haircut_bps"] / 1e4
    initial = float(cfg["initial_equity"])

    # --- Benchmark (E4 ile AYNI kaynak; mühürle birebir) ---
    bench = compute_benchmarks(cfg)
    basket_equity = None  # crash analizi için sepet equity'sini kur (aynı fonksiyon)
    from tools.e4_common import build_basket_curve, load_us_closes as _luc
    _closes, _ = _luc(cfg)
    _, basket_equity, _ = build_basket_curve(_closes, initial)

    # --- Koşum A: ana (mühürlü tam paket) ---
    print("=== D2-US Koşum A: ana (mühürlü tam paket) ===")
    res = run_xsec_momentum(closes, xcfg, cost_model, cash_rate=cash_rate,
                            cashleg_haircut=cashleg_haircut)
    summ = compute_summary(res.equity_curve)
    monthly = compute_monthly_returns(res.equity_curve)
    print(json.dumps(summ, indent=2), "rebalances:", len(res.rebalances))
    res.equity_curve.to_csv(OUT_DIR / "equity_curve_main.csv")
    pd.DataFrame([{"signal_date": r.signal_date, "exec_date": r.exec_date,
                   "n_invested": len(r.invested), "n_cash_slots": r.n_cash_slots,
                   "exposure": r.exposure, "turnover": r.turnover, "cost": r.cost,
                   "invested": "|".join(r.invested)} for r in res.rebalances]).to_csv(
        OUT_DIR / "rebalances.csv", index=False)

    # --- MC (S1b yöntemi, seed=42) ---
    mc = cfg["monte_carlo"]
    mc_result = monte_carlo_monthly(monthly.to_numpy(), mc["runs"], mc["random_seed"])

    # --- OOS (walk-forward; param optimizasyonu YOK) ---
    wf = cfg["walk_forward"]
    windows = gen_walk_forward_windows(closes[cfg["symbols"][0]].index,
                                       wf["train_months"], wf["test_months"], wf["step_months"])
    oos_monthly: list[float] = []
    for _ts, _te, test_start, test_end in windows:
        rw = run_xsec_momentum(closes, xcfg, cost_model, date_range=(test_start, test_end),
                               cash_rate=cash_rate, cashleg_haircut=cashleg_haircut)
        oos_monthly.extend(compute_monthly_returns(rw.equity_curve).tolist())
    oos_ser = pd.Series(oos_monthly)
    oos_eq = (1 + oos_ser).cumprod()
    oos_strategy = {
        "n_windows": len(windows), "oos_monthly_sharpe": monthly_sharpe(oos_ser),
        "oos_max_dd": float((oos_eq / oos_eq.cummax() - 1).min()) if len(oos_eq) else 0.0,
        "oos_n_months": len(oos_ser),
    }
    print("OOS:", json.dumps(oos_strategy))

    # --- MÜHÜRLÜ TABLO (mekanik) ---
    sealed = evaluate_sealed_d2(summ, oos_strategy, bench)
    print("\n=== MÜHÜRLÜ TABLO (mekanik) ===")
    print(json.dumps(sealed, indent=2))

    # --- (a) Momentum-crash epizotları (2009 / 2020 dip-dönüşleri) ---
    crash = {
        "gfc_2009_rebound": window_stats(res.equity_curve, basket_equity, res.rebalances,
                                         "2009-03-09", "2009-09-30"),
        "gfc_2009_full_year": window_stats(res.equity_curve, basket_equity, res.rebalances,
                                           "2009-01-01", "2009-12-31"),
        "covid_2020_rebound": window_stats(res.equity_curve, basket_equity, res.rebalances,
                                           "2020-03-23", "2020-08-31"),
        "covid_2020_full_year": window_stats(res.equity_curve, basket_equity, res.rebalances,
                                             "2020-01-01", "2020-12-31"),
    }
    print("\n=== (a) Momentum-crash epizotları ===")
    print(json.dumps(crash, indent=2, default=str))

    # --- (b) Turnover + maliyet sürüklemesi ---
    by_year: dict[int, float] = {}
    for r in res.rebalances:
        by_year[r.signal_date.year] = by_year.get(r.signal_date.year, 0.0) + r.turnover
    total_cost = float(sum(r.cost for r in res.rebalances))
    years = (res.equity_curve.index[-1] - res.equity_curve.index[0]).days / 365.25
    # Yetkili sürükleme ölçüsü: sıfır-maliyet karşı-olgusu CAGR farkı (bps/yıl).
    zero_cm = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.0, taf_per_share=0.0, slippage_bps=0.0)
    res_zero = run_xsec_momentum(closes, xcfg, zero_cm, cash_rate=cash_rate, cashleg_haircut=cashleg_haircut)
    summ_zero = compute_summary(res_zero.equity_curve)
    cost_analysis = {
        "mean_annual_turnover": float(np.mean(list(by_year.values()))),
        "mean_monthly_turnover": float(np.mean([r.turnover for r in res.rebalances])),
        "total_cost_usd": total_cost,
        "cost_drag_bps_per_year_via_avg_equity": total_cost / float(res.equity_curve.mean()) / years * 1e4,
        "cagr_with_costs": summ["cagr"], "cagr_zero_cost": summ_zero["cagr"],
        "cost_drag_bps_per_year_via_cagr_delta": (summ_zero["cagr"] - summ["cagr"]) * 1e4,
        "annual_turnover_by_year": {str(y): round(v, 3) for y, v in sorted(by_year.items())},
    }
    print("\n=== (b) Turnover + maliyet sürüklemesi ===")
    print(json.dumps(cost_analysis, indent=2))

    # --- (c) ABLASYON (yalın → +FIP → +kapı → +vol) — BİLGİ-only, seçim YOK ---
    ablation = {}
    for name, ov in [
        ("V0_plain_12_1_top10", dict(use_fip=False, use_abs_gate=False, use_vol_target=False)),
        ("V1_plus_fip", dict(use_fip=True, use_abs_gate=False, use_vol_target=False)),
        ("V2_plus_abs_gate", dict(use_fip=True, use_abs_gate=True, use_vol_target=False)),
        ("V3_full_plus_vol", dict(use_fip=True, use_abs_gate=True, use_vol_target=True)),
    ]:
        rv = run_xsec_momentum(closes, build_xsec_cfg(cfg, **ov), cost_model,
                               cash_rate=cash_rate, cashleg_haircut=cashleg_haircut)
        sv = compute_summary(rv.equity_curve)
        ablation[name] = {"cagr": sv["cagr"], "max_drawdown": sv["max_drawdown"],
                          "sharpe": sv["sharpe"], "n_rebalances": len(rv.rebalances)}
    print("\n=== (c) ABLASYON (BİLGİ-only) ===")
    print(json.dumps(ablation, indent=2))

    # --- (d) Komşuluk (gözlemsel; SEÇİM ARACI DEĞİL) ---
    nb = cfg["neighborhood"]
    neighborhood = {"formation_months": {}, "final_n": {}, "vol_window_days": {}}
    for fm in nb["formation_months"]:
        rv = run_xsec_momentum(closes, build_xsec_cfg(cfg, formation_months=fm), cost_model,
                               cash_rate=cash_rate, cashleg_haircut=cashleg_haircut)
        s = compute_summary(rv.equity_curve)
        neighborhood["formation_months"][str(fm)] = {"cagr": s["cagr"], "sharpe": s["sharpe"],
                                                      "max_drawdown": s["max_drawdown"]}
    for fn in nb["final_n"]:
        rv = run_xsec_momentum(closes, build_xsec_cfg(cfg, final_n=fn), cost_model,
                               cash_rate=cash_rate, cashleg_haircut=cashleg_haircut)
        s = compute_summary(rv.equity_curve)
        neighborhood["final_n"][str(fn)] = {"cagr": s["cagr"], "sharpe": s["sharpe"],
                                            "max_drawdown": s["max_drawdown"]}
    for vw in nb["vol_window_days"]:
        rv = run_xsec_momentum(closes, build_xsec_cfg(cfg, vol_window_days=vw), cost_model,
                               cash_rate=cash_rate, cashleg_haircut=cashleg_haircut)
        s = compute_summary(rv.equity_curve)
        neighborhood["vol_window_days"][str(vw)] = {"cagr": s["cagr"], "sharpe": s["sharpe"],
                                                    "max_drawdown": s["max_drawdown"]}
    print("\n=== (d) Komşuluk (gözlemsel) ===")
    print(json.dumps(neighborhood, indent=2))

    episodes10 = find_drawdown_episodes(res.equity_curve, min_depth=0.10)

    output = {
        "run": "D2-US kesitsel momentum spike (mühürlü tam paket)",
        "sealed_design": cfg["design"],
        "main_run": {"summary": summ, "n_rebalances": len(res.rebalances),
                     "ghost_bars_removed": len(ghost)},
        "monte_carlo_monthly": mc_result,
        "walk_forward_oos_strategy": oos_strategy,
        "benchmarks": {"basket_buy_hold": bench["basket_buy_hold"], "basket_oos": bench["basket_oos"],
                       "spy_buy_hold": bench["spy_buy_hold"], "spy_oos": bench["spy_oos"]},
        "sealed_criteria_mechanical": sealed,
        "momentum_crash_episodes": crash,
        "turnover_cost_analysis": cost_analysis,
        "ablation_information_only": ablation,
        "neighborhood_observational": neighborhood,
        "drawdown_episodes_10pct_count": len(episodes10),
        "d1_us_context": D1_US_CONTEXT,
        "data_provenance": {"universe_snapshot": cfg["backtest"]["snapshot"],
                            "us_rate_snapshot": cfg["cash_yield"]["aux_snapshot"],
                            "spy_snapshot": cfg["benchmark"]["snapshot"],
                            "composite_start": bench["composite_start"], "composite_end": bench["composite_end"],
                            "n_days": bench["n_days"]},
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nYazildi: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()

# tools/run_regime_core.py
"""S1 spike backtest sürücüsü — Rejim-Filtreli Çekirdek (D1 tasarımı).

`backtest/regime_core.py`nin (bağımsız simülatör) 4 koşumunu (A: ana koşum,
B: walk-forward, C: Monte Carlo, D: uçurum kontrolü grid'i) + 3 benchmark'ı
(XU100 al-tut, 12-sembol sepeti al-tut, sadece-nakit) çalıştırır, sonuçları
JSON olarak yazar (REGIME_CORE_S1.md'nin girdisi).

`backtest/engine.py`, `strategy/`, `risk/`, `config/config.yaml`'a
DOKUNMAZ/BAĞIMLI DEĞİLDİR — tüm istatistik fonksiyonları bu dosyada
bağımsız olarak (yeniden) yazılmıştır.

Kullanım: python -m tools.run_regime_core
"""
from __future__ import annotations
import json
from datetime import date
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from backtest.regime_core import RegimeCoreConfig, run_regime_core
from data.cleaning import load_and_clean_universe

CFG_PATH = Path("config/regime_core.yaml")
OUT_DIR = Path("runtime/regime_core_s1")
TRADING_DAYS_PER_YEAR = 252
MONTHS_PER_YEAR = 12


def load_config() -> dict:
    return yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))


def load_closes(cfg: dict) -> dict[str, pd.Series]:
    snapshot_dir = Path(cfg["backtest"]["snapshot"])
    start = cfg["backtest"]["start"]
    symbols = cfg["symbols"]

    def _load_daily_raw(s: str) -> pd.DataFrame:
        df = pd.read_parquet(snapshot_dir / f"{s}.parquet")
        return df.loc[start:]

    cleaned, ghost_log = load_and_clean_universe(symbols, _load_daily_raw)
    closes = {s: df["close"] for s, df in cleaned.items()}
    return closes, ghost_log


# --- İstatistik yardımcıları (bağımsız, backtest/metrics.py'ye bağımlı değil) ---

def compute_summary(equity_curve: pd.Series) -> dict:
    if equity_curve.empty or len(equity_curve) < 2:
        return {"total_return": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    cagr = float((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    max_dd = float(drawdown.min())
    daily_returns = equity_curve.pct_change().dropna()
    sharpe = (
        float(daily_returns.mean() / daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        if daily_returns.std() > 0 else 0.0
    )
    return {"total_return": total_return, "cagr": cagr, "max_drawdown": max_dd, "sharpe": sharpe}


def compute_monthly_returns(equity_curve: pd.Series) -> pd.Series:
    if equity_curve.empty:
        return pd.Series(dtype=float)
    monthly = equity_curve.resample("ME").last()
    return monthly.pct_change().dropna()


def monthly_sharpe(monthly_returns: pd.Series) -> float:
    if len(monthly_returns) < 2 or monthly_returns.std() == 0:
        return 0.0
    return float(monthly_returns.mean() / monthly_returns.std() * np.sqrt(MONTHS_PER_YEAR))


def find_drawdown_episodes(equity_curve: pd.Series, min_depth: float = 0.0) -> list[dict]:
    """Peak->trough->recovery epizotlarını bulur. `min_depth`: yalnızca bu
    derinlikten (mutlak, örn. 0.10) DAHA KÖTÜ epizotlar döner. Recovery
    edilmemiş (hâlâ devam eden) bir epizot varsa recovery_date=None döner."""
    if equity_curve.empty:
        return []
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1

    episodes: list[dict] = []
    in_dd = False
    peak_date = equity_curve.index[0]
    last_peak_date = equity_curve.index[0]
    trough_date = None
    trough_val = 0.0

    for date_i, dd in drawdown.items():
        if dd >= -1e-12:
            last_peak_date = date_i
            if in_dd:
                episodes.append({
                    "peak_date": peak_date, "trough_date": trough_date,
                    "recovery_date": date_i, "depth": trough_val,
                })
                in_dd = False
        else:
            if not in_dd:
                in_dd = True
                peak_date = last_peak_date
                trough_date = date_i
                trough_val = dd
            elif dd < trough_val:
                trough_date = date_i
                trough_val = dd
    if in_dd:
        episodes.append({
            "peak_date": peak_date, "trough_date": trough_date,
            "recovery_date": None, "depth": trough_val,
        })

    episodes = [e for e in episodes if e["depth"] <= -min_depth]
    episodes.sort(key=lambda e: e["depth"])
    return episodes


def monte_carlo_monthly(monthly_returns: np.ndarray, runs: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    dds = np.empty(runs)
    for i in range(runs):
        eq = (1 + rng.permutation(monthly_returns)).cumprod()
        dds[i] = (eq / np.maximum.accumulate(eq) - 1.0).min()
    p5, p50, p95 = np.percentile(dds, [5, 50, 95])
    return {"dd_p5": float(p5), "dd_median": float(p50), "dd_p95": float(p95)}


def gen_walk_forward_windows(all_dates: pd.DatetimeIndex, train_months, test_months, step_months):
    start_date, end_date = all_dates[0], all_dates[-1]
    windows = []
    window_start = start_date
    while True:
        train_start = window_start
        train_end = train_start + pd.DateOffset(months=train_months)
        test_start = train_end
        test_end = test_start + pd.DateOffset(months=test_months)
        if test_end > end_date:
            break
        windows.append((train_start, train_end, test_start, test_end))
        window_start = window_start + pd.DateOffset(months=step_months)
    return windows


def main() -> None:
    cfg_dict = load_config()
    closes, ghost_log = load_closes(cfg_dict)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    reg = cfg_dict["regime"]
    core_cfg = RegimeCoreConfig(
        symbols=cfg_dict["symbols"], ma_period=reg["ma_period"], band_pct=reg["band_pct"],
        confirm_days=reg["confirm_days"], commission_bps=cfg_dict["costs"]["commission_bps"],
        slippage_bps=cfg_dict["costs"]["slippage_bps"], initial_equity=cfg_dict["initial_equity"],
    )

    print("=== Koşum A: ana koşum ===")
    result_a = run_regime_core(closes, core_cfg)
    summary_a = compute_summary(result_a.equity_curve)
    monthly_a = compute_monthly_returns(result_a.equity_curve)
    print(json.dumps(summary_a, indent=2))
    print(f"switches: {len(result_a.switches)}, composite_fill_log: {len(result_a.composite_fill_log)}")

    result_a.equity_curve.to_csv(OUT_DIR / "equity_curve_main.csv")
    pd.DataFrame([{"date": sw.date, "action": sw.action, "equity_before": sw.equity_before,
                  "equity_after": sw.equity_after} for sw in result_a.switches]).to_csv(
        OUT_DIR / "switches_main.csv", index=False)

    print("\n=== Benchmark: 12-sembol sepeti al-tut (filtresiz) ===")
    basket_equity = result_a.composite * core_cfg.initial_equity
    basket_equity = basket_equity.loc[result_a.equity_curve.index[0]:]
    summary_basket = compute_summary(basket_equity)
    print(json.dumps(summary_basket, indent=2))

    print("\n=== Benchmark: XU100 al-tut ===")
    from data.historical import load_cached, update_cache
    bench_cfg = cfg_dict["benchmark"]
    update_cache(bench_cfg["index_symbol"], bench_cfg["index_yf_symbol"], "1d")
    xu100_df = load_cached(bench_cfg["index_symbol"], "1d").loc[cfg_dict["backtest"]["start"]:]
    xu100_df = xu100_df.loc[result_a.equity_curve.index[0]: result_a.equity_curve.index[-1]]
    xu100_equity = xu100_df["close"] / xu100_df["close"].iloc[0] * core_cfg.initial_equity
    summary_xu100 = compute_summary(xu100_equity)
    print(json.dumps(summary_xu100, indent=2))

    cash_only_summary = {"total_return": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}

    print("\n=== En kötü 5 drawdown epizodu ===")
    episodes = find_drawdown_episodes(result_a.equity_curve)[:5]
    for e in episodes:
        print(e)

    print("\n=== %10+ DD epizotları ===")
    episodes_10 = find_drawdown_episodes(result_a.equity_curve, min_depth=0.10)
    print(f"{len(episodes_10)} epizot")

    print("\n=== Koşum C: Monte Carlo (aylık getiri permütasyonu) ===")
    mc = cfg_dict["monte_carlo"]
    mc_result = monte_carlo_monthly(monthly_a.to_numpy(), mc["runs"], mc["random_seed"])
    print(json.dumps(mc_result, indent=2))

    print("\n=== Koşum B: Walk-forward (parametre optimizasyonu YOK) ===")
    wf = cfg_dict["walk_forward"]
    windows = gen_walk_forward_windows(closes[cfg_dict["symbols"][0]].index, wf["train_months"],
                                       wf["test_months"], wf["step_months"])
    print(f"{len(windows)} pencere")

    oos_monthly_returns_strategy = []
    oos_monthly_returns_bench = []
    window_rows = []
    for train_start, train_end, test_start, test_end in windows:
        result_w = run_regime_core(closes, core_cfg, date_range=(test_start, test_end))
        m_ret = compute_monthly_returns(result_w.equity_curve)
        oos_monthly_returns_strategy.extend(m_ret.tolist())

        bench_slice = (result_a.composite * core_cfg.initial_equity).loc[test_start:test_end]
        bench_m_ret = compute_monthly_returns(bench_slice)
        oos_monthly_returns_bench.extend(bench_m_ret.tolist())

        window_rows.append({
            "train_start": str(train_start.date()), "test_start": str(test_start.date()),
            "test_end": str(test_end.date()), "test_trade_count": len(result_w.switches),
        })

    oos_strategy_series = pd.Series(oos_monthly_returns_strategy)
    oos_bench_series = pd.Series(oos_monthly_returns_bench)
    oos_sharpe_strategy = monthly_sharpe(oos_strategy_series)
    oos_sharpe_bench = monthly_sharpe(oos_bench_series)
    oos_eq_strategy = (1 + oos_strategy_series).cumprod()
    oos_dd_strategy = float((oos_eq_strategy / oos_eq_strategy.cummax() - 1).min()) if len(oos_eq_strategy) else 0.0
    oos_eq_bench = (1 + oos_bench_series).cumprod()
    oos_dd_bench = float((oos_eq_bench / oos_eq_bench.cummax() - 1).min()) if len(oos_eq_bench) else 0.0

    print(f"OOS aylık-Sharpe (strateji): {oos_sharpe_strategy:.4f}")
    print(f"OOS aylık-Sharpe (al-tut sepeti): {oos_sharpe_bench:.4f}")
    print(f"OOS max DD (strateji): {oos_dd_strategy:.4f}")
    print(f"OOS max DD (al-tut sepeti): {oos_dd_bench:.4f}")

    print("\n=== Koşum D: Uçurum kontrolü grid'i (36 kombinasyon, SEÇİM İÇİN DEĞİL) ===")
    grid = cfg_dict["cliff_grid"]
    grid_rows = []
    for n, b, m in product(grid["ma_period"], grid["band_pct"], grid["confirm_days"]):
        grid_cfg = RegimeCoreConfig(symbols=cfg_dict["symbols"], ma_period=n, band_pct=b, confirm_days=m,
                                    commission_bps=core_cfg.commission_bps, slippage_bps=core_cfg.slippage_bps,
                                    initial_equity=core_cfg.initial_equity)
        result_g = run_regime_core(closes, grid_cfg)
        s = compute_summary(result_g.equity_curve)
        grid_rows.append({"ma_period": n, "band_pct": b, "confirm_days": m,
                          "sharpe": s["sharpe"], "max_drawdown": s["max_drawdown"],
                          "total_return": s["total_return"], "n_switches": len(result_g.switches)})
        print(f"N={n} b={b} M={m}: sharpe={s['sharpe']:.3f} maxdd={s['max_drawdown']:.3f} switches={len(result_g.switches)}")

    pd.DataFrame(grid_rows).to_csv(OUT_DIR / "cliff_grid.csv", index=False)
    pd.DataFrame(window_rows).to_csv(OUT_DIR / "walk_forward_windows.csv", index=False)

    output = {
        "main_run": {
            "summary": summary_a, "n_switches": len(result_a.switches),
            "composite_fill_log_count": len(result_a.composite_fill_log),
            "ghost_bars_removed": [{"symbol": g["symbol"], "date": str(g["date"])} for g in ghost_log],
        },
        "benchmarks": {
            "basket_buy_hold": summary_basket, "xu100_buy_hold": summary_xu100,
            "cash_only": cash_only_summary,
        },
        "drawdown_episodes_top5": [
            {"peak_date": str(e["peak_date"]), "trough_date": str(e["trough_date"]),
            "recovery_date": str(e["recovery_date"]), "depth": e["depth"]}
            for e in episodes
        ],
        "drawdown_episodes_10pct_count": len(episodes_10),
        "drawdown_episodes_10pct": [
            {"peak_date": str(e["peak_date"]), "trough_date": str(e["trough_date"]),
            "recovery_date": str(e["recovery_date"]), "depth": e["depth"]}
            for e in episodes_10
        ],
        "monte_carlo_monthly": mc_result,
        "walk_forward": {
            "n_windows": len(windows),
            "oos_monthly_sharpe_strategy": oos_sharpe_strategy,
            "oos_monthly_sharpe_benchmark": oos_sharpe_bench,
            "oos_max_dd_strategy": oos_dd_strategy,
            "oos_max_dd_benchmark": oos_dd_bench,
        },
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nÖzet yazıldı: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()

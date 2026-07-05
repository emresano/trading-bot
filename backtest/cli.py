# backtest/cli.py
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from backtest.engine import run_backtest
from backtest.metrics import classify_regime, compute_metrics, regime_breakdown
from backtest.montecarlo import run_monte_carlo
from backtest.walkforward import apply_params, evaluate_acceptance, run_walk_forward, sweep_combinations
from indicators.engine import build_features


def _write_trades_csv(trades, path: Path) -> None:
    rows = [
        {
            "symbol": t.symbol, "entry_date": t.entry_date, "entry_price": t.entry_price,
            "exit_date": t.exit_date, "exit_price": t.exit_price, "quantity": t.quantity,
            "exit_reason": t.exit_reason, "pnl": t.pnl, "r_multiple": t.r_multiple,
        }
        for t in trades
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_equity_plot(equity_curve: pd.Series, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    equity_curve.plot(ax=ax)
    ax.set_title("Equity Curve")
    ax.set_xlabel("Tarih")
    ax.set_ylabel("Equity (TL)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _regime_breakdown_table(rows: pd.DataFrame) -> list[str]:
    if rows.empty:
        return ["Trade yok."]
    lines = ["| Rejim | Trade Sayısı | Win Rate | Toplam R |", "|---|---|---|---|"]
    for _, row in rows.iterrows():
        lines.append(f"| {row['regime']} | {row['trade_count']} | {row['win_rate']:.2%} | {row['total_r']:.2f} |")
    return lines


def _write_sweep_csv(symbols: list[str], cfg, load_daily, path: Path) -> list[dict]:
    combos = sweep_combinations()
    rows = []
    for combo in combos:
        combo_cfg = apply_params(cfg, combo)
        bt = run_backtest(symbols, combo_cfg, load_daily)
        m = compute_metrics(bt.equity_curve, bt.trades)
        rows.append({
            **combo, "total_return": m.total_return, "cagr": m.cagr,
            "max_drawdown": m.max_drawdown, "sharpe": m.sharpe,
            "win_rate": m.win_rate, "profit_factor": m.profit_factor,
            "trade_count": m.trade_count,
        })
    pd.DataFrame(rows).to_csv(path, index=False)
    return rows


def generate_report(
    symbols: list[str],
    cfg,
    load_daily: Callable[[str], pd.DataFrame],
    out_dir: str | Path,
    do_walk_forward: bool = False,
    do_monte_carlo: bool = False,
    do_regime_split: bool = False,
    do_sweep: bool = False,
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_backtest(symbols, cfg, load_daily)
    metrics = compute_metrics(result.equity_curve, result.trades)

    _write_trades_csv(result.trades, out_dir / "trades.csv")
    if not result.equity_curve.empty:
        _write_equity_plot(result.equity_curve, out_dir / "equity.png")

    lines = ["# Backtest Raporu", "", f"Semboller: {', '.join(symbols)}",
             f"Başlangıç sermayesi: {cfg.backtest.initial_equity}", "",
             "## Özet Metrikler (tüm dönem)",
             f"- Toplam getiri: {metrics.total_return:.2%}",
             f"- CAGR: {metrics.cagr:.2%}",
             f"- Maks. drawdown: {metrics.max_drawdown:.2%}",
             f"- Sharpe: {metrics.sharpe:.2f}",
             f"- Win rate: {metrics.win_rate:.2%}",
             f"- Profit factor: {metrics.profit_factor:.2f}",
             f"- Ortalama R-multiple: {metrics.avg_r_multiple:.2f}",
             f"- Expectancy: {metrics.expectancy:.2f} TL/trade",
             f"- Trade sayısı: {metrics.trade_count}",
             f"- Nakitte kalma oranı: {metrics.time_in_cash_pct:.1f}%", ""]

    red_flags: list[str] = []
    if metrics.trade_count < 30:
        red_flags.append(f"Trade sayısı istatistiksel anlam için çok az ({metrics.trade_count} < 30).")

    if do_regime_split:
        lines.append("## Rejim Kırılımı")
        regimes_by_symbol = {s: classify_regime(build_features(load_daily(s), cfg), cfg) for s in symbols}
        breakdown = regime_breakdown(result.trades, regimes_by_symbol)
        lines.extend(_regime_breakdown_table(breakdown))
        lines.append("")

    wf_results = None
    if do_walk_forward:
        wf_results = run_walk_forward(symbols, cfg, load_daily)
        acceptance = evaluate_acceptance(wf_results)
        lines.append("## Walk-Forward")
        for r in wf_results:
            lines.append(
                f"- {r.train_start.date()}–{r.train_end.date()} (train) / "
                f"{r.test_start.date()}–{r.test_end.date()} (test): params={r.chosen_params}, "
                f"robust={r.robust}, test_trade_count={r.test_metrics.trade_count}, "
                f"test_pf={r.test_metrics.profit_factor:.2f}, "
                f"train_max_dd={r.train_metrics.max_drawdown:.2%}"
            )
        lines.append("")
        lines.append(f"Birleşik OOS profit factor: {acceptance.get('oos_profit_factor', 0):.2f}")
        lines.append(f"Birleşik OOS max DD: {acceptance.get('oos_max_drawdown', 0):.2%}")
        lines.append(f"Ortalama in-sample max DD: {acceptance.get('avg_in_sample_max_drawdown', 0):.2%}")
        lines.append(f"Kabul kriteri sonucu: {'GEÇTİ' if acceptance['passed'] else 'GEÇMEDİ'}")
        if metrics.max_drawdown != 0:
            oos_to_full_period_ratio = abs(acceptance.get("oos_max_drawdown", 0)) / abs(metrics.max_drawdown)
            lines.append(
                f"Bilgi (kabul kriterine dahil değil): Birleşik OOS max DD / "
                f"tam-dönem in-sample max DD oranı: {oos_to_full_period_ratio:.2f}×"
            )
        else:
            lines.append(
                "Bilgi (kabul kriterine dahil değil): tam-dönem in-sample max DD sıfır "
                "olduğundan oran hesaplanamadı."
            )
        lines.append("")
        if not acceptance["passed"]:
            red_flags.append("Walk-forward kabul kriteri geçmedi (Bölüm 12.5).")

    mc_result = None
    if do_monte_carlo:
        mc_result = run_monte_carlo(result.trades, cfg)
        lines.append("## Monte Carlo Drawdown Analizi")
        lines.append(f"- dd_p5: {mc_result['dd_p5']:.2%}")
        lines.append(f"- dd_median: {mc_result['dd_median']:.2%}")
        lines.append(f"- dd_p95: {mc_result['dd_p95']:.2%}")
        lines.append("")
        if abs(mc_result["dd_p95"]) >= cfg.risk.max_drawdown_breaker_pct:
            red_flags.append("Monte Carlo dd_p95, breaker eşiğine yakın/aşkın.")

    sweep_rows = None
    if do_sweep:
        sweep_rows = _write_sweep_csv(symbols, cfg, load_daily, out_dir / "sweep_results.csv")
        lines.append(f"## Parametre Taraması: {len(sweep_rows)} kombinasyon tamamlandı, sweep_results.csv'ye yazıldı.")
        lines.append("")

    lines.append("## Kırmızı Bayraklar")
    if red_flags:
        lines.extend(f"- [X] {rf}" for rf in red_flags)
    else:
        lines.append("- Otomatik kontrol edilen kırmızı bayrak yok (yine de BACKTEST_REVIEW.md'deki "
                     "tam kontrol listesini elle gözden geçir).")

    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    return {
        "metrics": metrics, "result": result, "wf_results": wf_results,
        "mc_result": mc_result, "sweep_rows": sweep_rows, "red_flags": red_flags,
        "report_path": out_dir / "report.md",
    }


def main() -> None:
    from core.config import load_config
    from data.historical import load_cached

    parser = argparse.ArgumentParser(description="Backtest CLI (Bölüm 12.8)")
    parser.add_argument("--symbols", required=True, help="virgülle ayrılmış AlgoLab sembolleri")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--monte-carlo", action="store_true")
    parser.add_argument("--regime-split", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--out", default="runtime/backtest_reports/")
    args = parser.parse_args()

    cfg = load_config(args.config)
    symbols = [s.strip() for s in args.symbols.split(",")]
    generate_report(
        symbols, cfg, lambda s: load_cached(s, "1d"), args.out,
        do_walk_forward=args.walk_forward, do_monte_carlo=args.monte_carlo,
        do_regime_split=args.regime_split, do_sweep=args.sweep,
    )
    print(f"Rapor yazıldı: {Path(args.out) / 'report.md'}")


if __name__ == "__main__":
    main()

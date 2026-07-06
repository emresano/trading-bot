# backtest/cli.py
from __future__ import annotations
import argparse
import hashlib
import itertools
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from backtest.engine import run_backtest
from backtest.metrics import (
    cash_only_metrics,
    classify_regime,
    compute_buy_hold_metrics,
    compute_metrics,
    regime_breakdown,
)
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


def _write_sweep_csv(symbols: list[str], cfg, load_daily, path: Path,
                     breaker_dir: Optional[Path] = None) -> list[dict]:
    """`breaker_dir`: verilirse (performans turu, v7) 27 kombinasyonun HER BİRİ
    kendi geçici dizinini açıp silmek yerine bu paylaşılan dizin içinde
    benzersiz bir dosya yolu alır (breaker durumu yine kombinasyonlar arasında
    İZOLE kalır). Verilmezse eski davranış (her çağrı kendi izole dizinini
    açar) korunur."""
    combos = sweep_combinations()
    breaker_counter = itertools.count()
    rows = []
    for combo in combos:
        combo_cfg = apply_params(cfg, combo)
        breaker_file = (breaker_dir / f"BREAKER_sweep_{next(breaker_counter)}") if breaker_dir is not None else None
        bt = run_backtest(symbols, combo_cfg, load_daily, breaker_file=breaker_file)
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
    do_benchmark: bool = False,
    benchmark_loader: Optional[Callable[[], pd.DataFrame]] = None,
    stamps: Optional[dict] = None,
    ghost_bars_removed: Optional[list[dict]] = None,
    disabled_gates: Optional[list[str]] = None,
    trace: Optional[list] = None,
) -> dict:
    """`disabled_gates`/`trace`: verilirse (read-only portföy-ablasyon turu —
    bkz. `tools/portfolio_ablation.py`), sırasıyla ana koşuma VE walk-forward'a
    (yalnızca disabled_gates) aynen iletilir. İkisi de verilmezse (None,
    varsayılan) davranış BİREBİR aynıdır — mevcut hiçbir çağıran etkilenmez."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Performans turu (v7): bu fonksiyonun tetiklediği TÜM run_backtest çağrıları
    # (ana koşum + walk-forward'ın pencere×27-kombinasyon çağrıları + sweep'in 27
    # çağrısı — v6'da ~6.5 saatlik koşumun büyük kısmı buradaki tempfile
    # oluştur/sil yükünden kaynaklanıyordu) TEK bir paylaşılan geçici dizini
    # paylaşır; her çağrı yine de İÇİNDE kendi benzersiz dosya yolunu alır, yani
    # breaker durumu çağrılar arasında hâlâ tam İZOLE kalır — yalnızca dizin
    # oluşturma/silme işlemi tek seferde yapılır.
    breaker_dir = Path(tempfile.mkdtemp(prefix="backtest_cli_breaker_"))

    result = run_backtest(symbols, cfg, load_daily, breaker_file=breaker_dir / "BREAKER_main",
                          disabled_gates=disabled_gates, trace=trace)
    metrics = compute_metrics(result.equity_curve, result.trades)

    _write_trades_csv(result.trades, out_dir / "trades.csv")
    if not result.equity_curve.empty:
        _write_equity_plot(result.equity_curve, out_dir / "equity.png")

    lines = ["# Backtest Raporu", "", f"Semboller: {', '.join(symbols)}",
             f"Başlangıç sermayesi: {cfg.backtest.initial_equity}", ""]
    if stamps:
        lines.append(f"Git commit: {stamps.get('git_commit', 'N/A')}")
        lines.append(f"Config hash (sha256): {stamps.get('config_hash', 'N/A')}")
        lines.append(f"Snapshot manifest hash (sha256): {stamps.get('snapshot_manifest_hash', 'N/A (snapshot kullanılmadı)')}")
        lines.append("")
    if ghost_bars_removed is not None:
        if ghost_bars_removed:
            pd.DataFrame(ghost_bars_removed).to_csv(out_dir / "ghost_bars_removed.csv", index=False)
        lines.append(
            f"Veri temizleme (data/cleaning.py): {len(ghost_bars_removed)} hayalet bar elendi "
            f"(detay: ghost_bars_removed.csv). Tarihler Istanbul takvim gününe normalize edildi."
        )
        lines.append("")
    lines += [
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
        wf_results = run_walk_forward(symbols, cfg, load_daily, breaker_dir=breaker_dir,
                                      disabled_gates=disabled_gates)
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
        lines.append(f"- dd_p5 (en kötü %5 senaryo / worst-5%): {mc_result['dd_p5']:.2%}")
        lines.append(f"- dd_median: {mc_result['dd_median']:.2%}")
        lines.append(f"- dd_p95 (en iyi %5 senaryo): {mc_result['dd_p95']:.2%}")
        lines.append("")
        # Kontrol dd_p5 (en kötü %5 senaryo / worst-5%) üzerinden yapılır — dd_p95
        # değil, çünkü dd_p95 permütasyonların en HAFİF ucu, tail-risk sorusuyla
        # ("en kötü ne olur") ilgisizdir (bkz. BACKTEST_REVIEW_v5.md bulgusu).
        if abs(mc_result["dd_p5"]) >= cfg.risk.max_drawdown_breaker_pct:
            red_flags.append("Monte Carlo worst-5% (dd_p5), breaker eşiğine yakın/aşkın.")

    sweep_rows = None
    if do_sweep:
        sweep_rows = _write_sweep_csv(symbols, cfg, load_daily, out_dir / "sweep_results.csv",
                                      breaker_dir=breaker_dir)
        lines.append(f"## Parametre Taraması: {len(sweep_rows)} kombinasyon tamamlandı, sweep_results.csv'ye yazıldı.")
        lines.append("")

    benchmark_metrics = None
    if do_benchmark and benchmark_loader is not None and not result.equity_curve.empty:
        bench_df = benchmark_loader()
        bench_df = bench_df.loc[result.equity_curve.index[0]: result.equity_curve.index[-1]]
        benchmark_metrics = compute_buy_hold_metrics(bench_df, cfg.backtest.initial_equity)
        cash_metrics = cash_only_metrics()
        lines.append("## Benchmark Kıyası (bilgilendirici, kabul kriterine dahil değil)")
        lines.append("| | Strateji | Endeks Al-Tut | Sadece Nakit |")
        lines.append("|---|---|---|---|")
        lines.append(f"| Toplam getiri | {metrics.total_return:.2%} | {benchmark_metrics.total_return:.2%} | {cash_metrics.total_return:.2%} |")
        lines.append(f"| CAGR | {metrics.cagr:.2%} | {benchmark_metrics.cagr:.2%} | {cash_metrics.cagr:.2%} |")
        lines.append(f"| Maks. drawdown | {metrics.max_drawdown:.2%} | {benchmark_metrics.max_drawdown:.2%} | {cash_metrics.max_drawdown:.2%} |")
        lines.append(f"| Sharpe | {metrics.sharpe:.2f} | {benchmark_metrics.sharpe:.2f} | {cash_metrics.sharpe:.2f} |")
        lines.append("")

    lines.append("## Kırmızı Bayraklar")
    if red_flags:
        lines.extend(f"- [X] {rf}" for rf in red_flags)
    else:
        lines.append("- Otomatik kontrol edilen kırmızı bayrak yok (yine de BACKTEST_REVIEW.md'deki "
                     "tam kontrol listesini elle gözden geçir).")

    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    shutil.rmtree(breaker_dir, ignore_errors=True)

    return {
        "metrics": metrics, "result": result, "wf_results": wf_results,
        "mc_result": mc_result, "sweep_rows": sweep_rows, "red_flags": red_flags,
        "benchmark_metrics": benchmark_metrics, "report_path": out_dir / "report.md",
    }


def _compute_stamps(config_path: str, snapshot_dir: Optional[str]) -> dict:
    """Rapor başlığı için üç damga: git commit + config dosyası hash'i +
    snapshot manifest hash'i (HARDENING.md A1). Tekrarlanabilirlik kanıtı içindir,
    hiçbir davranışı etkilemez."""
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent.parent, text=True,
        ).strip()
    except Exception:
        git_commit = "N/A (git bulunamadı)"

    try:
        config_hash = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
    except Exception:
        config_hash = "N/A"

    if snapshot_dir:
        manifest_path = Path(snapshot_dir) / "manifest.json"
        if manifest_path.exists():
            snapshot_manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        else:
            snapshot_manifest_hash = "N/A (manifest.json bulunamadı)"
    else:
        snapshot_manifest_hash = "N/A (snapshot kullanılmadı)"

    return {
        "git_commit": git_commit,
        "config_hash": config_hash,
        "snapshot_manifest_hash": snapshot_manifest_hash,
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
    parser.add_argument("--start-date", default=None,
                        help="YYYY-MM-DD — verilirse yüklenen veri bu tarihten itibaren kırpılır "
                             "(örn. eski/güvenilmez tarihçeyi dışlamak için)")
    parser.add_argument("--benchmark", action="store_true",
                        help="XU100 al-tut ve sadece-nakit karşılaştırma bölümünü rapora ekler "
                             "(bilgilendirici, kabul kriterine dahil değil)")
    parser.add_argument("--benchmark-symbol", default="XU100",
                        help="Benchmark endeksinin AlgoLab-tarzı kısa adı (cache dosya adı için)")
    parser.add_argument("--benchmark-yf-symbol", default="XU100.IS",
                        help="Benchmark endeksinin yfinance sembolü")
    parser.add_argument("--snapshot", default=None,
                        help="Dondurulmuş bir snapshot dizini (örn. data/snapshots/2026-07-06) — "
                             "verilirse ağdan indirme YOK, yalnızca <SEMBOL>.parquet dosyaları okunur. "
                             "Verilmezse mevcut davranış (data/historical cache) aynen korunur.")
    parser.add_argument("--no-clean", action="store_true",
                        help="data/cleaning.py'nin hayalet-bar filtresi + tarih normalizasyonunu "
                             "ATLA (yalnızca eski v1-v6 davranışıyla karşılaştırma/hata ayıklama "
                             "amaçlı — v7+ varsayılanı temizlemedir).")
    args = parser.parse_args()

    cfg = load_config(args.config)
    symbols = [s.strip() for s in args.symbols.split(",")]

    if args.snapshot:
        snapshot_dir = Path(args.snapshot)

        def _load_daily_raw(s: str):
            df = pd.read_parquet(snapshot_dir / f"{s}.parquet")
            return df.loc[args.start_date:] if args.start_date else df
    else:
        def _load_daily_raw(s: str):
            df = load_cached(s, "1d")
            return df.loc[args.start_date:] if args.start_date else df

    ghost_bars_removed: list[dict] = []
    if args.no_clean:
        def _load_daily(s: str):
            return _load_daily_raw(s)
    else:
        # Veri temizleme katmanı (v7 harness düzeltme turu, DIAGNOSTICS_v6.md Paket 1):
        # kaynak parquet dosyalarına DOKUNMAZ, yalnızca bellek-içi kopyayı düzeltir.
        # Tüm evren AYNI ANDA temizlenir (hayalet-bar tespiti çapraz-sembol bilgisi
        # gerektirir), sonra her sembol için sabit bir sözlükten okunur.
        from data.cleaning import load_and_clean_universe

        cleaned, ghost_bars_removed = load_and_clean_universe(symbols, _load_daily_raw)

        def _load_daily(s: str):
            return cleaned[s]

    benchmark_loader = None
    if args.benchmark:
        from data.historical import update_cache

        update_cache(args.benchmark_symbol, args.benchmark_yf_symbol, "1d")

        def benchmark_loader():
            df = load_cached(args.benchmark_symbol, "1d")
            return df.loc[args.start_date:] if args.start_date else df

    stamps = _compute_stamps(args.config, args.snapshot)

    generate_report(
        symbols, cfg, _load_daily, args.out,
        do_walk_forward=args.walk_forward, do_monte_carlo=args.monte_carlo,
        do_regime_split=args.regime_split, do_sweep=args.sweep,
        do_benchmark=args.benchmark, benchmark_loader=benchmark_loader,
        stamps=stamps, ghost_bars_removed=ghost_bars_removed,
    )
    print(f"Rapor yazıldı: {Path(args.out) / 'report.md'}")


if __name__ == "__main__":
    main()

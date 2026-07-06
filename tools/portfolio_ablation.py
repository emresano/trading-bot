# tools/portfolio_ablation.py
"""Portföy-seviyesi gate ablasyon turu (read-only counterfactual).

DIAGNOSTICS_v6.md Paket 3, huninin 6 aktif gate'inden üçünün (trend, regime,
rsi) İZOLE sinyal-kalite ölçümünde değer katmadığını buldu — ama o ölçüm
portföy etkilerini (nakit/korelasyon/max_open_positions/breaker) YOK
SAYIYORDU. Bu araç AYNI üç gate'i GERÇEK portföy motoruyla (backtest/engine.py,
tüm kısıtlarıyla) devre dışı bırakarak izole bulgunun portföy seviyesinde de
geçerli olup olmadığını test eder.

Hiçbir eşik/gate/parametre config.yaml'da DEĞİŞTİRİLMEZ — `disabled_gates`
yalnızca bu ARACIN geçtiği, run_backtest'in read-only bir parametresidir
(main.py/PaperBroker bunu hiç kullanmaz). Mevcut snapshot'lara YAZILMAZ.
v7 taban çizgisi (runtime/backtest_reports_v7/) OKUNUR ama DEĞİŞTİRİLMEZ.

Kullanım: python -m tools.portfolio_ablation
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

from backtest.cli import _compute_stamps, generate_report
from backtest.walkforward import evaluate_acceptance
from core.config import load_config
from data.cleaning import load_and_clean_universe
from tools.data_audit_v2 import classify_jump, download_raw, find_jumps

SYMBOLS = ["THYAO", "GARAN", "ASELS", "AKBNK", "KCHOL", "SAHOL",
          "EREGL", "TUPRS", "TCELL", "TOASO", "SISE", "ARCLK"]

SNAPSHOT_DIR = Path("data/snapshots/2026-07-06")
START_DATE = "2005-01-01"
USDTRY_PATH = Path("data/snapshots/aux/2026-07-06/USDTRY.parquet")
OUT_ROOT = Path("runtime/ablation_portfolio")

VARIANTS: dict[str, list[str]] = {
    "baseline": [],
    "no_trend": ["trend"],
    "no_regime": ["regime"],
    "no_rsi": ["rsi"],
    "no_trend_regime_rsi": ["trend", "regime", "rsi"],
}

SUSPICIOUS_CLASSIFICATION = "açıklanamayan gap (muhtemel bedelli)"
GAP_WINDOW_BARS = 5


def load_cleaned_universe() -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """v7 ile BİREBİR aynı yükleme sırası: önce START_DATE'e kırp, sonra
    data/cleaning.py (hayalet-bar filtresi + tarih normalizasyonu) uygula."""
    def _load_daily_raw(s: str) -> pd.DataFrame:
        df = pd.read_parquet(SNAPSHOT_DIR / f"{s}.parquet")
        return df.loc[START_DATE:]

    return load_and_clean_universe(SYMBOLS, _load_daily_raw)


def compute_suspicious_days(cleaned: dict[str, pd.DataFrame]) -> list[tuple[str, pd.Timestamp]]:
    """DATA_AUDIT_v2.md'nin ürettiği sınıflandırmayı YENİDEN üretir (aynı
    fonksiyonlar, aynı eşik) — yalnızca 'açıklanamayan gap' sınıfına giren
    günleri döner. Ham veri zaten `runtime/diagnostics_v2_raw/`de önbelleğe
    alınmış (ağ çağrısı yapılmaz)."""
    cfg = load_config()
    yf_map = {i.symbol: i.yf_symbol for i in cfg.instruments}

    suspicious: list[tuple[str, pd.Timestamp]] = []
    for symbol, df in cleaned.items():
        yf_symbol = yf_map.get(symbol, f"{symbol}.IS")
        raw_raw = download_raw(symbol, yf_symbol)
        raw_tz_aware = raw_raw.tz_localize("Europe/Istanbul") if raw_raw.index.tz is None else raw_raw
        from data.cleaning import normalize_bist_dates
        raw_normalized = normalize_bist_dates(raw_tz_aware)

        jumps = find_jumps(df)
        for _, j in jumps.iterrows():
            classification = classify_jump(j["date"], raw_normalized, j["vol_ratio_20d"])
            if classification == SUSPICIOUS_CLASSIFICATION:
                suspicious.append((symbol, j["date"]))
    return suspicious


def compute_gap_proximity(trades_df: pd.DataFrame, suspicious_days: list[tuple[str, pd.Timestamp]],
                          cleaned: dict[str, pd.DataFrame], window: int = GAP_WINDOW_BARS) -> dict:
    """`trades_df`in kaç tanesinin giriş/çıkışı, KENDİ sembolündeki herhangi
    bir şüpheli günün ±window bar mesafesinde? (temiz veriyle üretilen yeni
    trade'lerin tarihleri zaten Istanbul-normalize edilmiş olduğundan, ek bir
    tarih dönüşümüne gerek yok.)"""
    if trades_df.empty:
        return {"total_trades": 0, "trades_near_suspicious_day": 0, "pct": 0.0}

    by_symbol: dict[str, list[pd.Timestamp]] = {}
    for sym, date in suspicious_days:
        by_symbol.setdefault(sym, []).append(date)

    near_count = 0
    for _, t in trades_df.iterrows():
        sym = t["symbol"]
        df = cleaned.get(sym)
        susp_dates = by_symbol.get(sym)
        if df is None or not susp_dates:
            continue
        is_near = False
        for susp_date in susp_dates:
            if susp_date not in df.index:
                continue
            susp_pos = df.index.get_loc(susp_date)
            for col in ("entry_date", "exit_date"):
                d = pd.Timestamp(t[col])
                if d in df.index:
                    trade_pos = df.index.get_loc(d)
                    if abs(trade_pos - susp_pos) <= window:
                        is_near = True
                        break
            if is_near:
                break
        if is_near:
            near_count += 1

    total = len(trades_df)
    return {
        "total_trades": total, "trades_near_suspicious_day": near_count,
        "pct": 100.0 * near_count / total if total else 0.0,
    }


def compute_time_in_market_and_capital_utilization(trace: list) -> dict:
    """`trace` (run_backtest'in salt-okunur teşhis kancası) üzerinden:
    - time_in_market_pct: en az 1 açık pozisyon olan gün / toplam gün (%)
    - avg_capital_utilization_pct: günlük toplam notional/equity ortalaması (%)
    """
    if not trace:
        return {"time_in_market_pct": 0.0, "avg_capital_utilization_pct": 0.0}

    days_with_position = 0
    utilization_ratios: list[float] = []
    for day in trace:
        positions = day["positions"]
        if positions:
            days_with_position += 1
        total_notional = sum(p["notional"] for p in positions.values() if p["notional"] is not None)
        equity = day["equity"]
        utilization_ratios.append(total_notional / equity if equity else 0.0)

    return {
        "time_in_market_pct": 100.0 * days_with_position / len(trace),
        "avg_capital_utilization_pct": 100.0 * (sum(utilization_ratios) / len(utilization_ratios)),
    }


def convert_equity_to_usd(equity_curve: pd.Series, usdtry: pd.Series) -> pd.Series:
    """Bilgilendirici USD çevrimi — HİÇBİR karar/sinyal/risk hesabına girmez,
    yalnızca raporlama (HARDENING C2'nin kullanıcı onaylı kısmi aktivasyonu)."""
    if equity_curve.empty:
        return equity_curve
    aligned = usdtry.reindex(equity_curve.index, method="ffill").bfill()
    return equity_curve / aligned


def run_variant(name: str, disabled_gates: list[str], cleaned: dict[str, pd.DataFrame],
                cfg, stamps: dict, usdtry: pd.Series, suspicious_days: list[tuple[str, pd.Timestamp]],
                ghost_bars_removed: list[dict]) -> dict:
    out_dir = OUT_ROOT / name
    trace: list = []

    def benchmark_loader():
        from data.historical import load_cached
        return load_cached("XU100", "1d").loc[START_DATE:]

    out = generate_report(
        SYMBOLS, cfg, lambda s: cleaned[s], out_dir,
        do_walk_forward=True, do_monte_carlo=True, do_regime_split=True,
        do_sweep=False, do_benchmark=True, benchmark_loader=benchmark_loader,
        stamps=stamps, ghost_bars_removed=ghost_bars_removed,
        disabled_gates=disabled_gates or None, trace=trace,
    )

    metrics = out["metrics"]
    result = out["result"]
    wf_results = out["wf_results"]
    acceptance = evaluate_acceptance(wf_results) if wf_results else {"passed": False}
    mc = out["mc_result"] or {}
    bench = out["benchmark_metrics"]

    trades_df = pd.DataFrame([
        {"symbol": t.symbol, "entry_date": t.entry_date, "exit_date": t.exit_date, "pnl": t.pnl}
        for t in result.trades
    ])

    usd_equity = convert_equity_to_usd(result.equity_curve, usdtry)
    from backtest.metrics import compute_metrics
    usd_metrics = compute_metrics(usd_equity, result.trades) if not usd_equity.empty else None

    tim = compute_time_in_market_and_capital_utilization(trace)
    gap = compute_gap_proximity(trades_df, suspicious_days, cleaned)

    return {
        "variant": name, "disabled_gates": disabled_gates,
        "trade_count": metrics.trade_count,
        "total_return_try_pct": metrics.total_return * 100,
        "total_return_usd_pct": (usd_metrics.total_return * 100) if usd_metrics else None,
        "cagr_usd_pct": (usd_metrics.cagr * 100) if usd_metrics else None,
        "profit_factor": metrics.profit_factor,
        "win_rate_pct": metrics.win_rate * 100,
        "max_drawdown_pct": metrics.max_drawdown * 100,
        "sharpe": metrics.sharpe,
        "benchmark_sharpe": bench.sharpe if bench else None,
        "benchmark_max_drawdown_pct": (bench.max_drawdown * 100) if bench else None,
        "dd_over_index_dd_ratio": (
            abs(metrics.max_drawdown / bench.max_drawdown) if bench and bench.max_drawdown else None
        ),
        "oos_profit_factor": acceptance.get("oos_profit_factor"),
        "oos_max_drawdown_pct": (acceptance.get("oos_max_drawdown", 0) * 100) if acceptance.get("oos_max_drawdown") is not None else None,
        "wf_acceptance_passed": acceptance.get("passed", False),
        "mc_dd_p5_pct": (mc.get("dd_p5", 0) * 100) if mc else None,
        "time_in_market_pct": tim["time_in_market_pct"],
        "avg_capital_utilization_pct": tim["avg_capital_utilization_pct"],
        "breaker_trip_count": len(result.breaker_trips),
        "gap_proximity": gap,
        "out_dir": str(out_dir),
    }


def main() -> None:
    cfg = load_config()
    cleaned, ghost_bars_removed = load_cleaned_universe()
    stamps = _compute_stamps("config/config.yaml", str(SNAPSHOT_DIR))

    usdtry_df = pd.read_parquet(USDTRY_PATH)
    usdtry = usdtry_df["close"]

    print("Şüpheli-gün listesi hesaplanıyor (DATA_AUDIT_v2.md sınıflandırmasının tekrarı)...")
    suspicious_days = compute_suspicious_days(cleaned)
    print(f"{len(suspicious_days)} açıklanamayan-gap günü bulundu.")

    summaries = []
    for name, gates in VARIANTS.items():
        print(f"\n=== Varyant: {name} (disabled_gates={gates}) ===")
        summary = run_variant(name, gates, cleaned, cfg, stamps, usdtry, suspicious_days, ghost_bars_removed)
        summaries.append(summary)
        print(json.dumps({k: v for k, v in summary.items() if k != "gap_proximity"}, indent=2, default=str))

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "summary.json").write_text(json.dumps(summaries, indent=2, default=str), encoding="utf-8")
    print(f"\nÖzet yazıldı: {OUT_ROOT / 'summary.json'}")


if __name__ == "__main__":
    main()

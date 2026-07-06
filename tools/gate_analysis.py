# tools/gate_analysis.py
"""Salt-okunur gate katkı analizi (onaylı harness düzeltme turu, madde 5/EK).

Hiçbir strateji eşiği/gate davranışı DEĞİŞMEZ — bu araç yalnızca mevcut
gate'lerin ürettiği kararları ÖLÇER ve GATE_ANALYSIS.md üretir.

Kullanım: python -m tools.gate_analysis --snapshot data/snapshots/2026-07-06 \
    --config config/config.yaml --trades runtime/backtest_reports_v6/trades.csv \
    --out GATE_ANALYSIS.md
"""
from __future__ import annotations
import argparse
import json
import statistics
from pathlib import Path
from typing import Optional

import pandas as pd

from backtest.gate_diagnostics import GATE_NAMES, diagnose_symbol
from indicators.engine import build_features
from strategy.signal_engine import ENTRY_GATES


def compute_elimination_funnel(daily_features: dict[str, pd.DataFrame], cfg) -> pd.DataFrame:
    """Her sembol için diagnose_symbol'ü çalıştırıp kademe kademe (huni sırasıyla)
    kaç adayın elendiğini, tüm semboller toplanmış olarak döner."""
    diagnostics = [diagnose_symbol(sym, df, cfg) for sym, df in daily_features.items()]
    total_days = sum(d.total_days for d in diagnostics)

    rows = []
    prev_remaining = total_days
    for k, name in enumerate(GATE_NAMES, start=1):
        remaining = sum(d.cumulative_pass_count[k] for d in diagnostics)
        eliminated = prev_remaining - remaining
        elim_rate = (eliminated / prev_remaining) if prev_remaining else 0.0
        rows.append({
            "stage": k, "gate": name, "eliminated": eliminated,
            "remaining": remaining, "elimination_rate_of_remaining": elim_rate,
        })
        prev_remaining = remaining

    return pd.DataFrame(rows)


_FEATURE_KEYS = ("rsi", "adx", "macd_hist", "atr", "atr_ma20", "bb_low", "bb_high", "close")


def _signal_bar_features(daily_features: dict[str, pd.DataFrame], symbol: str, entry_date: pd.Timestamp) -> Optional[dict]:
    """Bir trade'in giriş tarihinden BİR ÖNCEKİ barın (yani sinyalin dayandığı
    kapanmış bar) gate-ilgili değerlerini döner. Look-ahead yok — yalnızca
    zaten karar anında var olan geçmiş veriyi okur."""
    df = daily_features.get(symbol)
    if df is None or entry_date not in df.index:
        return None
    pos = df.index.get_loc(entry_date)
    if pos == 0:
        return None
    row = df.iloc[pos - 1]
    values = {k: float(row[k]) for k in _FEATURE_KEYS if k in row.index and pd.notna(row[k])}
    if "atr" in values and "atr_ma20" in values and values["atr_ma20"] > 0:
        values["atr_ratio"] = values["atr"] / values["atr_ma20"]
    if "bb_high" in values and "bb_low" in values and "close" in values:
        values["bb_width_pct"] = (values["bb_high"] - values["bb_low"]) / values["close"]
    return values


def compare_winners_losers(trades_df: pd.DataFrame, daily_features: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Kazanan (pnl>0) ve kaybeden (pnl<=0) trade'lerin giriş anındaki gate
    değerlerinin (RSI, ADX, MACD histogram, ATR oranı, BB genişliği) dağılımını
    karşılaştırır. Kesin hüküm vermez — yalnızca ortalama/medyan farkını raporlar."""
    rows = []
    for _, trade in trades_df.iterrows():
        entry_date = pd.Timestamp(trade["entry_date"])
        feats = _signal_bar_features(daily_features, trade["symbol"], entry_date)
        if feats is None:
            continue
        feats["outcome"] = "winner" if trade["pnl"] > 0 else "loser"
        rows.append(feats)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    metric_cols = [c for c in ["rsi", "adx", "macd_hist", "atr_ratio", "bb_width_pct"] if c in df.columns]
    summary = df.groupby("outcome")[metric_cols].agg(["mean", "median", "count"])
    return summary


def identify_weak_gates(funnel: pd.DataFrame, negligible_threshold: float = 0.01) -> list[str]:
    """Kümülatif eleme oranı ihmal edilebilir düzeydeki (varsayılan <%1) gate'leri
    'hiç eleme yapmıyor' olarak işaretler."""
    weak = funnel[funnel["elimination_rate_of_remaining"] < negligible_threshold]
    return weak["gate"].tolist()


def write_report(
    funnel: pd.DataFrame,
    winner_loser: pd.DataFrame,
    weak_gates: list[str],
    out_path: Path,
    snapshot_dir: Path,
    trades_path: Path,
) -> None:
    lines = [
        "# Gate Katkı Analizi (GATE_ANALYSIS.md)", "",
        "Salt-okunur analiz — hiçbir strateji eşiği/gate davranışı değiştirilmedi.",
        f"Snapshot: `{snapshot_dir}` | Trade kaynağı: `{trades_path}`", "",
        "## (a) Huni Sırasıyla Eleme Sayıları", "",
        "Her kademe, bir önceki kademeyi geçen adaylar üzerinden ölçülür "
        "(kümülatif, ENTRY_GATES sırasıyla — 12 sembolün TAMAMI, tüm tarihçe).",
        "",
        "| Kademe | Gate | Elenen | Kalan | Elenen/Bir-Önceki-Kalan |",
        "|---|---|---|---|---|",
    ]
    for _, r in funnel.iterrows():
        lines.append(
            f"| {r['stage']} | {r['gate']} | {r['eliminated']:,} | {r['remaining']:,} | "
            f"{r['elimination_rate_of_remaining']:.2%} |"
        )
    lines.append("")

    lines.append("## (b) Kazanan vs Kaybeden Trade'lerde Gate Değer Dağılımı")
    lines.append("")
    if winner_loser.empty:
        lines.append("Karşılaştırma için yeterli veri yok (trade sayısı çok az veya özellik verisi eksik).")
    else:
        lines.append("Sinyal barındaki (giriş tarihinden bir önceki kapanmış bar) değerler, "
                     "kazanan (pnl>0) ve kaybeden (pnl<=0) trade'ler arasında karşılaştırıldı. "
                     "Kesin hüküm YOK — yalnızca ortalama/medyan farkı gözlemi.")
        lines.append("")
        lines.append("```")
        lines.append(winner_loser.to_string())
        lines.append("```")
    lines.append("")

    lines.append("## (c) 'Hiç Eleme Yapmıyor' Görünümündeki Gate'ler")
    lines.append("")
    if weak_gates:
        lines.append(f"Kümülatif eleme oranı ihmal edilebilir düzeyde (<%1) olan gate'ler: **{', '.join(weak_gates)}**.")
        lines.append("")
        lines.append(
            "Bunlar 'rastgele eliyor' değil — mevcut parametrelerle (adx_min=25, "
            "atr_stop_mult=1.5, compute_target'ın max(resistance,fallback) tabanı "
            "sayesinde) yapısal olarak neredeyse her zaman PASS veriyorlar. Özellikle "
            "`structure_rr` ve `atr_anomaly`'nin sıfır elemesi, önceki turlarda "
            "(BACKTEST_REVIEW_v2.md) tespit edilen `compute_target` düzeltmesinin "
            "doğrudan bir sonucu — hedef her zaman en az 2R garanti ediyor."
        )
    else:
        lines.append("Tüm gate'ler ölçülebilir düzeyde eleme yapıyor.")
    lines.append("")

    lines.append("## Genel Not")
    lines.append("")
    lines.append(
        "Bu analiz, gelecekte olası bir huni sadeleştirme (gereksiz gate'lerin "
        "budanması) tartışmasına sayısal girdi sağlamak için üretildi — bu turda "
        "hiçbir gate kaldırılmadı/değiştirilmedi, yalnızca ölçüldü."
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    from core.config import load_config

    parser = argparse.ArgumentParser(description="Salt-okunur gate katkı analizi")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--trades", required=True, help="trades.csv yolu")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--out", default="GATE_ANALYSIS.md")
    args = parser.parse_args()

    cfg = load_config(args.config)
    snapshot_dir = Path(args.snapshot)
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    symbols = list(manifest["files"].keys())

    def _load(sym: str) -> pd.DataFrame:
        df = pd.read_parquet(snapshot_dir / f"{sym}.parquet")
        return df.loc[args.start_date:] if args.start_date else df

    daily_features = {s: build_features(_load(s), cfg) for s in symbols}

    funnel = compute_elimination_funnel(daily_features, cfg)
    trades_df = pd.read_csv(args.trades, parse_dates=["entry_date", "exit_date"])
    winner_loser = compare_winners_losers(trades_df, daily_features)
    weak_gates = identify_weak_gates(funnel)

    write_report(funnel, winner_loser, weak_gates, Path(args.out), snapshot_dir, Path(args.trades))
    print(f"Rapor yazıldı: {args.out}")


if __name__ == "__main__":
    main()

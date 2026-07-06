# tools/data_audit_v2.py
"""Salt-okunur genişletilmiş veri denetimi (v7 motor+veri turu, madde 4).

DIAGNOSTICS_v6.md Paket 2'nin devamı: sıçrama eşiği %25'ten %10'a indirilerek
12 sembolün TAMAMI taranır. Her %10+ gün, ham (auto_adjust=False) verinin
Dividends/Stock Splits kolonlarıyla çapraz kontrol edilip 3 sınıftan birine
atanır: "kayıtlı kurumsal işlem" / "açıklanamayan gap (muhtemel bedelli)" /
"hacim destekli gerçek hareket". Sembol başına açıklanamayan-gap sayısı ve bu
günlere ±5 bar mesafede v6 trade'i olup olmadığı raporlanır.

Hiçbir veri DEĞİŞTİRİLMEZ. Snapshot parquet dosyalarına dokunulmaz. Ham veri
snapshot'tan AYRI bir klasöre (varsayılan: runtime/diagnostics_v2_raw/) iner.

Bağlam: KCHOL 2007-06-08'in Koç Holding IR sayfasında kayıtlı bir sermaye
artırımı (bedelli) olduğu dışarıdan doğrulandı — yfinance bedelli artırımları
İZLEMİYOR (Dividends/Stock Splits kolonlarında görünmüyor). Bu tarama, o kör
noktanın 12 sembollük evrende ne kadar yaygın olduğunu ölçer.

Kullanım: python -m tools.data_audit_v2 --snapshot data/snapshots/2026-07-06 \
    --trades runtime/backtest_reports_v6/trades.csv --out DATA_AUDIT_v2.md
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import pandas as pd
import yfinance as yf

from data.cleaning import normalize_bist_dates

JUMP_THRESHOLD_V2 = 0.10
VOLUME_SUPPORT_RATIO = 1.5
TRADE_PROXIMITY_BARS = 5
RAW_CACHE_DIR = Path("runtime/diagnostics_v2_raw")


def load_snapshot(snapshot_dir: Path) -> dict[str, pd.DataFrame]:
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    symbols = list(manifest["files"].keys())
    return {s: pd.read_parquet(snapshot_dir / f"{s}.parquet") for s in symbols}


def download_raw(symbol: str, yf_symbol: str, cache_dir: Path = RAW_CACHE_DIR) -> pd.DataFrame:
    """auto_adjust=False HAM veriyi indirir (Dividends/Stock Splits kolonları
    dahil), snapshot'tan AYRI bir klasöre kaydeder — snapshot'a dokunulmaz.
    Zaten indirilmişse cache'ten okur (tekrar ağ çağrısı yapmaz)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{symbol}_raw.parquet"
    if path.exists():
        return pd.read_parquet(path)
    df = yf.Ticker(yf_symbol).history(interval="1d", period="max", auto_adjust=False)
    df.to_parquet(path)
    return df


def _to_istanbul_midnight_utc(ts: pd.Timestamp) -> pd.Timestamp:
    """`data/cleaning.normalize_bist_dates` ile AYNI etiketleme kuralı: gerçek
    Istanbul takvim gününü UTC gece yarısı olarak temsil et — böylece farklı
    kaynaklardan (snapshot, ham indirme, v6 trades.csv) gelen tarihler aynı
    ölçekte karşılaştırılabilir."""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    ist_date = ts.tz_convert("Europe/Istanbul").normalize().tz_localize(None)
    return pd.Timestamp(ist_date).tz_localize("UTC")


def find_jumps(df: pd.DataFrame, threshold: float = JUMP_THRESHOLD_V2) -> pd.DataFrame:
    """|günlük getiri| >= threshold olan günleri, 20-bar hacim oranıyla birlikte listeler."""
    returns = df["close"].pct_change()
    jumps = returns[returns.abs() >= threshold]
    if jumps.empty:
        return pd.DataFrame(columns=["date", "return", "volume", "vol_ratio_20d"])

    vol_avg20 = df["volume"].rolling(20).mean()
    rows = []
    for date, ret in jumps.items():
        vol = float(df.loc[date, "volume"])
        avg_vol = vol_avg20.loc[date]
        vol_ratio = float(vol / avg_vol) if pd.notna(avg_vol) and avg_vol > 0 else None
        rows.append({"date": date, "return": float(ret), "volume": vol, "vol_ratio_20d": vol_ratio})
    return pd.DataFrame(rows)


def classify_jump(jump_date_ist: pd.Timestamp, raw_normalized: pd.DataFrame, vol_ratio) -> str:
    """3 sınıf: kayıtlı kurumsal işlem / hacim destekli gerçek hareket /
    açıklanamayan gap (muhtemel bedelli). Kurumsal-işlem kontrolü, tarih
    normalizasyonundaki olası ±1 günlük belirsizliğe karşı jump_date_ist'in
    kendisi VE komşu 1 günü de tarar."""
    candidates = [jump_date_ist, jump_date_ist - pd.Timedelta(days=1), jump_date_ist + pd.Timedelta(days=1)]
    has_corp_action = False
    for c in candidates:
        if c in raw_normalized.index:
            row = raw_normalized.loc[c]
            div = float(row.get("Dividends", 0.0) or 0.0)
            splits = float(row.get("Stock Splits", 0.0) or 0.0)
            if div != 0.0 or splits != 0.0:
                has_corp_action = True
                break
    if has_corp_action:
        return "kayıtlı kurumsal işlem"
    if vol_ratio is not None and vol_ratio >= VOLUME_SUPPORT_RATIO:
        return "hacim destekli gerçek hareket"
    return "açıklanamayan gap (muhtemel bedelli)"


def trade_within_bars(symbol: str, jump_date_ist: pd.Timestamp, normalized_df: pd.DataFrame,
                      trades: pd.DataFrame, window: int = TRADE_PROXIMITY_BARS) -> bool:
    """Bu sembole ait herhangi bir v6 trade'inin giriş/çıkış barı, jump_date_ist'in
    normalized_df'teki bar POZİSYONUNA ±window bar mesafede mi?"""
    sym_trades = trades[trades["symbol"] == symbol]
    if sym_trades.empty or jump_date_ist not in normalized_df.index:
        return False
    jump_pos = normalized_df.index.get_loc(jump_date_ist)

    for _, t in sym_trades.iterrows():
        for col in ("entry_date", "exit_date"):
            d_ist = _to_istanbul_midnight_utc(pd.Timestamp(t[col]))
            if d_ist in normalized_df.index:
                trade_pos = normalized_df.index.get_loc(d_ist)
                if abs(trade_pos - jump_pos) <= window:
                    return True
    return False


def audit_symbol(symbol: str, yf_symbol: str, normalized_df: pd.DataFrame,
                 trades: pd.DataFrame, raw_cache_dir: Path = RAW_CACHE_DIR) -> dict:
    jumps = find_jumps(normalized_df)
    raw_raw = download_raw(symbol, yf_symbol, raw_cache_dir)
    # yfinance normalde tz-aware (Europe/Istanbul) döner; naive dönerse zaten
    # borsa yerel saati olduğu varsayılır (data/historical.py'nin varsayımıyla
    # tutarlı). normalize_bist_dates herhangi bir tz-aware index'i kabul eder.
    raw_tz_aware = raw_raw.tz_localize("Europe/Istanbul") if raw_raw.index.tz is None else raw_raw
    raw_normalized = normalize_bist_dates(raw_tz_aware)

    rows = []
    for _, j in jumps.iterrows():
        jump_date_ist = j["date"]  # normalized_df zaten Istanbul-normalize edilmiş
        classification = classify_jump(jump_date_ist, raw_normalized, j["vol_ratio_20d"])
        near_trade = trade_within_bars(symbol, jump_date_ist, normalized_df, trades)
        rows.append({
            "symbol": symbol, "date": jump_date_ist, "return": j["return"],
            "vol_ratio_20d": j["vol_ratio_20d"], "classification": classification,
            "trade_within_5_bars": near_trade,
        })
    return {"symbol": symbol, "jumps": pd.DataFrame(rows)}


def algolab_source_assessment() -> list[str]:
    """Madde 5 (read-only keşif): AlgoLab'ın tarihsel OHLCV derinliği/düzeltme
    yöntemi hakkında CLAUDE.md Bölüm 11.4 + execution/algolab/ kod tabanından
    çıkarılan değerlendirme. Kod YAZILMADI, yalnızca mevcut dokümantasyon/kod
    okunarak derlendi."""
    return [
        "## Alternatif Kaynak Değerlendirmesi: AlgoLab (madde 5, read-only keşif)",
        "",
        "**Durum: `execution/algolab/` henüz İMPLEMENTE EDİLMEDİ** (Faz 5 kapsamı, "
        "CLAUDE.md Bölüm 3.2/11) — bu değerlendirme yalnızca CLAUDE.md Bölüm 11.4'teki "
        "planlanan endpoint eşlemesine dayanır, çalışan koda değil.",
        "",
        "- **Endpoint**: `GetCandleData` (Bölüm 11.4) — planlanan tarihsel bar kaynağı. "
        "`period` parametresi dakika cinsinden (günlük=1440).",
        "- **Derinlik**: CLAUDE.md Bölüm 11.4 açıkça belirtiyor: \"Tarihsel derinlik "
        "sınırlı olabilir — canlıda sorun değil (son ~300 bar yeter)\". Yani AlgoLab, "
        "**çok yıllı geriye dönük backtest verisi için tasarlanmamış** — yalnızca canlı/"
        "paper döngünün ihtiyaç duyduğu son birkaç yüz barlık pencereyi hedefliyor.",
        "- **Düzeltme yöntemi**: CLAUDE.md'de bu konuda hiçbir bilgi yok (Bölüm 16, "
        "Belirsizlik #1: \"AlgoLab endpoint/alan adlarının birebir doğruluğu\" Faz 5 "
        "başında resmi dokümanla doğrulanacak). Bölünme/bedelli/temettü düzeltmesi "
        "yapıp yapmadığı, yapıyorsa hangi yöntemle — BİLİNMİYOR.",
        "- **Sonuç**: AlgoLab, mevcut mimaride ZATEN yalnızca Faz 5'te (canlı veri + "
        "emir iletimi) devreye giriyor (CLAUDE.md Bölüm 1) — backtest veri katmanı "
        "yfinance'ten TAMAMEN bağımsız (mimari karar, değişmiyor). Bu denetimin bulduğu "
        "yfinance kör noktaları (bedelli artırımların Dividends/Stock Splits'te "
        "görünmemesi), AlgoLab'a geçilse bile GEÇMİŞ (backtest) verisi için çözülmez — "
        "çünkü AlgoLab geçmiş veri sağlamak için tasarlanmamış. **Öneri**: yfinance'in "
        "kör noktaları (aşağıdaki tabloda ölçülen) için BIST/KAP'ın resmi kurumsal "
        "aksiyon takvimini (örn. `financial_calendar` benzeri bir kaynak veya elle "
        "girilen `blackout_dates` listesinin genişletilmiş bir versiyonu — Bölüm 13.1 "
        "madde 6'daki `news_blackout` mekanizmasına benzer) ayrı bir veri kaynağı "
        "olarak değerlendirmek, AlgoLab'a geçmek değil.",
    ]


def write_report(audits: list[dict], out_path: Path, snapshot_dir: Path, trades_path: Path) -> None:
    all_jumps = pd.concat([a["jumps"] for a in audits], ignore_index=True) if audits else pd.DataFrame()

    lines = [
        "# Genişletilmiş Veri Denetimi v2 (DATA_AUDIT_v2.md)", "",
        "Salt-okunur denetim (v7 motor+veri turu, madde 4) — hiçbir veri değiştirilmedi, "
        "snapshot'a dokunulmadı. DATA_AUDIT.md'nin (%25 eşik) devamı, eşik %10'a indirildi.",
        f"Snapshot: `{snapshot_dir}` | Trade kaynağı: `{trades_path}`", "",
    ]

    if all_jumps.empty:
        lines.append("Hiçbir sembolde %10+ günlük sıçrama bulunamadı.")
    else:
        lines.append(f"Toplam {len(all_jumps)} gün, {all_jumps['symbol'].nunique()} sembolde %10+ sıçrama gösterdi.")
        lines.append("")
        lines.append("## Sınıflandırma Özeti")
        lines.append("")
        summary = all_jumps.groupby("classification").size().sort_values(ascending=False)
        lines.append("| Sınıf | Gün Sayısı |")
        lines.append("|---|---|")
        for cls, n in summary.items():
            lines.append(f"| {cls} | {n} |")
        lines.append("")

        lines.append("## Sembol Başına Açıklanamayan-Gap Sayısı ve Trade Yakınlığı")
        lines.append("")
        lines.append("| Sembol | Toplam %10+ Gün | Açıklanamayan Gap | Açıklanamayan Gap'lerden ±5 Bar'da Trade Olan |")
        lines.append("|---|---|---|---|")
        for sym in sorted(all_jumps["symbol"].unique()):
            sym_jumps = all_jumps[all_jumps["symbol"] == sym]
            unexplained = sym_jumps[sym_jumps["classification"] == "açıklanamayan gap (muhtemel bedelli)"]
            near = unexplained["trade_within_5_bars"].sum()
            lines.append(f"| {sym} | {len(sym_jumps)} | {len(unexplained)} | {near} |")
        lines.append("")

        lines.append("## Tüm %10+ Günlerin Detayı")
        lines.append("")
        lines.append("| Sembol | Tarih (Istanbul) | Getiri | Hacim Oranı (20g) | Sınıf | ±5 Bar'da Trade |")
        lines.append("|---|---|---|---|---|---|")
        for _, row in all_jumps.sort_values(["symbol", "date"]).iterrows():
            vr = f"{row['vol_ratio_20d']:.2f}" if pd.notna(row["vol_ratio_20d"]) else "N/A"
            lines.append(
                f"| {row['symbol']} | {row['date'].strftime('%Y-%m-%d')} | {row['return']:.2%} | "
                f"{vr} | {row['classification']} | {'Evet' if row['trade_within_5_bars'] else 'Hayır'} |"
            )
        lines.append("")

    lines.append("## Yorum")
    lines.append("")
    lines.append(
        "Bu tarama, KCHOL 2007-06-08'in (dışarıdan Koç Holding IR sayfasından doğrulanmış "
        "bir bedelli sermaye artırımı) neden yfinance'in Dividends/Stock Splits kolonlarında "
        "GÖRÜNMEDİĞİNİ açıklıyor — yfinance yalnızca temettü ve klasik bölünmeleri izliyor, "
        "bedelli sermaye artırımlarını İZLEMİYOR. Yukarıdaki 'açıklanamayan gap (muhtemel "
        "bedelli)' sınıfı, bu kör noktanın 12 sembollük evrende kaç kez tekrarlandığının "
        "bir alt sınırıdır (yalnızca %10+ günler taranmıştır — daha küçük bedelli etkileri "
        "bu eşiğin altında kalıp hiç yakalanmamış olabilir)."
    )
    lines.append("")
    lines.extend(algolab_source_assessment())
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Genişletilmiş veri denetimi v2 (madde 4, read-only)")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--trades", required=True, help="v6 trades.csv yolu")
    parser.add_argument("--out", default="DATA_AUDIT_v2.md")
    parser.add_argument("--raw-cache", default=str(RAW_CACHE_DIR))
    args = parser.parse_args()

    snapshot_dir = Path(args.snapshot)
    data = load_snapshot(snapshot_dir)
    trades = pd.read_csv(args.trades)

    from core.config import load_config
    cfg = load_config()
    yf_map = {i.symbol: i.yf_symbol for i in cfg.instruments}

    audits = []
    for symbol, df in data.items():
        normalized = normalize_bist_dates(df)
        yf_symbol = yf_map.get(symbol, f"{symbol}.IS")
        audits.append(audit_symbol(symbol, yf_symbol, normalized, trades, Path(args.raw_cache)))
        print(f"{symbol}: {len(audits[-1]['jumps'])} sıçrama (>=%{JUMP_THRESHOLD_V2*100:.0f})")

    write_report(audits, Path(args.out), snapshot_dir, Path(args.trades))
    print(f"Rapor yazıldı: {args.out}")


if __name__ == "__main__":
    main()

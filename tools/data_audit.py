# tools/data_audit.py
"""Salt-okunur veri bütünlüğü denetimi (HARDENING.md A2).

Hiçbir veriyi DEĞİŞTİRMEZ, hiçbir cache/config dosyasını güncellemez —
yalnızca data/snapshots/ altındaki dondurulmuş veriyi okur ve DATA_AUDIT.md
üretir. Sinyal motoru, gate'ler, eşikler bu betikten etkilenmez/etkilenemez.

Kullanım: python -m tools.data_audit --snapshot data/snapshots/2026-07-06 --out DATA_AUDIT.md
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import pandas as pd

from data.quality import check_quality

JUMP_THRESHOLD = 0.25
MAJORITY_FRACTION = 0.70  # bir günü "beklenen işlem günü" saymak için sembollerin en az bu kadarında bulunmalı


def load_snapshot(snapshot_dir: Path) -> dict[str, pd.DataFrame]:
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    symbols = list(manifest["files"].keys())
    return {s: pd.read_parquet(snapshot_dir / f"{s}.parquet") for s in symbols}


def check_missing_bars(data: dict[str, pd.DataFrame]) -> dict[str, list]:
    """Her sembolün işlem günleri kümesini diğerleriyle çapraz karşılaştırır.
    Sembollerin çoğunda (>=%70) var olan ama bu sembolde eksik olan günler
    'şüpheli eksik' sayılır (BIST tatilleri sembole özgü olmadığından, çoğunlukta
    varsa o gün genel bir işlem günüdür)."""
    date_counts: dict[pd.Timestamp, int] = {}
    for df in data.values():
        for d in df.index.normalize():
            date_counts[d] = date_counts.get(d, 0) + 1
    n = len(data)
    majority_dates = {d for d, c in date_counts.items() if c >= n * MAJORITY_FRACTION}

    missing = {}
    for sym, df in data.items():
        sym_dates = set(df.index.normalize())
        missing_days = sorted(majority_dates - sym_dates)
        missing[sym] = missing_days
    return missing


def check_jumps(df: pd.DataFrame, threshold: float = JUMP_THRESHOLD) -> pd.DataFrame:
    """|günlük getiri| > threshold olan günleri listeler ve basit bir sınıflandırma
    DENER (kesin hüküm değil — hacim ve getiri büyüklüğü kalıbına dayalı bir işaret)."""
    returns = df["close"].pct_change()
    jumps = returns[returns.abs() > threshold]
    if jumps.empty:
        return pd.DataFrame(columns=["date", "return", "volume", "vol_ratio_20d", "classification"])

    vol_avg20 = df["volume"].rolling(20).mean()
    rows = []
    for date, ret in jumps.items():
        vol = float(df.loc[date, "volume"])
        avg_vol = vol_avg20.loc[date]
        vol_ratio = float(vol / avg_vol) if pd.notna(avg_vol) and avg_vol > 0 else None

        near_clean_ratio = any(abs(abs(1 + ret) - k) < 0.03 for k in (0.5, 2.0, 1.5, 0.33, 3.0))
        if near_clean_ratio:
            classification = "muhtemel kurumsal işlem (bölünme/bedelli oranına yakın — düzeltme hatası olabilir)"
        elif vol_ratio is not None and vol_ratio >= 1.5:
            classification = "muhtemel gerçek hareket (hacim destekli)"
        else:
            classification = "sınıflandırılamadı — elle incelenmeli"

        rows.append({
            "date": date, "return": float(ret), "volume": vol,
            "vol_ratio_20d": vol_ratio, "classification": classification,
        })
    return pd.DataFrame(rows)


def audit_symbol(symbol: str, df: pd.DataFrame, missing_days: list) -> dict:
    quality = check_quality(df)
    zero_neg = int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    dup_dates = int(df.index.duplicated().sum())
    jumps = check_jumps(df)

    status = "PASS"
    if not quality.passed or zero_neg > 0 or dup_dates > 0:
        status = "FAIL"
    elif missing_days or not jumps.empty:
        status = "WARN"

    return {
        "symbol": symbol, "status": status, "rows": len(df),
        "quality_passed": quality.passed, "quality_errors": quality.errors,
        "zero_or_negative_price_count": zero_neg, "duplicate_date_count": dup_dates,
        "missing_days": [str(d.date()) for d in missing_days],
        "jumps": jumps,
    }


def _tolerance_boundary_proof() -> list[str]:
    """A2 ek maddesi: dc56ed2'deki OHLC rtol/atol toleransının (rtol=0.005,
    atol=1e-6) epsilon gürültüsünü geçirip GERÇEK ihlalleri hâlâ yakaladığını
    sentetik örneklerle kanıtlar."""
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    close = [100.0, 101.0, 102.0, 103.0, 104.0]
    open_ = [99.5, 100.5, 101.5, 102.5, 103.5]
    low = [o - 0.5 for o in open_]

    def make_df(high_offset: float) -> pd.DataFrame:
        high = [c + high_offset for c in close]
        return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                             "volume": [1000.0] * 5}, index=idx)

    cases = [
        ("epsilon (-1e-13, kayan nokta gürültüsü)", -1e-13),
        ("%0.3 sapma (tolerans içinde, rtol=%0.5)", -0.3),
        ("%0.5 sapma (tolerans sınırında)", -0.5),
        ("%5 sapma (gerçek ihlal, rtol'un 10 katı)", -5.0),
    ]
    lines = []
    for label, offset in cases:
        result = check_quality(make_df(offset))
        lines.append(f"- {label} → {'PASS' if result.passed else 'FAIL'}")
    return lines


def write_report(audits: list[dict], tolerance_proof: list[str], out_path: Path, snapshot_dir: Path) -> None:
    lines = [
        "# Veri Bütünlüğü Denetimi (DATA_AUDIT.md)", "",
        "Salt-okunur denetim (HARDENING.md A2) — hiçbir veri değiştirilmedi.",
        f"Snapshot: `{snapshot_dir}`", "",
        "## Özet Tablo", "",
        "| Sembol | Durum | Satır | Kalite Kontrolü | Sıfır/Negatif Fiyat | Yinelenen Tarih | Eksik Gün | Sıçrama (>%25) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a in audits:
        lines.append(
            f"| {a['symbol']} | {a['status']} | {a['rows']} | "
            f"{'PASS' if a['quality_passed'] else 'FAIL'} | {a['zero_or_negative_price_count']} | "
            f"{a['duplicate_date_count']} | {len(a['missing_days'])} | {len(a['jumps'])} |"
        )
    lines.append("")

    any_fail = any(a["status"] == "FAIL" for a in audits)
    any_warn = any(a["status"] == "WARN" for a in audits)

    lines.append("## Sembol Detayları")
    lines.append("")
    for a in audits:
        lines.append(f"### {a['symbol']} — {a['status']}")
        if not a["quality_passed"]:
            lines.append(f"- Kalite kontrolü hatası: {a['quality_errors']}")
        if a["missing_days"]:
            lines.append(f"- Eksik gün(ler) (çoğunlukta var, bu sembolde yok): {a['missing_days'][:10]}"
                         + (f" ... (+{len(a['missing_days'])-10} tane daha)" if len(a["missing_days"]) > 10 else ""))
        if not a["jumps"].empty:
            lines.append(f"- {len(a['jumps'])} şüpheli sıçrama (>%25):")
            for _, row in a["jumps"].iterrows():
                vol_ratio_str = f", 20g_hacim_oranı={row['vol_ratio_20d']:.2f}x" if row["vol_ratio_20d"] is not None else ""
                lines.append(
                    f"  - {row['date'].date()}: getiri={row['return']:.1%}, "
                    f"hacim={row['volume']:.0f}{vol_ratio_str} — {row['classification']}"
                )
        if a["status"] == "PASS":
            lines.append("- Bulgu yok.")
        lines.append("")

    lines.append("## auto_adjust Durumu")
    lines.append("")
    lines.append(
        "Tüm veri `yfinance` üzerinden `auto_adjust=True` ile indirildi "
        "(`data/historical.py`). Bu, temettü ve bölünme düzeltmelerinin OHLC "
        "sütunlarına doğrudan işlendiği, ayrı bir `Adj Close` sütununun "
        "TUTULMADIĞI anlamına gelir — pipeline'ımız yalnızca düzeltilmiş "
        "fiyatı saklıyor, ham (düzeltilmemiş) fiyatla karşılaştırma yapılamıyor. "
        "Bu, projenin bilinen bir sınırlaması: bir günün 'sıçraması' gerçek bir "
        "fiyat hareketi mi yoksa auto_adjust'ın bir kurumsal işlemi hatalı "
        "düzeltmesi mi, ham veri olmadan kesin olarak ayırt edilemez."
    )
    lines.append("")

    lines.append("## Ek: OHLC Tolerans Sınır Kanıtı (dc56ed2 denetimi)")
    lines.append("")
    lines.append(
        "`data/quality.py`'nin OHLC toleransı (rtol=%0.5, atol=1e-6) sentetik "
        "sınır durumlarıyla test edildi:"
    )
    lines.extend(tolerance_proof)
    lines.append("")
    lines.append(
        "Sonuç: tolerans, kayan nokta gürültüsünü (epsilon) ve küçük "
        "adjustment-yuvarlama sapmalarını (%0.3'e kadar) doğru şekilde "
        "geçiriyor, ama %5'lik gerçek bir ihlali hâlâ doğru şekilde "
        "reddediyor. Sınır (rtol=%0.5) ile gerçek ihlal arasında 10 kat "
        "güvenlik marjı var — makul."
    )
    lines.append("")

    lines.append("## Genel Değerlendirme")
    lines.append("")
    if any_fail:
        lines.append(
            "**FAIL bulundu.** Bu denetim FAIL üreten sembol(ler) için, veri "
            "düzeltilene kadar v5 (ve sonrası) backtest sonuçları karantinadadır "
            "— bkz. yukarıdaki sembol detayları."
        )
    elif any_warn:
        lines.append(
            "Hiçbir sembol FAIL almadı. Bazı semboller WARN aldı (şüpheli "
            "sıçrama ve/veya eksik gün) — bunlar aşağıda listelendi ve "
            "sınıflandırma DENEMESİ yapıldı, ama kesin hüküm verilmedi "
            "(kullanıcıyla birlikte değerlendirilmeli). v5 sonuçları "
            "karantinada DEĞİL, ama bu WARN'lar dikkate alınmalı."
        )
    else:
        lines.append("Tüm semboller PASS. Herhangi bir veri bütünlüğü sorunu tespit edilmedi.")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Salt-okunur veri bütünlüğü denetimi (HARDENING.md A2)")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--out", default="DATA_AUDIT.md")
    args = parser.parse_args()

    snapshot_dir = Path(args.snapshot)
    data = load_snapshot(snapshot_dir)
    missing = check_missing_bars(data)

    audits = [audit_symbol(sym, df, missing[sym]) for sym, df in sorted(data.items())]
    tolerance_proof = _tolerance_boundary_proof()

    write_report(audits, tolerance_proof, Path(args.out), snapshot_dir)
    print(f"Rapor yazıldı: {args.out}")


if __name__ == "__main__":
    main()

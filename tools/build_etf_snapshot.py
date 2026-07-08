# tools/build_etf_snapshot.py
"""D4US-S1 (varlık-sınıfı ETF dual-momentum ailesi) — ETF evreni DONDURULMUŞ snapshot'ı.

10 SEMBOL SABİT (ikame YASAK — D4US_CRITERIA.md/KALICI KAYIT 20):
  SPY IWM EFA EEM VNQ TLT IEF LQD GLD DBC
(US large/small-cap, gelişmiş/gelişen uluslararası, US GYO, uzun/orta vadeli Hazine,
yatırım-yapılabilir kredi, altın, geniş emtia — 10 varlık sınıfı/segment).

**TOTAL-RETURN serisi:** `data/adapters/yf_us.py` (yfinance, auto_adjust=True) →
kapanış temettü+bölünme düzeltmeli (total-return). Tahvil ETF'lerinde (TLT/IEF/LQD)
fiyat-only seri ciddi hata verir (kupon getirisi kaybolur) → strateji VE sepet AYNI
total-return seride ölçülür. Kullanılan ayar (auto_adjust=True) manifest'e yazılır.

**KİMLİK DOĞRULAMASI (US3 dersi — DATA_FEASIBILITY_US3):** bazı ticker'lar sessizce
başka bir enstrümanın verisini döndürebilir. Bu yüzden fiyat indirmeden ÖNCE her sembol
için yfinance `longName` + `quoteType` çekilir ve beklenen fon adının anahtar kelimesiyle
eşleştiği doğrulanır. **Herhangi biri eşleşmezse İKAME YAPILMAZ — snapshot yazılMAZ,
hata fırlatılır (DUR-ve-sor).** Kimlik sonuçları `identity.json`'a yazılır (provenance).

Mevcut snapshot'lara (BIST/us/us2/aux/aux_us/us_bench/fx) DOKUNMAZ — yalnız yeni bir
`data/snapshots/etf_us/<tarih>/` dizini yazar. Bir kez çalıştırılıp commit'lenir →
sonrası deterministik/offline (sha256 manifest). Canlı bot bu snapshot'ı OKUMAZ.

Kullanım:  python -m tools.build_etf_snapshot
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yfinance as yf

from data.adapters.yf_us import YfUsAdapter
from tools.build_snapshot import build_snapshot

# ETF evreni (10 sembol, SABİT). (sembol, varlık-sınıfı, longName anahtar-kelime[ler])
# Anahtar kelime BİRDEN FAZLA olabilir — TÜMÜ (case-insensitive) longName'de bulunmalı.
ETF_UNIVERSE = [
    ("SPY", "US Large-Cap Hisse",          ["s&p 500"]),
    ("IWM", "US Small-Cap Hisse",          ["russell 2000"]),
    ("EFA", "Gelişmiş Uluslararası Hisse", ["eafe"]),
    ("EEM", "Gelişen Piyasa Hissesi",      ["emerging markets"]),
    ("VNQ", "US GYO (Gayrimenkul)",        ["real estate"]),
    ("TLT", "US 20+ Yıl Hazine Tahvili",   ["20+ year treasury"]),
    ("IEF", "US 7-10 Yıl Hazine Tahvili",  ["7-10 year treasury"]),
    ("LQD", "US Yatırım-Yapılabilir Kredi", ["investment grade corporate"]),
    ("GLD", "Altın",                        ["gold"]),
    ("DBC", "Geniş Emtia",                  ["commodity"]),
]

ETF_SYMBOLS = [s for s, _, _ in ETF_UNIVERSE]

OUT_DIR = Path("data/snapshots/etf_us/2026-07-08")
START = date(2005, 1, 1)

SCOPE = (
    "D4US-S1 ETF evreni (10 varlık-sınıfı ETF: SPY IWM EFA EEM VNQ TLT IEF LQD GLD DBC) "
    "— SABİT, ikame YASAK. TOTAL-RETURN (auto_adjust=True; tahvil ETF'lerinde fiyat-only "
    "ciddi hata). Kompozit başlangıç = en geç başlayan ETF (DBC ~2006). Kimlik longName "
    "ile doğrulandı (identity.json). Varlık-sınıfı dual-momentum ailesinin (D4-US) "
    "araştırma evreni; canlı bot bu snapshot'ı OKUMAZ."
)


class IdentityMismatch(RuntimeError):
    """Bir ETF'in yfinance longName/quoteType kimliği beklentiyle uyuşmadı → DUR-ve-sor."""


def verify_identities() -> dict:
    """Fiyat indirmeden ÖNCE her sembolün kimliğini (longName + quoteType) doğrula.
    Uyuşmazlıkta İKAME YAPMA — IdentityMismatch fırlat. Döner: {symbol: {...}} raporu."""
    report: dict[str, dict] = {}
    failures: list[str] = []
    for symbol, asset_class, keywords in ETF_UNIVERSE:
        info = yf.Ticker(symbol).get_info()
        long_name = info.get("longName") or info.get("shortName") or ""
        quote_type = info.get("quoteType") or ""
        ln_lower = long_name.lower()
        missing = [kw for kw in keywords if kw.lower() not in ln_lower]
        is_etf = quote_type.upper() == "ETF"
        ok = (not missing) and is_etf
        report[symbol] = {
            "asset_class": asset_class, "expected_keywords": keywords,
            "long_name": long_name, "quote_type": quote_type,
            "keyword_ok": not missing, "quote_type_ok": is_etf, "pass": ok,
        }
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {symbol:4s} quoteType={quote_type:6s} longName={long_name!r}")
        if not ok:
            reason = []
            if missing:
                reason.append(f"beklenen anahtar {missing} longName'de YOK")
            if not is_etf:
                reason.append(f"quoteType={quote_type!r} (ETF değil)")
            failures.append(f"{symbol}: {'; '.join(reason)}")
    if failures:
        raise IdentityMismatch(
            "ETF kimlik doğrulaması BAŞARISIZ (İKAME YOK — snapshot yazılmadı, DUR-ve-sor):\n  "
            + "\n  ".join(failures)
        )
    return report


def main() -> None:
    assert len(ETF_SYMBOLS) == 10, f"ETF evreni 10 olmalı, {len(ETF_SYMBOLS)} bulundu"
    assert len(set(ETF_SYMBOLS)) == 10, "ETF evreninde yinelenen sembol var"

    print("=== Kimlik doğrulaması (longName + quoteType, fiyat indirmeden ÖNCE) ===")
    identity = verify_identities()
    print("Tüm 10 ETF kimliği DOĞRULANDI.\n")

    print("=== Total-return fiyat snapshot'ı (auto_adjust=True) ===")
    manifest = build_snapshot(
        market_id="etf_us",
        symbols=ETF_SYMBOLS,
        adapter=YfUsAdapter(),
        start_date=START,
        out_dir=OUT_DIR,
        scope_note=SCOPE,
    )
    # Kimlik raporunu snapshot dizinine yaz (provenance — DATA_AUDIT_ETF.md kaynağı).
    (OUT_DIR / "identity.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False), encoding="utf-8")

    files = manifest["files"]
    starts = {s: v["start"][:10] for s, v in files.items()}
    ends = {v["end"][:10] for v in files.values()}
    rows = {s: v["rows"] for s, v in files.items()}
    latest_start = max(starts.values())
    latest_sym = [s for s, d in starts.items() if d == latest_start]
    print(f"\nETF snapshot yazıldı: {OUT_DIR} ({len(files)} sembol)")
    print(f"  başlangıçlar: {json.dumps(starts, indent=2)}")
    print(f"  bitiş(ler): {sorted(ends)}")
    print(f"  satır sayıları: {json.dumps(rows)}")
    print(f"  EN GEÇ başlayan (kompozit t0 adayı): {latest_sym} @ {latest_start}")


if __name__ == "__main__":
    main()

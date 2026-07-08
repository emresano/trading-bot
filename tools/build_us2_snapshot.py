# tools/build_us2_snapshot.py
"""D2US-S1 (kesitsel momentum ailesi) — US2 evreni (~50 sembol) DONDURULMUŞ snapshot'ı.

Mevcut E4 US evrenini (20 sembol) KORUYARAK ~50'ye genişletir: 2005-01'den bugüne
KESİNTİSİZ tarihçesi olan, bugün likit US large-cap'ler, sektör dağılımı dengeli.
Seçim kriteri "bugün büyük/likit + 2005'ten beri sürekli işlem gören" — **geçmiş
getiriye göre seçim YAPILMADI**. Bilinen survivorship yanlılığı DATA_AUDIT_US2.md'nin
ZORUNLU bölümünde raporlanır (E4 emsali: sepet çıtası gerçek-üstü yüksek =
kıyasta muhafazakâr).

Kaynak: `data/adapters/yf_us.py` (yfinance, auto_adjust=True). Temizlik borusu
S1b/E4 ile AYNI (`data/cleaning.py::load_and_clean_universe`) — bu snapshot yalnız
HAM veriyi dondurur, temizlik yükleme anında uygulanır.

Mevcut snapshot'lara (BIST/us/aux/aux_us/us_bench/fx) DOKUNMAZ — yalnız yeni bir
`data/snapshots/us2/<tarih>/` dizini yazar. Bir kez çalıştırılıp commit'lenir →
sonrası deterministik/offline (sha256 manifest).

Kullanım:  python -m tools.build_us2_snapshot
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from data.adapters.yf_us import YfUsAdapter
from tools.build_snapshot import build_snapshot

# US2 evreni (50 sembol, 10 GICS sektörü). İlk 20 = E4 US evreni (KORUNDU, aynı sıra);
# kalan 30 yeni. Sektör etiketleri DATA_AUDIT_US2.md'de tam tabloda.
US2_SYMBOLS = [
    # --- E4 US evreni (20, korundu) ---
    "AAPL", "MSFT", "INTC", "CSCO",          # Bilgi Teknolojisi
    "JNJ", "PFE", "MRK",                      # Sağlık
    "JPM", "BAC",                             # Finans
    "XOM", "CVX",                             # Enerji
    "PG", "KO", "WMT",                        # Temel Tüketim
    "HD", "MCD", "NKE",                       # Tüketici Takdiri
    "DIS", "VZ",                              # İletişim
    "CAT",                                    # Sanayi
    # --- Yeni 30 (2005-01-03'ten sürekli, likit large-cap, sektör dengesi) ---
    "ORCL", "IBM", "TXN", "QCOM",             # Bilgi Teknolojisi (+4 → 8)
    "ABT", "AMGN", "MDT", "LLY", "GILD",      # Sağlık (+5 → 8)
    "WFC", "GS", "AXP", "C",                  # Finans (+4 → 6)
    "COP", "SLB",                             # Enerji (+2 → 4)
    "PEP", "CL", "MO",                        # Temel Tüketim (+3 → 6)
    "SBUX", "LOW", "TGT",                     # Tüketici Takdiri (+3 → 6)
    "CMCSA", "T",                             # İletişim (+2 → 4)
    "HON", "UNP", "BA",                       # Sanayi (+3 → 4)
    "DUK", "SO",                              # Kamu Hizmetleri (+2, yeni sektör)
    "NEM", "APD",                             # Malzeme (+2, yeni sektör)
]

OUT_DIR = Path("data/snapshots/us2/2026-07-08")
START = date(2005, 1, 1)

SCOPE = (
    "D2US-S1 US2 evreni (50 sembol, 10 GICS sektörü) — E4 US evrenini (20) KORUYARAK "
    "genişletti. 2005-01'den bugüne sürekli tarihçe; bugün likit large-cap; geçmiş "
    "getiriye göre SEÇİLMEDİ (survivorship yanlılığı DATA_AUDIT_US2.md'de raporlanır). "
    "Kesitsel momentum ailesinin (D2-US) araştırma evreni; canlı bot bu snapshot'ı OKUMAZ."
)


def main() -> None:
    assert len(US2_SYMBOLS) == 50, f"US2 evreni 50 olmalı, {len(US2_SYMBOLS)} bulundu"
    assert len(set(US2_SYMBOLS)) == 50, "US2 evreninde yinelenen sembol var"
    manifest = build_snapshot(
        market_id="us2",
        symbols=US2_SYMBOLS,
        adapter=YfUsAdapter(),
        start_date=START,
        out_dir=OUT_DIR,
        scope_note=SCOPE,
    )
    files = manifest["files"]
    rows = {v["rows"] for v in files.values()}
    print(f"US2 snapshot yazıldı: {OUT_DIR} ({len(files)} sembol)")
    print(f"  satır sayıları (benzersiz): {sorted(rows)}")
    starts = {v["start"][:10] for v in files.values()}
    ends = {v["end"][:10] for v in files.values()}
    print(f"  başlangıç(lar): {sorted(starts)}  bitiş(ler): {sorted(ends)}")


if __name__ == "__main__":
    main()

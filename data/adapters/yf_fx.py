# data/adapters/yf_fx.py
"""FX için yfinance tabanlı DataAdapter — E1'in belgelenmiş kaynak sapması.

EXPANSION.md Bölüm 6.2: "oanda.py: v20 REST practice ... Hesap yoksa E1 yedek
yolu: Dukascopy/histdata CSV." Bu E1 turunda:
- OANDA practice hesabı YOK (secrets.env'de kimlik bilgisi bulunmuyor).
- Dukascopy'nin ham tick endpoint'i bu ortamdan ERİŞİLEMEDİ (bağlantı
  kurulamadı — muhtemelen ağ kısıtı).
- histdata.com'un CSV indirme akışı etkileşimli (JS/token tabanlı) olup
  otomatik/güvenilir bir programatik indirme sağlamıyor.

Bu nedenle E1'in DONDURULMUŞ FX anlık görüntüsü için PRATİK, ÇALIŞAN ve
TEST EDİLMİŞ bir kaynak olarak yfinance (EURUSD=X, GBPUSD=X, USDJPY=X)
kullanıldı — proje genelinde zaten güvenilen, BIST'te de aynı rolü oynayan
(CLAUDE.md Bölüm 1: "backtest veri katmanı AlgoLab'dan tamamen bağımsızdır,
yfinance ile") bir kütüphane. `oanda.py` yine de Bölüm 6.2'nin öngördüğü
ABC implementasyonu olarak YAZILDI (referans implementasyon, CLAUDE.md
Bölüm 11.2'deki AlgoLab auth.py emsaliyle tutarlı) — E3'te gerçek bir
practice hesapla doğrulanacak. E1'in snapshot'ı BU modülden (yf_fx) üretildi.

**Bilinen sınırlama:** yfinance'in FX günlük barları Europe/London gece
yarısıyla etiketlenir (borsa kapanışı kavramı yok, 24 saatlik piyasa) —
EXPANSION.md Bölüm 5'in tanımladığı FX_24_5 takviminin "17:00 America/New_York
kapanışı" kuralıyla BİREBİR ÖRTÜŞMEZ. Bu modül yalnızca Europe/London takvim
gününe göre tarihleri normalize eder (DST'ye karşı tutarlılık için); NY-17:00
haftalık kaydırması calendars.py'nin işi (E2), bu adaptörün kapsamı DIŞINDA.
"""
from __future__ import annotations
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from .base import AdapterMeta, DataAdapter, relabel_to_local_calendar_day, validate_canonical_schema

_INTERVAL_MAP = {"1d": "1d"}

# EXPANSION.md Bölüm 11.3 enstrüman listesi -> yfinance sembolü
FX_YF_SYMBOL_MAP = {
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "USD_JPY": "USDJPY=X",
}


class YfFxAdapter(DataAdapter):
    adapter_id = "yf_fx"

    def fetch_history(self, symbol: str, timeframe: str,
                      start: date, end: Optional[date] = None) -> tuple[pd.DataFrame, AdapterMeta]:
        yf_symbol = FX_YF_SYMBOL_MAP.get(symbol, symbol)
        interval = _INTERVAL_MAP[timeframe]
        kwargs = {"interval": interval, "start": str(start), "auto_adjust": True}
        if end is not None:
            kwargs["end"] = str(end)
        raw = yf.Ticker(yf_symbol).history(**kwargs)
        df = self._normalize(raw)
        validate_canonical_schema(df, self.adapter_id)
        meta = AdapterMeta(
            adapter_id=self.adapter_id, source="yfinance",
            download_params={"interval": interval, "start": str(start), "end": str(end) if end else None,
                            "yf_symbol": yf_symbol},
            correction_policy="yok (FX'te kurumsal aksiyon/ayarlama kavramı yok)",
            library_version=getattr(yf, "__version__", "unknown"),
            volume_kind="none",  # yfinance FX hacmi her zaman 0 — merkezi hacim yok
        )
        return df, meta

    def fetch_latest(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        yf_symbol = FX_YF_SYMBOL_MAP.get(symbol, symbol)
        interval = _INTERVAL_MAP[timeframe]
        raw = yf.Ticker(yf_symbol).history(interval=interval, period="max", auto_adjust=True)
        df = self._normalize(raw)
        return df.tail(lookback)

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        if raw.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].copy()
        df = df.astype("float64")  # EXPANSION.md Bölüm 6.1: kanonik şema 5 kolonda da float64
        df.index.name = "ts"
        return relabel_to_local_calendar_day(df, "Europe/London")

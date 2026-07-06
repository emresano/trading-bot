# data/adapters/yf_us.py
"""ABD hisseleri için yfinance tabanlı DataAdapter (EXPANSION.md Bölüm 6.2)."""
from __future__ import annotations
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from .base import AdapterMeta, DataAdapter, relabel_to_local_calendar_day, validate_canonical_schema

_INTERVAL_MAP = {"1d": "1d"}


class YfUsAdapter(DataAdapter):
    adapter_id = "yf_us"

    def fetch_history(self, symbol: str, timeframe: str,
                      start: date, end: Optional[date] = None) -> tuple[pd.DataFrame, AdapterMeta]:
        interval = _INTERVAL_MAP[timeframe]
        kwargs = {"interval": interval, "start": str(start), "auto_adjust": True}
        if end is not None:
            kwargs["end"] = str(end)
        raw = yf.Ticker(symbol).history(**kwargs)
        df = self._normalize(raw)
        validate_canonical_schema(df, self.adapter_id)
        meta = AdapterMeta(
            adapter_id=self.adapter_id, source="yfinance",
            download_params={"interval": interval, "start": str(start), "end": str(end) if end else None},
            correction_policy="auto_adjust=True (yfinance) — kurumsal işlemler (split/temettü) düzeltilir",
            library_version=getattr(yf, "__version__", "unknown"),
            volume_kind="shares",
        )
        return df, meta

    def fetch_latest(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        interval = _INTERVAL_MAP[timeframe]
        raw = yf.Ticker(symbol).history(interval=interval, period="max", auto_adjust=True)
        df = self._normalize(raw)
        return df.tail(lookback)

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        if raw.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].copy()
        df = df.astype("float64")  # EXPANSION.md Bölüm 6.1: kanonik şema 5 kolonda da float64
        df.index.name = "ts"
        # NYSE/NASDAQ UTC-5/-4 (Amerika her zaman UTC'nin GERİSİNDE) — borsa
        # yerel gece yarısını UTC'ye çevirmek AYNI takvim gününde kalır (BIST'in
        # yaşadığı bir-gün-geri kayması burada yapısal olarak yok). Yine de
        # DST geçiş haftalarında tutarlılık için ortak relabel fonksiyonu
        # kullanılıyor (bkz. tests/test_calendars.py'nin E2'de ekleyeceği
        # DST sınır testleri).
        return relabel_to_local_calendar_day(df, "America/New_York")

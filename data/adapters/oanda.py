# data/adapters/oanda.py
"""OANDA v20 REST DataAdapter — REFERANS İMPLEMENTASYON, DOĞRULANMAMIŞ.

**Doğruluk notu (CLAUDE.md Bölüm 11.2/11.4 kalıbıyla):** Bu implementasyon
OANDA v20 REST API'sinin kamuya açık dokümantasyonuna (candles endpoint)
dayanır. E1 sırasında `secrets.env`'de OANDA kimlik bilgisi (API token) YOKTU
— bu kod HİÇBİR CANLI/PRACTICE HESABA KARŞI TEST EDİLMEDİ. E3'te (broker
adapter fazı), gerçek bir practice hesapla doğrulanana kadar bu modülü
GÜVENİLİR SAYMA — E1'in dondurulmuş FX snapshot'ı bu modülden DEĞİL,
`yf_fx.py`'den üretildi (bkz. o dosyanın docstring'i).

JSON ayrıştırma mantığı (`_parse_candles_response`) sabit bir fixture'la
(gerçek OANDA dokümantasyonundaki örnek yanıt formatına dayanan, ağsız)
test edilmiştir — bu, formatın DOĞRU YORUMLANDIĞINI kanıtlar, API'nin bu
formatı GERÇEKTEN döndürdüğünü değil.

Uyuşmazlık bulunursa bu dosyaya düzeltme notu ekleyin (CLAUDE.md Bölüm 11
kuralı).
"""
from __future__ import annotations
import os
from datetime import date
from typing import Optional

import pandas as pd
import requests

from .base import AdapterMeta, DataAdapter, relabel_to_local_calendar_day, validate_canonical_schema

PRACTICE_BASE_URL = "https://api-fxpractice.oanda.com"
_GRANULARITY_MAP = {"1d": "D"}


class OandaAuthError(Exception):
    pass


def _parse_candles_response(payload: dict) -> pd.DataFrame:
    """OANDA v20 `/v3/instruments/{instrument}/candles` yanıtını kanonik
    şemaya çevirir. Beklenen format (kamuya açık dokümantasyon):
    {"candles": [{"time": "2024-01-02T22:00:00.000000000Z", "complete": true,
                  "volume": 12345, "mid": {"o": "1.10", "h": "1.11",
                  "l": "1.09", "c": "1.105"}}, ...]}
    Yalnızca `complete=true` mumlar dahil edilir (oluşmakta olan bar hariç —
    CLAUDE.md Bölüm 4.3'ün "son bar KAPANMIŞ bar olmalı" kuralıyla tutarlı)."""
    candles = payload.get("candles", [])
    rows = []
    index = []
    for c in candles:
        if not c.get("complete", False):
            continue
        mid = c["mid"]
        index.append(pd.Timestamp(c["time"]))
        rows.append({
            "open": float(mid["o"]), "high": float(mid["h"]),
            "low": float(mid["l"]), "close": float(mid["c"]),
            "volume": float(c.get("volume", 0)),
        })
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(index, name="ts"))
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.sort_index()


class OandaAdapter(DataAdapter):
    adapter_id = "oanda"

    def __init__(self, api_token: Optional[str] = None, base_url: str = PRACTICE_BASE_URL):
        self.api_token = api_token or os.environ.get("OANDA_API_TOKEN")
        self.base_url = base_url

    def _headers(self) -> dict:
        if not self.api_token:
            raise OandaAuthError(
                "OANDA_API_TOKEN yok — secrets.env'e eklenmeden bu adaptör canlı çağrı yapamaz "
                "(E1'in snapshot'ı yf_fx.py'den üretildi, bu adaptör E3'e kadar kullanılmadı)."
            )
        return {"Authorization": f"Bearer {self.api_token}"}

    def fetch_history(self, symbol: str, timeframe: str,
                      start: date, end: Optional[date] = None) -> tuple[pd.DataFrame, AdapterMeta]:
        granularity = _GRANULARITY_MAP[timeframe]
        params = {"granularity": granularity, "price": "M", "from": f"{start}T00:00:00Z"}
        if end is not None:
            params["to"] = f"{end}T00:00:00Z"
        resp = requests.get(
            f"{self.base_url}/v3/instruments/{symbol}/candles",
            headers=self._headers(), params=params, timeout=15,
        )
        resp.raise_for_status()
        df = _parse_candles_response(resp.json())
        df = relabel_to_local_calendar_day(df, "UTC") if not df.empty else df
        validate_canonical_schema(df, self.adapter_id)
        meta = AdapterMeta(
            adapter_id=self.adapter_id, source=f"OANDA v20 REST ({self.base_url})",
            download_params={"granularity": granularity, "from": str(start), "to": str(end) if end else None},
            correction_policy="yok (FX'te kurumsal aksiyon kavramı yok)",
            library_version=getattr(requests, "__version__", "unknown"),
            volume_kind="tick",  # OANDA'nın 'volume' alanı tick-volume'dur, merkezi hacim değil
        )
        return df, meta

    def fetch_latest(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        granularity = _GRANULARITY_MAP[timeframe]
        resp = requests.get(
            f"{self.base_url}/v3/instruments/{symbol}/candles",
            headers=self._headers(),
            params={"granularity": granularity, "price": "M", "count": lookback},
            timeout=15,
        )
        resp.raise_for_status()
        df = _parse_candles_response(resp.json())
        return relabel_to_local_calendar_day(df, "UTC") if not df.empty else df

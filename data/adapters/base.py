# data/adapters/base.py
"""Kanonik OHLCV veri adaptörü arayüzü (EXPANSION.md Bölüm 6).

Piyasa farkı yalnızca burada (adapter'lar), costs/ (maliyet modelleri) ve gate
profillerinde soğurulur — çekirdek motor/sinyal/risk kodu hiçbir adaptöre veya
piyasaya özel dallanma içermez (EXPANSION.md Bölüm 3.2).

BIST'in mevcut veri katmanına (`data/historical.py`, `data/cleaning.py`)
KASITLI olarak dokunulmadı/bağımlı olunmadı — EXPANSION.md E1'in kabul
kriteri "BIST hattında sıfır değişiklik"tir. Bu modüldeki
`relabel_to_local_calendar_day`, `data/cleaning.py::normalize_bist_dates` ile
AYNI mantığı (borsa yerel takvim gününü UTC gece yarısı olarak yeniden
etiketlemek) genelleştirilmiş biçimde uygular, ama bağımsız bir
implementasyondur.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd

CANONICAL_COLUMNS = ["open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class AdapterMeta:
    """Snapshot manifest'ine yazılan kaynak/düzeltme bilgisi (EXPANSION.md 6.1)."""
    adapter_id: str
    source: str
    download_params: dict = field(default_factory=dict)
    correction_policy: str = ""    # örn. "auto_adjust=True (yfinance)"
    library_version: str = ""
    volume_kind: str = "shares"    # "shares" | "tick" | "none"


class DataAdapter(ABC):
    """Tüm piyasa adaptörlerinin ortak sözleşmesi. Çıktı DataFrame'i her zaman
    kanonik şemadadır (bkz. `validate_canonical_schema`)."""

    adapter_id: str

    @abstractmethod
    def fetch_history(self, symbol: str, timeframe: str,
                      start: date, end: date) -> tuple[pd.DataFrame, AdapterMeta]:
        """Kanonik şemada DataFrame + kaynak metadata'sı döner."""

    @abstractmethod
    def fetch_latest(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        """Son `lookback` barı kanonik şemada döner (canlı/paper döngüsü için)."""


def relabel_to_local_calendar_day(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Barın index'ini `tz` bölgesindeki GERÇEK takvim gününü UTC gece yarısı
    olarak yeniden etiketler (saat bilgisi zaten anlamsız — günlük bar tek bir
    takvim gününü temsil eder).

    Neden gerekli: kaynak kütüphaneler (yfinance vb.) günlük barları borsa
    yerel gece yarısıyla (tz-aware) döner. Borsa UTC'nin İLERİSİNDEYSE
    (örn. Istanbul UTC+3) bunu ham UTC'ye çevirmek tarihi bir gün GERİYE
    kaydırır (v7'nin bulduğu bug). Borsa UTC'nin GERİSİNDEYSE (örn. New York
    UTC-5/-4) kayma olmaz — ama DST geçiş haftalarında (örn. Londra tz'li FX
    verisi, BST'de UTC+1) yine de kayabilir. Bu fonksiyon HER İKİ durumda da
    doğru sonucu garanti eder (borsanın kendi yerel takvim gününü baz alır,
    sabit bir ofset varsaymaz)."""
    if df.empty:
        return df
    corrected = df.copy()
    local = corrected.index.tz_convert(tz)
    local_dates = local.normalize().tz_localize(None)
    corrected.index = pd.DatetimeIndex(local_dates, name=corrected.index.name).tz_localize("UTC")
    return corrected


def validate_canonical_schema(df: pd.DataFrame, adapter_id: str) -> None:
    """Şema doğrulayıcı (EXPANSION.md Bölüm 15.4): kolonlar, tip, tz-aware
    index, index monotonik artan/yinelenmesiz. İhlalde ValueError — sessiz
    geçme yasak (CLAUDE.md BrokerAdapter felsefesiyle tutarlı)."""
    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{adapter_id}: kanonik kolonlar eksik: {missing}")
    if df.empty:
        return
    if df.index.tz is None:
        raise ValueError(f"{adapter_id}: index tz-aware değil")
    if not df.index.is_monotonic_increasing:
        raise ValueError(f"{adapter_id}: index monotonik artan değil")
    if df.index.duplicated().any():
        raise ValueError(f"{adapter_id}: index'te yinelenen tarih var")
    for c in CANONICAL_COLUMNS:
        if df[c].dtype.kind != "f":
            raise ValueError(f"{adapter_id}: '{c}' kolonu float64 değil (dtype={df[c].dtype})")

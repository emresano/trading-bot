# data/cleaning.py
"""Veri temizleme katmanı — YÜKLEME anında uygulanır, kaynak (snapshot/cache)
parquet dosyalarına DOKUNMAZ (yalnızca bellek-içi DataFrame'leri düzeltir).
DIAGNOSTICS_v6.md Paket 1'in iki bulgusunun düzeltmesi (v7 motor+veri turu):

(a) Hayalet-bar filtresi: bir tarih yalnızca TEK bir sembolde var, o barın
    volume'u 0 ve OHLC'si önceki kapanışla (göreli tolerans dahilinde) birebir
    aynıysa bu bar elenir — `backtest/engine.py`nin `all_dates` birleşiminin
    (tüm sembollerin tarihlerinin union'ı olduğundan) tek bir sahte satırı
    TÜM evren için "geçerli işlem günü" sayması engellenir.
(b) Tarih normalizasyonu: yfinance günlük barları Europe/Istanbul yerel gece
    yarısını temsil eder; UTC'ye instant-preserving tz_convert edildiğinde
    (Istanbul her zaman UTC'nin ilerisinde olduğundan) her barın TARİH
    ETİKETİ bir önceki UTC takvim gününe kayar. Bu düzeltilir.
"""
from __future__ import annotations
from typing import Callable

import pandas as pd

# OHLC'nin "önceki kapanışla birebir aynı" sayılması için göreli tolerans.
GHOST_BAR_RELATIVE_TOLERANCE = 1e-6


def normalize_bist_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Barın GERÇEK Istanbul takvim gününü UTC gece yarısı olarak yeniden
    etiketler (saat bilgisi zaten anlamsızdır — günlük bar tek bir takvim
    gününü temsil eder). Örnek: UTC "2024-04-08 21:00:00+00:00" ->
    Istanbul "2024-04-09 00:00:00+03:00" -> yeniden etiketlenmiş
    "2024-04-09 00:00:00+00:00". Boş DataFrame'i olduğu gibi döner."""
    if df.empty:
        return df
    corrected = df.copy()
    istanbul_local = corrected.index.tz_convert("Europe/Istanbul")
    istanbul_dates = istanbul_local.normalize().tz_localize(None)
    corrected.index = pd.DatetimeIndex(istanbul_dates, name=corrected.index.name).tz_localize("UTC")
    return corrected


def _is_ghost_bar(row: pd.Series, prev_close: float | None) -> bool:
    if prev_close is None or prev_close == 0 or float(row["volume"]) != 0:
        return False
    tol = GHOST_BAR_RELATIVE_TOLERANCE * max(abs(prev_close), 1.0)
    return all(abs(float(row[col]) - prev_close) <= tol for col in ("open", "high", "low", "close"))


def filter_ghost_bars(daily: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """`daily`: sembol -> (tarihleri zaten normalize edilmiş) günlük DataFrame.
    Tüm evren AYNI ANDA verilmelidir — "tarih yalnızca 1 sembolde var" kontrolü
    çapraz-sembol bilgisi gerektirir. Döner: (temizlenmiş sözlük, elenen
    barların logu [{symbol, date, reason}])."""
    dates_by_symbol = {s: set(df.index) for s, df in daily.items()}
    cleaned: dict[str, pd.DataFrame] = {}
    removed_log: list[dict] = []

    for symbol, df in daily.items():
        other_dates: set = set()
        for other_symbol, dates in dates_by_symbol.items():
            if other_symbol != symbol:
                other_dates |= dates

        rows_to_drop = []
        prev_close: float | None = None
        for date, row in df.iterrows():
            is_singleton = date not in other_dates
            if is_singleton and _is_ghost_bar(row, prev_close):
                rows_to_drop.append(date)
                removed_log.append({
                    "symbol": symbol,
                    "date": date,
                    "reason": "tek-sembolde-var + volume=0 + OHLC≈onceki_kapanis (hayalet bar)",
                })
            else:
                prev_close = float(row["close"])
        cleaned[symbol] = df.drop(index=rows_to_drop) if rows_to_drop else df

    return cleaned, removed_log


def load_and_clean_universe(
    symbols: list[str], loader: Callable[[str], pd.DataFrame]
) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """Tek giriş noktası: her sembolü `loader` ile oku, tarih normalizasyonu
    uygula, sonra TÜM evren üzerinde hayalet-bar filtresini çalıştır."""
    normalized = {s: normalize_bist_dates(loader(s)) for s in symbols}
    return filter_ghost_bars(normalized)

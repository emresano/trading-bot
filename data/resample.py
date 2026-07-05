# data/resample.py
from __future__ import annotations
import pandas as pd

from core.clock import TZ_ISTANBUL


def resample_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    """1h barları BIST seansına hizalı 4H barlara indirger (Bölüm 7.5).

    Istanbul saatinde 10:00 başlangıçlı gruplama (10:00-14:00, 14:00-18:00).
    Seans dışı boş dilimler tamamen atılır; seans içi ama eksik saat barı olan
    4H barları NaN bırakılır (quality katmanı bunu yakalar)."""
    if df_1h.empty:
        return df_1h

    local = df_1h.copy()
    local.index = local.index.tz_convert(TZ_ISTANBUL)

    resampler_kwargs = dict(rule="4h", origin="start_day", offset="10h")
    counts = local["close"].resample(**resampler_kwargs).count()
    resampled = local.resample(**resampler_kwargs).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )

    has_data = counts > 0
    resampled = resampled[has_data]
    counts = counts[has_data]

    incomplete = counts < 4
    resampled.loc[incomplete, ["open", "high", "low", "close", "volume"]] = float("nan")

    resampled.index = resampled.index.tz_convert("UTC")
    resampled.index.name = df_1h.index.name
    return resampled

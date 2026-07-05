# indicators/engine.py
from __future__ import annotations

import pandas as pd
import pandas_ta_classic as ta


def _col(result: pd.DataFrame, prefix: str) -> pd.Series:
    matches = [c for c in result.columns if c.startswith(prefix)]
    if not matches:
        raise KeyError(f"beklenen kolon bulunamadı: prefix={prefix!r}, mevcut={list(result.columns)}")
    return result[matches[0]]


def add_ema(df: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    df = df.copy()
    df[f"ema_{fast}"] = ta.ema(df["close"], length=fast)
    df[f"ema_{slow}"] = ta.ema(df["close"], length=slow)
    return df


def add_adx(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df = df.copy()
    result = ta.adx(df["high"], df["low"], df["close"], length=period)
    df["adx"] = _col(result, "ADX_")
    return df


def add_rsi(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df = df.copy()
    df["rsi"] = ta.rsi(df["close"], length=period)
    return df


def add_macd(df: pd.DataFrame, fast: int, slow: int, sig: int) -> pd.DataFrame:
    df = df.copy()
    result = ta.macd(df["close"], fast=fast, slow=slow, signal=sig)
    df["macd"] = _col(result, "MACD_")
    df["macd_signal"] = _col(result, "MACDs_")
    df["macd_hist"] = _col(result, "MACDh_")
    return df


def add_atr(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df = df.copy()
    atr = ta.atr(df["high"], df["low"], df["close"], length=period)
    df["atr"] = atr
    df["atr_ma20"] = atr.rolling(20).mean()
    return df


def add_bbands(df: pd.DataFrame, period: int, std: float) -> pd.DataFrame:
    df = df.copy()
    result = ta.bbands(df["close"], length=period, std=std)
    df["bb_low"] = _col(result, "BBL_")
    df["bb_mid"] = _col(result, "BBM_")
    df["bb_high"] = _col(result, "BBU_")
    df["bb_width"] = _col(result, "BBB_")
    return df


def add_swings(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Fraktal swing: swing_high[i]=True ise high[i] her iki yanındaki n barın
    high'ından büyük. İlk/son n bar için tanımsız (yeterli komşu yok / geleceğe
    bakamayız) → False."""
    df = df.copy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n_rows = len(df)

    swing_high = [False] * n_rows
    swing_low = [False] * n_rows
    for i in range(n, n_rows - n):
        left_h, right_h = high[i - n:i], high[i + 1:i + n + 1]
        left_l, right_l = low[i - n:i], low[i + 1:i + n + 1]
        if high[i] > left_h.max() and high[i] > right_h.max():
            swing_high[i] = True
        if low[i] < left_l.min() and low[i] < right_l.min():
            swing_low[i] = True

    df["swing_high"] = swing_high
    df["swing_low"] = swing_low
    return df


def add_support_resistance(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Son `lookback` bardaki swing seviyelerinden en yakın destek (altta) ve
    direnç (üstte). Kolonlar: nearest_support, nearest_resistance (float, yoksa NaN)."""
    df = df.copy()
    n_rows = len(df)
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    swing_high = df["swing_high"].to_numpy()
    swing_low = df["swing_low"].to_numpy()

    supports = [float("nan")] * n_rows
    resistances = [float("nan")] * n_rows
    for i in range(n_rows):
        start = max(0, i - lookback + 1)
        sup_candidates = [lows[j] for j in range(start, i + 1) if swing_low[j] and lows[j] < closes[i]]
        res_candidates = [highs[j] for j in range(start, i + 1) if swing_high[j] and highs[j] > closes[i]]
        if sup_candidates:
            supports[i] = max(sup_candidates)
        if res_candidates:
            resistances[i] = min(res_candidates)

    df["nearest_support"] = supports
    df["nearest_resistance"] = resistances
    return df


def add_volume_confirm(df: pd.DataFrame, mult: float) -> pd.DataFrame:
    """Kolon: vol_confirm (bool) = volume >= 20-bar SMA(volume) * mult"""
    df = df.copy()
    vol_sma20 = df["volume"].rolling(20).mean()
    df["vol_confirm"] = (df["volume"] >= vol_sma20 * mult).fillna(False)
    return df


def add_candle_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Elle implementasyon — pandas-ta'nın pattern modülüne güvenme (TA-Lib bağımlılığı var).
    Kolonlar: pat_engulf, pat_pin, pat_inside_break (bool)"""
    df = df.copy()
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    prev_o, prev_c = o.shift(1), c.shift(1)
    prev_h, prev_l = h.shift(1), l.shift(1)

    prev_red = prev_c < prev_o
    curr_green = c > o
    engulf = prev_red & curr_green & (o <= prev_c) & (c >= prev_o)
    df["pat_engulf"] = engulf.fillna(False)

    body = (c - o).abs()
    body_top = pd.concat([o, c], axis=1).max(axis=1)
    body_bottom = pd.concat([o, c], axis=1).min(axis=1)
    lower_wick = body_bottom - l
    upper_wick = h - body_top
    midpoint = (h + l) / 2
    pin = (lower_wick >= body * 2) & (upper_wick <= body * 0.5) & (c > midpoint)
    df["pat_pin"] = pin.fillna(False)

    mother_h, mother_l = h.shift(2), l.shift(2)
    is_inside_bar = (prev_h < mother_h) & (prev_l > mother_l)
    breakout = is_inside_bar & (c > prev_h)
    df["pat_inside_break"] = breakout.fillna(False)

    return df


# Genişletilebilirlik kaydı (Bölüm 17): yeni bir add_x() burada listelenir.
# NOT: build_features, farklı fonksiyon imzalarını (her add_x farklı config
# alanları alır) cfg.signal'den bağlayarak sırayla çağırır — bu liste,
# pipeline sırasının tek referans kaynağı olarak dokümantasyon amaçlıdır.
FEATURE_PIPELINE = [
    add_ema, add_adx, add_rsi, add_macd, add_atr,
    add_bbands, add_swings, add_support_resistance,
    add_volume_confirm, add_candle_patterns,
]


def build_features(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Pipeline'ı sırayla uygular. Girdi df'i mutate etmez (copy).
    Warm-up dönemi (ilk max(ema_slow, ...) bar) NaN kalır; huni bunları işlemez."""
    sc = cfg.signal
    out = df.copy()
    out = add_ema(out, sc.ema_fast, sc.ema_slow)
    out = add_adx(out, sc.adx_period)
    out = add_rsi(out, sc.rsi_period)
    out = add_macd(out, *sc.macd)
    out = add_atr(out, sc.atr_period)
    out = add_bbands(out, sc.bb_period, sc.bb_std)
    out = add_swings(out, sc.swing_fractal_n)
    out = add_support_resistance(out, sc.swing_lookback)
    out = add_volume_confirm(out, sc.volume_confirm_mult)
    out = add_candle_patterns(out)
    return out

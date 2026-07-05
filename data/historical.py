# data/historical.py
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

HISTORICAL_DIR = Path("data/historical")
GOLD_GRAM_DIVISOR = 31.1035  # 1 ons = 31.1035 gram

# Backtest veri katmanı AlgoLab'dan tamamen bağımsızdır (CLAUDE.md Bölüm 1).
_INTERVAL_MAP = {"1d": "1d", "1h": "1h", "4h": "1h"}  # 4h kaynak barı 1h'dir, resample edilir


def _cache_path(symbol: str, timeframe: str) -> Path:
    return HISTORICAL_DIR / f"{symbol}_{timeframe}.parquet"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=str.lower)
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index.name = "ts"
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df


def download_bars(yf_symbol: str, timeframe: str = "1d", start: Optional[str] = None) -> pd.DataFrame:
    interval = _INTERVAL_MAP.get(timeframe, timeframe)
    ticker = yf.Ticker(yf_symbol)
    # yfinance start=None verildiğinde varsayılan olarak yalnızca ~1 aylık veri döner;
    # "sınırsız geçmiş" (Bölüm 7.1) için start yoksa period="max" zorunlu.
    if start is None:
        df = ticker.history(interval=interval, period="max", auto_adjust=True)
    else:
        df = ticker.history(interval=interval, start=start, auto_adjust=True)
    if df.empty:
        return df
    return _normalize_columns(df)


def update_cache(symbol: str, yf_symbol: str, timeframe: str = "1d") -> pd.DataFrame:
    """Cache'i artımlı günceller: mevcut parquet'in son tarihinden itibaren çeker, birleştirir."""
    HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(symbol, timeframe)
    if path.exists():
        existing = pd.read_parquet(path)
        overlap_start = (existing.index[-1] - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
        fresh = download_bars(yf_symbol, timeframe, start=overlap_start)
        if not fresh.empty:
            combined = pd.concat([existing, fresh])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        else:
            combined = existing
    else:
        combined = download_bars(yf_symbol, timeframe, start=None)
    if not combined.empty:
        combined.to_parquet(path)
    return combined


def load_cached(symbol: str, timeframe: str = "1d") -> pd.DataFrame:
    path = _cache_path(symbol, timeframe)
    if not path.exists():
        return pd.DataFrame(columns=list(("open", "high", "low", "close", "volume")))
    return pd.read_parquet(path)


def build_gold_try_proxy() -> pd.DataFrame:
    """XAUUSD × USDTRY / 31.1035 -> gram altın TL serisi.
    Hacim sentetik (sıfır) — volume gate bu seride otomatik SKIP-PASS sayılır (Bölüm 7.1)."""
    gold_usd = download_bars("GC=F", "1d")
    if gold_usd.empty:
        gold_usd = download_bars("XAUUSD=X", "1d")
    usdtry = download_bars("USDTRY=X", "1d")
    if gold_usd.empty or usdtry.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    merged = gold_usd[["close"]].join(usdtry[["close"]], lsuffix="_gold", rsuffix="_try", how="inner")
    gram_try = merged["close_gold"] * merged["close_try"] / GOLD_GRAM_DIVISOR

    out = pd.DataFrame(index=merged.index)
    out["open"] = gram_try
    out["high"] = gram_try
    out["low"] = gram_try
    out["close"] = gram_try
    out["volume"] = 0
    out.index.name = "ts"
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Tarihsel veri cache doldurucu (backtest için)")
    parser.add_argument("--symbols", required=True, help="virgülle ayrılmış AlgoLab sembolleri, örn: THYAO,GARAN")
    parser.add_argument("--timeframe", default="1d")
    args = parser.parse_args()

    from core.config import load_config

    cfg = load_config()
    symbol_map = {i.symbol: i.yf_symbol for i in cfg.instruments}

    for raw_symbol in args.symbols.split(","):
        symbol = raw_symbol.strip()
        yf_symbol = symbol_map.get(symbol)
        if yf_symbol is None:
            print(f"UYARI: {symbol} config/config.yaml içinde tanımlı değil, atlanıyor")
            continue
        df = update_cache(symbol, yf_symbol, args.timeframe)
        last = df.index[-1] if not df.empty else "yok"
        print(f"{symbol}: {len(df)} bar, son tarih {last}")


if __name__ == "__main__":
    main()

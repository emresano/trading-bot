# tests/test_cleaning_fx.py
"""FX OHLC onarımı testleri (EXPANSION.md Bölüm 6 / DATA_AUDIT_FX.md E2 notu)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data.cleaning import repair_fx_ohlc
from data.quality import check_quality

FX_SNAPSHOT = Path("data/snapshots/fx/2026-07-06")


def test_repair_synthetic_close_above_high():
    idx = pd.to_datetime(["2010-07-01", "2010-07-02"], utc=True)
    df = pd.DataFrame({
        "open": [1.223, 1.25], "high": [1.224, 1.26], "low": [1.219, 1.24],
        "close": [1.2508, 1.255], "volume": [0.0, 0.0],
    }, index=idx)  # 1. satır: close 1.2508 > high 1.224 → ihlal
    repaired, log = repair_fx_ohlc(df, "EUR_USD")
    assert len(log) == 1
    assert log[0]["date"] == idx[0]
    # onarım sonrası OHLC tutarlı
    r = repaired.iloc[0]
    assert r["high"] >= max(r["open"], r["close"])
    assert r["low"] <= min(r["open"], r["close"])
    # close korundu
    assert repaired["close"].tolist() == df["close"].tolist()


def test_repair_noop_when_consistent():
    idx = pd.to_datetime(["2020-01-01"], utc=True)
    df = pd.DataFrame({"open": [1.1], "high": [1.12], "low": [1.09], "close": [1.11], "volume": [0.0]}, index=idx)
    repaired, log = repair_fx_ohlc(df, "EUR_USD")
    assert log == []
    assert repaired.equals(df)


def test_repair_makes_quality_pass():
    """Onarım öncesi check_quality FAIL, sonrası PASS (Bölüm 7.2 OHLC kontrolü)."""
    idx = pd.to_datetime(["2010-06-30", "2010-07-01"], utc=True)
    df = pd.DataFrame({
        "open": [1.223, 1.2232], "high": [1.224, 1.2243], "low": [1.219, 1.2199],
        "close": [1.220, 1.2508], "volume": [1.0, 1.0],
    }, index=idx)
    assert check_quality(df).passed is False  # close>high FAIL
    repaired, log = repair_fx_ohlc(df, "EUR_USD")
    assert len(log) == 1
    assert check_quality(repaired).passed is True


@pytest.mark.skipif(not (FX_SNAPSHOT / "EUR_USD.parquet").exists(), reason="FX snapshot yok")
def test_real_snapshot_2010_07_01_repaired():
    """DATA_AUDIT_FX.md: EUR_USD & GBP_USD 2010-07-01 close>high — onarılır."""
    for symbol in ("EUR_USD", "GBP_USD"):
        df = pd.read_parquet(FX_SNAPSHOT / f"{symbol}.parquet")
        repaired, log = repair_fx_ohlc(df, symbol)
        # 2010-07-01 barı onarım logunda olmalı
        dates = {pd.Timestamp(e["date"]).date().isoformat() for e in log}
        assert "2010-07-01" in dates, f"{symbol}: 2010-07-01 onarılmadı, log={dates}"
        # onarım sonrası o bar tutarlı
        row = repaired.loc[repaired.index.date == pd.Timestamp("2010-07-01").date()].iloc[0]
        assert row["high"] >= row["close"] and row["low"] <= row["close"]

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from data.quality import check_quality

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> pd.DataFrame:
    df = pd.read_csv(FIXTURES / name, parse_dates=["ts"], index_col="ts")
    df.index = df.index.tz_localize("UTC")
    return df


def test_good_data_passes_with_no_warnings():
    result = check_quality(_load("quality_good.csv"))
    assert result.passed
    assert result.errors == []
    assert result.warnings == []
    assert len(result.cleaned_df) == 8


def test_nan_in_middle_fails():
    result = check_quality(_load("quality_nan_middle.csv"))
    assert not result.passed
    assert any("NaN" in e for e in result.errors)


def test_leading_nan_is_dropped_as_warmup():
    result = check_quality(_load("quality_leading_nan.csv"))
    assert result.passed
    assert len(result.cleaned_df) == 6
    assert not result.cleaned_df.isna().any().any()


def test_ohlc_violation_fails():
    result = check_quality(_load("quality_ohlc_violation.csv"))
    assert not result.passed
    assert any("tutars" in e.lower() for e in result.errors)


def test_duplicate_index_fails():
    result = check_quality(_load("quality_duplicate_index.csv"))
    assert not result.passed
    assert any("duplicate" in e.lower() for e in result.errors)


def test_non_monotonic_index_fails():
    df = _load("quality_good.csv").iloc[::-1]
    result = check_quality(df)
    assert not result.passed
    assert any("monoton" in e.lower() for e in result.errors)


def test_price_jump_warns_but_passes():
    result = check_quality(_load("quality_price_jump.csv"))
    assert result.passed
    assert any("sıçrama" in w for w in result.warnings)


def test_stale_data_fails():
    df = _load("quality_good.csv")
    far_future = df.index[-1].to_pydatetime() + timedelta(days=30)
    result = check_quality(df, max_staleness=timedelta(days=1), now=far_future)
    assert not result.passed
    assert any("eski" in e for e in result.errors)


def test_missing_columns_fail():
    df = _load("quality_good.csv").drop(columns=["volume"])
    result = check_quality(df)
    assert not result.passed
    assert any("eksik kolon" in e for e in result.errors)


def test_empty_dataframe_fails():
    result = check_quality(pd.DataFrame(columns=["open", "high", "low", "close", "volume"]))
    assert not result.passed


# --- OHLC toleransı: kayan nokta gürültüsü gerçek veri sorunu sayılmamalı ---

def _synthetic_ohlc_df(high_offset: float) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    close = [100.0, 101.0, 102.0, 103.0, 104.0]
    open_ = [99.5, 100.5, 101.5, 102.5, 103.5]
    high = [c + high_offset for c in close]  # high = close + offset (negatifse ihlal)
    low = [o - 0.5 for o in open_]
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                        "volume": [1000.0] * 5}, index=idx)


def test_ohlc_epsilon_level_float_noise_passes():
    # high, close'dan yalnızca kayan nokta epsilon'u kadar küçük (auto_adjust
    # kaynaklı yuvarlama gürültüsü) — gerçek bir veri sorunu değil.
    df = _synthetic_ohlc_df(high_offset=-1e-13)
    result = check_quality(df)
    assert result.passed


def test_ohlc_small_relative_noise_within_tolerance_passes():
    # ~%0.3'lük bir sapma (varsayılan rtol=%0.5 içinde) tolere edilmeli.
    df = _synthetic_ohlc_df(high_offset=-0.3)
    result = check_quality(df)
    assert result.passed


def test_ohlc_violation_beyond_tolerance_still_fails():
    # ~%5'lik bir sapma, varsayılan rtol=%0.5'i çok aşıyor — gerçek bir ihlal.
    df = _synthetic_ohlc_df(high_offset=-5.0)
    result = check_quality(df)
    assert not result.passed
    assert any("tutars" in e.lower() for e in result.errors)

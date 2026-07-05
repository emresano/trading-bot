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

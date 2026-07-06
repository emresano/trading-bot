import pandas as pd
import pytest

from data.adapters.base import (
    CANONICAL_COLUMNS,
    AdapterMeta,
    relabel_to_local_calendar_day,
    validate_canonical_schema,
)


def _valid_df(idx) -> pd.DataFrame:
    n = len(idx)
    return pd.DataFrame({
        "open": [1.0] * n, "high": [1.1] * n, "low": [0.9] * n,
        "close": [1.05] * n, "volume": [100.0] * n,
    }, index=idx)


def test_relabel_handles_positive_offset_shift_like_istanbul():
    """UTC+ (Istanbul benzeri) bir tz: yerel gece yarısı önceki UTC takvim
    gününe denk gelir — relabel bunu düzeltmeli (v7'nin bulduğu bug deseni)."""
    idx = pd.to_datetime(["2024-04-07 21:00:00", "2024-04-08 21:00:00"], utc=True)
    df = _valid_df(idx)
    corrected = relabel_to_local_calendar_day(df, "Europe/Istanbul")
    assert list(corrected.index.strftime("%Y-%m-%d")) == ["2024-04-08", "2024-04-09"]


def test_relabel_handles_negative_offset_no_shift_like_new_york():
    """UTC- (New York benzeri) bir tz: yerel gece yarısı AYNI UTC takvim
    gününde kalır — relabel hiçbir şeyi değiştirmemeli."""
    idx = pd.to_datetime(["2024-01-02 00:00:00-05:00", "2024-01-03 00:00:00-05:00"])
    df = _valid_df(idx)
    corrected = relabel_to_local_calendar_day(df, "America/New_York")
    assert list(corrected.index.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"]


def test_relabel_handles_dst_transition_for_london():
    """Europe/London: kışın UTC+0 (kayma yok), yazın UTC+1 (BST, kayma var) —
    relabel her iki rejimde de doğru takvim gününü üretmeli."""
    idx = pd.to_datetime(["2024-01-02 00:00:00+00:00", "2024-07-02 23:00:00+00:00"], utc=True)
    df = _valid_df(idx)
    corrected = relabel_to_local_calendar_day(df, "Europe/London")
    # 2024-01-02 00:00 UTC -> Londra kışın UTC+0 -> aynı gün
    # 2024-07-02 23:00 UTC -> Londra yazın UTC+1 -> 2024-07-03 00:00 yerel -> 07-03
    assert list(corrected.index.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-07-03"]


def test_relabel_empty_df_returns_unchanged():
    df = pd.DataFrame(columns=CANONICAL_COLUMNS)
    result = relabel_to_local_calendar_day(df, "America/New_York")
    assert result.empty


def test_validate_canonical_schema_passes_for_valid_df():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    df = _valid_df(idx)
    validate_canonical_schema(df, "test_adapter")  # exception atmamalı


def test_validate_canonical_schema_empty_df_passes():
    df = pd.DataFrame(columns=CANONICAL_COLUMNS)
    validate_canonical_schema(df, "test_adapter")


def test_validate_canonical_schema_rejects_missing_column():
    idx = pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")
    df = pd.DataFrame({"open": [1.0, 1.0], "high": [1.0, 1.0], "low": [1.0, 1.0], "close": [1.0, 1.0]}, index=idx)
    with pytest.raises(ValueError, match="eksik"):
        validate_canonical_schema(df, "test_adapter")


def test_validate_canonical_schema_rejects_naive_index():
    idx = pd.date_range("2024-01-01", periods=2, freq="1D")  # tz yok
    df = _valid_df(idx)
    with pytest.raises(ValueError, match="tz-aware"):
        validate_canonical_schema(df, "test_adapter")


def test_validate_canonical_schema_rejects_duplicate_dates():
    idx = pd.to_datetime(["2024-01-01", "2024-01-01"], utc=True)
    df = _valid_df(idx)
    with pytest.raises(ValueError, match="yinelenen"):
        validate_canonical_schema(df, "test_adapter")


def test_validate_canonical_schema_rejects_non_monotonic_index():
    idx = pd.to_datetime(["2024-01-02", "2024-01-01"], utc=True)
    df = _valid_df(idx)
    with pytest.raises(ValueError, match="monotonik"):
        validate_canonical_schema(df, "test_adapter")


def test_validate_canonical_schema_rejects_non_float_column():
    idx = pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")
    df = _valid_df(idx)
    df["volume"] = [100, 200]  # int, float değil
    with pytest.raises(ValueError, match="float64"):
        validate_canonical_schema(df, "test_adapter")


def test_adapter_meta_defaults():
    meta = AdapterMeta(adapter_id="test", source="test-source")
    assert meta.download_params == {}
    assert meta.volume_kind == "shares"

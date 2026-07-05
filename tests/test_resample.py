import pandas as pd

from data.resample import resample_to_4h


def _bar(o, h, l, c, v):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def test_full_session_produces_two_complete_4h_bars():
    # 2024-01-02 Salı, Istanbul saatiyle 10:00-18:00 arası 8 saatlik bar (UTC = Istanbul-3h)
    idx = pd.date_range("2024-01-02 07:00", periods=8, freq="1h", tz="UTC")
    rows = [_bar(100 + i, 101 + i, 99 + i, 100.5 + i, 1000 + i) for i in range(8)]
    df = pd.DataFrame(rows, index=idx)
    df.index.name = "ts"

    out = resample_to_4h(df)
    assert len(out) == 2
    assert not out.isna().any().any()
    # ilk 4H bar: open=ilk barın open'ı, close=4. barın close'u
    assert out.iloc[0]["open"] == 100
    assert out.iloc[0]["close"] == 103.5
    assert out.iloc[0]["high"] == 104
    assert out.iloc[0]["low"] == 99


def test_missing_hour_leaves_4h_bar_nan():
    idx = pd.date_range("2024-01-02 07:00", periods=8, freq="1h", tz="UTC")
    rows = [_bar(100 + i, 101 + i, 99 + i, 100.5 + i, 1000 + i) for i in range(8)]
    df = pd.DataFrame(rows, index=idx)
    df.index.name = "ts"
    df = df.drop(df.index[1])  # ilk 4H dilimindeki bir saati eksik bırak

    out = resample_to_4h(df)
    assert len(out) == 2
    assert out.iloc[0].isna().all()
    assert not out.iloc[1].isna().any()


def test_off_hours_bins_are_dropped_not_nan_padded():
    idx = pd.date_range("2024-01-02 07:00", periods=8, freq="1h", tz="UTC")
    rows = [_bar(100 + i, 101 + i, 99 + i, 100.5 + i, 1000 + i) for i in range(8)]
    df = pd.DataFrame(rows, index=idx)
    df.index.name = "ts"

    out = resample_to_4h(df)
    # seans dışı (18:00-10:00 Istanbul) dilimler için satır üretilmemeli
    assert len(out) == 2


def test_empty_input_returns_empty():
    df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = resample_to_4h(df)
    assert out.empty

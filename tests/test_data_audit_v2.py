import pandas as pd

from tools.data_audit_v2 import (
    _to_istanbul_midnight_utc,
    classify_jump,
    find_jumps,
    trade_within_bars,
)


def test_find_jumps_flags_only_days_at_or_above_threshold():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    close = [100.0, 100.0, 111.0, 111.0, 95.0]  # gün3: +11%, gün5: ~-14.4%
    volume = [1000.0] * 5
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": volume}, index=idx)
    jumps = find_jumps(df, threshold=0.10)
    assert len(jumps) == 2
    assert set(jumps["date"]) == {idx[2], idx[4]}


def test_find_jumps_empty_when_no_jump_exceeds_threshold():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    close = [100.0, 101.0, 102.0, 101.0, 100.0]
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close,
                       "volume": [1000.0] * 5}, index=idx)
    jumps = find_jumps(df, threshold=0.10)
    assert jumps.empty


def test_classify_jump_recognizes_recorded_corporate_action():
    jump_date = pd.Timestamp("2005-05-17", tz="UTC")
    raw = pd.DataFrame({
        "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1000],
        "Dividends": [0.143002], "Stock Splits": [1.257858],
    }, index=[jump_date])
    assert classify_jump(jump_date, raw, vol_ratio=1.0) == "kayıtlı kurumsal işlem"


def test_classify_jump_volume_supported_when_no_corp_action():
    jump_date = pd.Timestamp("2024-01-01", tz="UTC")
    raw = pd.DataFrame({
        "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1000],
        "Dividends": [0.0], "Stock Splits": [0.0],
    }, index=[jump_date])
    assert classify_jump(jump_date, raw, vol_ratio=2.5) == "hacim destekli gerçek hareket"


def test_classify_jump_unexplained_when_no_corp_action_and_low_volume():
    jump_date = pd.Timestamp("2024-01-01", tz="UTC")
    raw = pd.DataFrame({
        "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1000],
        "Dividends": [0.0], "Stock Splits": [0.0],
    }, index=[jump_date])
    assert classify_jump(jump_date, raw, vol_ratio=1.0) == "açıklanamayan gap (muhtemel bedelli)"
    assert classify_jump(jump_date, raw, vol_ratio=None) == "açıklanamayan gap (muhtemel bedelli)"


def test_classify_jump_checks_neighboring_day_for_corp_action():
    """Tarih normalizasyonundaki olası ±1 günlük belirsizliğe karşı tolerans."""
    jump_date = pd.Timestamp("2005-05-17", tz="UTC")
    raw = pd.DataFrame({
        "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1000],
        "Dividends": [0.143002], "Stock Splits": [0.0],
    }, index=[pd.Timestamp("2005-05-18", tz="UTC")])  # bir gün kaymış kayıt
    assert classify_jump(jump_date, raw, vol_ratio=1.0) == "kayıtlı kurumsal işlem"


def test_to_istanbul_midnight_utc_matches_normalize_bist_dates_convention():
    from data.cleaning import normalize_bist_dates
    idx = pd.to_datetime(["2024-04-08 21:00:00"], utc=True)  # UTC etiketi, gerçek Istanbul günü 04-09
    df = pd.DataFrame({"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [100.0]}, index=idx)
    normalized = normalize_bist_dates(df)
    assert _to_istanbul_midnight_utc(idx[0]) == normalized.index[0]


def test_trade_within_bars_true_when_entry_within_window():
    idx = pd.date_range("2024-01-01", periods=20, freq="1D", tz="UTC")
    df = pd.DataFrame({"close": range(20)}, index=idx)
    jump_date = idx[10]
    trades = pd.DataFrame([
        {"symbol": "TEST", "entry_date": idx[8].isoformat(), "exit_date": idx[9].isoformat()},
    ])
    assert trade_within_bars("TEST", jump_date, df, trades, window=5) is True


def test_trade_within_bars_false_when_outside_window_or_different_symbol():
    idx = pd.date_range("2024-01-01", periods=20, freq="1D", tz="UTC")
    df = pd.DataFrame({"close": range(20)}, index=idx)
    jump_date = idx[10]
    trades = pd.DataFrame([
        {"symbol": "TEST", "entry_date": idx[0].isoformat(), "exit_date": idx[1].isoformat()},  # çok uzak
        {"symbol": "OTHER", "entry_date": idx[10].isoformat(), "exit_date": idx[10].isoformat()},  # farklı sembol
    ])
    assert trade_within_bars("TEST", jump_date, df, trades, window=5) is False


def test_trade_within_bars_false_when_no_trades_for_symbol():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    df = pd.DataFrame({"close": range(5)}, index=idx)
    trades = pd.DataFrame(columns=["symbol", "entry_date", "exit_date"])
    assert trade_within_bars("TEST", idx[2], df, trades) is False

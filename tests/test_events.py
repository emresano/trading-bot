import pandas as pd
import pytest

from data.events import EventCalendar, _infer_session


def test_infer_session_before_open_is_bmo():
    ts = pd.Timestamp("2024-01-02 07:00:00", tz="America/New_York")
    assert _infer_session(ts) == "bmo"


def test_infer_session_after_close_is_amc():
    ts = pd.Timestamp("2024-01-02 16:00:00", tz="America/New_York")
    assert _infer_session(ts) == "amc"


def test_infer_session_midday_is_unknown():
    ts = pd.Timestamp("2024-01-02 12:00:00", tz="America/New_York")
    assert _infer_session(ts) == "unknown"


def test_infer_session_naive_timestamp_is_unknown():
    ts = pd.Timestamp("2024-01-02 16:00:00")
    assert _infer_session(ts) == "unknown"


def test_infer_session_boundary_930_is_not_bmo():
    ts = pd.Timestamp("2024-01-02 09:30:00", tz="America/New_York")
    assert _infer_session(ts) == "unknown"


def test_is_blackout_no_data_falls_back_no_veto(tmp_path):
    """Bölüm 10.4 fallback: veri yoksa (False, açıklama) — backtest vetosuz koşar."""
    cal = EventCalendar(events_dir=tmp_path)
    blocked, reason = cal.is_blackout("us", "AAPL", pd.Timestamp("2024-01-01").date())
    assert blocked is False
    assert "earnings verisi yok" in reason


def test_bist_market_has_no_deterministic_veto():
    cal = EventCalendar()
    blocked, reason = cal.is_blackout("bist", "THYAO", pd.Timestamp("2024-01-01").date())
    assert blocked is False and "bist" in reason


def _write_earnings(tmp_path, symbol, dates):
    df = pd.DataFrame({"announce_date": pd.to_datetime(dates)})
    df.to_parquet(tmp_path / f"earnings_{symbol}.parquet")


def test_earnings_blackout_window_and_boundaries(tmp_path):
    from data.events import EarningsRule
    _write_earnings(tmp_path, "AAPL", ["2024-07-25"])  # announce
    cal = EventCalendar(events_dir=tmp_path,
                        earnings_rule=EarningsRule(enabled=True, days_before=3, days_after=1))
    d = lambda s: pd.Timestamp(s).date()
    # pencere: [07-22, 07-26]
    assert cal.is_blackout("us", "AAPL", d("2024-07-22"))[0] is True   # T-3 sınır
    assert cal.is_blackout("us", "AAPL", d("2024-07-25"))[0] is True   # T0
    assert cal.is_blackout("us", "AAPL", d("2024-07-26"))[0] is True   # T+1 sınır
    assert cal.is_blackout("us", "AAPL", d("2024-07-21"))[0] is False  # T-4 dışında
    assert cal.is_blackout("us", "AAPL", d("2024-07-27"))[0] is False  # T+2 dışında
    # reason formatı
    blocked, reason = cal.is_blackout("us", "AAPL", d("2024-07-23"))
    assert blocked and "earnings 2024-07-25" in reason and "T-2" in reason


def test_earnings_disabled_rule(tmp_path):
    from data.events import EarningsRule
    _write_earnings(tmp_path, "AAPL", ["2024-07-25"])
    cal = EventCalendar(events_dir=tmp_path, earnings_rule=EarningsRule(enabled=False))
    assert cal.is_blackout("us", "AAPL", pd.Timestamp("2024-07-25").date())[0] is False


def test_econ_blackout_no_history_fallback(tmp_path):
    cal = EventCalendar(events_dir=tmp_path)
    blocked, reason = cal.is_blackout("fx", "EUR_USD", pd.Timestamp("2024-07-25").date())
    assert blocked is False and "econ takvim verisi yok" in reason


def test_econ_blackout_currency_and_window(tmp_path):
    from data.events import EconRule
    econ = pd.DataFrame({
        "ts_utc": [pd.Timestamp("2024-07-25 12:00:00", tz="UTC")],
        "impact": ["high"],
        "currencies": [["USD"]],
    })
    econ.to_parquet(tmp_path / "econ_calendar.parquet")
    cal = EventCalendar(events_dir=tmp_path,
                        econ_rule=EconRule(enabled=True, impact="high", hours_before=12, hours_after=12))
    d = lambda s: pd.Timestamp(s).date()
    # USD etkileniyor → EUR_USD ve USD_JPY blackout; EUR_GBP değil
    assert cal.is_blackout("fx", "EUR_USD", d("2024-07-25"))[0] is True
    assert cal.is_blackout("fx", "USD_JPY", d("2024-07-25"))[0] is True
    assert cal.is_blackout("fx", "EUR_GBP", d("2024-07-25"))[0] is False   # USD yok
    # pencere dışı gün (2 gün sonra) → serbest
    assert cal.is_blackout("fx", "EUR_USD", d("2024-07-28"))[0] is False

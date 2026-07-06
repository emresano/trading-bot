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


def test_event_calendar_is_blackout_not_yet_implemented():
    cal = EventCalendar()
    with pytest.raises(NotImplementedError):
        cal.is_blackout("us", "AAPL", pd.Timestamp("2024-01-01").date())

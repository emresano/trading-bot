# tests/test_bist_calendar.py
"""F5A-9 — BIST seans/takvim testleri (B1). Config otoriter, kütüphane değil."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from core.bist_calendar import BistCalendar

TZ = ZoneInfo("Europe/Istanbul")


@pytest.fixture
def cal():
    return BistCalendar()


def test_verified_session_hours(cal):
    assert cal.continuous_start.strftime("%H:%M") == "10:00"
    assert cal.continuous_end.strftime("%H:%M") == "18:00"
    assert cal.opening_auction_start.strftime("%H:%M") == "09:40"
    assert cal.closing_auction_end.strftime("%H:%M") == "18:10"


def test_2026_holidays_closed(cal):
    for d in [date(2026, 1, 1), date(2026, 4, 23), date(2026, 5, 1),
              date(2026, 5, 19), date(2026, 10, 29), date(2026, 5, 27)]:
        assert not cal.is_trading_day(d), d


def test_normal_weekday_open(cal):
    assert cal.is_trading_day(date(2026, 6, 3))   # sıradan Çarşamba
    assert not cal.is_trading_day(date(2026, 6, 6))  # Cumartesi


def test_half_day_shortened_session(cal):
    hd = date(2026, 3, 19)   # Ramazan Arefesi
    assert cal.is_half_day(hd)
    assert cal.continuous_end_for(hd).strftime("%H:%M") == "12:40"
    assert cal.continuous_end_for(date(2026, 6, 3)).strftime("%H:%M") == "18:00"


def test_continuous_session_window(cal):
    d = date(2026, 6, 3)
    assert not cal.is_continuous_session(datetime(2026, 6, 3, 9, 45, tzinfo=TZ))   # müzayede
    assert cal.is_continuous_session(datetime(2026, 6, 3, 11, 0, tzinfo=TZ))       # sürekli
    assert not cal.is_continuous_session(datetime(2026, 6, 3, 18, 5, tzinfo=TZ))   # kapanış seansı
    assert cal.is_auction_window(datetime(2026, 6, 3, 9, 45, tzinfo=TZ))
    assert cal.is_auction_window(datetime(2026, 6, 3, 18, 5, tzinfo=TZ))


def test_half_day_continuous_session_ends_early(cal):
    hd = datetime(2026, 3, 19, 13, 0, tzinfo=TZ)   # yarım gün, 12:40 sonrası
    assert not cal.is_continuous_session(hd)
    assert cal.is_continuous_session(datetime(2026, 3, 19, 11, 0, tzinfo=TZ))


def test_missing_data_days_flags_and_logs(cal):
    logs = []
    c = BistCalendar(logger=logs.append)
    # 2026-06-01..03 arası işlem günleri; veride yalnız 1 ve 3 var → 2 eksik
    available = [date(2026, 6, 1), date(2026, 6, 3)]
    missing = c.missing_data_days(available, date(2026, 6, 1), date(2026, 6, 3))
    assert date(2026, 6, 2) in missing
    assert any("VERİ-YOK" in m for m in logs)


def test_reconcile_with_library_detects_admin_bridge(tmp_path):
    """config'e kütüphanede OLMAYAN bir idari-izin köprüsü eklenirse uyuşmazlık
    raporlanır (kütüphane tek otorite değil)."""
    import yaml
    base = yaml.safe_load((__import__("pathlib").Path("config/bist_calendar.yaml")).read_text())
    base["admin_leave_bridges_2026"] = [{"date": "2026-07-16", "name": "test köprü"}]
    p = tmp_path / "cal.yaml"
    p.write_text(yaml.safe_dump(base, allow_unicode=True))
    logs = []
    c = BistCalendar(p, logger=logs.append)
    disc = c.reconcile_with_library(date(2026, 7, 16), date(2026, 7, 16))
    # 2026-07-16 Perşembe: kütüphane açık sayar, config kapalı → uyuşmazlık
    assert len(disc) == 1 and disc[0]["config_trading"] is False
    assert any("TAKVİM UYUŞMAZLIĞI" in m for m in logs)

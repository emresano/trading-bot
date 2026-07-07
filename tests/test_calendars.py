# tests/test_calendars.py
"""Takvim / DST testleri (EXPANSION.md Bölüm 15.2).

NOT — v6 hayalet-bar tarihi tutarsızlığı (dürüst kayıt): EXPANSION.md 15.2 bu
tarihi 2024-04-08, E2 talimatı ise 2024-04-09 olarak anıyor VE "XIST'te işlem
günü DEĞİL" varsayıyor. Gerçek: `exchange_calendars` 4.13.2'ye göre 2024 Ramazan
Bayramı XIST tatilleri **2024-04-10/11/12**'dir; 2024-04-08 ve 2024-04-09 GERÇEK
işlem günleridir (arife). Repo'daki gerçek hayalet bar EREGL 2024-04-09'dur ve
bir `volume=0` phantom bar'dır (data/cleaning.py'nin çapraz-sembol+hacim
sezgiseli yakalar) — takvim katmanının yakaladığı sınıf DEĞİL. Dolayısıyla
takvim katmanı 2024-04-09'u haklı olarak işaretlemez; bu iki mekanizma FARKLI
hata sınıfları içindir (bkz. data/quality.py Bölüm-5 notu). Test aşağıda GERÇEK
tatilleri (2024-04-10..12) çapa alır.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from core.calendars import MarketCalendar, get_calendar


# ---------------------------------------------------------------- XNYS DST
def test_xnys_dst_close_shift():
    """DST geçişi kapanış UTC anını kaydırır (16:00 ET → yazın 20:00, kışın 21:00 UTC)."""
    xnys = get_calendar("XNYS")
    # 2024-03-08 hâlâ EST (kış): 16:00 ET = 21:00 UTC
    assert xnys.close_dt_utc(date(2024, 3, 8)) == datetime(2024, 3, 8, 21, 0, tzinfo=timezone.utc)
    # 2024-03-11 artık EDT (yaz): 16:00 ET = 20:00 UTC
    assert xnys.close_dt_utc(date(2024, 3, 11)) == datetime(2024, 3, 11, 20, 0, tzinfo=timezone.utc)
    # Kasım geçişi: 11-01 EDT (20:00 UTC), 11-04 EST (21:00 UTC)
    assert xnys.close_dt_utc(date(2024, 11, 1)) == datetime(2024, 11, 1, 20, 0, tzinfo=timezone.utc)
    assert xnys.close_dt_utc(date(2024, 11, 4)) == datetime(2024, 11, 4, 21, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------- XIST tatiller
def test_xist_known_holidays_not_trading():
    xist = get_calendar("XIST")
    # 2024 Ramazan Bayramı (gerçek XIST tatilleri):
    assert xist.is_trading_day(date(2024, 4, 10)) is False
    assert xist.is_trading_day(date(2024, 4, 11)) is False
    assert xist.is_trading_day(date(2024, 4, 12)) is False
    # Sabit resmî tatiller:
    assert xist.is_trading_day(date(2024, 1, 1)) is False   # yılbaşı
    assert xist.is_trading_day(date(2024, 5, 1)) is False    # emek/dayanışma günü


def test_xist_ghost_bar_date_is_actually_a_session():
    """Dürüst çapa: repo'daki gerçek hayalet bar tarihi (EREGL 2024-04-09) XIST'te
    GERÇEK bir işlem günüdür — takvim katmanı bunu işaretlemez; onu data/cleaning.py
    yakalar (spec'in 2024-04-08/09'u 'tatil' sayan varsayımı hatalıdır)."""
    xist = get_calendar("XIST")
    assert xist.is_trading_day(date(2024, 4, 9)) is True
    assert xist.is_trading_day(date(2024, 4, 8)) is True


def test_xist_weekend_not_trading():
    xist = get_calendar("XIST")
    assert xist.is_trading_day(date(2024, 6, 8)) is False   # Cumartesi
    assert xist.is_trading_day(date(2024, 6, 9)) is False   # Pazar


# ---------------------------------------------------------------- FX_24_5
def test_fx_saturday_sunday_no_bar():
    fx = get_calendar("FX_24_5")
    assert fx.is_trading_day(date(2024, 6, 8)) is False   # Cumartesi
    assert fx.is_trading_day(date(2024, 6, 9)) is False   # Pazar
    assert fx.is_trading_day(date(2024, 6, 10)) is True   # Pazartesi
    assert fx.is_trading_day(date(2024, 6, 14)) is True   # Cuma


def test_fx_close_dst_aware():
    """FX günlük kapanışı 17:00 NY — DST otomatik (yazın 21:00, kışın 22:00 UTC)."""
    fx = get_calendar("FX_24_5")
    # 2024-01-15 EST: 17:00 ET = 22:00 UTC
    assert fx.close_dt_utc(date(2024, 1, 15)) == datetime(2024, 1, 15, 22, 0, tzinfo=timezone.utc)
    # 2024-07-15 EDT: 17:00 ET = 21:00 UTC
    assert fx.close_dt_utc(date(2024, 7, 15)) == datetime(2024, 7, 15, 21, 0, tzinfo=timezone.utc)


def test_fx_year_boundary_trading_dates():
    fx = get_calendar("FX_24_5")
    # 2024-12-30 (Pzt), 12-31 (Sal), 2025-01-01 (Çar), 01-02 (Per), 01-03 (Cum) hepsi weekday
    dates = fx.trading_dates(date(2024, 12, 28), date(2025, 1, 5))
    assert date(2024, 12, 28) not in dates  # Cumartesi
    assert date(2024, 12, 30) in dates
    assert date(2025, 1, 1) in dates        # FX modeli resmî tatil tanımaz (Bölüm 5)
    assert date(2025, 1, 4) not in dates    # Cumartesi


# ---------------------------------------------------------------- next_eval + hatalar
def test_next_eval_skips_weekend():
    fx = get_calendar("FX_24_5")
    # Cuma kapanışından sonra → Pazartesi kapanışı
    friday_after_close = datetime(2024, 6, 14, 22, 0, tzinfo=timezone.utc)
    nxt = fx.next_eval_dt_utc(friday_after_close)
    assert nxt.astimezone(timezone.utc).date() == date(2024, 6, 17)  # Pazartesi


def test_close_on_non_session_raises():
    xist = get_calendar("XIST")
    with pytest.raises(ValueError):
        xist.close_dt_utc(date(2024, 4, 10))  # tatil


def test_unsupported_calendar_raises():
    with pytest.raises(ValueError, match="Desteklenmeyen"):
        MarketCalendar("NASDAQ_FOO")


# ---------------------------------------------------------------- clock delegasyonu
def test_clock_is_trading_day_delegates_to_xist():
    """core/clock.py API'si korunur ama artık tatil-farkındalıklı (Bölüm 5)."""
    from core.clock import is_trading_day
    assert is_trading_day(datetime(2024, 4, 10, 12, 0, tzinfo=timezone.utc)) is False  # Bayram
    assert is_trading_day(datetime(2024, 6, 10, 12, 0, tzinfo=timezone.utc)) is True   # normal Pzt
    assert is_trading_day(datetime(2024, 6, 8, 12, 0, tzinfo=timezone.utc)) is False   # Cumartesi

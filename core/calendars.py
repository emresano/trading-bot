# core/calendars.py
"""Piyasa takvimleri (EXPANSION.md Bölüm 5).

- XIST / XNYS: `exchange_calendars` kütüphanesi (resmî tatil + DST farkındalıklı).
- FX_24_5: kütüphanesiz özel takvim — işlem günü kapanışı 17:00 America/New_York;
  Cumartesi/Pazar günlük barı yok (Pazar akşamı 17:00 NY sonrası açılan işlem
  Pazartesi barına aittir); haftanın ilk günlük barı Pazartesi 17:00 NY kapanışı.

DST kuralı (mutlak, Bölüm 5): sabit saat farkı hard-code YASAK. XIST/XNYS için
`exchange_calendars` kapanış anlarını doğru kaydırır; FX_24_5 için `zoneinfo`
(America/New_York) DST'yi otomatik uygular. (Örn: NYSE 16:00 ET kapanışı yazın
20:00 UTC, kışın 21:00 UTC — bkz. tests/test_calendars.py golden değerleri.)
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd

TZ_UTC = timezone.utc
TZ_NEW_YORK = ZoneInfo("America/New_York")

FX_DAILY_CLOSE_NY = time(17, 0)          # 17:00 America/New_York (Bölüm 5)
_EXCHANGE_BACKED = {"XIST", "XNYS"}
_SUPPORTED = _EXCHANGE_BACKED | {"FX_24_5"}


class MarketCalendar:
    """Tek arayüz; XIST/XNYS exchange_calendars'a, FX_24_5 özel mantığa delege eder."""

    def __init__(self, calendar_id: str):
        if calendar_id not in _SUPPORTED:
            raise ValueError(
                f"Desteklenmeyen calendar_id: '{calendar_id}' (desteklenen: {sorted(_SUPPORTED)})"
            )
        self.calendar_id = calendar_id
        self._ec = _load_exchange_calendar(calendar_id) if calendar_id in _EXCHANGE_BACKED else None

    # ------------------------------------------------------------------ API
    def is_trading_day(self, d: date) -> bool:
        if self._ec is not None:
            return bool(self._ec.is_session(pd.Timestamp(_as_date(d))))
        # FX_24_5: Pazartesi–Cuma (Cumartesi/Pazar günlük barı yok)
        return _as_date(d).weekday() < 5

    def close_dt_utc(self, d: date) -> datetime:
        """O günün bar KAPANIŞ anı (UTC). İşlem günü değilse ValueError."""
        dd = _as_date(d)
        if not self.is_trading_day(dd):
            raise ValueError(f"{self.calendar_id}: {dd} işlem günü değil, kapanış anı yok")
        if self._ec is not None:
            return self._ec.session_close(pd.Timestamp(dd)).to_pydatetime().astimezone(TZ_UTC)
        # FX_24_5: 17:00 NY (DST otomatik) → UTC
        local = datetime.combine(dd, FX_DAILY_CLOSE_NY, tzinfo=TZ_NEW_YORK)
        return local.astimezone(TZ_UTC)

    def next_eval_dt_utc(self, after: datetime) -> datetime:
        """`after`den (UTC) SONRA gelen ilk bar kapanış anı (scheduler girdisi)."""
        if after.tzinfo is None:
            raise ValueError("naive datetime yasak — tzinfo zorunlu")
        after_utc = after.astimezone(TZ_UTC)
        d = after_utc.astimezone(TZ_NEW_YORK).date()
        for _ in range(400):  # >1 yıl tatil zinciri güvenlik sınırı
            if self.is_trading_day(d):
                close = self.close_dt_utc(d)
                if close > after_utc:
                    return close
            d += timedelta(days=1)
        raise RuntimeError(f"{self.calendar_id}: {after}dan sonra 400 gün içinde işlem günü bulunamadı")

    def trading_dates(self, start: date, end: date) -> list[date]:
        s, e = _as_date(start), _as_date(end)
        if self._ec is not None:
            sessions = self._ec.sessions_in_range(pd.Timestamp(s), pd.Timestamp(e))
            return [ts.date() for ts in sessions]
        out: list[date] = []
        d = s
        while d <= e:
            if self.is_trading_day(d):
                out.append(d)
            d += timedelta(days=1)
        return out


def _as_date(d: date | datetime | pd.Timestamp) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, pd.Timestamp):
        return d.date()
    return d


@lru_cache(maxsize=8)
def _load_exchange_calendar(calendar_id: str):
    import exchange_calendars as ec
    return ec.get_calendar(calendar_id)


@lru_cache(maxsize=8)
def get_calendar(calendar_id: str) -> MarketCalendar:
    """Memoize'li MarketCalendar üreticisi (exchange_calendars kurulumu pahalı)."""
    return MarketCalendar(calendar_id)

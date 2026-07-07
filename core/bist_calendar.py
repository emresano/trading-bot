# core/bist_calendar.py
"""BIST seans/takvim gerçeği — config otoriter, kütüphane tek-otorite DEĞİL (B1, F5A-9).

config/bist_calendar.yaml resmî tatil/yarım-gün tablosunun otoriter kopyasıdır
(2026-07-07 web doğrulaması). exchange_calendars (XIST) ile UYUŞMAZLIK loglanır —
idari-izin köprü tatilleri kütüphanede olmayabilir. "Veri-yok" günü zarafetle atlanır.

Canlı döngü bir günü yanlış "işlem günü" sayarsa regime_core o gün hatalı sinyal/
yürütme üretebilir → bu modül o riski azaltır (STATUS real-öncesi kuyruk, B1).
"""
from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Callable, Optional

import yaml

DEFAULT_CALENDAR_CFG = Path("config/bist_calendar.yaml")


def _parse_time(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


class BistCalendar:
    def __init__(self, cfg_path: Path | str = DEFAULT_CALENDAR_CFG,
                 logger: Optional[Callable[[str], None]] = None):
        self.cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
        self._log = logger or (lambda m: None)
        s = self.cfg["session"]
        self.opening_auction_start = _parse_time(s["opening_auction_start"])
        self.continuous_start = _parse_time(s["continuous_start"])
        self.continuous_end = _parse_time(s["continuous_end"])
        self.closing_auction_end = _parse_time(s["closing_auction_end"])
        self.half_day_continuous_end = _parse_time(s["half_day_continuous_end"])
        self._holidays = {self._d(h["date"]) for h in self.cfg.get("holidays_2026", [])}
        self._holidays |= {self._d(h["date"]) for h in self.cfg.get("admin_leave_bridges_2026", [])}
        self._half_days = {self._d(h["date"]) for h in self.cfg.get("half_days_2026", [])}

    @staticmethod
    def _d(v) -> date:
        return v if isinstance(v, date) and not isinstance(v, datetime) else \
            datetime.strptime(str(v), "%Y-%m-%d").date()

    # ------------------------------------------------------------------ sorgular
    def is_config_holiday(self, d: date) -> bool:
        return self._d(d) in self._holidays

    def is_half_day(self, d: date) -> bool:
        return self._d(d) in self._half_days

    def is_weekend(self, d: date) -> bool:
        return self._d(d).weekday() >= 5

    def is_trading_day(self, d: date) -> bool:
        """Config otoriter: hafta sonu veya config tatili → kapalı. Aksi halde
        (config tablosu 2026 dışında ise) kütüphaneye düşer."""
        dd = self._d(d)
        if self.is_weekend(dd) or self.is_config_holiday(dd):
            return False
        return True

    def continuous_end_for(self, d: date) -> time:
        return self.half_day_continuous_end if self.is_half_day(d) else self.continuous_end

    def is_continuous_session(self, dt_local: datetime) -> bool:
        """dt_local (Europe/Istanbul) sürekli işlem seansında mı (müzayede hariç)."""
        d = dt_local.date()
        if not self.is_trading_day(d):
            return False
        t = dt_local.time()
        return self.continuous_start <= t < self.continuous_end_for(d)

    def is_auction_window(self, dt_local: datetime) -> bool:
        d = dt_local.date()
        if not self.is_trading_day(d):
            return False
        t = dt_local.time()
        end = self.continuous_end_for(d)
        return (self.opening_auction_start <= t < self.continuous_start) or \
               (end <= t < self.closing_auction_end)

    # ------------------------------------------------------------------ kütüphane mutabakatı + veri-yok
    def reconcile_with_library(self, start: date, end: date) -> list[dict]:
        """config tatilleri ↔ exchange_calendars(XIST) uyuşmazlıklarını döndürür +
        loglar. Boş liste = uyum. Uyuşmazlık idari-izin köprüsü / kütüphane
        gecikmesi olabilir — insan denetimi için işaretlenir (otomatik düzeltme YOK)."""
        from core.calendars import get_calendar
        lib = get_calendar("XIST")
        lib_days = set(lib.trading_dates(self._d(start), self._d(end)))
        discrepancies: list[dict] = []
        d = self._d(start)
        from datetime import timedelta
        while d <= self._d(end):
            if not self.is_weekend(d):
                cfg_trading = self.is_trading_day(d)
                lib_trading = d in lib_days
                if cfg_trading != lib_trading:
                    disc = {"date": str(d), "config_trading": cfg_trading,
                            "library_trading": lib_trading}
                    discrepancies.append(disc)
                    self._log(f"TAKVİM UYUŞMAZLIĞI {disc} (config otoriter; insan denetimi)")
            d += timedelta(days=1)
        return discrepancies

    def missing_data_days(self, available_dates, start: date, end: date) -> list[date]:
        """Config'e göre işlem günü olması BEKLENEN ama veride OLMAYAN günler.
        Bunlar canlıda zarafetle atlanır + loglanır (veri-yok toleransı, B1)."""
        have = {self._d(x) for x in available_dates}
        out: list[date] = []
        from datetime import timedelta
        d = self._d(start)
        while d <= self._d(end):
            if self.is_trading_day(d) and d not in have:
                out.append(d)
                self._log(f"VERİ-YOK işlem günü {d} — zarafetle atlanıyor (sinyal üretilmez)")
            d += timedelta(days=1)
        return out

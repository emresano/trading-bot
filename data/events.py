# data/events.py
"""Takvim vetoları — VETO, ASLA GİRİŞ SİNYALİ DEĞİL (EXPANSION.md Bölüm 10).

Bu modül E1 kapsamında bir İSKELET + veri kaynağı değerlendirmesidir. Tam
üretim implementasyonu (gerçek blackout kararları risk motoruna bağlanması)
E2+ işidir. Burada yalnızca: (a) arayüz (Bölüm 10.1), (b) iki kaynak adayının
GERÇEK örnek çekimle değerlendirilmesi, (c) Bölüm 10.4 fallback protokolüne
göre tarihsel derinlik bulgusu.

## Bulgu 1 — ABD kazanç tarihleri (earnings): DERİN TARİHÇE VAR
`yfinance.Ticker.get_earnings_dates(limit=100)` (lxml bağımlılığı gerektirir)
test edilen 4 sembolde (AAPL, JPM, XOM, CAT) 2001-2002'ye kadar giden tarihçe
döndürdü — 2005-01-01 backtest başlangıcından ÖNCESİNE geçiyor. CLAUDE.md'nin
öngördüğü "yfinance earnings geçmişi sığdır" endişesi bu 4 sembolde
DOĞRULANMADI (limit=100 çeyrek ≈ 25 yıl). Zaman damgası (örn. "16:00-04:00")
duyuru saatinden BMO/AMC çıkarımına izin veriyor (16:00 ET ~ kapanışta/sonrasında
= AMC; sabah saatleri = BMO).

## Bulgu 2 — Ekonomik takvim: TARİHSEL DERİNLİK YOK (Bölüm 10.4 fallback devrede)
ForexFactory'nin herkese açık, kimlik doğrulamasız widget feed'i
(`nfs.faireconomy.media/ff_calendar_thisweek.json`) çalışıyor ve şemaya uygun
(title/country/date/impact) VERİ DÖNDÜRÜYOR — ama yalnızca İÇİNDE BULUNULAN
HAFTA için. Programatik, ücretsiz bir TARİHSEL arşiv bulunamadı (FMP/
AlphaVantage ücretsiz katmanları API anahtarı gerektiriyor, bu oturumda
değerlendirilemedi — E3'te kullanıcıyla birlikte netleştirilebilir).
**Sonuç: Bölüm 10.4 fallback protokolü ekonomik takvim için DEVREDE** — FX
vetosu backtest'te MODELLENEMEYECEK, yalnızca canlı/paper'da aktif olacak
(E2+ implementasyonu), her FX raporuna bu sınırlama notu düşülecek.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class EarningsSample:
    symbol: str
    announce_date: pd.Timestamp
    session: str  # "bmo" | "amc" | "unknown"


@dataclass(frozen=True)
class EarningsRule:
    """us earnings blackout kuralı (Bölüm 10.3)."""
    enabled: bool = True
    days_before: int = 3
    days_after: int = 1


@dataclass(frozen=True)
class EconRule:
    """fx ekonomik takvim blackout kuralı (Bölüm 10.3)."""
    enabled: bool = True
    impact: str = "high"
    hours_before: int = 12
    hours_after: int = 12


class EventCalendar:
    """Deterministik (Tier 0) takvim vetoları — VETO, ASLA GİRİŞ SİNYALİ DEĞİL
    (Bölüm 10). ÇIKIŞLAR HER ZAMAN SERBEST (çağıran risk motoru bunu garanti eder).

    Veri: data/events/earnings_<SEMBOL>.parquet (kolon: announce_date[, session]),
    data/events/econ_calendar.parquet (kolon: ts_utc, impact, currencies).
    Veri YOKSA (Bölüm 10.4 fallback): (False, "...veri yok...") döner — backtest
    vetosuz koşar, sınırlama notu rapora çağıran tarafından düşülür. Bu, üretim
    modelleme ALTYAPISIDIR; gerçek parquet dosyaları E1/E3'te doldurulur."""

    def __init__(self, events_dir: str | "Path" = "data/events",
                 earnings_rule: Optional["EarningsRule"] = None,
                 econ_rule: Optional["EconRule"] = None):
        from pathlib import Path
        self.events_dir = Path(events_dir)
        self.earnings_rule = earnings_rule or EarningsRule()
        self.econ_rule = econ_rule or EconRule()
        self._earnings_cache: dict[str, Optional[pd.DataFrame]] = {}
        self._econ_cache: Optional[pd.DataFrame] = None

    def is_blackout(self, market_id: str, symbol: str, d: date) -> tuple[bool, str]:
        """True + insan-okur reason ise CALENDAR_BLACKOUT (risk motoru yeni girişi
        reddeder). market_id'e göre earnings (us) / econ (fx) / yok (bist)."""
        if market_id == "us":
            return self._earnings_blackout(symbol, d)
        if market_id == "fx":
            return self._econ_blackout(symbol, d)
        return (False, f"{market_id}: deterministik takvim vetosu tanımlı değil (bist NEWS_BLACKOUT ayrı)")

    # ---------------------------------------------------------------- earnings (us)
    def _load_earnings(self, symbol: str) -> Optional[pd.DataFrame]:
        if symbol in self._earnings_cache:
            return self._earnings_cache[symbol]
        path = self.events_dir / f"earnings_{symbol}.parquet"
        df = pd.read_parquet(path) if path.exists() else None
        self._earnings_cache[symbol] = df
        return df

    def _earnings_blackout(self, symbol: str, d: date) -> tuple[bool, str]:
        rule = self.earnings_rule
        if not rule.enabled:
            return (False, "earnings vetosu kapalı")
        df = self._load_earnings(symbol)
        if df is None or df.empty:
            return (False, f"earnings verisi yok ({symbol}) — Bölüm 10.4: backtest vetosuz")
        from datetime import timedelta
        for announce in pd.to_datetime(df["announce_date"]):
            a = announce.date()
            if a - timedelta(days=rule.days_before) <= d <= a + timedelta(days=rule.days_after):
                delta = (d - a).days
                tag = f"T{delta:+d}" if delta != 0 else "T0"
                return (True, f"earnings {a.isoformat()} ({tag})")
        return (False, f"earnings penceresi dışında ({symbol})")

    # ---------------------------------------------------------------- econ (fx)
    def _load_econ(self) -> Optional[pd.DataFrame]:
        if self._econ_cache is not None:
            return self._econ_cache
        path = self.events_dir / "econ_calendar.parquet"
        self._econ_cache = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        return self._econ_cache

    @staticmethod
    def _symbol_currencies(symbol: str) -> set[str]:
        # "EUR_USD" -> {EUR, USD}; "USD_JPY" -> {USD, JPY}
        return {p for p in symbol.split("_") if p}

    def _econ_blackout(self, symbol: str, d: date) -> tuple[bool, str]:
        rule = self.econ_rule
        if not rule.enabled:
            return (False, "econ vetosu kapalı")
        df = self._load_econ()
        if df is None or df.empty:
            return (False, f"econ takvim verisi yok — Bölüm 10.4: FX backtest vetosuz ({symbol})")
        from datetime import datetime, timedelta, timezone
        ccys = self._symbol_currencies(symbol)
        day_start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        for _, row in df.iterrows():
            if str(row.get("impact")) != rule.impact:
                continue
            row_ccys = row.get("currencies")
            if isinstance(row_ccys, str):
                row_set = {row_ccys}
            elif hasattr(row_ccys, "__iter__"):   # list/tuple/set/np.ndarray (parquet round-trip)
                row_set = {str(c) for c in row_ccys}
            else:
                row_set = {str(row_ccys)}
            if not (ccys & row_set):
                continue
            ts = pd.to_datetime(row["ts_utc"])
            ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
            ts = ts.to_pydatetime()
            window_start = ts - timedelta(hours=rule.hours_before)
            window_end = ts + timedelta(hours=rule.hours_after)
            # gün, olay penceresiyle kesişiyor mu (gün [day_start, +24h))
            if window_start < day_start + timedelta(days=1) and window_end > day_start:
                return (True, f"econ {rule.impact}-impact {ts.isoformat()} ({'/'.join(sorted(ccys & row_set))})")
        return (False, f"econ penceresi dışında ({symbol})")


def _infer_session(ts: pd.Timestamp) -> str:
    """Duyuru saatinden kaba bir BMO/AMC çıkarımı (ET saatine göre).
    9:30 açılıştan önce = bmo (before market open), 16:00 kapanıştan
    sonra/civarı = amc (after market close), aksi = unknown."""
    if ts.tzinfo is None:
        return "unknown"
    et = ts.tz_convert("America/New_York")
    if et.hour < 9 or (et.hour == 9 and et.minute < 30):
        return "bmo"
    if et.hour >= 16:
        return "amc"
    return "unknown"


def fetch_earnings_sample(symbol: str, limit: int = 100) -> list[EarningsSample]:
    """ABD kazanç tarihleri için örnek çekim (Bölüm 10, veri kaynağı
    değerlendirmesi). `yfinance` (lxml bağımlılığı gerektirir — Bölüm 18'e
    henüz eklenmedi, yalnızca bu değerlendirme için venv'e geçici kuruldu;
    E2'de gerçek implementasyon kararlaştırılırsa requirements.txt/.lock'a
    işlenir). Ağ hatası/lxml eksikse boş liste döner (sessizce başarısız
    olmaz — çağıran loglar)."""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    df = ticker.get_earnings_dates(limit=min(limit, 100))
    return [
        EarningsSample(symbol=symbol, announce_date=idx, session=_infer_session(idx))
        for idx in df.index
    ]


def fetch_economic_calendar_current_week_sample() -> pd.DataFrame:
    """Ekonomik takvim için örnek çekim (Bölüm 10, veri kaynağı
    değerlendirmesi). ForexFactory'nin herkese açık widget feed'i —
    yalnızca İÇİNDE BULUNULAN HAFTA, TARİHSEL DERİNLİK YOK (bkz. modül
    docstring'i, Bulgu 2). Kolonlar: title, country, date(UTC), impact."""
    import requests

    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], utc=True)
    return df

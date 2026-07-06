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


class EventCalendar:
    """Bölüm 10.1 arayüzü — E1'de yalnızca imza + NotImplementedError iskeleti.
    Gerçek blackout kararı E2+'ta (data/events/*.parquet dosyalarından
    okuyarak) implemente edilir."""

    def is_blackout(self, market_id: str, symbol: str, d: date) -> tuple[bool, str]:
        raise NotImplementedError("E2+ işi — EXPANSION.md Bölüm 10.3 kurallarına göre implemente edilecek")


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

# data/cash_rate_feed.py
"""TRY gecelik/politika faizi CANLI uzantı beslemesi (Faz 5, F5-B1.1 K1).

NEDEN: nakit tahakkuku (rejim KAPALI günlerde TRY_ON_RATE − 200bp, ACT/365; backtest
ile AYNI formül) canlıda GÜNCEL faiz ister. Aux snapshot 2026-03'te bitiyor —
`data/snapshots/aux/.../TRY_ON_RATE.parquet` bu turda DEĞİŞTİRİLMEZ (DEĞİŞMEZLER).

TASARIM: snapshot READ-ONLY temeldir; canlı yeni aylar AYRI bir uzantı deposuna
(SQLite, live_store deseni) yazılır. Birleşik seri = snapshot ∪ uzantı (uzantı
snapshot-sonrası ayları ekler). Formül/haircut DEĞİŞMEZ — yalnız serinin canlı ucu uzar.

İHTİMAL PLANI #7: günlük döngü faiz serisinin bayatlığını kontrol eder; bayatlık
> staleness_days ise FRED'den çeker (kaynak: aux manifest — OECD MEI IRSTCI01TRM156N);
çekim başarısızsa SON BİLİNEN değer korunur + WARN (nakit tahakkuku durmaz, sadece
bayat faizle sürer; muhafazakâr — yükselen faiz ortamında düşük tahmin = az tahakkuk).

AĞ: yalnız `fetch_fn` gerçek FRED'e gider; testlerde enjekte edilir (offline).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRSTCI01TRM156N"
DEFAULT_STALENESS_DAYS = 35   # aylık seri; ~1 ay + tamponu aşarsa bayat


def fred_fetch_try_on_rate(since_iso: Optional[str]) -> pd.Series:
    """Gerçek FRED çekimi (rate_pct, aylık, tarih-index). since verilirse o tarihten
    SONRASINI döndürür. Ağ ÇAĞRISI burada — testlerde enjekte edilir, çağrılmaz."""
    import io
    import requests
    r = requests.get(FRED_URL, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    # kolonlar: observation_date/DATE, IRSTCI01TRM156N (veya değer kolonu)
    date_col = df.columns[0]
    val_col = df.columns[1]
    idx = pd.DatetimeIndex(pd.to_datetime(df[date_col], utc=True))  # tz-aware KORUNUR (.values tz'yi siler)
    vals = pd.to_numeric(df[val_col], errors="coerce")             # '.' → NaN
    s = pd.Series(vals.values, index=idx, name="rate_pct")
    s = s[s.notna()]
    if since_iso is not None:
        s = s[s.index > pd.Timestamp(since_iso)]
    return s


class CashRateFeed:
    """snapshot (read-only) + canlı uzantı (SQLite) birleşik faiz serisi."""

    def __init__(self, snapshot_path: Path | str, ext_store_path: Path | str,
                 fetch_fn: Callable[[Optional[str]], pd.Series] = fred_fetch_try_on_rate,
                 staleness_days: int = DEFAULT_STALENESS_DAYS):
        self.snapshot_path = Path(snapshot_path)
        self.ext_path = Path(ext_store_path)
        self.fetch_fn = fetch_fn
        self.staleness_days = staleness_days
        self.ext_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.ext_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cash_rate_ext (ts_utc TEXT PRIMARY KEY, "
            "rate_pct REAL NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL)")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ seriler
    def _snapshot_series(self) -> pd.Series:
        if not self.snapshot_path.exists():
            return pd.Series(dtype=float)
        s = pd.read_parquet(self.snapshot_path)["rate_pct"]
        s.index = pd.to_datetime(s.index, utc=True)
        return s[s.notna()]

    def _ext_series(self) -> pd.Series:
        rows = self._conn.execute(
            "SELECT ts_utc, rate_pct FROM cash_rate_ext ORDER BY ts_utc").fetchall()
        if not rows:
            return pd.Series(dtype=float)
        idx = pd.to_datetime([r[0] for r in rows], utc=True)
        return pd.Series([r[1] for r in rows], index=idx, name="rate_pct")

    def combined_rate_pct(self) -> pd.Series:
        """snapshot ∪ uzantı (uzantı çakışan/sonraki ayları belirler). rate_pct (yüzde)."""
        snap = self._snapshot_series()
        ext = self._ext_series()
        if ext.empty:
            return snap.sort_index()
        combined = pd.concat([snap[~snap.index.isin(ext.index)], ext]).sort_index()
        return combined

    def combined_series(self) -> pd.Series:
        """regime_core/runner'ın beklediği KESİR (rate_pct/100) — backtest ile AYNI."""
        return self.combined_rate_pct() / 100.0

    def last_date(self) -> Optional[pd.Timestamp]:
        c = self.combined_rate_pct()
        return c.index[-1] if len(c) else None

    # ------------------------------------------------------------------ yenileme
    def _upsert_ext(self, s: pd.Series, source: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        n = 0
        for ts, val in s.items():
            if pd.isna(val):
                continue
            self._conn.execute(
                "INSERT INTO cash_rate_ext (ts_utc, rate_pct, source, created_at) VALUES (?,?,?,?) "
                "ON CONFLICT(ts_utc) DO UPDATE SET rate_pct=excluded.rate_pct, source=excluded.source",
                (pd.Timestamp(ts).tz_convert("UTC").isoformat() if pd.Timestamp(ts).tzinfo
                 else pd.Timestamp(ts, tz="UTC").isoformat(), float(val), source, now))
            n += 1
        self._conn.commit()
        return n

    def refresh(self, as_of, logger: Optional[Callable[[str], None]] = None) -> dict:
        """Bayatlık kontrolü + gerekirse FRED çekimi (İHTİMAL PLANI #7).
        Döner: {action, staleness_days, last_date, source, rate}."""
        log = logger or (lambda m: None)
        as_of_ts = pd.Timestamp(as_of, tz="UTC") if not isinstance(as_of, pd.Timestamp) or as_of.tzinfo is None \
            else as_of
        last = self.last_date()
        staleness = (as_of_ts - last).days if last is not None else 10_000
        if staleness <= self.staleness_days:
            return self._status_dict("fresh", as_of_ts)
        # bayat → çek
        try:
            since = last.isoformat() if last is not None else None
            fresh = self.fetch_fn(since)
            if fresh is not None and len(fresh):
                n = self._upsert_ext(fresh, source="fred")
                log(f"cash_rate: FRED'den {n} yeni ay çekildi (bayatlık {staleness}g)")
                return self._status_dict("fetched", as_of_ts)
            log(f"cash_rate: FRED boş döndü (bayatlık {staleness}g) → son bilinen değer korunuyor")
            return self._status_dict("fetch_empty", as_of_ts)
        except Exception as e:
            log(f"cash_rate: FRED çekimi BAŞARISIZ ({type(e).__name__}) → son bilinen değer + WARN "
                f"(bayatlık {staleness}g)")
            return self._status_dict("fetch_failed", as_of_ts)

    def _status_dict(self, action: str, as_of_ts: pd.Timestamp) -> dict:
        c = self.combined_rate_pct()
        last = c.index[-1] if len(c) else None
        rate = float(c.iloc[-1]) if len(c) else None
        staleness = (as_of_ts - last).days if last is not None else None
        stale_flag = staleness is not None and staleness > self.staleness_days
        return {"action": action, "rate_pct": rate,
                "source_date": str(last.date()) if last is not None else None,
                "staleness_days": staleness, "stale": stale_flag}

    def status(self, as_of) -> dict:
        as_of_ts = pd.Timestamp(as_of, tz="UTC")
        return self._status_dict("status", as_of_ts)

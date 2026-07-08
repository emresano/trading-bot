# tests/test_cash_rate_feed.py
"""F5-B1.1 K1 — TRY_ON_RATE canlı uzantı besleme (OFFLINE, FRED enjekte)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data.cash_rate_feed import CashRateFeed


def _snapshot(tmp_path: Path, last="2026-03-01") -> Path:
    idx = pd.date_range("2026-01-01", last, freq="MS", tz="UTC")
    df = pd.DataFrame({"rate_pct": [40.0 + i for i in range(len(idx))]}, index=idx)
    df.index.name = "date"
    p = tmp_path / "TRY_ON_RATE.parquet"
    df.to_parquet(p)
    return p


def test_fresh_no_fetch(tmp_path: Path):
    """Bayatlık ≤ eşik → çekim YOK, birleşik seri = snapshot."""
    snap = _snapshot(tmp_path, "2026-03-01")
    calls = []
    feed = CashRateFeed(snap, tmp_path / "ext.sqlite",
                        fetch_fn=lambda since: calls.append(since) or pd.Series(dtype=float),
                        staleness_days=35)
    st = feed.refresh("2026-03-20")   # 19 gün < 35 → taze
    assert st["action"] == "fresh"
    assert calls == []                 # çekim yok
    assert feed.last_date().date().isoformat() == "2026-03-01"
    feed.close()


def test_stale_triggers_fetch_and_extends(tmp_path: Path):
    """Bayatlık > eşik → FRED çekilir, uzantı snapshot-sonrası ayları ekler."""
    snap = _snapshot(tmp_path, "2026-03-01")
    def fake_fred(since):
        idx = pd.date_range("2026-04-01", "2026-06-01", freq="MS", tz="UTC")
        return pd.Series([45.0, 46.0, 47.0], index=idx, name="rate_pct")
    feed = CashRateFeed(snap, tmp_path / "ext.sqlite", fetch_fn=fake_fred, staleness_days=35)
    st = feed.refresh("2026-07-01")    # >35 gün → çek
    assert st["action"] == "fetched"
    assert feed.last_date().date().isoformat() == "2026-06-01"
    # birleşik seri kesir olarak (backtest formülü)
    comb = feed.combined_series()
    assert abs(comb.iloc[-1] - 0.47) < 1e-9
    feed.close()


def test_fetch_failure_keeps_last_and_warns(tmp_path: Path):
    """Çekim istisna atarsa → son bilinen değer korunur, action=fetch_failed (İHTİMAL #7)."""
    snap = _snapshot(tmp_path, "2026-03-01")
    def boom(since):
        raise ConnectionError("FRED down")
    feed = CashRateFeed(snap, tmp_path / "ext.sqlite", fetch_fn=boom, staleness_days=35)
    logs = []
    st = feed.refresh("2026-07-01", logger=logs.append)
    assert st["action"] == "fetch_failed"
    assert st["stale"] is True                       # hâlâ bayat (çekemedi)
    assert feed.last_date().date().isoformat() == "2026-03-01"   # son bilinen korunur
    assert any("BAŞARISIZ" in m for m in logs)
    # tahakkuk durmaz: birleşik seri hâlâ mevcut
    assert feed.combined_series().iloc[-1] > 0
    feed.close()


def test_snapshot_never_modified(tmp_path: Path):
    """Uzantı yazımı snapshot parquet'ini DEĞİŞTİRMEZ (DEĞİŞMEZLER)."""
    snap = _snapshot(tmp_path, "2026-03-01")
    before = snap.read_bytes()
    feed = CashRateFeed(snap, tmp_path / "ext.sqlite",
                        fetch_fn=lambda s: pd.Series([45.0], index=pd.date_range("2026-04-01","2026-04-01",freq="MS",tz="UTC"), name="rate_pct"),
                        staleness_days=35)
    feed.refresh("2026-07-01")
    assert snap.read_bytes() == before               # snapshot bayt-bayt aynı
    feed.close()


def test_status_reports_staleness(tmp_path: Path):
    snap = _snapshot(tmp_path, "2026-03-01")
    feed = CashRateFeed(snap, tmp_path / "ext.sqlite", fetch_fn=lambda s: pd.Series(dtype=float))
    st = feed.status("2026-05-10")
    assert st["source_date"] == "2026-03-01"
    assert st["staleness_days"] == (pd.Timestamp("2026-05-10", tz="UTC") - pd.Timestamp("2026-03-01", tz="UTC")).days
    assert st["stale"] is True
    feed.close()

# tests/test_live_store.py
"""F5A-1 — canlı günlük tarihçe deposu testleri (offline, ağ yok)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data.live_store import LiveHistoryStore, CROSS_SOURCE_TOL_PCT


def _bars(dates_close: dict[str, float]) -> pd.DataFrame:
    idx = pd.to_datetime(list(dates_close.keys()), utc=True)
    closes = list(dates_close.values())
    return pd.DataFrame(
        {"open": closes, "high": [c * 1.01 for c in closes],
         "low": [c * 0.99 for c in closes], "close": closes,
         "volume": [1000] * len(closes)},
        index=idx,
    )


def test_upsert_and_read_closes(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    df = _bars({"2024-01-02T21:00:00+00:00": 10.0, "2024-01-03T21:00:00+00:00": 11.0})
    rep = store.upsert_bars("THYAO", df, source="snapshot")
    assert rep.inserted == 2 and rep.conflicts == 0
    closes = store.get_closes("THYAO")
    assert list(closes.values) == [10.0, 11.0]
    assert store.history_len("THYAO") == 2
    store.close()


def test_idempotent_reupsert_same_source(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    df = _bars({"2024-01-02T21:00:00+00:00": 10.0})
    store.upsert_bars("THYAO", df, source="snapshot")
    rep2 = store.upsert_bars("THYAO", df, source="snapshot")
    assert rep2.inserted == 0 and rep2.conflicts == 0 and rep2.unchanged == 1
    assert store.history_len("THYAO") == 1  # yinelenmedi
    store.close()


def test_cross_source_conflict_flags_suspect(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    day = "2024-01-02T21:00:00+00:00"
    store.upsert_bars("THYAO", _bars({day: 100.0}), source="snapshot")
    # farklı kaynak, %2 sapma (>%0.5 tolerans) → çakışma + suspect
    rep = store.upsert_bars("THYAO", _bars({day: 102.0}), source="algolab")
    assert rep.conflicts == 1
    conflicts = store.conflicts()
    assert len(conflicts) == 1
    assert conflicts.iloc[0]["source_existing"] == "snapshot"
    assert conflicts.iloc[0]["source_incoming"] == "algolab"
    assert conflicts.iloc[0]["pct_diff"] == pytest.approx(0.02, abs=1e-9)
    assert day in store.suspect_days("THYAO")
    store.close()


def test_cross_source_within_tolerance_no_conflict(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    day = "2024-01-02T21:00:00+00:00"
    store.upsert_bars("THYAO", _bars({day: 100.0}), source="snapshot")
    small = 100.0 * (1 + CROSS_SOURCE_TOL_PCT / 2)  # tolerans altı
    rep = store.upsert_bars("THYAO", _bars({day: small}), source="algolab")
    assert rep.conflicts == 0 and rep.unchanged == 1
    assert store.suspect_days("THYAO") == []
    store.close()


def test_ma_ready(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    dates = pd.date_range("2023-01-01", periods=205, freq="D", tz="UTC")
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
                      index=dates)
    store.upsert_bars("THYAO", df, source="snapshot")
    ready = store.ma_ready(["THYAO", "GARAN"], ma_period=200)
    assert ready["THYAO"] is True
    assert ready["GARAN"] is False  # hiç veri yok
    store.close()


def test_eod_update_incremental(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    store.upsert_bars("THYAO", _bars({"2024-01-02T21:00:00+00:00": 10.0}), source="snapshot")

    captured_since = {}

    def fetch_fn(symbol: str, since):
        captured_since[symbol] = since
        return _bars({"2024-01-03T21:00:00+00:00": 11.0})

    rep = store.eod_update(["THYAO"], fetch_fn, source="algolab")
    assert rep["THYAO"].inserted == 1
    assert captured_since["THYAO"] == "2024-01-02T21:00:00+00:00"  # artımlı: son bardan sonra
    assert store.history_len("THYAO") == 2
    store.close()


def test_naive_datetime_rejected(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    idx = pd.to_datetime(["2024-01-02"])  # tz yok → naive
    df = pd.DataFrame({"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0],
                       "volume": [1.0]}, index=idx)
    with pytest.raises(ValueError, match="naive"):
        store.upsert_bars("THYAO", df, source="snapshot")
    store.close()


def test_bootstrap_from_snapshot(tmp_path: Path):
    snap = Path("data/snapshots/2026-07-06")
    if not (snap / "THYAO.parquet").exists():
        pytest.skip("snapshot yok")
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    reps = store.bootstrap_from_snapshot(snap, ["THYAO"], start="2026-01-01")
    assert reps["THYAO"].inserted > 0
    assert store.history_len("THYAO") == reps["THYAO"].inserted
    assert store.get_closes("THYAO").index.tz is not None  # UTC korunuyor
    store.close()

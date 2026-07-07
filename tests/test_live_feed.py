# tests/test_live_feed.py
"""F5-B1 — yfinance canlı besleme testleri (OFFLINE, ağ yok — fetch enjekte edilir).

yfinance'in kendisi test edilmez (CLAUDE.md 7.4). Test edilen: temizlik paritesi
(normalize_bist_dates + ghost filtre), idempotent EOD güncelleme, çapraz-tutarlılık,
'bar yok' zarafeti ve MA-kompozit hazırlık kanıtı — hepsi enjekte fetch ile.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data.live_feed import LiveDataFeed, YF_SOURCE, SNAPSHOT_SOURCE
from data.live_store import LiveHistoryStore


def _raw_bars(dates_close: dict[str, float], volume: float = 1000.0) -> pd.DataFrame:
    """Ham yfinance-emsali bar (UTC index, 21:00 = Istanbul gece yarısı emsali)."""
    idx = pd.to_datetime(list(dates_close.keys()), utc=True)
    closes = list(dates_close.values())
    n = len(closes)
    return pd.DataFrame(
        {"open": closes, "high": [c * 1.01 for c in closes],
         "low": [c * 0.99 for c in closes], "close": closes,
         "volume": [volume] * n},
        index=pd.DatetimeIndex(idx, name="ts"),
    )


def _fetch_from(store_data: dict[str, pd.DataFrame]):
    """Sembol→ham-DataFrame sözlüğünden bir fetch_raw_fn üretir (start filtresini uygular)."""
    def _fn(yf_sym: str, start):
        sym = yf_sym.replace(".IS", "")
        df = store_data.get(sym)
        if df is None or df.empty:
            return pd.DataFrame()
        if start is not None:
            df = df.loc[start:]
        return df
    return _fn


def test_normalize_parity_with_backtest_cleaning(tmp_path: Path):
    """live_feed'in temizliği backtest'in load_and_clean_universe'iyle AYNI etiketi üretir."""
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    # 2026-07-02 21:00 UTC = Istanbul 2026-07-03 00:00 → normalize → 2026-07-03 00:00 UTC
    data = {"THYAO": _raw_bars({"2026-07-02T21:00:00+00:00": 334.0}),
            "GARAN": _raw_bars({"2026-07-02T21:00:00+00:00": 100.0})}
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=_fetch_from(data))
    feed.eod_update()
    closes = store.get_closes("THYAO")
    assert len(closes) == 1
    assert str(closes.index[0].date()) == "2026-07-03"  # Istanbul günü
    assert closes.iloc[0] == 334.0
    store.close()


def test_eod_idempotent_and_incremental(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    data = {"THYAO": _raw_bars({"2026-07-02T21:00:00+00:00": 334.0}),
            "GARAN": _raw_bars({"2026-07-02T21:00:00+00:00": 100.0})}
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=_fetch_from(data))
    r1 = feed.eod_update()
    assert r1.totals()["inserted"] == 2
    # ikinci koşum: aynı barlar → yeni ekleme yok (idempotent)
    r2 = feed.eod_update()
    assert r2.totals()["inserted"] == 0
    # yeni gün ekle → yalnız o eklenir
    data["THYAO"] = _raw_bars({"2026-07-02T21:00:00+00:00": 334.0,
                               "2026-07-05T21:00:00+00:00": 350.0})
    data["GARAN"] = _raw_bars({"2026-07-02T21:00:00+00:00": 100.0,
                               "2026-07-05T21:00:00+00:00": 105.0})
    r3 = feed.eod_update()
    assert r3.totals()["inserted"] == 2
    store.close()


def test_cross_source_consistency_flags_conflict(tmp_path: Path):
    """snapshot günü yfinance'te >%0.5 farklıysa çakışma + suspect (çapraz-veri raporu)."""
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    day = "2026-07-02T21:00:00+00:00"
    # snapshot kaynağıyla önceden yaz (temizlenmiş etiketle)
    from data.cleaning import normalize_bist_dates
    snap_df = normalize_bist_dates(_raw_bars({day: 100.0}))
    store.upsert_bars("THYAO", snap_df, source=SNAPSHOT_SOURCE)
    store.upsert_bars("GARAN", normalize_bist_dates(_raw_bars({day: 50.0})), source=SNAPSHOT_SOURCE)
    # yfinance aynı günü %3 farklı verir → çakışma
    data = {"THYAO": _raw_bars({day: 103.0}), "GARAN": _raw_bars({day: 50.0})}
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=_fetch_from(data))
    rep = feed.eod_update()
    assert rep.per_symbol["THYAO"].conflicts == 1
    assert "2026-07-03" in "".join(store.suspect_days("THYAO"))
    store.close()


def test_no_data_symbol_graceful(tmp_path: Path):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    data = {"THYAO": _raw_bars({"2026-07-02T21:00:00+00:00": 334.0}), "GARAN": pd.DataFrame()}
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=_fetch_from(data))
    rep = feed.eod_update()
    assert "GARAN" in rep.no_data_symbols
    assert rep.per_symbol["THYAO"].inserted == 1
    store.close()


def test_ghost_bar_filtered_like_backtest(tmp_path: Path):
    """Tek-sembolde-var + volume=0 + OHLC=onceki_kapanis → ghost, elenmeli."""
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    # THYAO'da 06-30 ve 07-01; 07-01 ghost (vol=0, OHLC düz = 06-30 kapanışı). GARAN'da yalnız 06-30.
    thyao = _raw_bars({"2026-06-30T21:00:00+00:00": 300.0}, volume=1000.0)
    gidx = pd.DatetimeIndex(pd.to_datetime(["2026-07-01T21:00:00+00:00"], utc=True), name="ts")
    ghost = pd.DataFrame({"open": [300.0], "high": [300.0], "low": [300.0],
                          "close": [300.0], "volume": [0.0]}, index=gidx)  # düz OHLC = prev close
    thyao = pd.concat([thyao, ghost])
    garan = _raw_bars({"2026-06-30T21:00:00+00:00": 100.0}, volume=1000.0)
    data = {"THYAO": thyao, "GARAN": garan}
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=_fetch_from(data))
    rep = feed.eod_update()
    assert len(rep.ghost_removed) == 1
    assert store.history_len("THYAO") == 1  # ghost yazılmadı
    store.close()


def test_composite_readiness_report(tmp_path: Path):
    """MA(N) kompozit hazırlık raporu: yeterli geçmişte all_ready + computable."""
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    dates = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
    data = {}
    for sym in ["THYAO", "GARAN"]:
        df = pd.DataFrame(
            {"open": range(10), "high": range(10), "low": range(10),
             "close": [100.0 + i for i in range(10)], "volume": [1000] * 10},
            index=pd.DatetimeIndex(dates, name="ts"))
        data[sym] = df
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=_fetch_from(data))
    feed.eod_update()
    rep = feed.composite_readiness(ma_period=5)
    assert rep["all_ready"] is True
    assert rep["composite_computable_to_today"] is True
    assert rep["ma_last_value"] is not None
    # kısa MA hazır değil
    rep2 = feed.composite_readiness(ma_period=50)
    assert rep2["all_ready"] is False
    store.close()

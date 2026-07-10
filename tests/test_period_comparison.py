import hashlib
import json

import pandas as pd
import pytest

from backtest.regime_core import Switch
from tools.period_comparison import (
    _extend_one,
    daily_ffill,
    freeze_aux_cmp,
    switch_count_and_regime_ratio,
    window_bounds,
)


def _df(dates, closes, vol=100.0):
    idx = pd.DatetimeIndex(dates, tz="UTC")
    return pd.DataFrame({
        "open": closes, "high": [c * 1.01 for c in closes], "low": [c * 0.99 for c in closes],
        "close": closes, "volume": [vol] * len(closes),
    }, index=idx)


def test_freeze_aux_cmp_empty_frames_writes_nothing(tmp_path, monkeypatch):
    import tools.period_comparison as pc
    monkeypatch.setattr(pc, "AUX_CMP_ROOT", tmp_path / "aux_cmp")
    out = freeze_aux_cmp("tag1", {}, "scope", "source")
    assert out is None
    assert not (tmp_path / "aux_cmp").exists()


def test_freeze_aux_cmp_writes_manifest_with_matching_sha256(tmp_path, monkeypatch):
    import tools.period_comparison as pc
    monkeypatch.setattr(pc, "AUX_CMP_ROOT", tmp_path / "aux_cmp")
    df = _df(["2026-07-03", "2026-07-04"], [100.0, 101.0])
    out_dir = freeze_aux_cmp("tag1", {"THYAO": df}, "scope-note", "source-note")
    assert out_dir == tmp_path / "aux_cmp" / "tag1"
    assert (out_dir / "THYAO.parquet").exists()
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["groups"][0]["scope"] == "scope-note"
    assert manifest["groups"][0]["source"] == "source-note"
    actual_hash = hashlib.sha256((out_dir / "THYAO.parquet").read_bytes()).hexdigest()
    assert manifest["files"]["THYAO"]["sha256"] == actual_hash
    assert manifest["files"]["THYAO"]["rows"] == 2


def test_freeze_aux_cmp_second_call_same_tag_merges_not_overwrites(tmp_path, monkeypatch):
    import tools.period_comparison as pc
    monkeypatch.setattr(pc, "AUX_CMP_ROOT", tmp_path / "aux_cmp")
    df1 = _df(["2026-07-03"], [100.0])
    df2 = _df(["2026-07-03"], [46.5])
    out_dir1 = freeze_aux_cmp("tag1", {"THYAO": df1}, "d1 scope", "yfinance")
    out_dir2 = freeze_aux_cmp("tag1", {"USDTRY": df2}, "usd scope", "yfinance")
    assert out_dir1 == out_dir2
    manifest = json.loads((out_dir1 / "manifest.json").read_text())
    assert set(manifest["files"].keys()) == {"THYAO", "USDTRY"}
    assert len(manifest["groups"]) == 2
    assert (out_dir1 / "THYAO.parquet").exists()
    assert (out_dir1 / "USDTRY.parquet").exists()


def test_window_bounds_full_coverage_flag():
    series_first = pd.Timestamp("2020-01-01", tz="UTC")
    windows = window_bounds(series_first)
    keys = [w[0] for w in windows]
    assert keys == ["son_1y", "son_3y", "son_5y", "son_10y", "tam_donem"]
    by_key = {w[0]: w for w in windows}
    # seri 2020'de basliyor, rapor sonu 2026-07-08 -> 1y/3y/5y pencereleri TAM kapsanir
    assert by_key["son_1y"][4] is True
    assert by_key["son_5y"][4] is True
    # 10 yillik pencere istenen baslangicin (2016-07-08) ONCESINE gidemez -> KISMI
    assert by_key["son_10y"][4] is False
    assert by_key["son_10y"][2] == series_first


def test_daily_ffill_forward_fills_and_backfills_edges():
    s = pd.Series([1.0, 2.0], index=pd.DatetimeIndex(["2020-01-01", "2020-01-05"], tz="UTC"))
    all_dates = pd.date_range("2020-01-01", "2020-01-06", freq="D", tz="UTC")
    out = daily_ffill(s, all_dates)
    assert out.loc["2020-01-03"] == 1.0  # forward-fill
    assert out.loc["2020-01-06"] == 2.0  # son deger korunur


def test_switch_count_and_regime_ratio():
    dates = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    regime_on = pd.Series([False, True, True, True, False], index=dates)
    switches = [
        Switch(date=dates[1], action="ENTER", equity_before=100.0, equity_after=100.0),
        Switch(date=dates[4], action="EXIT", equity_before=110.0, equity_after=109.0),
    ]
    n, ratio = switch_count_and_regime_ratio(switches, regime_on, dates[0], dates[2])
    assert n == 1  # yalnizca ENTER bu aralikta
    assert ratio == pytest.approx(2 / 3)


def test_extend_one_no_extension_needed_when_frozen_already_covers_end(tmp_path):
    frozen = _df(["2026-07-06", "2026-07-07", "2026-07-08"], [10.0, 11.0, 12.0])
    frozen.to_parquet(tmp_path / "THYAO.parquet")
    combined, new_bars, note = _extend_one("THYAO", "THYAO.IS", tmp_path, pd.Timestamp("2026-07-08", tz="UTC"))
    assert new_bars is None
    assert note is None
    assert len(combined) == 3


def test_extend_one_appends_fresh_bars_beyond_frozen_last_date(tmp_path, monkeypatch):
    import tools.period_comparison as pc
    frozen = _df(["2026-07-01", "2026-07-02"], [10.0, 11.0])
    frozen.to_parquet(tmp_path / "THYAO.parquet")

    fresh = _df(["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"], [10.0, 11.0, 12.0, 13.0])

    def fake_download_bars(yf_symbol, timeframe, start=None):
        return fresh

    monkeypatch.setattr(pc, "download_bars", fake_download_bars)
    combined, new_bars, note = _extend_one("THYAO", "THYAO.IS", tmp_path, pd.Timestamp("2026-07-04", tz="UTC"))
    assert len(new_bars) == 2  # yalniz 07-03/07-04
    assert len(combined) == 4
    assert note["max_abs_rel_diff"] == 0.0
    assert note["overlap_days"] == 2

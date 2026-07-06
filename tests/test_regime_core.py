import numpy as np
import pandas as pd
import pytest

from backtest.regime_core import (
    RegimeCoreConfig,
    build_composite,
    compute_regime_signal,
    run_regime_core,
)


def _flat_closes(symbols, n=300, start="2020-01-01", base=100.0):
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    return {s: pd.Series(base, index=idx) for s in symbols}


# --- build_composite ---

def test_build_composite_normalizes_to_one_at_t0():
    idx = pd.date_range("2020-01-01", periods=5, freq="1D", tz="UTC")
    closes = {
        "A": pd.Series([100.0, 110.0, 120.0, 130.0, 140.0], index=idx),
        "B": pd.Series([50.0, 55.0, 60.0, 65.0, 70.0], index=idx),
    }
    composite, fill_log = build_composite(closes)
    assert composite.iloc[0] == pytest.approx(1.0)
    assert fill_log == []
    # gün 2: A=1.10, B=1.10 -> ortalama 1.10
    assert composite.iloc[1] == pytest.approx(1.10)


def test_build_composite_t0_is_latest_starting_symbol():
    idx_a = pd.date_range("2020-01-01", periods=10, freq="1D", tz="UTC")
    idx_b = pd.date_range("2020-01-05", periods=6, freq="1D", tz="UTC")  # A'dan 4 gün sonra başlıyor
    closes = {
        "A": pd.Series(100.0, index=idx_a),
        "B": pd.Series(50.0, index=idx_b),
    }
    composite, _ = build_composite(closes)
    assert composite.index[0] == idx_b[0]  # t0 = B'nin başlangıcı (en geç başlayan)
    assert len(composite) == len(idx_b)


def test_build_composite_forward_fills_single_missing_day_and_logs_it():
    idx_full = pd.date_range("2020-01-01", periods=5, freq="1D", tz="UTC")
    idx_gap = idx_full.delete(2)  # B'de 3. gün eksik
    closes = {
        "A": pd.Series([100.0, 101.0, 102.0, 103.0, 104.0], index=idx_full),
        "B": pd.Series([50.0, 51.0, 53.0, 54.0], index=idx_gap),
    }
    composite, fill_log = build_composite(closes)
    assert len(composite) == 5
    assert len(fill_log) == 1
    assert fill_log[0]["symbol"] == "B"
    assert fill_log[0]["date"] == idx_full[2]
    # B'nin eksik günündeki (3. gün, index 2) normalize değeri, önceki (2. gün,
    # index 1) değeriyle taşınmış olmalı: B_norm[1] = 51/50 = 1.02
    a_norm_day3 = 102.0 / 100.0  # A'nın 3. günü (index 2) = 102.0
    b_norm_carried = 51.0 / 50.0  # B'nin 2. günü (index 1), taşınan değer
    expected_day3_composite = (a_norm_day3 + b_norm_carried) / 2
    assert composite.iloc[2] == pytest.approx(expected_day3_composite)


# --- compute_regime_signal ---

def test_regime_entry_requires_consecutive_confirm_days():
    idx = pd.date_range("2020-01-01", periods=20, freq="1D", tz="UTC")
    # 10 gün baz (1.0, MA ısınması + denge), sonra kademeli yükseliş (1.03,
    # sürdürülen) — MA(5) yavaş tepki verdiğinden üst bandı aşmak birkaç gün
    # sürer; doğrulanmış (deterministik) davranış: above_upper index 10'da
    # başlar, 3. ardışık gün (index 12) confirmed_entry'yi tetikler.
    composite = pd.Series([1.0] * 10 + [1.03] * 10, index=idx)
    signal = compute_regime_signal(composite, ma_period=5, band_pct=0.01, confirm_days=3)
    assert signal.iloc[10] == False  # above_upper'ın 1. günü — henüz teyit yok
    assert signal.iloc[11] == False  # 2. gün — hâlâ teyit yok
    assert signal.iloc[12] == True   # 3. ardışık gün — teyit tamam, ON
    assert signal.iloc[19] == True   # ON durumu devam ediyor


def test_regime_exit_is_single_day_no_confirmation_needed():
    idx = pd.date_range("2020-01-01", periods=25, freq="1D", tz="UTC")
    # ON'a geçiş (yukarıdaki testle aynı desen, index 12'de ON), ardından TEK
    # günlük keskin düşüş (index 18, 0.97) -> ANINDA OFF (teyit gerekmiyor),
    # tekrar yükselişte ise yine 3 gün teyit gerekiyor (index 21'de tekrar ON).
    composite = pd.Series([1.0] * 10 + [1.03] * 8 + [0.97] + [1.03] * 6, index=idx)
    signal = compute_regime_signal(composite, ma_period=5, band_pct=0.01, confirm_days=3)
    assert signal.iloc[12] == True    # önce ON'a geçmiş olmalı (giriş testiyle tutarlı)
    assert signal.iloc[17] == True    # düşüşten hemen önce hâlâ ON
    assert signal.iloc[18] == False   # TEK günlük düşüş -> ANINDA OFF
    assert signal.iloc[19] == False   # tekrar yükseldi ama henüz teyit yok (1. gün)
    assert signal.iloc[20] == False   # 2. gün, hâlâ teyit yok
    assert signal.iloc[21] == True    # 3. ardışık gün -> tekrar ON


def test_regime_signal_false_during_warmup():
    idx = pd.date_range("2020-01-01", periods=5, freq="1D", tz="UTC")
    composite = pd.Series([1.0, 1.05, 1.05, 1.05, 1.05], index=idx)
    signal = compute_regime_signal(composite, ma_period=10, band_pct=0.01, confirm_days=3)
    assert not signal.any()  # ma_period=10 > veri uzunluğu, hep NaN/False


# --- run_regime_core ---

def _step_composite_scenario():
    """3 sembol, hepsi aynı hareket eden bir seri: gün 0-19 sabit 100 (ısınma +
    band içi), gün 20'den itibaren güçlü yukarı trend (giriş teyidi tetiklensin),
    sonra keskin bir düşüş (çıkış tetiklensin)."""
    n = 60
    idx = pd.date_range("2020-01-01", periods=n, freq="1D", tz="UTC")
    prices = np.concatenate([
        np.full(20, 100.0),
        np.linspace(100.0, 130.0, 20),   # güçlü yükseliş
        np.linspace(130.0, 90.0, 20),    # keskin düşüş
    ])
    return {s: pd.Series(prices, index=idx) for s in ["A", "B", "C"]}


def test_run_regime_core_executes_at_t_plus_1_not_same_day():
    closes = _step_composite_scenario()
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                           confirm_days=3, commission_bps=0.0, slippage_bps=0.0,
                           initial_equity=100_000.0)
    result = run_regime_core(closes, cfg)
    assert len(result.switches) >= 1
    enter = next(sw for sw in result.switches if sw.action == "ENTER")
    signal_dates = result.regime_on[result.regime_on].index
    first_signal_date = signal_dates[0]
    # yürütme (ENTER tarihi), sinyalin karar tarihinden bir gün SONRA olmalı
    assert enter.date > first_signal_date
    idx_list = list(result.composite.index)
    assert idx_list.index(enter.date) == idx_list.index(first_signal_date) + 1


def test_run_regime_core_no_negative_cash_or_equity():
    closes = _step_composite_scenario()
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                           confirm_days=3, commission_bps=10.0, slippage_bps=5.0,
                           initial_equity=100_000.0)
    result = run_regime_core(closes, cfg)
    assert (result.equity_curve >= 0).all()


def test_run_regime_core_commission_reduces_equity_on_enter():
    closes = _step_composite_scenario()
    cfg_no_cost = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                                   confirm_days=3, commission_bps=0.0, slippage_bps=0.0,
                                   initial_equity=100_000.0)
    cfg_with_cost = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                                     confirm_days=3, commission_bps=50.0, slippage_bps=50.0,
                                     initial_equity=100_000.0)
    r_no_cost = run_regime_core(closes, cfg_no_cost)
    r_with_cost = run_regime_core(closes, cfg_with_cost)
    enter_no_cost = next(sw for sw in r_no_cost.switches if sw.action == "ENTER")
    enter_with_cost = next(sw for sw in r_with_cost.switches if sw.action == "ENTER")
    assert enter_with_cost.equity_after < enter_no_cost.equity_after


def test_run_regime_core_is_deterministic_across_runs():
    closes = _step_composite_scenario()
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                           confirm_days=3, commission_bps=10.0, slippage_bps=5.0,
                           initial_equity=100_000.0)
    r1 = run_regime_core(closes, cfg)
    r2 = run_regime_core(closes, cfg)
    assert r1.equity_curve.equals(r2.equity_curve)
    assert r1.switches == r2.switches


def test_run_regime_core_date_range_restricts_output_but_full_history_used_for_ma():
    closes = _step_composite_scenario()
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                           confirm_days=3, commission_bps=0.0, slippage_bps=0.0,
                           initial_equity=100_000.0)
    full = run_regime_core(closes, cfg)
    start, end = full.composite.index[30], full.composite.index[50]
    windowed = run_regime_core(closes, cfg, date_range=(start, end))
    assert windowed.equity_curve.index[0] >= start
    assert windowed.equity_curve.index[-1] < end
    # aynı aralıktaki equity değerleri, tam koşumla BİREBİR aynı olmalı
    # (warm-up/MA tam tarihçeden hesaplandığı için pencereleme sonucu etkilemez)
    overlap = full.equity_curve.loc[windowed.equity_curve.index]
    assert overlap.equals(windowed.equity_curve)


def test_run_regime_core_never_open_position_when_regime_off_throughout():
    closes = _flat_closes(["A", "B", "C"], n=250, base=100.0)
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=200, band_pct=0.01,
                           confirm_days=3, initial_equity=100_000.0)
    result = run_regime_core(closes, cfg)
    assert len(result.switches) == 0
    assert (result.equity_curve == 100_000.0).all()

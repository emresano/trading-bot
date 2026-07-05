from types import SimpleNamespace

import pandas as pd
import pytest

from core.models import SignalAction
from strategy.signal_engine import (
    ENTRY_GATES,
    compute_target,
    evaluate_entry,
    evaluate_exit,
    gate_atr_anomaly,
    gate_bb_overextension,
    gate_macd,
    gate_mtf,
    gate_regime,
    gate_rsi,
    gate_structure_rr,
    gate_trend,
    gate_trigger_4h,
    gate_volume,
)


def make_cfg():
    signal = SimpleNamespace(
        ema_fast=50, ema_slow=200,
        adx_min=20, rsi_entry_low=40, rsi_entry_high=55,
        atr_stop_mult=1.5, atr_anomaly_mult=2.0,
    )
    risk = SimpleNamespace(min_rr=1.8)
    return SimpleNamespace(signal=signal, risk=risk)


CFG = make_cfg()


def row(**fields) -> pd.Series:
    return pd.Series(fields)


# --- Tekil gate testleri: geçmesi gereken / kalması gereken durum + detail içeriği ---

def test_gate_trend_passes_in_uptrend():
    r = gate_trend(row(close=110, ema_200=95, ema_50=100), None, CFG)
    assert r.passed
    assert "close=110.00" in r.detail and "ema200=95.00" in r.detail


def test_gate_trend_fails_below_ema200():
    r = gate_trend(row(close=90, ema_200=95, ema_50=100), None, CFG)
    assert not r.passed


def test_gate_trend_fails_when_ema50_below_ema200():
    r = gate_trend(row(close=110, ema_200=95, ema_50=93), None, CFG)
    assert not r.passed


def test_gate_regime_passes_above_adx_min():
    r = gate_regime(row(adx=25), None, CFG)
    assert r.passed
    assert "ADX=25.00" in r.detail


def test_gate_regime_fails_below_adx_min():
    r = gate_regime(row(adx=15), None, CFG)
    assert not r.passed


def test_gate_rsi_passes_inside_band():
    r = gate_rsi(row(rsi=45), None, CFG)
    assert r.passed
    assert "RSI=45.00" in r.detail


@pytest.mark.parametrize("rsi_value", [10, 39.9, 55.1, 90])
def test_gate_rsi_fails_outside_band(rsi_value):
    assert not gate_rsi(row(rsi=rsi_value), None, CFG).passed


def test_gate_macd_passes_above_signal():
    r = gate_macd(row(macd=1.0, macd_signal=0.5, macd_hist=0.5, macd_hist_prev1=0.4), None, CFG)
    assert r.passed
    assert "above_signal=True" in r.detail


def test_gate_macd_passes_on_rising_hist_even_if_below_signal():
    r = gate_macd(row(macd=0.4, macd_signal=0.5, macd_hist=0.2, macd_hist_prev1=0.1), None, CFG)
    assert r.passed
    assert "hist_rising=True" in r.detail


def test_gate_macd_fails_below_signal_and_not_rising():
    r = gate_macd(row(macd=0.4, macd_signal=0.5, macd_hist=0.1, macd_hist_prev1=0.2), None, CFG)
    assert not r.passed


def test_gate_atr_anomaly_passes_normal_atr():
    r = gate_atr_anomaly(row(atr=5.0, atr_ma20=4.0), None, CFG)
    assert r.passed


def test_gate_atr_anomaly_fails_when_spiking():
    r = gate_atr_anomaly(row(atr=10.0, atr_ma20=4.0), None, CFG)  # 10 > 4*2.0
    assert not r.passed


def test_gate_bb_overextension_passes_inside_band():
    r = gate_bb_overextension(row(close=100, bb_high=105), None, CFG)
    assert r.passed


def test_gate_bb_overextension_fails_above_band():
    r = gate_bb_overextension(row(close=110, bb_high=105), None, CFG)
    assert not r.passed


def test_gate_structure_rr_passes_with_good_rr():
    # entry=100, stop=100-1.5*2=97, target(resistance)=110 -> rr=(110-100)/(100-97)=3.33
    r = gate_structure_rr(row(close=100, atr=2.0, nearest_resistance=110), None, CFG)
    assert r.passed
    assert "RR=3.33" in r.detail


def test_gate_structure_rr_fails_when_resistance_too_close():
    # entry=100, stop=97, target=101 -> rr=(101-100)/3=0.33 < 1.8
    r = gate_structure_rr(row(close=100, atr=2.0, nearest_resistance=101), None, CFG)
    assert not r.passed


def test_gate_structure_rr_uses_fallback_target_when_no_resistance():
    # nearest_resistance NaN -> target = entry + 2*(entry-stop) = 100 + 2*3 = 106
    # rr = (106-100)/3 = 2.0 >= 1.8
    r = gate_structure_rr(row(close=100, atr=2.0, nearest_resistance=float("nan")), None, CFG)
    assert r.passed


def test_compute_target_fallback_formula():
    d = row(close=100, atr=2.0, nearest_resistance=float("nan"))
    target = compute_target(d, CFG)
    assert target == pytest.approx(106.0)


def test_gate_volume_passes_when_confirmed():
    assert gate_volume(row(vol_confirm=True), None, CFG).passed


def test_gate_volume_fails_when_not_confirmed():
    assert not gate_volume(row(vol_confirm=False), None, CFG).passed


def test_gate_trigger_4h_uses_h4_row_when_present():
    d = row(pat_engulf=False, pat_pin=False, pat_inside_break=False)
    h4 = row(pat_engulf=True, pat_pin=False, pat_inside_break=False)
    r = gate_trigger_4h(d, h4, CFG)
    assert r.passed
    assert "mode=4h" in r.detail


def test_gate_trigger_4h_degrades_to_daily_when_h4_missing():
    d = row(pat_engulf=False, pat_pin=True, pat_inside_break=False)
    r = gate_trigger_4h(d, None, CFG)
    assert r.passed
    assert "mode=degrade(1d)" in r.detail


def test_gate_trigger_4h_fails_when_no_pattern():
    d = row(pat_engulf=False, pat_pin=False, pat_inside_break=False)
    assert not gate_trigger_4h(d, None, CFG).passed


def test_gate_mtf_skip_pass_when_no_h4():
    r = gate_mtf(row(), None, CFG)
    assert r.passed
    assert "SKIP-PASS" in r.detail


def test_gate_mtf_passes_when_4h_aligned():
    h4 = row(close=110, ema_50=100)
    assert gate_mtf(row(), h4, CFG).passed


def test_gate_mtf_fails_when_4h_contradicts():
    h4 = row(close=90, ema_50=100)
    assert not gate_mtf(row(), h4, CFG).passed


# --- Huni bütünü ---

def _daily_df_for_funnel(all_pass: bool) -> pd.DataFrame:
    """9 gate PASS + 1 (rsi) FAIL senaryosu üretir (all_pass=False),
    ya da 10 gate de PASS eden tam geçiş senaryosu (all_pass=True)."""
    base = dict(
        open=100, high=112, low=98, close=100,
        ema_50=100, ema_200=90,
        adx=25,
        rsi=45 if all_pass else 90,  # all_pass=False -> rsi gate FAIL
        macd=1.0, macd_signal=0.5, macd_hist=0.6,
        atr=2.0, atr_ma20=1.8,
        bb_low=90, bb_mid=100, bb_high=115,
        nearest_support=95, nearest_resistance=110,
        vol_confirm=True,
        pat_engulf=True, pat_pin=False, pat_inside_break=False,
        volume=5000,
    )
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    rows = [dict(base, macd_hist=0.4), dict(base, macd_hist=0.5), base]
    return pd.DataFrame(rows, index=idx)


def test_funnel_nine_pass_one_fail_yields_hold_cash_with_ten_reasons():
    # Daily tarafında hepsi PASS eden fixture'ı kullan, yalnızca son gate'i
    # (mtf) kontrollü biçimde FAIL ettirmek için 4h verisini trend ile çelişecek
    # şekilde ver — böylece önceki 9 gate PASS olurken huni tam 10 satır üretir.
    daily_df = _daily_df_for_funnel(all_pass=True)
    h4_df = pd.DataFrame(
        [dict(close=90, ema_50=100, pat_engulf=True, pat_pin=False, pat_inside_break=False)],
        index=pd.date_range("2024-01-03", periods=1, freq="4h", tz="UTC"),
    )
    sig = evaluate_entry("TEST", daily_df, h4_df, CFG)
    assert sig.action == SignalAction.HOLD_CASH
    assert len(sig.reasons) == 10
    passed = [ln for ln in sig.reasons if ln.startswith("[PASS]")]
    failed = [ln for ln in sig.reasons if ln.startswith("[FAIL]")]
    assert len(passed) == 9
    assert len(failed) == 1
    assert "mtf" in failed[0]


def test_funnel_short_circuits_before_last_gate_when_early_gate_fails():
    daily_df = _daily_df_for_funnel(all_pass=False)
    daily_df.iloc[-1, daily_df.columns.get_loc("close")] = 50  # gate_trend now fails first
    sig = evaluate_entry("TEST", daily_df, None, CFG)
    assert sig.action == SignalAction.HOLD_CASH
    assert len(sig.reasons) == 1
    assert sig.reasons[0].startswith("[FAIL] trend")


def test_funnel_all_pass_yields_enter_long_with_stop_and_target():
    daily_df = _daily_df_for_funnel(all_pass=True)
    sig = evaluate_entry("TEST", daily_df, None, CFG)
    assert sig.action == SignalAction.ENTER_LONG
    assert len(sig.reasons) == 10
    assert all(ln.startswith("[PASS]") for ln in sig.reasons)
    assert sig.suggested_stop == pytest.approx(100 - 1.5 * 2.0)
    assert sig.suggested_target == pytest.approx(110)
    assert sig.entry_ref_price == pytest.approx(100)


def test_evaluate_entry_features_snapshot_present():
    daily_df = _daily_df_for_funnel(all_pass=True)
    sig = evaluate_entry("TEST", daily_df, None, CFG)
    assert sig.features["rsi"] == pytest.approx(45)
    assert sig.features["close"] == pytest.approx(100)


# --- Çıkış mantığı ---

def test_evaluate_exit_holds_when_trend_and_momentum_intact():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    rows = [
        dict(close=98, ema_50=95, macd=1.0, macd_signal=0.8, macd_hist=0.3),
        dict(close=99, ema_50=96, macd=1.1, macd_signal=0.8, macd_hist=0.4),
        dict(close=100, ema_50=97, macd=1.2, macd_signal=0.8, macd_hist=0.5),
    ]
    daily_df = pd.DataFrame(rows, index=idx)
    sig = evaluate_exit("TEST", daily_df, CFG)
    assert sig.action == SignalAction.HOLD_POSITION


def test_evaluate_exit_triggers_on_close_below_ema50():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    rows = [
        dict(close=98, ema_50=95, macd=1.0, macd_signal=0.8, macd_hist=0.3),
        dict(close=99, ema_50=96, macd=1.1, macd_signal=0.8, macd_hist=0.4),
        dict(close=90, ema_50=97, macd=1.2, macd_signal=0.8, macd_hist=0.5),
    ]
    daily_df = pd.DataFrame(rows, index=idx)
    sig = evaluate_exit("TEST", daily_df, CFG)
    assert sig.action == SignalAction.EXIT_LONG


def test_evaluate_exit_triggers_on_momentum_collapse():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    rows = [
        dict(close=98, ema_50=90, macd=1.0, macd_signal=1.2, macd_hist=0.6),
        dict(close=99, ema_50=90, macd=0.9, macd_signal=1.2, macd_hist=0.4),
        dict(close=100, ema_50=90, macd=0.8, macd_signal=1.2, macd_hist=0.2),
    ]
    daily_df = pd.DataFrame(rows, index=idx)
    sig = evaluate_exit("TEST", daily_df, CFG)
    assert sig.action == SignalAction.EXIT_LONG


def test_entry_gates_registry_has_ten_components():
    assert len(ENTRY_GATES) == 10

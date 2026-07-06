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
    prepare_row_context,
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


def test_gate_structure_rr_target_floor_prevents_close_resistance_from_failing():
    # DÜZELTME: nearest_resistance çok yakın olsa bile (101), max(resistance, fallback)
    # sayesinde hedef en az entry+2R'ye (106) yükseltilir -> rr=2.0 >= min_rr=1.8 GEÇER.
    # Gerekçe: pullback girişinde en-yakın-direnç tanım gereği yakındır; onu doğrudan
    # hedef almak R:R'yi yapısal olarak neredeyse her zaman düşürüyordu.
    r = gate_structure_rr(row(close=100, atr=2.0, nearest_resistance=101), None, CFG)
    assert r.passed
    assert "RR=2.00" in r.detail


def test_gate_structure_rr_still_fails_when_min_rr_exceeds_fallback_floor():
    # fallback her zaman tam 2R garantiler; min_rr bunun üstündeyse (örn. sweep grid'in
    # en sıkı ucu 2.2) yakın resistance hâlâ yetersiz kalabilir.
    strict_cfg = SimpleNamespace(signal=CFG.signal, risk=SimpleNamespace(min_rr=2.2))
    r = gate_structure_rr(row(close=100, atr=2.0, nearest_resistance=101), None, strict_cfg)
    assert not r.passed


def test_gate_structure_rr_uses_fallback_target_when_no_resistance():
    # nearest_resistance NaN -> target = entry + 2*(entry-stop) = 100 + 2*3 = 106
    # rr = (106-100)/3 = 2.0 >= 1.8
    r = gate_structure_rr(row(close=100, atr=2.0, nearest_resistance=float("nan")), None, CFG)
    assert r.passed


def test_compute_target_uses_max_of_resistance_and_fallback():
    # resistance (110) fallback'ten (106) büyük -> resistance kazanır
    assert compute_target(row(close=100, atr=2.0, nearest_resistance=110), CFG) == pytest.approx(110.0)
    # resistance (101) fallback'ten (106) küçük -> 2R tabanı (fallback) kazanır
    assert compute_target(row(close=100, atr=2.0, nearest_resistance=101), CFG) == pytest.approx(106.0)


def test_compute_target_fallback_formula_when_resistance_nan():
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


def test_gate_trigger_4h_degrades_via_recent_pattern_within_3_bars():
    d = row(pattern_recent_3bar=True, close_above_prev_high=False)
    r = gate_trigger_4h(d, None, CFG)
    assert r.passed
    assert "mode=degrade(1d)" in r.detail
    assert "pattern_last_3bar=True" in r.detail


def test_gate_trigger_4h_degrades_via_breakout_above_prev_high():
    d = row(pattern_recent_3bar=False, close_above_prev_high=True)
    r = gate_trigger_4h(d, None, CFG)
    assert r.passed
    assert "close_above_prev_high=True" in r.detail


def test_gate_trigger_4h_fails_when_neither_recent_pattern_nor_breakout():
    d = row(pattern_recent_3bar=False, close_above_prev_high=False)
    assert not gate_trigger_4h(d, None, CFG).passed


def test_gate_trigger_4h_defaults_to_fail_when_context_fields_missing():
    # prepare_row_context çağrılmadan (alanlar yoksa) sessizce PASS değil, FAIL vermeli
    assert not gate_trigger_4h(row(), None, CFG).passed


# --- prepare_row_context: paylaşılan çoklu-bar bağlam hazırlayıcı ---

def _context_daily_df():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    return pd.DataFrame({
        "close": [100, 101, 99, 98, 105],
        "high": [101, 102, 100, 99, 106],
        "macd_hist": [0.1, 0.2, -0.1, -0.2, 0.3],
        "pat_engulf": [False, False, False, False, True],
        "pat_pin": [False, False, False, False, False],
        "pat_inside_break": [False, False, False, False, False],
    }, index=idx)


def test_prepare_row_context_macd_hist_prev1():
    df = _context_daily_df()
    d = prepare_row_context(df, 4)
    assert d["macd_hist_prev1"] == pytest.approx(-0.2)


def test_prepare_row_context_first_bar_has_nan_macd_hist_prev1():
    df = _context_daily_df()
    d = prepare_row_context(df, 0)
    assert pd.isna(d["macd_hist_prev1"])


def test_prepare_row_context_pattern_recent_3bar_looks_back_three_bars():
    df = _context_daily_df()
    d = prepare_row_context(df, 4)  # son bar: pat_engulf=True -> son 3 barda VAR
    assert d["pattern_recent_3bar"] is True

    d2 = prepare_row_context(df, 3)  # bar 3: kendisi ve önceki 2 bar hepsi False
    assert d2["pattern_recent_3bar"] is False


def test_prepare_row_context_close_above_prev_high():
    df = _context_daily_df()
    d = prepare_row_context(df, 4)  # close=105 > prev high=99
    assert d["close_above_prev_high"] is True

    d2 = prepare_row_context(df, 1)  # close=101, prev high=101 -> eşit, kesin büyük değil
    assert d2["close_above_prev_high"] is False


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


def test_disabled_gates_forces_automatic_pass():
    """Portföy ablasyon turu: `disabled_gates`'te ismi geçen gate hiç
    çağrılmaz, otomatik PASS sayılır — 9-PASS-1-FAIL (rsi) senaryosunda
    rsi'yi devre dışı bırakmak HOLD_CASH'i ENTER_LONG'a çevirmeli."""
    daily_df = _daily_df_for_funnel(all_pass=False)  # rsi FAIL eder
    sig = evaluate_entry("TEST", daily_df, None, CFG, disabled_gates={"rsi"})
    assert sig.action == SignalAction.ENTER_LONG
    assert len(sig.reasons) == 10
    rsi_reason = [ln for ln in sig.reasons if "rsi" in ln][0]
    assert rsi_reason.startswith("[PASS]")
    assert "DEVRE DIŞI" in rsi_reason


def test_disabled_gates_none_or_empty_matches_baseline():
    daily_df = _daily_df_for_funnel(all_pass=False)
    baseline = evaluate_entry("TEST", daily_df, None, CFG)
    with_none = evaluate_entry("TEST", daily_df, None, CFG, disabled_gates=None)
    with_empty = evaluate_entry("TEST", daily_df, None, CFG, disabled_gates=set())
    assert baseline.action == with_none.action == with_empty.action == SignalAction.HOLD_CASH
    assert baseline.reasons == with_none.reasons == with_empty.reasons


def test_disabled_gates_other_gate_still_evaluated_and_fails():
    """rsi FAIL eden senaryoda BAŞKA bir gate'i (örn. macd) devre dışı
    bırakmak sonucu değiştirmemeli — rsi hâlâ FAIL eder, HOLD_CASH kalır."""
    daily_df = _daily_df_for_funnel(all_pass=False)
    sig = evaluate_entry("TEST", daily_df, None, CFG, disabled_gates={"macd"})
    assert sig.action == SignalAction.HOLD_CASH
    rsi_reason = [ln for ln in sig.reasons if "rsi" in ln][0]
    assert rsi_reason.startswith("[FAIL]")


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

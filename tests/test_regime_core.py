import numpy as np
import pandas as pd
import pytest

from backtest.regime_core import (
    RegimeCoreConfig,
    build_composite,
    compute_cash_only_curve,
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


# --- S1b: nakit getirisi (cash_rate) — tek davranış değişikliği ---

def _cost_free_cfg():
    return RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                            confirm_days=3, commission_bps=0.0, slippage_bps=0.0,
                            initial_equity=100_000.0)


def test_cash_rate_none_is_byte_identical_to_s1_baseline():
    """ZORUNLU regresyon kanıtı (madde 2): cash_rate verilmezse (None,
    varsayılan) davranış S1 ile BİREBİR aynı kalmalı."""
    closes = _step_composite_scenario()
    cfg = _cost_free_cfg()
    baseline = run_regime_core(closes, cfg)  # cash_rate parametresi hiç verilmiyor (S1 çağrısı)
    explicit_none = run_regime_core(closes, cfg, cash_rate=None)
    assert baseline.equity_curve.equals(explicit_none.equity_curve)
    assert baseline.switches == explicit_none.switches


def test_cash_rate_all_zero_series_is_also_byte_identical_to_baseline():
    """ZORUNLU regresyon kanıtı (madde 2): TÜMÜ SIFIR bir faiz serisi
    verilse bile (None değil, gerçek bir Series) sonuç S1 ile BİREBİR
    aynı olmalı — mekanizmanın kendisinin matematiksel olarak etkisiz
    (r_net=0 -> cash *= 1.0) olduğunun kanıtı."""
    closes = _step_composite_scenario()
    cfg = _cost_free_cfg()
    baseline = run_regime_core(closes, cfg)
    zero_rate = pd.Series(0.0, index=closes["A"].index)
    result = run_regime_core(closes, cfg, cash_rate=zero_rate)
    assert baseline.equity_curve.equals(result.equity_curve)
    assert baseline.switches == result.switches


def test_cash_accrual_math_matches_act365_formula_on_flat_period():
    """Rejim hep KAPALI (hiç pozisyon açılmıyor) bir senaryoda, sabit bir
    yıllık faizle, N gün sonraki nakit bakiyesi ACT/365 üstel formülüyle
    BİREBİR eşleşmeli: cash_N = cash_0 * (1+r_net/365)^N (günlük bar
    aralığı = 1 takvim günü olduğundan her adımda üs artışı 1)."""
    closes = _flat_closes(["A", "B", "C"], n=30, base=100.0)  # hiçbir zaman rejim ON olmaz (ma_period=200 > 30)
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=200, band_pct=0.01,
                          confirm_days=3, initial_equity=100_000.0)
    annual_rate = 0.20  # %20
    rate_series = pd.Series(annual_rate, index=closes["A"].index)
    result = run_regime_core(closes, cfg, cash_rate=rate_series)

    r_net = annual_rate - 0.02  # 200bp kırpma
    expected = 100_000.0 * (1 + r_net / 365) ** np.arange(len(result.equity_curve))
    np.testing.assert_allclose(result.equity_curve.to_numpy(), expected, rtol=1e-9)


def test_cash_accrual_haircut_floors_at_zero_below_200bp():
    """Faiz 200bp'nin altındaysa (örn. %1) r_net negatif olmaz, SIFIRDA
    kırpılır -> nakit büyümez (ama KÜÇÜLMEZ de)."""
    closes = _flat_closes(["A", "B", "C"], n=30, base=100.0)
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=200, band_pct=0.01,
                          confirm_days=3, initial_equity=100_000.0)
    low_rate = pd.Series(0.01, index=closes["A"].index)  # %1 < 200bp kırpma
    result = run_regime_core(closes, cfg, cash_rate=low_rate)
    assert (result.equity_curve == 100_000.0).all()  # r_net=0 -> hiç büyüme, hiç küçülme


def test_cash_accrual_uses_calendar_days_not_trading_days():
    """Hafta sonu atlanan (Cuma->Pazartesi) bir tarih dizisinde, o
    aralıktaki tahakkuk 1 değil 3 TAKVİM günü üzerinden hesaplanmalı."""
    # Cuma, sonra (hafta sonu atlanarak) Pazartesi -> Salı ... (iş günü indeksi)
    dates = pd.bdate_range("2020-01-03", periods=10, tz="UTC")  # is günleri (haftaici)
    closes = {s: pd.Series(100.0, index=dates) for s in ["A", "B", "C"]}
    cfg = RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=200, band_pct=0.01,
                          confirm_days=3, initial_equity=100_000.0)
    annual_rate = 0.20
    rate_series = pd.Series(annual_rate, index=dates)
    result = run_regime_core(closes, cfg, cash_rate=rate_series)

    r_net = annual_rate - 0.02
    # Cuma (2020-01-03) -> Pazartesi (2020-01-06): 3 takvim günü farkı
    gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    assert 3 in gaps  # hafta sonu atlaması gerçekten 3 günlük bir boşluk yaratmış olmalı
    expected = [100_000.0]
    acc = 100_000.0
    for g in gaps:
        acc *= (1 + r_net / 365) ** g
        expected.append(acc)
    np.testing.assert_allclose(result.equity_curve.to_numpy(), np.array(expected), rtol=1e-9)


def test_cash_accrual_ratio_stable_while_in_position_then_grows_after_exit():
    """Pozisyondayken (ENTER dahil, EXIT dahil) faizli/faizsiz equity ORANI
    yaklaşık SABİT kalmalı (o dönemde YENİ tahakkuk yok — ENTER günündeki
    TEK seferlik tahakkuk yüzünden kalan küçük nakit artığının fiyat
    hareketiyle payı kaydığından ufak bir sürüklenme olabilir, ama bu EXIT
    sonrası büyümeyle KIYASLANAMAYACAK kadar küçük olmalı). EXIT'ten SONRAKİ
    günden itibaren oran BELİRGİN ŞEKİLDE artmalı (nakit tekrar tahakkuk
    ediyor)."""
    closes = _step_composite_scenario()
    cfg = _cost_free_cfg()
    rate_series = pd.Series(0.30, index=closes["A"].index)

    r_no_rate = run_regime_core(closes, cfg)
    r_with_rate = run_regime_core(closes, cfg, cash_rate=rate_series)

    enter = next(sw for sw in r_no_rate.switches if sw.action == "ENTER")
    exit_sw = next(sw for sw in r_no_rate.switches if sw.action == "EXIT")
    ratio = r_with_rate.equity_curve / r_no_rate.equity_curve

    in_position_ratios = ratio.loc[enter.date:exit_sw.date]
    in_position_drift = in_position_ratios.max() - in_position_ratios.min()
    assert in_position_drift < 1e-3  # kalıntı nakdin fiyat-ağırlıklı ufak sürüklenmesi

    idx_list = list(ratio.index)
    day_after_exit = idx_list[idx_list.index(exit_sw.date) + 1]
    ten_days_after_exit = idx_list[min(idx_list.index(exit_sw.date) + 10, len(idx_list) - 1)]
    growth_after_exit = ratio.loc[ten_days_after_exit] - ratio.loc[day_after_exit]
    assert growth_after_exit > in_position_drift * 10  # net tahakkuk büyümesi, kalıntı sürüklenmeden AÇIKÇA büyük


def test_cash_accrual_excluded_exactly_on_exit_day():
    """EXIT gününün KENDİSİNDE hiç tahakkuk uygulanmamalı: EXIT günü
    equity'sinin faizli/faizsiz oranı, ENTER gününkiyle (o ana kadar tek
    kaynak ENTER'daki tek seferlik tahakkuk) yaklaşık aynı olmalı —
    ENTER'dan EXIT'e kadar ORANDA sıçrama YOK."""
    closes = _step_composite_scenario()
    cfg = _cost_free_cfg()
    rate_series = pd.Series(0.30, index=closes["A"].index)

    r_no_rate = run_regime_core(closes, cfg)
    r_with_rate = run_regime_core(closes, cfg, cash_rate=rate_series)

    enter = next(sw for sw in r_no_rate.switches if sw.action == "ENTER")
    exit_sw = next(sw for sw in r_no_rate.switches if sw.action == "EXIT")
    ratio = r_with_rate.equity_curve / r_no_rate.equity_curve

    assert ratio.loc[exit_sw.date] == pytest.approx(ratio.loc[enter.date], abs=1e-3)


def test_cash_rate_run_is_deterministic_across_runs():
    closes = _step_composite_scenario()
    cfg = _cost_free_cfg()
    rate_series = pd.Series(0.20, index=closes["A"].index)
    r1 = run_regime_core(closes, cfg, cash_rate=rate_series)
    r2 = run_regime_core(closes, cfg, cash_rate=rate_series)
    assert r1.equity_curve.equals(r2.equity_curve)
    assert r1.switches == r2.switches


def test_compute_cash_only_curve_matches_act365_formula():
    idx = pd.date_range("2020-01-01", periods=10, freq="1D", tz="UTC")
    rate = pd.Series(0.20, index=idx)
    curve = compute_cash_only_curve(idx, rate, 100_000.0)
    r_net = 0.20 - 0.02
    expected = 100_000.0 * (1 + r_net / 365) ** np.arange(len(idx))
    np.testing.assert_allclose(curve.to_numpy(), expected, rtol=1e-9)


def test_compute_cash_only_curve_below_haircut_stays_flat():
    idx = pd.date_range("2020-01-01", periods=5, freq="1D", tz="UTC")
    rate = pd.Series(0.01, index=idx)
    curve = compute_cash_only_curve(idx, rate, 100_000.0)
    assert (curve == 100_000.0).all()

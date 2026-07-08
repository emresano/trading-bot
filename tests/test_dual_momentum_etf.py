# tests/test_dual_momentum_etf.py
"""D4US-S1 — varlık-sınıfı ETF dual-momentum simülatörü
(backtest/dual_momentum_etf.py) testleri.

Kanıtlanan iddialar:
  1. Determinizm (aynı girdi → bayt-özdeş equity + rebalans dizisi).
  2. Look-ahead YASAĞI: her rebalans SONRAKİ işlem gününde yürütülür (exec > signal,
     bitişik gün) — sinyal barının KENDİSİNDE fill yok (t+1).
  3. Göreli momentum: top-N, formation getirisi en yüksek N sembolü seçer.
  4. Mutlak-momentum kapısı: 12-0 getirisi T-bill formation-penceresi getirisinin
     ALTINDA olan slot NAKİT (invested boşalır); kapı kapalıyken yatırılır.
  5. Vol-hedefleme YOK: tek yatırılan slot ~tam equity alır (maruziyet = 1, ölçekleme yok).
  6. Nakit tahakkuku: tam-nakit ısınmada equity DGS3MO−50bp ile büyür (S1b formülü).
  7. Isınma öncesi pozisyon yok (formation_months tamamlanana dek).
  8. t0 KIRPMA (ragged ETF başlangıcı): fiyat matrisi en geç başlayanın ilk gününe
     kırpılır, lider-NaN yok — build_composite ile aynı t0.
  9. Headline regresyon çapası (gerçek ETF snapshot, mühürlü tam paket).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.dual_momentum_etf import (
    DualMomentumEtfConfig,
    _build_price_matrix,
    run_dual_momentum_etf,
)
from costs.us_equities import UsEquitiesCostModel


def _idx(n: int = 420) -> pd.DatetimeIndex:
    return pd.date_range("2004-01-02", periods=n, freq="B", tz="UTC")


def _us_cm() -> UsEquitiesCostModel:
    return UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.28,
                               taf_per_share=0.000166, slippage_bps=5.0)


def _steady(idx, daily, start=100.0) -> pd.Series:
    return pd.Series(start * (1 + daily) ** np.arange(len(idx)), index=idx)


def _universe() -> dict[str, pd.Series]:
    """5 sembol, kesin sıralı 12-0 momentum: A>B>C>D>E."""
    idx = _idx()
    return {"A": _steady(idx, 0.0020), "B": _steady(idx, 0.0015),
            "C": _steady(idx, 0.0010), "D": _steady(idx, 0.0005),
            "E": _steady(idx, -0.0010)}


def _cfg(**kw) -> DualMomentumEtfConfig:
    base = dict(symbols=["A", "B", "C", "D", "E"], formation_months=12,
                skip_months=0, top_n=3, use_abs_gate=False, initial_equity=100_000.0)
    base.update(kw)
    return DualMomentumEtfConfig(**base)


def test_determinism():
    closes = _universe()
    cfg = _cfg(use_abs_gate=True)
    rate = pd.Series(0.03, index=closes["A"].index)
    a = run_dual_momentum_etf(closes, cfg, _us_cm(), cash_rate=rate)
    b = run_dual_momentum_etf(closes, cfg, _us_cm(), cash_rate=rate)
    pd.testing.assert_series_equal(a.equity_curve, b.equity_curve)
    assert [(r.signal_date, r.exec_date, tuple(r.invested)) for r in a.rebalances] == \
           [(r.signal_date, r.exec_date, tuple(r.invested)) for r in b.rebalances]


def test_no_lookahead_execution_is_next_day():
    res = run_dual_momentum_etf(_universe(), _cfg(), _us_cm())
    all_dates = list(res.all_dates)
    assert len(res.rebalances) >= 2
    for r in res.rebalances:
        assert r.exec_date > r.signal_date                       # sinyal barında fill YOK
        i = all_dates.index(r.signal_date)
        assert all_dates[i + 1] == r.exec_date                   # tam bir sonraki işlem günü (t+1)


def test_top_n_selects_highest_formation_returns():
    res = run_dual_momentum_etf(_universe(), _cfg(top_n=3), _us_cm())
    # A>B>C>D>E momentum sıralaması → top-3 = [A, B, C] (azalan sıra).
    assert res.rebalances[0].selected == ["A", "B", "C"]
    assert set(res.rebalances[0].invested) == {"A", "B", "C"}    # kapı kapalı → hepsi yatırılır
    # top_n=2 → [A, B].
    res2 = run_dual_momentum_etf(_universe(), _cfg(top_n=2), _us_cm())
    assert res2.rebalances[0].selected == ["A", "B"]


def test_12_0_uses_current_month_end_not_skipped():
    """skip_months=0 → formation num_date = m[j] (sinyal ayı sonu), atlama YOK."""
    res = run_dual_momentum_etf(_universe(), _cfg(), _us_cm())
    all_dates = list(res.all_dates)
    r0 = res.rebalances[0]
    # 12-0: sinyal günü, formation üst sınırı m[j] ile AYNI ay-sonudur → signal_date
    # bir ay-sonudur ve exec bir sonraki gündür. (12-1 olsaydı num m[j-1] olurdu.)
    i = all_dates.index(r0.signal_date)
    assert all_dates[i + 1] == r0.exec_date


def test_abs_gate_single_winner_below_tbill_goes_cash():
    closes = _universe()
    idx = closes["A"].index
    # A formation (daily 0.0020, ~252 gün) ~65%; rate 0.80 → ~1yr ACT/365 accrual ~123% > 65%.
    high_rate = pd.Series(0.80, index=idx)
    # Kapı KAPALI: A yatırılır.
    off = run_dual_momentum_etf(closes, _cfg(top_n=1, use_abs_gate=False), _us_cm(),
                                cash_rate=high_rate)
    assert off.rebalances[0].invested == ["A"]
    # Kapı AÇIK: A 12-0 (~65%) < T-bill (~123%) → NAKİT.
    on = run_dual_momentum_etf(closes, _cfg(top_n=1, use_abs_gate=True), _us_cm(),
                               cash_rate=high_rate)
    assert on.rebalances[0].invested == []
    assert on.rebalances[0].n_cash_slots == 1


def test_abs_gate_all_declining_universe_all_cash():
    """Tüm evren düşüşte + pozitif T-bill → top-N seçilir ama HEPSİ nakde gider."""
    idx = _idx()
    closes = {s: _steady(idx, -0.0005) for s in ["A", "B", "C", "D", "E"]}
    rate = pd.Series(0.02, index=idx)        # pozitif T-bill; tüm formation'lar negatif
    on = run_dual_momentum_etf(closes, _cfg(top_n=3, use_abs_gate=True), _us_cm(), cash_rate=rate)
    assert all(r.invested == [] for r in on.rebalances)
    assert all(r.n_cash_slots == 3 for r in on.rebalances)
    # Kapı kapalı → top-3 yatırılır (nakit değil).
    off = run_dual_momentum_etf(closes, _cfg(top_n=3, use_abs_gate=False), _us_cm(), cash_rate=rate)
    assert all(len(r.invested) == 3 for r in off.rebalances)


def test_no_vol_targeting_single_slot_takes_full_equity():
    """Vol-hedefleme YOK → tek yatırılan slot ~tam equity alır (per_slot = equity/top_n,
    top_n=1 → tüm equity; hiçbir ölçekleme/kaldıraç yok). Kanıt: exec'ten SONRA equity'nin
    günlük getirisi ≈ kazananın (A) günlük getirisi (~%100 maruziyet), cash_rate=None."""
    res = run_dual_momentum_etf(_universe(), _cfg(top_n=1, use_abs_gate=False), _us_cm())
    r0 = res.rebalances[0]
    assert r0.invested == ["A"]
    daily_ret = res.equity_curve.pct_change()
    # exec'ten ~5 iş günü sonra (yeniden rebalans olmadan) equity, A'nın günlük getirisini izler.
    after = daily_ret.loc[r0.exec_date:].iloc[1:6]
    # ~%100 A maruziyeti → günlük getiri ≈ 0.0020 (küçük yuvarlama-nakdi seyreltmesiyle).
    assert after.mean() == pytest.approx(0.0020, rel=0.05)
    assert (after > 0.0018).all()   # ölçeklenmemiş: A getirisinin >%90'ı


def test_cash_warmup_accrues_at_haircut_rate():
    """İlk formation_months ay boyunca tam-nakit: equity, DGS3MO−50bp ile büyümeli."""
    closes = _universe()
    idx = closes["A"].index
    rate = pd.Series(0.05, index=idx)        # %5 yıllık; net = 5%−0.5% = 4.5%
    res = run_dual_momentum_etf(closes, _cfg(), _us_cm(), cash_rate=rate, cashleg_haircut=0.005)
    warmup = res.equity_curve.loc[: res.rebalances[0].signal_date]
    assert warmup.iloc[-1] > warmup.iloc[0]
    assert (warmup.diff().dropna() >= -1e-6).all()
    yrs = (warmup.index[-1] - warmup.index[0]).days / 365.25
    approx = (1 + 0.045) ** yrs
    assert warmup.iloc[-1] / warmup.iloc[0] == pytest.approx(approx, rel=0.03)


def test_no_position_before_warmup_completes():
    res = run_dual_momentum_etf(_universe(), _cfg(), _us_cm())
    # İlk rebalans sinyali en erken 12. ay-sonunda (formation ısınması).
    assert res.rebalances[0].signal_date > _universe()["A"].index[0] + pd.DateOffset(months=11)


def test_price_matrix_clips_to_latest_inception_no_leading_nan():
    """Ragged başlangıç: geç-başlayan sembol matris t0'ını bağlar; lider-NaN yok."""
    idx = _idx(200)
    early = _steady(idx, 0.001)                       # 200 gün
    late = _steady(idx[40:], 0.001)                   # 40 gün geç başlar
    mat = _build_price_matrix({"EARLY": early, "LATE": late})
    assert mat.index[0] == idx[40]                     # t0 = en geç başlayan
    assert not mat.isna().any().any()                  # hiç NaN yok (lider dahil)
    assert mat["EARLY"].iloc[0] == pytest.approx(early.loc[idx[40]])


def test_d4_us_headline_numbers_regression():
    """D4_US_S1.md headline mekanik sayılarını (gerçek ETF snapshot, mühürlü tam paket)
    ÇAPA alır — sessiz sapmayı yakalar + determinizm garantisi (E4/D2US emsali)."""
    import yaml
    from tools.e4_common import load_us_closes
    from tools.run_regime_core import compute_summary

    cfg = yaml.safe_load(open("config/dual_momentum_etf.yaml", encoding="utf-8"))
    closes, _ = load_us_closes(cfg)
    d = cfg["design"]
    xcfg = DualMomentumEtfConfig(
        symbols=cfg["symbols"], formation_months=d["formation_months"],
        skip_months=d["skip_months"], top_n=d["top_n"],
        use_abs_gate=d["abs_momentum_gate"]["enabled"],
        abs_gate_haircut=d["abs_momentum_gate"]["haircut_bps"] / 1e4,
        initial_equity=cfg["initial_equity"])
    cm = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.28,
                             taf_per_share=0.000166, slippage_bps=5.0)
    rate = pd.read_parquet(cfg["cash_yield"]["aux_snapshot"])["rate_pct"] / 100.0
    res = run_dual_momentum_etf(closes, xcfg, cm, cash_rate=rate,
                                cashleg_haircut=cfg["cash_yield"]["haircut_bps"] / 1e4)
    s = compute_summary(res.equity_curve)
    assert len(res.rebalances) == 233
    assert s["sharpe"] == pytest.approx(0.54621, abs=5e-4)
    assert s["cagr"] == pytest.approx(0.06667, abs=5e-4)
    assert s["max_drawdown"] == pytest.approx(-0.25724, abs=5e-4)

# tests/test_xsec_momentum.py
"""D2US-S1 — kesitsel momentum simülatörü (backtest/xsec_momentum.py) testleri.

Kanıtlanan iddialar:
  1. Determinizm (aynı girdi → bayt-özdeş equity + rebalans dizisi).
  2. Look-ahead YASAĞI: her rebalans SONRAKİ işlem gününde yürütülür (exec > signal,
     bitişik gün) — sinyal barının KENDİSİNDE fill yok (t+1).
  3. FIP information-discreteness: momentumu DAHA DÜŞÜK ama daha SÜREKLİ (düşük ID)
     aday, use_fip=True'da momentumu daha yüksek ama süreksiz (yüksek ID) adaya
     TERCİH edilir; use_fip=False'da yalın momentum lideri seçilir.
  4. Mutlak-momentum kapısı: 12-1 getirisi T-bill formation-penceresi getirisinin
     ALTINDA olan slot NAKİT (invested boşalır); kapı kapalıyken yatırılır.
  5. Vol-hedefleme: maruziyet HER ZAMAN ≤ max_leverage (kaldıraç YOK); çok küçük
     target_vol → maruziyet < 1; çok büyük target_vol → maruziyet = max_leverage.
  6. Nakit tahakkuku: tam-nakit ısınmada equity DGS3MO−50bp ile büyür (S1b formülü).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.xsec_momentum import XSecMomentumConfig, run_xsec_momentum
from costs.us_equities import UsEquitiesCostModel


def _idx(n: int = 420) -> pd.DatetimeIndex:
    return pd.date_range("2004-01-02", periods=n, freq="B", tz="UTC")


def _us_cm() -> UsEquitiesCostModel:
    return UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.28,
                               taf_per_share=0.000166, slippage_bps=5.0)


def _steady_up(idx, daily=0.0015, start=100.0) -> pd.Series:
    return pd.Series(start * (1 + daily) ** np.arange(len(idx)), index=idx)


def _jumpy_up(idx, up=0.03, down=-0.0005, period=10, start=100.0) -> pd.Series:
    """Çoğu gün küçük negatif, her `period` günde bir büyük pozitif sıçrama →
    yüksek toplam getiri ama düşük süreklilik (yüksek ID)."""
    rets = np.where(np.arange(len(idx)) % period == 0, up, down)
    px = start * np.cumprod(1 + rets)
    return pd.Series(px, index=idx)


def _decline(idx, daily=-0.001, start=100.0) -> pd.Series:
    return pd.Series(start * (1 + daily) ** np.arange(len(idx)), index=idx)


def _fip_universe() -> dict[str, pd.Series]:
    idx = _idx()
    return {"CONT": _steady_up(idx), "JUMP": _jumpy_up(idx),
            "FILL1": _decline(idx), "FILL2": _decline(idx, daily=-0.0012)}


def _fip_cfg(**kw) -> XSecMomentumConfig:
    base = dict(symbols=["CONT", "JUMP", "FILL1", "FILL2"], formation_months=12,
                skip_months=1, preselect_top=2, final_n=1, use_vol_target=False,
                use_abs_gate=False, initial_equity=100_000.0)
    base.update(kw)
    return XSecMomentumConfig(**base)


def test_determinism():
    closes, cfg = _fip_universe(), _fip_cfg(use_vol_target=True, use_abs_gate=True)
    a = run_xsec_momentum(closes, cfg, _us_cm())
    b = run_xsec_momentum(closes, cfg, _us_cm())
    pd.testing.assert_series_equal(a.equity_curve, b.equity_curve)
    assert [(r.signal_date, r.exec_date, tuple(r.invested), r.exposure) for r in a.rebalances] == \
           [(r.signal_date, r.exec_date, tuple(r.invested), r.exposure) for r in b.rebalances]


def test_no_lookahead_execution_is_next_day():
    closes = _fip_universe()
    res = run_xsec_momentum(closes, _fip_cfg(), _us_cm())
    all_dates = list(res.all_dates)
    assert len(res.rebalances) >= 2
    for r in res.rebalances:
        assert r.exec_date > r.signal_date                       # sinyal barında fill YOK
        i = all_dates.index(r.signal_date)
        assert all_dates[i + 1] == r.exec_date                   # tam bir sonraki işlem günü (t+1)


def test_fip_prefers_continuous_over_higher_but_discrete_momentum():
    closes = _fip_universe()
    # JUMP momentumu CONT'tan YÜKSEK (kontrol): yalın momentum liderini seçmeli.
    r_nofip = run_xsec_momentum(closes, _fip_cfg(use_fip=False), _us_cm())
    assert r_nofip.rebalances[0].selected == ["JUMP"]
    # FIP açık: CONT (düşük ID) TERCİH edilmeli.
    r_fip = run_xsec_momentum(closes, _fip_cfg(use_fip=True), _us_cm())
    assert r_fip.rebalances[0].selected == ["CONT"]


def test_abs_momentum_gate_sends_below_tbill_to_cash():
    closes = _fip_universe()
    idx = closes["CONT"].index
    high_rate = pd.Series(0.50, index=idx)   # %50 → formation-penceresi T-bill ~%58 > CONT ~%40
    # Kapı KAPALI: CONT yatırılır.
    r_off = run_xsec_momentum(closes, _fip_cfg(use_fip=True, use_abs_gate=False),
                              _us_cm(), cash_rate=high_rate)
    assert r_off.rebalances[0].invested == ["CONT"]
    # Kapı AÇIK: CONT 12-1 (~%40) < T-bill (~%58) → NAKİT.
    r_on = run_xsec_momentum(closes, _fip_cfg(use_fip=True, use_abs_gate=True),
                             _us_cm(), cash_rate=high_rate)
    assert r_on.rebalances[0].invested == []
    assert r_on.rebalances[0].n_cash_slots == 1


def test_vol_target_never_levers_and_scales_down():
    closes = _fip_universe()
    # Çok büyük target_vol → maruziyet daima max_leverage (kaldıraç sınırında sabit).
    r_big = run_xsec_momentum(closes, _fip_cfg(use_vol_target=True, target_vol=100.0), _us_cm())
    assert all(r.exposure == 1.0 for r in r_big.rebalances)
    # Çok küçük target_vol → en az bir rebalansta maruziyet < 1, ve HİÇBİR zaman > max_leverage.
    r_small = run_xsec_momentum(closes, _fip_cfg(use_vol_target=True, target_vol=0.005), _us_cm())
    assert all(r.exposure <= 1.0 + 1e-12 for r in r_small.rebalances)
    assert any(r.exposure < 1.0 for r in r_small.rebalances)


def test_cash_warmup_accrues_at_haircut_rate():
    """İlk formation_months ay boyunca tam-nakit: equity, DGS3MO−50bp ile büyümeli."""
    closes = _fip_universe()
    idx = closes["CONT"].index
    rate = pd.Series(0.05, index=idx)   # %5 yıllık; net = 5%−0.5% = 4.5%
    res = run_xsec_momentum(closes, _fip_cfg(), _us_cm(), cash_rate=rate, cashleg_haircut=0.005)
    # Isınma = ilk sinyal gününe KADAR (tam-nakit); ilk işlem SONRAKİ gün (exec) olur.
    warmup = res.equity_curve.loc[: res.rebalances[0].signal_date]
    # Isınma boyunca monoton artan (yalnız faiz) ve ilk günden büyük.
    assert warmup.iloc[-1] > warmup.iloc[0]
    assert (warmup.diff().dropna() >= -1e-6).all()
    # Kaba büyüklük kontrolü: ~1 yıl %4.5 → ~%3.5-5 arası.
    yrs = (warmup.index[-1] - warmup.index[0]).days / 365.25
    approx = (1 + 0.045) ** yrs
    assert warmup.iloc[-1] / warmup.iloc[0] == pytest.approx(approx, rel=0.03)


def test_no_position_before_warmup_completes():
    """formation_months tamamlanmadan hiçbir rebalans (pozisyon) olmamalı."""
    closes = _fip_universe()
    res = run_xsec_momentum(closes, _fip_cfg(), _us_cm())
    # İlk rebalans sinyali en erken 12. ay-sonunda → exec_date ~13. ay.
    assert res.rebalances[0].signal_date > closes["CONT"].index[0] + pd.DateOffset(months=11)


def test_d2_us_headline_numbers_regression():
    """D2_US_S1.md headline mekanik sayılarını (gerçek US2 snapshot, mühürlü tam
    paket) ÇAPA alır — sessiz sapmayı yakalar + determinizm garantisi. E4 emsali."""
    import yaml
    from tools.e4_common import load_us_closes
    from tools.run_regime_core import compute_summary
    from tools.run_xsec_momentum_us2 import build_xsec_cfg

    cfg = yaml.safe_load(open("config/momentum_us2.yaml", encoding="utf-8"))
    closes, _ = load_us_closes(cfg)
    xcfg = build_xsec_cfg(cfg)
    cm = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.28,
                             taf_per_share=0.000166, slippage_bps=5.0)
    rate = pd.read_parquet(cfg["cash_yield"]["aux_snapshot"])["rate_pct"] / 100.0
    res = run_xsec_momentum(closes, xcfg, cm, cash_rate=rate,
                            cashleg_haircut=cfg["cash_yield"]["haircut_bps"] / 1e4)
    s = compute_summary(res.equity_curve)
    assert len(res.rebalances) == 246
    assert s["sharpe"] == pytest.approx(0.72540, abs=5e-4)
    assert s["cagr"] == pytest.approx(0.10875, abs=5e-4)
    assert s["max_drawdown"] == pytest.approx(-0.32610, abs=5e-4)

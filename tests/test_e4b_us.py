# tests/test_e4b_us.py
"""EXPANSION E4b — D1-US nakit tahakkuku (US 3-aylık T-bill, 50bp haircut) testleri.

Kanıtlar:
  1. TEK-DEĞİŞİKLİK İZOLASYONU: %0 (cash_rate=None) koşumu E4 headline'ını bayt-
     bayt yeniden üretir; faizli koşum AYNI anahtarlama tarihlerini üretir (nakit
     sinyali etkilemez).
  2. Haircut mekaniği: rate>haircut → nakit büyür; rate≤haircut → tahakkuk yok
     (r_net=0 → %0 ile bayt-eşdeğer).
  3. E4b faizli headline REGRESYONU (57 switch, Sharpe/CAGR/maxDD çapa).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.regime_core import RegimeCoreConfig
from backtest.regime_core_us import run_regime_core_costmodel
from costs.us_equities import UsEquitiesCostModel, us_cost_model_from_config
from tools.e4_common import load_us_closes, load_us_config
from tools.run_regime_core import compute_summary


def _load():
    cfg = load_us_config()
    closes, _ = load_us_closes(cfg)
    reg, c = cfg["regime"], cfg["costs"]
    core = RegimeCoreConfig(symbols=cfg["symbols"], ma_period=reg["ma_period"], band_pct=reg["band_pct"],
                            confirm_days=reg["confirm_days"], commission_bps=c["commission_bps"],
                            slippage_bps=c["slippage_bps"], initial_equity=cfg["initial_equity"])
    cm = us_cost_model_from_config(c)
    cash_rate = pd.read_parquet(cfg["cash_yield"]["aux_snapshot"])["rate_pct"] / 100.0
    haircut = cfg["cash_yield"]["haircut_bps"] / 1e4
    return cfg, closes, core, cm, cash_rate, haircut


def test_single_change_isolation_switches_and_zero_reproduce_e4():
    _cfg, closes, core, cm, cash_rate, haircut = _load()
    r0 = run_regime_core_costmodel(closes, core, cm, cash_rate=None)
    ry = run_regime_core_costmodel(closes, core, cm, cash_rate=cash_rate, haircut=haircut)
    # Nakit sinyali/anahtarlamayı ETKİLEMEZ:
    assert [(s.date, s.action) for s in r0.switches] == [(s.date, s.action) for s in ry.switches]
    # %0 koşumu = E4 headline (bayt-bayt tek-değişiklik çapası):
    s0 = compute_summary(r0.equity_curve)
    assert len(r0.switches) == 57
    assert s0["max_drawdown"] == pytest.approx(-0.23106, abs=5e-4)
    assert s0["sharpe"] == pytest.approx(0.7262, abs=5e-4)


def test_yield_increases_equity_when_rate_above_haircut():
    _cfg, closes, core, cm, cash_rate, haircut = _load()
    r0 = run_regime_core_costmodel(closes, core, cm, cash_rate=None)
    ry = run_regime_core_costmodel(closes, core, cm, cash_rate=cash_rate, haircut=haircut)
    # DGS3MO çoğu dönemde 50bp üstü → faizli nihai equity daha yüksek.
    assert ry.equity_curve.iloc[-1] > r0.equity_curve.iloc[-1]


def test_rate_at_or_below_haircut_yields_no_accrual():
    """rate ≤ haircut → r_net=max(rate-haircut,0)=0 → nakit büyümez → %0 ile aynı."""
    _cfg, closes, core, cm, _cash_rate, haircut = _load()
    all_dates = next(iter(closes.values())).index
    flat_low = pd.Series(haircut, index=all_dates)  # tam haircut seviyesinde → net 0
    r0 = run_regime_core_costmodel(closes, core, cm, cash_rate=None)
    rlow = run_regime_core_costmodel(closes, core, cm, cash_rate=flat_low, haircut=haircut)
    pd.testing.assert_series_equal(r0.equity_curve, rlow.equity_curve)


def test_e4b_yield_headline_regression():
    _cfg, closes, core, cm, cash_rate, haircut = _load()
    ry = run_regime_core_costmodel(closes, core, cm, cash_rate=cash_rate, haircut=haircut)
    s = compute_summary(ry.equity_curve)
    assert len(ry.switches) == 57
    assert s["cagr"] == pytest.approx(0.08599, abs=5e-4)
    assert s["max_drawdown"] == pytest.approx(-0.23111, abs=5e-4)
    assert s["sharpe"] == pytest.approx(0.75784, abs=5e-4)


def test_haircut_param_default_is_s1b_200bps():
    """Regresyon: haircut default'u 0.02 (S1b/TRY 200bp) olmalı — imza değişmedi."""
    import inspect
    sig = inspect.signature(run_regime_core_costmodel)
    assert sig.parameters["haircut"].default == pytest.approx(0.02)

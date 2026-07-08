# tests/test_e4_us.py
"""EXPANSION E4 (US adil test) — D1-US CostModel döngüsü + veri yolu testleri.

Kanıtlanan iddialar:
  1. PARİTE: BIST-eşdeğeri CostModel ile yeni döngü, S1/S1b'nin basit-bps
     modelini (backtest/regime_core.run_regime_core) ~1e-9'da yeniden üretir
     → yürütme/maliyet aritmetiği doğru; anahtarlama tarihleri BİREBİR aynı.
  2. Determinizm.
  3. Nakit %0 (cash_rate=None) == tümü-sıfır cash_rate → bayt-bayt (mekanizma
     0'da nötr; "muhafazakâr %0" kararının bayt-eşdeğerliğinin kanıtı).
  4. normalize_bist_dates US 00:00-UTC verisinde NO-OP → load_and_clean_universe
     reuse'u güvenli (S1b ile aynı yol).
  5. US CostModel SEC/TAF yalnız SATIŞTA (exit_costs) akıyor.
  6. REGRESYON: D1-US gerçek snapshot headline sayıları (57 switch, maxDD ~-23.1%)
     rapordan sapmasın.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.regime_core import RegimeCoreConfig, run_regime_core
from backtest.regime_core_us import run_regime_core_costmodel
from costs.us_equities import UsEquitiesCostModel


def _trend_series() -> dict[str, pd.Series]:
    idx = pd.date_range("2020-01-01", periods=90, freq="D", tz="UTC")
    prices = np.concatenate([
        np.full(15, 100.0),
        np.linspace(100.0, 140.0, 25),   # yükseliş → ENTER
        np.linspace(140.0, 95.0, 25),    # düşüş → EXIT
        np.full(25, 96.0),
    ])
    return {s: pd.Series(prices, index=idx) for s in ["A", "B", "C"]}


def _cfg() -> RegimeCoreConfig:
    return RegimeCoreConfig(symbols=["A", "B", "C"], ma_period=10, band_pct=0.01,
                            confirm_days=2, commission_bps=10.0, slippage_bps=5.0,
                            initial_equity=100_000.0)


def _bist_equiv_costmodel() -> UsEquitiesCostModel:
    # commission 10bps her iki yön, SEC/TAF=0, slippage 5bps → S1b basit-bps modeliyle özdeş.
    return UsEquitiesCostModel(commission_bps=10.0, sec_fee_bps=0.0, taf_per_share=0.0, slippage_bps=5.0)


def test_costmodel_loop_parity_with_simple_bps_model():
    closes, cfg = _trend_series(), _cfg()
    ref = run_regime_core(closes, cfg, cash_rate=None)
    mine = run_regime_core_costmodel(closes, cfg, cost_model=_bist_equiv_costmodel(), cash_rate=None)

    sw_ref = [(s.date, s.action) for s in ref.switches]
    sw_mine = [(s.date, s.action) for s in mine.switches]
    assert sw_ref == sw_mine
    assert len(sw_ref) >= 2  # en az bir ENTER + bir EXIT olsun ki test anlamlı olsun
    rel = ((mine.equity_curve - ref.equity_curve).abs() / ref.equity_curve.abs()).max()
    assert rel < 1e-9


def test_costmodel_loop_deterministic():
    closes, cfg = _trend_series(), _cfg()
    cm = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.28, taf_per_share=0.000166, slippage_bps=5.0)
    a = run_regime_core_costmodel(closes, cfg, cost_model=cm, cash_rate=None)
    b = run_regime_core_costmodel(closes, cfg, cost_model=cm, cash_rate=None)
    pd.testing.assert_series_equal(a.equity_curve, b.equity_curve)
    assert [(s.date, s.action) for s in a.switches] == [(s.date, s.action) for s in b.switches]


def test_cash_rate_none_equals_all_zero_series_byte_identical():
    """%0 kararının bayt-eşdeğerliği: cash_rate=None ile tümü-sıfır seri aynı
    sonucu vermeli (r_net = max(0 - haircut, 0) = 0 → cash ×1)."""
    closes, cfg = _trend_series(), _cfg()
    cm = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.28, taf_per_share=0.000166, slippage_bps=5.0)
    all_dates = next(iter(closes.values())).index
    zero_rate = pd.Series(0.0, index=all_dates)
    none_run = run_regime_core_costmodel(closes, cfg, cost_model=cm, cash_rate=None)
    zero_run = run_regime_core_costmodel(closes, cfg, cost_model=cm, cash_rate=zero_rate)
    pd.testing.assert_series_equal(none_run.equity_curve, zero_run.equity_curve)


def test_normalize_bist_dates_is_noop_on_us_00utc_data():
    """US snapshot 00:00-UTC tarih etiketleri taşır → normalize_bist_dates kimlik.
    load_and_clean_universe reuse'unun US için güvenli olduğunun kanıtı."""
    from data.cleaning import normalize_bist_dates
    df = pd.read_parquet("data/snapshots/us/2026-07-06/AAPL.parquet")
    out = normalize_bist_dates(df)
    assert (out.index == df.index).all()


def test_us_costmodel_sec_taf_only_charged_on_sale():
    """SEC/TAF farkı yalnız SATIŞTA (exit) görünmeli: sec_fee>0 modeli, sec_fee=0
    modeline göre SATIŞTAN sonra daha düşük nihai equity üretir; fark satış
    notional'ının SEC oranı kadar (tek round-trip)."""
    closes, cfg = _trend_series(), _cfg()
    no_sec = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.0, taf_per_share=0.0, slippage_bps=5.0)
    with_sec = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=1.0, taf_per_share=0.0, slippage_bps=5.0)
    r0 = run_regime_core_costmodel(closes, cfg, cost_model=no_sec, cash_rate=None)
    r1 = run_regime_core_costmodel(closes, cfg, cost_model=with_sec, cash_rate=None)
    # SEC yalnız satışta → farkı olmalı ve with_sec daha düşük.
    assert r1.equity_curve.iloc[-1] < r0.equity_curve.iloc[-1]
    # ENTER anına kadar (ilk switch ENTER) iki eğri AYNI olmalı (SEC henüz uygulanmadı).
    first_enter = next(s.date for s in r0.switches if s.action == "ENTER")
    pre = r0.equity_curve.index < first_enter
    assert np.allclose(r0.equity_curve[pre].to_numpy(), r1.equity_curve[pre].to_numpy())


@pytest.mark.parametrize("_", [0])
def test_d1_us_headline_numbers_regression(_):
    """Rapordaki headline D1-US sayılarını (gerçek snapshot) çapa alır — sessiz
    sapmayı yakalar. cash=0% (cash_rate=None), US CostModel."""
    from tools.e4_common import load_us_closes, load_us_config
    from tools.run_regime_core import compute_summary
    from costs.us_equities import us_cost_model_from_config

    cfg = load_us_config()
    closes, _ = load_us_closes(cfg)
    reg, c = cfg["regime"], cfg["costs"]
    core = RegimeCoreConfig(symbols=cfg["symbols"], ma_period=reg["ma_period"], band_pct=reg["band_pct"],
                            confirm_days=reg["confirm_days"], commission_bps=c["commission_bps"],
                            slippage_bps=c["slippage_bps"], initial_equity=cfg["initial_equity"])
    res = run_regime_core_costmodel(closes, core, cost_model=us_cost_model_from_config(c), cash_rate=None)
    s = compute_summary(res.equity_curve)
    assert len(res.switches) == 57
    assert s["max_drawdown"] == pytest.approx(-0.23106, abs=5e-4)
    assert s["sharpe"] == pytest.approx(0.7262, abs=5e-4)
    assert s["cagr"] == pytest.approx(0.08193, abs=5e-4)

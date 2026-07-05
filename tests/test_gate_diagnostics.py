from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backtest.gate_diagnostics import GATE_NAMES, diagnose_symbol, run_gate_diagnostics
from indicators.engine import build_features


def make_cfg():
    signal = SimpleNamespace(
        ema_fast=5, ema_slow=10, adx_period=5, adx_min=20,
        rsi_period=7, rsi_entry_low=40, rsi_entry_high=55,
        macd=(3, 6, 3), atr_period=5, atr_stop_mult=1.5, atr_anomaly_mult=2.0,
        bb_period=7, bb_std=2.0, swing_lookback=10, swing_fractal_n=1,
        volume_confirm_mult=1.5, min_history_bars=15,
    )
    risk = SimpleNamespace(min_rr=1.8)
    return SimpleNamespace(signal=signal, risk=risk)


def _flat_series(n=60):
    idx = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    close = np.full(n, 100.0)
    return pd.DataFrame({"open": close, "high": close + 0.1, "low": close - 0.1,
                        "close": close, "volume": np.full(n, 1000.0)}, index=idx)


def _downtrend_series(n=60):
    idx = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    close = np.linspace(130, 100, n)
    return pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5,
                        "close": close, "volume": np.full(n, 1000.0)}, index=idx)


def test_diagnose_symbol_has_all_ten_gates():
    cfg = make_cfg()
    df = build_features(_flat_series(), cfg)
    diag = diagnose_symbol("TEST", df, cfg)
    assert len(GATE_NAMES) == 10
    assert set(diag.standalone_pass_rate.keys()) == set(GATE_NAMES)
    assert set(diag.cumulative_pass_rate.keys()) == set(range(1, 11))


def test_pass_rates_are_bounded_0_to_100():
    cfg = make_cfg()
    df = build_features(_flat_series(), cfg)
    diag = diagnose_symbol("TEST", df, cfg)
    for rate in diag.standalone_pass_rate.values():
        assert 0.0 <= rate <= 100.0
    for rate in diag.cumulative_pass_rate.values():
        assert 0.0 <= rate <= 100.0


def test_cumulative_pass_rate_is_non_increasing():
    cfg = make_cfg()
    df = build_features(_downtrend_series(), cfg)
    diag = diagnose_symbol("TEST", df, cfg)
    rates = [diag.cumulative_pass_rate[k] for k in range(1, 11)]
    assert all(rates[i] >= rates[i + 1] for i in range(len(rates) - 1))


def test_downtrend_fails_trend_gate_on_every_day_so_cumulative_is_zero():
    cfg = make_cfg()
    df = build_features(_downtrend_series(), cfg)
    diag = diagnose_symbol("TEST", df, cfg)
    # sürekli düşen seri: close hep ema200'ün altında -> gate_trend hep FAIL
    assert diag.standalone_pass_rate["trend"] == pytest.approx(0.0)
    for k in range(1, 11):
        assert diag.cumulative_pass_rate[k] == pytest.approx(0.0)


def test_insufficient_history_returns_zeroed_diagnostics():
    cfg = make_cfg()
    df = build_features(_flat_series(n=14), cfg)  # min_history_bars=15'ten az
    diag = diagnose_symbol("TEST", df, cfg)
    assert diag.total_days == 0
    assert all(v == 0.0 for v in diag.standalone_pass_rate.values())


def test_run_gate_diagnostics_writes_report_file(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    out_path = tmp_path / "gate_diagnostics.md"
    diagnostics = run_gate_diagnostics(["A", "B"], cfg, lambda s: df, out_path)
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "Gate Teşhis Raporu" in content
    assert "## A" in content
    assert "## B" in content
    assert "Özet (semboller arası ortalama)" in content
    assert len(diagnostics) == 2

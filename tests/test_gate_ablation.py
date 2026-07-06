from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from indicators.engine import build_features
from tools.gate_ablation import (
    GATE_NAMES,
    compute_gate_matrix,
    find_counterfactual_candidates,
    run_baseline_isolated,
    simulate_isolated_entry,
    summarize_isolated,
)


def make_cfg():
    signal = SimpleNamespace(
        ema_fast=5, ema_slow=10, adx_period=5, adx_min=20,
        rsi_period=7, rsi_entry_low=40, rsi_entry_high=55,
        macd=(3, 6, 3), atr_period=5, atr_stop_mult=1.5, atr_anomaly_mult=2.0,
        bb_period=7, bb_std=2.0, swing_lookback=10, swing_fractal_n=1,
        volume_confirm_mult=1.5, min_history_bars=15,
    )
    risk = SimpleNamespace(min_rr=1.8)
    costs = SimpleNamespace(commission_bps=0.0, slippage_bps=0.0)
    return SimpleNamespace(signal=signal, risk=risk, costs=costs)


def _pretrigger_bars(seed=13, n=45):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.15, 1.0, n - 1)
    close = np.concatenate([[100.0], 100 + np.cumsum(steps)])
    close[-1] = close[-2] + abs(rng.normal(2.5, 0.5))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) + 0.3
    low = np.minimum(open_, close) - 0.3
    open_[-1] = close[-2] - 0.1
    high[-1] = close[-1] + 0.3
    low[-1] = open_[-1] - 0.2
    volume = np.full(n, 1000.0)
    volume[-1] = 3000.0
    idx = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def test_compute_gate_matrix_has_all_ten_gate_columns():
    cfg = make_cfg()
    df = build_features(_pretrigger_bars(), cfg)
    matrix = compute_gate_matrix({"TEST": df}, cfg)
    assert set(GATE_NAMES) <= set(matrix.columns)
    assert len(matrix) == len(df) - cfg.signal.min_history_bars


def test_find_counterfactual_candidates_excludes_the_target_gate():
    matrix = pd.DataFrame([
        {"symbol": "A", "date": 1, "pos": 0, "trend": False, "regime": True, "rsi": True,
         "macd": True, "atr_anomaly": True, "bb_overextension": True, "structure_rr": True,
         "volume": True, "trigger_4h": True, "mtf": True},
        {"symbol": "A", "date": 2, "pos": 1, "trend": True, "regime": False, "rsi": True,
         "macd": True, "atr_anomaly": True, "bb_overextension": True, "structure_rr": True,
         "volume": True, "trigger_4h": True, "mtf": True},
        {"symbol": "A", "date": 3, "pos": 2, "trend": False, "regime": False, "rsi": True,
         "macd": True, "atr_anomaly": True, "bb_overextension": True, "structure_rr": True,
         "volume": True, "trigger_4h": True, "mtf": True},
    ])
    trend_candidates = find_counterfactual_candidates(matrix, "trend")
    assert len(trend_candidates) == 1  # yalnızca satır 1 (yalnızca trend FAIL)
    assert trend_candidates.iloc[0]["pos"] == 0


def test_simulate_isolated_entry_stop_gives_negative_one_r_with_zero_costs():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    df = pd.DataFrame({
        "open": [100, 100, 95, 95, 95],
        "high": [101, 100.5, 95.5, 95.5, 95.5],
        "low": [99, 99.5, 85, 85, 85],       # 3. barda (fill sonrası) stop'a değer
        "close": [100, 100, 90, 90, 90],
        "atr": [2.0, 2.0, 2.0, 2.0, 2.0],
        "nearest_resistance": [float("nan")] * 5,
        # evaluate_exit'in çökmemesi için gerekli kolonlar (EXIT_LONG'un tetiklenmediği,
        # nötr bir durum): close hep ema_fast üstünde, macd hep signal üstünde.
        "ema_5": [100, 100, 100, 100, 100],
        "macd": [1.0, 1.0, 1.0, 1.0, 1.0],
        "macd_signal": [0.5, 0.5, 0.5, 0.5, 0.5],
        "macd_hist": [0.5, 0.5, 0.5, 0.5, 0.5],
    }, index=idx)
    cfg = make_cfg()
    # signal_idx=0 -> fill_idx=1 (open=100), stop=100-1.5*2=97
    result = simulate_isolated_entry(df, signal_idx=0, cfg=cfg)
    assert result is not None
    assert result["exit_reason"] == "STOP"
    assert result["r_multiple"] == pytest.approx(-1.0, abs=1e-6)


def test_simulate_isolated_entry_target_gives_positive_r():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    df = pd.DataFrame({
        "open": [100, 100, 100, 100, 100],
        "high": [101, 100.5, 115, 100.5, 100.5],  # 3. barda target'a değer
        "low": [99, 99.5, 99, 99.5, 99.5],
        "close": [100, 100, 100, 100, 100],
        "atr": [2.0, 2.0, 2.0, 2.0, 2.0],
        "nearest_resistance": [110.0] * 5,  # target = 110 (resistance, fallback 106'dan büyük)
        "ema_5": [100, 100, 100, 100, 100],
        "macd": [1.0, 1.0, 1.0, 1.0, 1.0],
        "macd_signal": [0.5, 0.5, 0.5, 0.5, 0.5],
        "macd_hist": [0.5, 0.5, 0.5, 0.5, 0.5],
    }, index=idx)
    cfg = make_cfg()
    result = simulate_isolated_entry(df, signal_idx=0, cfg=cfg)
    assert result is not None
    assert result["exit_reason"] == "TARGET"
    # entry=100 (open, slippage=0), stop=97, target=110 -> r=(110-100)/3=3.33
    assert result["r_multiple"] == pytest.approx(10 / 3, rel=1e-6)


def test_simulate_isolated_entry_returns_none_when_insufficient_forward_data():
    idx = pd.date_range("2024-01-01", periods=1, freq="1D", tz="UTC")
    df = pd.DataFrame({
        "open": [100], "high": [101], "low": [99], "close": [100],
        "atr": [2.0], "nearest_resistance": [float("nan")],
    }, index=idx)
    cfg = make_cfg()
    result = simulate_isolated_entry(df, signal_idx=0, cfg=cfg)
    assert result is None


def test_summarize_isolated_empty_results():
    summary = summarize_isolated(pd.DataFrame())
    assert summary == {"n": 0, "win_rate": 0.0, "avg_r": 0.0, "profit_factor": 0.0}


def test_summarize_isolated_computes_win_rate_and_pf():
    results = pd.DataFrame([{"r_multiple": 2.0}, {"r_multiple": -1.0}, {"r_multiple": 1.0}])
    summary = summarize_isolated(results)
    assert summary["n"] == 3
    assert summary["win_rate"] == pytest.approx(2 / 3)
    assert summary["avg_r"] == pytest.approx((2.0 - 1.0 + 1.0) / 3)
    assert summary["profit_factor"] == pytest.approx(3.0 / 1.0)


def test_run_baseline_isolated_skips_trade_with_unknown_symbol():
    cfg = make_cfg()
    df = build_features(_pretrigger_bars(), cfg)
    trades_df = pd.DataFrame([{"symbol": "UNKNOWN", "entry_date": df.index[20]}])
    result = run_baseline_isolated({"TEST": df}, trades_df, cfg)
    assert result.empty

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from indicators.engine import build_features
from tools.gate_analysis import (
    compare_winners_losers,
    compute_elimination_funnel,
    identify_weak_gates,
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
    return SimpleNamespace(signal=signal, risk=risk)


def _flat_series(n=60, start="2024-01-01"):
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    close = np.full(n, 100.0)
    return pd.DataFrame({"open": close, "high": close + 0.1, "low": close - 0.1,
                        "close": close, "volume": np.full(n, 1000.0)}, index=idx)


def _downtrend_series(n=60, start="2024-01-01"):
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    close = np.linspace(130, 100, n)
    return pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5,
                        "close": close, "volume": np.full(n, 1000.0)}, index=idx)


def test_compute_elimination_funnel_has_ten_stages_and_monotonic_remaining():
    cfg = make_cfg()
    daily_features = {"A": build_features(_downtrend_series(), cfg)}
    funnel = compute_elimination_funnel(daily_features, cfg)
    assert len(funnel) == 10
    remaining = funnel["remaining"].tolist()
    assert all(remaining[i] >= remaining[i + 1] for i in range(len(remaining) - 1))


def test_compute_elimination_funnel_downtrend_all_eliminated_at_trend_stage():
    cfg = make_cfg()
    daily_features = {"A": build_features(_downtrend_series(), cfg)}
    funnel = compute_elimination_funnel(daily_features, cfg)
    trend_row = funnel[funnel["gate"] == "trend"].iloc[0]
    assert trend_row["remaining"] == 0  # sürekli düşen seride hiçbir gün trend'i geçemez


def test_identify_weak_gates_flags_zero_elimination():
    funnel = pd.DataFrame([
        {"stage": 1, "gate": "a", "eliminated": 50, "remaining": 50, "elimination_rate_of_remaining": 0.5},
        {"stage": 2, "gate": "b", "eliminated": 0, "remaining": 50, "elimination_rate_of_remaining": 0.0},
        {"stage": 3, "gate": "c", "eliminated": 25, "remaining": 25, "elimination_rate_of_remaining": 0.5},
    ])
    weak = identify_weak_gates(funnel)
    assert weak == ["b"]


def test_identify_weak_gates_empty_when_all_gates_eliminate_meaningfully():
    funnel = pd.DataFrame([
        {"stage": 1, "gate": "a", "eliminated": 50, "remaining": 50, "elimination_rate_of_remaining": 0.5},
        {"stage": 2, "gate": "b", "eliminated": 25, "remaining": 25, "elimination_rate_of_remaining": 0.5},
    ])
    weak = identify_weak_gates(funnel)
    assert weak == []


def test_compare_winners_losers_splits_by_pnl_sign():
    cfg = make_cfg()
    df = build_features(_flat_series(n=60), cfg)
    daily_features = {"A": df}
    trades_df = pd.DataFrame([
        {"symbol": "A", "entry_date": df.index[30], "pnl": 100.0},
        {"symbol": "A", "entry_date": df.index[40], "pnl": -50.0},
    ])
    summary = compare_winners_losers(trades_df, daily_features)
    assert not summary.empty
    # her iki outcome grubu da (winner/loser) tabloda temsil ediliyor olmalı
    outcomes = summary.index.tolist()
    assert "winner" in outcomes
    assert "loser" in outcomes


def test_compare_winners_losers_empty_when_no_trades():
    cfg = make_cfg()
    df = build_features(_flat_series(n=60), cfg)
    trades_df = pd.DataFrame(columns=["symbol", "entry_date", "pnl"])
    summary = compare_winners_losers(trades_df, {"A": df})
    assert summary.empty


def test_compare_winners_losers_skips_trade_with_unknown_symbol():
    cfg = make_cfg()
    df = build_features(_flat_series(n=60), cfg)
    trades_df = pd.DataFrame([
        {"symbol": "UNKNOWN", "entry_date": df.index[30], "pnl": 100.0},
    ])
    summary = compare_winners_losers(trades_df, {"A": df})
    assert summary.empty

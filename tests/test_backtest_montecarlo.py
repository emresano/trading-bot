from types import SimpleNamespace

import numpy as np
import pytest

from backtest.engine import Trade
from backtest.montecarlo import monte_carlo_dd, run_monte_carlo, trade_returns_from_trades


def make_trade(pnl, r_multiple):
    return Trade(
        symbol="A", entry_date=None, entry_price=100.0, exit_date=None, exit_price=105.0,
        quantity=10, exit_reason="TARGET", pnl=pnl, r_multiple=r_multiple,
    )


def test_monte_carlo_dd_is_deterministic_for_same_seed():
    returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, -0.005] * 10)
    r1 = monte_carlo_dd(returns, runs=200, seed=42)
    r2 = monte_carlo_dd(returns, runs=200, seed=42)
    assert r1 == r2


def test_monte_carlo_dd_different_seed_can_differ():
    returns = np.array([0.01, -0.02, 0.015, -0.01, 0.02, -0.005] * 10)
    r1 = monte_carlo_dd(returns, runs=200, seed=1)
    r2 = monte_carlo_dd(returns, runs=200, seed=2)
    assert r1 != r2


def test_monte_carlo_dd_values_are_non_positive():
    returns = np.array([0.02, -0.03, 0.01, -0.02, 0.015] * 20)
    result = monte_carlo_dd(returns, runs=500, seed=42)
    assert result["dd_p5"] <= 0
    assert result["dd_median"] <= 0
    assert result["dd_p95"] <= 0
    # p5 en kötü (en negatif), p95 en iyi (en az negatif) olmalı
    assert result["dd_p5"] <= result["dd_median"] <= result["dd_p95"]


def test_all_positive_returns_yield_zero_drawdown():
    returns = np.array([0.01, 0.02, 0.015] * 10)
    result = monte_carlo_dd(returns, runs=100, seed=42)
    assert result["dd_p5"] == pytest.approx(0.0)
    assert result["dd_p95"] == pytest.approx(0.0)


def test_trade_returns_from_trades_scales_by_risk_pct():
    trades = [make_trade(100, 2.0), make_trade(-50, -1.0)]
    returns = trade_returns_from_trades(trades, risk_per_trade_pct=0.0075)
    assert returns[0] == pytest.approx(2.0 * 0.0075)
    assert returns[1] == pytest.approx(-1.0 * 0.0075)


def make_cfg(monte_carlo_runs=300, random_seed=42, risk_per_trade_pct=0.0075):
    risk = SimpleNamespace(risk_per_trade_pct=risk_per_trade_pct)
    backtest = SimpleNamespace(monte_carlo_runs=monte_carlo_runs, random_seed=random_seed)
    return SimpleNamespace(risk=risk, backtest=backtest)


def test_run_monte_carlo_empty_trades_returns_zeros():
    cfg = make_cfg()
    result = run_monte_carlo([], cfg)
    assert result == {"dd_p5": 0.0, "dd_median": 0.0, "dd_p95": 0.0, "trade_count": 0}


def test_run_monte_carlo_with_trades_is_deterministic():
    cfg = make_cfg()
    trades = [make_trade(100, 2.0), make_trade(-50, -1.0), make_trade(80, 1.5)] * 5
    r1 = run_monte_carlo(trades, cfg)
    r2 = run_monte_carlo(trades, cfg)
    assert r1 == r2
    assert r1["trade_count"] == 15

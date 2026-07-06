import numpy as np
import pandas as pd
import pytest

from tools.run_regime_core import (
    compute_monthly_returns,
    compute_summary,
    find_drawdown_episodes,
    gen_walk_forward_windows,
    monte_carlo_monthly,
    monthly_sharpe,
)


def test_compute_summary_empty_curve():
    result = compute_summary(pd.Series(dtype=float))
    assert result == {"total_return": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}


def test_compute_summary_basic_values():
    idx = pd.date_range("2020-01-01", periods=3, freq="1D", tz="UTC")
    eq = pd.Series([100.0, 110.0, 121.0], index=idx)
    result = compute_summary(eq)
    assert result["total_return"] == pytest.approx(0.21)
    assert result["max_drawdown"] == pytest.approx(0.0)  # hiç düşüş yok


def test_find_drawdown_episodes_identifies_peak_trough_recovery():
    idx = pd.date_range("2020-01-01", periods=9, freq="1D", tz="UTC")
    eq = pd.Series([100, 110, 100, 95, 105, 111, 111, 100, 90], index=idx)
    episodes = find_drawdown_episodes(eq)
    assert len(episodes) >= 1
    first = episodes[-1]  # sort by depth (en derinden en sığa) -> son eleman ilk (en sığ) epizot olabilir
    # en derin epizot: peak=111, henüz recovery yok (son deger 90)
    deepest = episodes[0]
    assert deepest["depth"] == pytest.approx(90 / 111 - 1)
    assert deepest["recovery_date"] is None


def test_find_drawdown_episodes_filters_by_min_depth():
    idx = pd.date_range("2020-01-01", periods=5, freq="1D", tz="UTC")
    eq = pd.Series([100, 99, 100, 100, 100], index=idx)  # yalnızca %1 düşüş
    episodes = find_drawdown_episodes(eq, min_depth=0.10)
    assert episodes == []


def test_find_drawdown_episodes_empty_curve():
    assert find_drawdown_episodes(pd.Series(dtype=float)) == []


def test_compute_monthly_returns_basic():
    idx = pd.date_range("2020-01-01", periods=90, freq="1D", tz="UTC")
    eq = pd.Series(np.linspace(100, 130, 90), index=idx)
    monthly = compute_monthly_returns(eq)
    assert len(monthly) >= 1
    assert (monthly > -1).all()  # mantıklı aralık


def test_monthly_sharpe_zero_std_returns_zero():
    returns = pd.Series([0.01, 0.01, 0.01])
    assert monthly_sharpe(returns) == 0.0


def test_monthly_sharpe_positive_for_positive_trend():
    returns = pd.Series([0.02, 0.01, 0.03, 0.015, 0.025])
    result = monthly_sharpe(returns)
    assert result > 0


def test_monte_carlo_monthly_deterministic_with_seed():
    returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.01, 0.01])
    r1 = monte_carlo_monthly(returns, runs=100, seed=42)
    r2 = monte_carlo_monthly(returns, runs=100, seed=42)
    assert r1 == r2
    assert r1["dd_p5"] <= r1["dd_median"] <= r1["dd_p95"]


def test_gen_walk_forward_windows_non_overlapping_and_stepped():
    idx = pd.date_range("2005-01-01", periods=365 * 20, freq="1D", tz="UTC")
    windows = gen_walk_forward_windows(idx, train_months=24, test_months=6, step_months=6)
    assert len(windows) > 0
    for train_start, train_end, test_start, test_end in windows:
        assert train_end == test_start
        assert test_end > test_start
    if len(windows) > 1:
        assert windows[1][0] == windows[0][0] + pd.DateOffset(months=6)


def test_gen_walk_forward_windows_empty_when_insufficient_history():
    idx = pd.date_range("2020-01-01", periods=100, freq="1D", tz="UTC")
    windows = gen_walk_forward_windows(idx, train_months=24, test_months=6, step_months=6)
    assert windows == []

from types import SimpleNamespace

import pandas as pd
import pytest

from backtest.engine import Trade
from backtest.metrics import (
    cash_only_metrics,
    classify_regime,
    compute_buy_hold_metrics,
    compute_metrics,
    regime_breakdown,
)


def make_trade(symbol="A", entry_date="2024-01-01", exit_date="2024-01-05",
               pnl=100.0, r_multiple=1.0):
    return Trade(
        symbol=symbol,
        entry_date=pd.Timestamp(entry_date, tz="UTC"), entry_price=100.0,
        exit_date=pd.Timestamp(exit_date, tz="UTC"), exit_price=105.0,
        quantity=10, exit_reason="TARGET", pnl=pnl, r_multiple=r_multiple,
    )


def test_empty_equity_curve_returns_zeroed_metrics():
    m = compute_metrics(pd.Series(dtype=float), [])
    assert m.trade_count == 0
    assert m.time_in_cash_pct == 100.0
    assert m.total_return == 0.0


def test_total_return_and_max_drawdown():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    equity = pd.Series([100, 110, 90, 95, 120], index=idx, dtype=float)
    m = compute_metrics(equity, [])
    assert m.total_return == pytest.approx(0.20)
    # tepe 110'dan 90'a düşüş: (90/110 - 1)
    assert m.max_drawdown == pytest.approx(90 / 110 - 1)


def test_cagr_matches_hand_computed_value():
    idx = pd.date_range("2024-01-01", periods=366, freq="1D", tz="UTC")  # tam 1 yıl
    equity = pd.Series([100.0] * 365 + [200.0], index=idx)
    m = compute_metrics(equity, [])
    years = (idx[-1] - idx[0]).days / 365.25
    expected_cagr = (200 / 100) ** (1 / years) - 1
    assert m.cagr == pytest.approx(expected_cagr, rel=1e-6)


def test_win_rate_profit_factor_expectancy():
    trades = [
        make_trade(pnl=100, r_multiple=2.0),
        make_trade(pnl=-50, r_multiple=-1.0),
        make_trade(pnl=50, r_multiple=1.0),
    ]
    idx = pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")
    equity = pd.Series([100, 105], index=idx, dtype=float)
    m = compute_metrics(equity, trades)
    assert m.trade_count == 3
    assert m.win_rate == pytest.approx(2 / 3)
    assert m.profit_factor == pytest.approx(150 / 50)
    assert m.avg_r_multiple == pytest.approx((2.0 - 1.0 + 1.0) / 3)
    assert m.expectancy == pytest.approx((100 - 50 + 50) / 3)


def test_profit_factor_infinite_when_no_losses():
    trades = [make_trade(pnl=100, r_multiple=2.0)]
    idx = pd.date_range("2024-01-01", periods=2, freq="1D", tz="UTC")
    equity = pd.Series([100, 105], index=idx, dtype=float)
    m = compute_metrics(equity, trades)
    assert m.profit_factor == float("inf")


def test_time_in_cash_pct_with_no_trades_is_100():
    idx = pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")
    equity = pd.Series([100.0] * 10, index=idx)
    m = compute_metrics(equity, [])
    assert m.time_in_cash_pct == 100.0


def test_time_in_cash_pct_reflects_covered_days():
    idx = pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")
    equity = pd.Series([100.0] * 10, index=idx)
    trade = make_trade(entry_date="2024-01-03", exit_date="2024-01-07")  # 5 gün kapsıyor
    m = compute_metrics(equity, [trade])
    assert m.time_in_cash_pct == pytest.approx(100.0 * (1 - 5 / 10))


# --- Rejim sınıflandırması ---

def make_regime_cfg():
    return SimpleNamespace(signal=SimpleNamespace(ema_slow=200))


def test_classify_regime_bull_bear_sideways():
    idx = pd.date_range("2024-01-01", periods=25, freq="1D", tz="UTC")
    ema_200 = pd.Series(list(range(100, 125)), index=idx, dtype=float)  # sürekli yükseliyor
    close_bull = ema_200 + 5   # close > ema, ema yükseliyor -> bull
    df_bull = pd.DataFrame({"close": close_bull, "ema_200": ema_200}, index=idx)
    regime = classify_regime(df_bull, make_regime_cfg())
    assert regime.iloc[-1] == "bull"

    ema_falling = pd.Series(list(range(125, 100, -1)), index=idx, dtype=float)
    close_bear = ema_falling - 5  # close < ema, ema düşüyor -> bear
    df_bear = pd.DataFrame({"close": close_bear, "ema_200": ema_falling}, index=idx)
    regime_bear = classify_regime(df_bear, make_regime_cfg())
    assert regime_bear.iloc[-1] == "bear"

    ema_flat = pd.Series([100.0] * 25, index=idx)
    close_flat = ema_flat + 0.1
    df_side = pd.DataFrame({"close": close_flat, "ema_200": ema_flat}, index=idx)
    regime_side = classify_regime(df_side, make_regime_cfg())
    assert regime_side.iloc[-1] == "sideways"


def test_regime_breakdown_groups_correctly():
    trades = [
        make_trade(symbol="A", entry_date="2024-01-10", pnl=100, r_multiple=2.0),
        make_trade(symbol="A", entry_date="2024-01-11", pnl=-50, r_multiple=-1.0),
        make_trade(symbol="B", entry_date="2024-01-10", pnl=30, r_multiple=0.5),
    ]
    idx = pd.date_range("2024-01-01", periods=20, freq="1D", tz="UTC")
    regime_a = pd.Series("bull", index=idx)
    regime_b = pd.Series("bear", index=idx)
    breakdown = regime_breakdown(trades, {"A": regime_a, "B": regime_b})
    bull_row = breakdown[breakdown["regime"] == "bull"].iloc[0]
    bear_row = breakdown[breakdown["regime"] == "bear"].iloc[0]
    assert bull_row["trade_count"] == 2
    assert bull_row["win_rate"] == pytest.approx(0.5)
    assert bull_row["total_r"] == pytest.approx(1.0)
    assert bear_row["trade_count"] == 1
    assert bear_row["win_rate"] == pytest.approx(1.0)


def test_regime_breakdown_empty_trades_returns_empty_frame():
    result = regime_breakdown([], {})
    assert result.empty


# --- Benchmark kıyası: al-tut ve sadece-nakit ---

def test_compute_buy_hold_metrics_matches_price_return():
    idx = pd.date_range("2020-01-01", periods=366, freq="1D", tz="UTC")  # tam 1 yıl
    close = pd.Series([100.0] * 365 + [120.0], index=idx)
    df = pd.DataFrame({"close": close})
    m = compute_buy_hold_metrics(df, initial_equity=100_000.0)
    assert m.total_return == pytest.approx(0.20)
    years = (idx[-1] - idx[0]).days / 365.25
    assert m.cagr == pytest.approx((1.20) ** (1 / years) - 1, rel=1e-6)


def test_compute_buy_hold_metrics_drawdown_from_price_series():
    idx = pd.date_range("2020-01-01", periods=5, freq="1D", tz="UTC")
    close = pd.Series([100, 110, 90, 95, 105], index=idx, dtype=float)
    df = pd.DataFrame({"close": close})
    m = compute_buy_hold_metrics(df, initial_equity=100_000.0)
    assert m.max_drawdown == pytest.approx(90 / 110 - 1)
    # trade bazlı alanlar al-tut senaryosunda anlamsız/sıfır
    assert m.trade_count == 0
    assert m.win_rate == 0.0
    assert m.profit_factor == 0.0


def test_compute_buy_hold_metrics_empty_dataframe():
    m = compute_buy_hold_metrics(pd.DataFrame(columns=["close"]), initial_equity=100_000.0)
    assert m.total_return == 0.0
    assert m.trade_count == 0


def test_cash_only_metrics_all_zero():
    m = cash_only_metrics()
    assert m.total_return == 0.0
    assert m.cagr == 0.0
    assert m.max_drawdown == 0.0
    assert m.sharpe == 0.0
    assert m.time_in_cash_pct == 100.0

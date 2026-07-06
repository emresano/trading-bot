from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backtest.engine import Trade
from backtest.walkforward import (
    SWEEP_KEYS,
    WindowResult,
    apply_params,
    combined_oos_metrics,
    evaluate_acceptance,
    is_neighbor_robust,
    run_walk_forward,
    select_robust_params,
    sweep_combinations,
)


def make_cfg():
    signal = SimpleNamespace(
        ema_fast=5, ema_slow=10, adx_period=5, adx_min=20,
        rsi_period=7, rsi_entry_low=40, rsi_entry_high=55,
        macd=(3, 6, 3), atr_period=5, atr_stop_mult=1.5, atr_anomaly_mult=2.0,
        bb_period=7, bb_std=2.0, swing_lookback=10, swing_fractal_n=1,
        volume_confirm_mult=1.5, min_history_bars=15,
    )
    risk = SimpleNamespace(
        risk_per_trade_pct=0.0075, daily_loss_limit_pct=0.5, weekly_loss_limit_pct=0.5,
        max_open_positions=2, max_position_notional_pct=0.25, max_drawdown_breaker_pct=0.5,
        min_rr=1.8, correlation_lookback_days=90, correlation_max=0.85, news_blackout=False,
    )
    costs = SimpleNamespace(commission_bps=10, slippage_bps=5)
    backtest = SimpleNamespace(
        initial_equity=100_000.0,
        walk_forward=SimpleNamespace(train_months=2, test_months=1, step_months=1),
    )
    safety = SimpleNamespace(kill_switch_file="runtime/__nonexistent_kill_switch_for_tests__")
    return SimpleNamespace(signal=signal, risk=risk, costs=costs, backtest=backtest, safety=safety)


def test_sweep_combinations_has_27_entries():
    combos = sweep_combinations()
    assert len(combos) == 27
    assert len(set(tuple(c[k] for k in SWEEP_KEYS) for c in combos)) == 27


def test_apply_params_overrides_without_mutating_original():
    cfg = make_cfg()
    original_atr_mult = cfg.signal.atr_stop_mult
    new_cfg = apply_params(cfg, {"atr_stop_mult": 2.0, "adx_min": 25, "min_rr": 2.2})
    assert new_cfg.signal.atr_stop_mult == 2.0
    assert new_cfg.signal.adx_min == 25
    assert new_cfg.risk.min_rr == 2.2
    assert cfg.signal.atr_stop_mult == original_atr_mult  # orijinal değişmedi


# --- Komşu-sağlamlık ---

def _fake_metrics(sharpe: float):
    from backtest.metrics import Metrics
    return Metrics(0, 0, 0, sharpe, 0, 0, 0, 0, 1, 0)


def test_is_neighbor_robust_true_when_neighbors_hold_up():
    scores = {
        (1.25, 15, 1.5): 0.5, (1.25, 20, 1.5): 0.8, (1.25, 25, 1.5): 0.5,
        (1.5, 15, 1.5): 0.8, (1.5, 20, 1.5): 1.0, (1.5, 25, 1.5): 0.8,
        (2.0, 15, 1.5): 0.5, (2.0, 20, 1.5): 0.8, (2.0, 25, 1.5): 0.5,
        (1.5, 20, 1.8): 0.9, (1.5, 20, 2.2): 0.9,
    }
    best = {"atr_stop_mult": 1.5, "adx_min": 20, "min_rr": 1.5}
    assert is_neighbor_robust(scores, best)


def test_is_neighbor_robust_false_when_isolated_spike():
    # (1.5,20,1.5) tek başına yüksek skorlu, komşuları çok düşük -> overfitting şüphesi
    scores = {
        (1.25, 15, 1.5): 0.01, (1.25, 20, 1.5): 0.01, (1.25, 25, 1.5): 0.01,
        (1.5, 15, 1.5): 0.01, (1.5, 20, 1.5): 1.0, (1.5, 25, 1.5): 0.01,
        (2.0, 15, 1.5): 0.01, (2.0, 20, 1.5): 0.01, (2.0, 25, 1.5): 0.01,
        (1.5, 20, 1.8): 0.01, (1.5, 20, 2.2): 0.01,
    }
    best = {"atr_stop_mult": 1.5, "adx_min": 20, "min_rr": 1.5}
    assert not is_neighbor_robust(scores, best)


def test_select_robust_params_falls_back_to_best_when_none_robust():
    train_results = {
        (1.25, 15, 1.5): _fake_metrics(0.0),
        (1.5, 20, 1.8): _fake_metrics(0.3),
    }
    chosen = select_robust_params(train_results)
    assert chosen  # boş değil, en azından bir şey döndü


# --- Pencere üretimi ---

def _flat_series(n=400, start="2020-01-01"):
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    close = np.full(n, 100.0)
    return pd.DataFrame({"open": close, "high": close + 0.1, "low": close - 0.1,
                        "close": close, "volume": np.full(n, 1000.0)}, index=idx)


def test_run_walk_forward_produces_non_overlapping_windows():
    cfg = make_cfg()  # train=2ay, test=1ay, step=1ay
    df = _flat_series(n=500)  # ~16 ay
    results = run_walk_forward(["TEST"], cfg, lambda s: df)
    assert len(results) > 0
    for r in results:
        assert r.train_end == r.test_start  # train biter bitmez test başlıyor
        assert r.test_end > r.test_start
    # ardışık pencereler step_months kadar kayıyor
    if len(results) > 1:
        expected_next_start = results[0].train_start + pd.DateOffset(months=cfg.backtest.walk_forward.step_months)
        assert results[1].train_start == expected_next_start


def test_disabled_gates_forwarded_to_all_internal_run_backtest_calls(monkeypatch):
    """Portföy ablasyon turu: `run_walk_forward`'a verilen `disabled_gates`,
    train grid taramasının HER kombinasyonuna VE test koşumuna aynen
    iletilmeli."""
    import backtest.walkforward as wf_mod
    calls = []
    original = wf_mod.run_backtest

    def _spy(*args, **kwargs):
        calls.append(kwargs.get("disabled_gates"))
        return original(*args, **kwargs)

    monkeypatch.setattr(wf_mod, "run_backtest", _spy)

    cfg = make_cfg()
    df = _flat_series(n=500)
    run_walk_forward(["TEST"], cfg, lambda s: df, disabled_gates=["regime"])

    assert len(calls) > 0
    assert all(c == ["regime"] for c in calls)


def test_disabled_gates_none_default_forwards_none(monkeypatch):
    import backtest.walkforward as wf_mod
    calls = []
    original = wf_mod.run_backtest

    def _spy(*args, **kwargs):
        calls.append(kwargs.get("disabled_gates"))
        return original(*args, **kwargs)

    monkeypatch.setattr(wf_mod, "run_backtest", _spy)

    cfg = make_cfg()
    df = _flat_series(n=500)
    run_walk_forward(["TEST"], cfg, lambda s: df)  # disabled_gates verilmedi

    assert len(calls) > 0
    assert all(c is None for c in calls)


def test_run_walk_forward_empty_data_returns_empty_list():
    cfg = make_cfg()
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    results = run_walk_forward(["TEST"], cfg, lambda s: empty)
    assert results == []


# --- OOS birleştirme + kabul kriteri ---

def make_trade(entry_date, exit_date, pnl, r_multiple=1.0):
    return Trade(
        symbol="A", entry_date=pd.Timestamp(entry_date, tz="UTC"), entry_price=100.0,
        exit_date=pd.Timestamp(exit_date, tz="UTC"), exit_price=105.0,
        quantity=10, exit_reason="TARGET", pnl=pnl, r_multiple=r_multiple,
    )


def _fake_window(test_trades, train_dd=0.05):
    from backtest.metrics import Metrics
    train_m = Metrics(0, 0, -train_dd, 0, 0, 0, 0, 0, 5, 0)
    test_m = Metrics(0, 0, 0, 0, 0, 0, 0, 0, len(test_trades), 0)
    return WindowResult(
        train_start=pd.Timestamp("2020-01-01", tz="UTC"), train_end=pd.Timestamp("2020-03-01", tz="UTC"),
        test_start=pd.Timestamp("2020-03-01", tz="UTC"), test_end=pd.Timestamp("2020-04-01", tz="UTC"),
        chosen_params={"atr_stop_mult": 1.5, "adx_min": 20, "min_rr": 1.8},
        train_metrics=train_m, test_metrics=test_m, test_trades=test_trades, robust=True,
    )


def test_combined_oos_metrics_aggregates_across_windows():
    w1 = _fake_window([make_trade("2020-03-05", "2020-03-10", 100)])
    w2 = _fake_window([make_trade("2020-04-05", "2020-04-10", -30)])
    combined = combined_oos_metrics([w1, w2])
    assert combined.trade_count == 2
    assert combined.expectancy == pytest.approx((100 - 30) / 2)


def test_combined_oos_metrics_empty_when_no_trades():
    w = _fake_window([])
    combined = combined_oos_metrics([w])
    assert combined.trade_count == 0


def test_evaluate_acceptance_passes_good_scenario():
    trades = [make_trade("2020-03-05", "2020-03-10", 200), make_trade("2020-03-12", "2020-03-15", -50)]
    w = _fake_window(trades, train_dd=0.10)
    result = evaluate_acceptance([w])
    assert result["oos_profit_factor"] == pytest.approx(200 / 50)
    assert result["passed"]


def test_evaluate_acceptance_fails_on_poor_profit_factor():
    trades = [make_trade("2020-03-05", "2020-03-10", 50), make_trade("2020-03-12", "2020-03-15", -200)]
    w = _fake_window(trades, train_dd=0.10)
    result = evaluate_acceptance([w])
    assert not result["passed"]
    assert not result["pf_ok"]


def test_evaluate_acceptance_no_windows_fails():
    result = evaluate_acceptance([])
    assert not result["passed"]

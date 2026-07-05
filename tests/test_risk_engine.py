from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from core.models import AccountState, Position, RejectReason, Signal, SignalAction
from risk.risk_engine import (
    check_and_trip_breaker,
    historical_correlation,
    size_and_approve,
)


def make_cfg():
    risk = SimpleNamespace(
        risk_per_trade_pct=0.0075,
        daily_loss_limit_pct=0.025,
        weekly_loss_limit_pct=0.05,
        max_open_positions=2,
        max_position_notional_pct=0.25,
        max_drawdown_breaker_pct=0.10,
        min_rr=1.8,
        correlation_lookback_days=90,
        correlation_max=0.85,
        news_blackout=False,
    )
    costs = SimpleNamespace(commission_bps=10, slippage_bps=5)
    safety = SimpleNamespace(kill_switch_file="runtime/__nonexistent_kill_switch_for_tests__")
    return SimpleNamespace(risk=risk, costs=costs, safety=safety)


def make_signal(entry=100.0, stop=94.0, target=112.0, symbol="TEST") -> Signal:
    return Signal(
        symbol=symbol, ts=datetime(2024, 1, 1, tzinfo=timezone.utc),
        action=SignalAction.ENTER_LONG, reasons=["test"], features={},
        entry_ref_price=entry, suggested_stop=stop, suggested_target=target,
    )


def make_account(equity=100_000.0, cash=100_000.0, positions=None,
                 peak_equity=None, realized_pnl_today=0.0, realized_pnl_week=0.0) -> AccountState:
    return AccountState(
        equity=equity, cash=cash, positions=positions or [],
        peak_equity=peak_equity if peak_equity is not None else equity,
        realized_pnl_today=realized_pnl_today, realized_pnl_week=realized_pnl_week,
    )


def make_position(symbol="OTHER") -> Position:
    return Position(
        symbol=symbol, quantity=10, avg_price=50.0, stop_price=47.0, target_price=60.0,
        opened_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


NO_CORR = lambda symbol, positions: 0.0  # noqa: E731


# --- Baseline: hepsi PASS -> onaylı ve doğru boyutlama ---

def test_baseline_all_pass_approves_with_expected_sizing():
    cfg = make_cfg()
    sig = make_signal(entry=100, stop=94, target=112)
    acct = make_account()
    decision = size_and_approve(sig, acct, cfg, NO_CORR)
    assert decision.approved
    assert decision.reject_reasons == []
    assert decision.quantity == 125
    assert decision.stop_price == 94
    assert decision.target_price == 112
    assert decision.risk_amount_try == pytest.approx(125 * 6)


def test_numeric_example_from_spec_bolum_9_3():
    # equity=100.000, risk %0.75, entry=100, stop=94 -> risk 750 TL / 6 TL = 125 lot;
    # notional tavanı 25.000/100=250 -> bağlayıcı değil -> beklenen qty=125
    cfg = make_cfg()
    sig = make_signal(entry=100, stop=94, target=200)  # yüksek target, yalnızca boyutlamayı test ediyoruz
    acct = make_account(equity=100_000, cash=100_000)
    decision = size_and_approve(sig, acct, cfg, NO_CORR)
    assert decision.approved
    assert decision.quantity == 125


# --- Her reddetme nedeni için izole test ---

def test_kill_switch_rejects(tmp_path):
    cfg = make_cfg()
    kf = tmp_path / "KILL_SWITCH"
    kf.write_text("")
    cfg.safety.kill_switch_file = str(kf)
    decision = size_and_approve(make_signal(), make_account(), cfg, NO_CORR)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.KILL_SWITCH]


def test_drawdown_breaker_rejects(tmp_path, monkeypatch):
    import risk.risk_engine as re_mod
    monkeypatch.setattr(re_mod, "BREAKER_FILE", tmp_path / "BREAKER_TRIPPED")
    re_mod.BREAKER_FILE.write_text("already tripped")
    cfg = make_cfg()
    decision = size_and_approve(make_signal(), make_account(), cfg, NO_CORR)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.DRAWDOWN_BREAKER]


def test_check_and_trip_breaker_writes_file_when_drawdown_exceeded(tmp_path, monkeypatch):
    import risk.risk_engine as re_mod
    breaker_path = tmp_path / "BREAKER_TRIPPED"
    monkeypatch.setattr(re_mod, "BREAKER_FILE", breaker_path)
    cfg = make_cfg()
    acct = make_account(equity=89_000, peak_equity=100_000)  # %11 drawdown > %10 eşik
    tripped = check_and_trip_breaker(acct, cfg)
    assert tripped
    assert breaker_path.exists()


def test_check_and_trip_breaker_does_not_trip_below_threshold(tmp_path, monkeypatch):
    import risk.risk_engine as re_mod
    breaker_path = tmp_path / "BREAKER_TRIPPED"
    monkeypatch.setattr(re_mod, "BREAKER_FILE", breaker_path)
    cfg = make_cfg()
    acct = make_account(equity=95_000, peak_equity=100_000)  # %5 drawdown < %10 eşik
    tripped = check_and_trip_breaker(acct, cfg)
    assert not tripped
    assert not breaker_path.exists()


def test_daily_loss_limit_rejects():
    cfg = make_cfg()
    acct = make_account(realized_pnl_today=-0.03 * 100_000)  # %3 > %2.5 limit
    decision = size_and_approve(make_signal(), acct, cfg, NO_CORR)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.DAILY_LOSS_LIMIT]


def test_weekly_loss_limit_rejects():
    cfg = make_cfg()
    acct = make_account(realized_pnl_week=-0.06 * 100_000)  # %6 > %5 limit
    decision = size_and_approve(make_signal(), acct, cfg, NO_CORR)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.WEEKLY_LOSS_LIMIT]


def test_max_positions_rejects():
    cfg = make_cfg()
    acct = make_account(positions=[make_position("A"), make_position("B")])
    decision = size_and_approve(make_signal(), acct, cfg, NO_CORR)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.MAX_POSITIONS]


def test_min_rr_failed_rejects():
    cfg = make_cfg()
    sig = make_signal(entry=100, stop=94, target=105)  # rr = 5/6 = 0.83 < 1.8
    decision = size_and_approve(sig, make_account(), cfg, NO_CORR)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.MIN_RR_FAILED]


def test_correlation_limit_rejects():
    cfg = make_cfg()
    acct = make_account(positions=[make_position("A")])
    high_corr = lambda symbol, positions: 0.90  # noqa: E731
    decision = size_and_approve(make_signal(), acct, cfg, high_corr)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.CORRELATION_LIMIT]


def test_correlation_below_max_does_not_reject():
    cfg = make_cfg()
    acct = make_account(positions=[make_position("A")])
    low_corr = lambda symbol, positions: 0.5  # noqa: E731
    decision = size_and_approve(make_signal(), acct, cfg, low_corr)
    assert decision.approved


def test_position_too_small_rejects():
    cfg = make_cfg()
    acct = make_account(equity=100, cash=100)  # risk_amount=0.75, per_share_risk=6 -> qty=0
    decision = size_and_approve(make_signal(), acct, cfg, NO_CORR)
    assert not decision.approved
    assert decision.reject_reasons == [RejectReason.POSITION_TOO_SMALL]


# --- Kırpma senaryoları ---

def test_notional_cap_binds():
    cfg = make_cfg()
    cfg.risk.max_position_notional_pct = 0.01  # max_notional=1000 -> notional qty cap=10
    decision = size_and_approve(make_signal(entry=100, stop=94, target=112), make_account(), cfg, NO_CORR)
    assert decision.approved
    assert decision.quantity == 10


def test_cash_cap_binds():
    cfg = make_cfg()
    acct = make_account(equity=100_000, cash=500)  # floor(500/100.1) = 4
    decision = size_and_approve(make_signal(entry=100, stop=94, target=112), acct, cfg, NO_CORR)
    assert decision.approved
    assert decision.quantity == 4


# --- Korelasyon hesabı ---

def _price_loader_factory(series_map: dict[str, pd.Series]):
    def _loader(symbol: str) -> pd.Series:
        return series_map[symbol]
    return _loader


def test_historical_correlation_perfectly_correlated_series():
    idx = pd.date_range("2024-01-01", periods=30, freq="1D")
    base = pd.Series(range(100, 130), index=idx, dtype=float)
    series_map = {"A": base, "B": base * 2}  # getiriler ölçekten bağımsız, mükemmel pozitif korelasyon
    positions = [make_position("B")]
    corr = historical_correlation("A", positions, _price_loader_factory(series_map), lookback_days=90)
    assert corr == pytest.approx(1.0, abs=1e-6)


def test_historical_correlation_no_positions_returns_zero():
    idx = pd.date_range("2024-01-01", periods=30, freq="1D")
    series_map = {"A": pd.Series(range(100, 130), index=idx, dtype=float)}
    corr = historical_correlation("A", [], _price_loader_factory(series_map), lookback_days=90)
    assert corr == 0.0


def test_historical_correlation_uncorrelated_series_near_zero():
    idx = pd.date_range("2024-01-01", periods=30, freq="1D")
    import numpy as np
    rng = np.random.default_rng(42)
    a = pd.Series(100 + rng.standard_normal(30).cumsum(), index=idx)
    b = pd.Series(100 + rng.standard_normal(30).cumsum(), index=idx)
    positions = [make_position("B")]
    corr = historical_correlation("A", positions, _price_loader_factory({"A": a, "B": b}), lookback_days=90)
    assert corr < 0.85

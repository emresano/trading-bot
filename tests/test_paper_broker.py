# tests/test_paper_broker.py
"""F5A-2 — PaperBroker + regime_core runner testleri (offline, deterministik)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.models import Side
from execution.broker_adapter import BrokerError
from execution.paper_broker import PaperBroker
from execution.regime_core_runner import RegimeCoreRunner
from strategy.regime_core import RegimeCoreParams, CASH_YIELD_HAIRCUT


def _broker(tmp_path, **kw) -> PaperBroker:
    return PaperBroker(initial_equity=100_000, commission_bps=10, slippage_bps=5,
                       state_path=tmp_path / "paper.sqlite", **kw)


def test_market_buy_fill_and_cash(tmp_path):
    b = _broker(tmp_path)
    b.update_prices({"THYAO": 100.0})
    b.submit_market_order("THYAO", Side.BUY, 10)
    # fill = 100*(1+0.0005)=100.05; gross=1000.5; comm=1.0005; cash -= 1001.5005
    assert b.cash == pytest.approx(100_000 - 1001.5005, abs=1e-6)
    pos = b.get_positions()
    assert len(pos) == 1 and pos[0].quantity == 10
    assert pos[0].avg_price == pytest.approx(100.05, abs=1e-9)
    b.close()


def test_market_sell_proceeds(tmp_path):
    b = _broker(tmp_path)
    b.update_prices({"THYAO": 100.0})
    b.submit_market_order("THYAO", Side.BUY, 10)
    cash_after_buy = b.cash
    b.update_prices({"THYAO": 110.0})
    b.submit_market_order("THYAO", Side.SELL, 10)
    # sell fill = 110*(1-0.0005)=109.945; gross=1099.45; comm=1.09945; cash += 1098.35055
    assert b.cash == pytest.approx(cash_after_buy + 1098.35055, abs=1e-6)
    assert b.get_positions() == []
    b.close()


def test_insufficient_cash_raises(tmp_path):
    b = _broker(tmp_path)
    b.update_prices({"THYAO": 100.0})
    with pytest.raises(BrokerError, match="INSUFFICIENT_CASH"):
        b.submit_market_order("THYAO", Side.BUY, 2000)  # 2000*100 > 100k
    b.close()


def test_restart_state_recovery(tmp_path):
    path = tmp_path / "paper.sqlite"
    b1 = PaperBroker(100_000, 10, 5, state_path=path)
    b1.update_prices({"THYAO": 100.0})
    b1.submit_market_order("THYAO", Side.BUY, 10)
    cash1 = b1.cash
    b1.close()
    # yeni süreç: aynı dosyadan kurtar
    b2 = PaperBroker(100_000, 10, 5, state_path=path)
    assert b2.cash == pytest.approx(cash1, abs=1e-9)
    assert b2.quantities() == {"THYAO": 10}
    assert b2.get_last_price("THYAO") == 100.0  # fiyat da kurtarıldı
    b2.close()


def test_cash_accrual_matches_regime_core_formula(tmp_path):
    b = _broker(tmp_path)
    rate, days = 0.35, 3
    interest = b.accrue_cash(rate, days)
    r_net = max(rate - CASH_YIELD_HAIRCUT, 0.0)
    expected = 100_000 * (1 + r_net / 365) ** days
    assert b.cash == pytest.approx(expected, abs=1e-6)
    assert b.accrued_interest == pytest.approx(interest, abs=1e-9)
    assert b.accrued_interest == pytest.approx(expected - 100_000, abs=1e-6)
    b.close()


def test_cash_accrual_haircut_floor_at_zero(tmp_path):
    b = _broker(tmp_path)
    interest = b.accrue_cash(0.01, 30)  # rate < haircut → r_net=0 → faiz yok
    assert interest == 0.0
    assert b.cash == pytest.approx(100_000, abs=1e-9)
    b.close()


def test_bracket_stop_priority(tmp_path):
    b = _broker(tmp_path)
    b.update_prices({"THYAO": 100.0})
    b.submit_bracket_order("THYAO", Side.BUY, 10, stop_price=90.0, target_price=110.0)
    # aynı barda stop VE target tetiklenirse STOP öncelikli (last=95 sadece stop değil;
    # last <= stop kontrolü ilk): last=85 → stop
    result = b.process_price("THYAO", 85.0)
    assert result == "STOP"
    assert b.get_positions() == []
    b.close()


def test_session_guard_blocks_when_closed(tmp_path):
    b = _broker(tmp_path, session_check=lambda: False, enforce_session=True)
    b.update_prices({"THYAO": 100.0})
    with pytest.raises(BrokerError, match="MARKET_CLOSED"):
        b.submit_market_order("THYAO", Side.BUY, 1)
    b.close()


# ------------------------------------------------------------------ runner smoke
def _closes(values: list[float]) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx)


def test_runner_enter_then_exit(tmp_path):
    b = _broker(tmp_path)
    closes = {"THYAO": _closes([100, 100, 100, 110, 120, 110, 90])}
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              commission_bps=10, slippage_bps=5, initial_equity=100_000)
    runner = RegimeCoreRunner(b, params, state_path=tmp_path / "runner.sqlite")
    decisions = runner.process_up_to(closes)
    actions = [d.action for d in decisions]
    # regime_on = F,F,F,T,T,F,F → ENTER at index4 (d4), EXIT at index6 (d6)
    assert "ENTER" in actions and "EXIT" in actions
    assert actions.index("ENTER") == 4
    assert actions.index("EXIT") == 6
    assert b.quantities() == {}  # sonda nakitte
    runner.close()
    b.close()


def test_runner_parity_with_backtest_driver(tmp_path):
    """KRİTİK: runner (canlı loop) ↔ run_regime_core_prod (backtest) aynı SAF
    fonksiyonları kullandığından anahtarlama tarihleri/aksiyonları BİREBİR aynı;
    equity ULP/toplama-sırası düzeyinde örtüşür (parite, B5)."""
    import numpy as np
    from strategy.regime_core import run_regime_core_prod

    rng = np.random.default_rng(7)
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    # rejimi birkaç kez çevirecek trend + gürültü
    trend = np.concatenate([np.linspace(100, 140, 20), np.linspace(140, 100, 20),
                            np.linspace(100, 150, 20)])
    closes = {
        "AAA": pd.Series(trend + rng.normal(0, 1, n), index=idx),
        "BBB": pd.Series(trend * 0.5 + rng.normal(0, 0.5, n), index=idx),
    }
    params = RegimeCoreParams(symbols=["AAA", "BBB"], ma_period=5, band_pct=0.005,
                              confirm_days=2, commission_bps=10, slippage_bps=5,
                              initial_equity=100_000)
    bt = run_regime_core_prod(closes, params)
    bt_switches = [(pd.Timestamp(s.date), s.action) for s in bt.switches]

    b = _broker(tmp_path)
    runner = RegimeCoreRunner(b, params, state_path=tmp_path / "runner.sqlite")
    decs = runner.process_up_to(closes)
    live_switches = [(pd.Timestamp(d.date), d.action) for d in decs if d.action in ("ENTER", "EXIT")]

    assert live_switches == bt_switches, f"switch parite kırıldı\nBT={bt_switches}\nLIVE={live_switches}"
    assert len(bt_switches) >= 2  # en az bir ENTER + EXIT
    # equity örtüşmesi (toplama sırası → tolerans)
    final_live = decs[-1].equity_after
    final_bt = float(bt.equity_curve.iloc[-1])
    assert final_live == pytest.approx(final_bt, rel=1e-9)
    runner.close()
    b.close()


def test_runner_idempotent_no_reprocess(tmp_path):
    b = _broker(tmp_path)
    closes = {"THYAO": _closes([100, 100, 100, 110, 120, 110, 90])}
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              initial_equity=100_000)
    runner = RegimeCoreRunner(b, params, state_path=tmp_path / "runner.sqlite")
    d1 = runner.process_up_to(closes)
    d2 = runner.process_up_to(closes)  # aynı veri tekrar → işlenmemiş gün yok
    assert len(d1) == 7 and len(d2) == 0
    runner.close()
    b.close()

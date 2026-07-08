# tests/test_scheduler.py
"""F5-B1 — gölge paper scheduler testleri (OFFLINE, ağ yok — feed enjekte)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from data.live_feed import LiveDataFeed
from data.live_store import LiveHistoryStore
from main import PaperScheduler


BDAYS = pd.bdate_range("2025-03-03", periods=12)  # 12 iş günü (2026 tatili değil)


def _seed_store(store: LiveHistoryStore, symbols, series):
    for sym in symbols:
        df = pd.DataFrame(
            {"open": series, "high": series, "low": series, "close": series,
             "volume": [1000.0] * len(series)},
            index=pd.DatetimeIndex(BDAYS, name="ts").tz_localize("UTC"))
        store.upsert_bars(sym, df, source="test")


def _cfg(go_live=None):
    return {
        "symbols": ["THYAO", "GARAN"],
        "regime": {"ma_period": 3, "band_pct": 0.0, "confirm_days": 1},
        "costs": {"commission_bps": 10, "slippage_bps": 5},
        "initial_equity": 100000,
        "safety": {"freeze_dir": None},   # __init__ runtime altına düşer
        "telegram": {"enabled": False},
        "paper": {"go_live_date": go_live},
    }


def _make(tmp_path, go_live=None, rising=True):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    series = [100.0 + i for i in range(12)] if rising else [200.0 - i for i in range(12)]
    _seed_store(store, ["THYAO", "GARAN"], series)
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=lambda y, s: pd.DataFrame())
    cfg = _cfg(go_live)
    if cfg["safety"]["freeze_dir"] is None:
        cfg["safety"]["freeze_dir"] = str(tmp_path / "freeze")
    sent = []
    sched = PaperScheduler(cfg, tmp_path / "rt", feed=feed, notifier_sender=sent.append)
    return sched, sent


def test_observe_mode_logs_signal_no_trade(tmp_path: Path):
    sched, sent = _make(tmp_path, go_live=None, rising=True)
    assert sched.mode == "observe"
    sched.startup()
    res = sched.run_cycle(BDAYS[-1].date())
    assert res.mode == "observe"
    assert res.regime_on is True                 # yükselen seri → rejim ON
    assert res.action == "OBSERVE_REGIME_ON"
    assert sched.broker.quantities() == {}       # OBSERVE: işlem yok
    # journal'da signal_eval kaydı var
    rows = sched.journal.read_all()
    assert any(r["type"] == "signal_eval" for r in rows)
    # heartbeat yazıldı
    assert (sched.runtime / "heartbeat").exists()
    sched.close()


def test_skipped_when_not_trading_day(tmp_path: Path):
    sched, _ = _make(tmp_path, go_live=None)
    res = sched.run_cycle(date(2025, 3, 8))   # Cumartesi
    assert res.mode == "skipped" and res.trading_day is False
    assert (sched.runtime / "heartbeat").exists()
    sched.close()


def test_active_initial_enter_on_golive_regime_on(tmp_path: Path):
    go_live = BDAYS[4].date()                    # rejim bu tarihte ON (yükselen seri)
    sched, sent = _make(tmp_path, go_live=go_live, rising=True)
    assert sched.mode == "active"
    sched.startup()
    res = sched.run_cycle(BDAYS[-1].date())
    # ilk aktif günde mevcut rejim benimsendi → INITIAL_ENTER
    rows = sched.journal.read_all()
    actions = [r.get("action") for r in rows if r["type"] == "decision"]
    assert "INITIAL_ENTER" in actions
    assert sched.broker.quantities()             # pozisyon açıldı
    sched.close()


def test_active_regime_off_stays_cash(tmp_path: Path):
    go_live = BDAYS[4].date()
    sched, _ = _make(tmp_path, go_live=go_live, rising=False)  # düşen seri → rejim OFF
    sched.startup()
    res = sched.run_cycle(BDAYS[-1].date())
    rows = sched.journal.read_all()
    actions = [r.get("action") for r in rows if r["type"] == "decision"]
    assert "INITIAL_ENTER" not in actions
    assert sched.broker.quantities() == {}       # nakitte
    sched.close()


def test_parity_matches_after_active_cycle(tmp_path: Path):
    go_live = BDAYS[4].date()
    sched, _ = _make(tmp_path, go_live=go_live, rising=True)
    sched.startup()
    sched.run_cycle(BDAYS[-1].date())
    par = sched.parity_check(BDAYS[-1].date())
    assert par["applicable"] is True
    assert par["matched"] is True                # temiz replay ↔ canlı journal özdeş
    assert any(a == "INITIAL_ENTER" for _, a in par["live_switches"])
    sched.close()


def test_parity_not_applicable_in_observe(tmp_path: Path):
    sched, _ = _make(tmp_path, go_live=None)
    par = sched.parity_check(BDAYS[-1].date())
    assert par["applicable"] is False
    sched.close()


def test_provisional_bar_flagged_and_execution_deferred(tmp_path: Path):
    """as_of barı henüz kapanmamışsa (seans-içi 'now') → signal_eval provisional=True."""
    from datetime import datetime, timezone
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    _seed_store(store, ["THYAO", "GARAN"], [100.0 + i for i in range(12)])
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=lambda y, s: pd.DataFrame())
    cfg = _cfg(None)
    cfg["safety"]["freeze_dir"] = str(tmp_path / "freeze")
    # 'now' = son bar gününün seans-içi (12:00 Istanbul = 09:00 UTC) → bar henüz açık
    as_of = BDAYS[-1].date()
    now_intraday = datetime(as_of.year, as_of.month, as_of.day, 9, 0, tzinfo=timezone.utc)
    sched = PaperScheduler(cfg, tmp_path / "rt", feed=feed, now_fn=lambda: now_intraday)
    res = sched.run_cycle(as_of)
    rows = sched.journal.read_all()
    sev = [r for r in rows if r["type"] == "signal_eval"]
    assert sev and sev[-1]["provisional"] is True
    assert any("PROVISIONAL" in n or "KAPANMADI" in n for n in res.notes)
    sched.close()


def test_data_completeness_defers_partial_basket(tmp_path: Path):
    """K6 kök-neden: as_of gününde bir sembolün barı eksikse (yfinance gecikmesi)
    yürütme ERTELENİR (kısmi basket yasağı) — WARN + son tam güne sınırlanır."""
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    # THYAO tüm günler; GARAN son gün EKSİK (yfinance gecikmesi emsali)
    full = [100.0 + i for i in range(12)]
    idx = pd.DatetimeIndex(BDAYS, name="ts").tz_localize("UTC")
    store.upsert_bars("THYAO", pd.DataFrame(
        {"open": full, "high": full, "low": full, "close": full, "volume": [1000.0]*12},
        index=idx), source="test")
    garan = full[:-1]
    store.upsert_bars("GARAN", pd.DataFrame(
        {"open": garan, "high": garan, "low": garan, "close": garan, "volume": [1000.0]*11},
        index=idx[:-1]), source="test")
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=lambda y, s: pd.DataFrame())
    cfg = _cfg(BDAYS[4].date())
    cfg["safety"]["freeze_dir"] = str(tmp_path / "freeze")
    sched = PaperScheduler(cfg, tmp_path / "rt", feed=feed, notifier_sender=[].append)
    sched.startup()
    res = sched.run_cycle(BDAYS[-1].date())   # son gün GARAN eksik
    assert any("VERİ EKSİK" in n for n in res.notes)
    # yürütme yine de INITIAL_ENTER (BDAYS[5], iki sembol de var) — TAM basket
    assert set(sched.broker.quantities()) == {"THYAO", "GARAN"}
    sched.close()


def test_initial_enter_cost_reconciliation(tmp_path: Path):
    """K6: INITIAL_ENTER equity_after == initial − komisyon(10bp) − slippage_drag(5bp),
    invested notional üzerinden — bit-bit (broker yolu = plan_enter formülü)."""
    from execution.paper_broker import PaperBroker
    from strategy.regime_core import plan_enter
    from core.models import Side
    syms = ["THYAO", "GARAN", "ASELS"]
    prices = {"THYAO": 347.25, "GARAN": 134.40, "ASELS": 385.0}
    eq, comm, slip = 100000.0, 10.0, 5.0
    qty, cash_after = plan_enter(eq, prices, syms, comm, slip)
    b = PaperBroker(eq, comm, slip, state_path=tmp_path / "b.sqlite")
    b.update_prices(prices)
    for s in syms:
        if s in qty:
            b.submit_market_order(s, Side.BUY, qty[s])
    acct = b.get_account_state()
    slip_frac, comm_frac = slip / 1e4, comm / 1e4
    sum_comm = sum(prices[s] * (1 + slip_frac) * qty[s] * comm_frac for s in qty)
    sum_slip = sum(prices[s] * slip_frac * qty[s] for s in qty)
    expected = eq - sum_comm - sum_slip
    assert abs(b.cash - cash_after) < 1e-9          # broker == plan_enter
    assert abs(acct.equity - expected) < 1e-6       # equity == initial − comm − slip
    assert acct.equity < eq                          # maliyet drag'i (kusur değil)
    b.close()


def test_shadow_reconciliation_logs_no_broker(tmp_path: Path):
    sched, sent = _make(tmp_path, go_live=None)
    sched.startup()
    rows = sched.journal.read_all()
    recon_msgs = [r for r in rows if r.get("category") == "RECON"]
    assert any("GÖLGE" in r.get("message", "") for r in recon_msgs)
    sched.close()

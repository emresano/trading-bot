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


def _cfg(go_live=None, telegram_enabled=False):
    return {
        "symbols": ["THYAO", "GARAN"],
        "regime": {"ma_period": 3, "band_pct": 0.0, "confirm_days": 1},
        "costs": {"commission_bps": 10, "slippage_bps": 5},
        "initial_equity": 100000,
        "safety": {"freeze_dir": None},   # __init__ runtime altına düşer
        "telegram": {"enabled": telegram_enabled},
        "paper": {"go_live_date": go_live},
    }


def _make(tmp_path, go_live=None, rising=True, telegram_enabled=False):
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    series = [100.0 + i for i in range(12)] if rising else [200.0 - i for i in range(12)]
    _seed_store(store, ["THYAO", "GARAN"], series)
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=lambda y, s: pd.DataFrame())
    cfg = _cfg(go_live, telegram_enabled=telegram_enabled)
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


def _sched_with_clock(tmp_path, now_dt, go_live=None, subdir="rt"):
    store = LiveHistoryStore(tmp_path / f"{subdir}.sqlite")
    _seed_store(store, ["THYAO", "GARAN"], [100.0 + i for i in range(12)])
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=lambda y, s: pd.DataFrame())
    cfg = _cfg(go_live)
    cfg["safety"]["freeze_dir"] = str(tmp_path / f"freeze_{subdir}")
    return PaperScheduler(cfg, tmp_path / subdir, feed=feed,
                          notifier_sender=[].append, now_fn=lambda: now_dt)


def test_provisional_intrasession_flags_true_no_trade(tmp_path: Path):
    """K5: seans-içi 'now' (kapanış öncesi) → provisional=True + observe'da işlem yok."""
    from datetime import datetime, timezone
    as_of = BDAYS[-1].date()
    intraday = datetime(as_of.year, as_of.month, as_of.day, 9, 0, tzinfo=timezone.utc)  # 12:00 Istanbul
    sched = _sched_with_clock(tmp_path, intraday, go_live=None, subdir="a")
    res = sched.run_cycle(as_of)
    sev = [r for r in sched.journal.read_all() if r["type"] == "signal_eval"]
    assert sev and sev[-1]["provisional"] is True
    assert any("PROVISIONAL" in n or "KAPANMADI" in n for n in res.notes)
    assert sched.broker.quantities() == {}    # işlem yok
    sched.close()


def test_provisional_postclose_flags_false(tmp_path: Path):
    """K5 diğer yön: kapanış+grace SONRASI 'now' → provisional=False (bar final)."""
    from datetime import datetime, timezone
    as_of = BDAYS[-1].date()
    # 18:00 kapanış + 3600s grace = 19:00 Istanbul = 16:00 UTC; 20:00 UTC → final
    post_close = datetime(as_of.year, as_of.month, as_of.day, 20, 0, tzinfo=timezone.utc)
    sched = _sched_with_clock(tmp_path, post_close, go_live=None, subdir="b")
    res = sched.run_cycle(as_of)
    sev = [r for r in sched.journal.read_all() if r["type"] == "signal_eval"]
    assert sev and sev[-1]["provisional"] is False
    assert not any("PROVISIONAL" in n for n in res.notes)
    sched.close()


def test_provisional_active_intrasession_defers_execution(tmp_path: Path):
    """K5: active modda seans-içi → yürütme son yürütülebilir güne sınırlı (bugün açık)."""
    from datetime import datetime, timezone
    as_of = BDAYS[-1].date()
    intraday = datetime(as_of.year, as_of.month, as_of.day, 9, 0, tzinfo=timezone.utc)
    sched = _sched_with_clock(tmp_path, intraday, go_live=BDAYS[4].date(), subdir="c")
    sched.startup()
    sched.run_cycle(as_of)
    # yürütme bugünün (açık) barına DAYANMAZ — son işlenen karar günü < as_of olmalı
    last_proc, *_ = sched.runner._state()
    assert last_proc is not None and last_proc < pd.Timestamp(as_of, tz="UTC")
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


def _make_series(tmp_path, series, go_live, subdir="rt"):
    store = LiveHistoryStore(tmp_path / f"{subdir}.sqlite")
    _seed_store(store, ["THYAO", "GARAN"], series)
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=lambda y, s: pd.DataFrame())
    cfg = _cfg(go_live)
    cfg["safety"]["freeze_dir"] = str(tmp_path / f"freeze_{subdir}")
    return PaperScheduler(cfg, tmp_path / subdir, feed=feed, notifier_sender=[].append)


def test_catchup_no_switch_no_delayed_alarm(tmp_path: Path):
    """K3(a): bot birkaç gün kapalı, gapte anahtarlama YOK → kaçan günler sırayla
    işlenir (HOLD), GECİKMİŞ SİNYAL alarmı YOK, yeni işlem yok."""
    rising = [100.0 + i for i in range(12)]           # rejim sürekli ON
    sched = _make_series(tmp_path, rising, BDAYS[4].date(), subdir="a")
    sched.startup()
    sched.run_cycle(BDAYS[5].date())                  # aktivasyon → INITIAL_ENTER
    held = dict(sched.broker.quantities())
    assert held                                       # pozisyon açık
    sched.run_cycle(BDAYS[9].date())                  # 3 gün downtime, catch-up
    events = [r for r in sched.journal.read_all() if r.get("category") == "DELAYED_SIGNAL"]
    assert events == []                               # gecikmiş sinyal YOK
    assert dict(sched.broker.quantities()) == held    # pozisyon değişmedi
    sched.close()


def test_catchup_with_gap_switch_emits_delayed_signal(tmp_path: Path):
    """K3(b): bot kapalıyken rejim EXIT'i oluştu → GECİKMİŞ SİNYAL alarmı + journal
    etiketi + catch-up ile yürütüldü (pozisyon kapandı)."""
    # 0..6 yükselir (rejim ON), 7'de düşer → rejim OFF → BDAYS[8]'de EXIT
    series = [100.0, 101, 102, 103, 104, 105, 106, 90, 90, 90, 90, 90]
    sched = _make_series(tmp_path, series, BDAYS[4].date(), subdir="b")
    sched.startup()
    sched.run_cycle(BDAYS[5].date())                  # INITIAL_ENTER (rejim ON)
    assert sched.broker.quantities()
    sched.run_cycle(BDAYS[9].date())                  # downtime; gapte EXIT oldu
    events = [r for r in sched.journal.read_all() if r.get("category") == "DELAYED_SIGNAL"]
    assert events, "GECİKMİŞ SİNYAL alarmı bekleniyordu"
    assert any("EXIT" in r["message"] for r in events)
    assert sched.broker.quantities() == {}            # EXIT yürütüldü, nakitte
    sched.close()


def _dividend_fetch(adjust=0.98):
    """yfinance temettü sonrası auto_adjust emsali: GEÇMİŞ kapanışları ×adjust ile
    yeniden düzeltir. UTC-gece-yarısı barlar (normalize kimlik)."""
    def _fn(yf_sym, start):
        idx = pd.DatetimeIndex(BDAYS, name="ts").tz_localize("UTC")
        adj = [(100.0 + i) * adjust for i in range(12)]
        return pd.DataFrame({"open": adj, "high": adj, "low": adj, "close": adj,
                             "volume": [1000.0]*12}, index=idx)
    return _fn


def test_data_drift_blocks_finalization_and_resync_fixes(tmp_path: Path):
    """K4 uçtan uca: temettü yeniden-düzeltmesi → DATA_DRIFT (finalize edilmez) →
    resync tarihçeyi tazeler → drift kaybolur."""
    store = LiveHistoryStore(tmp_path / "h.sqlite")
    _seed_store(store, ["THYAO", "GARAN"], [100.0 + i for i in range(12)])   # orijinal (temettü öncesi)
    feed = LiveDataFeed(store, ["THYAO", "GARAN"], fetch_raw_fn=_dividend_fetch(0.98))
    # drift tespiti: geçmiş barlar %2 sapmış (bugün hariç)
    drifts = feed.detect_drift(exclude_from=pd.Timestamp(BDAYS[-1], tz="UTC"))
    assert drifts, "temettü kayması tespit edilmeliydi"
    assert all(d["pct_diff"] > 0.005 for d in drifts)

    # scheduler döngüsü: DATA_DRIFT alarmı + finalize edilmez
    cfg = _cfg(None)
    cfg["safety"]["freeze_dir"] = str(tmp_path / "freeze")
    sched = PaperScheduler(cfg, tmp_path / "rt", feed=feed, notifier_sender=[].append)
    res = sched.run_cycle(BDAYS[-1].date())
    assert any("VERİ KAYMASI" in n for n in res.notes)
    events = [r for r in sched.journal.read_all() if r.get("category") == "DATA_DRIFT"]
    assert events

    # resync: tam tarihçe yeniden yazılır (adjusted değerler); sonra drift YOK
    rep = sched.resync(BDAYS[-1].date())
    assert sum(rep["replaced"].values()) > 0
    assert feed.detect_drift(exclude_from=pd.Timestamp(BDAYS[-1], tz="UTC")) == []
    # yedek alındı
    assert Path(rep["backup"]).exists()
    sched.close()


def test_shadow_reconciliation_logs_no_broker(tmp_path: Path):
    sched, sent = _make(tmp_path, go_live=None)
    sched.startup()
    rows = sched.journal.read_all()
    recon_msgs = [r for r in rows if r.get("category") == "RECON"]
    assert any("GÖLGE" in r.get("message", "") for r in recon_msgs)
    sched.close()


# ------------------------------------------------------------------ F5-B2a: alarm→Telegram kablolaması
def test_freeze_and_drift_alarms_reach_telegram(tmp_path: Path, monkeypatch):
    """Kuru-test (madde 2): mock FREEZE + mock DATA_DRIFT alarmları enjekte edilen
    Telegram göndericisine ULAŞIR (kısa + maskeli) ve journal'a alarm olarak yazılır.
    Not: enabled = telegram.enabled AND token_present → testte token env'e konur;
    enjekte sender önceliklidir (gerçek HTTP YOK)."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "TESTTOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    sched, sent = _make(tmp_path, go_live=None, telegram_enabled=True)
    sched._alarm({"category": "KILL_SWITCH", "level": "CRITICAL",
                  "message": "consecutive_losses_freeze: 7 ardışık kayıp → FREEZE"})
    sched._alarm({"category": "DATA_DRIFT", "level": "CRITICAL",
                  "message": "THYAO son 30 barda sapma; finalize durduruldu"})
    joined = "\n".join(sent)
    assert "KILL_SWITCH" in joined and "FREEZE" in joined
    assert "DATA_DRIFT" in joined
    # journal alarm kaydı da düşer
    alarms = [r for r in sched.journal.read_all() if r.get("type") == "alarm"]
    cats = {a.get("category") for a in alarms}
    assert {"KILL_SWITCH", "DATA_DRIFT"} <= cats
    sched.close()


def test_eod_summary_sent_with_interest_and_staleness(tmp_path: Path, monkeypatch):
    """EOD özeti Telegram'a gider (K1 faiz satırı EOD şablonunda; bkz. test_notify)."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "TESTTOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    sched, sent = _make(tmp_path, go_live=None, telegram_enabled=True)
    sched.startup()
    sched.run_cycle(BDAYS[-1].date())
    eod = [m for m in sent if "EOD Özet" in m]
    assert eod, "EOD özeti Telegram'a gönderilmedi"
    sched.close()

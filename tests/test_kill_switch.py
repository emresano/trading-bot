# tests/test_kill_switch.py
"""F5A-4 — kill-switch hiyerarşisi kuru-testleri (HARDENING B3).

Her switch en az bir kez simüle-tetiklenir (B7 'kuru-test' gereksinimi hazırlığı).
FREEZE çıkışının yalnızca kullanıcı komutuyla olduğu doğrulanır.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from strategy.regime_core import RegimeCoreBreaker
from safety.kill_switch import (
    KillSwitchManager, SwitchConfig, SW_DAILY_LOSS, SW_CONSEC_LOSS, SW_DATA, SW_API, SW_DRAWDOWN,
)


def _mgr(tmp_path, **overrides):
    cfg = SwitchConfig(**overrides) if overrides else SwitchConfig()
    breaker = RegimeCoreBreaker(freeze_file=tmp_path / "BREAKER")
    alarms = []
    m = KillSwitchManager(cfg, freeze_dir=tmp_path / "freeze", breaker=breaker,
                          alarm_hook=alarms.append, state_path=tmp_path / "ks.sqlite")
    return m, alarms


def test_daily_loss_limit_trips(tmp_path):
    m, alarms = _mgr(tmp_path, daily_loss_limit_pct=0.08)
    ev = m.evaluate_cycle(equity=100_000, peak=100_000, daily_pnl=-9_000)  # -%9 > -%8
    assert any(e.switch == SW_DAILY_LOSS and e.freeze for e in ev)
    assert m.any_frozen() and SW_DAILY_LOSS in m.frozen_switches()
    assert alarms[-1]["level"] == "CRITICAL"
    m.close()


def test_daily_loss_within_limit_no_trip(tmp_path):
    m, _ = _mgr(tmp_path, daily_loss_limit_pct=0.08)
    ev = m.evaluate_cycle(equity=100_000, peak=100_000, daily_pnl=-5_000)  # -%5 < -%8
    assert ev == []
    assert not m.any_frozen()
    m.close()


def test_consecutive_losses_trips_and_win_resets(tmp_path):
    m, _ = _mgr(tmp_path, consecutive_losses_freeze=4)
    assert m.record_trade_result(-100) is None   # 1
    assert m.record_trade_result(-100) is None   # 2
    assert m.record_trade_result(+50) is None     # kazanç → sıfırla
    assert m.record_trade_result(-100) is None    # 1
    assert m.record_trade_result(-100) is None    # 2
    assert m.record_trade_result(-100) is None    # 3
    ev = m.record_trade_result(-100)              # 4 → FREEZE
    assert ev is not None and ev.switch == SW_CONSEC_LOSS and ev.freeze
    assert SW_CONSEC_LOSS in m.frozen_switches()
    m.close()


def test_consecutive_losses_counter_persists_across_restart(tmp_path):
    m, _ = _mgr(tmp_path, consecutive_losses_freeze=4)
    m.record_trade_result(-100)
    m.record_trade_result(-100)
    m.close()
    # yeni süreç, aynı state_path
    m2 = KillSwitchManager(SwitchConfig(consecutive_losses_freeze=4),
                           freeze_dir=tmp_path / "freeze", state_path=tmp_path / "ks.sqlite")
    m2.record_trade_result(-100)   # 3
    ev = m2.record_trade_result(-100)  # 4 → FREEZE (sayaç kurtarıldı)
    assert ev is not None and ev.freeze
    m2.close()


def test_data_stale_trips(tmp_path):
    m, _ = _mgr(tmp_path, data_stale_sec=86400)
    ev = m.evaluate_cycle(100_000, 100_000, 0.0, last_bar_age_sec=200_000)
    assert any(e.switch == SW_DATA and e.freeze for e in ev)
    m.close()


def test_price_jump_trips(tmp_path):
    m, _ = _mgr(tmp_path, data_max_price_jump_pct=0.20)
    ev = m.evaluate_cycle(100_000, 100_000, 0.0, max_intraday_jump_pct=0.35)
    assert any(e.switch == SW_DATA and e.freeze for e in ev)
    m.close()


def test_api_error_rate_trips_and_window_expiry(tmp_path):
    m, _ = _mgr(tmp_path, api_error_freeze_count=3, api_error_window_sec=300)
    assert m.note_api_error(now=1000) is None
    assert m.note_api_error(now=1100) is None
    ev = m.note_api_error(now=1200)  # 3 hata / 300s
    assert ev is not None and ev.switch == SW_API and ev.freeze
    # pencere dışı: eski hatalar düşer
    m2, _ = _mgr(tmp_path / "b", api_error_freeze_count=3, api_error_window_sec=300)
    m2.note_api_error(now=1000)
    m2.note_api_error(now=2000)   # >300s sonra → eski düşer
    assert m2.note_api_error(now=2001) is None  # yalnız 2 hata penceresinde
    m.close(); m2.close()


def test_drawdown_breaker_freeze_and_alarm(tmp_path):
    m, alarms = _mgr(tmp_path)
    # ALARM: -%25..-%40 arası → bildirim, freeze YOK
    ev = m.evaluate_cycle(equity=70_000, peak=100_000, daily_pnl=0.0, date="2024-01-01")
    assert any(e.switch == SW_DRAWDOWN and not e.freeze and e.level == "WARN" for e in ev)
    assert SW_DRAWDOWN not in m.frozen_switches()
    # FREEZE: <= -%40
    ev2 = m.evaluate_cycle(equity=55_000, peak=100_000, daily_pnl=0.0, date="2024-01-02")
    assert any(e.switch == SW_DRAWDOWN and e.freeze for e in ev2)
    assert SW_DRAWDOWN in m.frozen_switches()
    m.close()


def test_freeze_exit_only_by_user_command(tmp_path):
    m, _ = _mgr(tmp_path, daily_loss_limit_pct=0.08)
    m.evaluate_cycle(100_000, 100_000, -9_000)
    assert m.any_frozen()
    # yeniden değerlendirme FREEZE'i KENDİLİĞİNDEN kaldırmaz
    m.evaluate_cycle(100_000, 100_000, 0.0)
    assert m.any_frozen()
    # yalnızca kullanıcı komutu (clear) kaldırır
    m.clear(SW_DAILY_LOSS)
    assert not m.any_frozen()
    m.close()

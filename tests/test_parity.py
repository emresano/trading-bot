# tests/test_parity.py
"""F5A-6 — günlük parite kontrolü testleri (HARDENING B5)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from execution.paper_broker import PaperBroker
from execution.regime_core_runner import RegimeCoreRunner
from journal.decision_journal import DecisionJournal
from safety.parity import check_parity
from strategy.regime_core import RegimeCoreParams


def _dataset():
    rng = np.random.default_rng(11)
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    trend = np.concatenate([np.linspace(100, 140, 20), np.linspace(140, 100, 20),
                            np.linspace(100, 150, 20)])
    closes = {
        "AAA": pd.Series(trend + rng.normal(0, 1, n), index=idx),
        "BBB": pd.Series(trend * 0.5 + rng.normal(0, 0.5, n), index=idx),
    }
    params = RegimeCoreParams(symbols=["AAA", "BBB"], ma_period=5, band_pct=0.005,
                              confirm_days=2, initial_equity=100_000)
    return closes, params


def _run_live(tmp_path, closes, params) -> DecisionJournal:
    broker = PaperBroker(100_000, params.commission_bps, params.slippage_bps,
                         state_path=tmp_path / "paper.sqlite")
    jr = DecisionJournal(tmp_path / "dj.jsonl", ma_period=params.ma_period,
                         band_pct=params.band_pct, confirm_days=params.confirm_days)
    runner = RegimeCoreRunner(broker, params, state_path=tmp_path / "runner.sqlite",
                              decision_hook=jr.record_decision)
    runner.process_up_to(closes)
    runner.close(); broker.close()
    return jr


def test_parity_matches_after_live_run(tmp_path):
    closes, params = _dataset()
    jr = _run_live(tmp_path, closes, params)
    res = check_parity(closes, params, jr.read_all())
    assert res.matched and not res.red_alarm
    assert len(res.offline_switches) >= 2
    assert res.offline_switches == res.live_switches


def test_parity_detects_corrupted_journal(tmp_path):
    closes, params = _dataset()
    jr = _run_live(tmp_path, closes, params)
    rows = jr.read_all()
    # canlı defteri boz: bir ENTER'ı EXIT yap (kod/veri kayması simülasyonu)
    flipped = False
    for r in rows:
        if r.get("action") == "ENTER" and not flipped:
            r["action"] = "EXIT"
            flipped = True
    assert flipped
    alarms = []
    res = check_parity(closes, params, rows, alarm_hook=alarms.append)
    assert not res.matched and res.red_alarm
    assert len(alarms) == 1 and alarms[0]["level"] == "CRITICAL"


def test_parity_ignores_equity_only_differences(tmp_path):
    """Kapanışa-yakın yürütme equity'de küçük fark yaratsa da parite DECISION
    düzeyindedir — anahtarlamalar özdeşse parite OK (PHASE5_PLAN #3)."""
    closes, params = _dataset()
    jr = _run_live(tmp_path, closes, params)
    rows = jr.read_all()
    # equity alanlarını boz ama aksiyonlara dokunma → parite hâlâ OK olmalı
    for r in rows:
        if "account" in r:
            r["account"]["equity_after"] = 123456.0
    res = check_parity(closes, params, rows)
    assert res.matched

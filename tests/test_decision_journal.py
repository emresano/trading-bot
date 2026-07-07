# tests/test_decision_journal.py
"""F5A-5 — karar günlüğü (JSONL) + maskeleme testleri (HARDENING B4)."""
from __future__ import annotations

import pandas as pd
import pytest

from journal.masking import mask_secret, sanitize
from journal.decision_journal import DecisionJournal
from execution.paper_broker import PaperBroker
from execution.regime_core_runner import RegimeCoreRunner
from strategy.regime_core import RegimeCoreParams


# ------------------------------------------------------------------ maskeleme
def test_mask_api_key_hash_tcno():
    s = "APIKEY=API-ABCD1234 hash=deadbeef" + "0" * 40 + " tc=12345678901"
    m = mask_secret(s)
    assert "API-ABCD1234" not in m
    assert "deadbeef" not in m
    assert "12345678901" not in m
    assert "***" in m


def test_mask_known_secret_value():
    m = mask_secret("password is hunter2xyz", known_secrets=["hunter2xyz"])
    assert "hunter2xyz" not in m and "***" in m


def test_sanitize_preserves_numbers_masks_strings():
    obj = {"qty": 125, "price": 100.5, "note": "token=API-SECRET99", "ok": True}
    out = sanitize(obj)
    assert out["qty"] == 125 and out["price"] == 100.5 and out["ok"] is True
    assert "API-SECRET99" not in out["note"]


# ------------------------------------------------------------------ karar günlüğü
def test_record_decision_schema(tmp_path):
    jr = DecisionJournal(tmp_path / "dj.jsonl", ma_period=200, band_pct=0.01, confirm_days=3)

    class Dec:
        date = pd.Timestamp("2024-06-03", tz="UTC")
        composite = 1.23; ma = 1.20; upper_band = 1.212; lower_band = 1.188
        confirm_count = 3; signal_yesterday = True; in_position_before = False
        action = "ENTER"; planned_qty = {"THYAO": 100}; executed_order_ids = ["PAPER-00000001"]
        equity_before = 100_000.0; equity_after = 99_800.0; cash_after = 500.0
        interest_accrued = 0.0; breaker_state = "OK"; drawdown = 0.0; peak_equity = 100_000.0

    jr.record_decision(Dec())
    rows = jr.read_all()
    assert len(rows) == 1
    r = rows[0]
    assert r["type"] == "decision" and r["action"] == "ENTER"
    assert r["regime"]["composite"] == 1.23 and r["regime"]["ma_period"] == 200
    assert r["regime"]["confirm_count"] == 3 and r["regime"]["signal_yesterday"] is True
    assert r["planned_orders"] == {"THYAO": 100}
    assert r["breaker"]["state"] == "OK"


def test_order_event_is_masked(tmp_path):
    jr = DecisionJournal(tmp_path / "dj.jsonl", known_secrets=["myTCpass"])
    jr.record_order_event(
        request={"symbol": "THYAO", "qty": 100, "APIKEY": "API-TOPSECRET1", "pw": "myTCpass"},
        response={"hash": "a" * 40, "status": "FILLED"}, status="FILLED")
    raw = (tmp_path / "dj.jsonl").read_text()
    assert "API-TOPSECRET1" not in raw
    assert "myTCpass" not in raw
    assert "aaaaaaaa" not in raw  # hash maskelendi
    assert "THYAO" in raw and "100" in raw  # işlevsel veri korundu


def test_runner_decision_hook_writes_journal(tmp_path):
    broker = PaperBroker(100_000, 10, 5, state_path=tmp_path / "paper.sqlite")
    jr = DecisionJournal(tmp_path / "dj.jsonl", ma_period=2, band_pct=0.0, confirm_days=1)
    idx = pd.date_range("2024-01-01", periods=7, freq="D", tz="UTC")
    closes = {"THYAO": pd.Series([100, 100, 100, 110, 120, 110, 90.0], index=idx)}
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              initial_equity=100_000)
    runner = RegimeCoreRunner(broker, params, state_path=tmp_path / "runner.sqlite",
                              decision_hook=jr.record_decision)
    runner.process_up_to(closes)
    rows = jr.read_all()
    assert len(rows) == 7
    actions = [r["action"] for r in rows]
    assert "ENTER" in actions and "EXIT" in actions
    runner.close(); broker.close()

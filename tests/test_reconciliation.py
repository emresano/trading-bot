# tests/test_reconciliation.py
"""F5A-3 — mutabakat + durum kurtarma testleri (HARDENING B2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.models import Side
from execution.paper_broker import PaperBroker
from safety.reconciliation import (
    LocalLedger, reconcile, startup_reconcile, adopt_broker_state, recon_frozen,
    diff_positions, Mismatch,
)


def test_diff_positions_deterministic():
    d = diff_positions({"THYAO": 10, "GARAN": 5}, {"THYAO": 10, "ASELS": 3})
    # GARAN broker'da 5 yerel 0; ASELS yerel 3 broker 0; sıralı (alfabetik)
    assert d == [Mismatch("ASELS", 0, 3), Mismatch("GARAN", 5, 0)]


def test_reconcile_match_no_freeze(tmp_path):
    ff = tmp_path / "RECON"
    res = reconcile({"THYAO": 10}, {"THYAO": 10}, freeze_file=ff)
    assert res.matched and not res.froze
    assert not ff.exists()


def test_reconcile_mismatch_freezes_and_alarms(tmp_path):
    ff = tmp_path / "RECON"
    alarms = []
    res = reconcile({"THYAO": 10}, {}, freeze_file=ff, alarm_hook=alarms.append)
    assert not res.matched and res.froze
    assert ff.exists()
    assert recon_frozen(ff)
    assert len(alarms) == 1 and alarms[0]["level"] == "CRITICAL"
    assert alarms[0]["category"] == "RECON"


def test_order_sent_then_crash_before_local_write(tmp_path):
    """B2 senaryosu: emir gönderildi (broker fill commit etti) ama runner yerel
    defteri güncellemeden ÇÖKTÜ → yeniden başlatmada broker≠yerel → FREEZE + alarm."""
    broker = PaperBroker(100_000, 10, 5, state_path=tmp_path / "paper.sqlite")
    ledger = LocalLedger(tmp_path / "ledger.sqlite")
    ff = tmp_path / "RECON"

    # başlangıç: ikisi de flat, mutabakat temiz
    assert startup_reconcile(broker, ledger, freeze_file=ff).matched

    broker.update_prices({"THYAO": 100.0})
    broker.submit_market_order("THYAO", Side.BUY, 10)  # broker commit etti
    # ...runner burada ÇÖKTÜ (ledger.sync_from ÇAĞRILMADI)...

    # yeniden başlatma → mutabakat
    alarms = []
    res = startup_reconcile(broker, ledger, freeze_file=ff, alarm_hook=alarms.append)
    assert not res.matched
    assert res.mismatches == [Mismatch("THYAO", 10, 0)]
    assert recon_frozen(ff)
    assert len(alarms) == 1

    # kurtarma: yalnızca KULLANICI komutuyla broker gerçeği benimsenir + freeze temizlenir
    adopt_broker_state(broker, ledger, freeze_file=ff)
    assert not recon_frozen(ff)
    assert startup_reconcile(broker, ledger, freeze_file=ff).matched
    assert ledger.get_positions() == {"THYAO": 10}
    broker.close(); ledger.close()


def test_runner_syncs_ledger_each_cycle(tmp_path):
    """Runner döngü sonunda ledger'ı broker'a eşitler → normal akışta mutabakat temiz."""
    import pandas as pd
    from execution.regime_core_runner import RegimeCoreRunner
    from strategy.regime_core import RegimeCoreParams

    broker = PaperBroker(100_000, 10, 5, state_path=tmp_path / "paper.sqlite")
    ledger = LocalLedger(tmp_path / "ledger.sqlite")
    idx = pd.date_range("2024-01-01", periods=7, freq="D", tz="UTC")
    closes = {"THYAO": pd.Series([100, 100, 100, 110, 120, 110, 90.0], index=idx)}
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              initial_equity=100_000)
    runner = RegimeCoreRunner(broker, params, state_path=tmp_path / "runner.sqlite", ledger=ledger)
    runner.process_up_to(closes)
    # her döngü sonunda eşitlendiği için mutabakat temiz
    assert startup_reconcile(broker, ledger, freeze_file=tmp_path / "RECON").matched
    assert ledger.get_positions() == broker.quantities()
    runner.close(); broker.close(); ledger.close()

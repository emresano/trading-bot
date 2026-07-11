# tests/test_settlement.py
"""T+2 takas gecikmesi (execution katmanı) — RegimeCoreRunner.settlement_days.

Kapsam: yalnız execution/muhasebe katmanı (RegimeCoreRunner + PaperBroker çevresi).
strategy/regime_core.py DOKUNULMADI — bu testler ENTER/EXIT KARAR tarihlerinin
settlement_days'ten ETKİLENMEDİĞİNİ de doğrular (yalnız faiz-tahakkuk zamanlaması +
bilgilendirici uyarı değişir).
"""
from __future__ import annotations

import pandas as pd
import pytest

from execution.paper_broker import PaperBroker
from execution.regime_core_runner import RegimeCoreRunner
from strategy.regime_core import RegimeCoreParams


def _broker(tmp_path, **kw) -> PaperBroker:
    return PaperBroker(initial_equity=100_000, commission_bps=10, slippage_bps=5,
                       state_path=tmp_path / "paper.sqlite", **kw)


def _closes(values: list[float]) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx)


# ENTER@day4, EXIT@day6, sonra flat NAKİT (day7..10) — accrual-gating testleri için.
_LONG_CASH_TAIL = [100, 100, 100, 110, 120, 110, 90, 90, 90, 90, 90]
# ENTER@day4, EXIT@day6, ENTER@day8 (yalnızca 2 işlem günü sonra) — erken-ALIŞ testi için.
_FAST_REENTRY = [100, 100, 100, 110, 120, 110, 90, 140, 140]


def _rate_series(values: list[float], annual_rate: float = 0.10) -> pd.Series:
    idx = _closes(values).index
    return pd.Series(annual_rate, index=idx)


def test_settlement_days_zero_matches_baseline_interest_timing(tmp_path):
    """Varsayılan (settlement_days=0): faiz EXIT'ten SONRAKİ İLK gün başlar (ÖNCEKİ/
    mühürlü davranış — bit-bit korunur, bkz. test_regime_core_prod.py kriter B)."""
    closes = {"THYAO": _closes(_LONG_CASH_TAIL)}
    rate = _rate_series(_LONG_CASH_TAIL)
    b = _broker(tmp_path)
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              commission_bps=10, slippage_bps=5, initial_equity=100_000)
    runner = RegimeCoreRunner(b, params, cash_rate=rate, state_path=tmp_path / "r.sqlite",
                              settlement_days=0)
    decisions = runner.process_up_to(closes)
    by_idx = {i: d for i, d in enumerate(decisions)}
    assert by_idx[6].action == "EXIT"
    assert by_idx[7].action == "HOLD_CASH" and by_idx[7].interest_accrued > 0.0
    assert by_idx[8].interest_accrued > 0.0
    runner.close(); b.close()


def test_settlement_days_gates_interest_start(tmp_path):
    """settlement_days=2: EXIT'ten sonraki İLK işlem günü (t+1) faiz YOK (henüz
    settle değil); İKİNCİ gün (t+2) faiz BAŞLAR. Anahtarlama tarihleri (ENTER/EXIT)
    DEĞİŞMEZ — yalnız faiz zamanlaması."""
    closes = {"THYAO": _closes(_LONG_CASH_TAIL)}
    rate = _rate_series(_LONG_CASH_TAIL)
    b = _broker(tmp_path)
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              commission_bps=10, slippage_bps=5, initial_equity=100_000)
    runner = RegimeCoreRunner(b, params, cash_rate=rate, state_path=tmp_path / "r.sqlite",
                              settlement_days=2)
    decisions = runner.process_up_to(closes)
    by_idx = {i: d for i, d in enumerate(decisions)}
    assert by_idx[6].action == "EXIT"                          # karar DEĞİŞMEDİ
    assert by_idx[7].interest_accrued == 0.0                    # t+1: henüz settle değil
    assert by_idx[8].interest_accrued > 0.0                     # t+2: settle oldu, faiz başladı
    assert by_idx[9].interest_accrued > 0.0                     # sonrası normal devam
    runner.close(); b.close()


def test_settlement_note_when_enter_before_settled(tmp_path):
    """ENTER, en son EXIT'ten yalnızca 2 işlem günü sonra geliyor ama settlement_days=3
    isteniyor → 2 < 3, henüz settle değil → settlement_note DOLU. Karar (ENTER olması,
    hangi güne düştüğü) ETKİLENMEZ — yalnız bilgilendirici not eklenir."""
    closes = {"THYAO": _closes(_FAST_REENTRY)}
    b = _broker(tmp_path)
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              commission_bps=10, slippage_bps=5, initial_equity=100_000)
    runner = RegimeCoreRunner(b, params, state_path=tmp_path / "r.sqlite", settlement_days=3)
    decisions = runner.process_up_to(closes)
    actions = [d.action for d in decisions]
    assert actions[6] == "EXIT" and actions[8] == "ENTER"
    assert decisions[8].settlement_note is not None
    assert "T+3" in decisions[8].settlement_note
    runner.close(); b.close()


def test_settlement_note_absent_when_exactly_settled(tmp_path):
    """Aynı seri, settlement_days=2: ENTER tam 2 işlem günü sonra (sınırda) → 2>=2,
    settle SAYILIR → settlement_note YOK."""
    closes = {"THYAO": _closes(_FAST_REENTRY)}
    b = _broker(tmp_path)
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              commission_bps=10, slippage_bps=5, initial_equity=100_000)
    runner = RegimeCoreRunner(b, params, state_path=tmp_path / "r.sqlite", settlement_days=2)
    decisions = runner.process_up_to(closes)
    assert decisions[8].action == "ENTER"
    assert decisions[8].settlement_note is None
    runner.close(); b.close()


def test_settlement_days_does_not_change_switch_dates(tmp_path):
    """KRİTİK: settlement_days hiçbir ENTER/EXIT KARARINI/tarihini etkilemez (yalnız
    execution/muhasebe katmanı) — settlement_days=0 vs 3 aynı seride BİREBİR aynı
    switch listesini üretir."""
    closes = {"THYAO": _closes(_FAST_REENTRY)}
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              commission_bps=10, slippage_bps=5, initial_equity=100_000)

    def _switches(settlement_days, subdir):
        (tmp_path / subdir).mkdir()
        b = _broker(tmp_path / subdir)
        runner = RegimeCoreRunner(b, params, state_path=tmp_path / subdir / "r.sqlite",
                                  settlement_days=settlement_days)
        decs = runner.process_up_to(closes)
        out = [(d.date, d.action) for d in decs if d.action in ("ENTER", "EXIT")]
        runner.close(); b.close()
        return out

    assert _switches(0, "a") == _switches(3, "b")


def test_persists_across_restart(tmp_path):
    """cash_days_since_exit restart'tan SAĞ ÇIKAR (SQLite state) — watchdog/crash
    sonrası settlement penceresi baştan sayılmaz."""
    closes = {"THYAO": _closes(_LONG_CASH_TAIL)}
    rate = _rate_series(_LONG_CASH_TAIL)
    params = RegimeCoreParams(symbols=["THYAO"], ma_period=2, band_pct=0.0, confirm_days=1,
                              commission_bps=10, slippage_bps=5, initial_equity=100_000)
    b = _broker(tmp_path)
    state_path = tmp_path / "r.sqlite"
    runner = RegimeCoreRunner(b, params, cash_rate=rate, state_path=state_path, settlement_days=2)
    # yalnızca day0..7'ye kadar işle (EXIT@6, t+1@7 henüz settle değil)
    d1 = runner.process_up_to(closes, today=closes["THYAO"].index[7])
    assert d1[-1].interest_accrued == 0.0
    runner.close(); b.close()

    # YENİDEN AÇ (aynı state_path) — restart emsali
    b2 = _broker(tmp_path)
    b2.update_prices({"THYAO": 90.0})
    runner2 = RegimeCoreRunner(b2, params, cash_rate=rate, state_path=state_path, settlement_days=2)
    d2 = runner2.process_up_to(closes)   # kalan day8..10
    assert d2[0].interest_accrued > 0.0  # day8 = t+2, restart sonrası da doğru gated
    runner2.close(); b2.close()

# tests/test_regime_core_prod.py
"""D1 üretim portu testleri (P1) — mühürlü kriterler A/B/D + breaker kuru-test.

Kriter A: üretim yolu S1b'nin 67 anahtarlama tarihini BİREBİR üretir.
Kriter B: CAGR ±0.5 / maxDD ±1.0 / Sharpe ±0.05 (fiilen bit-bit eşit).
Kriter D: breaker tarihsel FREEZE tetiklenme 0 + kuru-test yeşil.
(Kriter C — v7.1-golden — tests/test_golden_bist.py'de.)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from strategy.family_registry import build_family, family_id_from_config
from strategy.regime_core import (
    BreakerState,
    RegimeCoreBreaker,
    RegimeCoreParams,
    plan_enter,
    plan_exit,
    run_regime_core_prod,
)

S1B_DIR = Path("runtime/regime_core_s1b")
SNAPSHOT = Path("data/snapshots/2026-07-06")
AUX_RATE = Path("data/snapshots/aux/2026-07-07/TRY_ON_RATE.parquet")
SYMBOLS = ["THYAO", "GARAN", "ASELS", "AKBNK", "KCHOL", "SAHOL",
           "EREGL", "TUPRS", "TCELL", "TOASO", "SISE", "ARCLK"]


def _load_prod_result():
    from data.cleaning import load_and_clean_universe
    cleaned, _ = load_and_clean_universe(
        SYMBOLS, lambda s: pd.read_parquet(SNAPSHOT / f"{s}.parquet").loc["2005-01-01":])
    closes = {s: df["close"] for s, df in cleaned.items()}
    cash_rate = pd.read_parquet(AUX_RATE)["rate_pct"] / 100.0
    params = RegimeCoreParams(symbols=SYMBOLS, ma_period=200, band_pct=0.01, confirm_days=3,
                              commission_bps=10.0, slippage_bps=5.0, initial_equity=100_000.0)
    breaker = RegimeCoreBreaker(freeze_file=Path("/tmp/_rc_prod_test_freeze_nonexist"))
    return run_regime_core_prod(closes, params, cash_rate=cash_rate, breaker=breaker)


# ---------------------------------------------------------------- Kriter A + B + D (tarihsel)
@pytest.mark.skipif(not (S1B_DIR / "switches_main.csv").exists() or not SNAPSHOT.exists(),
                    reason="S1b referansı veya snapshot yok")
def test_criterion_A_switch_dates_identical_to_s1b():
    res = _load_prod_result()
    prod = [(pd.Timestamp(s.date), s.action) for s in res.switches]
    s1b = pd.read_csv(S1B_DIR / "switches_main.csv")
    ref = [(pd.Timestamp(d), a) for d, a in zip(s1b["date"], s1b["action"])]
    assert len(prod) == 67
    assert prod == ref, "Üretim anahtarlama tarihleri S1b'den SAPTI (kriter A ihlali)"


@pytest.mark.skipif(not (S1B_DIR / "summary.json").exists() or not SNAPSHOT.exists(),
                    reason="S1b referansı veya snapshot yok")
def test_criterion_B_metrics_within_tolerance():
    import json
    from backtest.run_family import compute_summary
    res = _load_prod_result()
    prod = compute_summary(res.equity_curve)
    s1b = json.loads((S1B_DIR / "summary.json").read_text())["main_run"]["summary"]
    assert abs(prod["cagr"] - s1b["cagr"]) * 100 <= 0.5
    assert abs(prod["max_drawdown"] - s1b["max_drawdown"]) * 100 <= 1.0
    assert abs(prod["sharpe"] - s1b["sharpe"]) <= 0.05
    # fiilen bit-bit (tam-lot spike'ta zaten modellenmiş → sapma 0)
    assert prod["cagr"] == pytest.approx(s1b["cagr"], abs=1e-9)


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="snapshot yok")
def test_criterion_D_no_historical_freeze_trip():
    res = _load_prod_result()
    assert res.freeze_trips == 0, "Tarihsel FREEZE tetiklendi — davranış değişti (kriter D ihlali)"
    assert res.enters_blocked_by_freeze == 0
    # ALARM bilgilendirici olarak tetiklenebilir (maxDD -%28.4 > -%25) — davranış değiştirmez
    assert res.alarm_trips >= 1


# ---------------------------------------------------------------- Breaker kuru-test (sentetik)
def test_breaker_thresholds():
    brk = RegimeCoreBreaker(alarm_pct=0.25, freeze_pct=0.40, freeze_file=None)
    assert brk.evaluate("d", 100.0, 100.0) == BreakerState.OK       # 0%
    assert brk.evaluate("d", 80.0, 100.0) == BreakerState.OK        # -20% < 25 → OK
    assert brk.evaluate("d", 74.0, 100.0) == BreakerState.ALARM     # -26%
    assert brk.evaluate("d", 59.0, 100.0) == BreakerState.FREEZE    # -41%


def test_breaker_alarm_hook_latches_once():
    fired = []
    brk = RegimeCoreBreaker(alarm_pct=0.25, freeze_pct=0.40, freeze_file=None, alarm_hook=fired.append)
    brk.evaluate("d1", 70.0, 100.0)   # -30% → ALARM, hook fires
    brk.evaluate("d2", 71.0, 100.0)   # hâlâ ALARM zone → latch, hook fire ETMEZ
    assert len(fired) == 1
    # peak'e yaklaşınca latch reset, yeni düşüş yeni bildirim
    brk.evaluate("d3", 95.0, 100.0)   # -5% < 12.5% → reset
    brk.evaluate("d4", 70.0, 100.0)   # -30% → yeni ALARM
    assert len(fired) == 2


def test_breaker_freeze_writes_file_and_blocks(tmp_path):
    freeze_file = tmp_path / "FREEZE_TRIPPED"
    brk = RegimeCoreBreaker(alarm_pct=0.25, freeze_pct=0.40, freeze_file=freeze_file)
    assert brk.freeze_active() is False
    state = brk.evaluate("d", 55.0, 100.0)  # -45% → FREEZE
    assert state == BreakerState.FREEZE
    assert freeze_file.exists()
    assert brk.freeze_active() is True
    # reset yalnız kullanıcı: dosya silinene dek aktif kalır
    freeze_file.unlink()
    assert brk.freeze_active() is False


def test_breaker_freeze_blocks_enter_integration(tmp_path):
    """Sentetik seri: rejim ON olur (ENTER), sonra >%40 çöker (FREEZE), sonra
    yeni bir ENTER sinyali gelir ama FREEZE bloklar (çıkış serbest kalır)."""
    # composite'i doğrudan kontrol etmek için tek "sembol" (kompozit = o sembol).
    idx = pd.date_range("2020-01-01", periods=700, freq="D", tz="UTC")
    # düz → yükseliş (ENTER) → TEK-BAR uçurum (-%57, çıkış t+1 olduğundan pozisyondayken
    # MTM drawdown >%40 → FREEZE) → güçlü toparlanma (yeni ENTER denemesi, FREEZE bloklar).
    base = np.concatenate([
        np.full(205, 100.0),                # düz (MA otursun)
        np.linspace(100, 140, 100),         # yükseliş → ENTER
        np.array([60.0]),                   # TEK-BAR uçurum: -%57 (pozisyondayken FREEZE)
        np.linspace(62, 135, 394),          # toparlanma → yeni ENTER denemesi
    ])
    closes = {"X": pd.Series(base, index=idx)}
    params = RegimeCoreParams(symbols=["X"], ma_period=200, band_pct=0.01, confirm_days=3,
                              commission_bps=10.0, slippage_bps=5.0, initial_equity=100_000.0)
    freeze_file = tmp_path / "FREEZE"
    brk = RegimeCoreBreaker(alarm_pct=0.25, freeze_pct=0.40, freeze_file=freeze_file)
    res = run_regime_core_prod(closes, params, breaker=brk)
    assert res.freeze_trips >= 1, "sentetik >%40 çöküşte FREEZE tetiklenmeliydi"
    assert res.enters_blocked_by_freeze >= 1, "FREEZE sonrası yeni ENTER bloklanmalıydı"


# ---------------------------------------------------------------- saf boyutlama (tam-lot)
def test_plan_enter_whole_lot_and_residual_cash():
    prices = {"A": 100.0, "B": 33.33}
    qty, cash_after = plan_enter(10_000.0, prices, ["A", "B"], commission_bps=10.0, slippage_bps=5.0)
    # her sembole 5000 bütçe; tam-lot → kesirli yok
    assert all(isinstance(q, int) for q in qty.values())
    assert qty["A"] == int(np.floor(5000.0 / (100.0 * 1.0005 * 1.001)))
    # artık nakit >= 0 (negatif cash yasak)
    assert cash_after >= 0


def test_plan_enter_skips_symbol_without_price():
    qty, _ = plan_enter(10_000.0, {"A": 100.0}, ["A", "B"], 10.0, 5.0)
    assert "B" not in qty and "A" in qty


def test_plan_exit_proceeds():
    proceeds = plan_exit({"A": 10}, {"A": 100.0}, commission_bps=10.0, slippage_bps=5.0)
    assert proceeds == pytest.approx(100.0 * (1 - 0.0005) * 10 * (1 - 0.001))


def test_cash_rate_none_no_accrual():
    """cash_rate=None → nakit dönemde tahakkuk yok (S1 davranışı)."""
    idx = pd.date_range("2020-01-01", periods=300, freq="D", tz="UTC")
    closes = {"X": pd.Series(np.linspace(100, 100, 300), index=idx)}  # düz → hiç ENTER yok
    params = RegimeCoreParams(symbols=["X"], initial_equity=100_000.0)
    res = run_regime_core_prod(closes, params, cash_rate=None)
    assert res.equity_curve.iloc[-1] == pytest.approx(100_000.0)  # nakit sabit


# ---------------------------------------------------------------- family registry
def test_family_registry_build():
    assert build_family("ten_gate").family_id == "ten_gate"
    assert build_family("regime_core").family_id == "regime_core"


def test_family_registry_unknown_raises():
    with pytest.raises(ValueError, match="Bilinmeyen strateji ailesi"):
        build_family("nonexistent")


def test_family_id_from_config():
    assert family_id_from_config({"strategy_family": "regime_core"}) == "regime_core"
    assert family_id_from_config({}) == "ten_gate"          # config.yaml → varsayılan
    with pytest.raises(ValueError):
        family_id_from_config({"strategy_family": "bogus"})

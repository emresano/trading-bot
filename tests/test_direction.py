# tests/test_direction.py
"""Yön ve boyutlama testleri (EXPANSION.md Bölüm 15.3).

E2 short MEKANİĞİ (motor yeteneği) — short gate seti tasarımı kapsam dışı.
Ayna simetrisi, sayısal boyutlama (SHORT/FX), quote-ccy dönüşümü, marjin kırpma,
stop-önceliği (SHORT), settlement, PDT.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from core.models import AccountState, Direction, RejectReason
from risk.account_rules import available_cash, pdt_blocks_entry, settlement_allows
from risk.direction import (
    compute_stop_target,
    intrabar_fill,
    per_unit_risk,
    realized_pnl,
    reward_risk,
    size_position,
    unrealized_pnl,
)


# ---------------------------------------------------------------- ayna simetrisi
def test_mirror_symmetry_long_vs_short():
    """Fiyat serisi P ve aynası (2·P0−P) üzerinde LONG ve SHORT mekaniği:
    aynı trade sayısı, aynı R dizisi, aynı |PnL|. Deterministik mekanik koşu."""
    p0 = 100.0
    # basit dalga: giriş, sonra hedef/stopa gidiş
    P = np.array([100.0, 101.0, 103.0, 106.0, 104.0, 101.0, 98.0, 102.0, 107.0])
    mirror = 2 * p0 - P  # ayna

    atr, k = 2.0, 1.5
    slip = 5.0

    def run(series, direction):
        entry = float(series[0])
        # nearest_level yok → 2R fallback (her iki yönde simetrik)
        stop, target = compute_stop_target(entry, atr, k, direction, nearest_level=None)
        rr = reward_risk(entry, stop, target, direction)
        qty = 100.0
        # bar bar intrabar fill (giriş barından sonrası)
        for px in series[1:]:
            # tek fiyatlı bar (high=low=px) — simetrik test için yeterli
            fill = intrabar_fill(px, px, stop, target, direction, slip)
            if fill is not None:
                fill_price, reason = fill
                pnl = realized_pnl(entry, fill_price, qty, direction)
                r = pnl / (qty * per_unit_risk(entry, stop))
                return {"rr": rr, "reason": reason, "pnl": pnl, "r": r}
        return {"rr": rr, "reason": None, "pnl": 0.0, "r": 0.0}

    long_res = run(P, Direction.LONG)
    short_res = run(mirror, Direction.SHORT)

    assert long_res["reason"] == short_res["reason"]           # aynı olay (STOP/TARGET)
    assert long_res["rr"] == pytest.approx(short_res["rr"])     # aynı R:R
    assert abs(long_res["pnl"]) == pytest.approx(abs(short_res["pnl"]))  # |PnL| eşit
    assert long_res["r"] == pytest.approx(short_res["r"])       # aynı R çarpanı


def test_stop_target_mirror_geometry():
    entry, atr, k = 100.0, 2.0, 1.5
    ls, lt = compute_stop_target(entry, atr, k, Direction.LONG)
    ss, st = compute_stop_target(entry, atr, k, Direction.SHORT)
    assert ls == 100.0 - 1.5 * 2.0 and ss == 100.0 + 1.5 * 2.0
    # hedefler simetrik: LONG entry üstünde, SHORT altında, aynı mesafe
    assert (lt - entry) == pytest.approx(entry - st)


# ---------------------------------------------------------------- boyutlama (SHORT/FX)
def test_short_fx_sizing_numeric():
    """Bölüm 15.3: equity=10.000 USD, risk %0.75 → 75 USD; EURUSD SHORT
    entry=1.1000 stop=1.1080 → per_unit_risk≈0.0080.

    DÜRÜST NOT: spec 9375 der (tam aritmetik varsayımı). IEEE754 double'da
    1.1000-1.1080 = 0.008000000000000007 → 75/pur = 9374.99… → floor 9374.
    Bir birimlik fark saf float temsilinden gelir (mekanik doğru). leverage 5
    tavanı ~45.454 → bağlamaz."""
    qty, reject = size_position(
        10_000.0, 0.0075, 1.1000, 1.1080, direction=Direction.SHORT, qty_step=1.0,
        max_position_notional_pct=10.0, commission_bps=0.0, cash=10_000.0,
        max_leverage=5.0, free_margin=10_000.0,
    )
    assert reject is None
    assert qty == 9374.0


def test_quote_ccy_conversion_usdjpy():
    """USDJPY SHORT entry=150.00 stop=151.20 → per_unit_risk=1.20 JPY = 0.0080 USD
    (÷150) → EURUSD ile AYNI risk büyüklüğü (farklı parite). Bu parite float'ta
    9375'e yuvarlanır (EURUSD 9374); ikisi de spec'in 0.008 tam değerinin ±1
    birim float komşusu — quote-ccy dönüşümünün doğru çalıştığını gösterir."""
    qty, reject = size_position(
        10_000.0, 0.0075, 150.00, 151.20, direction=Direction.SHORT, qty_step=1.0,
        max_position_notional_pct=1000.0, commission_bps=0.0, cash=10_000.0,
        quote_to_sleeve_rate=150.0, max_leverage=200.0, free_margin=10_000.0,
    )
    assert reject is None
    assert qty == 9375.0
    # her iki parite de ~9.375k → risk-eşdeğerliği (±1 birim float) doğrulanır
    assert abs(qty - 9374.0) <= 1.0


def test_margin_insufficient():
    """free_margin o kadar küçük ki 1 birim (qty_step) bile alınamıyor →
    MARGIN_INSUFFICIENT. (free_margin=0.1 × lev 5 / 1.1 = 0.45 → floor 0 < 1)."""
    qty, reject = size_position(
        10_000.0, 0.0075, 1.1000, 1.1001, direction=Direction.SHORT, qty_step=1.0,
        max_position_notional_pct=1000.0, commission_bps=0.0, cash=0.1,
        max_leverage=5.0, free_margin=0.1,
    )
    assert reject == RejectReason.MARGIN_INSUFFICIENT


def test_long_sizing_matches_bist_reference():
    """LONG (BIST) referans: equity=100.000, risk %0.75, entry=100, stop=94 →
    750/6=125; notional tavanı %25 → 25.000/100=250 bağlamaz → 125 (Bölüm 9.3 örneği)."""
    qty, reject = size_position(
        100_000.0, 0.0075, 100.0, 94.0, direction=Direction.LONG, qty_step=1.0,
        max_position_notional_pct=0.25, commission_bps=10.0, cash=100_000.0,
    )
    assert reject is None
    assert qty == 125.0


# ---------------------------------------------------------------- stop-önceliği SHORT
def test_short_stop_priority_same_bar():
    """SHORT: aynı barda hem stop (üstte) hem target (altta) menzilde → STOP fill,
    slippage aleyhte (stop'un ÜSTÜNDE)."""
    stop, target, slip = 110.0, 90.0, 5.0
    fill = intrabar_fill(bar_high=111.0, bar_low=89.0, stop=stop, target=target,
                         direction=Direction.SHORT, slippage_bps=slip)
    assert fill is not None
    fill_price, reason = fill
    assert reason == "STOP"
    assert fill_price == stop * (1 + slip / 1e4)  # aleyhte: üstte dolar
    assert fill_price > stop


def test_long_stop_priority_unchanged():
    stop, target, slip = 94.0, 112.0, 5.0
    fill = intrabar_fill(bar_high=113.0, bar_low=93.0, stop=stop, target=target,
                         direction=Direction.LONG, slippage_bps=slip)
    fill_price, reason = fill
    assert reason == "STOP"
    assert fill_price == stop * (1 - slip / 1e4)


# ---------------------------------------------------------------- MTM
def test_unrealized_pnl_signs():
    assert unrealized_pnl(100.0, 105.0, 10, Direction.LONG) == 50.0
    assert unrealized_pnl(100.0, 105.0, 10, Direction.SHORT) == -50.0
    assert unrealized_pnl(100.0, 95.0, 10, Direction.SHORT) == 50.0


# ---------------------------------------------------------------- settlement
def test_settlement_bist_agnostic():
    acct = AccountState(100_000, 100_000, [], 100_000, 0, 0)  # settled_cash=-1 default
    assert available_cash(acct) == 100_000
    ok, reject = settlement_allows(acct, 999_999)
    assert ok and reject is None


def test_settlement_cash_unavailable():
    acct = AccountState(3000, 3000, [], 3000, 0, 0, currency="USD", settled_cash=1000.0)
    assert available_cash(acct) == 1000.0
    ok, reject = settlement_allows(acct, 1500.0)
    assert not ok and reject == RejectReason.SETTLEMENT_CASH_UNAVAILABLE


# ---------------------------------------------------------------- PDT
def test_pdt_blocks_margin_under_25k_with_3_daytrades():
    assert pdt_blocks_entry(24_000, 3, "margin") is True
    assert pdt_blocks_entry(24_000, 2, "margin") is False
    assert pdt_blocks_entry(26_000, 5, "margin") is False   # equity >= 25k → serbest
    assert pdt_blocks_entry(24_000, 5, "cash") is False      # cash hesap → PDT yok

# tests/test_costs.py
"""CostModel katmanı testleri (EXPANSION.md Bölüm 7).

BIST: satır-içi motor formülleriyle BİREBİR sayısal eşdeğerlik (göç kanıtı).
US: SEC+TAF yalnızca satışta, TAF tavanı. FX: yarım spread + swap + Çarşamba 3×.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from core.models import Direction, Side
from costs.base import CostModel
from costs.bist import BistCostModel
from costs.fx import FxCostModel
from costs.us_equities import UsEquitiesCostModel


@dataclass
class _Pos:
    quantity: float
    avg_price: float
    direction: Direction = Direction.LONG


# ---------------------------------------------------------------- BIST eşdeğerlik
def test_bist_matches_inline_engine_formulas():
    """costs/bist.py, backtest/engine.py'nin satır-içi ifadeleriyle bit-bit aynı."""
    commission_bps, slippage_bps = 10.0, 5.0
    m = BistCostModel(commission_bps, slippage_bps)
    open_price, qty, stop, target = 12.3456, 1000, 11.9, 13.5

    # entry fill (BUY): inline == open*(1+slip/1e4); commission == fill*qty*comm/1e4
    inline_entry_fill = open_price * (1 + slippage_bps / 1e4)
    assert m.slippage_price(open_price, Side.BUY) == inline_entry_fill
    assert m.entry_costs(inline_entry_fill, qty) == inline_entry_fill * qty * commission_bps / 1e4

    # signal-exit / stop fill (SELL): inline == price*(1-slip/1e4)
    inline_exit_fill = open_price * (1 - slippage_bps / 1e4)
    assert m.slippage_price(open_price, Side.SELL) == inline_exit_fill
    inline_stop_fill = stop * (1 - slippage_bps / 1e4)
    assert m.slippage_price(stop, Side.SELL) == inline_stop_fill

    # exit commission identical
    assert m.exit_costs(inline_exit_fill, qty) == inline_exit_fill * qty * commission_bps / 1e4


def test_bist_daily_carry_zero():
    m = BistCostModel(10, 5)
    assert m.daily_carry(_Pos(100, 10.0), date(2024, 6, 12)) == 0.0


# ---------------------------------------------------------------- US SEC/TAF
def test_us_sec_taf_only_on_sell():
    m = UsEquitiesCostModel(commission_bps=0.0, sec_fee_bps=0.28,
                            taf_per_share=0.000166, slippage_bps=5.0)
    price, qty = 100.0, 500
    assert m.entry_costs(price, qty) == 0.0  # alışta SEC/TAF yok, komisyon 0
    expected_sec = price * qty * 0.28 / 1e4
    expected_taf = 0.000166 * qty
    assert m.exit_costs(price, qty) == pytest.approx(expected_sec + expected_taf)


def test_us_taf_cap():
    m = UsEquitiesCostModel(taf_per_share=0.01, taf_max_per_sale=8.30, sec_fee_bps=0.0, commission_bps=0.0)
    # 100000 hisse × 0.01 = 1000 → tavan 8.30 bağlar
    assert m.exit_costs(50.0, 100000) == pytest.approx(8.30)


def test_us_daily_carry_zero():
    m = UsEquitiesCostModel()
    assert m.daily_carry(_Pos(10, 100.0), date(2024, 6, 12)) == 0.0


# ---------------------------------------------------------------- FX
def test_fx_half_spread_slippage():
    m = FxCostModel("EUR_USD", pip_size=0.0001, spread_pips=0.9, slippage_pips=0.3,
                    swap_long_annual_pct=-2.0, swap_short_annual_pct=-0.5)
    ref = 1.10000
    adj = (0.9 / 2 + 0.3) * 0.0001
    assert m.slippage_price(ref, Side.BUY) == pytest.approx(ref + adj)
    assert m.slippage_price(ref, Side.SELL) == pytest.approx(ref - adj)


def test_fx_swap_carry_sign_and_direction():
    m = FxCostModel("EUR_USD", pip_size=0.0001, spread_pips=0.9, slippage_pips=0.3,
                    swap_long_annual_pct=-2.0, swap_short_annual_pct=-0.5,
                    triple_swap_wednesday=True)
    pos_long = _Pos(100000, 1.10, Direction.LONG)
    notional = 100000 * 1.10
    thursday = date(2024, 6, 13)
    expected_long = notional * (-2.0 / 100) / 365
    assert m.daily_carry(pos_long, thursday) == pytest.approx(expected_long)
    assert m.daily_carry(pos_long, thursday) < 0  # negatif oran → maliyet (cash düşer)

    pos_short = _Pos(100000, 1.10, Direction.SHORT)
    expected_short = notional * (-0.5 / 100) / 365
    assert m.daily_carry(pos_short, thursday) == pytest.approx(expected_short)


def test_fx_triple_swap_wednesday():
    m = FxCostModel("EUR_USD", pip_size=0.0001, spread_pips=0.9, slippage_pips=0.3,
                    swap_long_annual_pct=-2.0, swap_short_annual_pct=-0.5,
                    triple_swap_wednesday=True)
    pos = _Pos(100000, 1.10, Direction.LONG)
    wednesday = date(2024, 6, 12)
    thursday = date(2024, 6, 13)
    assert m.daily_carry(pos, wednesday) == pytest.approx(3 * m.daily_carry(pos, thursday))


def test_all_models_satisfy_abc_shape():
    """ABC sözleşmesi: her model 4 metodu sağlar (isinstance kaydı gerekmez —
    yapısal uyum; motor duck-typing kullanır)."""
    for m in (BistCostModel(10, 5), UsEquitiesCostModel(), FxCostModel(
            "EUR_USD", 0.0001, 0.9, 0.3, -2.0, -0.5)):
        assert hasattr(m, "entry_costs") and hasattr(m, "exit_costs")
        assert hasattr(m, "slippage_price") and hasattr(m, "daily_carry")
        assert m.daily_carry.__call__ is not None

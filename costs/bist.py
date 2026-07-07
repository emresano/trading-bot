# costs/bist.py
"""BIST maliyet modeli (EXPANSION.md Bölüm 7.2) — mevcut komisyon+slippage
mantığının davranış-nötr göçü.

Sayısal davranış, backtest/engine.py'deki satır-içi ifadelerle BİREBİR aynı
olacak şekilde tanımlanmıştır (aynı işlem sırası, aynı ifadeler):
  - slippage_price: open*(1 ± slippage_bps/1e4)  (BUY +, SELL -)
  - entry/exit_costs: fill_price*qty*commission_bps/1e4
  - daily_carry: 0.0 (hisse taşıma maliyeti yok)
Bu eşdeğerlik tests/test_costs.py'de satır-içi formüllere karşı doğrulanır ve
tests/test_golden_bist.py çapası tüm BIST çıktısını korur.
"""
from __future__ import annotations

from core.models import Side


class BistCostModel:
    model_id = "bist"

    def __init__(self, commission_bps: float, slippage_bps: float):
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps

    def entry_costs(self, price: float, qty: float) -> float:
        return price * qty * self.commission_bps / 1e4

    def exit_costs(self, price: float, qty: float) -> float:
        return price * qty * self.commission_bps / 1e4

    def slippage_price(self, ref_price: float, side: Side) -> float:
        if side == Side.BUY:
            return ref_price * (1 + self.slippage_bps / 1e4)
        return ref_price * (1 - self.slippage_bps / 1e4)

    # daily_carry: ABC varsayılanı 0.0 — hisse taşıma maliyeti yok (override yok).
    def daily_carry(self, pos, d) -> float:
        return 0.0


def bist_cost_model_from_config(cfg) -> BistCostModel:
    """config.costs bloğundan (commission_bps, slippage_bps) BistCostModel üretir."""
    return BistCostModel(commission_bps=cfg.costs.commission_bps,
                         slippage_bps=cfg.costs.slippage_bps)

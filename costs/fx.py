# costs/fx.py
"""FX maliyet modeli (EXPANSION.md Bölüm 7.2) — enstrüman-başına bir model.

- Yarım spread (giriş + çıkış) + slippage, fill fiyatına pip cinsinden uygulanır.
- swap (taşıma): daily_carry = notional × (yıllık_oran_yüzde/100) / 365; Çarşamba
  (triple_swap_wednesday) 3× tahakkuk. Tarihsel swap serisi pratikte edinilemez →
  oranlar MUHAFAZAKÂR sabitlerdir (pozisyon aleyhine); her FX backtest raporuna
  "swap: sabit muhafazakâr tahmin" notu ZORUNLU (Bölüm 7.2 — E4 raporu).

İşaret: swap_*_annual_pct negatifse (örn. -2.0) daily_carry negatif → cash düşer
(taşıma maliyeti). LONG swap_long_annual_pct, SHORT swap_short_annual_pct kullanır.
"""
from __future__ import annotations

from datetime import date

from core.models import Direction, Side

WEDNESDAY = 2  # date.weekday(): Pazartesi=0 ... Çarşamba=2


class FxCostModel:
    model_id = "fx"

    def __init__(self, symbol: str, pip_size: float, spread_pips: float,
                 slippage_pips: float, swap_long_annual_pct: float,
                 swap_short_annual_pct: float, triple_swap_wednesday: bool = True):
        self.symbol = symbol
        self.pip_size = pip_size
        self.spread_pips = spread_pips
        self.slippage_pips = slippage_pips
        self.swap_long_annual_pct = swap_long_annual_pct
        self.swap_short_annual_pct = swap_short_annual_pct
        self.triple_swap_wednesday = triple_swap_wednesday

    def entry_costs(self, price: float, qty: float) -> float:
        # FX'te komisyon yok; maliyet spread/slippage'ta (fill fiyatında) yansır.
        return 0.0

    def exit_costs(self, price: float, qty: float) -> float:
        return 0.0

    def slippage_price(self, ref_price: float, side: Side) -> float:
        adj = (self.spread_pips / 2.0 + self.slippage_pips) * self.pip_size
        if side == Side.BUY:
            return ref_price + adj
        return ref_price - adj

    def daily_carry(self, pos, d: date) -> float:
        notional = pos.quantity * pos.avg_price
        rate_pct = (self.swap_long_annual_pct if pos.direction == Direction.LONG
                    else self.swap_short_annual_pct)
        carry = notional * (rate_pct / 100.0) / 365.0
        if self.triple_swap_wednesday and d.weekday() == WEDNESDAY:
            carry *= 3.0
        return carry


def fx_cost_models_from_config(fx_cfg: dict) -> dict[str, FxCostModel]:
    """config/markets/fx.yaml'ın instruments + costs bloğundan enstrüman→model sözlüğü."""
    costs = fx_cfg.get("costs", {})
    slippage_pips = costs.get("slippage_pips", 0.3)
    triple = costs.get("triple_swap_wednesday", True)
    models: dict[str, FxCostModel] = {}
    for ins in fx_cfg.get("instruments", []):
        models[ins["symbol"]] = FxCostModel(
            symbol=ins["symbol"], pip_size=ins["pip_size"], spread_pips=ins["spread_pips"],
            slippage_pips=slippage_pips,
            swap_long_annual_pct=ins.get("swap_long_annual_pct", 0.0),
            swap_short_annual_pct=ins.get("swap_short_annual_pct", 0.0),
            triple_swap_wednesday=triple,
        )
    return models

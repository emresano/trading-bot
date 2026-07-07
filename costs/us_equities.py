# costs/us_equities.py
"""ABD hisse maliyet modeli (EXPANSION.md Bölüm 7.2).

- commission_bps (varsayılan 0 — çoğu ABD broker'ı komisyonsuz).
- SATIŞTA: SEC fee (sec_fee_bps) + TAF (taf_per_share, tavanlı). Güncel oranlar
  E3'te resmî kaynakla doğrulanır (Bölüm 17 #3) — buradaki değerler config'ten.
- slippage_bps.
- daily_carry: 0.0 (nakit hesap; marjin faizi MVP kapsamı dışı).
"""
from __future__ import annotations

from core.models import Side

# FINRA TAF üst sınırı (satış başına) — güncel değeri E3'te doğrulanır.
TAF_MAX_PER_SALE = 8.30


class UsEquitiesCostModel:
    model_id = "us_equities"

    def __init__(self, commission_bps: float = 0.0, sec_fee_bps: float = 0.28,
                 taf_per_share: float = 0.000166, slippage_bps: float = 5.0,
                 taf_max_per_sale: float = TAF_MAX_PER_SALE):
        self.commission_bps = commission_bps
        self.sec_fee_bps = sec_fee_bps
        self.taf_per_share = taf_per_share
        self.slippage_bps = slippage_bps
        self.taf_max_per_sale = taf_max_per_sale

    def entry_costs(self, price: float, qty: float) -> float:
        # Alışta yalnızca komisyon (SEC/TAF satışa özgü).
        return price * qty * self.commission_bps / 1e4

    def exit_costs(self, price: float, qty: float) -> float:
        commission = price * qty * self.commission_bps / 1e4
        sec_fee = price * qty * self.sec_fee_bps / 1e4
        taf = min(self.taf_per_share * qty, self.taf_max_per_sale)
        return commission + sec_fee + taf

    def slippage_price(self, ref_price: float, side: Side) -> float:
        if side == Side.BUY:
            return ref_price * (1 + self.slippage_bps / 1e4)
        return ref_price * (1 - self.slippage_bps / 1e4)

    def daily_carry(self, pos, d) -> float:
        return 0.0


def us_cost_model_from_config(costs_cfg: dict) -> UsEquitiesCostModel:
    return UsEquitiesCostModel(
        commission_bps=costs_cfg.get("commission_bps", 0.0),
        sec_fee_bps=costs_cfg.get("sec_fee_bps", 0.28),
        taf_per_share=costs_cfg.get("taf_per_share", 0.000166),
        slippage_bps=costs_cfg.get("slippage_bps", 5.0),
    )

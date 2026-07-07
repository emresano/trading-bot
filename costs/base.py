# costs/base.py
"""CostModel ABC — motorun tek maliyet temas noktası (EXPANSION.md Bölüm 7.1).

Çekirdek (backtest/PaperBroker), piyasa maliyet farklarına yalnızca bu arayüz
üzerinden erişir; `if market == "fx"` tarzı dallanma YASAK (Bölüm 0.3/3.2).

İşaret sözleşmesi:
- entry_costs / exit_costs: POZİTİF = hesaptan çıkan komisyon/harç (maliyet).
- slippage_price: fill fiyatı (BUY'da referansın üstü, SELL'de altı).
- daily_carry: P&L etkisi (İŞARETLİ). Negatif = taşıma maliyeti (cash düşer),
  pozitif = taşıma geliri. Motor `cash += daily_carry(...)` uygular. BIST/US
  override etmez → 0.0 → BIST davranışı bit-bit aynı (golden çapası kanıtlar).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING

from core.models import Side

if TYPE_CHECKING:
    from core.models import Position


class CostModel(ABC):
    model_id: str

    @abstractmethod
    def entry_costs(self, price: float, qty: float) -> float:
        """Giriş komisyon/harçları (pozitif = maliyet)."""

    @abstractmethod
    def exit_costs(self, price: float, qty: float) -> float:
        """Çıkış komisyon/harçları (pozitif = maliyet)."""

    @abstractmethod
    def slippage_price(self, ref_price: float, side: Side) -> float:
        """Slippage (ve varsa yarım spread) uygulanmış fill fiyatı."""

    def daily_carry(self, pos: "Position", d: date) -> float:
        """Bir işlem günü taşıma P&L'i (işaretli). Varsayılan 0 — YALNIZCA fx override eder."""
        return 0.0

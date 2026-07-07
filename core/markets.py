# core/markets.py
"""MarketSpec + MARKET_REGISTRY (EXPANSION.md Bölüm 4.2).

Çekirdek (sinyal/risk/backtest), piyasa özelliğine YALNIZCA MarketSpec üzerinden
erişir. `if market == "fx"` tarzı dallanma çekirdekte YASAKTIR (Bölüm 0.3/3.2) —
piyasa farkları yalnızca üç yerde soğurulur: MarketSpec (metadata), CostModel
(maliyet), gate profili (hangi gate/eşik). MarketSpec alan eklemeye açık; mevcut
alan anlamı değiştirilemez.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MarketSpec:
    market_id: str                  # "bist" | "us" | "fx"
    calendar_id: str                # "XIST" | "XNYS" | "FX_24_5"
    currency: str
    direction_mode: str             # "long_only" | "two_sided"
    settlement_days: int            # BIST=2, US=1, FX=0
    qty_step: float                 # hisse=1; FX=1 unit (broker min'i E3'te doğrulanır)
    price_decimals: int
    cost_model_id: str              # costs/ registry anahtarı
    gate_profile_id: str            # config/markets/<id>.yaml profili
    data_adapter_id: str
    eval_after_close_min: int = 10
    pip_size: Optional[float] = None        # FX; enstrüman bazında config override
    max_leverage: Optional[float] = None    # FX; muhafazakâr varsayılan 5.0 (SPK üst sınır 10.0)
    account_type: str = "cash"              # us: cash | margin (Bölüm 9.3/9.4)

    def __post_init__(self) -> None:
        if self.direction_mode not in ("long_only", "two_sided"):
            raise ValueError(
                f"MarketSpec[{self.market_id}]: direction_mode geçersiz "
                f"'{self.direction_mode}' (long_only|two_sided beklenir)"
            )
        if self.settlement_days < 0:
            raise ValueError(f"MarketSpec[{self.market_id}]: settlement_days negatif olamaz")


# config yükleyici (core/config.py) doldurur (Bölüm 11). Boş başlar.
MARKET_REGISTRY: dict[str, MarketSpec] = {}


def register_market(spec: MarketSpec) -> None:
    """MarketSpec'i registry'ye ekler (config yükleme sırasında çağrılır)."""
    MARKET_REGISTRY[spec.market_id] = spec


def get_market(market_id: str) -> MarketSpec:
    """Kayıtlı MarketSpec'i döner; yoksa açık hata (sessiz None YASAK)."""
    try:
        return MARKET_REGISTRY[market_id]
    except KeyError as exc:
        raise KeyError(
            f"MarketSpec bulunamadı: '{market_id}' (kayıtlı: {sorted(MARKET_REGISTRY)})"
        ) from exc


def clear_registry() -> None:
    """Test/yeniden-yükleme yardımcısı — registry'yi boşaltır."""
    MARKET_REGISTRY.clear()


# BIST'in davranış-nötr yerleşik spec'i (config göçünden bağımsız bir referans
# değer; config yükleyici config/markets/bist.yaml ile bunu doğrular/üzerine yazar).
BIST_MARKET_SPEC = MarketSpec(
    market_id="bist",
    calendar_id="XIST",
    currency="TRY",
    direction_mode="long_only",
    settlement_days=2,
    qty_step=1,
    price_decimals=2,
    cost_model_id="bist",
    gate_profile_id="bist",
    data_adapter_id="bist_yf",
    eval_after_close_min=10,
)

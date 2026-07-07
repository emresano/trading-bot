# core/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Direction(str, Enum):
    """Pozisyon/sinyal yönü (EXPANSION.md 4.1). BIST/US long_only; FX two_sided.
    E2 yalnızca motor YETENEĞİNİ kurar — short gate seti tasarımı kapsam dışı."""
    LONG = "LONG"
    SHORT = "SHORT"


class SignalAction(str, Enum):
    ENTER_LONG = "ENTER_LONG"
    EXIT_LONG = "EXIT_LONG"          # trend bozulması / momentum çöküşü kaynaklı çıkış
    HOLD_CASH = "HOLD_CASH"          # birinci sınıf karar: koşullar uygun değil
    HOLD_POSITION = "HOLD_POSITION"  # pozisyon var, koşullar hâlâ geçerli
    ENTER_SHORT = "ENTER_SHORT"      # (EXPANSION.md 4.1) short mekaniği — FX aktivasyonu ön şartı
    EXIT_SHORT = "EXIT_SHORT"        # short pozisyon kapanışı


class RejectReason(str, Enum):
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    WEEKLY_LOSS_LIMIT = "WEEKLY_LOSS_LIMIT"
    DRAWDOWN_BREAKER = "DRAWDOWN_BREAKER"
    MAX_POSITIONS = "MAX_POSITIONS"
    CORRELATION_LIMIT = "CORRELATION_LIMIT"
    MIN_RR_FAILED = "MIN_RR_FAILED"
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    POSITION_TOO_SMALL = "POSITION_TOO_SMALL"
    KILL_SWITCH = "KILL_SWITCH"
    PRETRADE_CHECK_FAILED = "PRETRADE_CHECK_FAILED"
    MARKET_CLOSED = "MARKET_CLOSED"
    NEWS_BLACKOUT = "NEWS_BLACKOUT"
    # EXPANSION.md 4.1 ekleri:
    PDT_LIMIT = "PDT_LIMIT"                     # ABD pattern-day-trader koruması (Bölüm 9.4)
    MARGIN_INSUFFICIENT = "MARGIN_INSUFFICIENT" # FX marjin yetersiz
    CALENDAR_BLACKOUT = "CALENDAR_BLACKOUT"     # deterministik takvim vetosu (earnings/ekonomik)
    SETTLEMENT_CASH_UNAVAILABLE = "SETTLEMENT_CASH_UNAVAILABLE"  # T+1/T+2 nakdi henüz kullanılamaz


@dataclass(frozen=True)
class Signal:
    symbol: str
    ts: datetime                      # sinyalin dayandığı barın kapanış zamanı (UTC)
    action: SignalAction
    reasons: list[str]                # her gate'in kararı, insan-okur formatta
    features: dict[str, float]        # karar anındaki indikatör değerleri (journal için)
    entry_ref_price: float            # sinyal barının kapanışı (boyutlama referansı)
    suggested_stop: Optional[float] = None
    suggested_target: Optional[float] = None
    direction: Direction = Direction.LONG  # (EXPANSION.md 4.1) BIST varsayılanı LONG — geriye uyum


@dataclass(frozen=True)
class TradeDecision:
    signal: Signal
    approved: bool
    reject_reasons: list[RejectReason] = field(default_factory=list)
    quantity: int = 0
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    risk_amount_try: float = 0.0      # bu işlemde riske edilen TL
    # EXPANSION.md 4.1 ekleri: risk_amount_try geriye uyum için kalır — bist'te
    # ikisi eşit doldurulur, diğer sleeve'lerde 0 bırakılır; raporlar risk_amount_ccy kullanır.
    risk_amount_ccy: float = 0.0      # sleeve para biriminde risk
    currency: str = "TRY"


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    stop_price: float
    target_price: float
    opened_at: datetime
    broker_order_ids: list[str] = field(default_factory=list)
    # EXPANSION.md 4.1 ekleri (varsayılanlı → geriye uyum):
    direction: Direction = Direction.LONG
    market: str = "bist"


@dataclass
class AccountState:
    equity: float                     # nakit + pozisyonların piyasa değeri
    cash: float
    positions: list[Position]
    peak_equity: float                # circuit breaker referansı (journal'dan beslenir)
    realized_pnl_today: float
    realized_pnl_week: float
    # EXPANSION.md 4.1 ekleri:
    currency: str = "TRY"
    margin_used: float = 0.0          # FX; hisselerde 0
    settled_cash: float = -1.0        # -1 = "cash ile aynı" (BIST mevcut davranış);
                                      # ABD nakit-hesap modunda T+1 muhasebesi doldurur

# core/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalAction(str, Enum):
    ENTER_LONG = "ENTER_LONG"
    EXIT_LONG = "EXIT_LONG"          # trend bozulması / momentum çöküşü kaynaklı çıkış
    HOLD_CASH = "HOLD_CASH"          # birinci sınıf karar: koşullar uygun değil
    HOLD_POSITION = "HOLD_POSITION"  # pozisyon var, koşullar hâlâ geçerli


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


@dataclass(frozen=True)
class TradeDecision:
    signal: Signal
    approved: bool
    reject_reasons: list[RejectReason] = field(default_factory=list)
    quantity: int = 0
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    risk_amount_try: float = 0.0      # bu işlemde riske edilen TL


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    stop_price: float
    target_price: float
    opened_at: datetime
    broker_order_ids: list[str] = field(default_factory=list)


@dataclass
class AccountState:
    equity: float                     # nakit + pozisyonların piyasa değeri
    cash: float
    positions: list[Position]
    peak_equity: float                # circuit breaker referansı (journal'dan beslenir)
    realized_pnl_today: float
    realized_pnl_week: float

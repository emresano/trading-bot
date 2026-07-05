# core/clock.py
from __future__ import annotations
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

TZ_ISTANBUL = ZoneInfo("Europe/Istanbul")
TZ_UTC = timezone.utc

# BIST seans saatleri (Europe/Istanbul, yaklaşık) — Faz 5'te resmi kaynakla doğrulanacak (CLAUDE.md Bölüm 16 #5).
BIST_OPENING_AUCTION_START = time(9, 40)
BIST_CONTINUOUS_START = time(9, 55)
BIST_CONTINUOUS_END = time(18, 0)
BIST_CLOSING_AUCTION_END = time(18, 10)


def now_utc() -> datetime:
    return datetime.now(TZ_UTC)


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime yasak — tzinfo zorunlu")
    return dt.astimezone(TZ_UTC)


def to_istanbul(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime yasak — tzinfo zorunlu")
    return dt.astimezone(TZ_ISTANBUL)


def is_trading_day(dt: datetime) -> bool:
    """Yalnızca hafta içi kontrolü. Resmi tatil takvimi MVP kapsamı dışında."""
    local = to_istanbul(dt)
    return local.weekday() < 5  # 0=Pazartesi ... 4=Cuma


def is_bist_session(dt: datetime) -> bool:
    """Sürekli işlem seansında mı (açılış/kapanış müzayede pencereleri hariç)."""
    if not is_trading_day(dt):
        return False
    local = to_istanbul(dt)
    t = local.time()
    return BIST_CONTINUOUS_START <= t < BIST_CONTINUOUS_END


def is_auction_window(dt: datetime) -> bool:
    """Açılış veya kapanış müzayede penceresinde mi (işlem yasak, seans açık sayılır)."""
    if not is_trading_day(dt):
        return False
    local = to_istanbul(dt)
    t = local.time()
    in_open_auction = BIST_OPENING_AUCTION_START <= t < BIST_CONTINUOUS_START
    in_close_auction = BIST_CONTINUOUS_END <= t < BIST_CLOSING_AUCTION_END
    return in_open_auction or in_close_auction

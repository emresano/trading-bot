# risk/account_rules.py
"""Takas nakdi (settlement) + PDT koruması (EXPANSION.md Bölüm 9.3/9.4).

Saf fonksiyonlar; risk motorunun sleeve-farkındalıklı genişlemesi. BIST'te
settled_cash = -1 → `available_cash` = cash (mevcut davranış değişmez).
"""
from __future__ import annotations

from core.models import AccountState, RejectReason


def available_cash(acct: AccountState) -> float:
    """Boyutlamada kullanılabilir nakit (Bölüm 9.3). settled_cash >= 0 ise (ABD
    nakit-hesap T+1 muhasebesi) settled_cash; aksi halde (-1, BIST) cash."""
    return acct.settled_cash if acct.settled_cash >= 0 else acct.cash


def settlement_allows(acct: AccountState, required_cash: float) -> tuple[bool, RejectReason | None]:
    """Takas kuralı: gereken nakit kullanılabilir (takas olmuş) nakitten büyükse
    SETTLEMENT_CASH_UNAVAILABLE (yalnızca settled_cash>=0 modunda geçerli)."""
    if acct.settled_cash < 0:
        return True, None  # BIST/settlement-agnostik mod
    if required_cash > acct.settled_cash:
        return False, RejectReason.SETTLEMENT_CASH_UNAVAILABLE
    return True, None


PDT_EQUITY_THRESHOLD_USD = 25_000.0
PDT_DAYTRADE_LIMIT = 3


def pdt_blocks_entry(equity_usd: float, rolling_day_trades: int, account_type: str) -> bool:
    """PDT koruması (Bölüm 9.4, yalnızca us + account_type='margin').
    sleeve_equity < 25.000 USD VE son 5 iş günü day-trade sayısı >= 3 ise yeni
    ENTER reddedilir (yeni pozisyonun aynı gün stop'lanması 4.'yü oluşturabilir).
    account_type='cash' ise PDT devre dışı (settlement kuralı devrede)."""
    if account_type != "margin":
        return False
    return equity_usd < PDT_EQUITY_THRESHOLD_USD and rolling_day_trades >= PDT_DAYTRADE_LIMIT

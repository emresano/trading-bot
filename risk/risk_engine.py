# risk/risk_engine.py
from __future__ import annotations
import math
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from core.models import AccountState, Position, RejectReason, Signal, TradeDecision

# Bölüm 9.1: breaker tetiklendiğinde yazılan dosya. Yalnızca kullanıcı elle siler.
BREAKER_FILE = Path("runtime/BREAKER_TRIPPED")


def kill_switch_active(cfg) -> bool:
    return Path(cfg.safety.kill_switch_file).exists()


def breaker_tripped(breaker_file: Optional[Path] = None) -> bool:
    # None -> modül seviyesindeki BREAKER_FILE'ı ÇAĞRI ANINDA okur (geç bağlama) —
    # monkeypatch.setattr(risk_engine, "BREAKER_FILE", ...) ile testlerin ve
    # canlı/paper modun aynı ismi paylaşabilmesi için parametre varsayılanı
    # olarak DOĞRUDAN BREAKER_FILE kullanılmıyor (o, tanım anında erken bağlanırdı).
    if breaker_file is None:
        breaker_file = BREAKER_FILE
    return breaker_file.exists()


def check_and_trip_breaker(acct: AccountState, cfg, breaker_file: Optional[Path] = None) -> bool:
    """equity, peak_equity'den max_drawdown_breaker_pct kadar düştüyse breaker_file'ı
    yazar ve True döner. Dosya zaten varsa dokunmadan True döner (Bölüm 9.1:
    breaker'ı yalnızca kullanıcı elle sıfırlayabilir, kod kendiliğinden temizlemez).

    `breaker_file` parametresi, paper/real modda (BREAKER_FILE varsayılanı,
    davranış değişmez) ile backtest'te (her koşunun kendi izole, geçici dosyası —
    böylece paralel/ardışık backtest koşuları veya eşzamanlı bir canlı bot
    birbirinin breaker durumunu kirletmez) AYNI fonksiyonun güvenle
    paylaşılabilmesi için eklendi (HARDENING.md harness düzeltme turu)."""
    if breaker_file is None:
        breaker_file = BREAKER_FILE
    if breaker_tripped(breaker_file):
        return True
    if acct.peak_equity <= 0:
        return False
    drawdown = 1 - (acct.equity / acct.peak_equity)
    if drawdown >= cfg.risk.max_drawdown_breaker_pct:
        breaker_file.parent.mkdir(parents=True, exist_ok=True)
        breaker_file.write_text(
            f"equity={acct.equity} peak_equity={acct.peak_equity} "
            f"drawdown={drawdown:.4f} esik={cfg.risk.max_drawdown_breaker_pct}\n"
        )
        return True
    return False


def historical_correlation(
    symbol: str,
    positions: list[Position],
    price_loader: Callable[[str], pd.Series],
    lookback_days: int,
) -> float:
    """Adayın son `lookback_days` günlük getirisiyle her açık pozisyonun getiri
    serisi arasındaki Pearson korelasyonların en yükseğini (mutlak değer) döner.
    Açık pozisyon yoksa 0.0. `price_loader(symbol)` kapanış fiyatı Series'i
    döndürmeli (saf fonksiyon kalması için IO çağıranın sorumluluğundadır)."""
    if not positions:
        return 0.0

    candidate_close = price_loader(symbol)
    candidate_returns = candidate_close.pct_change().dropna().tail(lookback_days)

    max_corr = 0.0
    for pos in positions:
        other_close = price_loader(pos.symbol)
        other_returns = other_close.pct_change().dropna().tail(lookback_days)
        aligned = pd.concat([candidate_returns, other_returns], axis=1, join="inner")
        if len(aligned) < 2:
            continue
        corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        if pd.notna(corr):
            max_corr = max(max_corr, abs(float(corr)))
    return max_corr


def size_and_approve(
    sig: Signal,
    acct: AccountState,
    cfg,
    corr_fn: Callable[[str, list[Position]], float],
    breaker_file: Optional[Path] = None,
) -> TradeDecision:
    """Bölüm 9.2 referans implementasyonu. `sig` yalnızca ENTER_LONG aksiyonlu,
    suggested_stop/suggested_target dolu bir Signal olmalıdır (çağıranın
    sorumluluğu — HOLD_CASH sinyalleri risk motoruna hiç gelmemeli).
    `breaker_file`: bkz. check_and_trip_breaker — varsayılanı (None) paper/real
    modun paylaştığı gerçek BREAKER_FILE'ı çağrı anında okur, backtest kendi
    izole yolunu geçer."""
    if breaker_file is None:
        breaker_file = BREAKER_FILE
    rejects: list[RejectReason] = []
    entry, stop, target = sig.entry_ref_price, sig.suggested_stop, sig.suggested_target

    if kill_switch_active(cfg):
        rejects.append(RejectReason.KILL_SWITCH)
    if breaker_tripped(breaker_file):
        rejects.append(RejectReason.DRAWDOWN_BREAKER)
    if acct.realized_pnl_today <= -cfg.risk.daily_loss_limit_pct * acct.equity:
        rejects.append(RejectReason.DAILY_LOSS_LIMIT)
    if acct.realized_pnl_week <= -cfg.risk.weekly_loss_limit_pct * acct.equity:
        rejects.append(RejectReason.WEEKLY_LOSS_LIMIT)
    if len(acct.positions) >= cfg.risk.max_open_positions:
        rejects.append(RejectReason.MAX_POSITIONS)

    rr = (target - entry) / (entry - stop) if entry > stop else 0.0
    if rr < cfg.risk.min_rr:
        rejects.append(RejectReason.MIN_RR_FAILED)

    if corr_fn(sig.symbol, acct.positions) > cfg.risk.correlation_max:
        rejects.append(RejectReason.CORRELATION_LIMIT)

    if rejects:
        return TradeDecision(sig, approved=False, reject_reasons=rejects)

    # --- boyutlama ---
    risk_amount = acct.equity * cfg.risk.risk_per_trade_pct
    per_share_risk = entry - stop  # > 0 garantili (yukarıda kontrol)
    qty = math.floor(risk_amount / per_share_risk)
    max_notional = acct.equity * cfg.risk.max_position_notional_pct
    qty = min(qty, math.floor(max_notional / entry))
    qty = min(qty, math.floor(acct.cash / (entry * (1 + cfg.costs.commission_bps / 1e4))))
    if qty < 1:
        return TradeDecision(sig, approved=False, reject_reasons=[RejectReason.POSITION_TOO_SMALL])
    return TradeDecision(
        sig, approved=True, quantity=qty,
        stop_price=stop, target_price=target,
        risk_amount_try=qty * per_share_risk,
    )

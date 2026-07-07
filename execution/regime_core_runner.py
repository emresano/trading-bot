# execution/regime_core_runner.py
"""regime_core canlı/paper döngüsü — SAF fonksiyon çağrısı (Faz 5 F5A-2).

"backtest=canlı aynı fonksiyon" (CLAUDE.md 3.1): bu runner `strategy/regime_core.py`'nin
SAF fonksiyonlarını (build_composite / compute_regime_signal / plan_enter / plan_exit)
ÇAĞIRIR — kopyalamaz. `run_regime_core_prod` backtest sürücüsüdür; bu runner AYNI
loop gövdesini gün-gün, KALICI state (PaperBroker + runner state DB) ile yürütür.

t+1 KAPANIŞ YÜRÜTME (B1 canlı karşılığı): sinyal t günü kapanışında hesaplanır;
işlem t+1 günü kapanışına-yakın (müzayede penceresinden ÖNCE) yürütülür. Bu modül
"karar" katmanıdır — müzayede/seans zamanlaması PaperBroker.enforce_session +
scheduler (main.py) sorumluluğu. Backtest tam-kapanış fiyatı ile canlı kapanışa-yakın
fiyat farkı PARİTE RAPORUNDA izlenen bir sapma kalemidir (hata değil).

PARİTE: anahtarlama (switch) tarihleri/aksiyonları run_regime_core_prod ile BİREBİR
aynıdır (karar parite, B5). Equity, çok-sembollü enter/exit'te nakit toplama
ilişkilendirme sırası (sıralı broker güncellemesi vs plan_enter/exit tek-toplam) ve
kapanışa-yakın yürütme nedeniyle ULP/sapma düzeyinde farklı OLABİLİR — beklenen,
izlenen sapma.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from core.models import Side
from execution.paper_broker import PaperBroker
from strategy.regime_core import (
    RegimeCoreParams, RegimeCoreBreaker, BreakerState,
    build_composite, compute_regime_signal, plan_enter,
)

DEFAULT_RUNNER_STATE = Path("runtime/regime_runner.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runner_state (
    id INTEGER PRIMARY KEY CHECK(id=1),
    last_processed_date TEXT, peak_equity REAL, prev_breaker_state TEXT,
    alarm_latched INTEGER DEFAULT 0
);
"""


@dataclass
class DailyDecision:
    date: pd.Timestamp
    composite: float
    ma: float
    upper_band: float
    lower_band: float
    confirm_count: int          # son confirm_days içinde üst-bant üstü gün sayısı
    signal_yesterday: bool      # dün kapanışta hesaplanan rejim kararı (bugün uygulanır)
    in_position_before: bool
    action: str                 # "ENTER" | "EXIT" | "HOLD_POSITION" | "HOLD_CASH" | "FREEZE_BLOCK_ENTER"
    planned_qty: dict[str, int] = field(default_factory=dict)
    executed_order_ids: list[str] = field(default_factory=list)
    equity_before: float = 0.0
    equity_after: float = 0.0
    cash_after: float = 0.0
    interest_accrued: float = 0.0
    breaker_state: str = "OK"
    drawdown: float = 0.0
    peak_equity: float = 0.0


class RegimeCoreRunner:
    def __init__(self, broker: PaperBroker, params: RegimeCoreParams,
                 cash_rate: Optional[pd.Series] = None,
                 breaker: Optional[RegimeCoreBreaker] = None,
                 state_path: Path | str = DEFAULT_RUNNER_STATE,
                 decision_hook: Optional[Callable[[DailyDecision], None]] = None,
                 ledger=None):
        self.broker = broker
        self.params = params
        self.cash_rate = cash_rate
        self.breaker = breaker
        self.decision_hook = decision_hook
        self.ledger = ledger    # safety.reconciliation.LocalLedger | None (B2)
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.state_path))
        self._conn.executescript(_SCHEMA)
        row = self._conn.execute("SELECT id FROM runner_state WHERE id=1").fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO runner_state (id, last_processed_date, peak_equity, prev_breaker_state, "
                "alarm_latched) VALUES (1, NULL, ?, 'OK', 0)", (params.initial_equity,))
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ state
    def _state(self) -> tuple[Optional[pd.Timestamp], float, str, bool]:
        r = self._conn.execute(
            "SELECT last_processed_date, peak_equity, prev_breaker_state, alarm_latched "
            "FROM runner_state WHERE id=1").fetchone()
        last = pd.Timestamp(r[0]) if r[0] else None
        return last, float(r[1]), r[2], bool(r[3])

    def _save_state(self, last_date: pd.Timestamp, peak: float, prev_state: str, latched: bool) -> None:
        self._conn.execute(
            "UPDATE runner_state SET last_processed_date=?, peak_equity=?, prev_breaker_state=?, "
            "alarm_latched=? WHERE id=1",
            (last_date.isoformat(), peak, prev_state, int(latched)))
        self._conn.commit()

    def initialize_flat(self, as_of_date) -> None:
        """Canlı başlangıç: geçmişi TİCARETSİZ atla — bu tarihe kadar işlenmiş say,
        nakitte başla. (Paper go-live; geçmiş 20 yılı yeniden ticaretleme.)"""
        self._save_state(pd.Timestamp(as_of_date), self.params.initial_equity, "OK", False)

    # ------------------------------------------------------------------ ana döngü
    def process_up_to(self, closes: dict[str, pd.Series], today=None) -> list[DailyDecision]:
        """`closes` (sembol→kapanış serisi, LiveHistoryStore'dan) ile last_processed'dan
        `today`e kadar işlenmemiş her günü sırayla yürütür (run_regime_core_prod loop
        gövdesinin gün-gün, kalıcı hali). Döner: üretilen günlük kararlar."""
        composite, _fill = build_composite(closes)
        regime_on = compute_regime_signal(
            composite, self.params.ma_period, self.params.band_pct, self.params.confirm_days)
        ma = composite.rolling(self.params.ma_period).mean()
        above_upper = composite > ma * (1 + self.params.band_pct)

        all_dates = composite.index
        if today is not None:
            all_dates = all_dates[all_dates <= pd.Timestamp(today)]

        last_processed, peak, prev_state, latched = self._state()
        daily_rate = (self.cash_rate.reindex(all_dates, method="ffill").bfill()
                      if self.cash_rate is not None else None)

        decisions: list[DailyDecision] = []
        for i, date in enumerate(all_dates):
            if last_processed is not None and date <= last_processed:
                continue
            prev_date = all_dates[i - 1] if i > 0 else None
            in_position = bool(self.broker.quantities())
            signal_yesterday = bool(regime_on.loc[prev_date]) if prev_date is not None else False

            # --- prices for today (raw) ---
            prices_today = {s: float(closes[s].loc[date]) for s in self.params.symbols
                            if date in closes[s].index}
            mtm_prices = self._mtm_prices(closes, date)
            self.broker.update_prices({**mtm_prices, **prices_today})

            interest = 0.0
            # --- cash accrual (transition ÖNCESİ in_position'a göre) ---
            if prev_date is not None and not in_position and daily_rate is not None:
                days = (date - prev_date).days
                rate = daily_rate.loc[date]
                if days > 0 and pd.notna(rate):
                    interest = self.broker.accrue_cash(float(rate), days)

            equity_before = self.broker.get_account_state().equity
            action = "HOLD_POSITION" if in_position else "HOLD_CASH"
            planned_qty: dict[str, int] = {}
            order_ids: list[str] = []

            # --- t+1 transition ---
            if signal_yesterday != in_position:
                if signal_yesterday and not in_position:
                    if self.breaker is not None and self.breaker.freeze_active():
                        action = "FREEZE_BLOCK_ENTER"
                    else:
                        planned_qty, _cash_after = plan_enter(
                            equity_before, prices_today, self.params.symbols,
                            self.params.commission_bps, self.params.slippage_bps)
                        for sym in self.params.symbols:
                            if sym in planned_qty:
                                order_ids += self.broker.submit_market_order(sym, Side.BUY, planned_qty[sym])
                        action = "ENTER"
                elif not signal_yesterday and in_position:
                    order_ids = self.broker.close_all(order=self.params.symbols)
                    action = "EXIT"

            equity_after = self.broker.get_account_state().equity
            peak = max(peak, equity_after)
            drawdown = 1 - equity_after / peak if peak > 0 else 0.0

            breaker_state = "OK"
            if self.breaker is not None:
                st = self.breaker.evaluate(date, equity_after, peak)
                breaker_state = st.value
                # epizot latch reset (regime_core ile aynı mantık)
                if drawdown < self.breaker.alarm_pct * 0.5:
                    prev_state = "OK"
                if st == BreakerState.ALARM and prev_state != "ALARM":
                    prev_state = "ALARM"
                elif st == BreakerState.FREEZE and prev_state != "FREEZE":
                    prev_state = "FREEZE"

            comp_v = float(composite.loc[date])
            ma_v = float(ma.loc[date]) if pd.notna(ma.loc[date]) else float("nan")
            confirm_ct = int(above_upper.loc[:date].tail(self.params.confirm_days).sum())
            dec = DailyDecision(
                date=date, composite=comp_v, ma=ma_v,
                upper_band=ma_v * (1 + self.params.band_pct),
                lower_band=ma_v * (1 - self.params.band_pct),
                confirm_count=confirm_ct, signal_yesterday=signal_yesterday,
                in_position_before=in_position, action=action, planned_qty=planned_qty,
                executed_order_ids=order_ids, equity_before=equity_before,
                equity_after=equity_after, cash_after=self.broker.cash,
                interest_accrued=interest, breaker_state=breaker_state,
                drawdown=drawdown, peak_equity=peak)
            decisions.append(dec)
            if self.decision_hook is not None:
                self.decision_hook(dec)
            self._save_state(date, peak, prev_state, latched)
            # B2: döngü SONUNDA yerel defteri broker gerçeğine eşitle. Bu yazımdan
            # ÖNCE bir çöküş olursa broker≠yerel → bir sonraki startup_reconcile FREEZE.
            if self.ledger is not None:
                self.ledger.sync_from(self.broker.quantities())
        return decisions

    def _mtm_prices(self, closes: dict[str, pd.Series], date) -> dict[str, float]:
        """Tutulan her sembol için ham fiyat: bugünkü varsa o, yoksa son bilinen
        (regime_core._prices_for_mtm ile aynı)."""
        out: dict[str, float] = {}
        for sym in self.broker.quantities():
            px = closes[sym]
            if date in px.index:
                out[sym] = float(px.loc[date])
            else:
                prior = px.loc[:date]
                out[sym] = float(prior.iloc[-1]) if len(prior) else 0.0
        return out

# execution/paper_broker.py
"""PaperBroker — dahili emir simülatörü (CLAUDE.md Bölüm 10, Faz 5 F5A-2).

AlgoLab demo ortamına BAĞIMLI DEĞİLDİR. Kalıcı state SQLite'tadır
(`runtime/paper_state.sqlite`) — süreç yeniden başlasa da nakit/pozisyon/fiyat
kurtarılır (CLAUDE.md 3.1 #4).

PARİTE (backtest=canlı): market emri fill matematiği regime_core saf fonksiyonlarıyla
(plan_enter/plan_exit) BİREBİR aynıdır:
  ALIŞ:  fill = price×(1+slip);  nakit -= fill×qty×(1+comm)
  SATIŞ: fill = price×(1−slip);  nakit += fill×qty×(1−comm)
Böylece runner plan_enter ile miktarı belirleyip her sembol için market emri
gönderdiğinde broker nakdi, plan_enter'ın cash_after'ıyla bayt-bayt örtüşür.

NAKİT BACAĞI: `accrue_cash` regime_core ile AYNI modeli kullanır (TRY_ON_RATE−200bp,
ACT/365, takvim-günü üssü). Tahakkuk `accrued_interest`'te AYRI izlenir → raporlarda
"modellenmiş faiz" (KALICI KAYIT 6, madde 19: gerçek enstrüman real-öncesi kuyrukta).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from core.models import AccountState, Position, Side
from execution.broker_adapter import BrokerAdapter, BrokerError
from strategy.regime_core import CASH_YIELD_HAIRCUT

DEFAULT_STATE = Path("runtime/paper_state.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_account (
    id INTEGER PRIMARY KEY CHECK(id=1),
    cash REAL NOT NULL, accrued_interest REAL NOT NULL,
    initial_equity REAL NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_positions (
    symbol TEXT PRIMARY KEY, quantity INTEGER NOT NULL,
    avg_price REAL NOT NULL, opened_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_prices (
    symbol TEXT PRIMARY KEY, price REAL NOT NULL, ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    broker_order_id TEXT, ts TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
    quantity INTEGER NOT NULL, fill_price REAL, commission REAL, gross REAL,
    status TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_brackets (
    symbol TEXT PRIMARY KEY, quantity INTEGER, stop_price REAL, target_price REAL,
    active INTEGER NOT NULL DEFAULT 1
);
"""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperBroker(BrokerAdapter):
    """Kalıcı, deterministik emir simülatörü."""

    def __init__(self, initial_equity: float, commission_bps: float, slippage_bps: float,
                 state_path: Path | str = DEFAULT_STATE,
                 cash_yield_haircut: float = CASH_YIELD_HAIRCUT,
                 session_check: Optional[Callable[[], bool]] = None,
                 enforce_session: bool = False,
                 history_store=None):
        self.initial_equity = float(initial_equity)
        self.commission_frac = commission_bps / 1e4
        self.slippage_frac = slippage_bps / 1e4
        self.cash_yield_haircut = cash_yield_haircut
        self.enforce_session = enforce_session
        self._session_check = session_check
        self._history_store = history_store
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.state_path))
        self._conn.executescript(_SCHEMA)
        self._ensure_account()
        self._conn.commit()
        self._order_seq = self._max_order_seq()

    # ------------------------------------------------------------------ kurulum
    def _ensure_account(self) -> None:
        row = self._conn.execute("SELECT cash FROM paper_account WHERE id=1").fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO paper_account (id, cash, accrued_interest, initial_equity, updated_at) "
                "VALUES (1,?,?,?,?)",
                (self.initial_equity, 0.0, self.initial_equity, _utcnow_iso()),
            )

    def _max_order_seq(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM paper_orders").fetchone()
        return int(row[0]) if row else 0

    def connect(self) -> None:
        return None

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ nakit / hesap
    @property
    def cash(self) -> float:
        return float(self._conn.execute("SELECT cash FROM paper_account WHERE id=1").fetchone()[0])

    @property
    def accrued_interest(self) -> float:
        return float(self._conn.execute(
            "SELECT accrued_interest FROM paper_account WHERE id=1").fetchone()[0])

    def _set_cash(self, cash: float, add_interest: float = 0.0) -> None:
        self._conn.execute(
            "UPDATE paper_account SET cash=?, accrued_interest=accrued_interest+?, updated_at=? WHERE id=1",
            (cash, add_interest, _utcnow_iso()),
        )

    def update_prices(self, prices: dict[str, float]) -> None:
        """Son bilinen fiyatları güncelle (MTM + fill referansı + restart kurtarma)."""
        now = _utcnow_iso()
        for sym, px in prices.items():
            self._conn.execute(
                "INSERT INTO paper_prices (symbol, price, ts) VALUES (?,?,?) "
                "ON CONFLICT(symbol) DO UPDATE SET price=excluded.price, ts=excluded.ts",
                (sym, float(px), now),
            )
        self._conn.commit()

    def get_last_price(self, symbol: str) -> float:
        row = self._conn.execute("SELECT price FROM paper_prices WHERE symbol=?", (symbol,)).fetchone()
        if row is None:
            raise BrokerError(f"PaperBroker: {symbol} için fiyat yok (update_prices çağrılmadı)")
        return float(row[0])

    def accrue_cash(self, annual_rate: float, days: int) -> float:
        """Nakit tahakkuku — regime_core ile AYNI formül. Döner: eklenen faiz tutarı.
        r_net = max(annual_rate − haircut, 0); cash ×= (1+r_net/365)^days."""
        if days <= 0 or annual_rate is None or pd.isna(annual_rate):
            return 0.0
        r_net = max(float(annual_rate) - self.cash_yield_haircut, 0.0)
        old = self.cash
        new = old * (1 + r_net / 365) ** days
        interest = new - old
        self._set_cash(new, add_interest=interest)
        self._conn.commit()
        return interest

    # ------------------------------------------------------------------ pozisyonlar
    def _positions_raw(self) -> dict[str, tuple[int, float, str]]:
        rows = self._conn.execute(
            "SELECT symbol, quantity, avg_price, opened_at FROM paper_positions").fetchall()
        return {r[0]: (int(r[1]), float(r[2]), r[3]) for r in rows}

    def quantities(self) -> dict[str, int]:
        return {s: q for s, (q, _, _) in self._positions_raw().items()}

    def get_positions(self) -> list[Position]:
        out = []
        for sym, (qty, avg, opened) in self._positions_raw().items():
            out.append(Position(symbol=sym, quantity=qty, avg_price=avg, stop_price=0.0,
                                 target_price=0.0, opened_at=datetime.fromisoformat(opened)))
        return out

    def get_account_state(self) -> AccountState:
        cash = self.cash
        positions = self.get_positions()
        equity = cash
        for p in positions:
            equity += p.quantity * self.get_last_price(p.symbol)
        return AccountState(equity=equity, cash=cash, positions=positions,
                            peak_equity=equity, realized_pnl_today=0.0, realized_pnl_week=0.0)

    # ------------------------------------------------------------------ emir
    def _record_order(self, symbol: str, side: Side, qty: int, fill_price: float,
                      commission: float, gross: float, status: str, note: str) -> str:
        self._order_seq += 1
        oid = f"PAPER-{self._order_seq:08d}"
        self._conn.execute(
            "INSERT INTO paper_orders (broker_order_id, ts, symbol, side, quantity, fill_price, "
            "commission, gross, status, note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (oid, _utcnow_iso(), symbol, side.value, qty, fill_price, commission, gross,
             status, note, _utcnow_iso()),
        )
        return oid

    def _guard_session(self) -> None:
        if not self.enforce_session:
            return
        chk = self._session_check
        if chk is None:
            from core.clock import is_bist_session, now_utc
            chk = lambda: is_bist_session(now_utc())
        if not chk():
            raise BrokerError("MARKET_CLOSED: müzayede/seans dışı — emir kabul edilmez")

    def submit_market_order(self, symbol: str, side: Side, quantity: int) -> list[str]:
        """Düz market emri. ALIŞ: cash -= fill×qty×(1+comm). SATIŞ: cash += fill×qty×(1−comm)."""
        if quantity < 1:
            raise BrokerError(f"PaperBroker: geçersiz miktar {quantity}")
        self._guard_session()
        raw = self.get_last_price(symbol)
        if side == Side.BUY:
            fill = raw * (1 + self.slippage_frac)
            gross = fill * quantity
            commission = gross * self.commission_frac
            new_cash = self.cash - gross - commission
            if new_cash < -1e-6:
                raise BrokerError(f"INSUFFICIENT_CASH: {symbol} alış {gross+commission:.2f} > nakit {self.cash:.2f}")
            self._apply_buy(symbol, quantity, fill)
            self._set_cash(new_cash)
            oid = self._record_order(symbol, side, quantity, fill, commission, gross, "FILLED", "market buy")
        else:
            pos = self._positions_raw().get(symbol)
            if pos is None or pos[0] < quantity:
                raise BrokerError(f"PaperBroker: {symbol} satışta yetersiz pozisyon")
            fill = raw * (1 - self.slippage_frac)
            gross = fill * quantity
            commission = gross * self.commission_frac
            self._apply_sell(symbol, quantity)
            self._set_cash(self.cash + gross - commission)
            oid = self._record_order(symbol, side, quantity, fill, commission, gross, "FILLED", "market sell")
        self._conn.commit()
        return [oid]

    def _apply_buy(self, symbol: str, qty: int, fill: float) -> None:
        pos = self._positions_raw().get(symbol)
        if pos is None:
            self._conn.execute(
                "INSERT INTO paper_positions (symbol, quantity, avg_price, opened_at) VALUES (?,?,?,?)",
                (symbol, qty, fill, _utcnow_iso()),
            )
        else:
            old_qty, old_avg, opened = pos
            new_qty = old_qty + qty
            new_avg = (old_qty * old_avg + qty * fill) / new_qty
            self._conn.execute(
                "UPDATE paper_positions SET quantity=?, avg_price=? WHERE symbol=?",
                (new_qty, new_avg, symbol),
            )

    def _apply_sell(self, symbol: str, qty: int) -> None:
        pos = self._positions_raw()[symbol]
        remaining = pos[0] - qty
        if remaining <= 0:
            self._conn.execute("DELETE FROM paper_positions WHERE symbol=?", (symbol,))
        else:
            self._conn.execute(
                "UPDATE paper_positions SET quantity=? WHERE symbol=?", (remaining, symbol))

    def close_position(self, symbol: str) -> None:
        pos = self._positions_raw().get(symbol)
        if pos is None:
            return
        self.submit_market_order(symbol, Side.SELL, pos[0])

    def close_all(self, order: Optional[list[str]] = None) -> list[str]:
        """Tüm pozisyonları kapat (rejim EXIT). `order` verilirse o sırayla (parite:
        plan_exit ile aynı sembol sırası); yoksa alfabetik (deterministik)."""
        held = self.quantities()
        syms = [s for s in order if s in held] if order is not None else sorted(held)
        oids: list[str] = []
        for sym in syms:
            oids += self.submit_market_order(sym, Side.SELL, held[sym])
        return oids

    # ------------------------------------------------------------------ bracket (10-gate; regime_core kullanmaz)
    def submit_bracket_order(self, symbol: str, side: Side, quantity: int,
                             stop_price: float, target_price: float) -> list[str]:
        oids = self.submit_market_order(symbol, side, quantity)
        self._conn.execute(
            "INSERT INTO paper_brackets (symbol, quantity, stop_price, target_price, active) "
            "VALUES (?,?,?,?,1) ON CONFLICT(symbol) DO UPDATE SET quantity=excluded.quantity, "
            "stop_price=excluded.stop_price, target_price=excluded.target_price, active=1",
            (symbol, quantity, stop_price, target_price),
        )
        self._conn.commit()
        return oids

    def process_price(self, symbol: str, last: float) -> Optional[str]:
        """Bekleyen bracket için stop/target kontrolü. Aynı barda ikisi de → STOP ÖNCELİKLİ
        (konservatif, CLAUDE.md Bölüm 10). Döner: "STOP"|"TARGET"|None."""
        row = self._conn.execute(
            "SELECT quantity, stop_price, target_price FROM paper_brackets WHERE symbol=? AND active=1",
            (symbol,)).fetchone()
        if row is None:
            return None
        qty, stop, target = int(row[0]), float(row[1]), float(row[2])
        self.update_prices({symbol: last})
        if last <= stop:
            fill = stop * (1 - self.slippage_frac)  # slippage stop aleyhine
            self._apply_sell(symbol, qty)
            gross = fill * qty
            self._set_cash(self.cash + gross - gross * self.commission_frac)
            self._record_order(symbol, Side.SELL, qty, fill, gross * self.commission_frac, gross, "FILLED", "stop")
            self._conn.execute("UPDATE paper_brackets SET active=0 WHERE symbol=?", (symbol,))
            self._conn.commit()
            return "STOP"
        if last >= target:
            fill = target  # limit emir varsayımı (slippage yok)
            self._apply_sell(symbol, qty)
            gross = fill * qty
            self._set_cash(self.cash + gross - gross * self.commission_frac)
            self._record_order(symbol, Side.SELL, qty, fill, gross * self.commission_frac, gross, "FILLED", "target")
            self._conn.execute("UPDATE paper_brackets SET active=0 WHERE symbol=?", (symbol,))
            self._conn.commit()
            return "TARGET"
        return None

    def cancel_all_orders(self, symbol: str) -> None:
        self._conn.execute("UPDATE paper_brackets SET active=0 WHERE symbol=?", (symbol,))
        self._conn.commit()

    def get_open_orders(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT symbol, quantity, stop_price, target_price FROM paper_brackets WHERE active=1").fetchall()
        return [{"symbol": r[0], "quantity": r[1], "stop_price": r[2], "target_price": r[3]} for r in rows]

    # ------------------------------------------------------------------ ABC kalanı
    def get_bars(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        if self._history_store is None:
            raise BrokerError("PaperBroker.get_bars: history_store verilmedi (sinyal için LiveHistoryStore kullanın)")
        df = self._history_store.get_ohlcv(symbol)
        return df.tail(lookback)[["open", "high", "low", "close", "volume"]]

    def is_market_open(self) -> bool:
        if self._session_check is not None:
            return self._session_check()
        from core.clock import is_bist_session, now_utc
        return is_bist_session(now_utc())

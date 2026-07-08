# data/live_store.py
"""Canlı/paper için kalıcı yerel günlük tarihçe deposu (Faz 5, F5A-1).

NEDEN: regime_core kompozit sinyali MA(200) hesaplar — canlı döngü her gün en az
200+ günlük geçmişe ihtiyaç duyar. Bu depo o geçmişi kalıcı tutar (SQLite; CLAUDE.md
3.1 #4: "tek doğruluk kaynağı state SQLite'tadır"), A1 snapshot'ından bootstrap edilir
ve günlük EOD güncellemesiyle büyür.

F5-A KAPSAMI: kaynak-agnostik. Gerçek veri kaynağı (AlgoLab GetCandleData / yfinance)
F5-B'de `fetch_fn` ile bağlanır. Bu modül yalnızca DEPOLAMA + ÇAPRAZ-TUTARLILIK
mantığıdır; ağ çağrısı YOKTUR.

ÇAPRAZ-TUTARLILIK (madde 1): aynı sembol-gün için farklı kaynaklardan gelen kapanış
fiyatı eşik (%) üstünde ayrışırsa çakışma kaydedilir + WARN (o gün "şüpheli").

Tüm zaman damgaları UTC ISO string (Bölüm 5 / CLAUDE.md 2.5). Naive datetime yasak.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

DEFAULT_STORE = Path("runtime/live_history.sqlite")
CROSS_SOURCE_TOL_PCT = 0.005  # %0.5 — üstünde kapanış ayrışması = çakışma (şüpheli gün)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_bars (
    symbol TEXT NOT NULL,
    ts_utc TEXT NOT NULL,          -- barın kapanış anı, UTC ISO
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    source TEXT NOT NULL,          -- snapshot | algolab | yfinance | test
    suspect INTEGER NOT NULL DEFAULT 0,  -- çapraz-tutarlılık bayrağı
    created_at TEXT NOT NULL,
    PRIMARY KEY (symbol, ts_utc)
);
CREATE TABLE IF NOT EXISTS bar_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL, ts_utc TEXT NOT NULL,
    source_existing TEXT, close_existing REAL,
    source_incoming TEXT, close_incoming REAL,
    pct_diff REAL, detected_at TEXT NOT NULL
);
"""


@dataclass
class UpsertReport:
    inserted: int = 0
    updated: int = 0
    conflicts: int = 0
    unchanged: int = 0


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_utc_iso(ts) -> str:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        raise ValueError(f"naive datetime yasak — tzinfo zorunlu: {ts}")
    return t.tz_convert("UTC").isoformat()


class LiveHistoryStore:
    """Kalıcı günlük OHLCV deposu. Idempotent upsert + çapraz-kaynak tutarlılık."""

    def __init__(self, path: Path | str = DEFAULT_STORE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "LiveHistoryStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------ yazma
    def upsert_bars(self, symbol: str, df: pd.DataFrame, source: str,
                    tol_pct: float = CROSS_SOURCE_TOL_PCT) -> UpsertReport:
        """DataFrame (index=UTC DatetimeIndex, kolonlar open/high/low/close/volume) yaz.

        Idempotent: aynı (symbol, ts) yeniden gelirse ÇAPRAZ-TUTARLILIK kontrolü
        yapılır. Kapanış farkı tol_pct üstündeyse: çakışma kaydı + `suspect=1` +
        rapor. tol_pct altındaysa gelen kaynak yazılır (unchanged sayılır)."""
        rep = UpsertReport()
        now = _utcnow_iso()
        cur = self._conn.cursor()
        for ts, row in df.iterrows():
            ts_iso = _to_utc_iso(ts)
            existing = cur.execute(
                "SELECT close, source FROM daily_bars WHERE symbol=? AND ts_utc=?",
                (symbol, ts_iso),
            ).fetchone()
            close_in = None if pd.isna(row["close"]) else float(row["close"])
            if existing is None:
                cur.execute(
                    "INSERT INTO daily_bars (symbol, ts_utc, open, high, low, close, "
                    "volume, source, suspect, created_at) VALUES (?,?,?,?,?,?,?,?,0,?)",
                    (symbol, ts_iso, _f(row.get("open")), _f(row.get("high")),
                     _f(row.get("low")), close_in, _f(row.get("volume")), source, now),
                )
                rep.inserted += 1
                continue
            close_ex, source_ex = existing
            if close_ex is not None and close_in is not None and close_ex != 0:
                pct = abs(close_in - close_ex) / abs(close_ex)
                if pct > tol_pct and source_ex != source:
                    cur.execute(
                        "INSERT INTO bar_conflicts (symbol, ts_utc, source_existing, "
                        "close_existing, source_incoming, close_incoming, pct_diff, detected_at) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (symbol, ts_iso, source_ex, close_ex, source, close_in, pct, now),
                    )
                    cur.execute(
                        "UPDATE daily_bars SET suspect=1 WHERE symbol=? AND ts_utc=?",
                        (symbol, ts_iso),
                    )
                    rep.conflicts += 1
                    continue
            rep.unchanged += 1
        self._conn.commit()
        return rep

    def replace_bars(self, symbol: str, df: pd.DataFrame, source: str) -> int:
        """Bir sembolün TÜM barlarını sil + taze df ile değiştir (resync/force-overwrite,
        K4). Idempotent upsert'in aksine ÇAKIŞMAYI ÇÖZ = gelen değeri KABUL ET (yfinance
        temettü/split yeniden-düzeltmesi eski değerleri geçersiz kılar). Döner: yazılan satır."""
        now = _utcnow_iso()
        cur = self._conn.cursor()
        cur.execute("DELETE FROM daily_bars WHERE symbol=?", (symbol,))
        n = 0
        for ts, row in df.iterrows():
            close_in = None if pd.isna(row["close"]) else float(row["close"])
            cur.execute(
                "INSERT INTO daily_bars (symbol, ts_utc, open, high, low, close, volume, "
                "source, suspect, created_at) VALUES (?,?,?,?,?,?,?,?,0,?)",
                (symbol, _to_utc_iso(ts), _f(row.get("open")), _f(row.get("high")),
                 _f(row.get("low")), close_in, _f(row.get("volume")), source, now))
            n += 1
        self._conn.commit()
        return n

    def bootstrap_from_snapshot(self, snapshot_dir: Path | str, symbols: list[str],
                                start: Optional[str] = None) -> dict[str, UpsertReport]:
        """A1 snapshot (data/snapshots/<tarih>/<SEMBOL>.parquet) → depo. Kaynak='snapshot'."""
        snap = Path(snapshot_dir)
        out: dict[str, UpsertReport] = {}
        for sym in symbols:
            df = pd.read_parquet(snap / f"{sym}.parquet")
            if start is not None:
                df = df.loc[start:]
            out[sym] = self.upsert_bars(sym, df, source="snapshot")
        return out

    def eod_update(self, symbols: list[str], fetch_fn: Callable[[str, Optional[str]], pd.DataFrame],
                   source: str) -> dict[str, UpsertReport]:
        """Günlük EOD güncelleme ARAYÜZÜ (kaynak-agnostik). `fetch_fn(symbol, since_iso)`
        yeni barları döndürür (F5-B'de AlgoLab/yfinance'e bağlanır; F5-A'da test
        fixture'ı). since = deponun o semboldeki son barından sonrası (artımlı)."""
        out: dict[str, UpsertReport] = {}
        for sym in symbols:
            since = self.last_ts_iso(sym)
            df = fetch_fn(sym, since)
            if df is None or df.empty:
                out[sym] = UpsertReport()
                continue
            out[sym] = self.upsert_bars(sym, df, source=source)
        return out

    # ------------------------------------------------------------------ okuma
    def get_closes(self, symbol: str) -> pd.Series:
        rows = self._conn.execute(
            "SELECT ts_utc, close FROM daily_bars WHERE symbol=? AND close IS NOT NULL "
            "ORDER BY ts_utc", (symbol,),
        ).fetchall()
        if not rows:
            return pd.Series(dtype=float, name=symbol)
        idx = pd.to_datetime([r[0] for r in rows], utc=True)
        return pd.Series([r[1] for r in rows], index=idx, name=symbol)

    def get_closes_dict(self, symbols: list[str]) -> dict[str, pd.Series]:
        return {s: self.get_closes(s) for s in symbols}

    def get_ohlcv(self, symbol: str) -> pd.DataFrame:
        rows = self._conn.execute(
            "SELECT ts_utc, open, high, low, close, volume, suspect FROM daily_bars "
            "WHERE symbol=? ORDER BY ts_utc", (symbol,),
        ).fetchall()
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "suspect"])
        idx = pd.to_datetime([r[0] for r in rows], utc=True)
        df = pd.DataFrame(
            [r[1:] for r in rows], index=idx,
            columns=["open", "high", "low", "close", "volume", "suspect"],
        )
        df.index.name = "ts"
        return df

    def last_ts_iso(self, symbol: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT MAX(ts_utc) FROM daily_bars WHERE symbol=?", (symbol,),
        ).fetchone()
        return row[0] if row and row[0] else None

    def history_len(self, symbol: str) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM daily_bars WHERE symbol=? AND close IS NOT NULL", (symbol,),
        ).fetchone()[0]

    def ma_ready(self, symbols: list[str], ma_period: int) -> dict[str, bool]:
        """Her sembol için MA(ma_period) hesaplanabilir kadar geçmiş var mı."""
        return {s: self.history_len(s) >= ma_period for s in symbols}

    def conflicts(self) -> pd.DataFrame:
        rows = self._conn.execute(
            "SELECT symbol, ts_utc, source_existing, close_existing, source_incoming, "
            "close_incoming, pct_diff, detected_at FROM bar_conflicts ORDER BY detected_at",
        ).fetchall()
        return pd.DataFrame(rows, columns=[
            "symbol", "ts_utc", "source_existing", "close_existing", "source_incoming",
            "close_incoming", "pct_diff", "detected_at"])

    def suspect_days(self, symbol: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT ts_utc FROM daily_bars WHERE symbol=? AND suspect=1 ORDER BY ts_utc",
            (symbol,),
        ).fetchall()
        return [r[0] for r in rows]


def _f(v) -> Optional[float]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return None if pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return None

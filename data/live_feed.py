# data/live_feed.py
"""Canlı/paper veri beslemesi — yfinance EOD kaynağı (Faz 5, F5-B1 gölge mod).

NEDEN: F5-A'da `LiveHistoryStore` KAYNAK-AGNOSTİK bir iskeletti (fetch_fn ile
bağlanacaktı). Bu modül onu GERÇEK bir EOD kaynağına — yfinance'e — bağlar.
AlgoLab canlı entegrasyonu İPTAL edildi (broker 2025-12-31'de kapatıldı); F5-B2
`ManualExecutionAdapter` olarak yeniden tanımlandı. Gölge paper döngüsü EOD
stratejide broker'a muhtaç DEĞİLDİR — sinyal ve mark-to-market yalnızca günlük
kapanışlara ihtiyaç duyar, onları da yfinance verir.

CLEANING PARİTESİ (kritik, B5 ön şartı): backtest closes'ı `data/cleaning.py`
`load_and_clean_universe`'inden (normalize_bist_dates + evren-düzeyi ghost filtre)
geçer. Bu modül AYNI iki temizlik adımını canlı depoya da uygular — böylece
live-store'un beslediği `closes` backtest'in gördüğü closes'la NORMALIZE/FİLTRE
düzeyinde ÖZDEŞ olur (parite garantisi). Aksi halde 21:00-UTC vs UTC-gece-yarısı
etiket farkı ya da temizlenmemiş bir ghost bar canlı↔offline anahtarlama diff'i
üretirdi.

ÇAPRAZ-TUTARLILIK: snapshot ile örtüşen günlerde yfinance yeniden çekilir;
`LiveHistoryStore.upsert_bars` farklı kaynak + eşik-üstü kapanış farkı görürse
çakışma kaydeder + o günü "şüpheli" işaretler (madde 1 çapraz-veri raporu).

AĞ: yalnızca `fetch_raw_fn` gerçek yfinance'e gider. Testler bunu enjekte ederek
tamamen offline koşar (CLAUDE.md 7.4: ağa bağımlı test yasak).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from data.cleaning import filter_ghost_bars, normalize_bist_dates
from data.live_store import LiveHistoryStore, UpsertReport

# yfinance'ten çekerken snapshot ile örtüşen bir pencere bırak (çapraz-tutarlılık +
# ghost filtresinin prev_close bağlamı için). Takvim günü.
DEFAULT_OVERLAP_DAYS = 15
SNAPSHOT_SOURCE = "snapshot"
YF_SOURCE = "yfinance"


def yf_symbol(symbol: str) -> str:
    """BIST sembolü → yfinance sembolü (config/config.yaml instruments ile aynı kural)."""
    return f"{symbol}.IS"


def default_fetch_raw(yf_sym: str, start: Optional[str]) -> pd.DataFrame:
    """Gerçek yfinance çekimi (UTC-normalize kolonlar). `data.historical.download_bars`
    emsali; ağ ÇAĞRISI burada. Testlerde ENJEKTE edilir, çağrılmaz."""
    from data.historical import download_bars
    return download_bars(yf_sym, "1d", start=start)


@dataclass
class FeedReport:
    per_symbol: dict[str, UpsertReport] = field(default_factory=dict)
    ghost_removed: list[dict] = field(default_factory=list)
    no_data_symbols: list[str] = field(default_factory=list)

    def totals(self) -> dict[str, int]:
        ins = sum(r.inserted for r in self.per_symbol.values())
        upd = sum(r.updated for r in self.per_symbol.values())
        con = sum(r.conflicts for r in self.per_symbol.values())
        return {"inserted": ins, "updated": upd, "conflicts": con,
                "ghost_removed": len(self.ghost_removed)}


def clean_universe(raw: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """backtest ile AYNI iki adım: normalize_bist_dates (her sembol) + evren-düzeyi
    ghost filtre. `load_and_clean_universe`'in dict-girdili karşılığı."""
    normalized = {s: normalize_bist_dates(df) for s, df in raw.items()}
    return filter_ghost_bars(normalized)


class LiveDataFeed:
    """yfinance EOD kaynağını LiveHistoryStore'a bağlar (temizlik pariteli)."""

    def __init__(self, store: LiveHistoryStore, symbols: list[str],
                 fetch_raw_fn: Callable[[str, Optional[str]], pd.DataFrame] = default_fetch_raw,
                 overlap_days: int = DEFAULT_OVERLAP_DAYS,
                 logger: Optional[Callable[[str], None]] = None):
        self.store = store
        self.symbols = list(symbols)
        self.fetch_raw_fn = fetch_raw_fn
        self.overlap_days = overlap_days
        self._log = logger or (lambda m: None)

    # ------------------------------------------------------------------ bootstrap
    def bootstrap_from_snapshot(self, snapshot_dir: Path | str, start: Optional[str] = None
                                ) -> dict[str, UpsertReport]:
        """A1 snapshot → depo, AMA backtest-pariteli temizlikle (normalize + ghost).
        `LiveHistoryStore.bootstrap_from_snapshot` HAM saklar; bu ONUN YERİNE
        temizlenmiş barları saklar (parite ön şartı)."""
        from data.cleaning import load_and_clean_universe
        snap = Path(snapshot_dir)

        def _load(sym: str) -> pd.DataFrame:
            df = pd.read_parquet(snap / f"{sym}.parquet")
            if start is not None:
                df = df.loc[start:]
            return df

        cleaned, ghost = load_and_clean_universe(self.symbols, _load)
        out: dict[str, UpsertReport] = {}
        for sym in self.symbols:
            out[sym] = self.store.upsert_bars(sym, cleaned[sym], source=SNAPSHOT_SOURCE)
        if ghost:
            self._log(f"bootstrap: {len(ghost)} ghost bar elendi (backtest ile aynı)")
        return out

    # ------------------------------------------------------------------ EOD güncelleme
    def _fetch_universe_since(self) -> dict[str, pd.DataFrame]:
        """Her sembol için deponun son barından (overlap kadar geri) itibaren çek.
        Overlap: snapshot↔yfinance çapraz-tutarlılık + ghost prev_close bağlamı."""
        raw: dict[str, pd.DataFrame] = {}
        for sym in self.symbols:
            last = self.store.last_ts_iso(sym)
            if last is not None:
                start = (pd.Timestamp(last) - pd.Timedelta(days=self.overlap_days)).strftime("%Y-%m-%d")
            else:
                start = None
            df = self.fetch_raw_fn(yf_symbol(sym), start)
            raw[sym] = df if df is not None else pd.DataFrame()
        return raw

    def eod_update(self) -> FeedReport:
        """Gölge mod EOD işi: yfinance'ten güncel barları çek, backtest-pariteli
        temizle, depoya idempotent yaz. Snapshot ile örtüşen günlerde çapraz-
        tutarlılık `upsert_bars` içinde otomatik kontrol edilir.

        'Bar yok' (yfinance gecikmesi / tatil) sembol bazında zarafetle atlanır."""
        raw = self._fetch_universe_since()
        report = FeedReport()

        nonempty = {s: df for s, df in raw.items() if df is not None and not df.empty}
        report.no_data_symbols = [s for s in self.symbols if s not in nonempty]
        for s in report.no_data_symbols:
            self._log(f"EOD: {s} — yeni bar yok (yfinance gecikmesi/tatil) → atlanıyor")

        if not nonempty:
            return report

        cleaned, ghost = clean_universe(nonempty)
        report.ghost_removed = ghost
        for g in ghost:
            self._log(f"EOD: ghost bar elendi {g['symbol']} {g['date']}")

        for sym, df in cleaned.items():
            report.per_symbol[sym] = self.store.upsert_bars(sym, df, source=YF_SOURCE)
        return report

    # ------------------------------------------------------------------ kanıt / rapor
    def closes(self) -> dict[str, pd.Series]:
        return {s: self.store.get_closes(s) for s in self.symbols}

    def composite_readiness(self, ma_period: int) -> dict:
        """MA(ma_period) kompozitin BUGÜNKÜ değerine kadar hesaplanabildiğini kanıtla
        (madde 1). Döner: rapor sözlüğü — her sembol geçmiş uzunluğu, MA-hazır mı,
        kompozitin son tarihi + son değeri + son MA değeri."""
        from strategy.regime_core import build_composite

        closes = self.closes()
        ready = self.store.ma_ready(self.symbols, ma_period)
        hist_len = {s: self.store.history_len(s) for s in self.symbols}

        out = {
            "symbols": self.symbols,
            "ma_period": ma_period,
            "history_len": hist_len,
            "ma_ready": ready,
            "all_ready": all(ready.values()),
        }
        # Kompozit + MA yalnızca tüm seriler doluysa hesaplanır.
        if all(len(s) > 0 for s in closes.values()):
            composite, _fill = build_composite(closes)
            ma = composite.rolling(ma_period).mean()
            out["composite_last_date"] = str(composite.index[-1])
            out["composite_last_value"] = float(composite.iloc[-1])
            last_ma = ma.iloc[-1]
            out["ma_last_value"] = None if pd.isna(last_ma) else float(last_ma)
            out["composite_computable_to_today"] = not pd.isna(last_ma)
            out["composite_len"] = int(len(composite))
        else:
            out["composite_computable_to_today"] = False
        return out

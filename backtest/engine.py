# backtest/engine.py
from __future__ import annotations
import contextlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Optional

import pandas as pd

from core.models import AccountState, Position, SignalAction, TradeDecision
from indicators.engine import build_features
from risk.risk_engine import check_and_trip_breaker, historical_correlation, size_and_approve
from strategy.signal_engine import evaluate_entry, evaluate_exit


@contextlib.contextmanager
def _resolve_breaker_file(breaker_file: Optional[Path]) -> Iterator[Path]:
    """`breaker_file` verilmişse (walk-forward/sweep gibi run_backtest'i YÜZLERCE
    kez çağıran çağıranların, CLI çağrısı başına TEK bir geçici dizin açıp her
    çağrıya kendi dosya YOLUNU vermesi için — performans turu, v7) doğrudan onu
    kullanır, hiçbir dizin oluşturmaz/silmez. Verilmemişse (varsayılan, geriye
    dönük uyumlu davranış) eskisi gibi İZOLE bir geçici dizin açar ve döndükten
    sonra siler."""
    if breaker_file is not None:
        yield breaker_file
    else:
        with tempfile.TemporaryDirectory(prefix="backtest_breaker_") as tmp_dir:
            yield Path(tmp_dir) / "BREAKER_TRIPPED"


@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    quantity: int
    exit_reason: str  # "STOP" | "TARGET" | "SIGNAL_EXIT"
    pnl: float
    r_multiple: float


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    decision_log: list[dict] = field(default_factory=list)
    breaker_trips: list[dict] = field(default_factory=list)  # [{"date":..., "equity":..., "peak_equity":..., "drawdown":...}]


@dataclass
class _OpenPosition:
    symbol: str
    quantity: int
    entry_price: float
    entry_date: pd.Timestamp
    stop_price: float
    target_price: float
    cost_basis: float    # entry_price*qty + giriş komisyonu
    risk_amount: float   # per_share_risk * qty (R-multiple hesap referansı)


def _iso_week(ts: pd.Timestamp) -> tuple[int, int]:
    iso = ts.isocalendar()
    return (iso[0], iso[1])


def run_backtest(
    symbols: list[str],
    cfg,
    load_daily: Optional[Callable[[str], pd.DataFrame]] = None,
    initial_equity: Optional[float] = None,
    date_range: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None,
    precomputed_features: Optional[dict[str, pd.DataFrame]] = None,
    trace: Optional[list] = None,
    breaker_file: Optional[Path] = None,
    disabled_gates: Optional[list[str]] = None,
) -> BacktestResult:
    """Event-driven, bar-bazlı backtest motoru (Bölüm 12.2).

    Degrade mod: h4_df her zaman None geçilir — huni günlük kademelerle çalışır
    (Bölüm 8.2'nin ilk sınıf desteklediği mod). Gerçek 4H entegrasyonu, günlük/4H
    zaman damgası hizalamasının ek karmaşıklığı ve look-ahead riski nedeniyle
    sonraki bir iyileştirmeye bırakıldı (STATUS.md'de gerekçelendirildi).

    Look-ahead yasağı (Bölüm 12.3): sinyal t barının kapanışıyla hesaplanır;
    yeni giriş/çıkış fill'i en erken t+1 barının açılışındadır. Stop/target
    intrabar fill'leri yalnızca pozisyon zaten mevcutken, o barın high/low'una
    karşı kontrol edilir — gelecek veri kullanılmaz.

    `date_range`: verilirse SİMÜLASYON yalnızca bu (start, end] aralığındaki
    barlarla ilerler, ama `build_features` (ve dolayısıyla warm-up) her zaman
    `load_daily`/`precomputed_features`'ın verdiği TAM tarihçe üzerinden
    hesaplanır — bu yüzden `min_history_bars` kontrolü, dilimlenmiş pencereye
    değil tam tarihçedeki mutlak konuma göre uygulanır. Bir test dilimindeki
    gün, kendinden önceki tam tarihçeyi (train dönemi dahil) warm-up olarak
    kullanabilir — bu look-ahead değildir, yalnızca geçmişe bakar (walk-forward
    OOS pencerelerinin gerçek warm-up'a sahip olması için gereklidir).

    `precomputed_features`: verilirse `build_features` tekrar çağrılmaz —
    walk-forward'ın aynı fiyat verisini farklı risk/stop eşikleriyle (indikatör
    hesaplamasını ETKİLEMEYEN parametreler) defalarca koşturması gerektiğinde
    performans için kullanılır.

    `trace`: verilirse (bir liste), her gün için salt-okunur bir teşhis kaydı
    (tarih, cash, equity, breaker kontrolüne giden peak_equity, breaker
    tetiklendi mi, açık pozisyonların anlık notional değerleri) bu listeye
    eklenir. Hiçbir hesaplamayı DEĞİŞTİRMEZ — yalnızca zaten hesaplanan
    değerleri gözlemler (DIAGNOSTICS_v6.md, Paket 1).

    `breaker_file`: verilmezse (varsayılan) bu çağrı kendi İZOLE geçici dizinini
    açar/siler (eski davranış — tek çağrılık kullanımlar için doğru ve basit).
    Walk-forward/sweep gibi run_backtest'i YÜZLERCE kez art arda çağıran
    çağıranlar performans için KENDİ paylaşılan geçici dizinlerini bir kez açıp
    her çağrıya İÇİNDE farklı bir dosya YOLU vermelidir (breaker durumu yine
    çağrılar arasında İZOLE kalır — yalnızca dizin oluşturma/silme yükü tek
    seferde ödenir). Bkz. `backtest/cli.py::generate_report` (v7 performans turu).

    `disabled_gates`: verilirse (read-only portföy-ablasyon turu amaçlı —
    ASLA üretim/paper/real modda kullanılmaz, `main.py`/`PaperBroker` bu
    parametreyi hiç geçmez), listelenen isimdeki gate'ler `evaluate_entry`
    içinde otomatik PASS sayılır (bkz. `strategy/signal_engine.py::GATE_NAMES`).
    Verilmezse (None, varsayılan) davranış BİREBİR aynıdır — kanıt:
    `tests/test_backtest_engine.py::test_disabled_gates_none_is_byte_identical_to_baseline`.
    """
    initial_equity = initial_equity if initial_equity is not None else cfg.backtest.initial_equity
    disabled_gates_set = set(disabled_gates) if disabled_gates else None

    if precomputed_features is not None:
        daily_features = precomputed_features
    else:
        daily_features = {s: build_features(load_daily(s), cfg) for s in symbols}
    min_history = cfg.signal.min_history_bars

    non_empty = []
    for df in daily_features.values():
        if len(df) <= min_history:
            continue
        eligible = df.index[min_history:]  # tam tarihçedeki mutlak konuma göre
        if date_range is not None:
            start, end = date_range
            eligible = eligible[(eligible >= start) & (eligible < end)]
        non_empty.append(eligible)
    all_dates = sorted(set().union(*non_empty)) if non_empty else []

    cash = initial_equity
    positions: dict[str, _OpenPosition] = {}
    trades: list[Trade] = []
    equity_points: list[tuple[pd.Timestamp, float]] = []
    decision_log: list[dict] = []
    breaker_trips: list[dict] = []
    last_known_close: dict[str, float] = {}

    peak_equity = initial_equity
    trade_pnls: list[tuple[pd.Timestamp, float]] = []
    breaker_was_tripped = False

    pending_exits: set[str] = set()
    pending_entries: dict[str, TradeDecision] = {}

    def _closed_pnls_on(date: pd.Timestamp) -> float:
        return sum(pnl for d, pnl in trade_pnls if d == date)

    def _closed_pnls_this_week(date: pd.Timestamp) -> float:
        wk = _iso_week(date)
        return sum(pnl for d, pnl in trade_pnls if _iso_week(d) == wk)

    def _make_corr_fn(as_of: pd.Timestamp):
        def _loader(sym: str) -> pd.Series:
            return daily_features[sym]["close"].loc[:as_of]

        def _corr(symbol: str, open_positions: list[Position]) -> float:
            return historical_correlation(symbol, open_positions, _loader, cfg.risk.correlation_lookback_days)

        return _corr

    # Breaker durumu her run_backtest çağrısı için İZOLE bir geçici dosyada tutulur —
    # paper/real modun paylaştığı gerçek runtime/BREAKER_TRIPPED dosyasına DOKUNULMAZ
    # (aksi halde eşzamanlı backtest koşuları veya bir canlı bot birbirinin breaker
    # durumunu kirletirdi). Kullanılan fonksiyon (check_and_trip_breaker/
    # size_and_approve) paper/real ile BİREBİR AYNI — yalnızca dosya yolu farklı.
    with _resolve_breaker_file(breaker_file) as breaker_file:

        for date in all_dates:
            # Fiyat önbelleğini bugün verisi olan sembollerle güncelle. `all_dates`
            # sembollerin BİRLEŞİMİ olduğundan (bkz. yukarıdaki yorum), bazı günler
            # yalnızca BİR sembolde veri bulunabilir (örn. bir veri artefaktı/tatil
            # uyuşmazlığı) — bu durumda diğer sembollerin equity katkısı, o günkü
            # (yok) fiyat yerine SON BİLİNEN kapanışla taşınır (0 SAYILMAZ). Bu,
            # DIAGNOSTICS_v6.md Paket 1'de bulunan equity-sıfırlama bug'ının
            # düzeltmesidir.
            for s, df in daily_features.items():
                if date in df.index:
                    last_known_close[s] = float(df.loc[date]["close"])

            # --- 0. Önceki barın sinyaliyle planlanmış işlemleri BUGÜNÜN açılışında doldur ---
            # `pending_exits` bir set olduğundan, Python'ın string hash'leri
            # PYTHONHASHSEED'e göre süreç başına RASTGELELEŞTİRİLDİĞİNDEN,
            # sorted() OLMADAN iterasyon aynı veriyle bile İKİ AYRI SÜREÇ
            # ÇALIŞTIRMASI arasında farklı sırada trade üretebilirdi (finansal
            # sonuç aynı kalır, yalnızca aynı güne denk gelen birden fazla
            # çıkışın trades.csv'deki SIRASI değişirdi — CLAUDE.md Bölüm 12.8'in
            # "aynı komut iki koşuda bit-bit aynı çıktı" şartını ihlal ederdi).
            # Deterministik alfabetik sıra, giriş huninin (sorted(symbols)) v7
            # düzeltmesiyle tutarlı.
            for symbol in sorted(pending_exits):
                df = daily_features[symbol]
                if symbol in positions and date in df.index:
                    bar = df.loc[date]
                    pos = positions[symbol]
                    fill_price = float(bar["open"]) * (1 - cfg.costs.slippage_bps / 1e4)
                    commission = fill_price * pos.quantity * cfg.costs.commission_bps / 1e4
                    proceeds = fill_price * pos.quantity - commission
                    pnl = proceeds - pos.cost_basis
                    cash += proceeds
                    trades.append(Trade(symbol, pos.entry_date, pos.entry_price, date, fill_price,
                                        pos.quantity, "SIGNAL_EXIT", pnl,
                                        pnl / pos.risk_amount if pos.risk_amount else 0.0))
                    trade_pnls.append((date, pnl))
                    del positions[symbol]
            pending_exits.clear()

            for symbol, decision in list(pending_entries.items()):
                df = daily_features[symbol]
                if symbol not in positions and date in df.index:
                    bar = df.loc[date]
                    fill_price = float(bar["open"]) * (1 + cfg.costs.slippage_bps / 1e4)
                    commission = fill_price * decision.quantity * cfg.costs.commission_bps / 1e4
                    cost = fill_price * decision.quantity + commission
                    if cost <= cash:
                        cash -= cost
                        per_share_risk = fill_price - decision.stop_price
                        positions[symbol] = _OpenPosition(
                            symbol=symbol, quantity=decision.quantity, entry_price=fill_price,
                            entry_date=date, stop_price=decision.stop_price, target_price=decision.target_price,
                            cost_basis=cost, risk_amount=per_share_risk * decision.quantity,
                        )
            pending_entries.clear()

            # --- 1. Açık pozisyonlar için stop/target intrabar kontrolü (bugünün high/low'u) ---
            for symbol in list(positions.keys()):
                df = daily_features[symbol]
                if date not in df.index:
                    continue
                pos = positions[symbol]
                bar = df.loc[date]
                hit_stop = bar["low"] <= pos.stop_price
                hit_target = bar["high"] >= pos.target_price
                if hit_stop or hit_target:
                    if hit_stop:  # STOP ÖNCELİKLİ (Bölüm 12.2)
                        fill_price = pos.stop_price * (1 - cfg.costs.slippage_bps / 1e4)
                        reason = "STOP"
                    else:
                        fill_price = pos.target_price  # limit emir varsayımı, slippage yok
                        reason = "TARGET"
                    commission = fill_price * pos.quantity * cfg.costs.commission_bps / 1e4
                    proceeds = fill_price * pos.quantity - commission
                    pnl = proceeds - pos.cost_basis
                    cash += proceeds
                    trades.append(Trade(symbol, pos.entry_date, pos.entry_price, date, fill_price,
                                        pos.quantity, reason, pnl,
                                        pnl / pos.risk_amount if pos.risk_amount else 0.0))
                    trade_pnls.append((date, pnl))
                    del positions[symbol]

            # --- 2. Açık pozisyonlar için çıkış sinyali (t+1 açılışında çıkış planla) ---
            for symbol, pos in list(positions.items()):
                df = daily_features[symbol]
                if date not in df.index:
                    continue
                idx_pos = df.index.get_loc(date)
                window = df.iloc[: idx_pos + 1]
                sig = evaluate_exit(symbol, window, cfg)
                if sig.action == SignalAction.EXIT_LONG:
                    pending_exits.add(symbol)

            # --- 3. Pozisyonsuz semboller için giriş sinyali (t+1 açılışında giriş planla) ---
            # last_known_close her açık pozisyon için garantilidir: bir pozisyon yalnızca
            # date in df.index olan bir günde açılabildiğinden (bkz. giriş fill bloğu),
            # last_known_close en azından giriş günündeki fiyatla önceden doldurulmuştur.
            equity_today = cash + sum(
                last_known_close[s] * p.quantity for s, p in positions.items()
            )

            acct = AccountState(
                equity=equity_today, cash=cash,
                positions=[
                    Position(s, p.quantity, p.entry_price, p.stop_price, p.target_price, p.entry_date)
                    for s, p in positions.items()
                ],
                peak_equity=peak_equity,
                realized_pnl_today=_closed_pnls_on(date),
                realized_pnl_week=_closed_pnls_this_week(date),
            )
            # Paper/real modun her kararsal döngüde yapacağının AYNISI: equity/peak'i
            # breaker eşiğine karşı kontrol et. Tetiklenirse dosya yazılır ve
            # size_and_approve aşağıda bunu okuyup DRAWDOWN_BREAKER ile reddeder —
            # bu andan itibaren backtest boyunca hiçbir yeni giriş onaylanmaz.
            is_tripped_now = check_and_trip_breaker(acct, cfg, breaker_file=breaker_file)
            if is_tripped_now and not breaker_was_tripped:
                drawdown = 1 - (acct.equity / acct.peak_equity) if acct.peak_equity > 0 else 0.0
                breaker_trips.append({
                    "date": date, "equity": acct.equity, "peak_equity": acct.peak_equity,
                    "drawdown": drawdown,
                })
            breaker_was_tripped = is_tripped_now

            if trace is not None:
                trace.append({
                    "date": date,
                    "cash": cash,
                    "equity": equity_today,
                    "peak_equity_seen_by_breaker": peak_equity,  # bugünün güncellemesinden ÖNCEKİ peak
                    "drawdown_seen_by_breaker": (1 - equity_today / peak_equity) if peak_equity > 0 else 0.0,
                    "breaker_tripped_today": is_tripped_now,
                    "positions": {
                        s: {
                            "quantity": p.quantity,
                            "close": last_known_close[s],
                            "notional": last_known_close[s] * p.quantity,
                            "price_is_stale": date not in daily_features[s].index,
                            "entry_price": p.entry_price,
                            "entry_date": p.entry_date,
                        }
                        for s, p in positions.items()
                    },
                })

            corr_fn = _make_corr_fn(date)
            # Bugün içinde onaylanan (ama henüz t+1 açılışında dolmamış) adaylar
            # bu listeye HEMEN eklenir — böylece aynı gün değerlendirilen sonraki
            # adaylar, o an SANKİ pozisyon zaten açılmış gibi doğru
            # max_open_positions/korelasyon durumunu görür (DIAGNOSTICS_v6.md
            # Paket 1, "aynı-gün-çoklu-onay" bug'ı: önceden her aday, günün
            # BAŞINDAKİ sabit `acct` snapshot'ına karşı bağımsız değerlendirilip
            # limit dolu olsa bile birden fazla aday onaylanabiliyordu).
            positions_snapshot: list[Position] = [
                Position(s, p.quantity, p.entry_price, p.stop_price, p.target_price, p.entry_date)
                for s, p in positions.items()
            ]
            # Aday değerlendirme sırası DETERMİNİSTİK (alfabetik sembol sırası).
            # Faz 5'in canlı/paper döngüsü de AYNI sırayı kullanmalı — aksi halde
            # backtest'in "kim önce onaylanır" davranışı canlıda tekrarlanamaz.
            for symbol in sorted(symbols):
                if symbol in positions or symbol in pending_entries:
                    continue
                df = daily_features[symbol]
                if date not in df.index:
                    continue
                idx_pos = df.index.get_loc(date)
                window = df.iloc[: idx_pos + 1]
                if len(window) < min_history:
                    continue
                sig = evaluate_entry(symbol, window, None, cfg, disabled_gates=disabled_gates_set)
                decision_log.append({"date": date, "symbol": symbol, "action": sig.action.value, "mode": "degrade"})
                if sig.action != SignalAction.ENTER_LONG:
                    continue
                acct_today = AccountState(
                    equity=equity_today, cash=cash,
                    positions=positions_snapshot,
                    peak_equity=peak_equity,
                    realized_pnl_today=_closed_pnls_on(date),
                    realized_pnl_week=_closed_pnls_this_week(date),
                )
                decision = size_and_approve(sig, acct_today, cfg, corr_fn, breaker_file=breaker_file)
                if decision.approved:
                    pending_entries[symbol] = decision
                    positions_snapshot.append(
                        Position(symbol, decision.quantity, sig.entry_ref_price,
                                decision.stop_price, decision.target_price, date)
                    )

            # --- 4. Equity snapshot ---
            peak_equity = max(peak_equity, equity_today)
            equity_points.append((date, equity_today))

    equity_curve = pd.Series(dict(equity_points)).sort_index() if equity_points else pd.Series(dtype=float)
    return BacktestResult(
        trades=trades, equity_curve=equity_curve, decision_log=decision_log, breaker_trips=breaker_trips,
    )

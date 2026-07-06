from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backtest.engine import run_backtest
from strategy.signal_engine import evaluate_entry
from core.models import SignalAction


def make_cfg(commission_bps=0.0, slippage_bps=0.0, initial_equity=100_000.0,
            risk_per_trade_pct=0.02, max_position_notional_pct=1.0,
            max_open_positions=2, min_rr=1.2, correlation_max=0.99):
    signal = SimpleNamespace(
        ema_fast=5, ema_slow=10, adx_period=5, adx_min=10,
        rsi_period=7, rsi_entry_low=35, rsi_entry_high=65,
        macd=(3, 6, 3), atr_period=5, atr_stop_mult=1.5, atr_anomaly_mult=3.0,
        bb_period=7, bb_std=2.0, swing_lookback=10, swing_fractal_n=1,
        volume_confirm_mult=1.0, min_history_bars=15,
    )
    risk = SimpleNamespace(
        risk_per_trade_pct=risk_per_trade_pct,
        daily_loss_limit_pct=0.5, weekly_loss_limit_pct=0.5,
        max_open_positions=max_open_positions, max_position_notional_pct=max_position_notional_pct,
        max_drawdown_breaker_pct=0.5, min_rr=min_rr,
        correlation_lookback_days=90, correlation_max=correlation_max, news_blackout=False,
    )
    costs = SimpleNamespace(commission_bps=commission_bps, slippage_bps=slippage_bps)
    backtest = SimpleNamespace(initial_equity=initial_equity)
    safety = SimpleNamespace(kill_switch_file="runtime/__nonexistent_kill_switch_for_tests__")
    return SimpleNamespace(signal=signal, risk=risk, costs=costs, backtest=backtest, safety=safety)


def _pretrigger_bars(seed: int = 13, n: int = 45) -> pd.DataFrame:
    """Bölüm 12'nin test setup'ı için: bu tam dizi (seed=13, n=45), make_cfg()'nin
    varsayılan gevşetilmiş eşikleriyle çalıştırıldığında 10 gate'in TAMAMINI
    PASS ettirip son barında ENTER_LONG üretir (deneysel olarak doğrulandı)."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.15, 1.0, n - 1)
    close = np.concatenate([[100.0], 100 + np.cumsum(steps)])
    close[-1] = close[-2] + abs(rng.normal(2.5, 0.5))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) + 0.3
    low = np.minimum(open_, close) - 0.3
    open_[-1] = close[-2] - 0.1
    high[-1] = close[-1] + 0.3
    low[-1] = open_[-1] - 0.2
    volume = np.full(n, 1000.0)
    volume[-1] = 3000.0
    idx = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def _extend(df: pd.DataFrame, extra_rows: list[dict]) -> pd.DataFrame:
    idx = pd.date_range(df.index[-1] + pd.Timedelta(days=1), periods=len(extra_rows), freq="1D", tz="UTC")
    extra = pd.DataFrame(extra_rows, index=idx)
    return pd.concat([df, extra])


def test_pretrigger_series_produces_enter_long_signal():
    """Sanity: sentetik dizinin gerçekten ENTER_LONG ürettiğini doğrular
    (backtest testlerinin geri kalanının dayandığı önkoşul)."""
    cfg = make_cfg()
    df = _pretrigger_bars()
    from indicators.engine import build_features
    feat = build_features(df, cfg)
    sig = evaluate_entry("TEST", feat, None, cfg)
    assert sig.action == SignalAction.ENTER_LONG
    assert sig.suggested_stop < sig.entry_ref_price < sig.suggested_target


# --- Look-ahead yasağı (Bölüm 12.3): sinyal barının kapanışıyla aynı günde fill yok ---

def test_entry_fills_at_t_plus_1_open_not_signal_bar():
    cfg = make_cfg()
    base = _pretrigger_bars()
    df = _extend(base, [
        dict(open=120.0, high=120.5, low=119.5, close=120.0, volume=1000.0),  # t+1: giriş burada dolar
        dict(open=120.0, high=130.0, low=119.0, close=125.0, volume=1000.0),  # target'a değip pozisyonu kapatır
    ])
    result = run_backtest(["TEST"], cfg, lambda s: df)
    assert len(result.trades) == 1
    trade = result.trades[0]
    entry_day_index = df.index.get_loc(trade.entry_date)
    signal_day_index = df.index.get_loc(base.index[-1])
    assert entry_day_index == signal_day_index + 1, "giriş, sinyal barından bir sonraki barda olmalı"
    # slippage=0 olduğundan giriş fiyatı tam olarak t+1'in açılışı olmalı
    assert trade.entry_price == pytest.approx(120.0)


def test_decision_log_records_signal_on_bar_before_entry():
    cfg = make_cfg()
    base = _pretrigger_bars()
    df = _extend(base, [
        dict(open=120.0, high=120.5, low=119.5, close=120.0, volume=1000.0),
        dict(open=120.0, high=130.0, low=119.0, close=125.0, volume=1000.0),
    ])
    result = run_backtest(["TEST"], cfg, lambda s: df)
    signal_bar_date = base.index[-1]
    enter_logs = [d for d in result.decision_log if d["symbol"] == "TEST" and d["action"] == "ENTER_LONG"]
    assert len(enter_logs) == 1
    assert enter_logs[0]["date"] == signal_bar_date
    assert result.trades[0].entry_date != signal_bar_date


# --- Fill mekaniği: stop / target / stop-önceliği ---

def test_target_hit_records_trade_with_exact_target_price_no_slippage():
    cfg = make_cfg()
    base = _pretrigger_bars()
    df = _extend(base, [
        dict(open=120.0, high=120.5, low=119.5, close=120.0, volume=1000.0),  # giriş günü, sakin
        dict(open=120.0, high=130.0, low=119.0, close=125.0, volume=1000.0),  # target'a ulaşır
    ])
    result = run_backtest(["TEST"], cfg, lambda s: df)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "TARGET"
    entry_sig_target = None
    from indicators.engine import build_features
    feat = build_features(base, cfg)
    entry_sig_target = evaluate_entry("TEST", feat, None, cfg).suggested_target
    assert trade.exit_price == pytest.approx(entry_sig_target)


def test_stop_hit_applies_slippage_against_position():
    cfg = make_cfg(slippage_bps=10.0)
    base = _pretrigger_bars()
    from indicators.engine import build_features
    feat = build_features(base, cfg)
    stop_price = evaluate_entry("TEST", feat, None, cfg).suggested_stop
    df = _extend(base, [
        dict(open=120.0, high=120.5, low=119.5, close=120.0, volume=1000.0),
        dict(open=118.0, high=118.5, low=stop_price - 1.0, close=117.0, volume=1000.0),
    ])
    result = run_backtest(["TEST"], cfg, lambda s: df)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "STOP"
    expected_fill = stop_price * (1 - 10.0 / 1e4)
    assert trade.exit_price == pytest.approx(expected_fill)
    assert trade.exit_price < stop_price  # slippage pozisyon aleyhine


def test_stop_priority_when_both_hit_same_bar():
    cfg = make_cfg()
    base = _pretrigger_bars()
    from indicators.engine import build_features
    feat = build_features(base, cfg)
    sig = evaluate_entry("TEST", feat, None, cfg)
    stop_price, target_price = sig.suggested_stop, sig.suggested_target
    df = _extend(base, [
        dict(open=120.0, high=120.5, low=119.5, close=120.0, volume=1000.0),  # giriş günü
        # ertesi gün: hem stop hem target aynı bar içinde teorik olarak vurulabilir
        dict(open=120.0, high=target_price + 5, low=stop_price - 5, close=120.0, volume=1000.0),
    ])
    result = run_backtest(["TEST"], cfg, lambda s: df)
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "STOP"  # Bölüm 12.2: STOP ÖNCELİKLİ


# --- Determinizm (Bölüm 12.8): aynı komut iki kez -> bit-bit aynı sonuç ---

def test_backtest_is_deterministic_across_runs():
    cfg = make_cfg()
    base = _pretrigger_bars()
    df = _extend(base, [
        dict(open=120.0, high=130.0, low=119.0, close=125.0, volume=1000.0),
        dict(open=125.0, high=126.0, low=124.0, close=125.5, volume=1000.0),
    ])
    r1 = run_backtest(["TEST"], cfg, lambda s: df)
    r2 = run_backtest(["TEST"], cfg, lambda s: df)
    assert r1.equity_curve.equals(r2.equity_curve)
    assert len(r1.trades) == len(r2.trades)
    for t1, t2 in zip(r1.trades, r2.trades):
        assert t1 == t2


# --- Komisyon uygulanıyor mu ---

def test_commission_reduces_pnl():
    cfg_no_fee = make_cfg(commission_bps=0.0)
    cfg_with_fee = make_cfg(commission_bps=50.0)  # %0.5
    base = _pretrigger_bars()
    df = _extend(base, [
        dict(open=120.0, high=130.0, low=119.0, close=125.0, volume=1000.0),
    ])
    r_no_fee = run_backtest(["TEST"], cfg_no_fee, lambda s: df)
    r_with_fee = run_backtest(["TEST"], cfg_with_fee, lambda s: df)
    assert r_with_fee.trades[0].pnl < r_no_fee.trades[0].pnl


def test_empty_symbol_list_returns_empty_result():
    cfg = make_cfg()
    result = run_backtest([], cfg, lambda s: pd.DataFrame())
    assert result.trades == []
    assert result.equity_curve.empty


# --- date_range / precomputed_features: walk-forward test-harness düzeltmesi ---
# (Faz 4 revizyon v3: walk-forward'ın OOS pencereleri, kendi veri dilimi üzerinde
# build_features'ı sıfırdan hesapladığı için hiç trade üretemiyordu — test dilimi
# min_history_bars'tan kısaydı. Düzeltme: build_features tam tarihçede bir kez
# hesaplanır, min_history_bars kontrolü tam tarihçedeki mutlak konuma göre yapılır,
# date_range yalnızca hangi barların SİMÜLE edileceğini kısıtlar.)

def test_date_range_restricts_simulation_but_uses_full_history_for_warmup():
    """Kendi başına min_history_bars'tan (15) çok daha kısa bir pencerede
    (yalnızca 3 gün) bile, öncesindeki tam tarihçe warm-up olarak kullanıldığından
    bir trade üretilebildiğini kanıtlar — walk-forward'ın 6 aylık test dilimlerinin
    artık gerçekten trade üretebilmesinin temeli budur."""
    cfg = make_cfg()
    base = _pretrigger_bars()  # 45 bar, son barda (index 44) ENTER_LONG sinyali üretir
    full_df = _extend(base, [
        dict(open=120.0, high=120.5, low=119.5, close=120.0, volume=1000.0),  # t+1: giriş dolar
        dict(open=120.0, high=130.0, low=119.0, close=125.0, volume=1000.0),  # target'a değer
    ])

    narrow_start = base.index[-1]                          # tam olarak sinyal barının tarihi
    narrow_end = full_df.index[-1] + pd.Timedelta(days=1)   # son devam barını da kapsa

    narrow_window_len = len(full_df.loc[narrow_start:])
    assert narrow_window_len < cfg.signal.min_history_bars, "pencere kendi başına yetersiz olmalı"

    result = run_backtest(["TEST"], cfg, lambda s: full_df, date_range=(narrow_start, narrow_end))
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "TARGET"
    assert trade.entry_date == full_df.index[-2]  # sinyal barından bir sonraki gün


def test_date_range_with_insufficient_full_history_produces_no_trades():
    """Kontrast testi: tam tarihçe de kısaysa (min_history_bars'ı hiç aşmıyorsa),
    date_range verilse bile hiç trade üretilmemeli — düzeltme warm-up şartını
    ortadan kaldırmıyor, yalnızca nereden sayılacağını düzeltiyor."""
    cfg = make_cfg()
    short_df = _pretrigger_bars(n=10)  # min_history_bars=15'ten az
    result = run_backtest(["TEST"], cfg, lambda s: short_df,
                          date_range=(short_df.index[0], short_df.index[-1] + pd.Timedelta(days=1)))
    assert result.trades == []


def test_precomputed_features_used_instead_of_recomputing():
    """precomputed_features verildiğinde load_daily hiç çağrılmamalı (walk-forward'ın
    aynı fiyat verisini 27 kombinasyon × onlarca pencerede tekrar tekrar
    build_features'tan geçirmemesi için performans kritik)."""
    from indicators.engine import build_features

    cfg = make_cfg()
    base = _pretrigger_bars()
    features = {"TEST": build_features(base, cfg)}

    def _loader(s):
        raise AssertionError("precomputed_features verilmişken load_daily çağrılmamalı")

    result = run_backtest(["TEST"], cfg, _loader, precomputed_features=features)
    assert len(result.equity_curve) > 0


# --- Breaker entegrasyonu (HARDENING.md harness düzeltme turu) ---

def test_breaker_trips_on_correct_bar_and_blocks_subsequent_entries():
    """Sentetik equity serisi: ilk pattern (seed=13) ENTER_LONG üretir, hemen
    ardından büyük bir düşüş bu pozisyonu STOP ile kapatır ve breaker'ı
    (kasıtlı olarak sıkı bir eşikle) tetikler. İkinci bir pattern (seed=1,
    fiyat seviyesi kaydırılmış) kendi başına yine geçerli bir ENTER_LONG
    üretir (decision_log ile kanıtlanır) — ama breaker tetiklendiği için
    HİÇBİR yeni pozisyon açılmamalı."""
    cfg = make_cfg()
    cfg.risk.max_drawdown_breaker_pct = 0.01  # tek stop-loss'un bile aşacağı kadar sıkı (test amaçlı)

    base1 = _pretrigger_bars(seed=13)  # ENTER_LONG üretir (entry~116.88, stop~114.31)
    # Ertesi gün açılışı sinyal barının kapanışına yakın (gerçekçi devam), ama
    # gün içi düşük stop seviyesinin (114.31) altına iniyor -> STOP, gerçek/temiz
    # bir zarar (aşırı gap değil, simülatörün "stop seviyesinden doldur" varsayımı
    # gerçekçi kalıyor).
    stop_bar = pd.DataFrame([
        dict(open=116.5, high=117.0, low=110.0, close=112.0, volume=1000.0),
    ], index=pd.date_range(base1.index[-1] + pd.Timedelta(days=1), periods=1, freq="1D", tz="UTC"))

    base2 = _pretrigger_bars(seed=1, n=45)
    shift = 112.0 - base2["close"].iloc[0]
    base2_shifted = base2.copy()
    for col in ["open", "high", "low", "close"]:
        base2_shifted[col] = base2_shifted[col] + shift
    base2_shifted.index = pd.date_range(
        stop_bar.index[-1] + pd.Timedelta(days=1), periods=len(base2_shifted), freq="1D", tz="UTC"
    )

    full_df = pd.concat([base1, stop_bar, base2_shifted])
    result = run_backtest(["TEST"], cfg, lambda s: full_df)

    # 1. İlk (ve TEK) trade STOP ile kapanmış olmalı
    assert len(result.trades) == 1
    first_trade = result.trades[0]
    assert first_trade.exit_reason == "STOP"

    # 2. Breaker, stop-loss'un gerçekleştiği barda tetiklenmiş olmalı
    assert len(result.breaker_trips) == 1
    assert result.breaker_trips[0]["date"] == first_trade.exit_date
    assert result.breaker_trips[0]["drawdown"] >= cfg.risk.max_drawdown_breaker_pct

    # 3. İkinci desen (seed=1) kendi başına geçerli bir ENTER_LONG sinyali
    #    ürettiğini decision_log'da kanıtlıyoruz...
    enter_signals_after_trip = [
        d for d in result.decision_log
        if d["action"] == "ENTER_LONG" and d["date"] > first_trade.exit_date
    ]
    assert len(enter_signals_after_trip) >= 1, "ikinci desen bir ENTER_LONG sinyali üretmeli (aksi halde test anlamsız)"

    # ...ama breaker tetiklendiği için bu sinyal hiçbir yeni pozisyona dönüşmemiş olmalı
    assert len(result.trades) == 1  # hâlâ yalnızca ilk (stop'lanan) trade var


def test_trace_hook_does_not_change_results_and_captures_expected_fields():
    """trace parametresi salt-okunur bir gözlem kancasıdır — verilmesi backtest
    sonucunu (trades/equity_curve) hiçbir şekilde değiştirmemeli (DIAGNOSTICS_v6.md
    Paket 1 için eklendi)."""
    cfg = make_cfg()
    base = _pretrigger_bars()
    df = _extend(base, [
        dict(open=120.0, high=130.0, low=119.0, close=125.0, volume=1000.0),
    ])

    result_without_trace = run_backtest(["TEST"], cfg, lambda s: df)

    trace: list = []
    result_with_trace = run_backtest(["TEST"], cfg, lambda s: df, trace=trace)

    assert result_without_trace.equity_curve.equals(result_with_trace.equity_curve)
    assert len(result_without_trace.trades) == len(result_with_trace.trades)

    assert len(trace) == len(result_with_trace.equity_curve)
    last_entry = trace[-1]
    assert set(["date", "cash", "equity", "peak_equity_seen_by_breaker",
               "drawdown_seen_by_breaker", "breaker_tripped_today", "positions"]) <= set(last_entry.keys())

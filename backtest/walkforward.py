# backtest/walkforward.py
from __future__ import annotations
import copy
import dataclasses
from dataclasses import dataclass, field
from itertools import product
from typing import Callable

import pandas as pd

from backtest.engine import Trade, run_backtest
from backtest.metrics import Metrics, compute_metrics

# Bölüm 12.7: overfitting'e karşı bilinçli dar grid — yalnızca bu 3 parametre taranır.
SWEEP_GRID: dict[str, list[float]] = {
    "atr_stop_mult": [1.25, 1.5, 2.0],
    "adx_min": [15, 20, 25],
    "min_rr": [1.5, 1.8, 2.2],
}
SWEEP_KEYS = list(SWEEP_GRID.keys())


def sweep_combinations() -> list[dict]:
    return [dict(zip(SWEEP_KEYS, values)) for values in product(*[SWEEP_GRID[k] for k in SWEEP_KEYS])]


def _replace_fields(obj, **kwargs):
    if dataclasses.is_dataclass(obj):
        return dataclasses.replace(obj, **kwargs)
    new_obj = copy.deepcopy(obj)
    for k, v in kwargs.items():
        setattr(new_obj, k, v)
    return new_obj


def apply_params(cfg, params: dict):
    """cfg.signal.atr_stop_mult/adx_min ve cfg.risk.min_rr'yi override eden yeni bir
    cfg döner (orijinali mutate etmez — hem frozen dataclass hem SimpleNamespace
    (test) cfg'leriyle çalışır)."""
    new_signal = _replace_fields(cfg.signal, atr_stop_mult=params["atr_stop_mult"], adx_min=params["adx_min"])
    new_risk = _replace_fields(cfg.risk, min_rr=params["min_rr"])
    return _replace_fields(cfg, signal=new_signal, risk=new_risk)


def _score(m: Metrics) -> float:
    """Basit skor: Sharpe. Trade yoksa (dolayısıyla Sharpe=0) skor 0 -> nötr."""
    return m.sharpe


def is_neighbor_robust(scores: dict[tuple, float], params: dict) -> bool:
    """Komşu-sağlamlık: seçilen kombinasyonun HER boyutta bir adım komşusu da
    pozitif skor üretiyor VE en iyi skorun en az yarısını koruyorsa sağlam sayılır.
    Amaç: tek bir izole kombinasyonun aşırı uyumunu (overfitting) elemektir."""
    best_score = scores[tuple(params[k] for k in SWEEP_KEYS)]
    if best_score <= 0:
        return False
    for k in SWEEP_KEYS:
        values = sorted(SWEEP_GRID[k])
        idx = values.index(params[k])
        neighbors = [values[i] for i in (idx - 1, idx + 1) if 0 <= i < len(values)]
        for nv in neighbors:
            neighbor_params = dict(params)
            neighbor_params[k] = nv
            neighbor_score = scores.get(tuple(neighbor_params[kk] for kk in SWEEP_KEYS))
            if neighbor_score is None or neighbor_score < best_score * 0.5:
                return False
    return True


def select_robust_params(train_results: dict[tuple, Metrics]) -> dict:
    """En yüksek skor yerine komşu-sağlamlık kriterini geçen en iyi kombinasyonu
    seçer (Bölüm 12.5). Sağlam kombinasyon yoksa yine de en iyi skorluyu döner —
    bu durum çağıran tarafından kırmızı bayrak olarak işaretlenmelidir."""
    scores = {combo: _score(m) for combo, m in train_results.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    for combo, _ in ranked:
        params = dict(zip(SWEEP_KEYS, combo))
        if is_neighbor_robust(scores, params):
            return params
    return dict(zip(SWEEP_KEYS, ranked[0][0])) if ranked else {}


@dataclass
class WindowResult:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    chosen_params: dict
    train_metrics: Metrics
    test_metrics: Metrics
    test_trades: list[Trade] = field(default_factory=list)
    robust: bool = False


def run_walk_forward(
    symbols: list[str],
    cfg,
    load_daily: Callable[[str], pd.DataFrame],
) -> list[WindowResult]:
    """Bölüm 12.5: her pencerede train diliminde 27 kombinasyonluk grid taraması,
    komşu-sağlamlık kriteriyle parametre seçimi, test diliminde o parametreyle koşum.

    Basitleştirme: her pencere kendi veri dilimi üzerinde build_features'ı sıfırdan
    hesaplar (dilim başında yeniden warm-up NaN'ı oluşur) — tam tarihçe üzerinde
    hesaplayıp sonradan dilimlemek yerine. train_months (varsayılan 24 ay) min_history_bars'ı
    (260) rahatça aştığından pencere içi kullanılabilir bar sayısı yeterlidir.
    """
    combos = sweep_combinations()
    daily_raw = {s: load_daily(s) for s in symbols}
    non_empty = [df.index for df in daily_raw.values() if not df.empty]
    if not non_empty:
        return []
    all_index = sorted(set().union(*non_empty))
    start_date, end_date = all_index[0], all_index[-1]

    train_months = cfg.backtest.walk_forward.train_months
    test_months = cfg.backtest.walk_forward.test_months
    step_months = cfg.backtest.walk_forward.step_months

    def _slice_loader(train_start, train_end):
        def _loader(s):
            df = daily_raw[s]
            return df.loc[(df.index >= train_start) & (df.index < train_end)]
        return _loader

    results: list[WindowResult] = []
    window_start = start_date
    while True:
        train_start = window_start
        train_end = train_start + pd.DateOffset(months=train_months)
        test_start = train_end
        test_end = test_start + pd.DateOffset(months=test_months)
        if test_end > end_date:
            break

        train_results: dict[tuple, Metrics] = {}
        for combo in combos:
            combo_cfg = apply_params(cfg, combo)
            bt = run_backtest(symbols, combo_cfg, _slice_loader(train_start, train_end))
            train_results[tuple(combo[k] for k in SWEEP_KEYS)] = compute_metrics(bt.equity_curve, bt.trades)

        chosen = select_robust_params(train_results)
        scores = {combo: _score(m) for combo, m in train_results.items()}
        robust = bool(chosen) and is_neighbor_robust(scores, chosen)

        chosen_cfg = apply_params(cfg, chosen)
        test_bt = run_backtest(symbols, chosen_cfg, _slice_loader(test_start, test_end))
        test_metrics = compute_metrics(test_bt.equity_curve, test_bt.trades)
        train_metrics = train_results[tuple(chosen[k] for k in SWEEP_KEYS)]

        results.append(WindowResult(
            train_start=train_start, train_end=train_end, test_start=test_start, test_end=test_end,
            chosen_params=chosen, train_metrics=train_metrics, test_metrics=test_metrics,
            test_trades=test_bt.trades, robust=robust,
        ))

        window_start = window_start + pd.DateOffset(months=step_months)

    return results


def combined_oos_metrics(results: list[WindowResult]) -> Metrics:
    """Tüm pencerelerin OOS (test) trade'lerini birleştirip tek bir equity eğrisi
    üzerinden metrik hesaplar (kabul kriteri değerlendirmesi için)."""
    all_trades: list[Trade] = []
    for r in results:
        all_trades.extend(r.test_trades)
    if not all_trades:
        return compute_metrics(pd.Series(dtype=float), [])

    combined_index = sorted({t.exit_date for t in all_trades} | {t.entry_date for t in all_trades})
    equity = 100_000.0
    points = []
    running_pnl = 0.0
    for ts in combined_index:
        running_pnl += sum(t.pnl for t in all_trades if t.exit_date == ts)
        points.append((ts, equity + running_pnl))
    equity_curve = pd.Series(dict(points)).sort_index()
    return compute_metrics(equity_curve, all_trades)


def evaluate_acceptance(results: list[WindowResult]) -> dict:
    """Bölüm 12.5 kabul kriteri: birleşik OOS profit factor > 1.1 VE OOS max DD,
    ortalama in-sample max DD'nin 1.5 katından kötü değil."""
    if not results:
        return {"passed": False, "reason": "hiç pencere üretilmedi"}

    oos = combined_oos_metrics(results)
    avg_is_dd = sum(abs(r.train_metrics.max_drawdown) for r in results) / len(results)
    oos_dd = abs(oos.max_drawdown)

    pf_ok = oos.profit_factor > 1.1
    dd_ok = oos_dd <= avg_is_dd * 1.5 if avg_is_dd > 0 else oos_dd == 0

    return {
        "passed": bool(pf_ok and dd_ok),
        "oos_profit_factor": oos.profit_factor,
        "oos_max_drawdown": oos.max_drawdown,
        "avg_in_sample_max_drawdown": avg_is_dd,
        "pf_ok": pf_ok,
        "dd_ok": dd_ok,
        "oos_trade_count": oos.trade_count,
    }

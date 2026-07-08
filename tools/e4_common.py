# tools/e4_common.py
"""EXPANSION E4 (US adil test) — ORTAK yardımcılar: US veri yükleme + benchmark
eğrileri + OOS pencere yardımcısı.

Bu modül STRATEJİ KOŞUMU İÇERMEZ. Item 2 (benchmark + kriter mühürleme)
herhangi bir strateji koşumundan ÖNCE yalnızca bu modülü kullanır; item 4
(D1-US spike sürücüsü) de aynı benchmark fonksiyonlarını yeniden kullanır →
mühürlenen benchmark değerleri ile strateji-turu benchmark değerleri BİREBİR
aynı kaynaktan gelir (drift imkânsız).

İstatistik fonksiyonları `tools/run_regime_core.py`'den (S1/S1b sürücüsü)
İTHAL edilir — S1b ile metodolojik özdeşliğin garantisi (yeniden yazılmaz).
Veri temizleme `data/cleaning.py::load_and_clean_universe` ile yapılır —
S1b/BIST ile AYNI yol (US 00:00-UTC verisinde normalize_bist_dates no-op'tur,
hayalet-bar filtresi piyasa-agnostiktir; kanıt: tests/test_e4_us.py).

`backtest/engine.py`, `strategy/`, `risk/`, canlı bot modüllerine DOKUNMAZ.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from backtest.regime_core import build_composite
from data.cleaning import load_and_clean_universe
from tools.run_regime_core import (
    compute_monthly_returns,
    compute_summary,
    gen_walk_forward_windows,
    monthly_sharpe,
)

DEFAULT_CFG_PATH = Path("config/regime_core_us.yaml")


def load_us_config(path: str | Path = DEFAULT_CFG_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_us_ohlcv(cfg: dict) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """US snapshot'ından TAM OHLCV'yi (10-gate huni build_features için gerekli)
    S1b/BIST ile AYNI temizleme yolundan (load_and_clean_universe) geçirir."""
    snapshot_dir = Path(cfg["backtest"]["snapshot"])
    start = cfg["backtest"]["start"]

    def _load_daily_raw(s: str) -> pd.DataFrame:
        return pd.read_parquet(snapshot_dir / f"{s}.parquet").loc[start:]

    cleaned, ghost_log = load_and_clean_universe(cfg["symbols"], _load_daily_raw)
    return cleaned, ghost_log


def load_us_closes(cfg: dict) -> tuple[dict[str, pd.Series], list[dict]]:
    cleaned, ghost_log = load_us_ohlcv(cfg)
    return {s: df["close"] for s, df in cleaned.items()}, ghost_log


def build_basket_curve(closes: dict[str, pd.Series], initial_equity: float
                       ) -> tuple[pd.Series, pd.Series, list[dict]]:
    """Eşit-ağırlık US sepeti al-tut benchmark'ı = build_composite (S1b ile AYNI
    fonksiyon) × initial_equity. Döner: (composite, basket_equity, fill_log).
    Bu, mühürlü kriterlerin REFERANSIDIR (sepet al-tut)."""
    composite, fill_log = build_composite(closes)
    basket_equity = composite * initial_equity
    return composite, basket_equity, fill_log


def load_spy_curve(cfg: dict, index: pd.DatetimeIndex, initial_equity: float) -> pd.Series:
    """Dondurulmuş SPY snapshot'ından al-tut endeks proxy eğrisi (benchmark b,
    BİLGİLENDİRİCİ). `index` aralığına (strateji/sepet equity aralığı) dilimlenir,
    ilk ortak günde initial_equity'ye normalize edilir. SPY US snapshot'larıyla
    AYNI kanonik şemada (00:00 UTC) — tarih hizalama doğrudan."""
    spy_path = Path(cfg["benchmark"]["snapshot"])
    spy = pd.read_parquet(spy_path)
    close = spy["close"]
    # Strateji/sepet aralığına daralt (endeksin fazladan çektiği son günler kırpılır).
    close = close.loc[(close.index >= index[0]) & (close.index <= index[-1])]
    if close.empty:
        return pd.Series(dtype=float)
    return close / float(close.iloc[0]) * initial_equity


def oos_windowed_from_curve(full_curve: pd.Series, all_dates: pd.DatetimeIndex,
                            wf: dict) -> dict:
    """Bir al-tut eğrisi (sepet veya SPY) için S1b sürücüsüyle AYNI walk-forward
    OOS yöntemini uygular: her (test_start, test_end] penceresinde eğrinin
    dilimini al, aylık getirilerini çıkar, tüm pencerelerin OOS aylık getirilerini
    birleştir → OOS aylık-Sharpe + OOS max DD. (Al-tut için pencere-içi 'yeniden
    koşum' yok; strateji tarafı item 4'te date_range ile yeniden koşulur.)"""
    windows = gen_walk_forward_windows(all_dates, wf["train_months"],
                                       wf["test_months"], wf["step_months"])
    oos_monthly: list[float] = []
    for _train_start, _train_end, test_start, test_end in windows:
        sl = full_curve.loc[test_start:test_end]
        oos_monthly.extend(compute_monthly_returns(sl).tolist())
    ser = pd.Series(oos_monthly)
    sharpe = monthly_sharpe(ser)
    eq = (1 + ser).cumprod()
    max_dd = float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0
    return {"n_windows": len(windows), "oos_monthly_sharpe": sharpe, "oos_max_dd": max_dd,
            "oos_n_months": len(ser)}


def compute_benchmarks(cfg: dict) -> dict:
    """Item 2 çekirdeği: STRATEJİ KOŞUMU OLMADAN sepet + SPY benchmark metriklerini
    (CAGR/maxDD/Sharpe + OOS aylık-Sharpe + OOS maxDD) hesaplar. Mühürlemenin
    girdisi; item 4 sürücüsü aynı fonksiyonu yeniden çağırır."""
    initial_equity = float(cfg["initial_equity"])
    closes, ghost_log = load_us_closes(cfg)
    composite, basket_equity, fill_log = build_basket_curve(closes, initial_equity)
    all_dates = composite.index

    basket_summary = compute_summary(basket_equity)
    basket_oos = oos_windowed_from_curve(basket_equity, all_dates, cfg["walk_forward"])

    spy_curve = load_spy_curve(cfg, all_dates, initial_equity)
    spy_summary = compute_summary(spy_curve) if not spy_curve.empty else None
    spy_oos = (oos_windowed_from_curve(spy_curve, spy_curve.index, cfg["walk_forward"])
               if not spy_curve.empty else None)

    return {
        "universe_size": len(cfg["symbols"]),
        "composite_start": str(all_dates[0]),
        "composite_end": str(all_dates[-1]),
        "n_days": int(len(all_dates)),
        "ghost_bars_removed": [{"symbol": g["symbol"], "date": str(g["date"])} for g in ghost_log],
        "composite_fill_log_count": len(fill_log),
        "basket_buy_hold": basket_summary,
        "basket_oos": basket_oos,
        "spy_buy_hold": spy_summary,
        "spy_oos": spy_oos,
        "spy_snapshot": cfg["benchmark"]["snapshot"],
    }

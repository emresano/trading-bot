# tools/run_tengate_us.py
"""EXPANSION E4 (US adil test) — item 3: DONDURULMUŞ 10-gate huninin (ten_gate
ailesi) ABD evrenindeki ADİL REFERANS koşumu.

**Sonuç yalnız RAPOR** — bir kabul kapısı DEĞİL. 10-gate ailesi BIST'te KALICI
KAYIT 3 ile reddedildi ve DONDURULDU; bu koşum "BIST'te reddedilen aile US'te
nasıl davranıyor" sorusunun dürüst cevabıdır.

Dondurulmuş huni = `config/config.yaml`'ın signal/risk eşikleri AYNEN (hiçbiri
değiştirilmez). Yalnızca (a) evren US, (b) maliyet US (commission=0, slippage 5;
SEC/TAF ~0.3bps 10-gate motor yolunda modellenmez — ihmal edilebilir, raporda
notlanır). v7.1-golden yolu (backtest/engine.py) DEĞİŞTİRİLMEZ — yalnızca farklı
symbols/loader/cost ile çağrılır.

Kullanım:  python -m tools.run_tengate_us
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pandas as pd

from backtest.engine import run_backtest
from backtest.metrics import compute_metrics
from core.config import CostsConfig, load_config
from costs.us_equities import UsEquitiesCostModel
from tools.e4_common import build_basket_curve, load_spy_curve, load_us_config, load_us_ohlcv
from tools.run_regime_core import compute_summary

OUT_DIR = Path("runtime/e4/tengate_us")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Dondurulmuş huni = config/config.yaml (v7.1-golden config); yalnız costs → US.
    frozen = load_config("config/config.yaml")
    us_costs = CostsConfig(commission_bps=0.0, slippage_bps=5.0)
    cfg = dataclasses.replace(frozen, costs=us_costs)

    ucfg = load_us_config()
    symbols = ucfg["symbols"]
    cleaned, ghost = load_us_ohlcv(ucfg)

    def _load_daily(s: str) -> pd.DataFrame:
        return cleaned[s]

    cost_model = UsEquitiesCostModel(
        commission_bps=ucfg["costs"]["commission_bps"], sec_fee_bps=ucfg["costs"]["sec_fee_bps"],
        taf_per_share=ucfg["costs"]["taf_per_share"], slippage_bps=ucfg["costs"]["slippage_bps"])

    print("=== 10-gate ADİL TEST (US evreni, dondurulmuş huni) ===")
    result = run_backtest(symbols, cfg, load_daily=_load_daily, cost_model=cost_model)
    m = compute_metrics(result.equity_curve, result.trades)

    # Bağlam: eşit-ağırlık US sepeti al-tut (D1-US ile AYNI benchmark) + SPY.
    closes = {s: df["close"] for s, df in cleaned.items()}
    _composite, basket_equity, _ = build_basket_curve(closes, cfg.backtest.initial_equity)
    if not result.equity_curve.empty:
        basket_equity = basket_equity.loc[result.equity_curve.index[0]:result.equity_curve.index[-1]]
    basket_summary = compute_summary(basket_equity)
    spy_curve = load_spy_curve(ucfg, basket_equity.index, cfg.backtest.initial_equity)
    spy_summary = compute_summary(spy_curve) if not spy_curve.empty else None

    metrics_dict = dataclasses.asdict(m)
    print(json.dumps(metrics_dict, indent=2, default=str))
    print("trade_count:", m.trade_count, "| time_in_cash%:", round(m.time_in_cash_pct, 1))

    output = {
        "run": "10-gate (ten_gate) ADİL TEST — US evreni, dondurulmuş huni, RAPOR-ONLY",
        "note": "Kabul kapısı DEĞİL. 10-gate BIST'te reddedildi (KALICI KAYIT 3), donmuş referans.",
        "cost_note": "commission=0, slippage=5bps; SEC/TAF (~0.3bps) 10-gate motor yolunda modellenmedi (ihmal).",
        "frozen_funnel_source": "config/config.yaml (v7.1-golden config) signal/risk AYNEN",
        "universe": symbols,
        "ghost_bars_removed": len(ghost),
        "strategy_metrics": metrics_dict,
        "context_basket_buy_hold": basket_summary,
        "context_spy_buy_hold": spy_summary,
        "equity_range": [str(result.equity_curve.index[0]), str(result.equity_curve.index[-1])]
        if not result.equity_curve.empty else None,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    result.equity_curve.to_csv(OUT_DIR / "equity_curve.csv")
    pd.DataFrame([dataclasses.asdict(t) for t in result.trades]).to_csv(OUT_DIR / "trades.csv", index=False)
    print(f"\nYazildi: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()

# tools/e4_charts.py
"""EXPANSION E4 — equity + drawdown grafikleri (runtime/e4/). Ephemeral/
yeniden üretilebilir kanıt (runtime/* gitignore). D1-US stratejisi vs eşit-
ağırlık US sepeti vs SPY (endeks proxy). tools/run_regime_core_us.py'nin
kaydettiği equity_curve_main.csv + e4_common benchmark eğrilerini okur.

Kullanım:  python -m tools.e4_charts
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from tools.e4_common import build_basket_curve, load_spy_curve, load_us_closes, load_us_config  # noqa: E402

OUT_DIR = Path("runtime/e4")


def _drawdown(curve: pd.Series) -> pd.Series:
    return (curve / curve.cummax() - 1.0) * 100.0


def main() -> None:
    cfg = load_us_config()
    strat = pd.read_csv(OUT_DIR / "regime_core_us" / "equity_curve_main.csv",
                        index_col=0, parse_dates=True).iloc[:, 0]
    closes, _ = load_us_closes(cfg)
    _comp, basket, _ = build_basket_curve(closes, float(cfg["initial_equity"]))
    basket = basket.loc[strat.index[0]:strat.index[-1]]
    spy = load_spy_curve(cfg, strat.index, float(cfg["initial_equity"]))

    # 1) Equity (log ölçek)
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(strat.index, strat.values, label="D1-US strateji (regime_core, cash=0%)", color="#1f77b4", lw=1.6)
    ax.plot(basket.index, basket.values, label="Eşit-ağırlık US sepeti al-tut (MÜHÜR REF.)", color="#ff7f0e", lw=1.2, alpha=0.9)
    if not spy.empty:
        ax.plot(spy.index, spy.values, label="SPY al-tut (endeks proxy, bilgi)", color="#2ca02c", lw=1.2, alpha=0.8)
    ax.set_yscale("log")
    ax.set_title("EXPANSION E4 — D1-US equity (log) vs benchmark'lar, 2005–2026 (USD)")
    ax.set_ylabel("Equity (USD, log)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "regime_core_us_equity.png", dpi=110)
    plt.close(fig)

    # 2) Drawdown
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(strat.index, _drawdown(strat).values, label="D1-US strateji", color="#1f77b4", lw=1.2)
    ax.plot(basket.index, _drawdown(basket).values, label="Eşit-ağırlık US sepeti", color="#ff7f0e", lw=1.0, alpha=0.8)
    ax.axhline(-23.14, color="#d62728", ls="--", lw=0.9, label="Mühürlü kriter 2 eşiği (-23.14%)")
    ax.set_title("EXPANSION E4 — D1-US vs sepet drawdown (%)")
    ax.set_ylabel("Drawdown (%)")
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "regime_core_us_drawdown.png", dpi=110)
    plt.close(fig)

    print("Grafikler yazildi:", OUT_DIR / "regime_core_us_equity.png", "+", OUT_DIR / "regime_core_us_drawdown.png")


if __name__ == "__main__":
    main()

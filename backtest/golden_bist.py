# backtest/golden_bist.py
"""BIST v7.1 golden regresyon çapasının TEK üretim yolu (EXPANSION.md Bölüm 0.2).

Bu modül, `runtime/backtest_reports_v7_1/trades.csv` (git tag `backtest-v7.1-golden`,
SHA256 manifest'te) golden dosyasını üreten koşumun MİNİMAL, DETERMİNİSTİK
tekrarıdır: 12-sembol BIST evreni, `data/snapshots/2026-07-06` snapshot'ı,
`config/config.yaml` (v7 config), `data/cleaning.py` temizlemesi, ve tek bir
ana `run_backtest` koşumu (walk-forward/monte-carlo YOK — golden yalnızca ana
koşumun trades.csv'sidir, `tools/portfolio_ablation.py` baseline varyantıyla
bit-bit aynı ana koşum).

E2 ve sonrasındaki HER commit'te `tests/test_golden_bist.py` bu çıktının golden
dosyayla BAYT-BAYT aynı olduğunu doğrular. Bu, çekirdek motor genelleştirmesinin
(MarketSpec, CostModel, gate_registry, Direction, daily_carry) BIST davranışını
değiştirmediğinin mekanik kanıtıdır.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data" / "snapshots" / "2026-07-06"
GOLDEN_CONFIG = REPO_ROOT / "config" / "config.yaml"
GOLDEN_TRADES = REPO_ROOT / "tests" / "golden" / "bist_v7_trades.csv"
START_DATE = "2005-01-01"

# tools/portfolio_ablation.py::SYMBOLS ile BİREBİR aynı sıra (golden'ın kaynağı).
GOLDEN_SYMBOLS = ["THYAO", "GARAN", "ASELS", "AKBNK", "KCHOL", "SAHOL",
                  "EREGL", "TUPRS", "TCELL", "TOASO", "SISE", "ARCLK"]


def _trades_to_csv_bytes(trades) -> bytes:
    """backtest/cli.py::_write_trades_csv ile BİREBİR aynı kolon sırası/serileştirme,
    ama diske yazmadan bellek-içi bytes döner (golden kıyası için)."""
    rows = [
        {
            "symbol": t.symbol, "entry_date": t.entry_date, "entry_price": t.entry_price,
            "exit_date": t.exit_date, "exit_price": t.exit_price, "quantity": t.quantity,
            "exit_reason": t.exit_reason, "pnl": t.pnl, "r_multiple": t.r_multiple,
        }
        for t in trades
    ]
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def reproduce_golden_trades_bytes(breaker_file: Path | None = None, cost_model=None) -> bytes:
    """Golden koşumu tekrarlar ve trades.csv'nin bytes'ını döner (diske yazmaz).

    `cost_model`: verilirse run_backtest'e iletilir. BIST CostModel'i daily_carry=0
    döndürdüğünden çıktı golden ile bit-bit aynı kalmalıdır (daily_carry hook'unun
    BIST-güvenliğini kanıtlar — tests/test_golden_bist.py)."""
    # Yerel importlar: bu modül config yüklemeden de import edilebilsin (test toplama hızı).
    from backtest.engine import run_backtest
    from core.config import load_config
    from data.cleaning import load_and_clean_universe

    cfg = load_config(str(GOLDEN_CONFIG))

    def _load_daily_raw(s: str) -> pd.DataFrame:
        df = pd.read_parquet(SNAPSHOT_DIR / f"{s}.parquet")
        return df.loc[START_DATE:]

    cleaned, _ghost = load_and_clean_universe(GOLDEN_SYMBOLS, _load_daily_raw)
    result = run_backtest(GOLDEN_SYMBOLS, cfg, lambda s: cleaned[s],
                          breaker_file=breaker_file, cost_model=cost_model)
    return _trades_to_csv_bytes(result.trades)

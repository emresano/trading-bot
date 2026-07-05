# backtest/gate_diagnostics.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from indicators.engine import build_features
from strategy.signal_engine import ENTRY_GATES

GATE_NAMES: list[str] = [g.__name__.replace("gate_", "") for g in ENTRY_GATES]


@dataclass(frozen=True)
class GateDiagnostics:
    symbol: str
    total_days: int
    standalone_pass_rate: dict[str, float]    # gate adı -> geçiş oranı (%), diğer gate'lerden bağımsız
    cumulative_pass_rate: dict[int, float]    # kademe (1..10) -> o kademeye kadar TÜMÜNÜ geçen gün oranı (%)
    cumulative_pass_count: dict[int, int]


def diagnose_symbol(symbol: str, features_df: pd.DataFrame, cfg) -> GateDiagnostics:
    """Ölçüm amaçlı: hiçbir eşik değiştirmez, yalnızca mevcut cfg parametreleriyle
    her gate'in tek başına ve huninin kademe kademe kümülatif geçiş oranını sayar.

    `features_df`, indicators.engine.build_features(daily_df, cfg) çıktısı olmalı."""
    min_history = cfg.signal.min_history_bars
    if len(features_df) <= min_history:
        return GateDiagnostics(
            symbol=symbol, total_days=0,
            standalone_pass_rate={name: 0.0 for name in GATE_NAMES},
            cumulative_pass_rate={k: 0.0 for k in range(1, len(ENTRY_GATES) + 1)},
            cumulative_pass_count={k: 0 for k in range(1, len(ENTRY_GATES) + 1)},
        )

    standalone_counts = {name: 0 for name in GATE_NAMES}
    cumulative_counts = {k: 0 for k in range(1, len(ENTRY_GATES) + 1)}
    total_days = 0

    macd_hist = features_df["macd_hist"]
    for i in range(min_history, len(features_df)):
        d = features_df.iloc[i].copy()
        d["macd_hist_prev1"] = float(macd_hist.iloc[i - 1]) if i >= 1 else float("nan")
        total_days += 1

        all_pass_so_far = True
        for k, (gate, name) in enumerate(zip(ENTRY_GATES, GATE_NAMES), start=1):
            passed = gate(d, None, cfg).passed
            if passed:
                standalone_counts[name] += 1
            all_pass_so_far = all_pass_so_far and passed
            if all_pass_so_far:
                cumulative_counts[k] += 1

    standalone_rate = {name: 100.0 * c / total_days for name, c in standalone_counts.items()}
    cumulative_rate = {k: 100.0 * c / total_days for k, c in cumulative_counts.items()}
    return GateDiagnostics(symbol, total_days, standalone_rate, cumulative_rate, cumulative_counts)


def write_report(diagnostics: list[GateDiagnostics], out_path: str | Path) -> None:
    lines = [
        "# Gate Teşhis Raporu", "",
        "Ölçüm amaçlı — hiçbir eşik değiştirilmedi. Mevcut `config.yaml` parametreleriyle "
        "10 gate'in (ENTRY_GATES sırasıyla) tek başına ve kümülatif geçiş oranları ölçüldü.",
        "Degrade mod (h4_df=None) kullanıldı — gerçek backtest çalıştırmasıyla tutarlı.", "",
    ]

    for diag in diagnostics:
        lines.append(f"## {diag.symbol} (n={diag.total_days} gün)")
        lines.append("")
        lines.append("### Tek başına geçiş oranı (diğer gate'lerden bağımsız ölçüldü)")
        lines.append("| Kademe | Gate | Geçiş Oranı |")
        lines.append("|---|---|---|")
        for k, name in enumerate(GATE_NAMES, start=1):
            lines.append(f"| {k} | {name} | {diag.standalone_pass_rate[name]:.2f}% |")
        lines.append("")
        lines.append("### Kümülatif huni geçişi (o kademeye kadar TÜMÜNÜ geçen gün oranı)")
        lines.append("| Kademe | Gate | Kümülatif Geçiş Oranı | Gün Sayısı |")
        lines.append("|---|---|---|---|")
        for k, name in enumerate(GATE_NAMES, start=1):
            lines.append(f"| {k} | {name} | {diag.cumulative_pass_rate[k]:.4f}% | {diag.cumulative_pass_count[k]} |")
        lines.append("")

    if len(diagnostics) > 1:
        lines.append("## Özet (semboller arası ortalama)")
        lines.append("| Kademe | Gate | Ort. Tek Başına | Ort. Kümülatif |")
        lines.append("|---|---|---|---|")
        for k, name in enumerate(GATE_NAMES, start=1):
            avg_standalone = sum(d.standalone_pass_rate[name] for d in diagnostics) / len(diagnostics)
            avg_cumulative = sum(d.cumulative_pass_rate[k] for d in diagnostics) / len(diagnostics)
            lines.append(f"| {k} | {name} | {avg_standalone:.2f}% | {avg_cumulative:.4f}% |")
        lines.append("")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def run_gate_diagnostics(
    symbols: list[str],
    cfg,
    load_daily: Callable[[str], pd.DataFrame],
    out_path: str | Path,
) -> list[GateDiagnostics]:
    diagnostics = []
    for symbol in symbols:
        features_df = build_features(load_daily(symbol), cfg)
        diagnostics.append(diagnose_symbol(symbol, features_df, cfg))
    write_report(diagnostics, out_path)
    return diagnostics


def main() -> None:
    import argparse

    from core.config import load_config
    from data.historical import load_cached

    parser = argparse.ArgumentParser(description="Gate teşhis raporu (ölçüm amaçlı, hiçbir eşik değiştirmez)")
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--out", default="runtime/backtest_reports/gate_diagnostics.md")
    args = parser.parse_args()

    cfg = load_config(args.config)
    symbols = [s.strip() for s in args.symbols.split(",")]
    run_gate_diagnostics(symbols, cfg, lambda s: load_cached(s, "1d"), args.out)
    print(f"Rapor yazıldı: {args.out}")


if __name__ == "__main__":
    main()

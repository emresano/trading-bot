# tools/period_comparison.py
"""DÖNEMSEL KARŞILAŞTIRMA RAPORU — BİLGİLENDİRME ARACI (kriter/kabul/karar YOK).

Bu araç mühürlü hiçbir eşiği değiştirmez, hiçbir varyant/parametre seçmez.
D1 (regime_core) ailesinin mühürlü S1b konfigürasyonuyla (N=200/b=%1/M=3,
config/regime_core.yaml, backtest/regime_core.py + tools/run_regime_core.py'nin
BAĞIMSIZ, mühürlü fonksiyonları) equity eğrisini 2026-07-08'e kadar yeniden
üretir; birkaç dürüst-kıyas serisiyle (sepet al-tut, XU100, TRY faizi,
USD al-tut, best-effort altın/TÜFE) pencere bazlı (1y/3y/5y/10y/tam-dönem)
tablo üretir. STRATEJİ/MOTOR/RİSK/KARAR KODU DEĞİŞTİRİLMEZ — yalnız import
edip yeniden kullanır (S1b araçları AYNEN, `tools.run_regime_core` +
`backtest.regime_core`). Mevcut hiçbir snapshot değiştirilmez; yalnızca
frozen S1b snapshot'ının (data/snapshots/2026-07-06, son bar ~07-02) 2026-07-08'e
kadar olan EKSİK kuyruğu, ayrı bir `data/snapshots/aux_cmp/<tarih>/` dizinine
sha256 manifest'li olarak dondurulur (mevcut snapshot'a DOKUNULMAZ).

Kullanım:
  python -m tools.period_comparison
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yaml

from backtest.regime_core import RegimeCoreConfig, compute_cash_only_curve, run_regime_core
from data.cleaning import load_and_clean_universe, normalize_bist_dates
from data.historical import GOLD_GRAM_DIVISOR, download_bars, load_cached, update_cache
from tools.run_regime_core import (
    CFG_PATH,
    compute_monthly_returns,
    compute_summary,
    load_cash_rate,
    load_config,
)

REPORT_END = pd.Timestamp("2026-07-08", tz="UTC")
AUX_CMP_ROOT = Path("data/snapshots/aux_cmp")
CPI_FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TURCPIALLMINMEI"
CPI_SERIES_ID = "TURCPIALLMINMEI"  # Turkey CPI: All Items, OECD MEI seviyesi (index)
CASH_YIELD_HAIRCUT_S1B = 0.02  # backtest/regime_core.py::CASH_YIELD_HAIRCUT ile AYNI (belge amaçlı)

WINDOW_YEARS = [("son_1y", 1), ("son_3y", 3), ("son_5y", 5), ("son_10y", 10)]

CRISIS_WINDOWS = [
    ("2008", "2008-01-01", "2008-12-31"),
    ("2013", "2013-01-01", "2013-12-31"),
    ("2018", "2018-01-01", "2018-12-31"),
    ("2021-23", "2021-01-01", "2023-12-31"),
]


# --------------------------------------------------------------------------
# aux_cmp dondurma (yalnızca EKSİK kuyruk; mevcut snapshot'lara DOKUNMAZ)
# --------------------------------------------------------------------------

def freeze_aux_cmp(run_tag: str, frames: dict[str, pd.DataFrame], scope_note: str, source_note: str) -> Optional[Path]:
    """`frames` (sembol -> yalnızca YENİ barlar) boşsa hiçbir şey yazmaz, None döner.
    Aksi halde `data/snapshots/aux_cmp/<run_tag>/<SEMBOL>.parquet` + sha256'lı
    manifest.json yazar. Var olan hiçbir snapshot dizinine dokunmaz (yeni dizin).
    Aynı `run_tag` için BİRDEN FAZLA çağrı yapılırsa (örn. D1 evreni + USDTRY, aynı
    tarih etiketi) manifest ÜZERİNE YAZILMAZ — mevcut `files`/`groups` ile BİRLEŞTİRİLİR
    (kaybolan kayıt riski yok)."""
    frames = {s: df for s, df in frames.items() if df is not None and not df.empty}
    if not frames:
        return None
    out_dir = AUX_CMP_ROOT / run_tag
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "files": {}, "groups": [],
    }
    files: dict[str, dict] = manifest["files"]
    for symbol, df in frames.items():
        path = out_dir / f"{symbol}.parquet"
        df.to_parquet(path)
        raw = path.read_bytes()
        files[symbol] = {
            "rows": len(df), "start": str(df.index[0]), "end": str(df.index[-1]),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        }
    manifest["groups"].append({"scope": scope_note, "source": source_note, "symbols": sorted(frames.keys())})
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_dir


# --------------------------------------------------------------------------
# D1 evreni: frozen snapshot + eksik kuyruğun canlı tamamlanması
# --------------------------------------------------------------------------

def _extend_one(symbol: str, yf_symbol: str, frozen_dir: Path, end_ts: pd.Timestamp):
    """Döner: (combined_raw_df, new_bars_df_or_None, overlap_diff_note_or_None)."""
    frozen_path = frozen_dir / f"{symbol}.parquet"
    frozen_df = pd.read_parquet(frozen_path)
    frozen_last = frozen_df.index[-1]
    if frozen_last >= end_ts:
        return frozen_df, None, None

    fetch_start = (frozen_last - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    fresh_df = download_bars(yf_symbol, "1d", start=fetch_start)
    if fresh_df.empty:
        return frozen_df, None, {"symbol": symbol, "note": "canlı çekim boş döndü"}

    overlap_idx = fresh_df.index.intersection(frozen_df.index)
    diff_note = None
    if len(overlap_idx):
        rel_diff = ((fresh_df.loc[overlap_idx, "close"] - frozen_df.loc[overlap_idx, "close"]).abs()
                    / frozen_df.loc[overlap_idx, "close"]).max()
        diff_note = {"symbol": symbol, "overlap_days": int(len(overlap_idx)), "max_abs_rel_diff": float(rel_diff)}

    new_bars = fresh_df.loc[(fresh_df.index > frozen_last) & (fresh_df.index <= end_ts)]
    combined = pd.concat([frozen_df, new_bars]).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined, (new_bars if not new_bars.empty else None), diff_note


def load_extended_d1_closes(cfg: dict, run_tag: str):
    """S1b'nin frozen snapshot'ını (data/snapshots/2026-07-06) `REPORT_END`'e kadar
    canlı çekimle tamamlar (yalnız eksik kuyruk), gerekiyorsa aux_cmp'ye dondurur,
    ardından `data.cleaning.load_and_clean_universe`'i (S1b ile AYNI fonksiyon)
    kullanarak temizlenmiş close serilerini döner.
    Döner: (closes, ghost_log, diff_notes, aux_cmp_dir_or_None)."""
    snapshot_dir = Path(cfg["backtest"]["snapshot"])
    start = cfg["backtest"]["start"]
    symbols = cfg["symbols"]

    raw_cfg = yaml.safe_load(Path("config/config.yaml").read_text(encoding="utf-8"))
    yf_map = {i["symbol"]: i["yf_symbol"] for i in raw_cfg["instruments"]}

    combined_by_symbol: dict[str, pd.DataFrame] = {}
    new_bars_by_symbol: dict[str, pd.DataFrame] = {}
    diff_notes: list[dict] = []
    for s in symbols:
        combined, new_bars, note = _extend_one(s, yf_map[s], snapshot_dir, REPORT_END)
        combined_by_symbol[s] = combined
        if new_bars is not None:
            new_bars_by_symbol[s] = new_bars
        if note is not None:
            diff_notes.append(note)

    aux_dir = freeze_aux_cmp(
        run_tag, new_bars_by_symbol,
        scope_note="D1 12-sembol evreni — frozen S1b snapshot'ının (2026-07-06) EKSİK kuyruğu, "
                    f"yalnızca {REPORT_END.date()}'e kadar (period_comparison.py, BİLGİ turu)",
        source_note="yfinance (data.historical.download_bars, auto_adjust=True)",
    )

    def _loader(s: str) -> pd.DataFrame:
        return combined_by_symbol[s].loc[start:]

    closes_raw, ghost_log = load_and_clean_universe(symbols, _loader)
    closes = {s: df["close"] for s, df in closes_raw.items()}
    return closes, ghost_log, diff_notes, aux_dir


def load_extended_usdtry(run_tag: str):
    """USDTRY frozen aux snapshot'ını (data/snapshots/aux/2026-07-06) `REPORT_END`'e
    kadar canlı çekimle tamamlar (aynı aux_cmp mekanizması). Döner: (close_series, aux_dir_or_None)."""
    frozen_dir = Path("data/snapshots/aux/2026-07-06")
    combined, new_bars, _note = _extend_one("USDTRY", "USDTRY=X", frozen_dir, REPORT_END)
    aux_dir = freeze_aux_cmp(
        run_tag, {"USDTRY": new_bars} if new_bars is not None else {},
        scope_note="USDTRY bilgilendirici seri — frozen aux snapshot'ının (2026-07-06) EKSİK kuyruğu, "
                    f"yalnızca {REPORT_END.date()}'e kadar (period_comparison.py, BİLGİ turu)",
        source_note="yfinance (USDTRY=X)",
    )
    normalized, _ = load_and_clean_universe(["USDTRY"], lambda _s: combined)
    return normalized["USDTRY"]["close"], aux_dir


# --------------------------------------------------------------------------
# Best-effort ek seriler: altın (TRY), TÜFE (FRED)
# --------------------------------------------------------------------------

def load_gold_try_series() -> tuple[Optional[pd.Series], str]:
    """`data.historical.build_gold_try_proxy()` GC=F (~04:00 UTC) ile USDTRY=X
    (~00:00/23:00 UTC) barlarını SAAT-hizasız ham index'te iç-birleştirdiği için
    (farklı gün-içi saat damgaları) 0 satır üretiyor — mevcut, DEĞİŞTİRİLMEYEN bir
    ön-koşul kusuru (build_gold_try_proxy DOKUNULMADI). Best-effort için burada
    AYNI iki seri, `normalize_bist_dates` (mevcut, reuse) ile takvim-günü hizalı
    birleştirilir — yalnızca bu BİLGİ turunun yerel birleştirme mantığı."""
    try:
        gold_usd = download_bars("GC=F", "1d")
        usdtry = download_bars("USDTRY=X", "1d")
        if gold_usd.empty or usdtry.empty:
            return None, "GC=F veya USDTRY=X çekimi boş — satır atlandı"
        merged = normalize_bist_dates(gold_usd)[["close"]].join(
            normalize_bist_dates(usdtry)[["close"]], lsuffix="_gold", rsuffix="_try", how="inner")
        if merged.empty:
            return None, "GC=F/USDTRY=X takvim-günü hizalı birleşimi boş — satır atlandı"
        gram_try = (merged["close_gold"] * merged["close_try"] / GOLD_GRAM_DIVISOR).sort_index()
        return gram_try, f"GC=F×USDTRY=X/{GOLD_GRAM_DIVISOR} (gram altın TL), {len(gram_try)} gün"
    except Exception as e:
        return None, f"altın proxy hesaplaması BAŞARISIZ ({e}) — satır atlandı"


def load_cpi_level_series() -> tuple[Optional[pd.Series], str]:
    """FRED TURCPIALLMINMEI (Türkiye TÜFE, seviye endeksi). Ağ/parse hatasında
    (None, sebep) döner — çağıran BEST-EFFORT olarak atlar."""
    try:
        r = requests.get(CPI_FRED_URL, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        date_col, val_col = df.columns[0], df.columns[1]
        idx = pd.DatetimeIndex(pd.to_datetime(df[date_col], utc=True))
        vals = pd.to_numeric(df[val_col], errors="coerce")
        s = pd.Series(vals.values, index=idx, name=CPI_SERIES_ID).dropna().sort_index()
        last_date = str(s.index[-1].date())
        return s, f"FRED {CPI_SERIES_ID}, son gözlem {last_date} (bilinen gecikme)"
    except Exception as e:
        return None, f"FRED çekimi BAŞARISIZ ({e}) — satır atlandı"


# --------------------------------------------------------------------------
# Pencere yardımcıları
# --------------------------------------------------------------------------

def window_bounds(series_first: pd.Timestamp) -> list[tuple[str, str, pd.Timestamp, pd.Timestamp, bool]]:
    """Döner: [(key, etiket, start, end, full_coverage_mi)]. `full_coverage_mi`:
    istenen pencere başlangıcı `series_first`'ten ÖNCEYSE False (o pencere kısmi
    veri ile hesaplanmıştır — rapora not düşülür)."""
    out = []
    for key, years in WINDOW_YEARS:
        wanted_start = REPORT_END - pd.DateOffset(years=years)
        full = wanted_start >= series_first
        start = max(wanted_start, series_first)
        out.append((key, f"Son {years} Yıl", start, REPORT_END, full))
    out.append(("tam_donem", "Tam Dönem", series_first, REPORT_END, True))
    return out


def series_window_metrics(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    sliced = series.loc[start:end]
    return compute_summary(sliced)


def daily_ffill(series: pd.Series, all_dates: pd.DatetimeIndex) -> pd.Series:
    return series.reindex(all_dates, method="ffill").bfill()


def switch_count_and_regime_ratio(switches, regime_on: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> tuple[int, float]:
    n = sum(1 for sw in switches if start <= sw.date <= end)
    sliced = regime_on.loc[start:end]
    ratio = float(sliced.mean()) if len(sliced) else 0.0
    return n, ratio


# --------------------------------------------------------------------------
# Ana koşum: D1 yeniden-üretimi + karşılaştırma serileri + pencere tabloları
# --------------------------------------------------------------------------

def run_comparison(run_tag: Optional[str] = None) -> dict:
    """Mühürlü S1b konfigürasyonuyla D1'i (maliyet+nakit-faiz dahil) 2026-07-08'e
    kadar yeniden üretir, karşılaştırma serilerini + USD panelini + pencere
    tablolarını hesaplar. HİÇBİR eşik/parametre değiştirilmez/seçilmez."""
    run_tag = run_tag or date.today().isoformat()
    cfg = load_config()

    closes, ghost_log, d1_diff_notes, d1_aux_dir = load_extended_d1_closes(cfg, run_tag)
    cash_rate = load_cash_rate(cfg)  # S1b mühürlü aux (frozen, DEĞİŞTİRİLMEDİ)

    reg = cfg["regime"]
    core_cfg = RegimeCoreConfig(
        symbols=cfg["symbols"], ma_period=reg["ma_period"], band_pct=reg["band_pct"],
        confirm_days=reg["confirm_days"], commission_bps=cfg["costs"]["commission_bps"],
        slippage_bps=cfg["costs"]["slippage_bps"], initial_equity=cfg["initial_equity"],
    )

    # --- Madde 1: D1 equity eğrisi (mühürlü N/b/M + maliyet + nakit-faiz; haircut S1b'nin kendi dahili sabiti) ---
    result = run_regime_core(closes, core_cfg, cash_rate=cash_rate)
    equity = result.equity_curve
    basket_equity = (result.composite * core_cfg.initial_equity).loc[equity.index[0]: equity.index[-1]]

    # --- Madde 2: karşılaştırma serileri ---
    bench_cfg = cfg["benchmark"]
    update_cache(bench_cfg["index_symbol"], bench_cfg["index_yf_symbol"], "1d")  # S1b aracıyla AYNI çağrı (emsal, canlı)
    bt_start = pd.Timestamp(cfg["backtest"]["start"], tz="UTC")
    xu100_df = load_cached(bench_cfg["index_symbol"], "1d").loc[bt_start: REPORT_END]
    xu100_equity = xu100_df["close"]

    usdtry, usd_aux_dir = load_extended_usdtry(run_tag)
    gold, gold_note = load_gold_try_series()
    cpi, cpi_note = load_cpi_level_series()

    faiz_ham = compute_cash_only_curve(equity.index, cash_rate, core_cfg.initial_equity, haircut=0.0)
    faiz_haircut = compute_cash_only_curve(equity.index, cash_rate, core_cfg.initial_equity, haircut=CASH_YIELD_HAIRCUT_S1B)

    series_map: dict[str, pd.Series] = {
        "D1": equity, "sepet": basket_equity, "XU100": xu100_equity,
        "faiz_haircut": faiz_haircut, "faiz_ham": faiz_ham, "USD": usdtry,
    }
    if gold is not None:
        series_map["altin"] = gold
    if cpi is not None:
        series_map["TUFE"] = daily_ffill(cpi, equity.index)

    cpi_last_real_date = cpi.index[-1] if cpi is not None else None

    windows = window_bounds(equity.index[0])
    window_tables = {}
    for key, label, start, end, full_cov in windows:
        row = {name: series_window_metrics(s, start, end) for name, s in series_map.items()}
        n_sw, ratio = switch_count_and_regime_ratio(result.switches, result.regime_on, start, end)
        tufe_stale = cpi_last_real_date is not None and start > cpi_last_real_date
        window_tables[key] = {
            "label": label, "start": start, "end": end, "full_coverage": full_cov,
            "metrics": row, "n_switches": n_sw, "regime_on_ratio": ratio, "tufe_stale": tufe_stale,
        }

    # --- Madde 3: USD paneli (D1 + sepet, USD-terim CAGR/maxDD) ---
    usdtry_daily = daily_ffill(usdtry, equity.index)
    d1_usd = equity / usdtry_daily
    sepet_usd = basket_equity / usdtry_daily.loc[basket_equity.index[0]: basket_equity.index[-1]]
    usd_panel = {}
    for key, label, start, end, full_cov in windows:
        usd_panel[key] = {
            "label": label, "D1_usd": series_window_metrics(d1_usd, start, end),
            "sepet_usd": series_window_metrics(sepet_usd, start, end),
        }

    # --- Kriz-yılı ayrıştırması (BİLGİ) ---
    crisis_rows = []
    for label, cstart, cend in CRISIS_WINDOWS:
        cs, ce = pd.Timestamp(cstart, tz="UTC"), pd.Timestamp(cend, tz="UTC")
        crisis_rows.append({
            "label": label,
            "D1": series_window_metrics(equity, cs, ce)["total_return"],
            "sepet": series_window_metrics(basket_equity, cs, ce)["total_return"],
            "faiz_haircut": series_window_metrics(faiz_haircut, cs, ce)["total_return"],
        })

    return {
        "run_tag": run_tag, "cfg": cfg, "core_cfg": core_cfg,
        "result": result, "equity": equity, "basket_equity": basket_equity,
        "xu100_equity": xu100_equity, "usdtry": usdtry, "gold": gold, "gold_note": gold_note,
        "cpi": cpi, "cpi_note": cpi_note,
        "faiz_ham": faiz_ham, "faiz_haircut": faiz_haircut,
        "series_map": series_map, "windows": windows, "window_tables": window_tables,
        "usd_panel": usd_panel, "crisis_rows": crisis_rows,
        "ghost_log": ghost_log, "d1_diff_notes": d1_diff_notes,
        "d1_aux_dir": str(d1_aux_dir) if d1_aux_dir else None,
        "usd_aux_dir": str(usd_aux_dir) if usd_aux_dir else None,
    }


def main() -> None:
    data = run_comparison()
    eq = data["equity"]
    print(f"D1 equity: {eq.index[0].date()} -> {eq.index[-1].date()}, son değer {eq.iloc[-1]:,.0f}")
    for key, table in data["window_tables"].items():
        d1m = table["metrics"]["D1"]
        print(f"{table['label']:>12}: total_return={d1m['total_return']:+.2%} cagr={d1m['cagr']:+.2%} "
              f"maxDD={d1m['max_drawdown']:.2%} switches={table['n_switches']} regime_on={table['regime_on_ratio']:.1%} "
              f"(full_coverage={table['full_coverage']})")
    from tools.period_comparison_report import write_report
    write_report(data)


if __name__ == "__main__":
    main()

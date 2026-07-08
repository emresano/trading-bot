# tools/build_us_rate_snapshot.py
"""EXPANSION E4b — US kısa faiz serisi (3-aylık T-bill) DONDURULMUŞ snapshot'ı.

Kaynak: FRED (St. Louis Fed), herkese açık kimlik-doğrulamasız CSV.
- ÖNCELİK: `DGS3MO` — "3-Month Treasury Constant Maturity Rate", GÜNLÜK, %.
- YEDEK:  `TB3MS`  — "3-Month Treasury Bill Secondary Market Rate", AYLIK, %.

TRY_ON_RATE emsaliyle AYNI format: tek `rate_pct` kolonu (yüzde), UTC tarih
index'i. Yalnız GEÇERLİ gözlemler saklanır (FRED'in tatil "." işaretleri
düşürülür); kullanım noktasında (regime_core) günlük takvime forward-fill edilir.

Mevcut snapshot'lara (BIST/US/aux/us_bench) DOKUNMAZ — yalnız yeni bir dizin yazar.
Bir kez çalıştırılıp commit'lenir → sonrası deterministik/offline.

Kullanım:  python -m tools.build_us_rate_snapshot
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={cosd}"
PRIMARY = "DGS3MO"
FALLBACK = "TB3MS"
OUT_DIR = Path("data/snapshots/aux_us/2026-07-08")
START = "2005-01-01"


def fetch_fred_series(series_id: str) -> pd.DataFrame:
    r = requests.get(FRED_CSV.format(sid=series_id, cosd=START), timeout=30)
    r.raise_for_status()
    raw = pd.read_csv(io.StringIO(r.text))
    date_col, val_col = raw.columns[0], raw.columns[1]
    idx = pd.to_datetime(raw[date_col]).dt.tz_localize("UTC")
    rate = pd.to_numeric(raw[val_col], errors="coerce")
    df = pd.DataFrame({"rate_pct": rate.to_numpy()}, index=pd.DatetimeIndex(idx, name="date"))
    return df


def gap_report(valid_index: pd.DatetimeIndex) -> dict:
    """Ardışık GEÇERLİ gözlemler arası boşluk analizi. Günlük seride tatil boşlukları
    beklenir; >7 takvim günü boşluklar ('uzun') ayrıca raporlanır."""
    deltas = valid_index.to_series().diff().dropna().dt.days
    long_gaps = [(str(valid_index[i].date()), int(deltas.iloc[i - 1]))
                 for i in range(1, len(valid_index)) if deltas.iloc[i - 1] > 7]
    return {
        "max_gap_days": int(deltas.max()) if len(deltas) else 0,
        "n_gaps_gt_7d": int((deltas > 7).sum()),
        "long_gaps_gt_7d": long_gaps[:20],
    }


def build() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    used_id, cadence = PRIMARY, "daily"
    try:
        df = fetch_fred_series(PRIMARY)
        if df["rate_pct"].notna().sum() < 100:
            raise ValueError("DGS3MO çok az geçerli gözlem")
    except Exception as e:  # noqa: BLE001
        print(f"DGS3MO başarısız ({type(e).__name__}: {e}) → yedek TB3MS")
        df = fetch_fred_series(FALLBACK)
        used_id, cadence = FALLBACK, "monthly"

    n_total = len(df)
    n_dot = int(df["rate_pct"].isna().sum())      # FRED tatil "." işaretleri
    df_valid = df.dropna(subset=["rate_pct"]).copy()
    n_valid = len(df_valid)

    path = OUT_DIR / f"{used_id}.parquet"
    df_valid.to_parquet(path)
    raw_bytes = path.read_bytes()

    gaps = gap_report(df_valid.index)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "market_id": "us_aux",
        "scope": ("EXPANSION E4b — US 3-aylık T-bill kısa faizi; YALNIZCA cash-yield "
                  "modeline girer, HİÇBİR sinyal/gate hesabına girmez (S1b TRY_ON_RATE emsali)."),
        "series_id": used_id,
        "cadence": cadence,
        "source": "FRED (St. Louis Fed), herkese açık kimlik-doğrulamasız CSV",
        "fred_url": FRED_CSV.format(sid=used_id, cosd=START),
        "series_meaning": {
            "DGS3MO": "3-Month Treasury Constant Maturity Rate (günlük, %)",
            "TB3MS": "3-Month Treasury Bill Secondary Market Rate (aylık, %)",
        }[used_id],
        "haircut_bps": 50,
        "haircut_rationale": (
            "50bp kırpma MUHAFAZAKÂR: perakende bir nakit-sweep/para-piyasası fonu, "
            "3-aylık T-bill politika oranının ALTINDA getiri sağlar — fon gider oranı "
            "(~15-40bp), bid/ask + sürtünme ve vergi-öncesi net fark için kaba bir tampon. "
            "TRY (200bp) emsaliyle AYNI yapı, US için daha dar (USD faizi/spread'i daha küçük). "
            "Kırpma altında r_net=max(rate-0.005,0), ACT/365."),
        "start_date_filter": START,
        "rows_total_fetched": n_total,
        "rows_valid": n_valid,
        "rows_dropped_dot_holiday": n_dot,
        "value_range_pct": [float(df_valid["rate_pct"].min()), float(df_valid["rate_pct"].max())],
        "first_obs": str(df_valid.index[0]),
        "last_obs": str(df_valid.index[-1]),
        "gap_report": gaps,
        "file": {"name": path.name, "rows": n_valid,
                 "sha256": hashlib.sha256(raw_bytes).hexdigest(), "bytes": len(raw_bytes)},
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    m = build()
    print(f"US kısa faiz snapshot yazıldı: {OUT_DIR}/{m['series_id']}.parquet")
    print(f"  seri: {m['series_id']} ({m['cadence']}), {m['first_obs'][:10]} → {m['last_obs'][:10]}")
    print(f"  geçerli satır: {m['rows_valid']}, düşürülen tatil-'.': {m['rows_dropped_dot_holiday']}")
    print(f"  değer aralığı %: {m['value_range_pct']}")
    print(f"  boşluk: max {m['gap_report']['max_gap_days']}g, >7g boşluk sayısı: {m['gap_report']['n_gaps_gt_7d']}")
    print(f"  sha256: {m['file']['sha256']}")


if __name__ == "__main__":
    main()

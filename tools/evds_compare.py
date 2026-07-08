# tools/evds_compare.py
"""EVDS (TCMB) ↔ TRY_ON_RATE çapraz doğrulama (Faz 5 F5-B1, kuyruk #18).

AMAÇ: mevcut cash-yield serisi (TRY_ON_RATE) FRED/OECD rebroadcast'idir (TCMB'nin
KENDİSİ değil). Real moda geçmeden ÖNCE TCMB'nin resmî kaynağıyla (EVDS API)
karşılaştırılmalı — özellikle 2023 boşluk dönemi (9 NaN ay, forward-fill).

BU TUR ROLÜ: SNAPSHOT'I DEĞİŞTİRMEZ — yalnızca rapor + öneri üretir. Değiştirme
kararı AYRI onaylı bir turdur (KALICI KAYIT 6 çekince b). Kimlik bilgisi (API
anahtarı) HİÇBİR çıktıya yazılmaz.

KULLANIM:  .venv/bin/python -m tools.evds_compare
Anahtar (EVDS_API_KEY) yoksa: madde atlanır, blocker raporlanır.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

# EVDS aday politika/gecelik faiz seri kodları (endpoint doğrulanınca sabitlenecek).
EVDS_SERIES_CANDIDATES = {
    "TP.APIFON4": "1 hafta repo (politika faizi) — aday",
    "TP.APIFON1": "gecelik borç alma — aday",
    "TP.APIFON2": "gecelik borç verme — aday",
}
EVDS_HOSTS = ["evds2.tcmb.gov.tr", "evds3.tcmb.gov.tr"]
TRY_ON_RATE = Path("data/snapshots/aux/2026-07-07/TRY_ON_RATE.parquet")
OUT_DIR = Path("runtime/f5b1")


def _mask(text: str, key: str | None) -> str:
    return text.replace(key, "<KEY>") if key else text


def try_fetch_evds(key: str) -> dict:
    """EVDS API'yi birden fazla host/auth ile dener. JSON dönerse ayrıştırır.
    Döner: {"ok": bool, "series": {code: pd.Series}, "diagnostics": [...]}."""
    import requests
    diag = []
    series: dict[str, pd.Series] = {}
    for host in EVDS_HOSTS:
        for code in EVDS_SERIES_CANDIDATES:
            url = (f"https://{host}/service/evds/series={code}"
                   f"&startDate=01-01-2005&endDate=01-07-2026&type=json")
            try:
                r = requests.get(url, headers={"key": key}, timeout=25, allow_redirects=False)
                ctype = r.headers.get("content-type", "")
                is_json = ctype.startswith("application/json") or r.text.strip().startswith("{")
                diag.append({"host": host, "code": code, "status": r.status_code,
                             "ctype": ctype, "json": is_json,
                             "redirect": r.headers.get("location")})
                if r.status_code == 200 and is_json:
                    j = r.json()
                    items = j.get("items", []) if isinstance(j, dict) else []
                    if items:
                        idx = pd.to_datetime([it.get("Tarih") for it in items], dayfirst=True)
                        vals = [float(it.get(code.replace(".", "_"), "nan") or "nan")
                                for it in items]
                        series[code] = pd.Series(vals, index=idx, name=code)
            except Exception as e:
                diag.append({"host": host, "code": code, "error": type(e).__name__})
    return {"ok": bool(series), "series": series, "diagnostics": diag}


def _parse_evds_dates(col: pd.Series) -> pd.DatetimeIndex:
    """EVDS aylık tarih kolonu (çeşitli formatlar: 2024-1, 2024-01, 01-2024, 2024-01-01)."""
    raw = col.astype(str).str.strip()
    dt = pd.to_datetime(raw, errors="coerce")
    if dt.isna().mean() > 0.5:  # 'YYYY-M' gibi → başına gün ekle
        dt = pd.to_datetime(raw + "-01", errors="coerce")
    if dt.isna().mean() > 0.5:  # 'M-YYYY' → dayfirst
        dt = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    return pd.DatetimeIndex(dt).tz_localize("UTC")


def load_evds_csv(path: Path | str, date_col: Optional[str] = None,
                  value_col: Optional[str] = None) -> pd.Series:
    """EVDS web arayüzünden ELLE export edilen CSV → aylık rate_pct serisi (kuyruk #18
    endpoint düzelmeden kullanıcı export'uyla kapatılabilir). Kolon eşleme otomatik
    (Tarih/Date + değer) ya da açıkça verilir; ondalık virgül normalize edilir."""
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        df = pd.read_csv(path, sep=";")
    if date_col is None:
        date_col = next((c for c in df.columns
                         if c.lower() in ("tarih", "date", "observation_date")), df.columns[0])
    if value_col is None:
        cands = [c for c in df.columns if c != date_col]
        value_col = cands[-1] if cands else df.columns[-1]
    idx = _parse_evds_dates(df[date_col])
    vals = pd.to_numeric(df[value_col].astype(str).str.replace(",", ".", regex=False),
                         errors="coerce")
    s = pd.Series(vals.values, index=idx, name="rate_pct")
    return s[s.notna()].sort_index()


def compare_to_baseline(evds: pd.Series, label: str) -> dict:
    """EVDS serisini TRY_ON_RATE ile aylık hizala, fark hesapla, CSV yaz. 2023 boşluk
    dönemi ayrıca raporlanır (mevcut serinin en zayıf yeri)."""
    base = pd.read_parquet(TRY_ON_RATE)["rate_pct"]
    base.index = pd.to_datetime(base.index, utc=True)
    ev = evds.resample("MS").last()
    joined = pd.concat([base.rename("try_on_rate"), ev.rename("evds")], axis=1)
    joined["diff"] = joined["evds"] - joined["try_on_rate"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joined.to_csv(OUT_DIR / f"evds_compare_{label}.csv")
    both = joined.dropna(subset=["try_on_rate", "evds"])
    gap_2023 = joined.loc["2023-01":"2023-12"]
    return {
        "label": label, "overlap_months": int(len(both)),
        "mean_abs_diff": float(both["diff"].abs().mean()) if len(both) else None,
        "max_abs_diff": float(both["diff"].abs().max()) if len(both) else None,
        "max_diff_month": str(both["diff"].abs().idxmax().date()) if len(both) else None,
        "gap_2023_evds_available": int(gap_2023["evds"].notna().sum()),
        "gap_2023_base_missing": int(gap_2023["try_on_rate"].isna().sum()),
        "csv": str(OUT_DIR / f"evds_compare_{label}.csv"),
    }


def characterize_baseline() -> dict:
    """Mevcut TRY_ON_RATE (FRED/OECD) tanımı — EVDS gelince kıyas tabanı."""
    r = pd.read_parquet(TRY_ON_RATE)["rate_pct"]
    r.index = pd.to_datetime(r.index)
    nan_months = [str(d.date()) for d in r[r.isna()].index]
    return {
        "source": "FRED IRSTCI01TRM156N (OECD MEI, Turkey interbank call money, monthly)",
        "range": [str(r.index[0].date()), str(r.index[-1].date())],
        "n": int(len(r)), "nan_count": int(r.isna().sum()),
        "nan_months": nan_months,
        "note_2023_gap": ("2023 Şubat–Haziran + Eylül–Aralık NaN → forward-fill. Bu, "
                          "TCMB'nin agresif faiz artırım dönemidir; ff GERÇEĞİN ALTINDA "
                          "kalır → cash-yield DÜŞÜK tahakkuk eder (strateji lehine MUHAFAZAKÂR)."),
        "recent_values": {str(d.date()): (None if pd.isna(v) else float(v))
                          for d, v in r.tail(6).items()},
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="EVDS↔TRY_ON_RATE çapraz doğrulama (F5-B1)")
    ap.add_argument("--csv", default=None,
                    help="EVDS web export CSV (endpoint çalışmıyorsa elle export ile kapat)")
    ap.add_argument("--date-col", default=None)
    ap.add_argument("--value-col", default=None)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("EVDS_API_KEY")
    if not key:
        env = Path("config/secrets.env")
        if env.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env)
                key = os.environ.get("EVDS_API_KEY")
            except Exception:
                pass

    baseline = characterize_baseline()
    report = {"baseline": baseline, "evds_key_present": bool(key),
              "snapshot_modified": False}

    # ÖNCELİK: elle export edilen CSV (kuyruk #18'i endpoint olmadan kapatır).
    if args.csv:
        try:
            ev = load_evds_csv(args.csv, args.date_col, args.value_col)
            report["csv_input"] = {"path": args.csv, "rows": int(len(ev)),
                                   "range": [str(ev.index[0].date()), str(ev.index[-1].date())] if len(ev) else None}
            report["comparison"] = compare_to_baseline(ev, label="csv")
            report["status"] = "OK — CSV ile karşılaştırma yazıldı (endpoint gerekmedi)"
        except Exception as e:
            report["status"] = f"CSV OKUMA HATASI: {type(e).__name__}: {e}"
    elif not key:
        report["status"] = "SKIPPED — EVDS_API_KEY yok (ve --csv verilmedi)"
    else:
        res = try_fetch_evds(key)
        report["evds_diagnostics"] = res["diagnostics"]
        if res["ok"]:
            # karşılaştırma: aylık hizala, fark hesapla
            base = pd.read_parquet(TRY_ON_RATE)["rate_pct"]
            base.index = pd.to_datetime(base.index).tz_localize(None)
            comp = {}
            for code, s in res["series"].items():
                m = s.resample("MS").last()
                joined = pd.concat([base.rename("try_on_rate"), m.rename(code)], axis=1)
                joined["diff"] = joined[code] - joined["try_on_rate"]
                comp[code] = {"mean_abs_diff": float(joined["diff"].abs().mean()),
                              "max_abs_diff": float(joined["diff"].abs().max())}
                joined.to_csv(OUT_DIR / f"evds_compare_{code}.csv")
            report["status"] = "OK — EVDS verisi çekildi, karşılaştırma yazıldı"
            report["comparison"] = comp
        else:
            report["status"] = ("BLOCKED — EVDS_API_KEY var ama REST endpoint JSON "
                                "döndürmedi (evds2→evds3 SPA yönlendirmesi). Endpoint/auth "
                                "doğrulanmalı (TCMB evds3 dokümanı) ya da seri CSV elle export edilmeli.")

    (OUT_DIR / "evds_comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("STATUS:", report["status"])
    print("baseline nan_months:", baseline["nan_count"])
    print("snapshot_modified:", report["snapshot_modified"])


if __name__ == "__main__":
    main()

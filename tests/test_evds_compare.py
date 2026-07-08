# tests/test_evds_compare.py
"""F5-B1.1 K8 — EVDS elle-export CSV girdi modu (OFFLINE)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tools.evds_compare import load_evds_csv, compare_to_baseline


def test_load_evds_csv_iso_dates(tmp_path: Path):
    p = tmp_path / "evds.csv"
    p.write_text("Tarih,TP.APIFON4\n2023-07-01,16,0\n".replace(",0", ""))  # basit
    p.write_text("Tarih,TP_APIFON4\n2023-07-01,16.0\n2023-08-01,23.5\n")
    s = load_evds_csv(p)
    assert len(s) == 2
    assert s.index[0].tzinfo is not None
    assert abs(s.iloc[1] - 23.5) < 1e-9


def test_load_evds_csv_year_month_and_comma_decimal(tmp_path: Path):
    p = tmp_path / "evds2.csv"
    # 'YYYY-M' formatı + ondalık virgül (Türkçe export)
    p.write_text("Tarih;Politika Faizi\n2024-1;43,5\n2024-2;43,5\n")
    s = load_evds_csv(p)
    assert len(s) == 2
    assert abs(s.iloc[0] - 43.5) < 1e-9
    assert str(s.index[0].date()) == "2024-01-01"


def test_load_evds_csv_skips_trailing_empty_column(tmp_path: Path):
    """Gerçek EVDS export'unda sondaki virgül boş 'Unnamed: 2' kolonu üretir; otomatik
    value_col seçimi bunu ATLAMALI (aksi halde sessizce 0 satır okunurdu)."""
    p = tmp_path / "evds_trailing.csv"
    p.write_text("Tarih,TP_BISTTLREF_ORAN,Unnamed: 2\n"
                 "28-12-2018,23.8738,\n31-12-2018,25.1258,\n02-01-2019,23.0117,\n")
    s = load_evds_csv(p)   # value_col verilmedi → boş kolon atlanmalı
    assert len(s) == 3
    assert abs(s.iloc[0] - 23.8738) < 1e-6


def test_compare_to_baseline_structure(tmp_path: Path):
    # gerçek TRY_ON_RATE snapshot'ıyla karşılaştır (varsa)
    if not Path("data/snapshots/aux/2026-07-07/TRY_ON_RATE.parquet").exists():
        pytest.skip("TRY_ON_RATE snapshot yok")
    idx = pd.date_range("2023-01-01", "2023-12-01", freq="MS", tz="UTC")
    ev = pd.Series([30.0 + i for i in range(len(idx))], index=idx, name="rate_pct")
    rep = compare_to_baseline(ev, label="test")
    assert "overlap_months" in rep and "max_abs_diff" in rep
    assert rep["gap_2023_base_missing"] >= 1   # 2023 boşluğu var
    assert Path(rep["csv"]).exists()

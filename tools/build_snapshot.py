# tools/build_snapshot.py
"""Piyasa-parametrik snapshot dondurma aracı (EXPANSION.md Bölüm 6.2,
HARDENING.md A1'in genelleştirilmiş hali). `data/snapshots/<market>/<tarih>/`
altına parquet + manifest.json (sha256 hash'li) yazar.

Salt-okunur DEĞİLDİR — yeni bir snapshot dizini OLUŞTURUR, ama var olan hiçbir
snapshot'a (BIST dahil) dokunmaz/üzerine yazmaz.
"""
from __future__ import annotations
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from data.adapters.base import AdapterMeta, DataAdapter


def build_snapshot(
    market_id: str,
    symbols: list[str],
    adapter: DataAdapter,
    start_date: date,
    out_dir: Path,
    scope_note: str = "",
) -> dict:
    """Her sembol için `adapter.fetch_history` ile tam tarihçeyi indirir,
    `out_dir/<SEMBOL>.parquet` olarak yazar, sha256/bayt/satır bilgisiyle
    `manifest.json` üretir. Döner: manifest dict'i (test edilebilirlik için)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict] = {}
    last_meta: AdapterMeta | None = None

    for symbol in symbols:
        df, meta = adapter.fetch_history(symbol, "1d", start=start_date)
        last_meta = meta
        path = out_dir / f"{symbol}.parquet"
        df.to_parquet(path)
        raw_bytes = path.read_bytes()
        files[symbol] = {
            "rows": len(df),
            "start": str(df.index[0]) if len(df) else None,
            "end": str(df.index[-1]) if len(df) else None,
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "bytes": len(raw_bytes),
        }

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "market_id": market_id,
        "scope": scope_note,
        "adapter_id": adapter.adapter_id,
        "source": last_meta.source if last_meta else "N/A",
        "correction_policy": last_meta.correction_policy if last_meta else "N/A",
        "library_version": last_meta.library_version if last_meta else "N/A",
        "volume_kind": last_meta.volume_kind if last_meta else "N/A",
        "start_date_filter": str(start_date),
        "files": files,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest

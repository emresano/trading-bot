import json

import pandas as pd

from data.adapters.base import AdapterMeta
from tools.build_snapshot import build_snapshot


class _FakeAdapter:
    adapter_id = "fake"

    def fetch_history(self, symbol, timeframe, start):
        idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
        df = pd.DataFrame({
            "open": [1.0, 2.0, 3.0], "high": [1.1, 2.1, 3.1],
            "low": [0.9, 1.9, 2.9], "close": [1.05, 2.05, 3.05],
            "volume": [100.0, 200.0, 300.0],
        }, index=idx)
        meta = AdapterMeta(adapter_id="fake", source="fake-source",
                           correction_policy="none", library_version="0.0",
                           volume_kind="shares")
        return df, meta

    def fetch_latest(self, symbol, timeframe, lookback):
        raise NotImplementedError


def test_build_snapshot_writes_parquet_and_manifest(tmp_path):
    manifest = build_snapshot("fake_market", ["SYM1", "SYM2"], _FakeAdapter(),
                              start_date=pd.Timestamp("2024-01-01").date(), out_dir=tmp_path,
                              scope_note="test scope")

    assert (tmp_path / "SYM1.parquet").exists()
    assert (tmp_path / "SYM2.parquet").exists()
    assert (tmp_path / "manifest.json").exists()

    assert manifest["market_id"] == "fake_market"
    assert manifest["adapter_id"] == "fake"
    assert manifest["scope"] == "test scope"
    assert set(manifest["files"].keys()) == {"SYM1", "SYM2"}
    assert manifest["files"]["SYM1"]["rows"] == 3

    on_disk_manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert on_disk_manifest == manifest


def test_build_snapshot_sha256_matches_actual_file_bytes(tmp_path):
    import hashlib
    manifest = build_snapshot("fake_market", ["SYM1"], _FakeAdapter(),
                              start_date=pd.Timestamp("2024-01-01").date(), out_dir=tmp_path)
    actual_hash = hashlib.sha256((tmp_path / "SYM1.parquet").read_bytes()).hexdigest()
    assert manifest["files"]["SYM1"]["sha256"] == actual_hash

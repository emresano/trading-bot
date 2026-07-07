# tests/test_golden_bist.py
"""BIST v7.1 golden regresyon çapası (EXPANSION.md Bölüm 0.2) — E2+'nın MUTLAK kuralı.

Bu test E2 ve sonrasındaki HER commit'te YEŞİL kalmak zorundadır: BIST profili +
v7 snapshot'ı + v7 config'i ile koşulan backtest, `tests/golden/bist_v7_trades.csv`
ile BAYT-BAYT aynı trades.csv üretir. Kırmızıyken hiçbir E-işi commitlenmez.

Golden dosya yalnızca kullanıcı onaylı bir "taban çizgisi güncelleme" turunda
değişebilir (gerekçe commit mesajına yazılır).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from backtest.golden_bist import GOLDEN_TRADES, reproduce_golden_trades_bytes

# runtime/backtest_reports_v7_1/MANIFEST.json::trades_csv_sha256
GOLDEN_SHA256 = "08fa8ea80034883383662cce37ad51eef5074ec91060410828aa5c732891fd33"


def test_golden_file_hash_pinned():
    """Golden dosyanın kendisi beklenen SHA256'ya sahip (yanlışlıkla değişmemiş)."""
    digest = hashlib.sha256(GOLDEN_TRADES.read_bytes()).hexdigest()
    assert digest == GOLDEN_SHA256, (
        f"Golden dosya hash'i değişmiş: {digest} != {GOLDEN_SHA256}. "
        "Golden yalnızca kullanıcı onaylı taban-çizgisi güncelleme turunda değişebilir."
    )


def test_bist_backtest_byte_identical_to_golden(tmp_path: Path):
    """Çekirdek motorun BIST çıktısı golden ile bayt-bayt aynı (E2 regresyon çapası)."""
    if not GOLDEN_TRADES.exists():
        pytest.skip("golden dosya yok")
    got = reproduce_golden_trades_bytes(breaker_file=tmp_path / "BREAKER_golden")
    want = GOLDEN_TRADES.read_bytes()
    assert got == want, (
        "BIST backtest çıktısı golden'dan SAPTI — E2 çekirdek genelleştirmesi "
        "BIST davranışını değiştirdi. Commit YASAK; önce sapmayı gider."
    )


def test_daily_carry_hook_is_bist_safe(tmp_path: Path):
    """daily_carry hook'u BIST CostModel'iyle (carry=0) çalıştırıldığında da çıktı
    golden ile bit-bit aynı (EXPANSION.md 7.1 — 'BIST/US 0 döndürdüğünden bit-bit aynı')."""
    if not GOLDEN_TRADES.exists():
        pytest.skip("golden dosya yok")
    from costs.bist import BistCostModel
    from core.config import load_config
    from backtest.golden_bist import GOLDEN_CONFIG

    cfg = load_config(str(GOLDEN_CONFIG))
    cm = BistCostModel(cfg.costs.commission_bps, cfg.costs.slippage_bps)
    got = reproduce_golden_trades_bytes(breaker_file=tmp_path / "BREAKER_carry", cost_model=cm)
    assert got == GOLDEN_TRADES.read_bytes(), (
        "daily_carry hook'u BIST CostModel'iyle golden'ı bozdu — carry 0 olmalıydı."
    )

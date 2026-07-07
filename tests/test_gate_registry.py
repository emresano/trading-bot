# tests/test_gate_registry.py
"""gate_registry davranış-nötr göç + hata sözleşmesi testleri (EXPANSION.md 8)."""
from __future__ import annotations

import pytest

from strategy.gate_registry import (
    BIST_ENTRY_PROFILE,
    FX_ENTRY_PROFILE,
    GATE_REGISTRY,
    build_entry_gates,
)
from strategy.signal_engine import ENTRY_GATES, GATE_NAMES


def test_bist_profile_reproduces_entry_gates_exactly():
    """BIST profili mevcut ENTRY_GATES'i birebir (aynı nesne, aynı sıra) üretir."""
    assert BIST_ENTRY_PROFILE == GATE_NAMES
    assert build_entry_gates(BIST_ENTRY_PROFILE) == list(ENTRY_GATES)


def test_registry_covers_all_gates():
    assert set(GATE_REGISTRY) == set(GATE_NAMES)


def test_unknown_gate_name_raises():
    with pytest.raises(ValueError, match="Bilinmeyen gate adı"):
        build_entry_gates(["trend", "nonexistent_gate"])


def test_fx_profile_excludes_volume():
    """FX profilinde volume gate'i YOK (Bölüm 1/8 gerekçesi)."""
    assert "volume" not in FX_ENTRY_PROFILE
    # geri kalan tüm gate'ler kayıtlı
    gates = build_entry_gates(FX_ENTRY_PROFILE)
    assert len(gates) == len(FX_ENTRY_PROFILE) == 9


def test_evaluate_entry_default_path_unchanged():
    """gates/gate_names verilmeyince evaluate_entry ENTRY_GATES kullanır
    (imza eklerinin davranış-nötrlüğü)."""
    import inspect

    from strategy import signal_engine

    sig = inspect.signature(signal_engine.evaluate_entry)
    assert sig.parameters["gates"].default is None
    assert sig.parameters["gate_names"].default is None

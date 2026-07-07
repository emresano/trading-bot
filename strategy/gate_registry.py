# strategy/gate_registry.py
"""Gate profilleri + registry (EXPANSION.md Bölüm 8).

CLAUDE.md Bölüm 17'de "gate listesini config'ten seçilebilir yapmak — şimdilik
YAGNI" denmişti; çok-piyasa ile YAGNI bitti (bu refactor E2'nin parçası).

DAVRANIŞ-NÖTR GÖÇ: `build_entry_gates(BIST_ENTRY_PROFILE)`, strategy.signal_engine'in
mevcut `ENTRY_GATES` listesini AYNI sıra ve AYNI fonksiyon nesneleriyle üretir —
BIST çıktısı golden ile bayt-bayt aynı kalır (tests/test_golden_bist.py kanıtlar).
Registry yalnızca YENİ bir seçim mekanizması ekler; mevcut değerlendirme yolunu
değiştirmez.
"""
from __future__ import annotations

from strategy.signal_engine import (
    ENTRY_GATES,
    GATE_NAMES,
    Gate,
    gate_atr_anomaly,
    gate_bb_overextension,
    gate_macd,
    gate_mtf,
    gate_regime,
    gate_rsi,
    gate_structure_rr,
    gate_trend,
    gate_trigger_4h,
    gate_volume,
)

# isim → gate fonksiyonu (EXPANSION.md 8). Çekirdek gate havuzu.
GATE_REGISTRY: dict[str, Gate] = {
    "trend": gate_trend,
    "regime": gate_regime,
    "rsi": gate_rsi,
    "macd": gate_macd,
    "atr_anomaly": gate_atr_anomaly,
    "bb_overextension": gate_bb_overextension,
    "structure_rr": gate_structure_rr,
    "volume": gate_volume,
    "trigger_4h": gate_trigger_4h,
    "mtf": gate_mtf,
}

# BIST profili = bugünkü ENTRY_GATES sırasının birebir isim listesi (Bölüm 8).
BIST_ENTRY_PROFILE: list[str] = list(GATE_NAMES)

# FX profili: volume YOK (Bölüm 1/8 gerekçesi — merkezî hacim yok). Referans;
# fiilen two_sided short gate seti tanımlanana dek aktive edilmez (Bölüm 8).
FX_ENTRY_PROFILE: list[str] = [
    "trend", "regime", "rsi", "macd", "atr_anomaly", "bb_overextension",
    "structure_rr", "trigger_4h", "mtf",
]


def build_entry_gates(profile: list[str]) -> list[Gate]:
    """config/markets/<id>.yaml -> gate_profile.entry listesinden huniyi kurar.
    Bilinmeyen isim = başlatma hatası (sessiz atlama YASAK — Bölüm 8)."""
    gates: list[Gate] = []
    for name in profile:
        try:
            gates.append(GATE_REGISTRY[name])
        except KeyError as exc:
            raise ValueError(
                f"Bilinmeyen gate adı: '{name}' (kayıtlı: {sorted(GATE_REGISTRY)}). "
                "gate_profile.entry listesi yalnızca kayıtlı gate'leri içerebilir."
            ) from exc
    return gates


def _assert_bist_profile_identical() -> None:
    """Davranış-nötr göç invaryantı: BIST profili tam olarak ENTRY_GATES'i üretir
    (aynı nesneler, aynı sıra). İmport-zamanı ucuz sağlık kontrolü."""
    built = build_entry_gates(BIST_ENTRY_PROFILE)
    assert built == list(ENTRY_GATES), "BIST gate profili ENTRY_GATES ile birebir eşleşmiyor"


_assert_bist_profile_identical()

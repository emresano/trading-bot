# tests/test_portfolio_config.py
"""Portföy + piyasa config yükleyici testleri (EXPANSION.md Bölüm 11)."""
from __future__ import annotations

import copy

import pytest
import yaml

from core.config import ConfigError
from core.markets import clear_registry, get_market
from core.portfolio_config import load_portfolio_config


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry()
    yield
    clear_registry()


def test_load_portfolio_registers_all_sleeves():
    pc = load_portfolio_config()
    assert set(pc.sleeves) == {"bist", "us", "fx"}
    # sadece bist enabled
    assert pc.sleeves["bist"].enabled is True
    assert pc.sleeves["us"].enabled is False
    assert pc.sleeves["fx"].enabled is False
    # registry dolduruldu
    assert get_market("bist").calendar_id == "XIST"
    assert get_market("us").calendar_id == "XNYS"
    assert get_market("fx").calendar_id == "FX_24_5"
    assert get_market("fx").direction_mode == "two_sided"
    assert get_market("fx").max_leverage == 5.0
    assert get_market("us").account_type == "cash"


def test_global_config():
    pc = load_portfolio_config()
    assert pc.global_cfg.global_max_open_positions == 5
    assert pc.global_cfg.global_dd_alert_pct == 0.15
    assert pc.base_reporting_currency == "TRY"


def test_bist_equivalence_passes_with_shipped_configs():
    """Gönderilen config.yaml + bist.yaml eşdeğerlik doğrulamasından geçer."""
    pc = load_portfolio_config()
    assert pc.sleeves["bist"].market_spec.cost_model_id == "bist"


def test_bist_equivalence_fails_on_cost_mismatch(tmp_path, monkeypatch):
    """bist.yaml costs config.yaml'dan saparsa başlatma reddedilir (11.4)."""
    # Bozuk bir bist.yaml + portfolio.yaml üret
    bist_raw = yaml.safe_load(open("config/markets/bist.yaml"))
    bist_raw["costs"]["commission_bps"] = 999  # config.yaml 10 → uyumsuz
    bad_bist = tmp_path / "bist.yaml"
    bad_bist.write_text(yaml.safe_dump(bist_raw), encoding="utf-8")

    port_raw = yaml.safe_load(open("config/portfolio.yaml"))
    port_raw["sleeves"] = {"bist": {**port_raw["sleeves"]["bist"], "market_config": str(bad_bist)}}
    bad_port = tmp_path / "portfolio.yaml"
    bad_port.write_text(yaml.safe_dump(port_raw), encoding="utf-8")

    with pytest.raises(ConfigError, match="11.4 eşdeğerlik ihlali"):
        load_portfolio_config(bad_port)


def test_bist_equivalence_fails_on_gate_mismatch(tmp_path):
    bist_raw = yaml.safe_load(open("config/markets/bist.yaml"))
    bist_raw["gate_profile"]["entry"] = ["trend", "regime"]  # eksik → uyumsuz
    bad_bist = tmp_path / "bist.yaml"
    bad_bist.write_text(yaml.safe_dump(bist_raw), encoding="utf-8")

    port_raw = yaml.safe_load(open("config/portfolio.yaml"))
    port_raw["sleeves"] = {"bist": {**port_raw["sleeves"]["bist"], "market_config": str(bad_bist)}}
    bad_port = tmp_path / "portfolio.yaml"
    bad_port.write_text(yaml.safe_dump(port_raw), encoding="utf-8")

    with pytest.raises(ConfigError, match="gate_profile.entry"):
        load_portfolio_config(bad_port)


def test_invalid_direction_mode_rejected(tmp_path):
    """MarketSpec geçersiz direction_mode → hata (core/markets __post_init__)."""
    us_raw = yaml.safe_load(open("config/markets/us_equities.yaml"))
    us_raw["market"]["direction_mode"] = "sideways_only"
    bad_us = tmp_path / "us.yaml"
    bad_us.write_text(yaml.safe_dump(us_raw), encoding="utf-8")

    port_raw = yaml.safe_load(open("config/portfolio.yaml"))
    port_raw["sleeves"] = {"us": {**port_raw["sleeves"]["us"], "market_config": str(bad_us)}}
    bad_port = tmp_path / "portfolio.yaml"
    bad_port.write_text(yaml.safe_dump(port_raw), encoding="utf-8")

    with pytest.raises(ValueError, match="direction_mode"):
        load_portfolio_config(bad_port)

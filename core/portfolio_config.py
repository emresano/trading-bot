# core/portfolio_config.py
"""Portföy + piyasa config yükleyici (EXPANSION.md Bölüm 11).

core/config.py'ye DOKUNMAZ (BIST golden yolu load_config'i kullanır) — bu ayrı,
additif bir yükleyicidir. Sorumluluklar:
  1. config/portfolio.yaml → sleeve tahsisleri + global limitler.
  2. Her sleeve'in market_config'i → MarketSpec, MARKET_REGISTRY'ye kaydeder.
  3. BIST için 11.4 eşdeğerlik doğrulaması: config/markets/bist.yaml'ın costs ve
     gate_profile'ı, config/config.yaml + strategy.gate_registry.BIST_ENTRY_PROFILE
     ile EŞDEĞER olmalı — fark = başlatma hatası (ConfigError).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from core.config import ConfigError, load_config
from core.markets import MarketSpec, register_market


@dataclass(frozen=True)
class SleeveConfig:
    sleeve_id: str
    enabled: bool
    mode: str
    allocation: float
    market_config: str
    market_spec: MarketSpec


@dataclass(frozen=True)
class GlobalConfig:
    global_max_open_positions: int
    global_dd_alert_pct: float
    kill_switch_file: str


@dataclass(frozen=True)
class PortfolioConfig:
    base_reporting_currency: str
    fx_rate_source: str
    sleeves: dict[str, SleeveConfig]
    global_cfg: GlobalConfig


def _load_yaml(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"config: dosya bulunamadı: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ConfigError(f"config: '{path}' geçerli bir YAML sözlüğü değil")
    return raw


def _build_market_spec(market_raw: dict, market_id_expected: str) -> MarketSpec:
    m = market_raw
    try:
        spec = MarketSpec(
            market_id=m["market_id"],
            calendar_id=m["calendar_id"],
            currency=m["currency"],
            direction_mode=m["direction_mode"],
            settlement_days=m["settlement_days"],
            qty_step=m["qty_step"],
            price_decimals=m["price_decimals"],
            cost_model_id=m["cost_model_id"],
            gate_profile_id=m["market_id"],
            data_adapter_id=m["data_adapter_id"],
            eval_after_close_min=m.get("eval_after_close_min", 10),
            pip_size=m.get("pip_size"),
            max_leverage=m.get("max_leverage"),
            account_type=m.get("account_type", "cash"),
        )
    except KeyError as exc:
        raise ConfigError(f"market config: zorunlu alan eksik: {exc}") from exc
    if spec.market_id != market_id_expected:
        raise ConfigError(
            f"market config: market_id '{spec.market_id}' beklenen '{market_id_expected}' ile uyuşmuyor"
        )
    return spec


def _validate_bist_equivalence(bist_market_cfg: dict) -> None:
    """11.4: bist.yaml ↔ config.yaml + ENTRY_GATES eşdeğerliği. Fark = başlatma hatası."""
    from strategy.gate_registry import BIST_ENTRY_PROFILE

    base = load_config("config/config.yaml")

    costs = bist_market_cfg.get("costs", {})
    if costs.get("commission_bps") != base.costs.commission_bps:
        raise ConfigError(
            f"11.4 eşdeğerlik ihlali: bist.yaml commission_bps={costs.get('commission_bps')} "
            f"!= config.yaml {base.costs.commission_bps}"
        )
    if costs.get("slippage_bps") != base.costs.slippage_bps:
        raise ConfigError(
            f"11.4 eşdeğerlik ihlali: bist.yaml slippage_bps={costs.get('slippage_bps')} "
            f"!= config.yaml {base.costs.slippage_bps}"
        )

    entry = bist_market_cfg.get("gate_profile", {}).get("entry")
    if entry != BIST_ENTRY_PROFILE:
        raise ConfigError(
            f"11.4 eşdeğerlik ihlali: bist.yaml gate_profile.entry, ENTRY_GATES ile "
            f"birebir eşleşmiyor.\n  yaml: {entry}\n  kod : {BIST_ENTRY_PROFILE}"
        )

    market = bist_market_cfg.get("market", {})
    if market.get("currency") != "TRY" or market.get("direction_mode") != "long_only":
        raise ConfigError("11.4 eşdeğerlik ihlali: bist market currency/direction_mode beklenmeyen")


def load_portfolio_config(path: str | Path = "config/portfolio.yaml") -> PortfolioConfig:
    raw = _load_yaml(path)
    sleeves_raw = raw.get("sleeves")
    if not isinstance(sleeves_raw, dict) or not sleeves_raw:
        raise ConfigError("portfolio: 'sleeves' boş olamaz")

    sleeves: dict[str, SleeveConfig] = {}
    for sid, s in sleeves_raw.items():
        market_raw = _load_yaml(s["market_config"])
        spec = _build_market_spec(market_raw.get("market", {}), sid)
        if sid == "bist":
            _validate_bist_equivalence(market_raw)
        register_market(spec)
        sleeves[sid] = SleeveConfig(
            sleeve_id=sid,
            enabled=bool(s.get("enabled", False)),
            mode=s.get("mode", "paper"),
            allocation=float(s["allocation"]),
            market_config=s["market_config"],
            market_spec=spec,
        )

    g = raw.get("global", {})
    global_cfg = GlobalConfig(
        global_max_open_positions=g.get("global_max_open_positions", 5),
        global_dd_alert_pct=g.get("global_dd_alert_pct", 0.15),
        kill_switch_file=g.get("kill_switch_file", "runtime/KILL_SWITCH"),
    )

    return PortfolioConfig(
        base_reporting_currency=raw.get("base_reporting_currency", "TRY"),
        fx_rate_source=raw.get("fx_rate_source", "yfinance:USDTRY=X"),
        sleeves=sleeves,
        global_cfg=global_cfg,
    )

# core/config.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import dotenv_values

REAL_MODE_PHRASE = "GERCEK PARA RISKINI ANLIYORUM VE KABUL EDIYORUM"


class ConfigError(Exception):
    """Config yükleme veya doğrulama hatası — başlatmayı reddetmek için fırlatılır."""


@dataclass(frozen=True)
class InstrumentConfig:
    symbol: str
    yf_symbol: str
    type: str
    lot_step: int


@dataclass(frozen=True)
class TimeframesConfig:
    trend: str
    entry: str
    source_intraday: str


@dataclass(frozen=True)
class SignalConfig:
    ema_fast: int
    ema_slow: int
    adx_period: int
    adx_min: float
    rsi_period: int
    rsi_entry_low: float
    rsi_entry_high: float
    macd: tuple[int, int, int]
    atr_period: int
    atr_stop_mult: float
    atr_anomaly_mult: float
    bb_period: int
    bb_std: float
    swing_lookback: int
    swing_fractal_n: int
    volume_confirm_mult: float
    min_history_bars: int


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_pct: float
    daily_loss_limit_pct: float
    weekly_loss_limit_pct: float
    max_open_positions: int
    max_position_notional_pct: float
    max_drawdown_breaker_pct: float
    min_rr: float
    correlation_lookback_days: int
    correlation_max: float
    news_blackout: bool


@dataclass(frozen=True)
class CostsConfig:
    commission_bps: float
    slippage_bps: float


@dataclass(frozen=True)
class WalkForwardConfig:
    train_months: int
    test_months: int
    step_months: int


@dataclass(frozen=True)
class BacktestConfig:
    start: str
    end: str
    initial_equity: float
    walk_forward: WalkForwardConfig
    monte_carlo_runs: int
    random_seed: int


@dataclass(frozen=True)
class ExecutionConfig:
    bar_close_grace_sec: int
    order_timeout_sec: int
    algolab_throttle_sec: float


@dataclass(frozen=True)
class PaperConfig:
    initial_equity: float
    fill_model: str


@dataclass(frozen=True)
class SafetyConfig:
    heartbeat_interval_sec: int
    heartbeat_stale_sec: int
    reconciliation_interval_min: int
    kill_switch_file: str
    max_price_jump_pct: float


@dataclass(frozen=True)
class TelegramConfig:
    enabled: bool


@dataclass(frozen=True)
class Config:
    mode: str
    real_mode_confirmation: str
    timezone: str
    instruments: tuple[InstrumentConfig, ...]
    timeframes: TimeframesConfig
    signal: SignalConfig
    risk: RiskConfig
    costs: CostsConfig
    backtest: BacktestConfig
    execution: ExecutionConfig
    paper: PaperConfig
    safety: SafetyConfig
    telegram: TelegramConfig


def _require(d: dict, key: str, ctx: str) -> object:
    if key not in d:
        raise ConfigError(f"config: '{ctx}.{key}' alanı eksik")
    return d[key]


def _build_instruments(raw: list) -> tuple[InstrumentConfig, ...]:
    if not raw:
        raise ConfigError("config: 'instruments' listesi boş olamaz")
    out = []
    seen = set()
    for i, item in enumerate(raw):
        symbol = _require(item, "symbol", f"instruments[{i}]")
        yf_symbol = _require(item, "yf_symbol", f"instruments[{i}]")
        itype = _require(item, "type", f"instruments[{i}]")
        lot_step = _require(item, "lot_step", f"instruments[{i}]")
        if symbol in seen:
            raise ConfigError(f"config: 'instruments' içinde tekrarlanan sembol: {symbol}")
        seen.add(symbol)
        if not isinstance(lot_step, int) or lot_step <= 0:
            raise ConfigError(f"config: instruments[{i}].lot_step pozitif tam sayı olmalı")
        out.append(InstrumentConfig(symbol=symbol, yf_symbol=yf_symbol, type=itype, lot_step=lot_step))
    return tuple(out)


def _in_range(value: float, lo: float, hi: float, name: str, inclusive_hi: bool = False) -> None:
    ok = (lo < value <= hi) if inclusive_hi else (lo < value < hi)
    if not ok:
        bound = f"({lo}, {hi}]" if inclusive_hi else f"({lo}, {hi})"
        raise ConfigError(f"config: '{name}'={value} geçerli aralıkta değil, beklenen {bound}")


def _validate(cfg: Config) -> None:
    if cfg.mode not in ("paper", "real"):
        raise ConfigError(f"config: 'mode' 'paper' veya 'real' olmalı, alınan: {cfg.mode!r}")

    if cfg.mode == "real" and cfg.real_mode_confirmation != REAL_MODE_PHRASE:
        raise ConfigError(
            "config: mode='real' için 'real_mode_confirmation' alanı birebir onay cümlesiyle "
            "eşleşmiyor. Bu alan yalnızca kullanıcının kendi eliyle doldurabileceği bir alandır."
        )

    s = cfg.signal
    if s.ema_fast >= s.ema_slow:
        raise ConfigError(f"config: signal.ema_fast ({s.ema_fast}) < signal.ema_slow ({s.ema_slow}) olmalı")
    if s.adx_min <= 0:
        raise ConfigError("config: signal.adx_min pozitif olmalı")
    if not (0 < s.rsi_entry_low < s.rsi_entry_high < 100):
        raise ConfigError("config: signal.rsi_entry_low < signal.rsi_entry_high, ikisi de (0,100) aralığında olmalı")
    if len(s.macd) != 3:
        raise ConfigError("config: signal.macd tam olarak 3 eleman içermeli [fast, slow, signal]")
    if s.atr_stop_mult <= 0 or s.atr_anomaly_mult <= 0:
        raise ConfigError("config: signal.atr_stop_mult ve signal.atr_anomaly_mult pozitif olmalı")
    if s.min_history_bars <= 0:
        raise ConfigError("config: signal.min_history_bars pozitif olmalı")

    r = cfg.risk
    _in_range(r.risk_per_trade_pct, 0, 0.02, "risk.risk_per_trade_pct")
    _in_range(r.daily_loss_limit_pct, 0, 1, "risk.daily_loss_limit_pct")
    _in_range(r.weekly_loss_limit_pct, 0, 1, "risk.weekly_loss_limit_pct")
    if r.max_open_positions <= 0:
        raise ConfigError("config: risk.max_open_positions pozitif olmalı")
    _in_range(r.max_position_notional_pct, 0, 1, "risk.max_position_notional_pct", inclusive_hi=True)
    _in_range(r.max_drawdown_breaker_pct, 0, 1, "risk.max_drawdown_breaker_pct")
    if r.min_rr <= 0:
        raise ConfigError("config: risk.min_rr pozitif olmalı")
    _in_range(r.correlation_max, 0, 1, "risk.correlation_max", inclusive_hi=True)
    if r.correlation_lookback_days <= 0:
        raise ConfigError("config: risk.correlation_lookback_days pozitif olmalı")

    c = cfg.costs
    if c.commission_bps < 0 or c.slippage_bps < 0:
        raise ConfigError("config: costs.commission_bps ve costs.slippage_bps negatif olamaz")

    b = cfg.backtest
    if b.initial_equity <= 0:
        raise ConfigError("config: backtest.initial_equity pozitif olmalı")
    if b.monte_carlo_runs <= 0:
        raise ConfigError("config: backtest.monte_carlo_runs pozitif olmalı")

    sf = cfg.safety
    if sf.heartbeat_stale_sec <= sf.heartbeat_interval_sec:
        raise ConfigError("config: safety.heartbeat_stale_sec, heartbeat_interval_sec'ten büyük olmalı")
    _in_range(sf.max_price_jump_pct, 0, 1, "safety.max_price_jump_pct")


def load_config(path: str | Path = "config/config.yaml") -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"config: dosya bulunamadı: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ConfigError(f"config: '{path}' geçerli bir YAML sözlüğü değil")

    try:
        cfg = Config(
            mode=_require(raw, "mode", "root"),
            real_mode_confirmation=raw.get("real_mode_confirmation", ""),
            timezone=_require(raw, "timezone", "root"),
            instruments=_build_instruments(_require(raw, "instruments", "root")),
            timeframes=TimeframesConfig(**_require(raw, "timeframes", "root")),
            signal=SignalConfig(**{**_require(raw, "signal", "root"), "macd": tuple(raw["signal"]["macd"])}),
            risk=RiskConfig(**_require(raw, "risk", "root")),
            costs=CostsConfig(**_require(raw, "costs", "root")),
            backtest=BacktestConfig(
                **{
                    **{k: v for k, v in _require(raw, "backtest", "root").items() if k != "walk_forward"},
                    "walk_forward": WalkForwardConfig(**raw["backtest"]["walk_forward"]),
                }
            ),
            execution=ExecutionConfig(**_require(raw, "execution", "root")),
            paper=PaperConfig(**_require(raw, "paper", "root")),
            safety=SafetyConfig(**_require(raw, "safety", "root")),
            telegram=TelegramConfig(enabled=_require(raw, "telegram", "root")["enabled"]),
        )
    except TypeError as e:
        raise ConfigError(f"config: alan eksik veya fazla — {e}") from e

    _validate(cfg)
    return cfg


def load_secrets(path: str | Path = "config/secrets.env") -> dict[str, str]:
    """Sırları dosyadan okur, os.environ'a yazmaz. Dosya yoksa boş dict döner
    (Faz 1-4 AlgoLab'a bağımlı değildir; secrets yalnızca Faz 5'te zorunludur)."""
    path = Path(path)
    if not path.exists():
        return {}
    values = dotenv_values(path)
    return {k: v for k, v in values.items() if v is not None}

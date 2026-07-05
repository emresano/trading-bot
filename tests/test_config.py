import copy
from pathlib import Path

import pytest
import yaml

from core.config import ConfigError, load_config, load_secrets, REAL_MODE_PHRASE

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def _raw_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write(tmp_path: Path, raw: dict) -> Path:
    path = tmp_path / "config.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f)
    return path


def test_default_config_loads_and_validates():
    cfg = load_config(CONFIG_PATH)
    assert cfg.mode == "paper"
    assert len(cfg.instruments) == 12
    assert cfg.signal.ema_fast < cfg.signal.ema_slow
    assert cfg.risk.max_open_positions == 2


def test_missing_file_raises():
    with pytest.raises(ConfigError):
        load_config("does/not/exist.yaml")


def test_invalid_mode_rejected(tmp_path):
    raw = _raw_config()
    raw["mode"] = "live"
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_real_mode_without_confirmation_rejected(tmp_path):
    raw = _raw_config()
    raw["mode"] = "real"
    raw["real_mode_confirmation"] = "yanlis cumle"
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_real_mode_with_exact_confirmation_accepted(tmp_path):
    raw = _raw_config()
    raw["mode"] = "real"
    raw["real_mode_confirmation"] = REAL_MODE_PHRASE
    cfg = load_config(_write(tmp_path, raw))
    assert cfg.mode == "real"


@pytest.mark.parametrize("bad_value", [0.0, 0.02, 0.05, -0.01])
def test_risk_per_trade_pct_out_of_range_rejected(tmp_path, bad_value):
    raw = _raw_config()
    raw["risk"]["risk_per_trade_pct"] = bad_value
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_ema_fast_must_be_less_than_slow(tmp_path):
    raw = _raw_config()
    raw["signal"]["ema_fast"] = 200
    raw["signal"]["ema_slow"] = 50
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_empty_instruments_rejected(tmp_path):
    raw = _raw_config()
    raw["instruments"] = []
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_duplicate_instrument_symbol_rejected(tmp_path):
    raw = _raw_config()
    raw["instruments"].append(copy.deepcopy(raw["instruments"][0]))
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_missing_required_field_rejected(tmp_path):
    raw = _raw_config()
    del raw["risk"]["min_rr"]
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_correlation_max_must_be_in_0_1(tmp_path):
    raw = _raw_config()
    raw["risk"]["correlation_max"] = 1.5
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, raw))


def test_load_secrets_missing_file_returns_empty_dict():
    assert load_secrets("does/not/exist.env") == {}


def test_load_secrets_example_file_parses(tmp_path):
    example = Path(__file__).parent.parent / "config" / "secrets.env.example"
    secrets = load_secrets(example)
    assert "ALGOLAB_API_KEY" in secrets

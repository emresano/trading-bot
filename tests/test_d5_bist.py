# tests/test_d5_bist.py
"""D5-BIST CHALLENGER birim testleri (offline araştırma spike'ı).

Kapsam:
- **Sadakat çapası**: `gate_cfg=None` → `run_regime_core_gated` D1'i BİT-BİT üretir
  (kopyalanan yürütme döngüsünün sapmadığının kanıtı).
- Kapı matematiği: trailing getiri tanımı, ham-oran (haircut'sız) bileşikleme,
  nakit tahakkukuyla formül tutarlılığı.
- Kapı durum makinesi: 3-gün açılış teyidi / 1-gün kapanış, ısınma KAPALI.
- Kısıtlayıcılık değişmezi: kapı asla D1'in kapalı olduğu günde pozisyon açtırmaz.
- Mühür bütünlüğü: `config/d5_bist.yaml` D1 sabitlerini DEVRALIR (N/b/M=200/0.01/3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest.regime_core import RegimeCoreConfig, compute_cash_only_curve, run_regime_core
from backtest.regime_core_gated import (
    GateConfig,
    compute_opportunity_gate,
    compute_trailing_returns,
    run_regime_core_gated,
)
from tools.run_d5_bist import core_config_from, load_d5_config

# ------------------------------------------------------------------ yardımcı fixture'lar


def _dates(n: int, start: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="D", tz="UTC")


def _flat_rate(idx: pd.DatetimeIndex, pct: float) -> pd.Series:
    """Sabit yıllık oran (ondalık), günlük seri."""
    return pd.Series(pct, index=idx)


def _synth_closes(n: int, symbols: list[str], drift: float = 0.0005) -> dict[str, pd.Series]:
    idx = _dates(n)
    out = {}
    for k, s in enumerate(symbols):
        base = 100.0 + k
        out[s] = pd.Series(base * np.exp(drift * np.arange(n)), index=idx)
    return out


# ============================================================ 1) SADAKAT ÇAPASI


def test_gate_none_is_bit_identical_to_d1():
    """`gate_cfg=None` → kapı yok → D1'in (backtest/regime_core.py) BİREBİR
    yeniden üretimi. Bu test, `regime_core_gated.py`'deki yürütme döngüsünün
    D1'inkinden sapmadığının KALICI kanıtıdır — sapma olursa kırmızı yanar."""
    symbols = [f"S{i}" for i in range(4)]
    closes = _synth_closes(400, symbols)
    # Rejim sinyalinin hem ON hem OFF ürettiği bir seri kurmak için ortada düşüş ekle.
    for s in symbols:
        closes[s].iloc[250:320] *= np.linspace(1.0, 0.6, 70)
    cfg = RegimeCoreConfig(symbols=symbols, ma_period=50, band_pct=0.01, confirm_days=3)
    rate = _flat_rate(closes[symbols[0]].index, 0.30)

    ref = run_regime_core(closes, cfg, cash_rate=rate)
    got = run_regime_core_gated(closes, cfg, gate_cfg=None, cash_rate=rate)

    pd.testing.assert_series_equal(got.equity_curve, ref.equity_curve, check_exact=True)
    pd.testing.assert_series_equal(got.regime_on, ref.regime_on, check_exact=True)
    pd.testing.assert_series_equal(got.composite, ref.composite, check_exact=True)
    assert [(s.date, s.action, s.equity_before, s.equity_after) for s in got.switches] == \
           [(s.date, s.action, s.equity_before, s.equity_after) for s in ref.switches]
    assert len(ref.switches) >= 2, "fixture hem ENTER hem EXIT üretmeli (test anlamlı olsun)"


def test_gate_none_bit_identical_also_without_cash_rate():
    """S1 davranışı (tahakkuk yok) da korunur."""
    symbols = ["A", "B"]
    closes = _synth_closes(300, symbols)
    cfg = RegimeCoreConfig(symbols=symbols, ma_period=50, band_pct=0.01, confirm_days=3)
    ref = run_regime_core(closes, cfg, cash_rate=None)
    got = run_regime_core_gated(closes, cfg, gate_cfg=None, cash_rate=None)
    pd.testing.assert_series_equal(got.equity_curve, ref.equity_curve, check_exact=True)


# ============================================================ 2) KAPI MATEMATİĞİ


def test_trailing_returns_definition():
    """stock_ret[t] = composite[t]/composite[t-L] - 1; ilk L bar NaN (look-ahead yok)."""
    idx = _dates(10)
    comp = pd.Series(np.arange(1, 11, dtype=float), index=idx)  # 1..10
    rate = _flat_rate(idx, 0.0)
    stock_ret, cash_ret = compute_trailing_returns(comp, rate, lookback_bars=3)

    assert stock_ret.iloc[:3].isna().all()
    assert cash_ret.iloc[:3].isna().all()
    assert stock_ret.iloc[3] == pytest.approx(4 / 1 - 1)     # comp[3]=4, comp[0]=1
    assert stock_ret.iloc[9] == pytest.approx(10 / 7 - 1)
    assert cash_ret.iloc[3] == pytest.approx(0.0)            # %0 faiz → 0 getiri


def test_cash_ret_uses_raw_rate_no_haircut():
    """Kapı SİNYALİ ham oranı kullanır (haircut=0). Haircut'lı çağrı DAHA DÜŞÜK
    nakit getirisi üretmeli — ikisinin farkı haircut'ın kendisidir."""
    idx = _dates(400)
    comp = pd.Series(100.0, index=idx)
    rate = _flat_rate(idx, 0.30)
    _, raw = compute_trailing_returns(comp, rate, 252, haircut=0.0)
    _, cut = compute_trailing_returns(comp, rate, 252, haircut=0.02)
    assert raw.iloc[-1] > cut.iloc[-1] > 0.0
    # Ham oran ACT/365 bileşiği: 252 bar = 251 takvim günü ilerleme (günlük index).
    span_days = (idx[-1] - idx[-1 - 252]).days
    assert raw.iloc[-1] == pytest.approx((1 + 0.30 / 365) ** span_days - 1, rel=1e-12)


def test_cash_ret_formula_matches_cash_only_curve():
    """Kapının nakit bileşiklemesi, motorun `compute_cash_only_curve`'ü ile AYNI
    fonksiyondan gelir (drift imkânsız) — bağımsız yeniden hesapla doğrula."""
    idx = _dates(300)
    comp = pd.Series(100.0, index=idx)
    rate = _flat_rate(idx, 0.25)
    _, cash_ret = compute_trailing_returns(comp, rate, 100, haircut=0.0)
    curve = compute_cash_only_curve(idx, rate, 1.0, haircut=0.0)
    expected = curve.iloc[299] / curve.iloc[199] - 1
    assert cash_ret.iloc[299] == pytest.approx(expected, rel=1e-15)


# ============================================================ 3) DURUM MAKİNESİ


def _gate_from_favorable(fav: list[bool], confirm: int = 3, close: int = 1) -> list[bool]:
    """`favorable` desenini doğrudan sürebilmek için: kompoziti/oranı, istenen
    favorable dizisini üretecek şekilde kurar (lookback=1, %0 faiz → favorable
    ⇔ kompozit bir önceki bara göre ARTMIŞ)."""
    n = len(fav)
    idx = _dates(n + 1)
    vals = [100.0]
    for f in fav:
        vals.append(vals[-1] * (1.01 if f else 0.99))
    comp = pd.Series(vals, index=idx)
    rate = _flat_rate(idx, 0.0)
    gate, _, _, favorable = compute_opportunity_gate(
        comp, rate, GateConfig(lookback_bars=1, confirm_days=confirm, close_days=close)
    )
    assert favorable.iloc[1:].tolist() == fav, "fixture favorable desenini üretmeli"
    return gate.iloc[1:].tolist()


def test_gate_opens_only_after_three_consecutive_confirmations():
    # 2 gün yeterli değil; 3. günde açılır.
    assert _gate_from_favorable([True, True, False, True, True, True]) == \
        [False, False, False, False, False, True]


def test_gate_closes_on_single_unfavorable_day():
    assert _gate_from_favorable([True, True, True, True, False, True]) == \
        [False, False, True, True, False, False]


def test_gate_warmup_is_closed_and_no_lookahead():
    """İlk `lookback_bars` bar tanımsız → kapı KAPALI (muhafazakâr, §1.5)."""
    idx = _dates(300)
    comp = pd.Series(np.linspace(100, 400, 300), index=idx)   # sürekli yükselen
    rate = _flat_rate(idx, 0.0)
    gate, stock_ret, _, _ = compute_opportunity_gate(comp, rate, GateConfig(lookback_bars=252))
    assert not gate.iloc[:252].any(), "ısınma barlarında kapı AÇIK olamaz"
    assert stock_ret.iloc[:252].isna().all()
    assert gate.iloc[254], "252+confirm-1 barında açılmalı (hisse >> faiz)"


def test_gate_stays_closed_when_cash_beats_stocks():
    """Yatay kompozit + yüksek faiz → kapı hiç açılmaz (fırsat maliyeti tezi)."""
    idx = _dates(400)
    comp = pd.Series(100.0, index=idx)
    rate = _flat_rate(idx, 0.45)
    gate, _, _, _ = compute_opportunity_gate(comp, rate, GateConfig(lookback_bars=252))
    assert not gate.any()


# ============================================================ 4) KISITLAYICILIK DEĞİŞMEZİ


def test_gate_can_only_restrict_never_add_exposure():
    """Efektif pozisyon = rejim_ON VE kapı_AÇIK → D5'in yatırımda olduğu HER gün
    D1 de yatırımdadır. Kapı asla yeni maruziyet AÇTIRMAZ."""
    symbols = [f"S{i}" for i in range(3)]
    closes = _synth_closes(500, symbols, drift=0.001)
    for s in symbols:
        closes[s].iloc[300:360] *= np.linspace(1.0, 0.7, 60)
    cfg = RegimeCoreConfig(symbols=symbols, ma_period=50, band_pct=0.01, confirm_days=3)
    rate = _flat_rate(closes[symbols[0]].index, 0.20)

    res = run_regime_core_gated(closes, cfg, gate_cfg=GateConfig(lookback_bars=100), cash_rate=rate)
    assert (~res.effective_on | res.regime_on).all(), "effective_on ⊆ regime_on ihlal edildi"
    assert res.effective_on.sum() <= res.regime_on.sum()


def test_gate_requires_cash_rate():
    symbols = ["A", "B"]
    closes = _synth_closes(300, symbols)
    cfg = RegimeCoreConfig(symbols=symbols, ma_period=50, band_pct=0.01, confirm_days=3)
    with pytest.raises(ValueError, match="cash_rate"):
        run_regime_core_gated(closes, cfg, gate_cfg=GateConfig(), cash_rate=None)


# ============================================================ 5) MÜHÜR BÜTÜNLÜĞÜ


def test_d5_config_inherits_sealed_d1_constants():
    """`config/d5_bist.yaml` D1 sabitlerini KOPYALAMAZ, DEVRALIR → N/b/M sapamaz."""
    cfg = load_d5_config()
    assert cfg["_inherited_from"] == "config/regime_core.yaml"
    assert (cfg["regime"]["ma_period"], cfg["regime"]["band_pct"], cfg["regime"]["confirm_days"]) \
        == (200, 0.01, 3), "D1'in mühürlü N/b/M'si değişmiş!"
    core = core_config_from(cfg)
    assert core.commission_bps == 10 and core.slippage_bps == 5
    assert core.initial_equity == 100000
    assert len(core.symbols) == 12


def test_d5_config_gate_block_is_sealed_values():
    g = load_d5_config()["gate"]
    assert g["lookback_bars"] == 252
    assert g["confirm_days"] == 3
    assert g["close_days"] == 1
    assert g["signal_rate_haircut_bps"] == 0     # sinyal eşiği HAM oran
    assert g["warmup_gate_closed"] is True


# ============================================================ 6) MÜHÜRLÜ TABLO MEKANİĞİ


def _mk(sharpe, cagr, oos, maxdd):
    return {"summary": {"sharpe": sharpe, "cagr": cagr, "max_drawdown": maxdd},
            "oos": {"oos_monthly_sharpe": oos}}


def test_sealed_table_all_pass_is_aday():
    from tools.run_d5_bist import evaluate_sealed_table
    t = evaluate_sealed_table(_mk(1.3, 0.30, 1.1, -0.25), _mk(1.2, 0.28, 1.0, -0.28))
    assert t["n_pass"] == 4 and t["mechanical_outcome"] == "ADAY"


def test_sealed_table_single_fail_is_red_no_narrow_margin():
    """'Dar fark' YOKTUR: 1e-9'luk bir eksiklik bile FAIL ve sonuç RED."""
    from tools.run_d5_bist import evaluate_sealed_table
    d1 = _mk(1.2, 0.28, 1.0, -0.28)
    t = evaluate_sealed_table(_mk(1.3, 0.28 - 1e-9, 1.1, -0.25), d1)
    assert [r["passed"] for r in t["criteria"]] == [True, False, True, True]
    assert t["n_pass"] == 3 and t["mechanical_outcome"] == "RED"


def test_sealed_table_equality_fails_strict_criteria_but_passes_maxdd():
    """Kriter 1/2/3a kesin `>` ister (eşitlik FAIL); 3b `>=` kabul eder."""
    from tools.run_d5_bist import evaluate_sealed_table
    d1 = _mk(1.2, 0.28, 1.0, -0.28)
    t = evaluate_sealed_table(_mk(1.2, 0.28, 1.0, -0.28), d1)
    assert [r["passed"] for r in t["criteria"]] == [False, False, False, True]
    assert t["mechanical_outcome"] == "RED"


def test_in_position_is_one_day_lagged_signal():
    """Motor değişmezi: pozisyon durumu = dünkü sinyal (t+1 yürütme); i=0'da nakit."""
    from tools.run_d5_bist import _in_position
    sig = pd.Series([False, True, True, False], index=_dates(4))
    assert _in_position(sig).tolist() == [False, False, True, True]


def test_spike_is_deterministic_across_two_runs():
    """Aynı frozen veri + aynı seed → bit-bit aynı eğri (tutarlılık şartı)."""
    symbols = [f"S{i}" for i in range(3)]
    closes = _synth_closes(400, symbols, drift=0.001)
    cfg = RegimeCoreConfig(symbols=symbols, ma_period=50, band_pct=0.01, confirm_days=3)
    rate = _flat_rate(closes[symbols[0]].index, 0.25)
    a = run_regime_core_gated(closes, cfg, gate_cfg=GateConfig(lookback_bars=100), cash_rate=rate)
    b = run_regime_core_gated(closes, cfg, gate_cfg=GateConfig(lookback_bars=100), cash_rate=rate)
    pd.testing.assert_series_equal(a.equity_curve, b.equity_curve, check_exact=True)
    pd.testing.assert_series_equal(a.gate_open, b.gate_open, check_exact=True)

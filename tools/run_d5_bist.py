# tools/run_d5_bist.py
"""D5-BIST CHALLENGER sürücüsü — "D1 + fırsat-maliyeti (faiz) kapısı".

STATUS.md KALICI KAYIT 23. **Offline araştırma spike'ı; üretim DEĞİL; HÜKÜM YOK.**

Mühürleme (`D5_CRITERIA.md` + `config/d5_bist.yaml`) bu dosyanın kapı-koşumu
eklenmeden ÖNCEKİ commit'inde yapıldı; `backtest/regime_core_gated.py` o commit'te
HENÜZ YOKTU — commit sırası, tasarımın sonuca göre seçilmediğinin kanıtıdır
(E4 §4 / D2US §5 / D4US §5 emsali).

İzolasyon: `mode: paper` + TÜM canlı bot modülleri + S1/S1b/E4/D2US/D4US araçları
+ TÜM snapshot'lar DOKUNULMAZ. `backtest/regime_core.py` ve
`tools/run_regime_core.py` YALNIZ **import** edilir (yeniden yazılmaz → drift
imkânsız). `config/regime_core.yaml` SALT-OKUNUR.

Kullanım:
  python -m tools.run_d5_bist --baseline-only    # D1 baseline üret + S1b'ye karşı doğrula
  python -m tools.run_d5_bist                    # tam spike: mühürlü tablo + analizler (a)-(f)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from backtest.regime_core import RegimeCoreConfig, compute_cash_only_curve, run_regime_core
from backtest.regime_core_gated import GateConfig, run_regime_core_gated
from tools.period_comparison import build_window_start_basket
from tools.run_regime_core import (
    compute_monthly_returns,
    compute_summary,
    gen_walk_forward_windows,
    load_cash_rate,
    load_closes,
    monte_carlo_monthly,
    monthly_sharpe,
)

D5_CFG_PATH = Path("config/d5_bist.yaml")
S1B_SUMMARY_PATH = Path("runtime/regime_core_s1b/summary.json")

# S1b'nin kayıtlı metriklerinin bit-bit yeniden üretilmesi için tolerans.
# 0.0 = BİREBİR aynı float. (Aynı frozen veri + aynı fonksiyonlar → sapma olmamalı.)
BIT_EXACT_TOL = 0.0


# --------------------------------------------------------------------------- config


def load_d5_config(path: str | Path = D5_CFG_PATH) -> dict:
    """`config/d5_bist.yaml`'ı yükler ve `inherit_from` ile işaret edilen D1
    config'ini (SALT-OKUNUR) altına serer. D1'in mühürlü sabitleri (symbols,
    regime.N/b/M, costs, initial_equity, backtest.snapshot, walk_forward,
    monte_carlo, cash_yield) **kopyalanmaz, devralınır** → N/b/M=200/0.01/3'ün
    aynen kaldığı yapısal garanti (elle senkronizasyon hatası imkânsız).

    D5'e özgü anahtarlar (gate, neighborhood, ...) devralınan değerleri EZER."""
    d5 = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    parent_path = d5.get("inherit_from")
    if not parent_path:
        return d5
    parent = yaml.safe_load(Path(parent_path).read_text(encoding="utf-8"))
    merged = {**parent, **{k: v for k, v in d5.items() if k != "inherit_from"}}
    merged["_inherited_from"] = parent_path
    return merged


def core_config_from(cfg: dict) -> RegimeCoreConfig:
    """D1'in MÜHÜRLÜ RegimeCoreConfig'i — devralınan değerlerden birebir kurulur."""
    reg = cfg["regime"]
    return RegimeCoreConfig(
        symbols=cfg["symbols"],
        ma_period=reg["ma_period"],
        band_pct=reg["band_pct"],
        confirm_days=reg["confirm_days"],
        commission_bps=cfg["costs"]["commission_bps"],
        slippage_bps=cfg["costs"]["slippage_bps"],
        initial_equity=cfg["initial_equity"],
    )


def load_universe(cfg: dict) -> tuple[dict[str, pd.Series], list[dict], pd.Series]:
    """S1b'nin frozen snapshot'ı + S1b'nin tarihsel TRY_ON_RATE serisi — AYNEN.
    Yeni indirme YOK (D1 baseline'ıyla bit-bit kıyaslanabilirlik şartı)."""
    closes, ghost_log = load_closes(cfg)
    cash_rate = load_cash_rate(cfg)
    if cash_rate is None:
        raise RuntimeError(
            "D5 kapısı TRY_ON_RATE serisini ZORUNLU kılar; config/regime_core.yaml "
            "cash_yield bloğu devre dışı görünüyor."
        )
    return closes, ghost_log, cash_rate


# ------------------------------------------------------------------ OOS / MC yardımı


def oos_from_reruns(
    closes: dict[str, pd.Series],
    cfg: dict,
    core_cfg: RegimeCoreConfig,
    cash_rate: pd.Series,
    runner,
    **runner_kwargs,
) -> dict:
    """S1b sürücüsüyle (tools/run_regime_core.py::main) **AYNI** walk-forward OOS
    yöntemi: her (test_start, test_end] penceresinde motoru `date_range` ile
    yeniden koş, aylık getirileri biriktir → birleşik OOS aylık-Sharpe + OOS maxDD.
    Parametre optimizasyonu YOK (N/b/M her pencerede AYNEN).

    `runner`: `run_regime_core` (D1) veya `run_regime_core_gated` (D5). İki aile de
    AYNI OOS makinesinden geçer → kıyas adil."""
    wf = cfg["walk_forward"]
    windows = gen_walk_forward_windows(
        closes[cfg["symbols"][0]].index, wf["train_months"], wf["test_months"], wf["step_months"]
    )
    oos_monthly: list[float] = []
    window_rows: list[dict] = []
    for _train_start, _train_end, test_start, test_end in windows:
        res = runner(closes, core_cfg, date_range=(test_start, test_end), cash_rate=cash_rate,
                     **runner_kwargs)
        m_ret = compute_monthly_returns(res.equity_curve)
        oos_monthly.extend(m_ret.tolist())
        window_rows.append({
            "test_start": str(test_start.date()), "test_end": str(test_end.date()),
            "test_switch_count": len(res.switches),
        })

    ser = pd.Series(oos_monthly)
    eq = (1 + ser).cumprod()
    return {
        "n_windows": len(windows),
        "oos_n_months": len(ser),
        "oos_monthly_sharpe": monthly_sharpe(ser),
        "oos_max_dd": float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0,
        "_windows": window_rows,
    }


def mc_from_curve(equity_curve: pd.Series, cfg: dict) -> dict:
    """Aylık permütasyon Monte Carlo — S1b/E4/D2US/D4US ile AYNI fonksiyon
    (`tools.run_regime_core.monte_carlo_monthly`), seed config'ten (42)."""
    mc = cfg["monte_carlo"]
    monthly = compute_monthly_returns(equity_curve)
    return monte_carlo_monthly(monthly.to_numpy(), mc["runs"], mc["random_seed"])


# ---------------------------------------------------------------- D1 baseline (benchmark)


def reproduce_d1_baseline(cfg: dict, closes: dict[str, pd.Series], cash_rate: pd.Series) -> dict:
    """**Mühürlenecek eşiklerin kaynağı.** D1'i (S1b: nakit-getirili, N/b/M mühürlü)
    aynı frozen veriyle deterministik olarak yeniden üretir ve tam metrik setini
    döndürür. Strateji kodu YOK — bu yalnızca `backtest/regime_core.py`nin
    (DEĞİŞTİRİLMEMİŞ S1/S1b simülatörü) yeniden çağrılmasıdır."""
    core_cfg = core_config_from(cfg)
    res = run_regime_core(closes, core_cfg, cash_rate=cash_rate)
    summary = compute_summary(res.equity_curve)
    oos = oos_from_reruns(closes, cfg, core_cfg, cash_rate, run_regime_core)
    return {
        "summary": summary,
        "n_switches": len(res.switches),
        "oos": {k: v for k, v in oos.items() if not k.startswith("_")},
        "monte_carlo_monthly": mc_from_curve(res.equity_curve, cfg),
        "equity_start": str(res.equity_curve.index[0]),
        "equity_end": str(res.equity_curve.index[-1]),
        "n_days": int(len(res.equity_curve)),
        "first_switch": {"date": str(res.switches[0].date.date()), "action": res.switches[0].action}
        if res.switches else None,
    }


def verify_against_s1b(baseline: dict) -> dict:
    """D1 yeniden üretiminin S1b KAYITLARIYLA **bit-bit** aynı olduğunu doğrular.
    Eşleşmezse mühürleme DURUR (RuntimeError) — eşik, kanıtlanmamış bir sayı
    üzerine mühürlenemez."""
    if not S1B_SUMMARY_PATH.exists():
        raise RuntimeError(f"S1b kaydı bulunamadı: {S1B_SUMMARY_PATH}")
    ref = json.loads(S1B_SUMMARY_PATH.read_text(encoding="utf-8"))

    checks: list[dict] = []
    for key in ("total_return", "cagr", "max_drawdown", "sharpe"):
        got, exp = baseline["summary"][key], ref["main_run"]["summary"][key]
        checks.append({"field": f"summary.{key}", "reproduced": got, "s1b_record": exp,
                       "delta": got - exp, "bit_exact": got == exp})
    pairs = [
        ("oos.oos_monthly_sharpe", baseline["oos"]["oos_monthly_sharpe"],
         ref["walk_forward"]["oos_monthly_sharpe_strategy"]),
        ("oos.oos_max_dd", baseline["oos"]["oos_max_dd"], ref["walk_forward"]["oos_max_dd_strategy"]),
        ("oos.n_windows", float(baseline["oos"]["n_windows"]), float(ref["walk_forward"]["n_windows"])),
        ("monte_carlo.dd_p5", baseline["monte_carlo_monthly"]["dd_p5"],
         ref["monte_carlo_monthly"]["dd_p5"]),
        ("n_switches", float(baseline["n_switches"]), float(ref["main_run"]["n_switches"])),
    ]
    for field, got, exp in pairs:
        checks.append({"field": field, "reproduced": got, "s1b_record": exp,
                       "delta": got - exp, "bit_exact": got == exp})

    failed = [c for c in checks if not c["bit_exact"]]
    if failed:
        raise RuntimeError(
            "D1 baseline S1b kayıtlarıyla bit-bit eşleşmedi — mühürleme DURDURULDU:\n"
            + json.dumps(failed, indent=2)
        )
    return {"all_bit_exact": True, "n_checks": len(checks), "checks": checks}


# ------------------------------------------------------------------------------- CLI


def run_baseline(cfg: dict) -> dict:
    closes, ghost_log, cash_rate = load_universe(cfg)
    print(f"evren: {len(cfg['symbols'])} sembol · snapshot: {cfg['backtest']['snapshot']}")
    print(f"N/b/M (devralındı: {cfg['_inherited_from']}): "
          f"{cfg['regime']['ma_period']}/{cfg['regime']['band_pct']}/{cfg['regime']['confirm_days']}")
    print(f"TRY_ON_RATE: {len(cash_rate)} gözlem, {cash_rate.index[0].date()} → {cash_rate.index[-1].date()}")

    baseline = reproduce_d1_baseline(cfg, closes, cash_rate)
    verification = verify_against_s1b(baseline)

    print("\n=== D1 BASELINE (mühürlenecek eşikler) ===")
    print(json.dumps({"summary": baseline["summary"], "oos": baseline["oos"],
                      "n_switches": baseline["n_switches"]}, indent=2))
    print(f"\n=== S1b bit-bit doğrulaması: {verification['n_checks']}/{verification['n_checks']} "
          f"BİREBİR (tolerans={BIT_EXACT_TOL}) ===")

    out = {
        "role": "BENCHMARK — D1 (S1b, nakit-getirili). D5'in yenmesi gereken eşik.",
        "sealed_at": "koşumdan ÖNCE (backtest/regime_core_gated.py henüz yok)",
        "config": {
            "inherited_from": cfg["_inherited_from"],
            "regime": cfg["regime"], "costs": cfg["costs"],
            "initial_equity": cfg["initial_equity"], "snapshot": cfg["backtest"]["snapshot"],
            "cash_yield": cfg["cash_yield"], "walk_forward": cfg["walk_forward"],
            "monte_carlo": cfg["monte_carlo"],
        },
        "ghost_bars_removed": [{"symbol": g["symbol"], "date": str(g["date"])} for g in ghost_log],
        "d1_baseline": baseline,
        "s1b_bit_exact_verification": verification,
    }
    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline_sealed.json").write_text(json.dumps(out, indent=2, default=str),
                                                  encoding="utf-8")
    print(f"\nYazıldı: {out_dir / 'baseline_sealed.json'}")
    return out


# ---------------------------------------------------------------- D5 (challenger) koşumu


def gate_config_from(cfg: dict, lookback: Optional[int] = None,
                     confirm: Optional[int] = None) -> GateConfig:
    """MÜHÜRLÜ kapı sabitleri (`config/d5_bist.yaml::gate`). `lookback`/`confirm`
    yalnızca **komşuluk GÖZLEMİ** (analiz e) için geçersiz kılınır — seçim aracı DEĞİL."""
    g = cfg["gate"]
    return GateConfig(
        lookback_bars=lookback if lookback is not None else g["lookback_bars"],
        confirm_days=confirm if confirm is not None else g["confirm_days"],
        close_days=g["close_days"],
        signal_rate_haircut=g["signal_rate_haircut_bps"] / 1e4,
        warmup_gate_closed=g["warmup_gate_closed"],
    )


def _in_position(signal: pd.Series) -> pd.Series:
    """Motor değişmezi: bar i'de pozisyon durumu = dünkü sinyal (t+1 yürütme).
    `run_regime_core[_gated]` döngüsünde transition sonrası
    `in_position == signal_yesterday` olur; i=0'da pozisyon yoktur."""
    return signal.shift(1, fill_value=False).astype(bool)


def run_d5(cfg: dict, closes: dict[str, pd.Series], cash_rate: pd.Series,
           gate_cfg: Optional[GateConfig] = None, core_cfg: Optional[RegimeCoreConfig] = None):
    core_cfg = core_cfg or core_config_from(cfg)
    gate_cfg = gate_cfg or gate_config_from(cfg)
    return run_regime_core_gated(closes, core_cfg, gate_cfg=gate_cfg, cash_rate=cash_rate)


def evaluate_sealed_table(d5: dict, d1: dict) -> dict:
    """`D5_CRITERIA.md` §3'ün MEKANİK uygulaması. Eşikler D1'in kendi metrikleridir.
    Kural: 1+2+3a+3b TAMAMI → ADAY; biri kalırsa RED. **Dar fark YOK.**
    Bu bir HÜKÜM değildir — mekanik doldurmadır; karar kullanıcının/baş danışmanın."""
    rows = [
        {"id": "1", "name": "TRY Sharpe > D1 Sharpe", "op": ">",
         "value": d5["summary"]["sharpe"], "threshold": d1["summary"]["sharpe"]},
        {"id": "2", "name": "TRY CAGR > D1 CAGR", "op": ">",
         "value": d5["summary"]["cagr"], "threshold": d1["summary"]["cagr"]},
        {"id": "3a", "name": "OOS aylık-Sharpe > D1 OOS aylık-Sharpe", "op": ">",
         "value": d5["oos"]["oos_monthly_sharpe"], "threshold": d1["oos"]["oos_monthly_sharpe"]},
        {"id": "3b", "name": "|maxDD| <= D1 |maxDD|", "op": ">=",
         "value": d5["summary"]["max_drawdown"], "threshold": d1["summary"]["max_drawdown"]},
    ]
    for r in rows:
        r["passed"] = (r["value"] > r["threshold"]) if r["op"] == ">" else (r["value"] >= r["threshold"])
        r["delta"] = r["value"] - r["threshold"]
    n_pass = sum(r["passed"] for r in rows)
    return {
        "criteria": rows, "n_pass": n_pass, "n_total": len(rows),
        "mechanical_outcome": "ADAY" if n_pass == len(rows) else "RED",
        "note": "Mekanik sonuç — HÜKÜM DEĞİL. Kabul ADAY olsa bile canlıya alma "
                "AYRI gölge dönemi + AYRI kullanıcı kararı gerektirir (D5_CRITERIA §0.3).",
    }


# ---------------------------------------------------------------- zorunlu analizler (BİLGİ)


def analysis_a_gate_timeline(res, d1_regime_on: pd.Series) -> dict:
    """(a) Kapı zaman çizelgesi: yıl-yıl nakit-gün oranı D5 vs D1 + kapının
    GERÇEKTEN bağladığı günler (rejim ON ama kapı KAPALI)."""
    d5_pos = _in_position(res.effective_on)
    d1_pos = _in_position(d1_regime_on)
    binding = d1_regime_on & ~res.gate_open        # kapı D1'i engelliyor (sinyal günü bazında)

    rows = []
    for year, idx in res.composite.groupby(res.composite.index.year).groups.items():
        rows.append({
            "year": int(year), "n_days": len(idx),
            "d1_cash_day_pct": float((~d1_pos.loc[idx]).mean()),
            "d5_cash_day_pct": float((~d5_pos.loc[idx]).mean()),
            "gate_open_pct": float(res.gate_open.loc[idx].mean()),
            "gate_binding_pct": float(binding.loc[idx].mean()),
        })
    total_binding = int(binding.sum())
    return {
        "per_year": rows,
        "gate_binding_days_total": total_binding,
        "gate_binding_pct_total": float(binding.mean()),
        "first_gate_open": str(res.gate_open[res.gate_open].index[0].date())
        if res.gate_open.any() else None,
    }


def analysis_b_windows(cfg: dict, curves: dict[str, pd.Series], closes: dict[str, pd.Series],
                       cash_rate: pd.Series) -> dict:
    """(b) Pencere kıyasları (1y/3y/5y/10y/tam): D5 vs D1 vs **taze** (pencere-başı
    eşit-ağırlık) sepet vs faiz. Taze sepet `tools/period_comparison.py::
    build_window_start_basket` ile — REUSE (2005-ağırlıklı sürüklenmiş sepet YANILTICI,
    bkz. PERIOD_COMPARISON.md Metodoloji Notu)."""
    ie = float(cfg["initial_equity"])
    end = curves["D5"].index[-1]
    out = []
    windows = [(f"Son {y} Yıl", end - pd.DateOffset(years=y)) for y in cfg["comparison_windows_years"]]
    windows.append(("Tam dönem", curves["D5"].index[0]))

    for label, start in windows:
        start = max(start, curves["D5"].index[0])
        row = {"window": label, "start": str(start.date()), "end": str(end.date())}
        for name, curve in curves.items():
            row[name] = compute_summary(curve.loc[start:end])
        row["sepet_taze"] = compute_summary(build_window_start_basket(closes, start, end, ie))
        cash_curve = compute_cash_only_curve(curves["D5"].loc[start:end].index, cash_rate, ie)
        row["faiz_haircutli"] = compute_summary(cash_curve)
        raw_cash = compute_cash_only_curve(curves["D5"].loc[start:end].index, cash_rate, ie, haircut=0.0)
        row["faiz_ham"] = compute_summary(raw_cash)
        out.append(row)
    return {"windows": out}


def _yearly_returns(curve: pd.Series) -> dict[int, float]:
    ye = curve.resample("YE").last()
    first = curve.iloc[0]
    prev = pd.concat([pd.Series([first], index=[ye.index[0]]), ye.shift(1).iloc[1:]])
    return {int(d.year): float(ye.loc[d] / prev.loc[d] - 1) for d in ye.index}


def analysis_c_crisis(cfg: dict, curves: dict[str, pd.Series], closes: dict[str, pd.Series],
                      cash_rate: pd.Series) -> dict:
    """(c) Kriz/testere yılları — kapının katkısı (+) / bedeli (−)."""
    ie = float(cfg["initial_equity"])
    full_start, full_end = curves["D1"].index[0], curves["D1"].index[-1]
    yearly = {name: _yearly_returns(c) for name, c in curves.items()}
    # Sepet: tam dönem boyunca t0=2005'te kurulan, hiç dengelenmeyen seri (build_composite).
    # Yıllık getiriler pencere-bağımsız olduğu için burada sürüklenme çarpıtması YOKTUR
    # (her yıl kendi başlangıç/bitiş seviyesine göre okunur) — bkz. PERIOD_COMPARISON.md.
    yearly["sepet"] = _yearly_returns(build_window_start_basket(closes, full_start, full_end, ie))
    yearly["faiz_haircutli"] = _yearly_returns(compute_cash_only_curve(curves["D1"].index, cash_rate, ie))

    rows = []
    for y in cfg["crisis_years"]:
        row = {"year": y}
        for name, series in yearly.items():
            row[name] = series.get(y)
        if row.get("D5") is not None and row.get("D1") is not None:
            row["gate_contribution_pp"] = (row["D5"] - row["D1"]) * 100
        rows.append(row)
    return {"crisis_years": rows, "all_years": {n: s for n, s in yearly.items()}}


def _round_trips(switches) -> list[dict]:
    trips, open_sw = [], None
    for sw in switches:
        if sw.action == "ENTER":
            open_sw = sw
        elif sw.action == "EXIT" and open_sw is not None:
            trips.append({
                "enter": str(open_sw.date.date()), "exit": str(sw.date.date()),
                "hold_days": int((sw.date - open_sw.date).days),
                "ret": float(sw.equity_after / open_sw.equity_after - 1),
            })
            open_sw = None
    return trips


def analysis_d_turnover(cfg: dict, closes: dict[str, pd.Series], cash_rate: pd.Series,
                        d5_res, d1_res) -> dict:
    """(d) Turnover/whipsaw + maliyet sürüklemesi (sıfır-maliyet yeniden koşumuyla)."""
    zero_core = RegimeCoreConfig(
        symbols=cfg["symbols"], ma_period=cfg["regime"]["ma_period"],
        band_pct=cfg["regime"]["band_pct"], confirm_days=cfg["regime"]["confirm_days"],
        commission_bps=0.0, slippage_bps=0.0, initial_equity=cfg["initial_equity"],
    )
    d5_zero = run_regime_core_gated(closes, zero_core, gate_cfg=gate_config_from(cfg), cash_rate=cash_rate)
    d1_zero = run_regime_core(closes, zero_core, cash_rate=cash_rate)

    out = {}
    for name, res, zero in (("D5", d5_res, d5_zero), ("D1", d1_res, d1_zero)):
        trips = _round_trips(res.switches)
        short = [t for t in trips if t["hold_days"] <= 30]
        losers = [t for t in trips if t["ret"] < 0]
        cagr_cost = compute_summary(res.equity_curve)["cagr"]
        cagr_free = compute_summary(zero.equity_curve)["cagr"]
        out[name] = {
            "n_switches": len(res.switches), "n_round_trips": len(trips),
            "switches_per_year": len(res.switches) / ((res.equity_curve.index[-1] -
                                                       res.equity_curve.index[0]).days / 365.25),
            "n_losing_trips": len(losers),
            "n_short_trips_le_30d": len(short),
            "n_short_losing_trips": len([t for t in short if t["ret"] < 0]),
            "mean_trip_ret": float(np.mean([t["ret"] for t in trips])) if trips else 0.0,
            "median_hold_days": float(np.median([t["hold_days"] for t in trips])) if trips else 0.0,
            "cagr_with_costs": cagr_cost, "cagr_zero_costs": cagr_free,
            "cost_drag_pp_per_year": (cagr_free - cagr_cost) * 100,
        }
    return out


def _underwater_stats(curve: pd.Series) -> dict:
    dd = curve / curve.cummax() - 1
    uw = dd < -1e-12
    longest = cur = 0
    for v in uw:
        cur = cur + 1 if v else 0
        longest = max(longest, cur)
    return {"underwater_day_pct": float(uw.mean()), "longest_underwater_days": int(longest)}


def analysis_dd_mechanism(curves: dict[str, pd.Series], d5_res, d1_res) -> dict:
    """DD MEKANİZMASI (kritik bulgu, BİLGİ): kapı **toparlanmaya katılımı** bastırdığı
    için, D1'in ayrı ayrı toparlanan iki epizodu D5'te TEK ve DAHA DERİN bir epizoda
    KAYNAŞIR. Kapı maruziyeti yalnızca AZALTABİLDİĞİ halde realize maxDD'nin DERİNLEŞMESİ
    ancak bu yolla mümkündür. Emsal: D2-US/D4-US 'rebound gecikmesi' bulgusu."""
    out = {name: _underwater_stats(c) for name, c in curves.items()}
    # 2013 dip'i sonrası toparlanma bacağı — D1'in yeni zirve yaptığı, D5'in yapamadığı leg.
    leg = (pd.Timestamp("2013-11-11", tz="UTC"), pd.Timestamp("2015-05-19", tz="UTC"))
    sl = slice(*leg)
    d5_pos, d1_pos = _in_position(d5_res.effective_on), _in_position(d1_res.regime_on)
    comp = d5_res.composite.loc[sl]
    out["recovery_leg_2013_2015"] = {
        "window": [str(leg[0].date()), str(leg[1].date())],
        "composite_ret": float(comp.iloc[-1] / comp.iloc[0] - 1),
        "gate_open_pct": float(d5_res.gate_open.loc[sl].mean()),
        "D1_invested_pct": float(d1_pos.loc[sl].mean()),
        "D5_invested_pct": float(d5_pos.loc[sl].mean()),
        "D1_equity_ret": float(curves["D1"].loc[sl].iloc[-1] / curves["D1"].loc[sl].iloc[0] - 1),
        "D5_equity_ret": float(curves["D5"].loc[sl].iloc[-1] / curves["D5"].loc[sl].iloc[0] - 1),
    }
    out["exposure_totals"] = {
        "gate_open_pct": float(d5_res.gate_open.mean()),
        "D1_regime_on_pct": float(d1_res.regime_on.mean()),
        "D5_effective_on_pct": float(d5_res.effective_on.mean()),
    }
    return out


def analysis_e_neighborhood(cfg: dict, closes: dict[str, pd.Series], cash_rate: pd.Series) -> dict:
    """(e) Komşuluk — **GÖZLEMSEL, SEÇİM DEĞİL** (`D5_CRITERIA.md` §5e).
    Mühürlü nokta (252, 3) zirve ÇIKARSA bu overfitting şüphesidir; komşuluğun
    en iyisini 'yeni aile' diye koşmak KALICI YASAKTIR."""
    core_cfg = core_config_from(cfg)
    nb = cfg["neighborhood"]
    rows = []
    for lb in nb["lookback_bars"]:
        for cd in nb["confirm_days"]:
            res = run_d5(cfg, closes, cash_rate, gate_cfg=gate_config_from(cfg, lb, cd),
                         core_cfg=core_cfg)
            s = compute_summary(res.equity_curve)
            rows.append({"lookback_bars": lb, "confirm_days": cd, "sharpe": s["sharpe"],
                         "cagr": s["cagr"], "max_drawdown": s["max_drawdown"],
                         "n_switches": len(res.switches),
                         "is_sealed_point": lb == cfg["gate"]["lookback_bars"]
                                            and cd == cfg["gate"]["confirm_days"]})
    sealed = next(r for r in rows if r["is_sealed_point"])
    best = max(rows, key=lambda r: r["sharpe"])
    return {"grid": rows, "sealed_point": sealed, "best_by_sharpe": best,
            "sealed_is_peak": sealed is best,
            "sharpe_min": min(r["sharpe"] for r in rows),
            "sharpe_max": max(r["sharpe"] for r in rows)}


def analysis_warmup_artifact(cfg: dict, curves: dict[str, pd.Series], first_gate_eval: pd.Timestamp) -> dict:
    """`D5_CRITERIA.md` §4 — ISINMA ARTEFAKTI yan-ölçümü. **KRİTER DEĞİL.**
    İki eğri de kapının ilk değerlendirilebildiği barda 100 000'e yeniden normalize
    edilip kıyaslanır: 'fark kapının ekonomik etkisi mi, 2.5 aylık ısınma kayması mı?'"""
    ie = float(cfg["initial_equity"])
    out = {"renormalized_at": str(first_gate_eval.date()), "is_criterion": False}
    for name, curve in curves.items():
        sl = curve.loc[first_gate_eval:]
        out[name] = compute_summary(sl / sl.iloc[0] * ie)
    return out


# ------------------------------------------------------------------------------- CLI


def run_spike(cfg: dict) -> dict:
    closes, ghost_log, cash_rate = load_universe(cfg)
    core_cfg = core_config_from(cfg)
    gate_cfg = gate_config_from(cfg)

    print("=== D1 baseline (benchmark) ===")
    d1_baseline = reproduce_d1_baseline(cfg, closes, cash_rate)
    verification = verify_against_s1b(d1_baseline)
    print(f"S1b bit-bit doğrulama: {verification['n_checks']}/{verification['n_checks']} BİREBİR")

    print("\n=== D5 ana koşum (mühürlü paket) ===")
    d5_res = run_regime_core_gated(closes, core_cfg, gate_cfg=gate_cfg, cash_rate=cash_rate)
    d1_res = run_regime_core(closes, core_cfg, cash_rate=cash_rate)
    d5 = {
        "summary": compute_summary(d5_res.equity_curve),
        "n_switches": len(d5_res.switches),
        "oos": {k: v for k, v in oos_from_reruns(closes, cfg, core_cfg, cash_rate,
                                                 run_regime_core_gated,
                                                 gate_cfg=gate_cfg).items()
                if not k.startswith("_")},
        "monte_carlo_monthly": mc_from_curve(d5_res.equity_curve, cfg),
    }
    print(json.dumps(d5["summary"], indent=2))
    print(f"switches: {d5['n_switches']} (D1: {d1_baseline['n_switches']})")

    print("\n=== MÜHÜRLÜ TABLO (mekanik) ===")
    table = evaluate_sealed_table(d5, d1_baseline)
    for r in table["criteria"]:
        print(f"  ({r['id']}) {r['name']}: {r['value']:.6f} vs {r['threshold']:.6f} "
              f"→ {'PASS' if r['passed'] else 'FAIL'} (Δ={r['delta']:+.6f})")
    print(f"  → {table['n_pass']}/{table['n_total']} — mekanik sonuç: {table['mechanical_outcome']}")

    curves = {"D5": d5_res.equity_curve, "D1": d1_res.equity_curve}
    first_gate_eval = d5_res.composite.index[gate_cfg.lookback_bars]

    print("\n=== Zorunlu analizler (BİLGİ) ===")
    analyses = {
        "a_gate_timeline": analysis_a_gate_timeline(d5_res, d1_res.regime_on),
        "b_windows": analysis_b_windows(cfg, curves, closes, cash_rate),
        "c_crisis": analysis_c_crisis(cfg, curves, closes, cash_rate),
        "d_turnover": analysis_d_turnover(cfg, closes, cash_rate, d5_res, d1_res),
        "dd_mechanism": analysis_dd_mechanism(curves, d5_res, d1_res),
        "e_neighborhood": analysis_e_neighborhood(cfg, closes, cash_rate),
        "f_monte_carlo": {"D5": d5["monte_carlo_monthly"], "D1": d1_baseline["monte_carlo_monthly"]},
        "warmup_artifact_sec4": analysis_warmup_artifact(cfg, curves, first_gate_eval),
    }
    print(f"  (a) kapı bağlayan gün: {analyses['a_gate_timeline']['gate_binding_days_total']} "
          f"({analyses['a_gate_timeline']['gate_binding_pct_total']:.1%})")
    print(f"  (d) D5 anahtarlama {analyses['d_turnover']['D5']['n_switches']} vs "
          f"D1 {analyses['d_turnover']['D1']['n_switches']}")
    print(f"  (e) komşuluk Sharpe aralığı: {analyses['e_neighborhood']['sharpe_min']:.3f}"
          f"–{analyses['e_neighborhood']['sharpe_max']:.3f}; mühürlü nokta zirve mi: "
          f"{analyses['e_neighborhood']['sealed_is_peak']}")

    out = {
        "run": "D5-BIST CHALLENGER spike (offline araştırma; ÜRETİM DEĞİL; HÜKÜM YOK)",
        "seal": "D5_CRITERIA.md (koşumdan ÖNCE mühürlendi)",
        "config": {"inherited_from": cfg["_inherited_from"], "regime": cfg["regime"],
                   "gate": cfg["gate"], "costs": cfg["costs"],
                   "snapshot": cfg["backtest"]["snapshot"], "cash_yield": cfg["cash_yield"]},
        "ghost_bars_removed": [{"symbol": g["symbol"], "date": str(g["date"])} for g in ghost_log],
        "d1_baseline": d1_baseline,
        "s1b_bit_exact_verification": {"all_bit_exact": verification["all_bit_exact"],
                                       "n_checks": verification["n_checks"]},
        "d5": d5,
        "sealed_table": table,
        "analyses": analyses,
    }
    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "d5_spike.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    d5_res.equity_curve.to_csv(out_dir / "equity_d5.csv")
    d1_res.equity_curve.to_csv(out_dir / "equity_d1.csv")
    pd.DataFrame([{"date": s.date, "action": s.action, "equity_before": s.equity_before,
                   "equity_after": s.equity_after} for s in d5_res.switches]).to_csv(
        out_dir / "switches_d5.csv", index=False)
    pd.DataFrame(analyses["e_neighborhood"]["grid"]).to_csv(out_dir / "neighborhood.csv", index=False)
    print(f"\nYazıldı: {out_dir / 'd5_spike.json'}")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="D5-BIST challenger sürücüsü")
    p.add_argument("--baseline-only", action="store_true",
                   help="Yalnızca D1 baseline'ını yeniden üret + S1b'ye karşı bit-bit doğrula "
                        "(mühürleme girdisi; strateji koşumu YOK).")
    args = p.parse_args()

    cfg = load_d5_config()
    if args.baseline_only:
        run_baseline(cfg)
    else:
        run_spike(cfg)


if __name__ == "__main__":
    main()

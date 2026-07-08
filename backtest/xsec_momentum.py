# backtest/xsec_momentum.py
"""D2US-S1 — KESİTSEL (cross-sectional) MOMENTUM ailesi (D2-US) BAĞIMSIZ simülatörü.

**BAĞIMSIZ SİMÜLATÖR**: `backtest/engine.py`, `backtest/regime_core*.py` (S1/S1b/E4
simülatörleri), `strategy/`, `risk/`, `config/config.yaml`'a DOKUNMAZ ve BAĞIMLI
DEĞİLDİR — v7.1-golden ve E4/E4b bayt-bayt korunur. Yalnız `costs/` (CostModel) ve
`data/cleaning.py` (yükleme) yeniden kullanılır (bunlar değişmez).

Bu bir DEĞERLENDİRME spike'ıdır (D2-US tasarımının tek-tur testi). Tasarım
`config/momentum_us2.yaml` + `D2US_CRITERIA.md` ile KOŞUMDAN ÖNCE mühürlendi;
bu modül o mührü MEKANİK uygular — parametre seçimi/tarama YOK. Ablasyon/komşuluk
toggle'ları (use_fip/use_abs_gate/use_vol_target, formation_months, final_n,
vol_window_days) YALNIZ item 4c/4d bilgilendirici analizleri içindir; mühürlü
paket bunların sealed-değerleriyle çalışır.

Tasarım (mühürlü — D2US_CRITERIA.md §1):
- 12-1 momentum (formation 12 ay, son ay atlanır), aylık rebalans.
- Ay-sonu (son işlem günü) sinyal → SONRAKİ işlem günü KAPANIŞ yürütme (t+1).
- Ön-seçim: formation getirisine göre top-20 → FIP information-discreteness ile
  en sürekli 10 (ID = sign(mom) × (%neg − %pos), formation penceresi; düşük ID).
- Eşit ağırlık (1/10). Pozisyon-bazlı mutlak-momentum NAKİT kapısı (12-1 ≤ T-bill
  formation-penceresi getirisi → slot nakit; ham DGS3MO, ACT/365).
- Vol-hedefleme: maruziyet = min(1, target_vol / realize_6ay_book_vol), kaldıraçsız.
- US CostModel devire uygulanır; nakit fraksiyonu DGS3MO−50bp kazanır.
- LONG-only.

Look-ahead YASAĞI: tüm sinyal bileşenleri rebalans günü m[j] KAPANIŞINA (≤ m[j])
kadarki veriyle hesaplanır; işlem en erken m[j]+1 KAPANIŞINDA. (Test: test_xsec_momentum.py)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from core.models import Side
from costs.base import CostModel

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class XSecMomentumConfig:
    symbols: list[str]
    formation_months: int = 12      # oluşum penceresi
    skip_months: int = 1            # son ay atla → 12-1
    preselect_top: int = 20         # momentum ön-seçim
    final_n: int = 10               # nihai seçim (FIP)
    use_fip: bool = True            # ablasyon toggle (FIP information-discreteness)
    use_abs_gate: bool = True       # ablasyon toggle (mutlak-momentum nakit kapısı)
    use_vol_target: bool = True     # ablasyon toggle (vol-hedefleme)
    target_vol: float = 0.182326    # SEPET tam-dönem realize yıllık vol (mühürlü sabit)
    vol_window_days: int = 126      # 6 ay (trailing book getirileri)
    max_leverage: float = 1.0       # maruziyet üst sınırı (kaldıraç YOK)
    initial_equity: float = 100_000.0
    abs_gate_haircut: float = 0.0   # kapı için HAM oran (nakit-bacağı haircut'tan ayrı)


@dataclass
class Rebalance:
    signal_date: pd.Timestamp
    exec_date: pd.Timestamp
    selected: list[str]             # FIP sonrası nihai N (kapı ÖNCESİ)
    invested: list[str]             # gerçekten yatırılan slotlar (kapı SONRASI)
    n_cash_slots: int               # kapı-nakdi slot sayısı (final_n − len(invested))
    exposure: float                 # vol-hedefleme maruziyeti
    turnover: float                 # devir = Σ|Δnotional| / equity
    cost: float                     # bu rebalansta toplam işlem maliyeti (slippage+fee)


@dataclass
class XSecMomentumResult:
    equity_curve: pd.Series
    rebalances: list[Rebalance] = field(default_factory=list)
    all_dates: pd.DatetimeIndex = None


def _build_price_matrix(daily_closes: dict[str, pd.Series]) -> pd.DataFrame:
    """Sembol -> kapanış Series sözlüğünü hizalı bir fiyat matrisine çevirir
    (index = tüm sembollerin tarihlerinin union'ı, forward-fill — build_composite
    ile aynı 'eksik günü son bilinen fiyatla taşı' ilkesi)."""
    union: set = set()
    for s in daily_closes.values():
        union |= set(s.index)
    idx = pd.DatetimeIndex(sorted(union))
    mat = pd.DataFrame({sym: closes.reindex(idx) for sym, closes in daily_closes.items()})
    return mat.ffill()


def _month_end_dates(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Her takvim ayının SON işlem günü (index'te var olan gerçek tarih)."""
    ser = pd.Series(idx, index=idx)
    return ser.resample("ME").last().dropna().tolist()


def _build_daily_rate(cash_rate: Optional[pd.Series], idx: pd.DatetimeIndex) -> Optional[pd.Series]:
    if cash_rate is None:
        return None
    return cash_rate.reindex(idx, method="ffill").bfill()


def _accrue_rate(daily_rate: Optional[pd.Series], dates: pd.DatetimeIndex,
                 start: pd.Timestamp, end: pd.Timestamp, haircut: float) -> float:
    """(start, end] penceresinde ACT/365 basit tahakkukun kümülatif getirisi.
    daily_rate None ise 0.0 (T-bill getirisi 0 → kapı hiçbir şeyi elemez)."""
    if daily_rate is None:
        return 0.0
    window = dates[(dates > start) & (dates <= end)]
    acc = 1.0
    prev = start
    for d in window:
        days = (d - prev).days
        rate = daily_rate.loc[d]
        if pd.notna(rate) and days > 0:
            acc *= (1 + max(float(rate) - haircut, 0.0) / 365) ** days
        prev = d
    return acc - 1.0


def run_xsec_momentum(
    daily_closes: dict[str, pd.Series],
    cfg: XSecMomentumConfig,
    cost_model: CostModel,
    date_range: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None,
    cash_rate: Optional[pd.Series] = None,
    cashleg_haircut: float = 0.005,
) -> XSecMomentumResult:
    """Kesitsel momentum ana simülasyon döngüsü.

    `cash_rate`: yıllık ondalık oran Series (DGS3MO). Nakit fraksiyonuna
    `cashleg_haircut` (50bp) kırpmalı tahakkuk eder; mutlak-momentum kapısı ise
    ham oranı (`cfg.abs_gate_haircut`, 0) kullanır.
    `date_range`: verilirse yalnız (start, end] equity_curve'e yazılır; sinyaller
    ve vol-geçmişi HER ZAMAN tam tarihçe üzerinden hesaplanır (warm-up + walk-forward
    OOS için — E4 emsali).
    """
    mat = _build_price_matrix(daily_closes)
    all_dates = mat.index
    n = len(all_dates)
    pos_of = {d: i for i, d in enumerate(all_dates)}
    price = {s: mat[s].to_numpy(dtype=float) for s in cfg.symbols}

    month_ends = _month_end_dates(all_dates)
    me_index = {d: j for j, d in enumerate(month_ends)}
    me_pos = {pos_of[d] for d in month_ends}  # daily-loop pozisyonları

    daily_rate = _build_daily_rate(cash_rate, all_dates)

    cash = cfg.initial_equity
    shares: dict[str, int] = {}
    equity_hist = np.empty(n, dtype=float)     # TAM geçmiş (vol için) — date_range'den bağımsız
    equity_points: list[tuple[pd.Timestamp, float]] = []
    rebalances: list[Rebalance] = []
    pending: Optional[dict] = None             # bir önceki ay-sonunda hesaplanan hedef

    def mark(i: int) -> float:
        total = cash
        for s, q in shares.items():
            total += q * price[s][i]
        return total

    for i, date in enumerate(all_dates):
        # 1) Nakit tahakkuku (nakit fraksiyonuna, 50bp kırpmalı) — bugünkü işlemden ÖNCE.
        if i > 0 and cash > 0 and daily_rate is not None:
            days = (date - all_dates[i - 1]).days
            rate = daily_rate.loc[date]
            if pd.notna(rate) and days > 0:
                cash *= (1 + max(float(rate) - cashleg_haircut, 0.0) / 365) ** days

        # 2) Bekleyen hedefi (önceki ay-sonu sinyali) BUGÜN kapanışta yürüt (t+1).
        if pending is not None:
            equity_now = mark(i)
            invested = pending["invested"]
            exposure = pending["exposure"]
            per_slot = equity_now * exposure / cfg.final_n
            target: dict[str, int] = {}
            for s in invested:
                px = price[s][i]
                buy_fill = cost_model.slippage_price(px, Side.BUY)
                unit = buy_fill + cost_model.entry_costs(buy_fill, 1.0)
                q = int(np.floor(per_slot / unit)) if unit > 0 else 0
                if q >= 1:
                    target[s] = q
            traded_notional = 0.0
            cost_paid = 0.0
            symbols_union = set(shares) | set(target)
            # Önce SATIŞLAR (nakit serbest bırak), sonra ALIŞLAR.
            for s in symbols_union:
                delta = target.get(s, 0) - shares.get(s, 0)
                if delta < 0:
                    q = -delta
                    px = price[s][i]
                    sell_fill = cost_model.slippage_price(px, Side.SELL)
                    fee = cost_model.exit_costs(sell_fill, q)
                    cash += sell_fill * q - fee
                    traded_notional += px * q
                    cost_paid += q * (px - sell_fill) + fee
            for s in symbols_union:
                delta = target.get(s, 0) - shares.get(s, 0)
                if delta > 0:
                    q = delta
                    px = price[s][i]
                    buy_fill = cost_model.slippage_price(px, Side.BUY)
                    fee = cost_model.entry_costs(buy_fill, q)
                    cash -= buy_fill * q + fee
                    traded_notional += px * q
                    cost_paid += q * (buy_fill - px) + fee
            shares = {s: q for s, q in target.items() if q >= 1}
            rebalances.append(Rebalance(
                signal_date=pending["signal_date"], exec_date=date,
                selected=pending["selected"], invested=invested,
                n_cash_slots=cfg.final_n - len(invested), exposure=exposure,
                turnover=traded_notional / equity_now if equity_now > 0 else 0.0,
                cost=cost_paid))
            pending = None

        # 3) Bugünün equity'sini işaretle (tam geçmiş + date_range'li çıktı).
        eq = mark(i)
        equity_hist[i] = eq
        if date_range is None or (date_range[0] <= date < date_range[1]):
            equity_points.append((date, eq))

        # 4) Ay-sonu ise SONRAKİ gün için sinyal hesapla (yürütme t+1'de).
        if i in me_pos and i + 1 < n:
            j = me_index[date]
            if j >= cfg.formation_months:
                pending = _compute_signal(j, i, date, month_ends, cfg, mat, price,
                                          pos_of, daily_rate, all_dates, equity_hist)

    equity_curve = pd.Series(dict(equity_points)).sort_index() if equity_points else pd.Series(dtype=float)
    return XSecMomentumResult(equity_curve=equity_curve, rebalances=rebalances, all_dates=all_dates)


def _compute_signal(j: int, i: int, date: pd.Timestamp, month_ends: list,
                    cfg: XSecMomentumConfig, mat: pd.DataFrame, price: dict,
                    pos_of: dict, daily_rate, all_dates, equity_hist) -> dict:
    """Rebalans ayı m[j] için mühürlü sinyal (≤ m[j] veriyle — look-ahead YOK)."""
    num_date = month_ends[j - cfg.skip_months]        # formation üst sınırı (m[j-1])
    den_date = month_ends[j - cfg.formation_months]    # formation alt sınırı (m[j-12])
    ni, di = pos_of[num_date], pos_of[den_date]

    # Formation (12-1) getirisi.
    form_ret: dict[str, float] = {}
    for s in cfg.symbols:
        p0, p1 = price[s][di], price[s][ni]
        form_ret[s] = (p1 / p0 - 1.0) if p0 > 0 else -np.inf

    # Ön-seçim: top-20 momentum (deterministik: getiri, eşitlikte sembol adı).
    ranked = sorted(cfg.symbols, key=lambda s: (form_ret[s], s), reverse=True)
    preselect = ranked[: cfg.preselect_top]

    # Nihai seçim: FIP information-discreteness (düşük ID) VEYA yalın top-N.
    if cfg.use_fip:
        ids: dict[str, float] = {}
        for s in preselect:
            path = mat[s].iloc[di: ni + 1]              # formation penceresi fiyat patikası
            rets = path.pct_change().dropna().to_numpy()
            if len(rets) == 0:
                ids[s] = 0.0
                continue
            pos = float((rets > 0).mean())
            neg = float((rets < 0).mean())
            sign = 1.0 if form_ret[s] > 0 else (-1.0 if form_ret[s] < 0 else 0.0)
            ids[s] = sign * (neg - pos)
        selected = sorted(preselect, key=lambda s: (ids[s], s))[: cfg.final_n]
    else:
        selected = preselect[: cfg.final_n]

    # Mutlak-momentum kapısı: hisse 12-1 ≤ T-bill formation-penceresi getirisi → nakit.
    if cfg.use_abs_gate:
        tbill_ret = _accrue_rate(daily_rate, all_dates, den_date, num_date, cfg.abs_gate_haircut)
        invested = [s for s in selected if form_ret[s] > tbill_ret]
    else:
        invested = list(selected)

    # Vol-hedefleme maruziyeti: min(1, target/realize_6ay_book_vol). Nedensel (≤ m[j]).
    if cfg.use_vol_target:
        lo = max(0, i - cfg.vol_window_days)
        seg = equity_hist[lo: i + 1]
        rets = np.diff(seg) / seg[:-1] if len(seg) >= 2 else np.array([])
        rets = rets[np.isfinite(rets)]
        rv = float(np.std(rets, ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if len(rets) >= 2 else 0.0
        exposure = min(cfg.max_leverage, cfg.target_vol / rv) if rv > 0 else cfg.max_leverage
    else:
        exposure = cfg.max_leverage

    return {"signal_date": date, "selected": selected, "invested": invested, "exposure": exposure}

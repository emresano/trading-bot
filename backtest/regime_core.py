# backtest/regime_core.py
"""S1 spike backtest — Rejim-Filtreli Çekirdek (D1 tasarımı).

**BAĞIMSIZ SİMÜLATÖR**: `backtest/engine.py`, `strategy/`, `risk/`,
`config/config.yaml`'a DOKUNMAZ ve BAĞIMLI DEĞİLDİR — v7.1-golden regresyon
çapası bu sayede otomatik korunur (bkz. `git diff` kanıtı, STATUS.md).

Bu bir DEĞERLENDİRME spike'ıdır (STATUS.md KALICI KAYIT 3'ün D1 tasarımının
tek-tur testi). Kabul edilirse üretim implementasyonu ayrı bir onaylı turda,
"backtest=canlı aynı fonksiyon" ilkesiyle (CLAUDE.md Bölüm 3.1) yeniden
yapılır — bu modül o ilkeye tabi DEĞİLDİR, yalnızca bir fikrin hızlı ve
dürüst testi.

Tasarım (D1, sabit — bu turda değiştirilmez):
- Çekirdek: 12 sembol, eşit ağırlık. Kompozit seri: ortak ilk geçerli tarihe
  (t0) normalize kapanışların eşit-ağırlıklı ortalaması.
- Rejim sinyali (kompozit üzerinde): GİRİŞ = close > MA(N)×(1+b) ardışık M
  gün; ÇIKIŞ = close < MA(N)×(1−b) tek gün (asimetrik histerezis — giriş
  teyitli, çıkış hızlı, sermaye-koruma önceliği).
- Pozisyon: rejim AÇIK → equity eşit bölünür (komisyon payı düşülerek,
  negatif cash yasak); rejim KAPALI → %100 nakit. Tutma sırasında rebalance
  YOK.
- Yürütme: sinyal t günü KAPANIŞINDA hesaplanır, işlem t+1 KAPANIŞ
  fiyatından (main engine'in t+1 AÇILIŞ kuralından kasıtlı farklı — bu
  basitleştirilmiş spike modelinin kendi, ayrı kuralı).
- Breaker YOK (bilinçli, bu spike'ta).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RegimeCoreConfig:
    symbols: list[str]
    ma_period: int = 200          # N
    band_pct: float = 0.01        # b
    confirm_days: int = 3         # M (giriş teyidi; çıkış her zaman 1 gün)
    commission_bps: float = 10.0
    slippage_bps: float = 5.0
    initial_equity: float = 100_000.0


@dataclass
class Switch:
    date: pd.Timestamp
    action: str          # "ENTER" | "EXIT"
    equity_before: float
    equity_after: float


@dataclass
class RegimeCoreResult:
    equity_curve: pd.Series
    composite: pd.Series
    regime_on: pd.Series           # bool Series — o gün rejim ON mu (mark-to-market günü)
    switches: list[Switch] = field(default_factory=list)
    composite_fill_log: list[dict] = field(default_factory=list)


def build_composite(daily_closes: dict[str, pd.Series]) -> tuple[pd.Series, list[dict]]:
    """Her sembolün ortak ilk geçerli tarihine (t0 = tüm sembollerin en geç
    başlayanının ilk günü) normalize edilmiş (t0=1.0) kapanışlarının
    eşit-ağırlıklı ortalaması. Bir sembolde tekil eksik gün varsa (union'da
    olup o sembolde olmayan tarih), o sembolün son bilinen normalize
    değeriyle taşınır (forward-fill) ve loglanır — 0 sayılmaz, silinmez."""
    t0 = max(s.index[0] for s in daily_closes.values())
    union_dates: set = set()
    for s in daily_closes.values():
        union_dates |= set(s.index)
    all_dates = sorted(d for d in union_dates if d >= t0)

    normalized: dict[str, pd.Series] = {}
    for sym, closes in daily_closes.items():
        s = closes.loc[closes.index >= t0]
        base = float(s.iloc[0])
        normalized[sym] = s / base

    fill_log: list[dict] = []
    aligned_cols = {}
    for sym, series in normalized.items():
        reindexed = series.reindex(all_dates)
        missing_mask = reindexed.isna()
        if missing_mask.any():
            for d in reindexed.index[missing_mask]:
                fill_log.append({"symbol": sym, "date": d, "action": "forward_fill"})
        reindexed = reindexed.ffill()
        aligned_cols[sym] = reindexed

    matrix = pd.DataFrame(aligned_cols)
    # İlk satırda hiçbir sembol için forward-fill imkanı yoksa (t0'da NaN
    # kalan) o satırlar (yalnızca t0 öncesi geriye kalanlar olabilir) atılır.
    matrix = matrix.dropna(how="any")
    composite = matrix.mean(axis=1)
    composite.index.name = "ts"
    return composite, fill_log


def compute_regime_signal(composite: pd.Series, ma_period: int, band_pct: float,
                          confirm_days: int) -> pd.Series:
    """Histerezis rejim sinyali. Döner: bool Series, index=composite.index,
    True = o günün KAPANIŞINDA rejim ON kararı verildi (yürütme ayrı bir
    fonksiyonun işi — bkz. run_regime_core, t+1 kaydırması orada yapılır).
    İlk `ma_period` gün NaN/False (ısınma dönemi, sinyal üretilmez)."""
    ma = composite.rolling(ma_period).mean()
    upper = ma * (1 + band_pct)
    lower = ma * (1 - band_pct)

    above_upper = composite > upper
    below_lower = composite < lower

    # Giriş teyidi: son `confirm_days` gün BOYUNCA above_upper true olmalı.
    confirmed_entry = above_upper.rolling(confirm_days).sum() >= confirm_days

    regime_on = pd.Series(False, index=composite.index)
    state = False
    for i in range(len(composite)):
        if pd.isna(ma.iloc[i]):
            regime_on.iloc[i] = False
            continue
        if not state and confirmed_entry.iloc[i]:
            state = True
        elif state and below_lower.iloc[i]:
            state = False
        regime_on.iloc[i] = state
    return regime_on


CASH_YIELD_HAIRCUT = 0.02  # 200bp — muhafazakâr kırpma (bkz. run_regime_core docstring)


def _build_daily_cash_rate(cash_rate: Optional[pd.Series], all_dates: pd.DatetimeIndex) -> Optional[pd.Series]:
    """`cash_rate` (aylık veya günlük, HAM — ondalık yıllık oran, örn. 0.1748)
    verilmişse `all_dates`'e forward-fill edilmiş bir Series döner. `cash_rate`
    None ise None döner (çağıran bunu "tahakkuk YOK" olarak yorumlar — S1
    davranışıyla BİREBİR aynı kalır, bkz. regresyon testi)."""
    if cash_rate is None:
        return None
    reindexed = cash_rate.reindex(all_dates, method="ffill")
    return reindexed.bfill()


def compute_cash_only_curve(dates: pd.DatetimeIndex, cash_rate: pd.Series, initial_equity: float,
                            haircut: float = CASH_YIELD_HAIRCUT) -> pd.Series:
    """'Sadece nakit, faizli' BİLGİLENDİRİCİ benchmark eğrisi (S1b madde 3b):
    tüm dönem boyunca hiç pozisyon açılmadan yalnızca nakitte kalınsaydı,
    nakdin `run_regime_core` ile AYNI ACT/365 tahakkuk formülüyle nasıl
    büyüyeceğini hesaplar. Strateji hesaplamasından TAMAMEN bağımsız bir
    yardımcıdır — yalnızca karşılaştırma amaçlı."""
    daily_rate = _build_daily_cash_rate(cash_rate, dates)
    equity = initial_equity
    points: list[tuple[pd.Timestamp, float]] = [(dates[0], equity)]
    for i in range(1, len(dates)):
        days_elapsed = (dates[i] - dates[i - 1]).days
        annual_rate = daily_rate.loc[dates[i]] if daily_rate is not None else None
        if annual_rate is not None and pd.notna(annual_rate) and days_elapsed > 0:
            r_net = max(float(annual_rate) - haircut, 0.0)
            equity *= (1 + r_net / 365) ** days_elapsed
        points.append((dates[i], equity))
    return pd.Series(dict(points)).sort_index()


def run_regime_core(
    daily_closes: dict[str, pd.Series],
    cfg: RegimeCoreConfig,
    date_range: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None,
    cash_rate: Optional[pd.Series] = None,
) -> RegimeCoreResult:
    """Ana simülasyon döngüsü. `daily_closes`: sembol -> kapanış fiyatı
    Series (data/cleaning.py'den geçmiş, tz-aware DatetimeIndex).
    `date_range`: verilirse yalnızca bu (start, end] aralığındaki günler
    equity_curve'e yazılır (ama kompozit/MA HER ZAMAN tam tarihçe üzerinden
    hesaplanır — ısınma ve look-ahead-siz warm-up walk-forward'ın OOS
    dilimlerinde de geçerli olsun diye).

    `cash_rate` (S1b — nakit-getiri düzeltmesi): verilirse (yıllık ondalık
    oran Series'i, örn. 0.1748 = %17.48), rejim KAPALI (tamamen nakitte)
    olunan günlerde nakit `r_net = max(rate - 200bp, 0)` oranıyla, basit
    ACT/365 ile, barlar arası geçen TAKVİM günü kadar tahakkuk eder:
    `cash *= (1 + r_net/365) ** gün_farkı`. 200bp'lik kırpma muhafazakâr bir
    seçimdir (gerçek mevduat/repo getirisi politika faizinin altında kalır —
    spread, vergi, likidite farkı vb. için kaba bir tampon).

    Tahakkuk, o günün transition'ı uygulanmadan ÖNCEKİ `in_position`
    durumuna göre karar verilir — bu, ENTER gününü DAHİL eder (kapanışa
    kadar nakitti) ama EXIT gününün KENDİSİNİ HARİÇ tutar (kapanışa kadar
    hisse pozisyonundaydı, o gün nakit hiç "boşta" durmadı) — muhafazakâr
    bir seçim, gerçek işlem mekaniğiyle de tutarlı.

    `cash_rate=None` (varsayılan) → HİÇBİR tahakkuk uygulanmaz, S1'in
    davranışıyla BİREBİR aynı kalır (bkz. regresyon testi:
    `test_cash_rate_none_is_byte_identical_to_s1_baseline` ve
    `test_cash_rate_all_zero_series_is_also_byte_identical`)."""
    composite, fill_log = build_composite(daily_closes)
    regime_on = compute_regime_signal(composite, cfg.ma_period, cfg.band_pct, cfg.confirm_days)

    all_dates = composite.index
    daily_cash_rate = _build_daily_cash_rate(cash_rate, all_dates)
    cash = cfg.initial_equity
    quantities: dict[str, int] = {}
    in_position = False
    switches: list[Switch] = []
    equity_points: list[tuple[pd.Timestamp, float]] = []

    commission_frac = cfg.commission_bps / 1e4
    slippage_frac = cfg.slippage_bps / 1e4

    def _equity_on(date: pd.Timestamp) -> float:
        if not in_position:
            return cash
        total = cash
        for sym, qty in quantities.items():
            px_series = daily_closes[sym]
            if date in px_series.index:
                total += qty * float(px_series.loc[date])
            else:
                # Kompozit forward-fill ile aynı ilke: fiyat eksikse son
                # bilinen fiyatla taşı (0 sayma).
                prior = px_series.loc[:date]
                total += qty * float(prior.iloc[-1]) if len(prior) else 0.0
        return total

    for i, date in enumerate(all_dates):
        signal_today = bool(regime_on.iloc[i])
        signal_yesterday = bool(regime_on.iloc[i - 1]) if i > 0 else False

        # Nakit getirisi tahakkuku (S1b): BUGÜNÜN transition'ı uygulanmadan
        # ÖNCEKİ `in_position` durumuna göre (bkz. docstring) — ENTER gününü
        # dahil eder, EXIT gününü hariç tutar. `daily_cash_rate` None ise
        # (varsayılan) bu blok hiç çalışmaz — S1 davranışı korunur.
        if i > 0 and not in_position and daily_cash_rate is not None:
            days_elapsed = (date - all_dates[i - 1]).days
            annual_rate = daily_cash_rate.loc[date]
            if pd.notna(annual_rate) and days_elapsed > 0:
                r_net = max(float(annual_rate) - CASH_YIELD_HAIRCUT, 0.0)
                cash *= (1 + r_net / 365) ** days_elapsed

        # t+1 yürütme: BUGÜN dünün sinyal DEĞİŞİMİNİ (yesterday's close'da
        # karar verilen) uygula. i=0 için önceki gün yok, işlem yapılmaz.
        if i > 0 and signal_yesterday != in_position:
            equity_before = _equity_on(date)
            if signal_yesterday and not in_position:
                # ENTER: equity'yi 12 sembole eşit böl, komisyon+slippage düş, negatif cash yasak.
                per_symbol_budget = equity_before / len(cfg.symbols)
                new_quantities = {}
                spent = 0.0
                for sym in cfg.symbols:
                    px_series = daily_closes[sym]
                    if date not in px_series.index:
                        continue
                    fill_price = float(px_series.loc[date]) * (1 + slippage_frac)
                    qty = int(np.floor(per_symbol_budget / (fill_price * (1 + commission_frac))))
                    if qty < 1:
                        continue
                    cost = fill_price * qty * (1 + commission_frac)
                    new_quantities[sym] = qty
                    spent += cost
                cash = equity_before - spent
                quantities = new_quantities
                in_position = True
                switches.append(Switch(date=date, action="ENTER",
                                       equity_before=equity_before, equity_after=_equity_on(date)))
            elif not signal_yesterday and in_position:
                # EXIT: tüm pozisyonları sat, komisyon+slippage düş, %100 nakit.
                proceeds = 0.0
                for sym, qty in quantities.items():
                    px_series = daily_closes[sym]
                    if date in px_series.index:
                        fill_price = float(px_series.loc[date]) * (1 - slippage_frac)
                    else:
                        prior = px_series.loc[:date]
                        fill_price = float(prior.iloc[-1]) * (1 - slippage_frac) if len(prior) else 0.0
                    proceeds += fill_price * qty * (1 - commission_frac)
                cash = cash + proceeds  # cash: ENTER'dan kalan bakiye (genelde küçük bir kırıntı)
                quantities = {}
                in_position = False
                switches.append(Switch(date=date, action="EXIT",
                                       equity_before=equity_before, equity_after=cash))

        equity_today = _equity_on(date)
        if date_range is None or (date_range[0] <= date < date_range[1]):
            equity_points.append((date, equity_today))

    equity_curve = pd.Series(dict(equity_points)).sort_index() if equity_points else pd.Series(dtype=float)
    return RegimeCoreResult(
        equity_curve=equity_curve, composite=composite, regime_on=regime_on,
        switches=switches, composite_fill_log=fill_log,
    )

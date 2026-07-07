# data/quality.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


@dataclass
class QualityResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cleaned_df: Optional[pd.DataFrame] = None


def check_quality(
    df: pd.DataFrame,
    *,
    max_staleness: Optional[timedelta] = None,
    now: Optional[datetime] = None,
    jump_threshold_pct: float = 0.20,
    ohlc_rtol: float = 0.005,
    ohlc_atol: float = 1e-6,
    calendar_id: Optional[str] = None,
) -> QualityResult:
    """Bölüm 7.2'deki 5 kontrolü sırayla uygular. Geçemeyen sembol o turda işlem görmez.

    `calendar_id` (EXPANSION.md Bölüm 5, ikinci doğrulama katmanı): verilirse
    (örn. "XIST"/"XNYS"), bar zaman damgalarının etiketlediği tarih o piyasada
    işlem günü DEĞİLSE WARN düşer ("tarih takvimde işlem günü değil → şüpheli
    bar"). Bu, v7 hayalet-bar filtresini (data/cleaning.py, phantom/volume=0
    bar'ları yakalar) TAMAMLAYAN bir katmandır — onun yerine geçmez; farklı bir
    hata sınıfını (kapalı günde damgalanmış bar) yakalar. Varsayılan None →
    davranış değişmez (mevcut çağıranlar ve golden etkilenmez)."""
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        return QualityResult(False, errors=[f"eksik kolon(lar): {missing_cols}"])

    if df.empty:
        return QualityResult(False, errors=["DataFrame boş"])

    if not isinstance(df.index, pd.DatetimeIndex):
        return QualityResult(False, errors=["index DatetimeIndex değil"])

    # 2. duplicate / monotonluk
    if df.index.has_duplicates:
        return QualityResult(False, errors=["index'te duplicate zaman damgası var"])
    if not df.index.is_monotonic_increasing:
        return QualityResult(False, errors=["index monoton artan değil"])

    working = df.copy()
    warnings: list[str] = []

    # 1. NaN: baştaki warm-up NaN'ları at, ortadaki NaN'lar fail
    nan_mask = working[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    if nan_mask.any():
        if nan_mask.all():
            return QualityResult(False, errors=["tüm satırlar NaN"])
        first_valid_pos = (~nan_mask).values.argmax()
        first_valid = working.index[first_valid_pos]
        remainder_nan = nan_mask.loc[first_valid:]
        if remainder_nan.any():
            bad_idx = remainder_nan[remainder_nan].index.tolist()
            return QualityResult(False, errors=[f"ortada NaN satır(lar) var: {bad_idx[:5]}"])
        working = working.loc[first_valid:]

    # 3. OHLC tutarlılığı — küçük bir rtol/atol toleransıyla (auto_adjust'ın
    # temettü/split düzeltmesinden kaynaklanan kayan nokta gürültüsü, örn.
    # high'ın close'a "neredeyse eşit ama 1e-16 küçük" çıkması, gerçek bir veri
    # sorunu değildir — bkz. BACKTEST_REVIEW_v5.md'deki teşhis notu).
    max_oc = working[["open", "close"]].max(axis=1)
    min_oc = working[["open", "close"]].min(axis=1)
    high_slack = ohlc_atol + ohlc_rtol * max_oc.abs()
    low_slack = ohlc_atol + ohlc_rtol * min_oc.abs()
    bad_high = working["high"] < max_oc - high_slack
    bad_low = working["low"] > min_oc + low_slack
    if bad_high.any() or bad_low.any():
        bad_idx = working.index[bad_high | bad_low].tolist()
        return QualityResult(False, errors=[f"OHLC tutarsızlığı (high/low ihlali): {bad_idx[:5]}"])

    # 4. Ardışık kapanış sıçraması (%20 üstü -> WARN, fail değil)
    pct_change = working["close"].pct_change().abs()
    jumps = pct_change[pct_change > jump_threshold_pct]
    if not jumps.empty:
        warnings.append(
            f"%{jump_threshold_pct * 100:.0f} üzeri kapanış sıçraması tespit edildi "
            f"(split/temettü şüphesi): {jumps.index.tolist()}"
        )

    # 5. Stale data
    if max_staleness is not None:
        last_ts = working.index[-1]
        if hasattr(last_ts, "to_pydatetime"):
            last_ts = last_ts.to_pydatetime()
        reference_now = now or last_ts
        if reference_now - last_ts > max_staleness:
            return QualityResult(
                False,
                errors=[f"son bar zamanı çok eski: {last_ts} (şimdi: {reference_now})"],
                warnings=warnings,
            )

    # 6. (opt-in) Takvim ikinci-doğrulama katmanı — kapalı günde damgalanmış bar (Bölüm 5)
    if calendar_id is not None:
        from core.calendars import get_calendar
        cal = get_calendar(calendar_id)
        non_session = [ts for ts in working.index if not cal.is_trading_day(ts.date())]
        if non_session:
            warnings.append(
                f"{calendar_id} takviminde işlem günü OLMAYAN tarihlerde bar var "
                f"(şüpheli, hayalet-bar filtresini tamamlayan katman): "
                f"{[str(ts.date()) for ts in non_session[:5]]}"
            )

    return QualityResult(True, errors=[], warnings=warnings, cleaned_df=working)

import pandas as pd
import pytest

from data.cleaning import filter_ghost_bars, load_and_clean_universe, normalize_bist_dates


def test_normalize_bist_dates_shifts_utc_label_to_real_istanbul_day():
    """UTC 21:00 (önceki takvim günü) -> gerçek Istanbul günü UTC gece yarısı
    olarak yeniden etiketlenir (DIAGNOSTICS_v6.md'nin EREGL hayalet-bar günü:
    ham UTC etiketi '2024-04-08', gerçek Istanbul günü '2024-04-09')."""
    idx = pd.to_datetime(["2024-04-07 21:00:00", "2024-04-08 21:00:00", "2024-04-14 21:00:00"], utc=True)
    df = pd.DataFrame({"open": [1, 2, 3], "high": [1, 2, 3], "low": [1, 2, 3],
                       "close": [1, 2, 3], "volume": [10, 0, 10]}, index=idx)
    corrected = normalize_bist_dates(df)
    assert list(corrected.index.strftime("%Y-%m-%d")) == ["2024-04-08", "2024-04-09", "2024-04-15"]
    assert corrected.index.tz is not None and str(corrected.index.tz) == "UTC"
    # Saat bileşeni gece yarısına (UTC) sıfırlanmış olmalı
    assert all(t.time() == pd.Timestamp("00:00:00").time() for t in corrected.index)


def test_normalize_bist_dates_empty_df_returns_unchanged():
    df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    result = normalize_bist_dates(df)
    assert result.empty


def test_filter_ghost_bars_removes_singleton_flat_zero_volume_bar():
    """EREGL senaryosu: bir tarih yalnızca EREGL'de var (diğer 11 sembolde yok),
    o barın volume'u 0 ve OHLC önceki kapanışla birebir aynı -> elenir."""
    dates_common = pd.to_datetime(["2024-04-07", "2024-04-15"], utc=True)
    ghost_date = pd.to_datetime(["2024-04-08"], utc=True)

    eregl = pd.DataFrame({
        "open": [20.08, 20.25, 20.25], "high": [20.32, 20.25, 20.34],
        "low": [19.90, 20.25, 19.90], "close": [20.25, 20.25, 19.95],
        "volume": [164_648_494, 0, 133_819_962],
    }, index=dates_common.insert(1, ghost_date[0]))

    other = pd.DataFrame({
        "open": [10.0, 10.2], "high": [10.1, 10.3], "low": [9.9, 10.1],
        "close": [10.05, 10.25], "volume": [1000, 1000],
    }, index=dates_common)

    cleaned, log = filter_ghost_bars({"EREGL": eregl, "OTHER": other})

    assert len(cleaned["EREGL"]) == 2  # hayalet bar elendi
    assert ghost_date[0] not in cleaned["EREGL"].index
    assert len(cleaned["OTHER"]) == 2  # dokunulmadı

    assert len(log) == 1
    assert log[0]["symbol"] == "EREGL"
    assert log[0]["date"] == ghost_date[0]


def test_filter_ghost_bars_keeps_bar_present_in_multiple_symbols():
    """Aynı 'düz + volume=0' desen, tarih İKİ sembolde de varsa (yani genel
    bir piyasa günüyse, tek-sembol artefaktı değilse) ELENMEMELİ."""
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True)
    flat_zero_vol = pd.DataFrame({
        "open": [10.0, 10.0], "high": [10.0, 10.0], "low": [10.0, 10.0],
        "close": [10.0, 10.0], "volume": [1000, 0],
    }, index=dates)

    cleaned, log = filter_ghost_bars({"A": flat_zero_vol.copy(), "B": flat_zero_vol.copy()})

    assert len(cleaned["A"]) == 2
    assert len(cleaned["B"]) == 2
    assert log == []


def test_filter_ghost_bars_keeps_singleton_date_with_real_volume():
    """Tarih tek sembolde olsa bile volume>0 ise (gerçek bir işlem günü,
    yalnızca diğer sembolün o gün verisi eksikse) ELENMEMELİ."""
    dates_a = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"], utc=True)
    dates_b = pd.to_datetime(["2024-01-01", "2024-01-03"], utc=True)  # 01-02 eksik ama GERÇEKTEN eksik

    a = pd.DataFrame({
        "open": [10.0, 10.5, 11.0], "high": [10.2, 10.7, 11.2], "low": [9.9, 10.3, 10.8],
        "close": [10.1, 10.6, 11.1], "volume": [1000, 500, 1000],  # 01-02 gerçek hacimli
    }, index=dates_a)
    b = pd.DataFrame({
        "open": [5.0, 5.2], "high": [5.1, 5.3], "low": [4.9, 5.1],
        "close": [5.05, 5.25], "volume": [1000, 1000],
    }, index=dates_b)

    cleaned, log = filter_ghost_bars({"A": a, "B": b})

    assert len(cleaned["A"]) == 3  # hiçbir şey elenmedi
    assert log == []


def test_filter_ghost_bars_first_bar_of_symbol_is_never_eliminated():
    """prev_close olmadan (sembolün ilk barı) hayalet sayılamaz."""
    dates_a = pd.to_datetime(["2024-01-01"], utc=True)
    dates_b = pd.to_datetime(["2024-01-05"], utc=True)
    a = pd.DataFrame({"open": [10.0], "high": [10.0], "low": [10.0], "close": [10.0], "volume": [0]}, index=dates_a)
    b = pd.DataFrame({"open": [5.0], "high": [5.0], "low": [5.0], "close": [5.0], "volume": [0]}, index=dates_b)

    cleaned, log = filter_ghost_bars({"A": a, "B": b})
    assert len(cleaned["A"]) == 1
    assert len(cleaned["B"]) == 1
    assert log == []


def test_load_and_clean_universe_normalizes_then_filters():
    dates_raw = pd.to_datetime(["2024-04-07 21:00:00", "2024-04-08 21:00:00", "2024-04-14 21:00:00"], utc=True)
    eregl_raw = pd.DataFrame({
        "open": [20.08, 20.25, 20.25], "high": [20.32, 20.25, 20.34],
        "low": [19.90, 20.25, 19.90], "close": [20.25, 20.25, 19.95],
        "volume": [164_648_494, 0, 133_819_962],
    }, index=dates_raw)
    other_raw = pd.DataFrame({
        "open": [10.0, 10.2], "high": [10.1, 10.3], "low": [9.9, 10.1],
        "close": [10.05, 10.25], "volume": [1000, 1000],
    }, index=pd.to_datetime(["2024-04-07 21:00:00", "2024-04-14 21:00:00"], utc=True))

    loader = {"EREGL": eregl_raw, "OTHER": other_raw}
    cleaned, log = load_and_clean_universe(["EREGL", "OTHER"], lambda s: loader[s])

    assert len(cleaned["EREGL"]) == 2
    assert len(log) == 1
    # tarihler normalize edilmiş olmalı (Istanbul günü 2024-04-08, 2024-04-15)
    assert list(cleaned["EREGL"].index.strftime("%Y-%m-%d")) == ["2024-04-08", "2024-04-15"]

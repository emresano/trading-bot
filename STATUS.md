# Proje Durumu
Son güncelleme: 2026-07-05T14:20:00+03:00 (Europe/Istanbul)
Şu an: Faz 1 tamamlandı — Faz 2'ye başlanacak
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı)
Bu oturumda yapılan:
- Git repo başlatıldı (`main` branch), CLAUDE.md ilk commit.
- `.gitignore`, `requirements.txt` oluşturuldu; `.venv` (Python 3.11.6) kuruldu.
- **Bağımlılık çözümü:** `pandas-ta==0.3.14b0` PyPI'dan tamamen kaldırılmış (yalnızca
  Python≥3.12 gerektiren 0.4.67b0/0.4.71b0 kalmış), upstream GitHub repo
  (twopirllc/pandas-ta) da silinmiş — eski sürüme hiçbir kurulum yolu yok.
  Çözüm: `pandas-ta-classic==0.6.52` (topluluk fork'u, aynı fonksiyonel API:
  `ta.ema/adx/rsi/macd/atr/bbands`, ama import adı `pandas_ta_classic`).
  `numpy` pini `1.26.*` → `2.2.*` yükseltildi (pandas-ta-classic numpy≥2.0 istiyor;
  eski numpy 1.26 pini zaten yalnızca eski pandas-ta'nın numpy 2.x
  uyumsuzluğunu atlatmak içindi). Detaylı gerekçe commit `e31e401`'de.
- `core/models.py`, `core/clock.py`, `core/config.py` yazıldı (Bölüm 4 sözleşmesi
  aynen korunarak).
- `config/config.yaml` (Bölüm 6 şeması aynen) ve `config/secrets.env.example`
  oluşturuldu.
- `data/historical.py` (yfinance artımlı parquet cache), `data/quality.py`
  (5 kontrol), `data/resample.py` (1h→4H BIST seans hizalı) yazıldı.
- **Önemli düzeltme:** yfinance `history(start=None)` çağrısı varsayılan olarak
  yalnızca ~1 aylık veri döndürüyor ("sınırsız geçmiş" garantisi yok); `start`
  verilmediğinde `period="max"` zorunlu hale getirildi (`download_bars`).
- `tests/fixtures/quality_*.csv` (6 senaryo: good, nan_middle, leading_nan,
  ohlc_violation, duplicate_index, price_jump) + `tests/test_config.py`,
  `tests/test_data_quality.py`, `tests/test_resample.py` yazıldı.
- `pytest.ini` (`pythonpath = .`) eklendi.
- Faz 1 Bitti Tanımı'nın 4 maddesi de çalıştırılarak doğrulandı:
  1. `pytest -q` → 30 passed.
  2. `python -m data.historical --symbols THYAO,GARAN,ASELS` → cache dolduruyor
     (THYAO/GARAN/ASELS: 6724'er günlük bar, 2000-05-10'dan bugüne).
  3. Quality kontrolleri fixture'daki 6 bozuk-veri senaryosunun hepsini doğru
     sınıflandırıyor (fail/pass+warn).
  4. Geçersiz config (örn. `risk_per_trade_pct=0.05`, `mode=real` + yanlış onay
     cümlesi) `ConfigError` ile açıkça reddediliyor.

Sırada: Faz 2 — `indicators/engine.py` (10 bileşen, `pandas_ta_classic` importuyla)
ve `strategy/signal_engine.py` (huni + exit mantığı) yazılacak. İlk somut adım:
`indicators/engine.py`'de `add_ema`/`add_adx`/`add_rsi`/`add_macd`/`add_atr`/
`add_bbands`/`add_swings`/`add_support_resistance`/`add_volume_confirm`/
`add_candle_patterns` fonksiyonlarını `FEATURE_PIPELINE` ile yazmak, ardından
`tests/fixtures/thyao_daily_2022.csv` golden fixture'ını üretip
`tests/test_indicators.py`'yi buna göre yazmak.

Bilinen sorun/blok: yok.

Varsayımlar/kararlar:
- pandas-ta yerine pandas-ta-classic + numpy 2.2 (yukarıda gerekçelendirildi,
  commit e31e401).
- BIST seans/müzayede saatleri (`core/clock.py`) yaklaşık değerlerle
  (10:00-18:00 sürekli, 09:40-09:55 açılış müzayedesi, 18:00-18:10 kapanış
  müzayedesi) sabitlendi — Faz 5'te resmi kaynakla doğrulanacak (Bölüm 16 #5).
- `data.historical.download_bars`: `start=None` olduğunda `period="max"`
  zorunlu kılındı (yfinance varsayılanı yalnızca ~1 ay veri döndürüyor).
- Resmi tatil takvimi `core.clock.is_trading_day`'de MVP kapsamı dışı
  bırakıldı (yalnızca hafta içi kontrolü) — Faz 5/6'da gerekirse eklenir.

Limit nedeniyle durdu mu: hayır.

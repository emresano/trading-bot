# Proje Durumu
Son güncelleme: 2026-07-05T15:10:00+03:00 (Europe/Istanbul)
Şu an: Faz 2 tamamlandı — Faz 3'e başlanacak
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal Motoru)
Bu oturumda yapılan (Faz 2):
- `indicators/engine.py`: 10 saf fonksiyon (EMA, ADX, RSI, MACD, ATR+atr_ma20,
  Bollinger, fraktal swing, destek/direnç, hacim teyidi, 3 mum formasyonu —
  engulfing/pin bar/inside-bar breakout elle implemente edildi). `build_features()`
  bunları `cfg.signal`'den bağlayarak sırayla uygular, girdiyi mutate etmez.
  `pandas_ta_classic` çıktı kolonları (`ADX_14`, `MACD_12_26_9`, `BBL_20_2.0` vb.)
  prefix-eşleşmeli `_col()` helper'ıyla okunuyor (format kırılganlığına karşı).
- `tests/fixtures/thyao_daily_2022.csv`: gerçek THYAO günlük verisi
  (2021-10-03 → 2022-12-29, 316 bar), cache'ten üretilip sabitlendi.
- `tests/test_indicators.py`: son 5 bar için pandas-ta-classic 0.6.52 ile
  üretilip sabitlenen referans değerlerle 1e-6 toleranslı karşılaştırma,
  RSI/ATR/BBands sınır testleri, swing'in son-n-barda hep False olduğu testi,
  mutate-etmeme testi, 6 elle kurgulanmış mum formasyonu senaryosu.
- `strategy/signal_engine.py`: Bölüm 8.2 Gate mimarisi — 10 gate fonksiyonu
  (trend, regime, rsi, macd, atr_anomaly, bb_overextension, structure_rr,
  volume, trigger_4h, mtf), `ENTRY_GATES`, `evaluate_entry`, `evaluate_exit`.
  Çoklu-bar bağlam gerektiren kontroller (MACD "son 2 bar yükseliş", exit'in
  "3 bardır düşen histogram") gate imzasını (d, h4, cfg) bozmadan, ilgili
  önceki bar değerlerini satıra ekleyerek çözüldü. Degrade mod (h4_df=None):
  gate_trigger_4h günlük pattern kolonlarına düşüyor, gate_mtf SKIP-PASS
  dönüyor.
- Debug CLI: `python -m strategy.signal_engine --symbol THYAO --date <tarih>`
  o günün 10 gate kararını insan-okur formatta basıyor (doğrulandı: 2022-12-29
  ve spec'in kendi örneği 2024-06-03).
- THYAO'nun tüm tarihçesi (~6400 kapanmış bar, 2000-2026) üzerinde
  `evaluate_entry` taraması hatasız/NaN'sız koştu — Faz 2 Bitti Tanımı'nın
  istediği "2 yıllık veri" eşiğini fazlasıyla aşıyor. 0 ENTER_LONG üretmesi
  beklenen bir durum (huni kasıtlı olarak çok seçici — Bölüm 0.3 "sermaye
  koruma > getiri" felsefesi); gerçek sinyal frekansı değerlendirmesi Faz 4
  backtest'in konusu.
- `tests/test_signal_engine.py`: her gate için ayrı PASS/FAIL/detail testi,
  "9 PASS + 1 FAIL → HOLD_CASH + 10 satır reasons" huni testi, erken gate'te
  durma testi, tam-geçiş ENTER_LONG testi (stop/target doğrulamalı),
  evaluate_exit'in iki tetikleyicisi + HOLD_POSITION testi.
- Faz 2 Bitti Tanımı'nın 3 maddesi de çalıştırılarak doğrulandı:
  1. `pytest -q` → 81 passed (30 Faz1 + 14 indikatör + 37 sinyal motoru).
  2. Debug CLI insan-okur çıktı üretiyor (yukarıdaki iki tarihle doğrulandı).
  3. Tüm THYAO tarihçesi üzerinde sinyal taraması NaN/exception vermeden koştu.

Sırada: Faz 3 — `risk/risk_engine.py` (Bölüm 9). İlk somut adım:
`size_and_approve(sig, acct, cfg, corr_fn)` fonksiyonunu Bölüm 9.2'deki
referans implementasyona sadık şekilde yazmak (kapı sırası: kill_switch →
breaker → daily/weekly loss limit → max_positions → min_rr → correlation →
boyutlama → notional/nakit kırpma → min qty). Korelasyon hesabı ve
breaker/kill-switch dosya mekanikleri (`runtime/KILL_SWITCH`,
`runtime/BREAKER_TRIPPED`) de bu fazda yazılacak. Bölüm 9.3'teki sayısal
örnek (equity=100.000, risk %0.75, entry=100, stop=94 → qty=125) test
olarak eklenecek; her RejectReason en az bir testte üretilecek.

Bilinen sorun/blok: yok.

Varsayımlar/kararlar (Faz 2'de eklenenler):
- MACD "son 2 bar yükseliş" kontrolü: `macd_hist[t] > macd_hist[t-1]` olarak
  yorumlandı (iki histogram değeri arası kıyas — spec'in "son 2 bar" ifadesi
  bunu kastediyor; 3+ bar monotonluk istemiyor).
- Exit'teki "macd_hist üç bardır düşüyor": `hist[t] < hist[t-1] < hist[t-2]`
  (üç ardışık değerin kesin azalan sıralaması) olarak uygulandı.
- `gate_structure_rr` risk motorunun (Faz 3) resmi min_rr reddinden önce,
  huni içinde bir ön-filtre olarak çalışıyor (Bölüm 8.1 tablosundaki "hedef
  çok yakınsa giriş yok" rolü); risk_engine kendi min_rr kontrolünü yine de
  bağımsız olarak yapacak (defence-in-depth, tek doğruluk kaynağını bozmuyor
  çünkü ikisi de aynı `entry/stop/target` formülünü kullanıyor).

Önceki fazdan taşınan varsayımlar (Faz 1):
- pandas-ta yerine pandas-ta-classic + numpy 2.2 (commit e31e401).
- BIST seans/müzayede saatleri yaklaşık değerlerle sabitlendi — Faz 5'te
  resmi kaynakla doğrulanacak (Bölüm 16 #5).
- `data.historical.download_bars`: `start=None` olduğunda `period="max"`
  zorunlu kılındı.
- Resmi tatil takvimi MVP kapsamı dışı (yalnızca hafta içi kontrolü).

Limit nedeniyle durdu mu: hayır.

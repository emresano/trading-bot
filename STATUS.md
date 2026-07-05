# Proje Durumu
Son güncelleme: 2026-07-05T15:10:00+03:00 (Europe/Istanbul)
Şu an: **Faz 4 tamamlandı — DURMA NOKTASI 1'de duruluyor (Bölüm 0.1).
Faz 5'e geçilmedi, kullanıcı onayı bekleniyor.**
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal
Motoru), Faz 3 (Risk Motoru), Faz 4 (Backtest Harness)

Bu oturumda yapılan (Faz 4):
- `backtest/engine.py`: Bölüm 12.2'nin 4 adımlı event-driven döngüsü (pending
  giriş/çıkışları t+1 açılışında doldur → stop/target intrabar kontrolü,
  STOP ÖNCELİKLİ → evaluate_exit → evaluate_entry+risk_engine → equity
  snapshot). Degrade mod (h4_df=None) bilinçli bir kapsam kararıyla
  kullanıldı — gerçek günlük/4H takvim-günü hizalaması (yfinance'in daily
  barları Europe/Istanbul tz'de, 4H resample UTC'de) ek karmaşıklık ve
  look-ahead riski taşıdığından bu fazda ertelendi.
- **Bug fix (Faz 2'den):** `gate_trend`/`gate_mtf`/`evaluate_exit`,
  `indicators.engine`'in `cfg.signal.ema_fast/ema_slow`'dan ürettiği kolon
  adları yerine `"ema_50"/"ema_200"` sabit string'lerini okuyordu — yalnızca
  config.yaml'daki varsayılan 50/200 ile çalışıyordu, farklı bir
  ema_fast/slow ile KeyError verirdi. Artık dinamik kolon adı okunuyor
  (backtest'in gevşetilmiş test config'iyle bu hata ortaya çıktı, düzeltildi).
- `backtest/metrics.py`: total_return, cagr, max_drawdown, sharpe, win_rate,
  profit_factor, avg_r_multiple, expectancy, trade_count, time_in_cash_pct
  + `classify_regime`/`regime_breakdown` (bull/bear/sideways).
- `backtest/walkforward.py`: 27 kombinasyonluk dar grid (Bölüm 12.7),
  komşu-sağlamlık kriteriyle parametre seçimi (en yüksek skor değil),
  OOS birleştirme + kabul kriteri (`evaluate_acceptance`).
- `backtest/montecarlo.py`: `monte_carlo_dd` Bölüm 12.6'nın referans kodu
  aynen; `trade_returns_from_trades` (r_multiple × risk_per_trade_pct
  yaklaşıklaması, gerekçesi kod içinde belgeli).
- `backtest/cli.py`: `python -m backtest.cli --symbols ... --walk-forward
  --monte-carlo --regime-split --sweep --out DIR` → report.md, trades.csv,
  equity.png, sweep_results.csv. Determinizm testte doğrulandı (bayt-bayt
  aynı çıktı, 2 çalıştırma).
- 142/142 test yeşil (pytest -q).
- **Gerçek backtest çalıştırıldı:** THYAO+GARAN+ASELS, 2000-05-09→2026-07-02
  (~26 yıl), tam CLI (`--walk-forward --monte-carlo --regime-split --sweep`),
  ~8 dakikada tamamlandı. **Sonuç: varsayılan parametrelerle 0 trade.** 27
  kombinasyonluk sweep'in HİÇBİRİ 3'ten fazla trade üretmedi; walk-forward'ın
  48 penceresinin hiçbirinde komşu-sağlamlık kriteri geçmedi (`robust=False`).
- `BACKTEST_REVIEW.md` yazıldı (repo kökünde) — dürüst değerlendirme: motor
  doğru çalışıyor (look-ahead yasağı, determinizm, stop-önceliği, komisyon/
  slippage testlerle kanıtlı) ama sinyal hunisi aşırı seçici; strateji fiilen
  hiç test edilemedi (0 trade → tüm metrikler anlamsız/sıfır).

**Sırada:** Hiçbir şey — burada duruluyor. Kullanıcı BACKTEST_REVIEW.md'yi
okuyup üç seçenekten birine karar verecek: (A) huniyi olduğu gibi kabul edip
Faz 5'e geç, (B) sinyal eşiklerini (RSI bandı, ADX eşiği vb.) gözden geçir
[risk limiti değil, strateji parametresi — yine de mimari karar, onay
istiyorum], (C) sembol/enstrüman kapsamını genişlet. Kullanıcı "Faz 5
onaylandı" veya net bir yön derse ona göre devam edilecek.

Bilinen sorun/blok: **Kullanıcı onayı bekleniyor (Durma Noktası 1) — bu bir
blok değil, spec'in kasıtlı, aşılamaz bir kapısı.**

Varsayımlar/kararlar (Faz 4'te eklenenler):
- Backtest degrade modda (h4_df=None) çalıştırıldı — gerçek 4H entegrasyonu
  ertelendi (yukarıda gerekçelendirildi). Bu, backtest sonuçlarının yalnızca
  günlük-kademe performansını yansıttığı, 4H tetik/MTF katkısının test
  edilmediği anlamına gelir.
- Walk-forward'ın skor fonksiyonu olarak Sharpe kullanıldı (spec bunu
  açıkça belirtmiyor, "en yüksek skor değil komşu-sağlam" ilkesini
  uygulayacak somut bir metrik gerekiyordu).
- Monte Carlo'nun `trade_returns` girdisi `r_multiple × risk_per_trade_pct`
  ile yaklaşıklandı (spec bu dönüşümü açık bırakmıştı).
- Walk-forward, her pencerede build_features'ı kendi veri dilimi üzerinde
  sıfırdan hesaplıyor (tam tarihçe üzerinde hesaplayıp dilimlemek yerine) —
  train_months (24) min_history_bars'ı (260) yeterince aştığından pratik
  etkisi düşük, ama not edilmiş bir basitleştirme.

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (commit e31e401); BIST seans saatleri yaklaşık (Faz 5'te
doğrulanacak); `data.historical.download_bars` `period="max"` zorunlu;
resmi tatil takvimi MVP dışı; MACD "son 2 bar yükseliş" =
`hist[t]>hist[t-1]`; exit'in "3 bar düşüş" = kesin azalan üçlü sıralama.

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu (bu,
Bölüm 2.3'teki "limit nedeniyle durma" ile karıştırılmamalı; bu kalıcı,
onay gerektiren bir kapı).

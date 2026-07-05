# Proje Durumu
Son güncelleme: 2026-07-05T20:10:00+03:00 (Europe/Istanbul)
Şu an: **Faz 4 revizyon turu (v3) tamamlandı — DURMA NOKTASI 1'de duruluyor
(Bölüm 0.1). Faz 5'e geçilmedi, kullanıcı onayı bekleniyor.**
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal
Motoru), Faz 3 (Risk Motoru), Faz 4 (Backtest Harness — v1 0-trade →
gate-teşhisi → v2 2-hedefli düzeltme (89 trade) → v3 walk-forward test-harness
düzeltmesi (gerçek OOS ölçümü))

Bu oturumda yapılan (Faz 4 revizyon turu v3):
- **Seçenek A onaylandı:** `BACKTEST_REVIEW_v2.md`'de tespit edilen walk-forward
  test-harness kusuru düzeltildi. Kusur: her pencere kendi veri dilimi üzerinde
  `build_features`'ı sıfırdan hesaplıyordu; test dilimi (6 ay ≈ 131 gün)
  `min_history_bars`'ın (260) altında kaldığından 48 pencerenin TAMAMINDA OOS
  trade sayısı sıfırdı.
- `backtest/engine.py`: `run_backtest`'e `date_range` ve `precomputed_features`
  opsiyonel parametreleri eklendi. `build_features` artık TAM tarihçe üzerinde
  bir kez hesaplanıyor; `min_history_bars` kontrolü tam tarihçedeki mutlak
  konuma göre uygulanıyor; `date_range` yalnızca hangi barların simüle
  edileceğini kısıtlıyor (warm-up'ı kısıtlamıyor) — test dilimindeki bir gün
  kendinden önceki tam tarihçeyi (train dahil) warm-up olarak kullanabiliyor
  (look-ahead değil, yalnızca geçmişe bakıyor).
- `backtest/walkforward.py`: `run_walk_forward` artık `build_features`'ı sembol
  başına bir kez hesaplıyor (`_slice_loader` kaldırıldı), pencereleri
  `date_range` ile veriyor — hem doğru hem daha hızlı (27 kombinasyon aynı
  özellik DataFrame'ini paylaşıyor).
- Kanıt testi eklendi: kendi başına `min_history_bars`'tan (15) çok kısa bir
  pencerede (3 gün) bile, tam tarihçe warm-up'ı sayesinde trade üretilebildiğini
  gösteren test + kontrast testi (tam tarihçe de kısaysa hâlâ trade yok) +
  `precomputed_features`'ın `load_daily`'yi atladığını doğrulayan test.
  159/159 test yeşil.
- **Gerçek backtest v3 çalıştırıldı** (aynı 3 sembol, aynı 26 yıl, tam CLI,
  ~34 dakika): Ana backtest/rejim/Monte Carlo/sweep sonuçları v2 ile **bayt-bayt
  aynı** (`trades.csv` diff ile doğrulandı — düzeltme yalnızca walk-forward'ı
  etkiledi). Walk-forward artık **23/48 pencerede** OOS trade üretiyor (v2'de
  0/48), toplam 54 OOS trade. **Birleşik OOS profit factor: 1.13** (Bölüm
  12.5'in >1.1 eşiğini GEÇİYOR). **Birleşik OOS max DD: -6.37%.** **Kabul
  kriteri sonucu: GEÇMEDİ** — ama artık gerçek bir ölçüme dayanıyor: pf_ok
  sağlandığından (1.13>1.1), başarısızlık mantıksal olarak dd_ok'tan geliyor
  (OOS max DD, ortalama in-sample max DD'nin 1.5 katından kötü) — klasik bir
  overfitting işareti.
- `BACKTEST_REVIEW_v3.md` yazıldı (repo kökünde, v1/v2'nin yanında duruyor).

**Sırada:** Hiçbir şey — burada duruluyor (Durma Noktası 1). Kullanıcının kararı
bekleniyor. Not: raporun walk-forward bölümü şu an `avg_in_sample_max_drawdown`
sayısını ayrıca basmıyor (yalnızca pass/fail) — bunu görmek isterse küçük,
davranış değiştirmeyen bir rapor iyileştirmesi (yalnızca zaten hesaplanan bir
sayının yazdırılması) yeterli olur, ~34 dakikalık yeniden koşum gerektirmez.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1)** — kasıtlı, aşılamaz kapı.
2. Walk-forward artık DOĞRU ölçüyor ama sonuç OLUMSUZ: DD kriteri geçmedi
   (overfitting işareti). Bu bir "bug" değil, gerçek bir bulgu — kullanıcının
   nasıl ilerlemek istediğine karar vermesi gerekiyor.
3. `indicators.engine.build_features`, çok kısa (< ~10-15 bar) bir DataFrame
   verildiğinde pandas_ta_classic'in None dönmesi nedeniyle AttributeError ile
   çöküyor (önceki turdan taşınan, düşük öncelikli, gerçek kullanımda
   tetiklenmiyor).

Varsayımlar/kararlar (bu turda eklenenler): Sweep grid'in 3 parametresinin
(atr_stop_mult, adx_min, min_rr) indikatör hesaplamasını etkilemediği
varsayımına dayanarak `precomputed_features` optimizasyonu eklendi — bu
varsayım `indicators/engine.py`'nin `add_*` fonksiyonlarının bu 3 alanı hiç
okumadığı doğrulanarak (kod okunarak) teyit edildi.

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (commit e31e401); BIST seans saatleri yaklaşık (Faz 5'te
doğrulanacak); `data.historical.download_bars` `period="max"` zorunlu;
resmi tatil takvimi MVP dışı; MACD "son 2 bar yükseliş" = `hist[t]>hist[t-1]`;
exit'in "3 bar düşüş" = kesin azalan üçlü sıralama; backtest degrade modda
(h4_df=None) çalışıyor, gerçek 4H entegrasyonu ertelendi; compute_target artık
max(resistance, fallback) (commit 67d2dd6); gate_trigger_4h degrade modda
son-3-bar-pattern VEYA breakout (commit 67d2dd6).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

# Proje Durumu
Son güncelleme: 2026-07-05T16:35:00+03:00 (Europe/Istanbul)
Şu an: **Faz 4 revizyon turu (v2) tamamlandı — DURMA NOKTASI 1'de duruluyor
(Bölüm 0.1). Faz 5'e geçilmedi, kullanıcı onayı bekleniyor.**
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal
Motoru), Faz 3 (Risk Motoru), Faz 4 (Backtest Harness — v1 0-trade sonucu →
teşhis → 2 hedefli düzeltme → v2 89-trade sonucu)

Bu oturumda yapılan (Faz 4 revizyon turu):
- Kullanıcı isteğiyle `backtest/gate_diagnostics.py` eklendi: her sembol için
  10 gate'in tek başına ve kümülatif (kademe kademe) geçiş oranını ölçen,
  hiçbir eşiği değiştirmeyen bir teşhis aracı. Gerçek veride koşturuldu
  (`runtime/backtest_reports/gate_diagnostics.md`, gitignored). Bulgu: asıl
  darboğazlar RSI değil — `structure_rr` (kümülatif geçiş %7→%0.2) ve
  `trigger_4h` (kümülatif geçiş %0.2→%0.0, 3 sembolde de TAM SIFIR).
- Teşhise dayanarak, kullanıcı onayıyla, **yalnızca iki hedefli düzeltme**
  yapıldı (RSI bandı/ADX/min_rr dahil hiçbir başka eşik değişmedi):
  1. `compute_target()`: hedef artık `max(nearest_resistance, entry+2×(entry-stop))`
     — pullback girişinde en-yakın-direnç yapısal olarak yakın olduğundan onu
     doğrudan hedef almak R:R'yi düşürüyordu.
  2. `gate_trigger_4h()` degrade mod genişletmesi: tetik artık "son 3 barda
     mum formasyonu OLUŞTU VEYA bugünkü kapanış önceki barın high'ının
     üstünde" ise geçerli. Gerçek 4H modu (h4_df dolu) değişmedi.
  3. Yeni paylaşılan yardımcı `prepare_row_context(daily_df, i)`: çoklu-bar
     bağlam gerektiren tüm türetilmiş alanları tek yerden hesaplıyor;
     `evaluate_entry` VE `gate_diagnostics.py` artık aynı fonksiyonu kullanıyor
     (üretim/teşhis tutarlılığı garantisi).
- Ölçülen etki: `structure_rr` kümülatif geçişi %7'ye (kayıpsız), `trigger_4h`
  kümülatif geçişi %0'dan %0.52'ye çıktı.
- 156/156 test yeşil (pytest -q) — 8 yeni/güncellenmiş test (`compute_target`
  max() mantığı, `gate_structure_rr`'nin artık yakın resistance'ta geçtiği +
  min_rr fallback tabanını (2.0R) aştığında hâlâ reddettiği, `gate_trigger_4h`'nin
  yeni degrade koşulları, `prepare_row_context` birim testleri).
- **Gerçek backtest v2 çalıştırıldı** (aynı 3 sembol, aynı 26 yıl, tam CLI):
  **89 trade** (v1'de 0), toplam getiri +%4.17, CAGR %0.16/yıl, Sharpe 0.14,
  win rate %38.2, profit factor 1.20, maks. DD -%3.78. Rejim kırılımı: 81/89
  trade bull rejiminde (toplam R +8.14), bear'da yalnızca 1 trade.
- **Önemli metodoloji bulgusu (bugünkü düzeltmelerden bağımsız, Faz 4'ten
  kalma):** walk-forward'ın 48 penceresinin TAMAMINDA OOS (test) trade sayısı
  sıfır çıktı. Nedeni araştırıldı: `test_months=6` ay ≈ 131 işlem günü,
  `min_history_bars=260`'ın altında kaldığından her test dilimi huniye hiç
  girmeden elenıyor. Bu, "Kabul kriteri: GEÇMEDİ" sonucunu anlamsız kılıyor —
  strateji başarısız değil, OOS ölçümü hiç çalışmadı. Bu turun "tek revizyon,
  ek eşik değiştirme" kuralı gereği DÜZELTİLMEDİ, yalnızca tespit edilip
  `BACKTEST_REVIEW_v2.md`'de raporlandı.
- Monte Carlo: dd_p5=-%7.81 (breaker eşiği %10'un altında ama %78'ine yakın),
  dd_median=-%5.18, dd_p95=-%3.47.
- `BACKTEST_REVIEW_v2.md` yazıldı (repo kökünde, v1'in yanında duruyor,
  üzerine yazılmadı) — dürüst değerlendirme + 3 yol önerisi.

**Sırada:** Hiçbir şey — burada duruluyor (Durma Noktası 1). Kullanıcının
kararı bekleniyor. Önerilen öncelik: walk-forward test-harness bug'ının
düzeltilmesi (`build_features`'ı tam tarihçede bir kez hesaplayıp pencereleri
sonradan dilimlemek) — bu olmadan gerçek bir OOS doğrulaması elde edilemez.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1)** — kasıtlı, aşılamaz kapı.
2. **Walk-forward OOS test'i yapısal olarak çalışmıyor** (yukarıda detaylı) —
   düzeltme için kullanıcı onayı gerekecek (Faz 4 mimarisine dokunmak).
3. `indicators.engine.build_features`, çok kısa (< ~10-15 bar) bir DataFrame
   verildiğinde pandas_ta_classic'in None dönmesi nedeniyle AttributeError ile
   çöküyor (test yazarken tesadüfen keşfedildi, `tests/test_gate_diagnostics.py`
   bunu atlayarak yazıldı). Küçük bir sağlamlaştırma gerektirir, henüz
   düzeltilmedi — düşük öncelikli, gerçek kullanımda (min_history_bars=260
   kontrolünden önce hiçbir yerde bu kadar kısa veri geçilmiyor) tetiklenmiyor.

Varsayımlar/kararlar (bu turda eklenenler): yukarıdaki düzeltmelerin ikisi de
kullanıcının açık talimatıyla yapıldı, ek yorum gerektirmiyor.

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (commit e31e401); BIST seans saatleri yaklaşık (Faz 5'te
doğrulanacak); `data.historical.download_bars` `period="max"` zorunlu;
resmi tatil takvimi MVP dışı; MACD "son 2 bar yükseliş" = `hist[t]>hist[t-1]`;
exit'in "3 bar düşüş" = kesin azalan üçlü sıralama; backtest degrade modda
(h4_df=None) çalışıyor, gerçek 4H entegrasyonu ertelendi.

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

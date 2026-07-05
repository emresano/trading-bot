# Proje Durumu
Son güncelleme: 2026-07-05T22:05:00+03:00 (Europe/Istanbul)
Şu an: **Faz 4 revizyon turu (v4) tamamlandı — DURMA NOKTASI 1'de duruluyor
(Bölüm 0.1). Faz 5'e geçilmedi, kullanıcı onayı bekleniyor.**
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal
Motoru), Faz 3 (Risk Motoru), Faz 4 (Backtest Harness — v1 0-trade →
gate-teşhisi → v2 2-hedefli düzeltme (89 trade) → v3 walk-forward test-harness
düzeltmesi (gerçek OOS ölçümü, DD kriteri geçmedi) → v4 onaylı adx_min
sıkılaştırma (47 trade, ana backtest iyileşti, walk-forward sonucu değişmedi))

Bu oturumda yapılan (Faz 4 revizyon turu v4):
- **Onaylı, izole tek değişiklik:** `config/config.yaml`: `signal.adx_min:
  20 → 25`. Başka hiçbir eşik/parametre/kod davranışı değişmedi.
- `backtest/cli.py`: walk-forward raporuna bilgilendirici bir satır eklendi —
  "Birleşik OOS max DD / tam-dönem in-sample max DD" oranı. Kabul kriterine
  DAHİL DEĞİL (passed hesabı hâlâ avg_in_sample_max_drawdown×1.5'e dayanıyor),
  yalnızca ek bağlam. 159/159 test yeşil.
- **Gerçek backtest v4 çalıştırıldı** (aynı 3 sembol, aynı 26 yıl, tam CLI,
  ~36 dakika):
  - **Ana backtest her ölçütte iyileşti:** trade 89→47, PF 1.20→1.48, win rate
    38.2%→46.8%, maks DD -3.78%→-2.71%, Sharpe 0.14→0.20, MC dd_p5
    -7.81%→-4.68%.
  - **Walk-forward sonuçları BİREBİR AYNI kaldı** (OOS PF=1.13, OOS maxDD=
    -6.37%, kabul kriteri GEÇMEDİ) — çünkü walk-forward'ın 27-kombinasyonluk
    grid'i zaten `adx_min∈{15,20,25}`'in hepsini her pencerede dener; config'in
    "varsayılan" değerini değiştirmek walk-forward'ı etkilemez. `sweep_results.csv`
    da v3 ile bayt-bayt aynı çıktı (bu bağımsızlığı doğruluyor).
  - **Bilgilendirici oran kötüleşti:** OOS DD / tam-dönem DD = 1.69×→2.35×
    (pay sabit kaldı, payda küçüldüğü için oran büyüdü).
  - **Trade sayısı kontrolü:** 47 ≥ 30, kırmızı bayrak tetiklenmedi.
  - **Bull rejim yoğunluğu pratikte değişmedi:** %91.0→%89.4 (gürültü
    seviyesinde fark).
- `BACKTEST_REVIEW_v4.md` yazıldı (repo kökünde, v1-v3'ün yanında duruyor).

**Sırada:** Hiçbir şey — burada duruluyor (Durma Noktası 1). Kullanıcının
kararı bekleniyor. Ana bulgu: adx_min sıkılaştırma tek-geçişlik (in-sample)
görünümü iyileştirdi ama walk-forward'ın tespit ettiği temel overfitting
sorununu ÇÖZMEDİ (zaten walk-forward'ın kendi arama uzayının bir parçasıydı).

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1)** — kasıtlı, aşılamaz kapı.
2. Walk-forward'ın DD kriteri hâlâ geçmiyor, v3'ten değişmedi — tek parametre
   ayarıyla çözülebilecek bir sorun değil gibi görünüyor (walk-forward zaten
   bu parametreyi kendi içinde deniyor).
3. `indicators.engine.build_features`, çok kısa (< ~10-15 bar) bir DataFrame
   verildiğinde çöküyor (önceki turlardan taşınan, düşük öncelikli, gerçek
   kullanımda tetiklenmiyor).

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (commit e31e401); BIST seans saatleri yaklaşık (Faz 5'te
doğrulanacak); `data.historical.download_bars` `period="max"` zorunlu;
resmi tatil takvimi MVP dışı; MACD "son 2 bar yükseliş" = `hist[t]>hist[t-1]`;
exit'in "3 bar düşüş" = kesin azalan üçlü sıralama; backtest degrade modda
(h4_df=None) çalışıyor; compute_target max(resistance, fallback) (commit
67d2dd6); gate_trigger_4h degrade modda son-3-bar-pattern VEYA breakout
(commit 67d2dd6); walk-forward date_range/precomputed_features ile tam
tarihçe warm-up kullanıyor (commit 60a6d3f); adx_min=25 (commit d6ea8fc).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

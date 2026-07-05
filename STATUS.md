# Proje Durumu
Son güncelleme: 2026-07-06T01:50:00+03:00 (Europe/Istanbul)
Şu an: **Faz 4 veri genişletme turu (v5) tamamlandı — DURMA NOKTASI 1'de
duruluyor (Bölüm 0.1). Faz 5'e geçilmedi, kullanıcı onayı bekleniyor.**
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal
Motoru), Faz 3 (Risk Motoru), Faz 4 (Backtest Harness — v1 0-trade → gate-teşhisi
→ v2 2-hedefli düzeltme (89 trade) → v3 walk-forward test-harness düzeltmesi →
v4 onaylı adx_min sıkılaştırma (47 trade) → **v5 veri genişletme: 3→12 sembol,
2005+ (125 trade, sonuç belirgin kötüleşti — bkz. aşağı))

Bu oturumda yapılan (Faz 4 veri genişletme turu v5):
- **Sembol evreni 3→12**: THYAO/GARAN/ASELS + AKBNK, KCHOL, SAHOL, EREGL,
  TUPRS, TCELL, TOASO, SISE, ARCLK. Seçim kriteri: 2005+ kesintisiz tarihçe +
  likidite + sektör çeşitliliği (geçmiş getiriye göre DEĞİL). Survivorship
  bias notu rapora eklendi. config/config.yaml güncellendi (strateji/eşik
  değişmedi, adx_min=25 v4'teki gibi kaldı).
- **Veri kalitesi bug'ı bulundu ve düzeltildi:** `data/quality.py`'nin OHLC
  kontrolü kayan nokta epsilon gürültüsünü gerçek veri sorunuyla
  karıştırıyordu (11/12 aday YANLIŞ POZİTİF FAIL alıyordu) — rtol/atol
  toleransı eklendi. Ayrıca 7 sembolün 2000-2004 verisinde GERÇEK bozukluk
  (yfinance auto_adjust kaynaklı negatif fiyatlar) bulundu — sembol
  değişikliği gerekmedi, `--start-date 2005-01-01` ile (kullanıcının zaten
  istediği kriterle) tüm 12 sembol temiz geçti.
- `backtest/cli.py`: `--start-date` (veri kırpma) ve `--benchmark` (XU100
  al-tut + sadece-nakit karşılaştırması, kabul kriterine dahil değil, salt
  bilgilendirici) eklendi. `backtest/metrics.py`: `compute_buy_hold_metrics`,
  `cash_only_metrics` eklendi. 168/168 test yeşil.
- **Gerçek backtest v5 çalıştırıldı** (12 sembol, 2005-2026, tam CLI +
  benchmark, ~2 saat 20 dakika):
  - **Sonuç belirgin kötüleşti:** trade 47→125, toplam getiri +4.68%→**-1.06%**,
    PF 1.48→**0.97** (artık <1), maks DD -2.71%→**-20.74%** (7.7× kötü),
    Sharpe 0.20→0.01.
  - **OOS artık çok daha büyük örneklemli ve çok daha kötü:** OOS trade 54→201
    (pencere kapsaması %48→%74), OOS PF 1.13→**0.75** (artık <1.1 VE <1.0),
    OOS max DD -6.37%→**-19.90%**. Kabul kriteri: v4'te yalnızca DD tarafı
    başarısızdı, v5'te HEM PF HEM DD başarısız.
  - Sembol bazında trade dağılımı dengeli (5-16 trade/sembol, yoğunlaşma yok);
    PnL 5 sembolde net kâr, 7 sembolde net zarar.
  - Bull rejim yoğunluğu azalmadı, hafif arttı (%89.4→%92.8).
  - **Benchmark kıyası (yeni):** XU100 al-tut aynı dönemde %3,523 toplam
    getiri / %19.14 CAGR / Sharpe 0.80 — stratejiyi (Sharpe 0.01) ve
    nakitte kalmayı (0%) açık ara geçiyor. Stratejinin tek avantajı daha
    sığ drawdown (-20.74% vs endeksin -63.43%'ü).
  - **3 yeni bulgu tespit edildi, bu turda DÜZELTİLMEDİ (kapsam dışı):**
    (1) backtest motoru drawdown breaker'ı hiç tetiklemiyor (kod
    `check_and_trip_breaker` hiç çağrılmıyor), (2) Monte Carlo kırmızı bayrak
    kontrolü muhtemelen yanlış persentili (dd_p95, en hafif senaryo) kontrol
    ediyor — dd_p5 (en kötü senaryo, -%11.71) breaker eşiğini (%10) aşıyor
    ama mevcut kontrol bunu kaçırıyor, (3) adx_min=25 sıkılaştırması (v4'te
    3 sembolle onaylanmıştı) 12-sembol sweep verisinde desteklenmiyor
    (adx_min=15 daha iyi PF gösteriyor).
- `BACKTEST_REVIEW_v5.md` yazıldı (repo kökünde, v1-v4'ün yanında duruyor).

**Sırada:** Hiçbir şey — burada duruluyor (Durma Noktası 1). Kullanıcının
kararı bekleniyor. Bu, dört raporun en açık sonucu: küçük örneklemdeki
(3 sembol) iyimser görünüm, büyük örneklemde (12 sembol) tutmadı.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1)** — kasıtlı, aşılamaz kapı.
2. Backtest motoru drawdown breaker'ı simüle etmiyor (bkz. yukarı) — düzeltme
   için ayrı bir onaylı tur gerekir.
3. MC kırmızı bayrak kontrolünün hangi persentili (p5 mi p95 mi) kullanması
   gerektiği netleştirilmeli.
4. `indicators.engine.build_features`, çok kısa DataFrame'de çöküyor (önceki
   turlardan taşınan, düşük öncelikli).

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (commit e31e401); BIST seans saatleri yaklaşık; `data.historical.
download_bars` `period="max"` zorunlu; resmi tatil takvimi MVP dışı; MACD
"son 2 bar yükseliş" = `hist[t]>hist[t-1]`; exit "3 bar düşüş" = kesin azalan
üçlü sıralama; backtest degrade modda çalışıyor; compute_target
max(resistance, fallback) (67d2dd6); gate_trigger_4h degrade modda son-3-bar-
pattern VEYA breakout (67d2dd6); walk-forward date_range/precomputed_features
ile tam tarihçe warm-up (60a6d3f); adx_min=25 (d6ea8fc); 12 sembol evreni +
2005-01-01 başlangıç + OHLC tolerans fix'i (dc56ed2).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

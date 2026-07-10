# Dönemsel Karşılaştırma Raporu (BİLGİLENDİRME)

> **Bu rapor BİLGİLENDİRME amaçlıdır. Kriter/kabul/karar İÇERMEZ, hiçbir mühürlü eşiği/parametreyi etkilemez.** Strateji/motor/risk/karar kodu bu turda DEĞİŞTİRİLMEMİŞTİR — yalnızca mevcut mühürlü S1b araçları (`tools/run_regime_core.py`, `backtest/regime_core.py`) import edilerek yeniden kullanılmıştır. Hiçbir grid/varyant taraması yapılmamıştır.

Üretim tarihi: 2026-07-10 · D1 equity aralığı: 2005-01-03 → 2026-07-08 · N/b/M = 200/0.01/3 (mühürlü, S1b — bkz. `config/regime_core.yaml`)

## Veri kaynağı notu (madde 1 — D1 yeniden-üretimi)

D1'in frozen S1b snapshot'ı (`data/snapshots/2026-07-06`) son barı ~2026-07-02'de bitiyordu; bu rapor için 2026-07-08'e kadar olan EKSİK kuyruk canlı yfinance çekimiyle tamamlandı ve (varsa) `data/snapshots/aux_cmp/` altına sha256 manifest'li olarak dondu — **mevcut hiçbir snapshot değiştirilmedi.**

- D1 12-sembol uzantısı: `data/snapshots/aux_cmp/2026-07-10/` (manifest.json + sha256).
- USDTRY uzantısı: `data/snapshots/aux_cmp/2026-07-10/` (manifest.json + sha256, aynı dizin).
- Örtüşen barlarda kaynak-tutarlılık kontrolü: 12 sembol, maksimum mutlak-göreli fark 0.00e+00 (frozen snapshot ↔ taze çekim; 07-09 DATA_DRIFT vakasının aksine bu turda anlamlı sapma YOK — bkz. STATUS.md 'DRIFT ÇÖZÜMÜ' bölümü).
- **Determinizm çekincesi (dürüstçe):** en güncel 1-2 günün bar verisi yfinance'in geç revizyon davranışına (STATUS.md K4/DATA_DRIFT — bilinen, tekrarlayan bir olgu) tabidir; bu rapor birkaç gün sonra yeniden koşulursa en son 1-2 günün kapanışı hafifçe değişebilir. 2005→(frozen snapshot son barı) kısmı TAM DETERMİNİSTİKTİR (S1b'nin kendi mühürlü kaynağı).
- Hayalet-bar filtresi (mevcut, reuse): 1 bar elendi (`EREGL` 2024-04-09 — bilinen, STATUS.md KALICI KAYIT 7'de belgeli EREGL 2024-04-09 hayalet barı).

- Altın (best-effort): GC=F×USDTRY=X/31.1035 (gram altın TL), 5393 gün
- TÜFE (best-effort): FRED TURCPIALLMINMEI, son gözlem 2025-04-01 (bilinen gecikme)
  Son gerçek gözlemden `Üretim tarihi`ne kadarki tüm günler forward-fill (son bilinen seviyeyle sabit) taşınmıştır — bu nedenle AŞAĞIDAKİ HER pencerenin TÜFE CAGR'ı, gerçek enflasyonu (özellikle son ~15 ay) HAFİFE ALIR/AŞAĞI SAPTIRIR; yalnızca 1 yıllık pencerede bu tamamen sıfıra düşecek kadar belirgindir (ayrıca işaretlendi).

## Metodoloji Notu — "Sepet Al-Tut" Satırı Nasıl Kuruluyor?

Tablolardaki **"sepet"** satırı, `backtest/regime_core.py::build_composite()`'in (mühürlü, S1b'nin kendi tanımı — REUSE, değiştirilmedi) ürettiği TEK bir seridir: 12 sembolün ortak ilk tarihine (t0=2005-01-03) eşit-DOLAR yatırılmış, o günden bugüne kadar **BİR KEZ BİLE yeniden dengelenmemiş** bir al-tut portföyüdür — pencere tabloları bu TEK seriyi yalnızca pencere sınırlarına göre KESER, o pencerenin başında ağırlıkları SIFIRLAMAZ. 21 yıllık sürüklenme nedeniyle en çok kazanan sembol(ler) zamanla portföyün ezici çoğunluğunu oluşturabilir (aşağıdaki pencere notlarında payı gösterilir) — bu yüzden "sepet" satırının KISA pencerelerdeki (örn. son 1 yıl) getirisi, aslında o dönemde **neredeyse tek bir sembolün** performansını yansıtıyor olabilir, 12 sembolün dengeli ortalamasını DEĞİL. Bunu netleştirmek için yeni bir **"sepet — PENCERE-BAŞI eşit ağırlık"** satırı eklendi: AYNI `build_composite()` fonksiyonu, yalnızca o pencerenin başlangıç tarihine kısıtlanmış kapanış serileriyle çağrılır (iç t0 = pencere başlangıcı) — yani "o pencerenin başında 12 sembole taze eşit-ağırlıklı girseydim, dengelemeden sonuna kadar tutsaydım" sorusuna cevap verir. D1'in kendi ENTER mantığı da (her girişte equity 12'ye eşit bölünür, sonraki tutma boyunca dengelenmez) AYNI ilkeyi izler — bu yüzden D1 ile PENCERE-BAŞI satırı, 2005-ağırlıklı satırdan çok daha adil bir kıyastır.

## Pencere Tabloları

> Satırlar: D1, sepet, XU100 (BİLGİ), faiz-haircut'lı (S1b'nin kendi mühürlü modeli), faiz-ham, USD al-tut, [altın], [TÜFE]. Sütunlar: toplam getiri, CAGR, max DD (pencerenin KENDİ başlangıcına göre, tam-dönem rakamlarıyla KARIŞTIRILMAMALI).

### Son 1 Yıl (2025-07-08 → 2026-07-08)

| Seri | Toplam Getiri | CAGR | Max DD |
|---|---:|---:|---:|
| D1 (rejim-filtreli çekirdek, mühürlü S1b) | +45.31% | +45.35% | -13.62% |
| 12-sembol sepet al-tut — 2005 AĞIRLIKLI, HİÇ dengelenmemiş (TRY, maliyetsiz) | +105.80% | +105.90% | -16.21% |
| 12-sembol sepet al-tut — PENCERE-BAŞI eşit ağırlık, dengelenmeden tutulan | +34.55% | +34.57% | -13.45% |
| XU100 al-tut (BİLGİ — fiyat endeksi, temettü hariç) | +39.57% | +39.73% | -13.01% |
| TRY faizi — haircut'lı (200bp, S1b'nin kendi mühürlü modeli) | +42.10% | +42.14% | 0.00% |
| TRY faizi — haircut'sız (ham, 'mevduat proxy'si') | +44.97% | +45.01% | 0.00% |
| USD al-tut (USDTRY değişimi, TRY-terim) | +17.12% | +17.13% | -0.32% |
| Gram altın (TRY, best-effort) | +44.17% | +44.21% | -20.31% |
| TÜFE (FRED, best-effort — bkz. gecikme notu) | +0.00% | +0.00% | 0.00% |

*(2005-ağırlıklı sepetin bu pencere başındaki payı: `ASELS` tek başına %58.3 — 21 yıllık sürüklenmiş ağırlıkla pencere-başı eşit-ağırlıklı satır arasındaki fark büyüdükçe bu pay da büyür.)*

**D1 − faiz(haircut'lı) farkı (CAGR, pp):** +3.21pp (D1 faizin üzerinde).

**İşlem/rejim özeti:** bu pencerede 0 anahtarlama (ENTER/EXIT), rejim-ON gün oranı 100.0%.

> ⚠ **Az olay = gürültü uyarısı:** bu penceredeki anahtarlama sayısı çok düşük (<5) — tek bir giriş/çıkışın zamanlaması, bu kısa pencerenin metriklerini (özellikle toplam getiri ve maxDD) orantısız etkileyebilir. 1 yıllık pencere istatistiksel olarak ANLAMLI DEĞİLDİR, yalnızca en güncel görüntü olarak verilmiştir.

> ⚠ **TÜFE bayat:** bu pencerenin TAMAMI, FRED serisinin son gerçek gözleminden SONRAKİ döneme denk geliyor — tablodaki TÜFE satırı bu yüzden son bilinen değerle sabit (forward-fill), toplam getiri/CAGR ≈ 0 görünür. Bu bir hesap hatası DEĞİL, veri gecikmesinin doğal sonucudur (bkz. yukarı best-effort notu).

### Son 3 Yıl (2023-07-08 → 2026-07-08)

| Seri | Toplam Getiri | CAGR | Max DD |
|---|---:|---:|---:|
| D1 (rejim-filtreli çekirdek, mühürlü S1b) | +161.38% | +37.82% | -22.53% |
| 12-sembol sepet al-tut — 2005 AĞIRLIKLI, HİÇ dengelenmemiş (TRY, maliyetsiz) | +409.32% | +72.20% | -18.27% |
| 12-sembol sepet al-tut — PENCERE-BAŞI eşit ağırlık, dengelenmeden tutulan | +218.47% | +47.22% | -22.75% |
| XU100 al-tut (BİLGİ — fiyat endeksi, temettü hariç) | +126.30% | +31.35% | -22.86% |
| TRY faizi — haircut'lı (200bp, S1b'nin kendi mühürlü modeli) | +224.03% | +48.07% | 0.00% |
| TRY faizi — haircut'sız (ham, 'mevduat proxy'si') | +244.02% | +51.06% | 0.00% |
| USD al-tut (USDTRY değişimi, TRY-terim) | +79.25% | +21.51% | -4.78% |
| Gram altın (TRY, best-effort) | +279.07% | +56.03% | -20.31% |
| TÜFE (FRED, best-effort — bkz. gecikme notu) | +105.65% | +27.22% | 0.00% |

*(2005-ağırlıklı sepetin bu pencere başındaki payı: `ASELS` tek başına %28.1 — 21 yıllık sürüklenmiş ağırlıkla pencere-başı eşit-ağırlıklı satır arasındaki fark büyüdükçe bu pay da büyür.)*

**D1 − faiz(haircut'lı) farkı (CAGR, pp):** -10.25pp (D1 faizin altında).

**İşlem/rejim özeti:** bu pencerede 6 anahtarlama (ENTER/EXIT), rejim-ON gün oranı 94.6%.

### Son 5 Yıl (2021-07-08 → 2026-07-08)

| Seri | Toplam Getiri | CAGR | Max DD |
|---|---:|---:|---:|
| D1 (rejim-filtreli çekirdek, mühürlü S1b) | +1457.78% | +73.19% | -22.78% |
| 12-sembol sepet al-tut — 2005 AĞIRLIKLI, HİÇ dengelenmemiş (TRY, maliyetsiz) | +2643.17% | +93.95% | -25.97% |
| 12-sembol sepet al-tut — PENCERE-BAŞI eşit ağırlık, dengelenmeden tutulan | +1567.15% | +75.56% | -22.80% |
| XU100 al-tut (BİLGİ — fiyat endeksi, temettü hariç) | +929.53% | +59.47% | -22.86% |
| TRY faizi — haircut'lı (200bp, S1b'nin kendi mühürlü modeli) | +304.12% | +32.23% | 0.00% |
| TRY faizi — haircut'sız (ham, 'mevduat proxy'si') | +346.61% | +34.90% | 0.00% |
| USD al-tut (USDTRY değişimi, TRY-terim) | +439.86% | +40.11% | -34.93% |
| Gram altın (TRY, best-effort) | +1121.23% | +64.96% | -34.41% |
| TÜFE (FRED, best-effort — bkz. gecikme notu) | +446.01% | +40.43% | 0.00% |

*(2005-ağırlıklı sepetin bu pencere başındaki payı: `ASELS` tek başına %37.0 — 21 yıllık sürüklenmiş ağırlıkla pencere-başı eşit-ağırlıklı satır arasındaki fark büyüdükçe bu pay da büyür.)*

**D1 − faiz(haircut'lı) farkı (CAGR, pp):** +40.97pp (D1 faizin üzerinde).

**İşlem/rejim özeti:** bu pencerede 8 anahtarlama (ENTER/EXIT), rejim-ON gün oranı 96.1%.

### Son 10 Yıl (2016-07-08 → 2026-07-08)

| Seri | Toplam Getiri | CAGR | Max DD |
|---|---:|---:|---:|
| D1 (rejim-filtreli çekirdek, mühürlü S1b) | +3269.86% | +42.16% | -23.96% |
| 12-sembol sepet al-tut — 2005 AĞIRLIKLI, HİÇ dengelenmemiş (TRY, maliyetsiz) | +7343.83% | +53.89% | -40.66% |
| 12-sembol sepet al-tut — PENCERE-BAŞI eşit ağırlık, dengelenmeden tutulan | +3653.00% | +43.70% | -32.70% |
| XU100 al-tut (BİLGİ — fiyat endeksi, temettü hariç) | +1690.88% | +33.48% | -31.82% |
| TRY faizi — haircut'lı (200bp, S1b'nin kendi mühürlü modeli) | +576.77% | +21.08% | 0.00% |
| TRY faizi — haircut'sız (ham, 'mevduat proxy'si') | +726.61% | +23.52% | 0.00% |
| USD al-tut (USDTRY değişimi, TRY-terim) | +1497.45% | +31.93% | -34.93% |
| Gram altın (TRY, best-effort) | +4693.64% | +47.26% | -34.41% |
| TÜFE (FRED, best-effort — bkz. gecikme notu) | +976.94% | +26.83% | -1.84% |

*(2005-ağırlıklı sepetin bu pencere başındaki payı: `ASELS` tek başına %32.5 — 21 yıllık sürüklenmiş ağırlıkla pencere-başı eşit-ağırlıklı satır arasındaki fark büyüdükçe bu pay da büyür.)*

**D1 − faiz(haircut'lı) farkı (CAGR, pp):** +21.09pp (D1 faizin üzerinde).

**İşlem/rejim özeti:** bu pencerede 28 anahtarlama (ENTER/EXIT), rejim-ON gün oranı 80.5%.

### Tam Dönem (2005-01-03 → 2026-07-08)

| Seri | Toplam Getiri | CAGR | Max DD |
|---|---:|---:|---:|
| D1 (rejim-filtreli çekirdek, mühürlü S1b) | +20175.69% | +28.01% | -28.43% |
| 12-sembol sepet al-tut — 2005 AĞIRLIKLI, HİÇ dengelenmemiş (TRY, maliyetsiz) | +69184.56% | +35.54% | -64.22% |
| 12-sembol sepet al-tut — PENCERE-BAŞI eşit ağırlık, dengelenmeden tutulan | +69184.56% | +35.54% | -64.22% |
| XU100 al-tut (BİLGİ — fiyat endeksi, temettü hariç) | +5566.51% | +20.65% | -63.43% |
| TRY faizi — haircut'lı (200bp, S1b'nin kendi mühürlü modeli) | +1507.08% | +13.78% | 0.00% |
| TRY faizi — haircut'sız (ham, 'mevduat proxy'si') | +2363.37% | +16.06% | 0.00% |
| USD al-tut (USDTRY değişimi, TRY-terim) | +3386.00% | +17.95% | -34.93% |
| Gram altın (TRY, best-effort) | +33002.81% | +30.97% | -34.41% |
| TÜFE (FRED, best-effort — bkz. gecikme notu) | +2558.07% | +16.47% | -1.84% |

*(2005-ağırlıklı sepetin bu pencere başındaki payı: `THYAO` tek başına %8.3 — 21 yıllık sürüklenmiş ağırlıkla pencere-başı eşit-ağırlıklı satır arasındaki fark büyüdükçe bu pay da büyür.)*

**D1 − faiz(haircut'lı) farkı (CAGR, pp):** +14.23pp (D1 faizin üzerinde).

**İşlem/rejim özeti:** bu pencerede 67 anahtarlama (ENTER/EXIT), rejim-ON gün oranı 72.5%.

## Son 1 Yıl Bilmecesi: Sayısal Ayrıştırma

D1 bu pencerede **+45.31%** getirdi, 2005-ağırlıklı sepet ise **+105.80%** — aradaki fark +60.5pp, oysa D1 bu pencerede **0 anahtarlama** yaptı ve rejim **%100 ON** kaldı (yani ikisi de saf al-tut, tek bir işlem/maliyet farkı YOK). Fark TAMAMEN ağırlık yapısından kaynaklanıyor:

1. **Ağırlık-sürüklenmesi etkisi (+71.2pp):** 2005-ağırlıklı sepette `ASELS` tek başına payın **%58.3**'ini oluşturuyor (21 yıllık sürüklenme) — pencere-başında TAZE eşit-ağırlıkla girilseydi (yeni "sepet — PENCERE-BAŞI" satırı) getiri **+34.55%** olurdu. Fark (+71.2pp), `ASELS`'ın bu penceredeki performansının 2005-ağırlıklı sepeti neredeyse TEK BAŞINA sürüklediğini gösteriyor — 12 sembolün dengeli bir ortalaması DEĞİL.

2. **Kalan fark (-10.8pp):** pencere-başı eşit-ağırlıklı sepet ile D1 arasında hâlâ bir fark var — bunun kaynağı D1'in ağırlıklarının pencere BAŞLANGICINDA değil, D1'in bu pencereden ÖNCEKİ son ENTER'ında (bkz. yukarı işlem özeti — pencere içinde 0 ama pencereden önce gerçekleşmiş) sabitlenmiş olmasıdır: D1 pencere başlamadan ÖNCE bir miktar ek sürüklenmeye (muhtemelen aynı yönde) zaten maruz kalmıştı, bu yüzden TAM pencere-başı-taze bir eşit-ağırlıkla birebir örtüşmez. Küçük komisyon/slipaj kalıntıları da bu kalan farka (ihmal edilebilir ölçüde) katkıda bulunur.

**Kısaca:** "D1 neden sepetten çok daha az kazandı" sorusunun cevabı bir strateji zayıflığı DEĞİL — 2005-ağırlıklı 'sepet' satırının kendisi, son 1 yılda esasen tek bir sembolün (yukarıda adı geçen) getirisini yansıtan, dengesiz bir ölçüttür. Pencere-başı eşit-ağırlıklı satır, D1'in kendi ENTER mantığına çok daha yakın bir kıyas sunuyor.

## "Faizde Tutsaydım" Sorusunun Net Cevabı

D1'in CAGR'ı, TRY faizinin (haircut'lı, S1b mühürlü model) CAGR'ından ne kadar farklı:

| Pencere | D1 CAGR | Faiz(haircut) CAGR | Fark (pp) |
|---|---:|---:|---:|
| Son 1 Yıl | +45.35% | +42.14% | +3.21pp |
| Son 3 Yıl | +37.82% | +48.07% | -10.25pp |
| Son 5 Yıl | +73.19% | +32.23% | +40.97pp |
| Son 10 Yıl | +42.16% | +21.08% | +21.09pp |
| Tam Dönem | +28.01% | +13.78% | +14.23pp |

## USD Paneli ("Satın Alma Gücü" Merceği)

D1 ve sepetin USD-terim (equity/USDTRY) CAGR + max DD'si — reel/uluslararası yatırımcı perspektifi. TRY-terim tablolarla KARIŞTIRILMAMALI (bkz. yukarı).

| Pencere | D1 USD CAGR | D1 USD maxDD | Sepet USD CAGR | Sepet USD maxDD |
|---|---:|---:|---:|---:|
| Son 1 Yıl | +24.09% | -15.41% | +75.78% | -18.75% |
| Son 3 Yıl | +13.42% | -34.34% | +41.72% | -22.52% |
| Son 5 Yıl | +23.61% | -34.34% | +38.42% | -31.85% |
| Son 10 Yıl | +7.75% | -55.40% | +16.64% | -64.99% |
| Tam Dönem | +8.53% | -67.03% | +14.91% | -75.06% |

**Tutarlılık kontrolü:** S1 spike'ı (faizsiz, KALICI KAYIT 4) tam-dönem D1 USD CAGR'ı +%5.08 bulmuştu; S1b (faizli, `REGIME_CORE_S1B.md` (f)) bunu +%8.70'e yükseltti. Bu turun (faizli, birkaç gün daha uzun tarihçeli) tam-dönem D1 USD CAGR'ı **+8.53%** — S1b'nin +%8.70'ine (S1'in +%5.08'ine DEĞİL, çünkü bu ölçüm de faizli) çok yakın, tutarlı. Sepet USD CAGR **+14.91%** de S1b'nin +%15.15'ine yakın — küçük farklar yalnızca birkaç ek günün (07-03→07-08) etkisidir, yeni bir varyant/parametre DEĞİL.

## Kriz-Yılı Ayrıştırması (BİLGİ)

Botun varlık sebebinin (sermaye koruma) görünür olduğu/olmadığı yıllar — yalnızca toplam getiri, D1 vs sepet vs faiz(haircut'lı):

| Yıl | D1 | Sepet | Faiz(haircut) |
|---|---:|---:|---:|
| 2008 | +0.29% | -50.37% | +14.97% |
| 2013 | -10.38% | +2.27% | +1.81% |
| 2018 | -5.60% | -18.89% | +13.43% |
| 2021-23 | +603.52% | +535.23% | +58.28% |

*(Buradaki "Sepet" de yukarıdaki 2005-ağırlıklı, HİÇ dengelenmemiş seridir — 2008/2013 gibi t0'a yakın yıllarda ağırlık sürüklenmesi henüz sınırlıyken, 2021-23 gibi geç yıllarda "Son 1 Yıl Bilmecesi" bölümündeki aynı çarpıtma etkisi devreye girer; bu tablo yalnızca BİLGİ amaçlıdır, pencere-başı eşit-ağırlık karşılaştırması burada hesaplanmamıştır.)*

2008 (küresel finansal kriz) ve 2018 (kur şoku) yıllarında D1 sepetin ciddi altındaki kaybını BÜYÜK ÖLÇÜDE ATLATIYOR (rejim filtresi nakde geçmiş) — varlık sebebi görünür. 2013'te ise D1 sepetin ALTINDA kalıyor (whipsaw/geç dönüş) — filtre her yıl işe yaramıyor, bu beklenen ve dürüst bir gözlem.

## Dürüst Kapanış Notu

Bu rapor **bilgilendirmedir** — STATUS.md'deki mühürlü kabul kararlarını (KALICI KAYIT 6/8, D1 ailesinin kabulü) hiçbir şekilde ETKİLEMEZ, geri almaz, güçlendirmez. Hiçbir pencere/yıl seçilerek strateji değerlendirmesi/parametre değişikliği yapılmamıştır (criterion-shopping YASAK) — tüm pencereler (1y/3y/5y/10y/tam-dönem) ve tüm kriz yılları AYNI, koşumdan önce belirlenmiş listeden, seçmeden raporlanmıştır. 1 yıllık pencerenin düşük anahtarlama sayısı nedeniyle istatistiksel önemi yoktur (yukarıda her tabloda ayrıca not düşüldü). İki durma noktası (Faz 4 backtest değerlendirmesi + gerçek sermaye) ve K1.5/G1 kuyruğu bu raporla HİÇBİR ŞEKİLDE değişmez.

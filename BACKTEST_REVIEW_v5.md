# Backtest Değerlendirme Raporu — v5 (veri genişletme: 3 → 12 sembol)

Tarih / commit: 2026-07-06, commit `dc56ed2` (12 sembol evreni + altyapı, strateji/eşik DEĞİŞMEDİ)
Komut: `python -m backtest.cli --symbols THYAO,GARAN,ASELS,AKBNK,KCHOL,SAHOL,EREGL,TUPRS,TCELL,TOASO,SISE,ARCLK --config config/config.yaml --start-date 2005-01-01 --walk-forward --monte-carlo --regime-split --sweep --benchmark --out runtime/backtest_reports_v5/`
Veri aralığı: 2005-01-02 → 2026-07-02 (~21.5 yıl — bkz. Adım 2'deki veri kalitesi
notu), degrade mod (h4_df=None). adx_min=25 dahil tüm eşikler v4'teki gibi
**değişmeden** kaldı. Bu bir örneklem büyütme turu, parametre revizyonu değil.
Koşum süresi: ~2 saat 20 dakika (12 sembol × tam süit).

## Adım 1 — Sembol Seçimi ve Gerekçe

**Seçim kriteri (geçmiş getiriye göre DEĞİL):**
1. **Tarihçe uzunluğu**: en az 2005'ten beri kesintisiz işlem görüyor olmak.
2. **Likidite**: BIST30/BIST100'ün en işlem gören, kurumsal hacimli hisseleri
   arasından (günlük ortalama hacim milyonlarca lot).
3. **Sektör çeşitliliği**: tek bir sektöre (özellikle bankacılığa, BIST hacminin
   ağırlıklı kısmını oluşturduğu için) aşırı yoğunlaşmamak.

**Seçilen 12 sembol:**

| Sembol | Sektör |
|---|---|
| THYAO | Havayolu/Ulaştırma |
| GARAN | Bankacılık |
| ASELS | Savunma/Teknoloji |
| AKBNK | Bankacılık |
| KCHOL | Holding |
| SAHOL | Holding |
| EREGL | Demir-Çelik |
| TUPRS | Enerji/Rafineri |
| TCELL | Telekom |
| TOASO | Otomotiv |
| SISE | Cam/Sanayi |
| ARCLK | Dayanıklı Tüketim |

Bankacılık iki kez temsil ediliyor (GARAN, AKBNK) çünkü BIST'in en likit iki
hissesi bunlar — tamamen dışlamak likidite kriteriyle çelişirdi; geri kalan
10 sembol 8 farklı sektöre yayılıyor.

**⚠️ Survivorship bias — dürüstlük notu:** Bu 12 sembol, bugün hâlâ işlem gören,
BIST'te tutunmuş şirketlerden seçildi. 2005'ten bu yana borsadan çıkan, iflas
eden veya küçülüp önemsizleşen şirketler evrene dahil edilmedi (çünkü böyle bir
liste tutmuyoruz ve bu MVP'nin kapsamı dışında). Bu, sonuçları **hafif iyimser**
gösterebilir — gerçek zamanlı bir yatırımcı 2005'te bugün hayatta olacak
şirketleri önceden bilemezdi. Bu önyargı hem stratejinin hem de aşağıdaki
XU100 benchmark'ının sonuçlarını aynı yönde etkiler (endeks de hayatta kalan
şirketlerden oluşur), yani stratejiyle-endeks karşılaştırması bu açıdan adil
kalır — ama her iki sayı da mutlak anlamda biraz iyimser olabilir.

## Adım 2 — Veri: Beklenmedik ama Önemli Bir Bulgu

**Sembol değişikliği gerekmedi — ama bir kod bug'ı bulundu ve düzeltildi.**

İlk kalite taramasında 12 sembolün **11'i** `check_quality()`'den FAIL aldı.
Araştırma şunu ortaya çıkardı: (1) `data/quality.py`'nin OHLC tutarlılık
kontrolü **kayan nokta epsilon gürültüsünü** (`high`'ın `close`'a "1e-16 kadar
küçük" çıkması gibi, `auto_adjust`'ın temettü/split düzeltme matematiğinden
kaynaklanan) gerçek bir veri sorunuyla karıştırıyordu — bu, gerçek bir strateji/
eşik hatası değil, veri-doğrulama kodundaki bir toleranssızlık bug'ıydı; küçük
bir rtol/atol toleransıyla düzeltildi (bkz. commit `dc56ed2`). (2) Ayrıca 7
sembolün 2000-2004 arası verisinde **gerçek** bir bozukluk vardı — yfinance'in
`auto_adjust` hesaplaması bu dönemde bazı sembollerde **negatif fiyatlar**
üretiyordu (muhtemelen 2005 TL reformu öncesi aşırı büyük nominal değerlerin
geriye dönük düzeltme matematiğini bozması).

**Çözüm — sembol değişikliği değil, tarih aralığı kırpması:** Kullanıcının
kendi seçim kriteri zaten "en az 2005'ten beri" idi. Veri, `--start-date
2005-01-01` ile kırpıldığında **12 sembolün tamamı** temiz geçti — hiçbirini
değiştirmek gerekmedi:

```
THYAO PASS  n=5511  GARAN PASS  n=5511  ASELS PASS  n=5511  AKBNK PASS  n=5511
KCHOL PASS  n=5511  SAHOL PASS  n=5511  EREGL PASS  n=5512  TUPRS PASS  n=5511
TCELL PASS  n=5511  TOASO PASS  n=5511  SISE  PASS  n=5511  ARCLK PASS  n=5511
```

Bu nedenle backtest'in etkili veri aralığı **2005-01-02 → 2026-07-02** (~21.5
yıl), v1-v4'ün 2000-2026 (~26 yıl) aralığından daha kısa. Bu, aşağıdaki
karşılaştırmalarda akılda tutulmalı — v5, v4'ten hem daha fazla sembol hem
daha kısa dönem kullanıyor.

## Adım 3 — Tam Süit Sonuçları

## v4 → v5 Yan Yana Karşılaştırma

| Metrik | v4 (3 sembol, 2000-2026) | v5 (12 sembol, 2005-2026) | Yön |
|---|---|---|---|
| Trade sayısı (tüm dönem) | 47 | **125** | ↑ |
| Toplam getiri | 4.68% | **-1.06%** | ↓↓ |
| Profit factor | 1.48 | **0.97** | ↓↓ (artık <1) |
| Win rate | 46.81% | **42.40%** | ↓ |
| Maks. drawdown (tüm dönem) | -2.71% | **-20.74%** | ↓↓↓ (7.7× kötüleşti) |
| Sharpe | 0.20 | **0.01** | ↓↓ |
| **OOS profit factor (walk-forward)** | 1.13 | **0.75** | ↓↓ (artık <1) |
| **OOS max DD (walk-forward)** | -6.37% | **-19.90%** | ↓↓↓ |
| Ortalama in-sample max DD | 0.75% | 2.24% | ↓ |
| **DD kriteri sonucu (resmi)** | GEÇMEDİ (yalnız DD tarafı) | GEÇMEDİ (**hem PF hem DD tarafı**) | ↓ |
| Bilgilendirici oran: OOS DD / tam-dönem DD | 2.35× | **0.96×** | (yakınsadı — bkz. yorum) |

**Bilgilendirici oranın yorumu:** v4'te OOS drawdown, tam-dönem (tek geçiş)
drawdown'un 2.35 katıydı — yani tek bir backtest çalıştırıp bakmak yanıltıcı
derecede iyimser bir tablo veriyordu. v5'te bu oran 0.96×'a düştü — yani artık
tam-dönem backtest'in kendisi ZATEN OOS'un gösterdiği kadar kötü görünüyor.
Bu "iyileşme" değil: iki ölçüm birbirine yakınsadı çünkü **her ikisi de kötü**,
tek geçişlik görünüm artık gerçeği daha az saklıyor.

## Sembol Bazında Trade Dağılımı

| Sembol | Trade Sayısı | Toplam PnL (TL) |
|---|---|---|
| TCELL | 16 | -614.39 |
| TOASO | 15 | +2,521.45 |
| THYAO | 12 | +1,779.88 |
| TUPRS | 11 | -801.98 |
| EREGL | 11 | -2,930.12 |
| ASELS | 11 | +2,875.55 |
| ARCLK | 11 | +2,102.46 |
| SISE | 11 | -3,541.97 |
| KCHOL | 9 | -745.63 |
| SAHOL | 8 | -42.42 |
| GARAN | 5 | +517.22 |
| AKBNK | 5 | -2,179.92 |

**Trade'ler birkaç sembole yoğunlaşmıyor — makul biçimde dağılıyor** (min 5,
maks 16, 12 sembolün hepsi en az 1 trade üretti). PnL tarafında ise net bir
kutuplaşma var: 5 sembol net kârlı (ASELS, TOASO, ARCLK, THYAO, GARAN — toplam
~+9,796 TL), 7 sembol net zararlı (SISE, EREGL, AKBNK, TUPRS, KCHOL, TCELL,
SAHOL — toplam ~-10,856 TL). Kaybedenlerin sayısı ve toplamı kazananları
hafifçe aşıyor, bu da toplam -1.06% getiriyi açıklıyor. Tek bir "kötü sembol"
sorumlu değil — kayıp 7 sembole dağılmış durumda; en büyük tekil kayıp
(SISE, -3,542 TL) toplam kaybın yalnızca ~%33'ü.

## OOS Trade Sayısı ve Pencere Kapsaması

| | v4 (3 sembol) | v5 (12 sembol) |
|---|---|---|
| Pencere sayısı | 48 | 38 (daha kısa dönem nedeniyle) |
| Trade üreten pencere | 23 (%47.9) | **28 (%73.7)** |
| Toplam OOS trade | 54 | **201** (3.7× artış) |
| Robust pencere sayısı | 23 | 16 |

**OOS örneklem büyüklüğü belirgin iyileşti** — 54'ten 201'e, pencere kapsaması
da %48'den %74'e çıktı. Bu, walk-forward'ın artık çok daha az "boş" pencereyle
çalıştığı, istatistiksel olarak daha güvenilir bir OOS ölçümü olduğu anlamına
geliyor. Ama daha güvenilir ölçüm **daha kötü bir sonuç** gösteriyor (OOS
PF 0.75, önceki 1.13'ten düşük) — az veriyle "iyi görünen" sonuç, çok veriyle
düzeldi.

## Rejim Kırılımı — Bull Yoğunluğu 12 Sembolle Değişiyor mu?

| Rejim | v4 (3 sembol) | v5 (12 sembol) |
|---|---|---|
| bull | 42/47 (%89.4) | **116/125 (%92.8)** |
| bear | 1/47 (%2.1) | 2/125 (%1.6) |
| sideways | 4/47 (%8.5) | 7/125 (%5.6) |

**Bull yoğunluğu azalmadı, tersine hafif arttı** (%89.4 → %92.8). 12 sembole
çıkmak, rejim-bağımlılığı sorununu çözmedi — beklenebilirdi, çünkü BIST
hisselerinin çoğu aynı makro döngüye (TL faiz/enflasyon rejimi, küresel risk
iştahı) tabi, sembol çeşitliliği rejim çeşitliliği garantilemiyor. Bear
rejiminde hâlâ neredeyse hiç veri yok (2 trade / 125).

## Benchmark Kıyası — "Bu bot, endeksi almaktan daha mı iyi?"

| | Strateji | XU100 Al-Tut | Sadece Nakit |
|---|---|---|---|
| Toplam getiri | -1.06% | **3,523.45%** | 0.00% |
| CAGR | -0.05% | **19.14%** | 0.00% |
| Maks. drawdown | -20.74% | -63.43% | 0.00% |
| Sharpe | 0.01 | **0.80** | 0.00 |

**İlk somut cevap: hayır, açık ara değil.** XU100'ü alıp 21.5 yıl elde tutmak,
stratejiden (ve nakitte kalmaktan) çok daha iyi bir sonuç veriyor — hem getiri
hem risk-ayarlı getiri (Sharpe) açısından. Strateji, endeksin yaşadığı büyük
drawdown'dan (-63.43%) kaçınıyor (kendi -20.74%'ü ile), yani "aşağı yönlü
koruma" felsefesi bir dereceye kadar işliyor — ama bunun bedeli, endeksin
devasa yukarı yönlü hareketinin neredeyse tamamını kaçırmak.

**Nominal getiri notu:** XU100'ün %3,523 toplam getirisi **nominal TL**
cinsindendir — Türkiye'nin bu dönemdeki yüksek enflasyonu düşülmemiştir.
Stratejinin getirisi de aynı nominal TL cinsinden olduğundan, ikisi arasındaki
karşılaştırma (strateji vs. endeks) adil ve geçerlidir; ama CAGR rakamlarının
(%19.14 endeks, -%0.05 strateji) "reel" satın alma gücü kazancı olarak
okunmaması gerekir.

## YENİ Bulgular (bu turun kapsamı dışında, düzeltilmedi — yalnızca tespit edildi)

Bu üç bulgu, 12-sembol/2005+ verisiyle daha görünür hale geldi ama bugünkü
görevin kapsamında (veri genişletme, eşik değişikliği yok) DÜZELTİLMEDİ:

1. **Backtest motoru, drawdown breaker'ı hiç tetiklemiyor.**
   `risk/risk_engine.py`'deki `check_and_trip_breaker()` fonksiyonu
   `backtest/engine.py`'nin event loop'unda **hiçbir yerde çağrılmıyor** —
   yalnızca `breaker_tripped()` (dosya var mı kontrolü) okunuyor, ama dosyayı
   YAZAN fonksiyon hiç invoke edilmiyor. Sonuç: backtest'te equity, config'in
   `max_drawdown_breaker_pct=%10` eşiğini fiilen aşabiliyor (nitekim bu raporda
   -%20.74'e kadar gitti) — halbuki paper/real modda (Faz 5) breaker tetiklenip
   yeni girişleri durdurmuş olurdu. Bu, raporlanan drawdown rakamlarının
   **canlı/paper moddaki gerçek üst sınırdan daha kötü** görünebileceği
   anlamına gelir (breaker devrede olsaydı muhtemelen daha erken durdurup daha
   sığ kalırdı) — ama aynı zamanda breaker'ın olmadığı bu "sınırsız" senaryo,
   stratejinin ÇIPLAK risk profilini de dürüstçe gösteriyor.

2. **Monte Carlo kırmızı bayrak kontrolü, muhtemelen yanlış persentili
   kontrol ediyor.** `cli.py`'nin kırmızı bayrak mantığı `dd_p95`'i (istatistiksel
   olarak EN HAFİF senaryo, çünkü değerler negatif ve p95 sıfıra en yakın olanı
   seçiyor) breaker eşiğiyle karşılaştırıyor — CLAUDE.md'nin kendi metni de
   aynı ismi ("dd_p95, breaker eşiğine yakın/aşkın mı?") kullanıyor, ama
   bu isimlendirme "en kötü %5'lik senaryo" ile "en iyi %5'lik senaryo"
   arasında olası bir kavram karışıklığı taşıyor. Bu raporda: `dd_p95=-%5.65`
   (breaker eşiğinin altında, bayrak TETİKLENMEDİ) ama `dd_p5=-%11.71`
   (breaker eşiğinin **üstünde**) — yani "en kötü %5 senaryo" ölçütüyle
   bakılsaydı bu rapor bir MC kırmızı bayrağı üretecekti. Hangi persentilin
   doğru risk ölçütü olduğu netleştirilmeli (muhtemelen `dd_p5`, tail-risk
   sorusu "en kötü ne olur" içindir).

3. **adx_min=25 sıkılaştırması (v4'te 3 sembolle onaylanmıştı), 12-sembol
   sweep verisinde desteklenmiyor.** `sweep_results.csv`'de `adx_min=15`
   (en gevşek) kombinasyonları, `adx_min=25`'ten daha İYİ profit factor
   (1.06-1.15 vs 0.97-1.05) ve çok daha fazla trade (400+ vs 125) gösteriyor
   — büyük mutlak drawdown pahasına (%19-26 aralığında, tüm kombinasyonlarda
   benzer şekilde yüksek). v4'ün 3-sembollük örneklemine dayanan sıkılaştırma
   kararı, daha geniş örneklemde aynı yönde doğrulanmıyor. Bu, gelecekteki bir
   karar noktası için not edildi — bu turda **hiçbir eşik değiştirilmedi.**

## KIRMIZI BAYRAKLAR

- [x] **Walk-forward kabul kriteri geçmedi** — v4'ten farklı olarak artık HEM
      profit factor (0.75<1.1) HEM drawdown kriteri başarısız. v4'te yalnızca
      DD tarafı başarısızdı.
- [x] **Trade sayısı 30'un altına düştü mü?** HAYIR, tam tersi — 125 (v4'ün
      47'sinden çok daha fazla). Ayrı kırmızı bayrak tetiklenmedi.
- [x] **Performans tek rejime yoğun** — bull %92.8, v4'ten (%89.4) daha da
      yoğunlaşmış durumda.
- [ ] **4H degrade dönem karşılaştırması N/A** (v1'den taşındı, değişmedi).
- [x] **YENİ: Maks. drawdown (-%20.74), breaker eşiğinin (%10) 2 katından
      fazla** — backtest'in breaker'ı hiç uygulamaması nedeniyle (yukarıda
      detaylı).
- [x] **YENİ: Monte Carlo dd_p5 (-%11.71), breaker eşiğini (%10) aşıyor**
      (mevcut otomatik kontrol dd_p95'e bakıyor ve bunu kaçırıyor — yukarıda
      detaylı).

## Benim (Claude Code) değerlendirmem

Bu, dört raporun en açık sonucu: **12 sembole ve daha geniş (ama daha kısa)
bir döneme çıkmak, stratejinin gerçek profilini ortaya çıkardı — ve bu profil
v3/v4'ün 3-sembollük görünümünden çok daha zayıf.** OOS profit factor artık
1'in altında (0.75), OOS drawdown %19.9'a fırladı, ve walk-forward'ın kabul
kriteri artık her iki koşulda da (PF ve DD) başarısız — v4'te yalnızca DD
tarafı başarısızdı. Trade örneklemi büyüdükçe (54→201 OOS trade) sonuç
"iyi görünmekten" "kötü görünmeye" döndü; bu, örneklem büyütmenin tam olarak
yapması gereken şeyi yaptığının kanıtı — küçük örneklemdeki iyimser görünüm,
büyük örneklemde tutmadı.

Benchmark kıyası da net: aynı dönemde XU100'ü alıp beklemek, stratejiden hem
mutlak hem risk-ayarlı getiri açısından çok daha iyi bir sonuç veriyor.
Stratejinin tek gerçek avantajı, endeksin yaşadığı çok daha büyük drawdown'dan
(-63% vs -21%) kaçınması — ama bu "aşağı yönlü koruma", getiriden feragat
etme bedeliyle geliyor ve nakitte kalmaktan (0% getiri, 0% risk) bile daha
iyi değil.

Üç ek bulgu (breaker'ın backtest'te hiç tetiklenmemesi, MC kırmızı bayrağının
muhtemelen yanlış persentili kontrol etmesi, adx_min sıkılaştırmasının geniş
örneklemde tutmaması) bu turun kapsamı dışında bırakıldı ama hepsi gelecekteki
kararlar için önemli girdi.

**Karar benim değil, kullanıcının.** Backtest v5 tamamlandı, BACKTEST_REVIEW_v5.md
hazır. Faz 5'e geçmiyorum, kullanıcı onayı bekliyorum.

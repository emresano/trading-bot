# S1b — Rejim-Çekirdek Ölçüm Tamamlama Turu (nakit-getiri düzeltmesi)

REGIME_CORE_S1.md'nin (D1 tasarımının ilk spike'ı) nakit-getiri düzeltmesi
eklenmiş TEKRARI. **Tek davranış değişikliği**: rejim KAPALI (tamamen
nakitte) günlerde nakit artık TRY gecelik/politika faizi tahakkuk ediyor
(200bp muhafazakâr kırpmayla). N=200, b=%1, M=3 ve maliyetler **AYNEN**
mühürlü kaldı, hiçbir eşik değişmedi.

**Bağımsızlık kanıtı**: `git diff backtest/engine.py strategy/ risk/
config/config.yaml data/snapshots/2026-07-06 data/snapshots/us
data/snapshots/fx` BOŞ — yalnızca bağımsız spike yığını (`backtest/regime_core.py`,
`tools/run_regime_core.py`, `config/regime_core.yaml`) ve yeni bir aux
snapshot değişti.

## Madde 1 — TRY Gecelik Faiz Kaynağı

`data/snapshots/aux/2026-07-07/TRY_ON_RATE.parquet` (manifest+SHA256'lı).

**Kaynak merdiveni**:
- (a) TCMB EVDS API: **denenmedi/başarısız** — `secrets.env` yok, API
  anahtarı bulunamadı.
- (b) TCMB'nin herkese açık statik indirmesi: **başarısız** —
  `evds2.tcmb.gov.tr`'ye programatik erişim 302 (login) yönlendirmesi
  döndürdü, basit HTTP GET ile ayrıştırılabilir bir statik dosya bulunamadı.
- (c) **KULLANILAN**: FRED (St. Louis Fed) üzerinden OECD MEI verisi —
  `IRSTCI01TRM156N`, *"Interest Rates: Immediate Rates (< 24 Hours): Call
  Money/Interbank Rate: Total for Turkey"*. Herkese açık, kimlik
  doğrulamasız CSV. **TCMB'nin KENDİ sitesi DEĞİL** ama TCMB'nin gecelik/
  bankalar arası faiz verisini yansıtan, OECD'nin topladığı saygın bir
  üçüncü-taraf kaynak — hiçbir veri UYDURULMADI.

**Kapsam**: 2005-01 → 2026-03, aylık (255 satır). **Kalite**: 0 negatif/
sıfır değer, 0 yinelenen tarih, **9 ay boşluk** (2023-02→06 ve 2023-09→12 —
muhtemelen Şubat 2023 depremi sonrası OECD veri toplama aksaması; bu, TAM
DE CBRT'nin 2023 ortası sert faiz artırım döngüsünün başladığı döneme denk
geliyor — forward-fill bu dönemde GERÇEK tahakkuku muhtemelen HAFİFE
ALIYOR). Aylık seri, kullanım noktasında (regime_core) günlük takvime
forward-fill edilir; snapshot HAM (aylık) veriyi tutar.

## Madde 2 — Nakit Getirisi Mekaniği

`r_net = max(faiz − 200bp, 0)`, ACT/365, `cash *= (1+r_net/365)^gün_farkı`.
Tahakkuk, o günün transition'ı uygulanmadan ÖNCEKİ `in_position` durumuna
göre kararlaştırılır — ENTER gününü DAHİL eder (kapanışa kadar nakitti),
EXIT gününün KENDİSİNİ HARİÇ tutar (kapanışa kadar hisse pozisyonundaydı).

**Zorunlu regresyon kanıtı** (`tests/test_regime_core.py`):
- `cash_rate=None` (varsayılan) → S1 ile **bayt-bayt aynı** equity_curve/switches.
- `cash_rate=<tümü sıfır Series>` → S1 ile **bayt-bayt aynı** (mekanizmanın
  matematiksel olarak etkisiz olduğunun kanıtı: r_net=0 → cash×1.0).
- CLI seviyesinde de doğrulandı: `python -m tools.run_regime_core` (bayrak
  yok) çalıştırıldı, `runtime/regime_core_s1/` çıktıları önceki S1
  koşumuyla karşılaştırıldı — yalnızca yeni eklenen `cash_only_with_yield:
  null` alanı dışında **tüm dosyalar bayt-bayt aynı**.
- 22 yeni birim testi: sabit-faiz ACT/365 matematiği, 200bp kırpma altı
  sıfırlanma, takvim-günü (hafta sonu atlaması dahil) formülü, pozisyon
  günlerinde/EXIT gününde tahakkuk yokluğu, determinizm — hepsi yeşil.

## (a) Ana Koşum — Özet Metrikler

| Metrik | S1 (faizsiz) | **S1b (faizli)** |
|---|---|---|
| Toplam getiri (TRY) | +9,978% | **+20,787%** |
| CAGR (TRY) | %23.94 | **%28.21** |
| Maks. drawdown | -%33.50 | **-%28.43** |
| Sharpe | 1.064 | **1.215** |
| Anahtarlama sayısı | 67 | 67 (**AYNI** — cash yield sinyal zamanlamasını etkilemiyor) |

## (b) Üç Benchmark — S1 ile AYNEN Karşılaştırma

| Metrik | Strateji (S1b) | XU100 al-tut | 12-sembol sepeti al-tut | Sadece nakit (%0) | **Sadece nakit, FAİZLİ (bilgi)** |
|---|---|---|---|---|---|
| Toplam getiri | +20,787% | +5,658% | +72,074% | 0% | **+1,500%** |
| CAGR | %28.21 | %20.76 | %35.83 | %0 | **%13.77** |
| Maks. drawdown | -%28.43 | -%63.43 | -%64.22 | %0 | 0% (monoton artan) |
| Sharpe | 1.215 | 0.851 | 1.184 | 0.0 | 12.5 (anlamsız — deterministik/monoton eğri) |

**Doğrulama**: XU100 al-tut ve 12-sembol sepeti al-tut satırları S1 ile
**BİREBİR AYNI** (nakit modeli onlara değmiyor — yalnızca stratejinin KENDİ
nakit tutma dönemlerini etkiliyor). "Sadece nakit, faizli" satırı yalnızca
bilgilendirici — %13.77 CAGR, 2005-2026 arası TRY'nin YÜKSEK nominal faiz
ortamını yansıtıyor (200bp kırpmadan sonra bile). Sharpe'ı (12.5) ANLAMSIZ
kabul edilmeli — eğri tamamen deterministik/monoton olduğundan risk-ayarlı
getiri kavramı burada uygulanamaz.

## (c) Drawdown Epizotları — Topoloji DEĞİŞTİ

**Önemli bulgu**: nakit getirisi eklenince, en kötü epizodun KİMLİĞİ
değişti VE bazı S1 epizotları İKİYE AYRILDI (nakit dönemlerindeki tahakkuk,
epizotlar arasında equity'nin YENİ bir tepe yapmasını sağladı):

| # | Peak | Trough | Recovery | Derinlik (S1b) | S1'deki karşılığı |
|---|---|---|---|---|---|
| 1 | 2013-05-22 | 2013-11-11 | 2015-01-22 | **-%28.43** (yeni en kötü) | S1'de -%29.25 (2013-2015, benzer ama daha derin ve az farklı sınırlarla) |
| 2 | 2006-02-28 | 2007-01-10 | 2007-07-23 | -%28.16 | S1'in -%33.50'lik (2006-2009, Lehman'a kadar birleşik) epizodunun İLK YARISI — nakit getirisi 2007 ortasında toparlanmayı HIZLANDIRMIŞ, 2008 krizi ARTIK AYRI bir epizot |
| 3 | 2015-05-19 | 2016-02-12 | 2017-04-20 | -%27.53 | S1'de -%28.05, neredeyse aynı |
| 4 | 2020-01-21 | 2020-03-12 | 2020-11-13 | -%23.96 | S1'de 2018-2020 BİRLEŞİK epizodun (-%31.59) parçasıydı — **ŞİMDİ AYRI**: 2018 TL krizi (2018-02-26→2019-03-11, -%12.89, ayrı satır) ile COVID (2020) arasında equity YENİ TEPE yapmış (nakit getirisi sayesinde) |
| 5 | 2023-01-03 | 2023-02-08 | 2023-03-06 | -%22.78 | S1'de -%22.78 (aynı — deprem dönemi, nakit-dışı) |

**2008 küresel finans krizi artık**: 2007-10-12→2008-01-17 (recovery
2009-05-05, derinlik **-%19.18**) — S1'in -%33.50'lik mega-epizodundan ÇOK
DAHA SIĞ görünüyor, çünkü nakit getirisi hem ÖNCESİNDE (2007 ortası
toparlanma) hem SONRASINDA (2009 toparlanması) equity'yi destekliyor.

## (d) %10+ Drawdown Epizotları — TAM Tablo (23 epizot)

| Peak | Trough | Recovery | Derinlik |
|---|---|---|---|
| 2013-05-22 | 2013-11-11 | 2015-01-22 | -28.43% |
| 2006-02-28 | 2007-01-10 | 2007-07-23 | -28.16% |
| 2015-05-19 | 2016-02-12 | 2017-04-20 | -27.53% |
| 2020-01-21 | 2020-03-12 | 2020-11-13 | -23.96% |
| 2023-01-03 | 2023-02-08 | 2023-03-06 | -22.78% |
| 2010-11-09 | 2012-06-11 | 2012-10-30 | -22.60% |
| 2024-07-11 | 2024-10-03 | 2025-08-04 | -22.53% |
| 2021-12-16 | 2021-12-22 | 2022-03-30 | -22.51% |
| 2007-07-24 | 2007-08-16 | 2007-10-05 | -20.95% |
| 2007-10-12 | 2008-01-17 | 2009-05-05 | -19.18% |
| 2021-01-13 | 2021-04-21 | 2021-10-14 | -18.33% |
| 2023-03-08 | 2023-05-25 | 2023-06-05 | -17.88% |
| 2015-01-26 | 2015-03-13 | 2015-05-14 | -16.38% |
| 2023-10-02 | 2023-10-25 | 2024-01-15 | -15.36% |
| 2022-09-12 | 2022-09-29 | 2022-10-17 | -15.31% |
| 2022-06-06 | 2022-07-14 | 2022-08-08 | -14.35% |
| 2010-01-20 | 2010-02-25 | 2010-03-25 | -14.18% |
| 2025-09-22 | 2025-11-14 | 2026-01-06 | -13.62% |
| 2018-02-26 | 2019-03-11 | 2019-11-18 | -12.89% |
| 2026-05-11 | 2026-05-21 | (devam ediyor) | -12.74% |
| 2009-10-23 | 2009-11-03 | 2009-12-03 | -11.63% |
| 2010-04-26 | 2010-05-25 | 2010-07-27 | -11.43% |
| 2025-08-26 | 2025-09-08 | 2025-09-19 | -10.02% |

(S1'de 19 epizot vardı, S1b'de **23** — nakit getirisiyle bazı büyük
epizotların ikiye bölünmesinin doğal sonucu. Breaker kalibrasyon kaydı
için ham girdi — bu turda karar VERİLMEDİ.)

## Madde 3(i) — 2024-2025 Epizodu ve DATA_AUDIT_v2 Örtüşmesi

S1b'de bu epizodun TEKNİK trough'u artık **2024-10-03** (derinlik -%22.53,
recovery 2025-08-04) — S1'deki 2025-03-21'den FARKLI (nakit getirisi,
2024-10-03 ile 2025-03 arası equity'yi kısmen desteklemiş ama YENİ bir tepe
yapacak kadar değil). **Ancak 2025-03-19/21 hâlâ bu epizodun İÇİNDE, KESKİN
bir YEREL düşüş olarak duruyor**: equity 2025-03-17'de ~14.38M'den
2025-03-21'de ~11.95M'ye (~%17 yerel düşüş, 3 işlem gününde) iniyor —
DATA_AUDIT_v2.md'nin **2025-03-19/21 piyasa-çapında gap kümesiyle** zamansal
olarak TAM örtüşüyor. **Sonuç: bu örtüşme S1b'de de GEÇERLİ** — yalnızca
"epizodun en derin noktası" etiketi teknik olarak başka bir tarihe kaymış,
olayın kendisi (ve veri kalitesi ilişkisi) aynen duruyor.

## (e) MÜHÜRLÜ KABUL TABLOSU — S1'in AYNI eşikleriyle, MEKANİK doldurma (hüküm yok)

| # | Kriter | S1 sonucu | **S1b sonucu** | S1b Durumu |
|---|---|---|---|---|
| 1 | TRY Sharpe > XU100 al-tut Sharpe | 1.064 > 0.851 (GEÇTİ) | **1.215 > 0.851** | ✅ **GEÇTİ** |
| 2 | Max DD ≤ endeks max DD'nin yarısı (≤ -%31.72) | -%33.50 (GEÇMEDİ) | **-%28.43 ≤ -%31.72** | ✅ **GEÇTİ** |
| 3 | OOS aylık-Sharpe > al-tut (sepet) OOS Sharpe VE OOS max DD ≤ al-tut OOS DD'nin yarısı (≤-%28.12) | Sharpe 0.9505<0.9723 (FAIL); DD -%30.30 (FAIL) — GEÇMEDİ | **Sharpe 1.0678>0.9723 (PASS); DD -%24.55≤-%28.12 (PASS)** | ✅ **GEÇTİ** |
| 4 | Uçurum kontrolü: 200/%1/3 komşuluğunda performans uçurumu yok | Komşu Sharpe 1.02-1.18, maxDD -%26.5/-%40.2 (GEÇTİ) | Komşu Sharpe 1.20-1.35, maxDD -%25.4/-%35.1 — yine sürekli, uçurum yok | ✅ **GEÇTİ** |

**Mekanik sonuç: 4/4 kriter GEÇTİ.** Bu bir HÜKÜM değildir — yalnızca
önceden mühürlenmiş eşiklerin mekanik olarak uygulanmasıdır. STATUS.md'deki
önceden belirlenmiş kural gereği ("4/4 geçerse aile kabul adayı") bu sonuç
D1 ailesini bir **kabul adayı** yapıyor — ama nihai kabul/üretim kararı
kullanıcının/baş danışmanın.

## (f) USD Çevrimi — ÜÇ Taraf

| Metrik | Strateji | 12-sembol sepeti al-tut | XU100 al-tut |
|---|---|---|---|
| USD toplam getiri | +501% | **+1,976%** | +66% |
| USD CAGR | **+%8.70** | **+%15.15** | +%2.38 |
| USD Sharpe | 0.435 | **0.577** | 0.234 |
| USD max DD | -%67.03 | -%75.06 | -%77.77 |

**Önemli, dürüst gözlem**: S1'e göre stratejinin USD CAGR'ı iyileşti
(+%5.08 → +%8.70) ve USD max DD'si düzeldi (-%75.03 → -%67.03) — nakit
getirisi USD performansına da (kısmen, TRY devalüasyonunu telafi ederek)
katkı sağlıyor. **AMA TRY'de gözlemlenen "filtre sepetten daha iyi Sharpe"
sonucu USD'DE TERSİNE DÖNÜYOR**: 12-sembol sepeti al-tut'un USD Sharpe'ı
(0.577) stratejininkinden (0.435) YÜKSEK — yani filtrenin risk-ayarlı
üstünlüğü yalnızca TRY-nominal terimde net; USD (reel/uluslararası yatırımcı
perspektifi) teriminde filtresiz sepet DAHA İYİ risk-ayarlı getiri
sağlıyor. Bu, "başarı çıtası" tartışmasında (STATUS.md KALICI KAYIT 1)
dikkate alınması gereken önemli bir nüans.

## (g) Monte Carlo — Aylık Getiri Permütasyonu

S1 ile AYNI yöntem (aylık getiri permütasyonu) ve AYNI örnek sayısı
(500 koşum, seed=42, `config/regime_core.yaml::monte_carlo`):

| Persentil | S1 (faizsiz) | **S1b (faizli)** |
|---|---|---|
| dd_p5 (en kötü %5 senaryo / worst-5%) | -%48.57 | **-%44.68** |
| dd_median | -%34.03 | **-%31.28** |
| dd_p95 (en iyi %5 senaryo) | -%25.23 | **-%23.03** |

Nakit getirisi, MC'nin ÜÇ persentilinde de (worst-5%'ten best-5%'e kadar)
tutarlı bir iyileşme gösteriyor — ana koşumun ve OOS'un gösterdiği aynı
yönde bir etki. Bu koşum S1b'nin ana `main()` çalıştırması sırasında ZATEN
üretilmişti (`runtime/regime_core_s1b/summary.json::monte_carlo_monthly`)
ama ilk yazımda bu markdown'a EKLENMEMİŞTİ — bu, o eksikliğin
düzeltilmesidir (S1b'nin hiçbir sayısı değişmedi, yalnızca rapora
eklendi).

## Madde 3(j) — Gap-Proximity ve Maliyet Duyarlılığı

**Gap-proximity**: 67 anahtarlamadan **3'ü (%4.48)** DATA_AUDIT_v2.md'nin
45 benzersiz şüpheli gününden birine ±5 bar mesafede — **S1 ile BİREBİR
AYNI** (beklenen: cash yield anahtarlama TARİHLERİNİ etkilemiyor, yalnızca
nakit-dönemi büyümesini). *(İlk hesaplamada bir betik hatası nedeniyle
yanlışlıkla 9/67 bulunmuştu — gerçek OHLCV verisiyle düzeltildi, bkz. yukarı.)*

**Maliyet duyarlılığı (2× komisyon, nakit getirisiyle birlikte)**: CAGR
%28.21→%27.81, Sharpe 1.215→1.201, max DD -%28.43→-%29.07. **Küçük bir
bozulma** — S1'deki gibi düşük anahtarlama sıklığı nedeniyle strateji
maliyet artışına nispeten dayanıklı kalıyor.

## Çekinceler (S1'den taşınan + yeni)

1. Tek tarihçe, tek koşum (S1'deki gibi).
2. Anahtarlama sayısının azlığı (67, S1'deki gibi — istatistiksel örneklem uyarısı).
3. **YENİ**: TRY_ON_RATE kaynağı TCMB'nin KENDİSİ değil, OECD/FRED
   rebroadcast'i — 9 aylık bir boşluk (2023) forward-fill ile dolduruldu,
   TAM DE yüksek faiz artış döneminde, muhtemelen gerçek tahakkuku HAFİFE
   ALIYOR.
4. **YENİ**: 200bp kırpma tek bir sabit varsayım — gerçek mevduat/repo
   spread'i zamanla değişmiş olabilir, bu turda sabit tutuldu.
5. **YENİ**: USD Sharpe karşılaştırması filtrenin lehine DEĞİL (bkz. (f)) —
   "başarı" tanımı hangi para biriminde ölçüldüğüne göre DEĞİŞEBİLİR.

---

**Karar benim değil, kullanıcının/baş danışmanın.** Hiçbir eşik/gate/
parametre değiştirilmedi. Faz 5'e/E2'ye geçilmedi. Sonuç ne olursa olsun bu
turda hiçbir ek koşum/parametre ayarı yapılmadı — Durma Noktası 1'de
duruluyor, değerlendirme bekleniyor.

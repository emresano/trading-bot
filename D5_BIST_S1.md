# D5_BIST_S1.md — "D1 + Fırsat-Maliyeti (Faiz) Kapısı" Challenger Spike Değerlendirme Raporu

**Tarih:** 2026-07-10 · **Mühür:** `D5_CRITERIA.md` (koşumdan ÖNCEKİ commit `5376aad`;
o commit'te `backtest/regime_core_gated.py` HENÜZ YOKTU — commit sırası kanıttır).
**Koşum commit'i:** `5e3961b`. **Veri:** frozen S1b snapshot (`data/snapshots/2026-07-06`)
+ S1b'nin tarihsel `TRY_ON_RATE` serisi (`data/snapshots/aux/2026-07-07/`) — **yeni indirme YOK.**

> **Bu bir DEĞERLENDİRME SPIKE'ıdır — üretim implementasyonu DEĞİL, HÜKÜM YOK.**
> Kabul/red/iterasyon kararı kullanıcının/baş danışmanın; bu rapor yalnız mekanik girdidir.
> `mode: paper`, D1 paper hattı ve TÜM canlı bot modülleri bu turda DOKUNULMADI.

---

## 0. AÇILIŞ ÇEKİNCESİ — sonuç-bilgili tasarım (KARARDAN ÖNCE okunmalı)

Bu fikir `PERIOD_COMPARISON.md`'nin **son-3-yıl gözleminden doğdu**: D1'in o pencerede
TL nakit faizinin gerisinde kaldığı **görüldükten SONRA** "hisse ≤ faiz ise nakitte kal"
kapısı tasarlandı. **Sonuç-bilgili (result-informed) bir tasarımdır**; BIST tarihçesine
bu proje boyunca defalarca bakılmıştır. `D5_CRITERIA.md` §0 bunu koşumdan önce kayda
geçirdi ve şu dengeleri kurdu: (i) referans **sepet/endeks değil, D1'in KENDİSİ** —
çıta yukarı çekildi; (ii) sonuç OOS-ağırlıklı okunur; (iii) **kabul bile canlıya alma
demek değildir**; (iv) ikinci ölçüm-bakışı yoktur.

**Bu raporun en önemli bulgusu, tam da bu kirlenmenin ölçülebilir hale gelmesidir**
(§6 pencere tablosu): D5'in tüm üstünlüğü fikrin doğduğu döneme (2016-2026) yığılmış,
o dönemin dışındaki 11 yılda ise D5 D1'in belirgin şekilde ALTINDA kalmıştır.

---

## 1. Mühürlü Tasarım Paketi (`D5_CRITERIA.md` §1 — özet)

| Bileşen | Değer | Not |
|---|---|---|
| D1 mekaniği | **AYNEN** | N/b/M = **200 / %1 / 3**, maliyet 10+5 bps, t+1 kapanış, tam-lot |
| N/b/M kaynağı | `inherit_from: config/regime_core.yaml` | **kopyalanmadı, devralındı** → sapma yapısal olarak imkânsız |
| **Kapı (TEK ek katman)** | kompozitin trailing **252 işlem-günü** getirisi vs **HAM** `TRY_ON_RATE`'in aynı takvim penceresindeki bileşik getirisi | `stock_ret ≤ cash_ret` → NAKİT |
| Kapı asimetrisi | açılış **3 gün** teyitli / kapanış **1 gün** | D1'in kendi asimetrisinin aynısı |
| Efektif pozisyon | `rejim_ON` **VE** `kapı_AÇIK` | kapı yalnız KISITLAR, asla maruziyet EKLEMEZ |
| Haircut ayrımı | sinyal eşiği **ham** (0bp) · nakit tahakkuku **200bp haircut'lı** (S1b) | emsal `D4US_CRITERIA.md` §1.5 |
| Isınma | ilk 252 bar: kapı **KAPALI** | muhafazakâr; genişleyen-pencere yaklaşıklığı YOK |
| Pencere gerekçesi | 252 işlem günü ≈ 12 ay | dual-momentum varsayılanı (Antonacci GEM / Faber GTAA) — **taranmadı** |

**Grid/varyant seçimi YAPILMADI.** Komşuluk (§8) ve MC (§9) yalnız bilgilendiricidir.

**Sadakat çapası (kopya-riskine karşı):** `regime_core_gated.py`nin yürütme döngüsü,
`backtest/regime_core.py`nin döngüsüyle aynı olmak zorundadır. `gate_cfg=None` verildiğinde
modül D1'i yeniden üretir ve `tests/test_d5_bist.py::test_gate_none_is_bit_identical_to_d1`
bunu equity eğrisi / anahtarlamalar / rejim serisi düzeyinde **bit-bit** doğrular.

---

## 2. Benchmark: D1'in KENDİSİ (mühürlü, strateji koşulmadan)

D1 (S1b, nakit-getirili), **aynı frozen veriyle** `backtest/regime_core.py` (DEĞİŞTİRİLMEMİŞ
S1/S1b simülatörü) yeniden çağrılarak üretildi ve `runtime/regime_core_s1b/summary.json`
kayıtlarına karşı **9/9 alanda BİREBİR (Δ = 0.0)** doğrulandı. Eşleşmeseydi mühürleme
`RuntimeError` ile duracaktı (`tools/run_d5_bist.py::verify_against_s1b`).

Kompozit: **2005-01-03 → 2026-07-03, 5511 gün.** Hayalet bar: EREGL 2024-04-09 (1, temizlendi).

| D1 (S1b) | Değer |
|---|---|
| CAGR | **+28.211%** |
| Max DD | **-28.428%** |
| Sharpe (günlük, √252) | **1.21526** |
| OOS aylık-Sharpe (39 pencere / 229 ay) | **1.06776** |
| OOS max DD | -24.553% |
| Anahtarlama | 67 |
| MC dd_p5 (aylık perm., seed=42, 500) | -44.68% |

---

## 3. MÜHÜRLÜ TABLO — MEKANİK SONUÇ (referans = D1)

> `D5_CRITERIA.md` §3'ün mekanik doldurmasıdır — **HÜKÜM DEĞİL.** Kabul kuralı önceden
> mühürlendi: **1+2+3a+3b'nin TAMAMI → ADAY; herhangi biri kalırsa RED. Dar fark YOK.**

| # | Kriter | D5 | Eşik (D1) | Δ | Sonuç |
|---|---|---|---|---|---|
| **1** | TRY Sharpe > D1 Sharpe | **1.27376** | 1.21526 | **+0.05849** | ✅ **PASS** |
| **2** | TRY CAGR > D1 CAGR | **27.150%** | 28.211% | **−1.061 pp** | ❌ **FAIL** |
| **3a** | OOS aylık-Sharpe > D1 OOS | **1.16089** | 1.06776 | **+0.09314** | ✅ **PASS** |
| **3b** | \|maxDD\| ≤ D1 \|maxDD\| | **35.224%** | 28.428% | **−6.796 pp** | ❌ **FAIL** |

### → **2/4 geçti. Önceden mühürlenen kurala göre D5-BIST bu turda REDDEDİLİR.**

Bu, Claude Code'un hükmü **değildir** — kullanıcının koyduğu kuralın mekanik uygulamasıdır.
**Nihai kayıt kullanıcının/baş danışmanın.**

---

## 4. Ana Koşum (tam dönem, mühürlü tam paket)

| | D5 | D1 |
|---|---|---|
| Toplam getiri | +17 370.1% | +20 786.7% |
| CAGR | 27.150% | 28.211% |
| Max DD | **-35.224%** | -28.428% |
| Sharpe | **1.27376** | 1.21526 |
| Anahtarlama | 69 | 67 |
| OOS aylık-Sharpe | **1.16089** | 1.06776 |
| **OOS max DD** | **-35.633%** | **-24.553%** |
| Maruziyet (yatırımda gün) | **58.7%** | 72.4% |
| Sualtı (drawdown'da) gün | 77.5% | 87.2% |
| **En uzun kesintisiz sualtı** | **1078 işlem günü (~4.3 yıl)** | 514 işlem günü (~2.0 yıl) |

**Kapı genel istatistiği:** kapı AÇIK gün oranı %64.3; kapı D1'i fiilen **bağladığı**
(rejim ON ama kapı KAPALI) gün: **755 gün (%13.7)**. İlk açılış: 2005-12-23.

---

## 5. ⚠ BULGU: Kapı realize drawdown'ı DERİNLEŞTİRDİ — mekanizma

Kapı maruziyeti **yalnızca azaltabildiği** halde (`effective_on ⊆ regime_on`, testle
çapalanmış değişmez) realize max DD **-28.43% → -35.22%'ye derinleşti.** Bu çelişki
gibi görünür; değildir. Mekanizma **toparlanma bastırması**dır:

- D1'in **iki AYRI** drawdown epizodu (2013-05→2013-11, -28.43%, toparlanma 2015-01-22;
  ve 2015-05→2016-02, -27.53%) D5'te **TEK ve DAHA DERİN bir epizoda KAYNAŞIR**:
  **2013-05-22 → 2016-01-08, -35.22%**, toparlanma ancak **2017-07-11**.
- Sebep: D5 aradaki toparlanmaya yeterince katılamadığı için **yeni bir equity zirvesi
  YAPAMADI**; drawdown sayacı sıfırlanmadı.
- Ölçüm — 2013-11-11 → 2015-05-19 toparlanma bacağı:

  | | değer |
  |---|---|
  | Kompozitin getirisi | **+55.6%** |
  | Kapı AÇIK gün oranı | %66.5 |
  | D1 yatırımda gün / equity getirisi | %73.8 / **+45.8%** |
  | D5 yatırımda gün / equity getirisi | %59.2 / **+20.0%** |

**Trailing 12-aylık mutlak momentum, tanımı gereği dip sonrası geç açılır** (çöküş bir yıl
boyunca trailing pencerede kalır). TL gibi yüksek nominal faizli bir para biriminde eşik
sıfır değil, çift haneli olduğu için gecikme **daha da uzar**. Bu, kapının fiyatıdır.

**Emsal tutarlılığı:** aynı yapısal bulgu D2-US'te (2009 rebound: strat −0.8% vs sepet +51%)
ve D4-US'te (2009: +11% vs +34%) kayıtlıdır (KALICI KAYIT 18/21). **Dördüncü aile, aynı
mekanizma.**

---

## 6. (b) Pencere Kıyasları — in-sample kirlenmenin ÖLÇÜMÜ

CAGR (maxDD parantez içinde). "Sepet": her pencerenin **başında taze eşit-ağırlıklı**
(`build_window_start_basket`, `PERIOD_COMPARISON.md` Metodoloji Notu). "Faiz (ham)":
kapının kendi eşiği.

| Pencere | **D5** | **D1** | Sepet (taze) | Faiz (ham) |
|---|---|---|---|---|
| Son 1 Yıl | **30.19%** (-13.6%) | **46.53%** (-13.6%) | 34.76% (-13.5%) | 45.13% |
| Son 3 Yıl | **52.48%** (-15.4%) | 40.14% (-22.5%) | 50.64% (-22.6%) | 50.86% |
| Son 5 Yıl | **82.78%** (-22.8%) | 73.74% (-22.8%) | 75.91% (-22.8%) | 34.85% |
| Son 10 Yıl | **51.04%** (-22.8%) | 42.46% (-24.0%) | 43.99% (-32.6%) | 23.48% |
| **Tam dönem** | 27.15% (**-35.2%**) | **28.21%** (-28.4%) | 35.83% (-64.2%) | 16.05% |

**Okuma (dürüst):**
- D5, fikrin doğduğu **3/5/10 yıllık pencerelerde D1'i geçiyor** — beklenen, çünkü kapı
  tam da o dönemin gözleminden tasarlandı. **Bu pencereler kanıt değil, kirlenmiş girdidir.**
- **Son 1 Yıl'da D5 D1'in çok altında** (30.2% vs 46.5%) — kapı 2025'in %54.2'sinde bağladı
  ve ralliyi kaçırdı. Fikri doğuran gözlemin en taze ucunda bile kapı zarar ettirdi.
- **Tam dönemde D5 kaybediyor** (hem CAGR hem maxDD).
- Kırmızı bayrak: **performans tek döneme yığılmış.** (Aşağıdaki §7 bunu yıl-yıl gösterir.)

---

## 7. (a) + (c) Kapı Zaman Çizelgesi ve Kriz/Testere Yılları

### 7.1 ÖNCEDEN YAZILAN BEKLENTİNİN SINANMASI (`D5_CRITERIA.md` §5a)

Mühürde şu beklenti kayıtlıydı: *"kapı 2005-2020'de **seyrek**, 2024-26'da **yoğun**
bağlamalı; aksi çıkarsa bu tasarımın hipotezinin çürüğüdür ve öyle raporlanır."*

**Sonuç: beklentinin ilk yarısı ÇÜRÜDÜ.** Kapının bağladığı gün oranı (rejim ON, kapı KAPALI):

| yıl | bağlama % | | yıl | bağlama % |
|---|---|---|---|---|
| 2005 | 20.4% | | 2016 | 9.6% |
| 2006 | 8.5% | | 2017 | 0.0% |
| **2007** | **33.5%** | | 2018 | 3.1% |
| 2008 | 0.0% | | **2019** | **22.3%** |
| **2009** | **35.2%** | | **2020** | **25.4%** |
| 2010 | 0.0% | | 2021 | 0.0% |
| 2011 | 0.0% | | **2022** | **0.0%** |
| **2012** | **33.3%** | | **2023** | **0.0%** |
| 2013 | 0.0% | | **2024** | **26.5%** |
| **2014** | **22.2%** | | **2025** | **54.2%** |
| 2015 | 1.9% | | 2026 | 0.0% |

- **Kapı 2005-2020'de SEYREK DEĞİL**: 2007/2009/2012/2014/2019/2020'de %22-35 bağladı.
- **2022 ve 2023'te kapı %100 AÇIK, 0 gün bağladı** — oysa fikir "son 3 yıl"
  gözleminden doğmuştu. O yıllarda BIST'in nominal TL getirisi faizi ezici farkla geçti
  (2022: +213% vs %9.5). Kapı, fikri doğuran gözlemin **iki yılına hiç dokunmuyor**.
- Beklentinin ikinci yarısı (2024-25 yoğun) **doğrulandı** (%26.5 / %54.2), 2026'da ise
  kapı hiç bağlamadı.
- **Yorum:** Düşük faiz dönemlerinde (2010-2014 nakit getirisi %3-6) kapı yine de yoğun
  bağladı → bağlamanın kaynağı yüksek faiz eşiği değil, **hisse bacağının çöküş-sonrası
  trailing-12ay zayıflığı**. Yani bu katman pratikte bir "fırsat-maliyeti filtresi"
  değil, **bir toparlanma-gecikmesi filtresidir.**

### 7.2 Yıllık getiriler — kapının katkısı (+) ve bedeli (−)

| yıl | D5 | D1 | Sepet | Faiz | **kapı (pp)** |
|---|---|---|---|---|---|
| 2005 | 13.2% | 26.7% | 52.1% | 13.5% | **−13.4** (ısınma, §10) |
| 2007 | 23.2% | 33.1% | 48.2% | 16.6% | **−9.9** |
| 2008 | −1.2% | −1.3% | −51.2% | 15.1% | +0.1 |
| **2009** | **40.4%** | **110.9%** | 140.4% | 7.5% | **−70.5** ⬅ *en büyük bedel* |
| 2012 | 30.7% | 37.9% | 71.6% | 3.1% | −7.2 |
| 2013 | −10.8% | −10.4% | 2.3% | 1.8% | −0.4 |
| **2014** | 11.2% | 35.1% | 39.5% | 5.9% | **−23.9** |
| **2018** | 5.2% | −5.6% | −18.9% | 13.5% | **+10.8** |
| **2020** | 51.5% | 21.7% | 40.4% | 7.3% | **+29.9** |
| 2021 | 42.8% | 42.9% | 53.6% | 15.1% | −0.1 |
| 2022 | 213.1% | 213.1% | 180.4% | 9.5% | −0.0 |
| 2023 | 57.5% | 57.5% | 47.7% | 25.7% | −0.0 |
| **2024** | **74.1%** | **30.9%** | 35.1% | 56.3% | **+43.1** ⬅ *en büyük katkı* |
| 2025 | 26.6% | 24.2% | 99.7% | 48.1% | +2.4 |
| 2026 (kısmi) | 26.8% | 33.3% | 58.6% | 18.4% | −6.6 |

**Örüntü:** kapı **gerçek bir çöküş-önleyicidir** (2018 +10.8, 2020 +29.9, 2024 +43.1) ama
**ağır bir toparlanma-kaçıranıdır** (2009 −70.5, 2014 −23.9). Tek başına 2009'un bedeli,
2024'ün katkısını aşıyor. Bu, D2-US/D4-US'te ölçülen mekanizmanın BIST'teki karşılığıdır.

---

## 8. (d) Turnover / Whipsaw + (e) Komşuluk

### 8.1 Turnover — zayıflık maliyet kaynaklı DEĞİL

| | D5 | D1 |
|---|---|---|
| Anahtarlama / round-trip | 69 / 34 | 67 / 33 |
| Anahtarlama / yıl | 3.21 | 3.11 |
| Zararlı round-trip | 17 (%50) | 20 (%61) |
| Kısa (≤30g) round-trip / zararlı | 18 / 12 | 17 / 15 |
| Medyan tutma (gün) | 21.5 | 29.0 |
| **Maliyet sürüklemesi** | **0.614 pp/yıl** | **0.601 pp/yıl** |

Maliyet farkı **0.013 pp/yıl** — CAGR'daki 1.06 pp'lik açığın **%1.2'si**. **Kapının
zararı işlem maliyetinden gelmiyor; maruziyet kaybından geliyor.** (D2/D4 ile aynı ders.)

### 8.2 Komşuluk — GÖZLEMSEL, SEÇİM ARACI DEĞİL

| lookback | confirm | Sharpe | CAGR | maxDD | switch |
|---|---|---|---|---|---|
| 126 | 1 | 1.2485 | 27.75% | -27.91% | 153 |
| 126 | 3 | 1.2411 | 27.25% | -27.57% | 103 |
| 252 | 1 | 1.2492 | 26.60% | -37.74% | 83 |
| **252** | **3** | **1.2738** | **27.15%** | **-35.22%** | **69** ⬅ **MÜHÜRLÜ** |
| 378 | 1 | 1.1994 | 24.63% | -32.39% | 117 |
| 378 | 3 | 1.1563 | 23.34% | -31.36% | 97 |

- **Uçurum yok** (Sharpe 1.156-1.274 sürekli).
- ⚠ **Mühürlü nokta komşuluğun Sharpe ZİRVESİDİR.** `D5_CRITERIA.md` §5e bunu koşumdan
  önce **overfitting şüphesi** olarak tanımlamıştı — öyle raporlanıyor. (Hafifletici not:
  252/3 sonuç görülmeden, literatür varsayılanı olarak seçildi; yine de zirve olması
  rahatsız edicidir ve raporda böyle durur.)
- **Karar tek bir kapı-parametresine bağlı DEĞİL:** komşuluktaki **6 noktanın HİÇBİRİ**
  kriter 2'yi geçmiyor (en yüksek CAGR %27.75 < D1'in %28.21'i). Kriter 3b'yi yalnız
  `lookback=126` noktaları geçiyor, onlar da kriter 2'de kalıyor. **Kapının hiçbir makul
  ayarı D1'i 4/4 yenmiyor.**
- **KALICI YASAK:** sonuç görüldükten sonra komşuluğun "en iyisini" yeni bir aile diye
  aynı tarihçede koşmak varyant-seçimi yasağının ihlalidir (KALICI KAYIT 22 emsali).

---

## 9. (f) Monte Carlo — ve MC ile realize DD'nin ÇELİŞMESİ

Aylık getiri permütasyonu, `seed=42`, 500 koşu:

| | dd_p5 | dd_median | dd_p95 |
|---|---|---|---|
| **D5** | **-39.88%** | -27.85% | -20.40% |
| **D1** | -44.68% | -31.28% | -23.03% |

**MC'ye göre D5 DAHA İYİ; realize patikaya göre D5 DAHA KÖTÜ (-35.2% vs -28.4%).** Bu bir
tutarsızlık değil, **teşhistir**: MC aylık getirileri permüte ederek **patika/seri
bağımlılığını yok eder** — oysa kapının zararı tam olarak patika-bağımlıdır (toparlanmaya
katılmamak → yeni zirve yapamamak → epizotların kaynaşması, §5). **Bu ailede MC, gerçek
drawdown riskini SİSTEMATİK OLARAK OLDUĞUNDAN İYİ gösterir.** Karar realize patikaya göre
verilir; MC yalnız gözlemseldir.

Ek not: D5'in MC `dd_p5`'i (-39.88%) D1 ailesinin **FREEZE eşiğine (-%40, KALICI KAYIT 6)**
pratik olarak temas ediyor. (D1'in kendi dd_p5'i -44.68% ile eşiği zaten aşıyor — bu ayrı,
önceden bilinen bir konudur, bu turun konusu değildir.)

---

## 10. ISINMA ARTEFAKTI (`D5_CRITERIA.md` §4 — KRİTER DEĞİL, koşumdan önce mühürlendi)

Kapı ilk **2005-12-21**'de değerlendirilebilir; D1'in ilk ENTER'ı **2005-10-12**'dir → D5
yapısal olarak ilk pozisyonun ~2.5 ayını kaçırır. **Artefakt mı, kapının etkisi mi?** İki
eğri de 2005-12-21'de 100 000'e yeniden normalize edilerek:

| | CAGR | maxDD | Sharpe |
|---|---|---|---|
| D1 | 28.360% | **-28.428%** | 1.2031 |
| D5 | 27.819% | **-35.224%** | 1.2752 |

**Sonuç: artefakt DEĞİL.** Isınma çıkarıldığında bile CAGR açığı (−0.54 pp) ve — asıl
önemlisi — **maxDD kötüleşmesi (−6.80 pp) AYNEN durur.** Kriter 2 ve 3b'nin başarısızlığı
ısınma kaymasıyla açıklanamaz. (Bu yan-ölçüm koşumdan ÖNCE mühürlendi; sonradan eklenmiş
bir savunma değildir.)

---

## 11. ⚠ KARAR-ÖNCESİ ÇEKİNCELER (`D5_CRITERIA.md` §5g — disiplin #6)

1. **Sonuç-bilgili tasarım / in-sample kirlenme (birincil çekince).** §0 + §6. D5'in
   üstünlüğü fikrin doğduğu 2016-2026 penceresine yığılı; dışındaki 11 yılda D1'in altında.

2. **"OOS geçti" argümanı bu turda ZAYIFTIR (metodoloji dersi).** `D5_CRITERIA.md` §0.2
   sonucun "OOS-ağırlıklı" okunacağını mühürlemişti ve kriter **3a geçti**. Ancak bu
   walk-forward'da **hiçbir parametre optimize edilmiyor** (N/b/M/kapı sabit) — "OOS",
   *aynı sabit stratejinin aynı 21 yılın dilimlerinde* ölçülmesidir. Dolayısıyla
   **tasarım-kökeni kirlenmesine karşı KORUMA SAĞLAMAZ.** Ayrıca OOS tablosunun diğer
   yarısı D5 aleyhinedir: **OOS max DD -35.63% vs D1 -24.55%.** OOS resmi karışıktır,
   D5 lehine değildir. *(Bu düzeltme sonucu değiştirmiyor — kriter 2 ve 3b zaten kaldı;
   bu yüzden "sonuca göre yorum" değil, kayda geçirilen bir derstir.)*

3. **OPERASYONEL — canlı faiz beslemesi BAYAT (bilinen sorun #18).** Backtest'te
   `TRY_ON_RATE` tarihsel olarak tamdır; **canlıda kapı BAYAT faizle karar verir**: FRED/OECD
   beslemesi ~**130 gün** gecikmelidir (son gerçek gözlem **2026-03-01**, %35.5 ile
   forward-fill). Backtest serisinin son ~4 ayı da bu ffill'e dayanır → **kapının EN SON
   dönemdeki kararları (2026) sabit varsayılmış bir faizle üretilmiştir.**
   → **Bu turun sonucu RED olduğu için ön koşul devreye girmiyor; ancak kayda geçirilir:
   D5 (veya faiz-eşikli herhangi bir kapı) ileride kabul edilirse, #18'in çözümü
   (tanım-uyumlu, zamanlı faiz serisi) canlıya alınmanın ÖN KOŞULUdur.**

4. **Faiz serisinin kaynağı TCMB değil** (FRED/OECD rebroadcast, KALICI KAYIT 6b): 2023'te
   9 aylık ff boşluğu; EVDS ile ~2-6 puanlık sistematik seri-tanım farkı (`EVDS_COMPARISON.md`).
   Kapı bu seriyi **eşik** olarak kullandığı için, tahakkuktan farklı olarak, seri-tanım
   farkı **karar sınırını kaydırabilir** (tahakkukta hata ikinci derecedendir; eşikte
   birinci derecedendir). Bu, faiz-eşikli her tasarım için yapısal bir kırılganlıktır.

5. **Örneklem:** 21 yıl, 34 round-trip, 755 bağlama günü. Kapının kritik anları (2009, 2024)
   **birer olaydır**; istatistiksel güç düşüktür.

6. **Mühürlü nokta komşuluğun Sharpe zirvesidir** (§8.2) — overfitting şüphesi olarak
   raporlanır.

---

## 12. Bağlam: DÖRT AİLE, AYNI MEKANİZMA (bilgilendirici)

| Aile | Referans | Mekanik | 3b (DD-kesme) | Getiri/risk-ayarlı edge |
|---|---|---|---|---|
| D1-US (E4/E4b) | US sepeti | rejim filtresi | PASS | FAIL |
| D2-US | US2 sepeti | kesitsel momentum | PASS | FAIL |
| D4-US | 10-ETF sepeti | dual-momentum | PASS | FAIL |
| **D5-BIST** | **D1'in kendisi** | **mutlak-momentum kapısı** | ❌ **FAIL** | kısmî (Sharpe ✅, CAGR ❌) |

D5, önceki üç aileden **iki yönden ayrışıyor**: (i) referansı bir sepet değil, kabul edilmiş
kendi ailemiz; (ii) **3b'yi geçen ilk-üç ailenin aksine D5 3b'de KALDI** — savunma katmanı
eklendiği halde realize drawdown **derinleşti** (§5). Buna karşılık D5, dördünün içinde
**risk-ayarlı getiride (Sharpe) referansını geçen TEK aile** oldu (1.274 > 1.215).

**Yapısal ders (üçüncü kez teyit):** trailing-12ay mutlak momentum katmanları çöküşü keser
ama toparlanmayı kaçırır. BIST'te bu, D1'in en güçlü özelliğini (hızlı yeniden-giriş →
epizotların toparlanıp sıfırlanması) bozarak **sermaye korumasını iyileştirmek yerine
kötüleştirdi**.

---

## 13. Kapanış (HÜKÜM YOK)

Mühürlü tablo **2/4**. Önceden belirlenen kurala göre (*"1+2+3a+3b'nin TAMAMI geçerse ADAY;
biri kalırsa RED; dar fark yok"*) **bu mekanik sonuç D5-BIST'i bir kabul adayı YAPMAZ.**
Bu bir HÜKÜM değil — kullanıcının koyduğu kuralın mekanik uygulamasıdır; **nihai kayıt
kullanıcının/baş danışmanın.**

- **İkinci ölçüm-bakışı YOKTUR** (mühürde kapalı, `D5_CRITERIA.md` §6.5). BIST tarihçesine
  D5 bakış sayacı: **1 kullanıldı.** Kapı ailesinin varyantları (farklı pencere/teyit/haircut)
  bu tarihçede **KAPALIDIR**.
- **Kabul çıksaydı bile canlıya alma demek olmayacaktı** (§0). Çıkmadı.
- **D1 paper hattı DEĞİŞMEDİ.** `mode: paper`, `config/regime_core.yaml`, N/b/M=200/%1/3,
  tüm canlı bot modülleri ve snapshot'lar bu turda **DOKUNULMADI**. Aktif kuyruk
  (K1.5 2/2 → G1 launchd → Faz 6) bu turdan **etkilenmedi**.
- Faz 6 / `go_live` / launchd / real adımı **YOK**; iki durma noktası kullanıcıda.

*Rapor sonu.*

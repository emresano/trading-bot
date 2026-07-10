# D5_CRITERIA.md — MÜHÜRLÜ Kabul Kriterleri + Tasarım Sabitleri (D5-BIST CHALLENGER)

> **Bu dosya bir SÖZLEŞMEDİR.** Aşağıdaki (a) tasarım paketi ve (b) kabul tablosu +
> sayısal eşikler, D5-BIST ("D1 + fırsat-maliyeti kapısı") spike'ı **KOŞULMADAN ÖNCE**,
> yalnızca **D1'in kendi (S1b) kayıtlı metriklerinden** ve dual-momentum literatürünün
> varsayılanlarından mekanik türetilerek mühürlenmiştir. **Commit sonrası ESNETİLEMEZ —
> "dar farkla geçti/geçmedi" YOKTUR; grid/varyant SEÇİMİ YOKTUR (tasarım TEK paket).**
> Strateji sonucu bu eşiklere MEKANİK uygulanır; kabul/red/iterasyon kararı
> kullanıcının/baş danışmanın (Claude Code hüküm vermez).
>
> Emsal: `D4US_CRITERIA.md` + `D2US_CRITERIA.md` + `E4_CRITERIA.md` + `REGIME_CORE_S1B.md`.
> Referans **D1'in KENDİSİdir** (sepet değil, XU100 değil) — bu bir *challenger* turudur.
> Para birimi: **TRY** (D1'in yerli para birimi; USD paneli yalnız BİLGİLENDİRİCİ).

**Mühür tarihi/commit:** 2026-07-10, `config/d5_bist.yaml` + bu dosyanın ilk commit'i,
HERHANGİ bir D5 strateji koşumundan ÖNCE. **Commit sırası kanıttır:**
`backtest/regime_core_gated.py` (kapı + kapılı simülatör) bu commit'te **HENÜZ YOKTUR.**

**Veri (yeni indirme YOK):** `data/snapshots/2026-07-06` (S1b frozen snapshot, 12 sembol)
+ `data/snapshots/aux/2026-07-07/TRY_ON_RATE.parquet` (S1b'nin tarihsel faiz serisi, 255
aylık gözlem, 2005-01-01 → 2026-03-01). Kompozit: **2005-01-03 → 2026-07-03, 5511 gün.**

---

## 0. AÇILIŞ ÇEKİNCESİ — sonuç-bilgili tasarım (bu turun en önemli sınırı)

Bu fikir **`PERIOD_COMPARISON.md`'nin son-3-yıl gözleminden doğdu**: D1'in bu pencerede
TL nakit faizinin gerisinde kaldığı **görüldükten SONRA** "hisse ≤ faiz ise nakitte kal"
kapısı tasarlandı. Bu, tanımı gereği **sonuç-bilgili (result-informed) bir tasarımdır**;
BIST tarihçesine bu proje boyunca defalarca bakılmıştır. Gizlenmez, kabul edilir ve
protokolle dengelenir:

1. **Çıta yukarı çekildi, aşağı değil.** Mühürlü referans sepet ya da endeks DEĞİL —
   **kendi kabul edilmiş ailemiz D1**. Bir challenger'ın, yenmeye çalıştığı şampiyondan
   daha zayıf bir çıtayla ölçülmesi anlamsızdır.
2. **Sonuç OOS-ağırlıklı okunur.** Tam-dönem tablosu (kriter 1/2/3b) in-sample kirlenmiş
   sayılır; **walk-forward OOS kriteri (3a) daha yüksek kanıt değeri taşır** ve raporda
   böyle yorumlanır.
3. **Kabul ≠ canlıya alma.** 4/4 çıksa dahi sonuç yalnızca "ADAY"dır. Canlıya alma
   AYRI bir gölge/paralel gözlem dönemi + AYRI kullanıcı kararı gerektirir
   (tek-davranış-değişikliği disiplini; CLAUDE.md Bölüm 0.1/0.2).
4. **İkinci ölçüm-bakışı YOKTUR** (D2US/D4US emsali). Ölçüm bu turda TAMdır (maliyet +
   nakit + OOS + MC + kriz + turnover dahil). Her yeniden-koşum tasarım değişikliği
   sayılır ve varyant-seçimi yasağına (disiplin #3) girer.

---

## 1. MÜHÜRLÜ TASARIM PAKETİ — TEK paket, literatür varsayılanları, TARAMA YOK

> Kaynak: `config/d5_bist.yaml`. Aşağıdakiler TEK paket olarak mühürlüdür; koşum
> sonucuna göre bileşen değiştirilmez/seçilmez. Komşuluk (§5e) ve MC (§5f) YALNIZ
> bilgilendiricidir — **kabul yalnız tam pakete uygulanır.**

### 1.1 D1 mekaniği AYNEN (hiçbir parametre ayarı yok)
12 sembol eşit-ağırlık kompozit; rejim sinyali MA(**N=200**) ± **b=%1** bandı, giriş
**M=3** gün teyitli / çıkış 1 gün; t+1 **KAPANIŞ** yürütmesi; tam-lot eşit bölme;
komisyon 10bps + slipaj 5bps; rejim KAPALI günlerde nakde ACT/365 tahakkuk.
**N/b/M = 200/0.01/3 mühürlüdür ve bu turda DEĞİŞTİRİLMEZ.** Yapısal garanti:
`config/d5_bist.yaml` bu sabitleri kopyalamaz, `inherit_from: config/regime_core.yaml`
ile **devralır** → elle senkronizasyon sapması imkânsızdır.

### 1.2 TEK EK YAPISAL KATMAN — sepet-düzeyi fırsat-maliyeti kapısı
Her işlem günü, kompozitin **trailing 252 işlem-günü toplam getirisi**, **ham
`TRY_ON_RATE`'in AYNI takvim penceresinde bileşiklenen getirisi** ile karşılaştırılır:

```
stock_ret[t] = composite[t] / composite[t-252] - 1
cash_ret[t]  = Π ( 1 + rate_raw[i]/365 ) ^ (takvim_gün_farkı[i])  - 1     ,  i ∈ (t-252, t]
favorable[t] = stock_ret[t] > cash_ret[t]
```

`cash_ret` bileşikleme formülü, `backtest/regime_core.py`'nin nakit tahakkuk
formülünün **birebir aynısıdır** (`(1 + r/365) ** gün_farkı`) — yalnız haircut yoktur
(§1.4). Uygulama, mevcut `compute_cash_only_curve(..., haircut=0.0)` fonksiyonunun
**yeniden kullanımıdır** (yeniden yazılmaz → drift imkânsız).

**Pencere kararının gerekçesi (mühürlü, sonuçtan BAĞIMSIZ):** 252 işlem günü ≈ **12 ay**.
Bu, mutlak-momentum / dual-momentum literatürünün (Antonacci, *Dual Momentum Investing*,
"GEM"; Faber, "GTAA/GAA") **varsayılan formation penceresidir** ve `D4US_CRITERIA.md`
§1.1'de aynı gerekçeyle zaten mühürlenmiştir. **Taranmaz, ayarlanmaz.**

### 1.3 Kapının asimetrisi = D1'in KENDİ asimetrisi
Kapı **günlük** değerlendirilir ve D1'in "giriş teyitli, çıkış hızlı" (sermaye-koruma
öncelikli) asimetrisini aynen kullanır:

- **AÇILIŞ:** `favorable` **3 gün üst üste** (`confirm_days = 3`, D1'in M'iyle aynı sayı).
- **KAPANIŞ:** `not favorable` **tek gün** (`close_days = 1`, D1'in çıkış kuralıyla aynı).

**Efektif pozisyon = `rejim_ON` VE `kapı_AÇIK`.** Yürütme yine t+1 kapanışta (dünün
efektif sinyaline göre). Kapı yalnızca **kısıtlar**; asla D1'in kapalı olduğu bir günde
pozisyon AÇTIRMAZ.

### 1.4 Haircut ayrımı (D4US emsali)
- **SİNYAL eşiği (kapı):** **HAM** `TRY_ON_RATE` — haircut YOK.
- **NAKİT TAHAKKUKU (equity):** S1b'nin **200bp haircut'lı** formülü AYNEN
  (`CASH_YIELD_HAIRCUT = 0.02`, değiştirilmez).

Emsal: `D4US_CRITERIA.md` **§1.5** — *"T-bill oranı = ham DGS3MO (haircut YOK — sinyal
eşiği, nakit-bacağı getirisi değil)"*. *(Kullanıcı talimatında bu emsal "§1.7" olarak
anıldı; içerik aynıdır, doğru bölüm numarası §1.5'tir.)*

### 1.5 Isınma kuralı (koşumdan ÖNCE mühürlü, muhafazakâr)
Kompozitin ilk **252** barında kapı **değerlendirilemez** → **KAPALI** sayılır.
Genişleyen-pencere (expanding-window) yaklaşıklığı **KULLANILMAZ** (look-ahead ve
tanım kayması riski).

**Bunun bilinen, önceden kabul edilen bedeli:** D1'in rejim sinyali `iloc=199`
(**2005-10-07**) itibarıyla değerlendirilebilirken kapı ancak `iloc=252`
(**2005-12-21**) itibarıyla değerlendirilebilir, en erken **2005-12-23**'te açılabilir.
D1'in ilk ENTER'ı **2005-10-12**'dir → **D5 bu ilk pozisyonun ilk ~2.5 ayını yapısal
olarak kaçırır.** Bu bir metodolojik artefakttır, kapının ekonomik katkısı değildir;
raporda **ayrıca ölçülür ve gizlenmez** (§4).

### 1.6 Kapsam
LONG-only; kaldıraç YOK; ara rebalance YOK; short YOK. Breaker/kill-switch bu spike'ta
YOK (D1 spike'ıyla aynı — `backtest/regime_core.py` docstring).

---

## 2. BENCHMARK: D1'in KENDİSİ — deterministik yeniden üretim + bit-bit doğrulama

D1 (S1b, nakit-getirili), **aynı frozen veriyle** `backtest/regime_core.py`
(DEĞİŞTİRİLMEMİŞ S1/S1b simülatörü) yeniden çağrılarak üretildi ve
`runtime/regime_core_s1b/summary.json` kayıtlarına karşı **9/9 alanda BİREBİR (Δ = 0.0)**
doğrulandı (`tools/run_d5_bist.py --baseline-only`; tolerans **0.0** = tam float eşitliği;
eşleşmeseydi mühürleme `RuntimeError` ile DURACAKTI).

| D1 (S1b) — MÜHÜRLÜ EŞİK KAYNAĞI | Değer |
|---|---|
| Toplam getiri | +20 786.66% (207.86655517405313×) |
| **CAGR** | **0.2821140177136967** (+28.211%) |
| **Max DD** | **-0.28427759469044955** (-28.428%) |
| **Sharpe** (günlük, √252) | **1.2152647870641098** |
| **OOS aylık-Sharpe** (39 pencere, 229 ay) | **1.0677568454631283** |
| OOS max DD | -0.24553189236156825 |
| Anahtarlama sayısı | 67 |
| MC dd_p5 (aylık perm., seed=42, 500) | -0.4467841906343389 |

Kapsam: kompozit 2005-01-03 → 2026-07-03 (5511 gün). Hayalet bar: EREGL 2024-04-09 (1).
OOS makinesi: `train=24ay / test=6ay / step=6ay`, parametre optimizasyonu YOK — D5 **aynı**
OOS makinesinden (`oos_from_reruns`, aynı fonksiyon) geçirilir → kıyas adil.

---

## 3. MÜHÜRLÜ KABUL TABLOSU (D5-BIST) — 4 kriter, referans = D1

> **Challenger şartı:** D5, D1'in **üstüne bir katman ekler**; dolayısıyla hem
> risk-ayarlı getiriyi hem mutlak getiriyi **iyileştirmeli**, hem de D1'in sermaye-koruma
> üstünlüğünü **bozmamalıdır**. İşaret sözleşmesi: max DD derinliği = |max DD| (pozitif).

| # | Kriter | MÜHÜRLÜ eşik (D1) | PASS koşulu (mekanik) |
|---|---|---|---|
| **1** | TRY Sharpe > D1 Sharpe | **1.2152647870641098** | D5 Sharpe **> 1.2152647870641098** |
| **2** | TRY CAGR > D1 CAGR | **0.2821140177136967** | D5 CAGR **> 0.2821140177136967** |
| **3a** | OOS aylık-Sharpe > D1 OOS aylık-Sharpe (S1b şablonu) | **1.0677568454631283** | D5 OOS aylık-Sharpe **> 1.0677568454631283** |
| **3b** | Tam-dönem \|maxDD\| ≤ D1 \|maxDD\| | **28.427759469044955%** | D5 maxDD **≥ -0.28427759469044955** |

**Kabul kuralı (önceden belirlenmiş, sonuç görülmeden):** kriter **1, 2, 3a, 3b'nin
TAMAMI** geçerse D5-BIST bir **ADAY**dır; **herhangi biri kalırsa RED** — *"dar fark"
YOKTUR*, üçüncü bakış YOKTUR. **ADAY olması bile canlıya alma anlamına GELMEZ** (§0.3).
**Nihai karar kullanıcının/baş danışmanın** — bu tablo yalnızca mekanik girdidir.

**Eşitlik durumu:** kriter 1/2/3a **kesin büyüklük** (`>`) ister; eşitlik FAIL'dir.
Kriter 3b `≤` kabul eder (D1'i kötüleştirmemek yeter).

---

## 4. ISINMA ARTEFAKTI — bilgilendirici yan-ölçüm (KRİTER DEĞİL, koşumdan ÖNCE mühürlü)

§1.5'teki ısınma bedeli, mühürlü kriterleri **etkilemez**: kriter tablosu **her zaman**
tam-dönem (2005-01-03'ten başlayan) eğrilerle doldurulur. Buna ek olarak, artefaktı
kirlilikten ayırt edebilmek için rapor şu **bilgilendirici** satırı da içerecektir:

> D1 vs D5, **ortak ısınma-sonrası pencerede** (kapının ilk değerlendirilebildiği bar =
> 2005-12-21'den itibaren, iki eğri de o gün 100 000'e yeniden normalize edilerek).

Bu satır **kriter değildir, eşik değildir ve kabul kararına giremez.** Amacı yalnızca
"D5'in farkı kapının ekonomik etkisi mi, yoksa 2.5 aylık ısınma kayması mı?" sorusunu
dürüstçe cevaplamaktır. Koşumdan sonra eklenmiş bir savunma olmadığı için **şimdi**
mühürlenmiştir.

---

## 5. ZORUNLU ANALİZLER (hepsi BİLGİ — hiçbiri kriter/seçim aracı değil)

- **(a) Kapı zaman çizelgesi:** yıl-yıl nakit-gün oranı, D1'inkiyle yan yana. Beklenti
  kontrolü (ÖNCEDEN yazılır): kapı 2005-2020'de **seyrek**, 2024-26'da **yoğun**
  bağlamalı — çünkü fikir o dönemin gözleminden doğdu. Aksi çıkarsa bu, tasarımın
  hipotezinin **çürüğü** olur ve öyle raporlanır.
- **(b) Pencere kıyasları:** 1y / 3y / 5y / 10y / tam — D5 vs D1 vs taze (pencere-başı
  eşit-ağırlık) sepet vs faiz.
- **(c) Kriz/testere yılları:** 2008, 2013, 2018, 2021-23, 2024-26 — kapının katkısı/bedeli.
- **(d) Turnover / whipsaw:** D5 vs D1 anahtarlama sayısı + maliyet sürüklemesi.
- **(e) Komşuluk — GÖZLEMSEL (SEÇİM DEĞİL):** `lookback ∈ {126, 252, 378}` ×
  `confirm ∈ {1, 3}` (6 kombinasyon). Uçurum var mı? Mühürlü nokta zirve mi?
  **Zirve OLMASI beklenmez ve zirve ÇIKARSA bu overfitting şüphesidir** — komşuluğun en
  iyisini "yeni aile" diye koşmak **KALICI YASAKTIR** (KALICI KAYIT 22 emsali).
- **(f) Monte Carlo:** aylık getiri permütasyonu, `seed=42`, `runs=500` — gözlemsel.
- **(g) KARAR-ÖNCESİ ÇEKİNCELER** (raporda kabul tablosundan ÖNCE):
  1. **Sonuç-bilgili tasarım / in-sample kirlenme** (§0).
  2. **OPERASYONEL — canlı faiz beslemesi BAYAT:** bilinen sorun **#18**. Canlı hatta
     `TRY_ON_RATE` FRED/OECD'den beslenir ve ~**130 gün bayattır** (son gözlem
     2026-03-01). **Backtest'te seri tarihsel olarak tamdır; canlıda kapı BAYAT faizle
     karar verir.** Bu fark açıkça yazılır. **Kabul halinde #18'in çözümü (tanım-uyumlu,
     zamanlı faiz serisi) D5'in canlıya alınması için ÖN KOŞUL ilan edilir.**
     *(Not: backtest serisinin son ~4 ayı — 2026-03-01 sonrası — zaten forward-fill'dir;
     bu, S1b'nin nakit tahakkukunda da böyleydi, D5 için ek bir sapma yaratmaz ama
     kapının EN SON dönemdeki kararları bu ffill'e dayanır ve raporda işaretlenir.)*
  3. **Faiz serisinin kaynağı TCMB değil** (FRED/OECD rebroadcast; KALICI KAYIT 6b) +
     2023'te 9 aylık ff boşluğu + EVDS ile ~2-6 puanlık sistematik seri-tanım farkı
     (`EVDS_COMPARISON.md`). Kapı **eşik** olarak bu seriyi kullandığı için, tahakkuktan
     farklı olarak, seri-tanım farkı **karar sınırını kaydırabilir** — duyarlılık
     raporda tartışılır.

---

## 6. BENCHMARK-REFERANSI KİLİDİ (E4 §4 / D2US §5 / D4US §5 emsali)

1. **Yukarıdaki (§1-§3) mühürlü tablo, eşikler ve TASARIM PAKETİ AYNEN geçerlidir.**
   Yeniden mühürleme, benchmark değişikliği, eşik ayarı veya bileşen seçimi YOKTUR.
2. **Benchmark referansı D1 olarak kalır.** Sonuç görüldükten SONRA "referansı sepete /
   XU100'e / faize çevirelim" türü değişiklik **kriter-alışverişidir (criterion-shopping)**
   ve D5 için bu turda ve GELECEK turlarda **YASAKTIR**.
3. **Karar kuralı (önceden):** 4 kriterin TAMAMI → **ADAY**; herhangi biri kalırsa **RED**.
4. **Grid/varyant seçimi YASAK:** bu spike TEK mühürlü paketi ölçer. Komşuluk (§5e) ve
   MC (§5f) ölçülür ama **karar onlara göre alınmaz**.
5. **İkinci ölçüm-bakışı YOK** (§0.4). BIST tarihçesine D5 bakış sayacı: **1 kullanılır.**

*Mühür sonu. Bu dosyadaki hiçbir eşik/sabit strateji sonucuna göre değiştirilemez.
Spike koşumu (madde 2) bu commit'ten SONRA yapılır.*

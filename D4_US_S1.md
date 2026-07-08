# D4_US_S1.md — Varlık-Sınıfı ETF Dual-Momentum (D4-US) Spike Değerlendirme Raporu

**Tur:** D4US-S1 (varlık-sınıfı ETF dual-momentum ailesi tasarım + spike). **Tarih:**
2026-07-08. **Tür:** offline araştırma spike'ı — üretim implementasyonu DEĞİL. **Karar:**
yok (HÜKÜM YOK — kabul/red kullanıcının/baş danışmanın; bu rapor yalnız mekanik girdi).

> **İzolasyon (E4/D2US emsali, korundu):** `mode: paper` + TÜM canlı bot modülleri
> (strategy/regime_core.py, execution/, safety/, data/live_*, notify/, main.py,
> config/config.yaml, config/regime_core.yaml) + S1/S1b/E4/D2US araçları
> (backtest/regime_core*.py, backtest/xsec_momentum.py, tools/run_regime_core*.py,
> tools/e4_common.py, tools/run_xsec_momentum_us2.py, config/regime_core*.yaml,
> config/momentum_us2.yaml) DEĞİŞTİRİLMEDİ. Yeni aile BAĞIMSIZ modülde
> (backtest/dual_momentum_etf.py) — `costs/` + `data/cleaning.py` +
> `e4_common`/`run_regime_core` fonksiyonları YALNIZ import edilerek yeniden kullanıldı
> (değişmeden → drift imkânsız). BIST v7.1-golden her commit 3/3 bayt-bayt. Grid/varyant
> SEÇİMİ YOK — tasarım TEK paket olarak koşumdan ÖNCE mühürlendi (D4US_CRITERIA.md).

---

## 0. Veri Envanteri + Survivorship (KARARDAN ÖNCE)

**Evren:** 10 varlık-sınıfı ETF (SPY IWM EFA EEM VNQ TLT IEF LQD GLD DBC), kimlik
`longName`+`quoteType` ile doğrulandı (10/10; US3 dersi), `data/snapshots/etf_us/2026-07-08/`
(dondurulmuş, manifest sha256 `5e80ada2…`). **TOTAL-RETURN** (auto_adjust=True; tahvil
ETF'lerinde fiyat-only ciddi hata). Kapsam: 9 ETF 2005-01-03'ten, **DBC 2006-02-06'dan**
(en geç başlayan → kompozit t0'ı bağlar); kompozit **2006-02-06 → 2026-07-08, 5136 gün**,
**0 hayalet-bar / 0 forward-fill / 0 sıçrama** (ETF'ler diversifiye → tek-isim şoku yok).
Strateji ilk-sinyali (t0 + 12 ay formation) ≈ 2007-02. Tam denetim: **DATA_AUDIT_ETF.md**.

**✅ Survivorship YAPISAL olarak küçük (D2/E4'ten temel FARK):** D1-US ve D2-US mühürlü
referansları (US-hisse sepetleri) survivorship-şişirilmişti (iflas eden 2005 firmaları
evrende yok → gerçek-üstü yüksek çıta). **D4-US'te bu yapısal olarak çok daha küçüktür:**
bir varlık SINIFI "iflas etmez" (SPY = US hisse piyasasının kendisi, TLT = uzun Hazine,
GLD = altın); eşit-ağırlık 10-ETF sepeti GERÇEKTEN yatırılabilir, dürüst bir çıtadır.
Hafif ETF-düzeyi survivorship (bu 10, sınıflarının bugün baskın fonları) mevcut ama
niceliksel olarak zayıf ve YÖNSÜZ (bir sınıfın getirisi, o sınıfı temsil eden fonun
kapanmasından bağımsızdır). Bu, D4-US'in D2 Ders-2'ye getirdiği yapısal iyileşmenin
çekirdeğidir (bilinen sorun #13 bu evren-sınıfında büyük ölçüde kapanır). Tam-titizlik:
point-in-time/kapanan-fon dahil ETF metodolojisi bu turun kapsamı DIŞINDA (§10'da çekince).

---

## 1. Mühürlü Tasarım Paketi (D4US_CRITERIA.md §1 — özet)

**12-0 momentum** (formation 12 ay, SON AY ATLANMAZ — varlık-sınıfı literatürü
Faber/Antonacci varsayılanı, tek-hisse 12-1 kısa-vadeli-tersine-dönüşünün karşıtı) ·
aylık rebalans (ay-sonu sinyal → **t+1** kapanış yürütme) · göreli momentum: 10 ETF'ten
**TOP-3**, eşit ağırlık 1/3 · pozisyon-bazlı **mutlak-momentum nakit kapısı** (12-0 ≤
T-bill formation-penceresi getirisi → slot nakit; ham DGS3MO, ACT/365) → göreli + mutlak =
"dual momentum" (Antonacci) · **VOL-HEDEFLEME YOK (Ders-1)** · kaldıraç YOK · US CostModel
devir · nakit DGS3MO−50bp · LONG-only. **Tasarım literatür varsayılanlarıyla, koşumdan
ÖNCE, tarama YAPILMADAN mühürlendi** (D4US_CRITERIA.md, ayrı commit — strateji kodundan önce).

---

## 2. Benchmark (D4US_CRITERIA.md §2 — mühürlü, strateji koşulmadan)

| Benchmark | CAGR | Max DD | Sharpe (√252) | OOS aylık-Sharpe | OOS max DD |
|---|---|---|---|---|---|
| **Eşit-ağırlık 10-ETF sepeti al-tut** (MÜHÜR REFERANSI, maliyetsiz, total-return) | **+6.696%** | **-34.53%** | **0.6164** | **0.5796** | -26.30% |
| SPY al-tut (endeks proxy, BİLGİLENDİRİCİ, total-return) | +11.10% | -55.19% | 0.6428 | 0.8209 | -39.80% |

- OOS: 36 walk-forward penceresi (train=24ay/test=6ay/step=6ay, S1b şablonu), 216 OOS ayı.
- **D2/E4'ün AKSİNE sepet SPY'ı GEÇMİYOR** (CAGR 6.70% < 11.10%; dengeli çok-varlık portföyü
  2006-2026 US-hisse-baskın dönemde tahvil/emtia tarafından sürüklendi) ama DD çok daha sığ.
  Bu, çıtayı gerçek-üstü YAPMAZ — **dürüst/yatırılabilir bir bar'dır** (survivorship'siz).

---

## 3. MÜHÜRLÜ TABLO — MEKANİK SONUÇ (referans = eşit-ağırlık 10-ETF sepeti)

> Bu tablo `D4US_CRITERIA.md` §3'ün mekanik doldurmasıdır — HÜKÜM DEĞİL. Kabul kuralı
> önceden mühürlendi: **1+2+3a+3b TAMAMI geçerse US-kabul ADAYI; herhangi biri kalırsa
> red — "dar fark" YOK.**

| # | Kriter | Mühürlü eşik | Strateji | Sonuç |
|---|---|---|---|---|
| **1** | USD Sharpe > sepet Sharpe | > 0.6164 | **0.5462** | **FAIL** |
| **2** | CAGR > sepet CAGR (getiri-arayan varlık şartı) | > 6.696% | **6.667%** | **FAIL** |
| **3a** | OOS aylık-Sharpe > sepet OOS aylık-Sharpe | > 0.5796 | **0.3987** | **FAIL** |
| **3b** | Tam-dönem \|maxDD\| ≤ sepet \|maxDD\| | ≤ 34.53% | **25.72%** | **PASS** |

→ **1/4 geçti (yalnız 3b).** `all_4_pass = False`. **Önceden mühürlenen kurala göre D4-US,
US-referansta kabul adayı DEĞİLDİR** — bu Claude Code'un hükmü değil, kullanıcının koyduğu
kuralın MEKANİK sonucudur. **Nihai kayıt kullanıcının/baş danışmanın.** (Dikkat: kriter 2
0.03 puanla kaldı — ama "dar fark" mühürlü kuralda YOKTUR; FAIL, FAIL'dir.)

---

## 4. Ana Koşum + Risk (tam dönem, mühürlü tam paket)

- **CAGR +6.667%**, toplam getiri +273.4%, **Sharpe 0.5462**, **max DD -25.72%**, 233 aylık
  rebalans. Nihai equity 373,449 (100k'dan). Ortalama yatırılan slot **2.84/3** (kapı
  nadiren tetikliyor — mean nakit-slot **0.16**; varlık-sınıfı momentumu genellikle
  T-bill üstü ≥3 varlık buluyor).
- **OOS (36 pencere, 216 ay):** aylık-Sharpe 0.3987, max DD -24.73%.
- **Monte Carlo (aylık getiri permütasyonu, seed=42, 500 koşu):** dd_p5 **-38.67%**, medyan
  -26.57%, p95 -18.78%. (dd_p5 gözlenen maxDD'den DERİN — tail permütasyonları; gözlemsel.)
- **En derin 5 drawdown epizodu:** 2008-07→11 **-25.72%** (GFC, global maks, toparlanma
  2010-04); 2011-04→2012-03 -20.55% (Euro krizi); 2018-01→12 -20.44% (yavaş toparlanma
  2021'e); 2022-04→2023-10 -19.88% (faiz şoku); 2015-01→2016-12 -18.65% (emtia/EM).
  (≥%10 epizot: 9 adet.) **Tüm epizotlar sepetin -34.5% maksından SIĞ** — savunmacı profil.

---

## 5. (a) Kriz Epizotları — GFC 2008-09, COVID 2020, 2022 (hisse+tahvil)

Varlık-sınıfı dual-momentumun ASIL tezi burada test edilir: kriz rejimlerinde en güçlü
varlık sınıfına (genellikle güvenli liman) rotasyon. **D4-US bu testi büyük ölçüde GEÇTİ
(sermaye-koruma):**

| Pencere | Strateji | Sepet | Fark | Strateji davranışı (tutulan varlıklar) |
|---|---|---|---|---|
| **GFC 2008-01→2009-06** | **-8.0%** | **-18.5%** | **+10.5pp** | GLD/TLT/IEF/DBC'ye rotasyon (güvenli liman: altın, Hazine); mean nakit 0.28 |
| 2009 rebound (03-09→12-31) | +11.3% | +34.0% | -22.7pp | hâlâ TLT/IEF/GLD/LQD (savunmada); keskin hisse toparlanmasını GECİKMELİ yakaladı |
| **COVID 2020-02-19→08-31** | **+5.0%** | **+2.5%** | **+2.5pp** | GLD/TLT/IEF (defansif); pencere-içi DD -15.1%; kapı tetiklemedi (bonolar pozitif momentum) |
| **2022 (hisse+tahvil ortak düşüş)** | **-4.7%** | **-17.0%** | **+12.3pp** | **DBC (emtia — 2022'de yükselen tek sınıf)/VNQ/SPY/GLD'ye rotasyon**; mean nakit 1.17 |

**Yorum (mekanik, hüküm değil):** D2-US'in AKSİNE (savunma katmanları toparlanmayı
kaçırıp getiriye zarar vermişti), D4-US'in varlık-sınıfı rotasyonu üç büyük krizde de
(GFC, COVID, 2022) sepetten ANLAMLI daha az kaybetti — **özellikle 2022'de** (hem hisse
hem tahvilin düştüğü nadir yıl), DBC/emtiaya rotasyon kaybı sepetin dörtte birine indirdi.
Bu, "dual-momentum tezi çalışıyor" kanıtıdır (sermaye-koruma). BEDELİ: 2009 gibi keskin
dip-dönüşlerinde savunma pozisyonlarından çıkış gecikmeli (+11% vs +34%) → getiri-arayan
kritere (1, 2, 3a) zarar. Yani D4-US **gerçek bir savunmacı rotasyon** ama getirisi sepeti
GEÇMİYOR — düşüşü keser, yukarıyı tam yakalamaz, net CAGR ~sepetle eşit.

---

## 6. (b) Turnover + Maliyet Sürüklemesi

- **Ortalama yıllık turnover: 4.84×** (484%/yıl); ortalama aylık devir 0.42. Yıllara göre
  2.1×–10.4× (dip yıllar 2014/2022 düşük; rotasyon-yoğun 2011/2019 yüksek).
- **Maliyet sürüklemesi: ~26 bps/yıl** (sıfır-maliyet karşı-olgusu: CAGR 6.925% → 6.667%,
  Δ=25.8 bps; ort-equity yöntemi 24.4 bps). Toplam $ maliyet ~9,284.
- **Yorum:** US komisyonsuz + ETF'lerin dar spread'i + 5bps slippage sayesinde 484%
  turnover'a RAĞMEN maliyet ILIMLI (~26bps/yıl). **Zayıf risk-ayarlı sonuç maliyet kaynaklı
  DEĞİL** — devir maliyeti stratejinin sepet-altı Sharpe'ını açıklamıyor (ana sürücü §10).

---

## 7. (c) Ablasyon — YALNIZ BİLGİ/ATIF (bileşen SEÇİMİ YAPILMAZ)

> Kabul YALNIZ tam pakete (V1) uygulanır. Aşağıdaki tablo kapının marjinal etkisini
> ŞEFFAF gösterir; bir bileşeni "seçmek" için DEĞİL (disiplin #3).

| Varyant | CAGR | Max DD | Sharpe |
|---|---|---|---|
| V0 yalın top-3 (kapısız) | 7.16% | -25.71% | **0.565** |
| **V1 +mutlak-kapı (MÜHÜRLÜ)** | 6.67% | -25.72% | 0.546 |

**Gözlem (mekanik):** mutlak-momentum kapısı bu ÖRNEKLEMDE Sharpe/CAGR'ı hafif DÜŞÜRÜYOR
(0.565→0.546; 7.16%→6.67%) — çünkü kapı nadiren tetikliyor (mean 0.16 slot) ve tetiklediğinde
(ör. 2022) nakde geçip varlığın sonraki toparlanmasını kısmen kaçırıyor; max DD neredeyse
değişmiyor. **KRİTİK NOT (seçim değil, dürüstlük):** kapısız V0 (0.565) BİLE kriter 1'i
(0.6164) geçmiyor → bileşen cherry-pick'i kabul/red sonucunu DEĞİŞTİRMEZDİ. Karar tek bir
katmanın hassas ayarına bağlı DEĞİL (D2US ile aynı disiplin-bulgusu).

---

## 8. (d) Komşuluk — GÖZLEMSEL (seçim aracı değil)

| Boyut | Değerler → Sharpe (CAGR, maxDD) |
|---|---|
| formation ay | 6 → 0.671 (8.68%, -23.6%) · **12 → 0.546 (6.67%, -25.7%)** |
| top-N | 2 → 0.379 (4.83%, -36.7%) · **3 → 0.546 (6.67%, -25.7%)** · 4 → 0.593 (6.82%, -19.3%) |

**Gözlem:** mühürlü nokta (formation 12 / top-3) komşularında UÇURUM YOK ama **komşuluğun
ZİRVESİ DE DEĞİL** — bu örneklemde formation-6 (0.671) ve top-4 (0.593) mühürlü noktadan
DAHA İYİ. Bu, **overfitting-karşıtı** güçlü bir işarettir: mühürlü 12-0/top-3 literatür
varsayılanıdır, sonuca göre SEÇİLMEDİ (seçilseydi 6/top-4'e giderdi). **Yapısal örüntü
(kritik, §10'a bağlanır):** top-N arttıkça (2→3→4) Sharpe artıyor ve DD sığlaşıyor — yani
KONSANTRASYON (düşük top-N) bu evrende Sharpe'ı DÜŞÜRÜYOR; top-N → 10'a giderken strateji
sepete yakınsar. Diversifiye varlık-sınıfı evreninde momentum-konsantrasyonu, çeşitlendirmeyi
kaybettirdiği kadar zamanlama-edge'i eklemiyor.

---

## 9. Bağlam (BİLGİLENDİRİCİ — mühürlü değil, karar etkilenmez)

- **D1-US (E4b) + D2-US kıyası:** D1-US (rejim-filtre, 1/4) ve D2-US (kesitsel momentum,
  1/4) US-referansta KESİN reddedilmişti (KALICI KAYIT 16 + 19). **D4-US da mekanik 1/4** —
  ama YAPISAL FARK var: D1/D2 survivorship-şişirilmiş HİSSE sepetinin altında kaldı; D4-US
  DÜRÜST/yatırılabilir sepeti CAGR'da neredeyse yakaladı (6.667% vs 6.696%) ve DD'yi sepetin
  ~%75'ine indirdi — yani "yapısal-imkânsız" değil, "risk-ayarlı olarak yetersiz". Üç aile de
  aynı headline (1/4) ama D4-US en yakın ve en savunmacı olanı.
- **SPY kıyası (referans DEĞİL — E4/D2US §4 kilidi: SPY'a geçiş YASAK):** D2-US SPY'ı
  Sharpe'ta geçmişti; **D4-US GEÇMİYOR** (0.546 < 0.643) ve CAGR'da çok altında (6.67% vs
  11.10%) — ama DD'de çok daha sığ (-25.7% vs -55.2%). D4-US, SPY'a karşı düşük-getiri/
  düşük-risk bir profil; **mühürlü referans SEPET, değiştirilemez** (kriter-alışverişi yasak).

---

## 10. ⚠ ÖRNEKLEM + Survivorship UYARISI (KARARDAN ÖNCE — disiplin #6)

1. **Survivorship (tekrar, §0):** D2/E4'ün aksine bu evrende yapısal olarak KÜÇÜK
   (varlık sınıfı iflas etmez) → sepet çıtası dürüst/yatırılabilir. Hafif ETF-düzeyi seçim
   etkisi var ama yönsüz; tam point-in-time/kapanan-fon ETF metodolojisi ayrı bir turdur.
2. **Diversifiye evren + yüksek çıta:** kesitsel momentum GENİŞ/dağınık evrende (D2 dersi)
   zayıftı; D4 bunu varlık-SINIFI evreniyle yanıtladı ama **yeni bir yapısal engel** ortaya
   çıktı: referans zaten çok-varlık diversifiye bir portföy (eşit-ağırlık 10-sınıf), bu
   yüzden top-3'e KONSANTRE olmak çeşitlendirmeyi kaybettiriyor (§8: top-N↑ → Sharpe↑).
   Klasik dual-momentum literatürü (Antonacci GEM) çoğunlukla SPY veya 60/40'ı geçer;
   eşit-ağırlık TÜM-varlık sepetini risk-ayarlı geçmek çok daha zordur.
3. **2015-sonrası momentum zayıflaması (literatür endişesi):** varlık-sınıfı/trend
   momentumunun canlı performansı 2015 sonrası belirgin zayıfladı (düşük-vol/QE rejimi);
   klasik backtest edge'inin büyük kısmı pre-2009 + 2008 kaçınmasından gelir. 2006-2026
   örneklemi bu zayıf dönemi ağırlıklı içeriyor → sonuç dönem-duyarlı.
4. **Örneklem/olay adedi:** ~19 yıl (2006-02'den), **233 aylık rebalans**, 2-3 büyük kriz
   rejimi (GFC, COVID, 2022). Sharpe/CAGR farkları birkaç kriz epizoduna duyarlı; OOS (36
   pencere) bunu bir ölçüde hafifletir ama aynı krizleri paylaşır. **DBC (emtia) 2006'da
   başladığı için ~13 ay daha kısa tarihçe** (veri sınırı, seçim değil).
5. **Tek örneklem, tek evren, tek tasarım:** bu bir SPIKE'tır (üretim değil). Farklı
   rebalans (kademeli/haftalık), farklı top-N (§8: 4 daha iyiydi ama SEÇİLMEZ), veya kaldıraçlı
   risk-parite HİÇBİRİ bu turda test EDİLMEDİ ve grid/varyant seçimi YASAK olduğu için
   edilMEYECEK. Kabul yalnız MÜHÜRLÜ tam pakete dairdir.
6. **Ölçüm TAM, ikinci-bakış YOK:** maliyet + nakit + OOS + MC bu tek turda dahildir →
   E4b-tarzı ikinci ölçüm-bakışı bu aile için YOKTUR (D4US_CRITERIA.md §3, koşumdan önce
   mühürlü). Her yeniden-koşum tasarım değişikliği sayılır.

---

## 11. Kapanış (HÜKÜM YOK)

**Mekanik sonuç:** mühürlü 4-kriter tablosunda **1/4** geçti (yalnız 3b, tam-dönem maxDD).
Önceden mühürlenen kurala göre (`D4US_CRITERIA.md` §3/§5) bu, **D4-US ailesini US-referansta
bir kabul adayı YAPMAZ.** Bu bir HÜKÜM değil — kullanıcının koyduğu kuralın mekanik
uygulamasıdır.

Dürüst özet (mekanik, karar değil): D4-US, üç büyük krizde de (GFC -8% vs -18.5%; COVID
+5% vs +2.5%; 2022 -4.7% vs -17%) sepetten anlamlı daha az kaybederek GERÇEK bir savunmacı
varlık-sınıfı rotasyonu sergiledi (max DD sepetin ~%75'i, tüm ailelerin en sığı) ve dürüst/
yatırılabilir sepeti CAGR'da neredeyse yakaladı (6.667% vs 6.696%). Ama sepetin Sharpe
(0.6164), CAGR (6.696%) ve OOS Sharpe (0.5796) çıtalarının ALTINDA kaldı — çünkü diversifiye
bir varlık-sınıfı evreninde top-3'e konsantrasyon, çeşitlendirmeyi kaybettirdiği kadar
zamanlama-edge'i eklemiyor (§8: top-N↑ → Sharpe↑, sepete yakınsar) + varlık-sınıfı momentumunun
2006-2026'daki (özellikle 2015-sonrası) zayıflığı. Ana sürücü maliyet DEĞİL (~26bps/yıl).
Ablasyon, sonucun kapı katmanına bağlı olmadığını gösterdi (kapısız V0 bile kriter 1'i
geçmiyor); komşuluk uçurumsuz ve mühürlü nokta zirve değil (overfitting-karşıtı).

**Not (üç ailenin ortak örüntüsü — bilgilendirici):** D1-US, D2-US ve D4-US'in üçü de mekanik
1/4 ile aynı yerde durdu; ortak yapısal engel, US-referans kıyasında getiri-arayan kriterleri
(Sharpe/CAGR) survivorship'siz-ama-güçlü bir diversifiye referansa karşı geçmenin zorluğudur.
D4-US bu üçlü içinde referansa EN YAKIN ve EN SAVUNMACI olanıdır — bu bir kabul değil,
gelecekteki tasarım yönü için bilgilendirici bir gözlemdir (kararı kullanıcı/baş danışman verir).

**Karar (kabul / red / farklı-tasarım iterasyonu) kullanıcının/baş danışmanındır.** Bu turda
hiçbir eşik esnetilmedi, bileşen/varyant seçilmedi, canlı bot modülüne dokunulmadı; Faz 6 /
go_live / launchd / real adımı YOK. İki durma noktası kullanıcıda.

*Rapor sonu.*

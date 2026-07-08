# EXPANSION_E4.md — ABD ADİL TEST Raporu

> **Ne bu:** EXPANSION.md E-hattının E4 turu. İki amaç: **(A)** dondurulmuş
> 10-gate ailesinin ABD'de ADİL REFERANS testi (hüküm yok), **(B)** D1
> (regime_core) mantığının US sepetinde spike'ı — USD-cinsi sleeve'in temeli.
> **Offline araştırma.** `mode: paper` ve tüm canlı bot modülleri DOKUNULMADI;
> D1 parametreleri (N=200, b=%1, M=3) mühürlü ve AYNEN kullanıldı; BIST
> v7.1-golden her commit'te 3/3 bayt-bayt korundu.
>
> **Kabul kriterleri KOŞUMDAN ÖNCE mühürlendi** (`E4_CRITERIA.md`, ayrı commit
> `cdf8100`). Bu rapor mühürlü tabloyu MEKANİK doldurur — **kabul/red/iterasyon
> kararı kullanıcının/baş danışmanın; Claude Code hüküm vermez.**

Tarih/commit: 2026-07-08. Para birimi: **USD** (ABD sleeve'inin doğal/yerli
para birimi — "USD Sharpe" = stratejinin yerli Sharpe'ı).

---

## 1. VERİ ENVANTERİ + SURVIVORSHIP NOTU (ZORUNLU bölüm)

**Evren (20 sembol, 8 sektör):** AAPL MSFT INTC CSCO (IT) · JNJ PFE MRK (Sağlık)
· JPM BAC (Finans) · XOM CVX (Enerji) · PG KO WMT (Temel Tüketim) · HD MCD NKE
(Tüketici Takdiri) · DIS VZ (İletişim) · CAT (Sanayi).

- **Kaynak:** `data/snapshots/us/2026-07-06/` (DONDURULMUŞ, manifest sha256
  `932a7ebd…5014446c`; adapter `yf_us`, `auto_adjust=True`). E1 çıktısı,
  DATA_AUDIT_US.md.
- **Kapsam:** **2005-01-03 → 2026-07-02, 5408 işlem günü**, 20 sembolün tamamı
  tam/yinelenmesiz/monoton (0 FAIL). Kompozit temizliği: **0 hayalet-bar elendi,
  0 forward-fill** — US verisi temiz (BIST'in EREGL phantom / bedelli-sermaye
  kör-nokta deneyiminin ABD karşılığı yapısal olarak yok).
- **Veri yolu = S1b/BIST ile AYNI:** `data/cleaning.py::load_and_clean_universe`
  değiştirilmeden yeniden kullanıldı. `normalize_bist_dates`, US verisinde (tarih
  etiketleri zaten 00:00 UTC) **NO-OP'tur** — kanıt: `tests/test_e4_us.py::
  test_normalize_bist_dates_is_noop_on_us_00utc_data`. Yani US, S1b'nin geçtiği
  temizleme borusundan bit-bit aynı biçimde geçer.

**⚠ SURVIVORSHIP (HAYATTA KALMA) YANLILIĞI — bilinen ve KABUL EDİLEN sınırlama.**
Bu 20 sembol BUGÜN hâlâ büyük/likit oldukları için seçildi; 2005'te benzer
büyüklükte olup o tarihten bu yana küçülen, birleşen veya iflas eden şirketler
(Lehman Brothers, Washington Mutual, GM'in 2009 iflası, Kodak…) **evrene DAHİL
DEĞİL.** Sonuç: hem stratejinin hem de özellikle **eşit-ağırlık sepet
benchmark'ının** getirisi, gerçekte-mümkün-olandan İYİMSER. Bu turda özellikle
önemli çünkü **stratejiyi survivorship-şişirilmiş bir sepete karşı ölçüyoruz** →
sepet, olması gerekenden YÜKSEK bir kabul çıtası (bu yönüyle kriterler
muhafazakârdır: kolay geçilen bir çıta değil). Düzeltme (hayatta kalmayanları
içeren evren inşası) E4 kapsamı dışı; yorumlarken bu yanlılık akılda tutulmalı.

**Nakit bacağı KARARI (madde 1, mühürden ÖNCE sabitlendi): nakit getirisi = %0
(MUHAFAZAKÂR).** `data/snapshots/aux/`'ta yalnızca `USDTRY` + `TRY_ON_RATE` var;
mevcut bir US aux faiz serisi (FED effective / T-bill) YOK → kullanıcı
talimatının açık dalı gereği %0 alındı (sürücü `cash_rate=None` → S1b mekanizması
%0'da bayt-bayt "tahakkuk yok"; kanıt: `test_cash_rate_none_equals_all_zero_
series_byte_identical`). **Neden muhafazakâr:** gerçek US kısa faizi 2005-2026'da
>0 idi (ort ~%1.3, uzun ~%0 dönemleriyle) → stratejinin mutlak getirisini HAFİFE
alır (bir geçişi şişiremez); ayrıca sepet DAİMA yatırımda olduğundan %0 nakit,
Sharpe-vs-sepet kıyasında strateji ALEYHİNEdir. Gerçek T-bill/para-piyasası
serisiyle yeniden ölçüm kuyruğa alındı (TRY EVDS emsali).

---

## 2. BENCHMARK TABLOSU (strateji koşumundan ÖNCE hesaplandı — E4_CRITERIA.md'de mühürlü)

Deterministik/offline. İstatistikler `tools/run_regime_core.py`'den (S1b ile AYNI
fonksiyonlar). OOS: 38 walk-forward penceresi (train24/test6/step6 — S1b ile AYNI;
**parametre optimizasyonu YOK**).

| Benchmark | Toplam getiri | CAGR | Max DD | Sharpe | OOS aylık-Sharpe | OOS max DD |
|---|---|---|---|---|---|---|
| **Eşit-ağırlık US sepeti al-tut** (MÜHÜR REFERANSI) | +2,471.8% | **+16.31%** | **-46.28%** | **0.8561** | **0.9154** | **-29.93%** |
| SPY al-tut (endeks proxy, BİLGİLENDİRİCİ) | +817.5% | +10.86% | -55.19% | 0.6400 | 0.6555 | -41.99% |

SPY: dondurulmuş `data/snapshots/us_bench/2026-07-08/SPY.parquet` (sha256
`056d3780…443e914302`), strateji aralığına dilimlendi. **Dürüst gözlem:**
eşit-ağırlık sepet SPY'ı belirgin geçiyor (CAGR 16.31% vs 10.86%) — farkın büyük
kısmı **survivorship + eşit-ağırlık**. Kriterleri bu yüksek sepet çıtasına
koymak kabul bakımından ZORLU (muhafazakâr) bir seçimdir.

---

## 3. D1-US SPIKE + MÜHÜRLÜ KRİTERLERİN MEKANİK UYGULANMASI (item 4)

D1 mantığı US'te AYNEN: eşit-ağırlık kompozit, MA(200)×1.01 3-gün teyit ENTER /
×0.99 tek-gün EXIT, sinyal t kapanışı → yürütme **t+1 kapanış**, **US CostModel**
(commission=0, SATIŞTA SEC+TAF, slippage 5bps — `costs/us_equities.py`), nakit=%0.

**PARİTE KANITI:** yeni CostModel-döngüsü (`backtest/regime_core_us.py`), SİNYAL
kodunu (`build_composite`, `compute_regime_signal`) S1b modülünden yeniden
kullanır; BIST-eşdeğeri bir CostModel ile S1'in basit-bps modelini **~3e-15
göreli** yeniden üretir (anahtarlama BİREBİR). S1/S1b simülatörüne (backtest/
regime_core.py) DOKUNULMADI — auditör orada sıfır diff görür.

### D1-US ana koşum (tam dönem, cash=0%)

| Metrik | D1-US strateji | (bağlam) Eşit-ağırlık sepet | (bağlam) SPY |
|---|---|---|---|
| Toplam getiri | +443.3% | +2,471.8% | +817.5% |
| CAGR | +8.19% | +16.31% | +10.86% |
| Max drawdown | **-23.11%** | -46.28% | -55.19% |
| Sharpe (günlük, √252) | 0.726 | 0.856 | 0.640 |
| Anahtarlama sayısı | 57 | — | — |

En kötü 5 drawdown epizodu: -23.11% (2011-07-21→2011-12-19→2014-03-20), -20.39%
(2020 COVID), -20.20% (2022-2024 ayı), -19.31% (2007-2009 GFC), -15.41% (2010).
%10+ epizot: **7**.

### Monte Carlo (aylık getiri permütasyonu, 500 koşum, seed=42 — S1b yöntemi)

| dd_p5 (worst-5%) | dd_median | dd_p95 (best-5%) |
|---|---|---|
| **-33.52%** | -22.03% | -15.89% |

(Bilgi: D1 ailesinin BIST operasyonel breaker'ı ALARM -25% / FREEZE -40%. US için
mühürlü breaker YOK — üretim/paper turunun işi. dd_p5 -33.5% > -40% FREEZE eşiği,
< -25% ALARM eşiği.)

### Walk-forward OOS (strateji; param. optimizasyonu YOK)

38 pencere, 218 OOS ayı: **OOS aylık-Sharpe 0.669**, **OOS max DD -20.41%**.

### ⇒ MÜHÜRLÜ KABUL TABLOSU — MEKANİK (E4_CRITERIA.md, referans = sepet)

| # | Kriter | Mühürlü eşik | D1-US | Sonuç |
|---|---|---|---|---|
| **1** | USD Sharpe > sepet Sharpe | > 0.8561 | 0.726 | ❌ **FAIL** |
| **2** | Tam-dönem |maxDD| ≤ sepet |maxDD|/2 | ≤ 23.14% | 23.11% | ✅ **PASS** |
| **3a** | OOS aylık-Sharpe > sepet OOS | > 0.9154 | 0.669 | ❌ **FAIL** |
| **3b** | OOS |maxDD| ≤ sepet OOS |maxDD|/2 | ≤ 14.96% | 20.41% | ❌ **FAIL** |
| **4** | Komşuluk (N/b/M ±) uçurumsuz (SAĞLAMLIK) | — | uçurum YOK (aşağı) | ✅ (gözlemsel) |

**MEKANİK SONUÇ: 4 kabul kriterinden yalnız 1'i (kriter 2) GEÇTİ.** Önceden
belirlenen kurala göre ("4/4 geçerse US-kabul adayı; herhangi biri kalırsa
reddedilir — dar-fark/üçüncü-bakış YOK"): **D1-US bu turda US-referansta kabul
adayı DEĞİL.** Bu bir HÜKÜM değil, mühürlü eşiklerin mekanik uygulanmasıdır.

**Kriter 4 — uçurum kontrolü (SAĞLAMLIK, seçim aracı DEĞİL):** N∈{150,200,250},
b∈{0,%1,%2}, M∈{1,3,5} komşuluğunda Sharpe 0.66–0.82, maxDD -20%…-28% arasında
SÜREKLİ değişiyor — uçurum yok. Dikkat çekici: **mühürlü nokta (200/%1/3,
Sharpe 0.726) komşuluğunun ALT tarafında** (bazı komşular 0.78-0.80) — yani
parametreler US'e göre optimize EDİLMEDİ (BIST'ten donduruldu); US'te "tepe"
değil, düz bir iç noktadalar. Bu, overfitting-KARŞITI bir gözlemdir.

---

## 4. 10-GATE ADİL REFERANS (item 3 — RAPOR-ONLY, kabul kapısı DEĞİL)

Dondurulmuş 10-gate huni (`config/config.yaml` signal/risk eşikleri AYNEN),
US evreninde, US maliyetiyle (SEC/TAF ~0.3bps 10-gate motor yolunda modellenmez —
ihmal edilebilir). 10-gate ailesi BIST'te KALICI KAYIT 3 ile reddedildi + donduruldu.

| Metrik | 10-gate (US) | (bağlam) sepet al-tut | (bağlam) SPY |
|---|---|---|---|
| Toplam getiri | **-2.27%** | +2,471.8% | +817.5% |
| CAGR | -0.11% | +16.31% | +10.86% |
| Max drawdown | -7.61% | -46.28% | -55.19% |
| Sharpe | -0.089 | 0.856 | 0.640 |
| Win rate | 41.3% | — | — |
| Profit factor | 0.88 | — | — |
| Trade sayısı | 80 | — | — |
| Nakitte kalma % | **94.5%** | 0% | 0% |

**Dürüst referans:** 10-gate huni US'te de değer üretmiyor — 21 yılda ~düz-negatif
(CAGR -%0.11), negatif Sharpe, PF<1, süresinin %94.5'i nakitte (küçük -7.61% DD
yalnızca "katılmadığı" için, bir erdem değil). BIST'te reddedilen ailenin US'te
de zayıf davrandığının teyidi (STATUS bilinen-sorun #6 ile tutarlı). Bu bir
kabul kapısı değildir.

---

## 5. Grafikler + Bağlam (BİLGİLENDİRİCİ)

- `runtime/e4/regime_core_us_equity.png` (log equity: D1-US vs sepet vs SPY) ve
  `runtime/e4/regime_core_us_drawdown.png` (D1-US vs sepet DD + kriter-2 eşiği).
  Ephemeral/yeniden üretilebilir (`python -m tools.run_regime_core_us` +
  `python -m tools.e4_charts`; runtime/* gitignore). Grafik, D1-US'in SPY'a yakın
  bir nihai değere ulaşırken kriz dönemlerinde (2008-09 tamamen nakit, 2020 sığ)
  belirgin daha düşük drawdown yaptığını gösteriyor.

- **BIST-D1 (S1b) USD bağlamı** (REGIME_CORE_S1B.md (f), BİLGİLENDİRİCİ): BIST'te
  USD-terimde strateji Sharpe 0.435 < sepet 0.577 — yani **filtrenin risk-ayarlı
  Sharpe üstünlüğü USD terimde BIST'te de yoktu.** US'te aynı yapı: strateji
  Sharpe 0.726 < sepet 0.856. İki piyasada da tutarlı bir bulgu: **regime-filtre
  DRAWDOWN'ı büyük ölçüde kesiyor (sepetin ~yarısı) ama survivorship-şişirilmiş
  eşit-ağırlık sepetin Sharpe'ını GEÇMİYOR.**

---

## 6. ⚠ ÖRNEKLEM / ANAHTARLAMA-ADEDİ UYARISI (disiplin #6 — karar bölümünden ÖNCE)

- **Tek tarihçe, tek koşum, tek evren.** Sonuçlar 2005-2026'nın TEK gerçekleşmiş
  yoluna dayanır (out-of-sample yeni gelecek verisi değil, walk-forward dilimleri).
- **Anahtarlama azlığı:** D1-US tam dönemde **57** anahtarlama (~28 round-trip,
  21 yıl). İstatistiksel olarak ince — Sharpe/OOS farkları birkaç epizoda duyarlı.
- **Survivorship yanlılığı (bölüm 1)** hem stratejiyi hem sepeti yukarı çeker;
  net etki belirsiz ama sepet çıtası gerçek-üstü yüksek.
- **Nakit=%0** stratejinin mutlak getirisini hafife alır (gerçek T-bill >0).
- **SEC/TAF** 10-gate motor yolunda modellenmedi (D1-US'te modellendi).
- Bu uyarılar, aşağıdaki değerlendirmenin bir HÜKÜM değil, dürüst bir okuma
  olduğunu vurgular.

---

## 7. Dürüst çekinceler

1. Kriter 2'nin geçişi **razor-thin** (23.11% vs 23.14%, ~0.03 puan) — mühürlü
   kural "dar-fark" tanımaz (mekanik PASS), ama zaten kriter 1/3a/3b kaldığından
   genel sonuç değişmez; yine de bu marjın kırılganlığı kayda geçer.
2. OOS max DD (-20.41%) tam-dönem max DD'den (-23.11%) sığ ama sepet OOS'un
   YARISINDAN (-14.96%) derin — kriter 3b bu yüzden kaldı.
3. MC dd_p5 (-33.5%) tam-dönem gerçekleşenden (-23.1%) belirgin derin (permütasyon
   daha kötü sıralamalar üretiyor) — breaker kalibrasyonu için ham girdi, bu turda
   karar YOK.
4. Benchmark seçimi kriterleri belirler: sepete karşı FAIL olan Sharpe, SPY'a
   karşı GEÇERDİ (0.726 > 0.640) — ama mühürlü referans SEPETtir (talimat madde 2)
   ve mühür ESNETİLEMEZ. Bu, "başarı"nın referansa göre değiştiğinin kaydıdır.

---

## 8. Benim (Claude Code) değerlendirmem — DÜRÜST, ama KARAR KULLANICININ

Mekanik sonuç net: **D1-US, mühürlü 4-kriter tablosunu geçmiyor (1/4).** Tek
geçen, drawdown-yarılama (kriter 2) — ki bu D1 ailesinin ASIL vaadidir (sermaye
koruma) ve US'te de tutuyor: filtre, sepetin -46% düşüşünü ~-23%'e indiriyor,
2008-09'da tamamen nakde geçiyor. Ama **risk-ayarlı getiri (Sharpe) tarafında,
survivorship-şişirilmiş eşit-ağırlık US sepetini geçemiyor** — hem tam dönemde
hem OOS'ta. Bu, BIST-USD'de (S1b) gözlenen yapının BİREBİR tekrarı: filtre
drawdown'da kazanıyor, USD-Sharpe'ta sepete kaybediyor.

Yorum (hüküm değil): (a) sepet çıtası survivorship + eşit-ağırlıkla gerçek-üstü
yüksek; gerçek dünyada bir yatırımcı bu ideal sepeti kuramazdı, dolayısıyla
"sepeti geçemedi" sonucu pratik başarısızlıkla eşdeğer OKUNMAMALI. (b) Buna
rağmen mühürlü kural mühürlüdür — bu turda D1-US US-kabul adayı DEĞİL. (c) SPY'a
(gerçekçi, kurulabilir bir endeks) karşı D1-US Sharpe'ı GEÇİYOR (0.726 vs 0.640)
ve drawdown'u çok daha sığ — bu, ileride bir yeniden-tasarım turunun "referansı
SPY yapalım mı?" sorusunu (mühürleme öncesi, ayrı onayla) gündeme getirebileceği
bir bulgudur; ama bu turda referans SEPETtir ve değiştirilemez.

**Nihai kabul/red/iterasyon kararı kullanıcının/baş danışmanın.** Bu turda
hiçbir eşik/parametre değiştirilmedi, hiçbir varyant seçilmedi, canlı bot
modüllerine dokunulmadı; iki durma noktası aynen kullanıcıda. E4 sonrası "US
gölge paper" ve "E3" adımları AYRI onaylar gerektirir (KALICI KAYIT 14).

---

### Tekrarlanabilirlik
```
python -m tools.run_regime_core_us     # D1-US + benchmark + OOS + MC + cliff + mühürlü tablo
python -m tools.run_tengate_us         # 10-gate adil referans
python -m tools.e4_charts              # equity + DD grafikleri
python -m pytest tests/test_e4_us.py -q # 6 test (parite/determinizm/%0-nötr/no-op/SEC-TAF/regresyon)
```
Çıktılar: `runtime/e4/regime_core_us/summary.json`, `runtime/e4/tengate_us/summary.json`.
Snapshot'lar dondurulmuş (sha256 manifest); nakit=%0 → deterministik.

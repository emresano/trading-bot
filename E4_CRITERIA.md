# E4_CRITERIA.md — MÜHÜRLÜ Kabul Kriterleri (US ADİL TEST, D1-US)

> **Bu dosya bir SÖZLEŞMEDİR.** Aşağıdaki kabul tablosu ve sayısal eşikler, D1
> (regime_core) ailesinin ABD evrenindeki spike'ı KOŞULMADAN ÖNCE, yalnızca
> benchmark (al-tut) verisinden mekanik olarak türetilerek mühürlenmiştir.
> **Commit sonrası ESNETİLEMEZ — "dar farkla geçti/geçmedi" diye bir kategori
> YOKTUR.** Strateji sonucu bu eşiklere MEKANİK olarak uygulanır; kabul/red/
> iterasyon kararı kullanıcının/baş danışmanın (Claude Code hüküm vermez).
>
> Emsal: `REGIME_CORE_S1B.md` (BIST-D1'in mühürlü 4-kriter tablosu). Aynı
> yapı, ABD evrenine uyarlanmış — tek fark: BIST'te tam-dönem kriter 1/2 XU100
> ENDEKSİNE karşıydı; burada **dört kriterin de referansı EŞİT-AĞIRLIK US
> SEPETİ al-tut'tur** (SPY endeks proxy'si yalnızca BİLGİLENDİRİCİ, kabul
> kapısı değildir). Bu, kullanıcının E4 talimatındaki kriter tanımının
> (madde 2) birebir uygulanmasıdır.

Mühür tarihi/commit: 2026-07-08 (bu dosyanın ilk commit'i). Para birimi: **USD**
(ABD sleeve'inin doğal/yerli para birimi — BIST'teki gibi ayrı bir çapraz-kur
çevrimi GEREKMEZ; "USD Sharpe" = stratejinin yerli Sharpe'ı).

---

## 0. Item 1 — Veri Envanteri + Nakit Bacağı Kararı (mühürlemeden ÖNCE sabitlendi)

**Evren (20 sembol, 8 sektör):** AAPL MSFT INTC CSCO JNJ PFE MRK JPM BAC XOM CVX
PG KO WMT HD MCD NKE DIS VZ CAT. Kaynak: `data/snapshots/us/2026-07-06/`
(manifest sha256 `932a7ebd…5014446c`). Kapsam: **2005-01-03 → 2026-07-02, 5408
işlem günü**, 20 sembolün tamamı tam/yinelenmesiz (DATA_AUDIT_US.md). Kompozit
hayalet-bar temizliği: **0 bar elendi, 0 forward-fill** (US verisi temiz;
BIST'in EREGL phantom deneyiminin US karşılığı yok).

**⚠ Survivorship (hayatta kalma) yanlılığı — bilinen ve KABUL EDİLEN sınırlama:**
Bu 20 sembol BUGÜN büyük/likit oldukları için seçildi; 2005'te mevcut olup o
tarihten bu yana küçülen/birleşen/iflas eden şirketler (Lehman, WaMu, GM 2009,
Kodak…) evrene DAHİL DEĞİL. Bu, benchmark'ı (özellikle eşit-ağırlık sepeti)
gerçekte-mümkün-olandan İYİMSER kılar → **sepet, olması gerekenden daha yüksek
bir kabul çıtasıdır** (kriterleri sepete karşı koymak bu yönüyle muhafazakârdır).
Tam detay EXPANSION_E4.md'nin ZORUNLU survivorship bölümünde.

**Nakit bacağı KARARI (madde 1): nakit getirisi = %0 (MUHAFAZAKÂR).**
`data/snapshots/aux/`'ta yalnızca `USDTRY` ve `TRY_ON_RATE` var; **mevcut bir
US aux faiz serisi (FED effective / T-bill) YOK.** Kullanıcı talimatının açık
dalı gereği ("yoksa nakit getirisi %0 + rapora muhafazakâr notu") nakit getirisi
%0 alınır (sürücü `cash_rate=None` geçer — S1b mekanizmasıyla bayt-bayt "tahakkuk
yok"). **Neden muhafazakâr:** (a) gerçek US kısa faizi 2005-2026'da >0 idi
(ortalama ~%1.3, uzun ~%0 dönemleriyle) → strateji mutlak getirisini HAFİFE
alır, bir geçişi ŞİŞİREMEZ; (b) sepet daima yatırımdadır (nakit dönemi yok),
dolayısıyla %0 nakit Sharpe-vs-sepet kıyasında strateji ALEYHİNEdir. Gerçek
T-bill/para-piyasası serisi kuyruğa alındı (TRY EVDS emsali, #18 benzeri).
**Bu seçim mühürden ÖNCE sabitlenmiştir ve değiştirilemez.**

---

## 1. Önceden hesaplanmış BENCHMARK metrikleri (strateji KOŞULMADAN)

Kaynak: `tools/e4_common.py::compute_benchmarks` (istatistikler
`tools/run_regime_core.py`'den — S1b ile AYNI fonksiyonlar). Deterministik/offline.

| Benchmark | Toplam getiri | CAGR | Max DD | Sharpe (günlük, √252) | OOS aylık-Sharpe | OOS max DD |
|---|---|---|---|---|---|---|
| **Eşit-ağırlık US sepeti al-tut** (MÜHÜR REFERANSI) | +2,471.8% | **+16.31%** | **-46.28%** | **0.8561** | **0.9154** | **-29.93%** |
| SPY al-tut (endeks proxy, BİLGİLENDİRİCİ) | +817.5% | +10.86% | -55.19% | 0.6400 | 0.6555 | -41.99% |

- SPY snapshot: `data/snapshots/us_bench/2026-07-08/SPY.parquet` (manifest sha256
  `056d3780…443e914302`), strateji/sepet aralığına dilimlendi.
- OOS: 38 walk-forward penceresi (train=24ay/test=6ay/step=6ay — S1b ile AYNI),
  225 OOS ayı. **Parametre optimizasyonu YOK** (N/b/M her pencerede sabit).
- **Dürüst gözlem (mühürden bağımsız):** eşit-ağırlık sepet, SPY'ı belirgin
  şekilde geçiyor (CAGR 16.31% vs 10.86%, Sharpe 0.856 vs 0.640) — bu FARKIN
  büyük kısmı survivorship + eşit-ağırlıktır. Kriterleri bu yüksek sepet çıtasına
  koymak, kabul bakımından ZORLU (muhafazakâr) bir seçimdir.

---

## 2. MÜHÜRLÜ KABUL TABLOSU (D1-US) — 4 kriter, referans = eşit-ağırlık US sepeti

> İşaret sözleşmesi: max DD **derinliği** = |max DD| (pozitif büyüklük). Kriter
> "derinlik ≤ eşik" biçiminde ifade edilir; işaretli karşılığı parantezde.

| # | Kriter | MÜHÜRLÜ eşik | PASS koşulu (mekanik) |
|---|---|---|---|
| **1** | USD Sharpe > sepet al-tut USD Sharpe | sepet Sharpe = **0.8561** | strateji Sharpe **> 0.8561** |
| **2** | Tam-dönem max DD derinliği ≤ sepet max DD derinliğinin YARISI | sepet |maxDD|=46.28% → yarısı **23.14%** | strateji |maxDD| **≤ 23.14%**  (yani maxDD ≥ **-0.231381**) |
| **3a** | OOS aylık-Sharpe > sepet OOS aylık-Sharpe | sepet OOS Sharpe = **0.9154** | strateji OOS aylık-Sharpe **> 0.9154** |
| **3b** | OOS max DD derinliği ≤ sepet OOS max DD derinliğinin YARISI | sepet OOS |maxDD|=29.93% → yarısı **14.96%** | strateji OOS |maxDD| **≤ 14.96%** (yani OOS maxDD ≥ **-0.149642**) |
| **4** | Komşuluk (N/b/M ±) uçurumsuz | — (yalnız SAĞLAMLIK) | 200/1%/3 komşularında performans UÇURUMU yok; **seçim aracı DEĞİL** |

**Kabul kuralı (S1b emsali, önceden belirlenmiş):** kriter 1, 2, 3a, 3b'nin
TAMAMI geçerse **aile US-kabul adayı**; herhangi biri kalırsa aile bu turda
US-referansta reddedilir — "üçüncü bakış / dar fark" YOK. Kriter 4 (uçurum)
bir SAĞLAMLIK kontrolüdür (mühürlü PASS/FAIL değil, gözlemsel). **Nihai karar
kullanıcının/baş danışmanın** — bu tablo yalnızca mekanik girdidir.

**10-gate satırı:** BİLGİLENDİRİCİ (dondurulmuş referans aile; BIST'te KALICI
KAYIT 3 ile reddedildi). Bir kabul KAPISI DEĞİLDİR — EXPANSION_E4.md'de yalnızca
"BIST'te reddedilen aile US'te nasıl davranıyor" dürüst referansı olarak raporlanır.

---

## 3. Bağlam (mühürlü değil, yalnızca karşılaştırma için — item 4'te doldurulur)

- **BIST-D1 (S1b) USD değerleri** kıyas için D1-US tablosuna BİLGİLENDİRİCİ
  eklenecek (S1b (f) bölümü: strateji USD Sharpe 0.435, sepet USD Sharpe 0.577
  — BIST'te USD-terimde filtre sepetten düşük Sharpe verdi). Bu, "başarı"
  tanımının para birimine göre değişebildiğinin kaydıdır; US için AYRI ölçülür.
- Örneklem/anahtarlama-adedi UYARISI (disiplin #6) EXPANSION_E4.md'de karar
  bölümünden ÖNCE yer alacak.

*Mühür sonu. Bu dosyadaki hiçbir eşik strateji sonucuna göre değiştirilemez.*

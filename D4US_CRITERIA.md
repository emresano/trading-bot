# D4US_CRITERIA.md — MÜHÜRLÜ Kabul Kriterleri + Tasarım Sabitleri (VARLIK-SINIFI ETF DUAL-MOMENTUM, D4-US)

> **Bu dosya bir SÖZLEŞMEDİR.** Aşağıdaki (a) tasarım paketi ve (b) kabul tablosu
> + sayısal eşikler, D4-US (varlık-sınıfı ETF dual-momentum) ailesinin spike'ı
> KOŞULMADAN ÖNCE, yalnızca benchmark (al-tut) verisinden ve varlık-sınıfı momentum
> literatürünün varsayılanlarından mekanik türetilerek mühürlenmiştir. **Commit sonrası
> ESNETİLEMEZ — "dar farkla geçti/geçmedi" YOKTUR; grid/varyant SEÇİMİ YOKTUR (tasarım
> TEK paket).** Strateji sonucu bu eşiklere MEKANİK uygulanır; kabul/red/iterasyon kararı
> kullanıcının/baş danışmanın (Claude Code hüküm vermez).
>
> Emsal: `D2US_CRITERIA.md` + `E4_CRITERIA.md` + `REGIME_CORE_S1B.md`. Referans
> **eşit-ağırlık 10-ETF sepeti al-tut**'tur (maliyetsiz, total-return); SPY endeks
> proxy'si yalnız BİLGİLENDİRİCİ. Para birimi: **USD** (US sleeve'in yerli para birimi;
> ayrı çapraz-kur çevrimi YOK — "USD Sharpe" = stratejinin yerli Sharpe'ı).

Mühür tarihi/commit: 2026-07-08 (bu dosyanın ve `config/dual_momentum_etf.yaml`'ın ilk
commit'i, HERHANGİ bir strateji koşumundan ÖNCE — commit sırası kanıttır:
`backtest/dual_momentum_etf.py` bu commit'te HENÜZ YOKTUR). Veri:
`data/snapshots/etf_us/2026-07-08/` (`manifest.json` sha256 `5e80ada2…260d935b`).

---

## 0. Item 1 — Veri Envanteri (mühürden ÖNCE dondurulmuş)

**Evren (10 varlık-sınıfı ETF, SABİT — ikame YASAK):** SPY IWM EFA EEM VNQ TLT IEF LQD
GLD DBC. Kimlik `longName`+`quoteType` ile doğrulandı (10/10, `identity.json`; US3 dersi).
Kapsam: 9 ETF **2005-01-03 →**, **DBC 2006-02-06 →** (evrenin en geç başlayanı, kompozit
t0'ı bağlar). Kompozit (eşit-ağırlık) **2006-02-06 → 2026-07-08, 5136 gün**, hayalet-bar
**0** / forward-fill **0**. Strateji ilk-sinyali (t0 + 12 ay formation) ≈ **2007-02**.
Tam denetim: DATA_AUDIT_ETF.md.

**TOTAL-RETURN (auto_adjust=True):** strateji VE sepet AYNI total-return seride;
tahvil ETF'lerinde (TLT/IEF/LQD) fiyat-only ciddi hata olurdu (kupon getirisi kaybolur).

**✅ Survivorship YAPISAL olarak küçük (D2/E4'ten temel fark):** referans sepet
GERÇEKTEN yatırılabilir bir 10-varlık-sınıfı portföyüdür; bir varlık SINIFI "iflas
etmez" → tek-hisse survivorship'inin şişirme mekanizması burada YOK. **Kabul çıtası
dürüst/uygulanabilir** (D2/E4'ün gerçek-üstü hisse sepetinin aksine). Hafif ETF-düzeyi
survivorship notu: DATA_AUDIT_ETF.md §4.

**Nakit bacağı KARARI:** US 3-aylık T-bill (FRED **DGS3MO**) − **50bp haircut** (E4b
serisi, dondurulmuş `data/snapshots/aux_us/2026-07-08/`, AYNEN reuse). r_net=max(rate−
haircut,0), ACT/365, NAKİT fraksiyonuna tahakkuk. Kapsam teyidi: DGS3MO first_obs
2005-01-03 < t0−12ay (2005-02-06) ✓. (Mutlak-momentum kapısı AYRI: ham DGS3MO, haircut
YOK — §1.5.)

---

## 1. MÜHÜRLÜ TASARIM PAKETİ (item 3) — literatür varsayılanları, TARAMA YOK

> Kaynak: `config/dual_momentum_etf.yaml::design`. Aşağıdakiler TEK paket olarak
> mühürlüdür; koşum sonucuna göre bileşen değiştirilmez/seçilmez. Ablasyon (item 4c)
> ve komşuluk (item 4d) YALNIZ bilgilendiricidir — **kabul yalnız tam pakete uygulanır.**

1.1 **Formation:** 12 ay, **SON AY ATLANMAZ → 12-0 momentum**. Ay-sonu kapanışlarla:
    rebalans ayı m[j] için formation getirisi = `close[m[j]] / close[m[j-12]] − 1`
    (tam 12-aylık span). j ≥ 12 gerekir (öncesi ısınma). **Pencere kararı (mühürlü):**
    son-ay-atlama (12-1) tek-hisse KISA-VADELİ TERSİNE-DÖNÜŞ olgusudur (Jegadeesh-Titman
    gap, tek-isim); varlık-sınıfı literatürünün (Faber "GTAA/GAA", Antonacci "GEM/Dual
    Momentum") varsayılanı **12-0**'dır — sonuçtan BAĞIMSIZ, koşumdan önce sabit.

1.2 **Rebalans:** aylık. Ay-sonu (son işlem günü) sinyal; işlem **SONRAKİ işlem günü
    KAPANIŞINDA** (t+1) yürütülür. Tutma sırasında ara rebalance YOK.

1.3 **Göreli momentum seçimi:** 10 ETF'ten formation getirisine göre **TOP-3**
    (deterministik: getiri, eşitlikte sembol adı). Ön-eleme/FIP YOK — evren zaten 10.

1.4 **Ağırlık:** eşit, her slot **1/top_n = 1/3**.

1.5 **Mutlak-momentum (dual-momentum) NAKİT kapısı — pozisyon bazlı:** seçilen 3 ETF'in
    HER BİRİ için, eğer **ETF'in 12-0 getirisi ≤ T-bill'in AYNI formation penceresi
    [m[j-12], m[j]] boyunca tahakkuk eden getirisi** ise o slot NAKİT kalır (yatırılmaz).
    T-bill oranı = **ham DGS3MO** (haircut YOK — sinyal eşiği, nakit-bacağı getirisi
    değil), ACT/365. Yatırılan slot sayısı < 3 olabilir; kalan nakit. Bu, göreli momentum
    (§1.3) + mutlak momentum (bu §) = "dual momentum"un (Antonacci) çekirdeğidir.

1.6 **Vol-hedefleme YOK (DERS-1):** D2'de (KALICI KAYIT 19) target_vol'ün sepet
    TAM-DÖNEM realize volünden türetilmesi hafif look-ahead'di → **bu pakette
    vol-hedefleme/kaldıraç katmanı HİÇ YOK.** Maruziyet her zaman ≤ 1 (yatırılan
    slotlar 1/3, gerisi nakit). Kaldıraç YOK.

1.7 **Yön:** LONG-only (short YOK — Bölüm 8/17 #10 emsali).

1.8 **Maliyet:** US CostModel (commission=0, SATIŞTA SEC+TAF, slippage 5bps) — rebalans
    devrine (turnover) uygulanır. **Nakit getirisi:** DGS3MO−50bp (§0), NAKİT fraksiyonuna
    (kapı-nakdi + top-3'ten az yatırım + yuvarlama artığı).

---

## 2. Önceden hesaplanmış BENCHMARK metrikleri (strateji KOŞULMADAN)

Kaynak: `tools/e4_common.py::compute_benchmarks` (istatistikler `tools/run_regime_core.py`'den
— S1b/E4/D2US ile AYNI fonksiyonlar; item 4 sürücüsü AYNI fonksiyonu yeniden çağırır →
drift imkânsız). Deterministik/offline. Ölçüm `runtime/d4us/benchmarks_sealed.json`.

| Benchmark | Toplam getiri | CAGR | Max DD | Sharpe (günlük, √252) | OOS aylık-Sharpe | OOS max DD |
|---|---|---|---|---|---|---|
| **Eşit-ağırlık 10-ETF sepeti al-tut** (MÜHÜR REFERANSI, maliyetsiz, total-return) | +275.5% | **+6.696%** | **-34.53%** | **0.6164** | **0.5796** | **-26.30%** |
| SPY al-tut (endeks proxy, BİLGİLENDİRİCİ, total-return) | +756.9% | +11.10% | -55.19% | 0.6428 | 0.8209 | -39.80% |

- Sepet: `build_composite` (S1b/E4/D2US ile AYNI) × 100000, maliyetsiz al-tut. SPY:
  AYNI `etf_us/2026-07-08/SPY.parquet` (total-return; ayrı us_bench snapshot'ı KULLANILMADI).
- OOS: **36 walk-forward penceresi** (train=24ay/test=6ay/step=6ay — S1b şablonu),
  **216 OOS ayı**. Pencere sayısı veriden türer (kompozit 2006-02'de başladığı için
  D2US'in 39'undan az). **Parametre optimizasyonu YOK.**
- **Dürüst gözlem (mühürden bağımsız):** D2/E4'ün AKSİNE sepet, SPY'ı GEÇMİYOR —
  CAGR'da (6.70% < 11.10%) ve Sharpe'ta (0.616 < 0.643) SPY'ın ALTINDA; çünkü sepet
  dengeli bir çok-varlık portföyüdür ve 2006-2026 (US-hisse baskın dönem) tahvil/emtia
  tarafından sürüklendi. Ama sepet DD'si çok daha sığ (-34.5% vs -55.2%). **Bu, çıtayı
  gerçek-üstü YAPMAZ — tersine dürüst/yatırılabilir bir bar'dır** (survivorship'siz).
  Bir dual-momentum stratejisinin bunu geçmesi, en güçlü varlık sınıflarına rotasyonla
  GERÇEK değer katmasını gerektirir (kolay değil, ama D1/D2'nin aksine yapısal-imkânsız
  da değil).

---

## 3. MÜHÜRLÜ KABUL TABLOSU (D4-US) — 4 kriter, referans = eşit-ağırlık 10-ETF sepeti

> **Getiri-arayan aile:** D4-US getiri hedefler → kriter 2 = **CAGR > sepet** bir VARLIK
> ŞARTIdır (D2 ile aynı yapı; D1/E4'te yoktu). İşaret sözleşmesi: max DD derinliği =
> |max DD| (pozitif büyüklük).

| # | Kriter | MÜHÜRLÜ eşik | PASS koşulu (mekanik) |
|---|---|---|---|
| **1** | USD Sharpe > sepet Sharpe | sepet Sharpe = **0.6164** | strateji Sharpe **> 0.6164** |
| **2** | CAGR > sepet CAGR (getiri-arayan varlık şartı) | sepet CAGR = **0.066957** | strateji CAGR **> 0.066957** (6.696%) |
| **3a** | OOS aylık-Sharpe > sepet OOS aylık-Sharpe | sepet OOS Sharpe = **0.5796** | strateji OOS aylık-Sharpe **> 0.5796** |
| **3b** | Tam-dönem \|maxDD\| ≤ sepet \|maxDD\| (al-tut'tan derin düşmemek) | sepet \|maxDD\| = **34.53%** | strateji \|maxDD\| **≤ 34.53%** (maxDD ≥ **-0.345309**) |
| **4** | Komşuluk (formation/top-N ±) uçurumsuz | — (yalnız SAĞLAMLIK) | mühürlü nokta komşularında UÇURUM yok; **seçim aracı DEĞİL** |

**Kabul kuralı (önceden belirlenmiş, sonuç görülmeden):** kriter **1, 2, 3a, 3b'nin
TAMAMI** geçerse **aile US-kabul ADAYI**; **herhangi biri kalırsa aile bu turda
US-referansta reddedilir** — "üçüncü bakış / dar fark" YOK. Kriter 4 (komşuluk) bir
SAĞLAMLIK gözlemidir (mühürlü PASS/FAIL değil). **Nihai karar kullanıcının/baş
danışmanın** — bu tablo yalnızca mekanik girdidir; Claude Code hüküm vermez.

**Ölçüm bu turda TAM** (maliyet + nakit + OOS + MC dahil): **E4b-tarzı ikinci ölçüm-bakışı
bu aile için YOKTUR** (D2 emsali — her yeniden-koşum tasarım değişikliği sayılır ve
varyant-seçimi yasağına girer). Bu, koşumdan önce mühürlüdür.

**Ablasyon (item 4c) ve komşuluk (item 4d):** YALNIZ BİLGİ/atıf. Bileşen SEÇİMİ
YAPILMAZ; kabul YALNIZ tam pakete (§1) uygulanır.

---

## 4. Bağlam (mühürlü değil, item 4'te doldurulur)

- **D1-US (E4/E4b) + D2-US kıyası:** D1-US (rejim-filtre) ve D2-US (kesitsel momentum)
  US-referansta mühürlü tablolarda **1/4** ile KESİN reddedildi (KALICI KAYIT 16 + 19).
  Her ikisi de survivorship-şişirilmiş US-hisse sepetini geçemedi. D4-US **AYRI bir
  ailedir** (varlık-sınıfı dual-momentum ≠ tek-hisse); D2 Ders-2'nin (evren genişliği)
  evren-SINIFI yanıtıdır. Kıyas D4_US_S1.md'de bilgilendirici.
- Örneklem/rebalans-adedi (~19 yıl ETF tarihçesi, ~230 aylık rebalans, 2-3 büyük kriz
  rejimi) + varlık-sınıfı momentumunun 2015-sonrası canlı-performans zayıflaması
  literatür endişesi + hafif ETF-düzeyi survivorship UYARISI (disiplin #6) D4_US_S1.md'de
  KARARDAN ÖNCE yer alacak.

---

## 5. BENCHMARK-REFERANSI KİLİDİ (E4 §4 / D2US §5 emsali — HERHANGİ bir koşumdan ÖNCE)

1. **Yukarıdaki (§0-§3) mühürlü tablo, eşikler ve TASARIM PAKETİ AYNEN geçerlidir.**
   Yeniden mühürleme, benchmark değişikliği, eşik ayarı veya bileşen seçimi YOKTUR.
2. **Benchmark referansı SEPET olarak kalır.** Sonuç görüldükten SONRA "referansı SPY
   yapalım" türü değişiklik kriter-alışverişidir (criterion-shopping) ve **D4-US için
   bu turda ve GELECEK turlarda YASAKTIR** — SPY'ın yalnız bilgilendirici olması kalıcı
   bir sınırdır. (Not: bu evrende sepet SPY'ın ALTINDA bir bar'dır — yani SPY'a geçmek
   kriter 2'yi ZORLAŞTIRIRDI; kilit yine de mutlaktır, avantaj/dezavantaj fark etmez.)
3. **Karar kuralı (önceden):** 4 kriterin (1, 2, 3a, 3b) TAMAMI geçerse D4-US **US-kabul
   ADAYIdır**; herhangi biri kalırsa **US-referansta reddedilir.** Kabul kararı yine
   kullanıcının/baş danışmanın.
4. **Grid/varyant seçimi YASAK:** bu spike TEK mühürlü paketi ölçer. Ablasyon (V0 yalın
   top-3 → V1 +kapı = mühürlü) ve komşuluk ölçülür ama karar onlara göre alınmaz.

*Mühür sonu. Bu dosyadaki hiçbir eşik/sabit strateji sonucuna göre değiştirilemez.
Spike koşumu (item 4) bu commit'ten SONRA yapılır.*

# D2US_CRITERIA.md — MÜHÜRLÜ Kabul Kriterleri + Tasarım Sabitleri (KESİTSEL MOMENTUM, D2-US)

> **Bu dosya bir SÖZLEŞMEDİR.** Aşağıdaki (a) tasarım paketi ve (b) kabul tablosu
> + sayısal eşikler, D2-US (kesitsel momentum) ailesinin spike'ı KOŞULMADAN ÖNCE,
> yalnızca benchmark (al-tut) verisinden ve literatür varsayılanlarından mekanik
> türetilerek mühürlenmiştir. **Commit sonrası ESNETİLEMEZ — "dar farkla geçti/
> geçmedi" YOKTUR; grid/varyant SEÇİMİ YOKTUR (tasarım TEK paket).** Strateji
> sonucu bu eşiklere MEKANİK uygulanır; kabul/red/iterasyon kararı kullanıcının/
> baş danışmanın (Claude Code hüküm vermez).
>
> Emsal: `E4_CRITERIA.md` (D1-US mühürlü tablo) + `REGIME_CORE_S1B.md`. Referans
> **eşit-ağırlık US2 sepeti al-tut**'tur (maliyetsiz); SPY endeks proxy'si yalnız
> BİLGİLENDİRİCİ. Para birimi: **USD** (US sleeve'in yerli para birimi; ayrı
> çapraz-kur çevrimi YOK — "USD Sharpe" = stratejinin yerli Sharpe'ı).

Mühür tarihi/commit: 2026-07-08 (bu dosyanın ve `config/momentum_us2.yaml`'ın ilk
commit'i, HERHANGİ bir strateji koşumundan ÖNCE). Veri: `data/snapshots/us2/2026-07-08/`
(manifest sha256 `7f34c669…a3032b34`).

---

## 0. Item 1 — Veri Envanteri (mühürden ÖNCE dondurulmuş)

**Evren (50 sembol, 10 GICS sektörü):** DATA_AUDIT_US2.md. Kapsam **2005-01-03 →
2026-07-08, 5411 işlem günü**, 50 sembolün TAMAMI tam/yinelenmesiz; kompozit
hayalet-bar temizliği **0 bar / 0 forward-fill**. E4 US evreni (20) korundu, +30 yeni.

**⚠ Survivorship yanlılığı (bilinen, KABUL EDİLEN):** bu 50 sembol bugün likit
oldukları için seçildi; delisting/iflas eden 2005 firmaları evrende YOK →
**eşit-ağırlık sepet gerçek-üstü yüksek bir kabul çıtasıdır** (kriterleri sepete
koymak muhafazakâr). Kesitsel-momentuma özgü nüans + tam gerekçe: DATA_AUDIT_US2.md §2.

**Nakit bacağı KARARI:** US 3-aylık T-bill (FRED **DGS3MO**) − **50bp haircut** (E4b
serisi, dondurulmuş `data/snapshots/aux_us/2026-07-08/`). r_net=max(rate−haircut,0),
ACT/365, NAKİT fraksiyonuna tahakkuk. (Mutlak-momentum kapısı AYRI: ham DGS3MO,
haircut YOK — §1.7.)

---

## 1. MÜHÜRLÜ TASARIM PAKETİ (item 3) — literatür varsayılanları, TARAMA YOK

> Kaynak: `config/momentum_us2.yaml::design`. Aşağıdakiler TEK paket olarak
> mühürlüdür; koşum sonucuna göre bileşen değiştirilmez/seçilmez. Ablasyon (item 4c)
> ve komşuluk (item 4d) YALNIZ bilgilendiricidir — **kabul yalnız tam pakete uygulanır.**

1.1 **Formation:** 12 ay, son ay atlanır → **12-1 momentum**. Ay-sonu kapanışlarla:
    rebalans ayı m[j] için formation getirisi = `close[m[j-1]] / close[m[j-12]] − 1`
    (en son ay [m[j-1], m[j]] atlanır; 11-aylık span). j ≥ 12 gerekir (öncesi ısınma).

1.2 **Rebalans:** aylık. Ay-sonu (son işlem günü) sinyal hesaplanır; işlem **SONRAKİ
    işlem günü KAPANIŞINDA** (t+1) yürütülür. Tutma sırasında ara rebalance YOK.

1.3 **Ön-seçim:** formation getirisine göre en iyi **20** (top-20 momentum).

1.4 **Nihai seçim (FIP information-discreteness):** 20 aday arasından en **sürekli**
    10. **ID = sign(12-1 getiri) × [%negatif_gün − %pozitif_gün]**, formation
    penceresinin ([m[j-12], m[j-1]]) günlük getirilerinden (%pos = getiri>0 gün oranı,
    %neg = getiri<0 gün oranı). **DÜŞÜK ID tercih** (frog-in-the-pan: sürekli/pürüzsüz
    momentum daha güçlü devam eder). En düşük ID'li **10** seçilir.

1.5 **Ağırlık:** eşit, her slot **1/10 = %10**.

1.6 **Vol-hedefleme katmanı:** maruziyet = **min(1, target_vol / realize_6ay_portföy_vol)**.
    - **target_vol = 0.182326** (SEPET tam-dönem realize yıllık vol, √252) — **TEK
      SABİT, mühürlü**; benchmark verisinden türetildi (strateji koşumundan BAĞIMSIZ).
    - realize_6ay_portföy_vol = stratejinin günlük book getirilerinin trailing **126
      işlem günü** (6 ay) √252-yıllıklaştırılmış std'si (rebalans günü m[j]'de, ≤m[j]
      veriyle — nedensel). Isınma/yetersiz-geçmiş/vol=0 → maruziyet=1.0.
    - **Kaldıraç YOK** (maruziyet ≤ 1). (1 − maruziyet) fraksiyonu NAKİT.

1.7 **Mutlak-momentum (dual-momentum) NAKİT kapısı — pozisyon bazlı:** seçilen 10
    hissenin HER BİRİ için, eğer **hissenin 12-1 getirisi ≤ T-bill'in AYNI formation
    penceresi [m[j-12], m[j-1]] boyunca tahakkuk eden getirisi** ise o slot NAKİT
    kalır (yatırılmaz). T-bill oranı = **ham DGS3MO** (haircut YOK — sinyal eşiği,
    nakit-bacağı getirisi değil), ACT/365. Yatırılan slot sayısı < 10 olabilir; kalan
    nakit. **Window kararı (mühürlü):** "12-ay" ≈ ~1-yıllık formation ufku; hisse
    12-1 getirisiyle apples-to-apples olsun diye T-bill de BİREBİR aynı [m[j-12],
    m[j-1]] penceresinde ölçülür (trailing-12-ay alternatifi değerlendirildi, window-
    tutarlılık için bu seçildi — sonuçtan BAĞIMSIZ, koşumdan önce sabit).

1.8 **Maliyet:** US CostModel (commission=0, SATIŞTA SEC+TAF, slippage 5bps) — rebalans
    devrine (turnover) uygulanır. **Nakit getirisi:** DGS3MO−50bp (§0), NAKİT fraksiyonuna.

1.9 **Yön:** LONG-only (short YOK — Bölüm 8/17 #10 emsali; engine-seviyesi short ayrı tur).

---

## 2. Önceden hesaplanmış BENCHMARK metrikleri (strateji KOŞULMADAN)

Kaynak: `tools/e4_common.py::compute_benchmarks` (istatistikler `tools/run_regime_core.py`'den
— S1b/E4 ile AYNI fonksiyonlar; item 4 sürücüsü AYNI fonksiyonu yeniden çağırır →
drift imkânsız). Deterministik/offline.

| Benchmark | Toplam getiri | CAGR | Max DD | Sharpe (günlük, √252) | OOS aylık-Sharpe | OOS max DD |
|---|---|---|---|---|---|---|
| **Eşit-ağırlık US2 sepeti al-tut** (MÜHÜR REFERANSI, maliyetsiz) | +1,523.7% | **+13.84%** | **-45.54%** | **0.8035** | **0.8310** | **-33.98%** |
| SPY al-tut (endeks proxy, BİLGİLENDİRİCİ) | +816.2% | +10.85% | -55.19% | 0.6394 | 0.6656 | -41.99% |

- Sepet: `build_composite` (S1b/E4 ile AYNI) × 100000, maliyetsiz al-tut. SPY snapshot:
  `data/snapshots/us_bench/2026-07-08/SPY.parquet` (manifest sha256 `e76c2750…`).
- OOS: **39 walk-forward penceresi** (train=24ay/test=6ay/step=6ay — S1b şablonu),
  **231 OOS ayı**. Pencere sayısı veriden türer (E4 = 38; US2 bitişi 07-08 → 39).
  **Parametre optimizasyonu YOK** (tasarım her pencerede sabit).
- **Dürüst gözlem (mühürden bağımsız):** eşit-ağırlık sepet SPY'ı belirgin geçiyor
  (CAGR 13.84% vs 10.85%, Sharpe 0.80 vs 0.64) — farkın büyük kısmı survivorship +
  eşit-ağırlıktır. Kriterleri bu yüksek sepet çıtasına koymak kabul bakımından ZORLU
  (muhafazakâr) bir seçimdir. Ayrıca **sepet realize volü %18.23** (= mühürlü target_vol).

---

## 3. MÜHÜRLÜ KABUL TABLOSU (D2-US) — 4 kriter, referans = eşit-ağırlık US2 sepeti

> **Getiri-arayan aile:** D2-US getiri hedefler (D1 sermaye-koruma odaklıydı) → kriter
> 2 = **CAGR > sepet** bir VARLIK ŞARTIdır (E4/D1'de yoktu; kullanıcı talimatı madde 2).
> İşaret sözleşmesi: max DD derinliği = |max DD| (pozitif büyüklük).

| # | Kriter | MÜHÜRLÜ eşik | PASS koşulu (mekanik) |
|---|---|---|---|
| **1** | USD Sharpe > sepet Sharpe | sepet Sharpe = **0.8035** | strateji Sharpe **> 0.8035** |
| **2** | CAGR > sepet CAGR (getiri-arayan varlık şartı) | sepet CAGR = **0.13836** | strateji CAGR **> 0.13836** |
| **3a** | OOS aylık-Sharpe > sepet OOS aylık-Sharpe | sepet OOS Sharpe = **0.8310** | strateji OOS aylık-Sharpe **> 0.8310** |
| **3b** | Tam-dönem \|maxDD\| ≤ sepet \|maxDD\| (al-tut'tan derin düşmemek) | sepet \|maxDD\| = **45.54%** | strateji \|maxDD\| **≤ 45.54%** (maxDD ≥ **-0.455400**) |
| **4** | Komşuluk (formation/N/vol penceresi ±) uçurumsuz | — (yalnız SAĞLAMLIK) | mühürlü nokta komşularında UÇURUM yok; **seçim aracı DEĞİL** |

**Kabul kuralı (önceden belirlenmiş, sonuç görülmeden):** kriter **1, 2, 3a, 3b'nin
TAMAMI** geçerse **aile US-kabul ADAYI**; **herhangi biri kalırsa aile bu turda
US-referansta reddedilir** — "üçüncü bakış / dar fark" YOK. Kriter 4 (komşuluk) bir
SAĞLAMLIK gözlemidir (mühürlü PASS/FAIL değil). **Nihai karar kullanıcının/baş
danışmanın** — bu tablo yalnızca mekanik girdidir; Claude Code hüküm vermez.

**Ablasyon (item 4c) ve komşuluk (item 4d):** YALNIZ BİLGİ/atıf. Bileşen SEÇİMİ
YAPILMAZ; kabul YALNIZ tam pakete (§1) uygulanır.

---

## 4. Bağlam (mühürlü değil, item 4'te doldurulur)

- **D1-US (E4/E4b) kıyası:** D1-US mühürlü tabloda 1/4 ile US-referansta KESİN
  reddedildi (KALICI KAYIT 16). D2-US AYRI bir ailedir (kesitsel momentum ≠
  rejim-filtre); D1-US'in "geri dönüşü" DEĞİL. Kıyas D2_US_S1.md'de bilgilendirici.
- Örneklem/rebalans-adedi + survivorship UYARISI (disiplin #6) D2_US_S1.md'de KARARDAN
  ÖNCE yer alacak.

---

## 5. BENCHMARK-REFERANSI KİLİDİ (E4 §4 emsali — HERHANGİ bir koşumdan ÖNCE)

1. **Yukarıdaki (§0-§3) mühürlü tablo, eşikler ve TASARIM PAKETİ AYNEN geçerlidir.**
   Yeniden mühürleme, benchmark değişikliği, eşik ayarı veya bileşen seçimi YOKTUR.
2. **Benchmark referansı SEPET olarak kalır.** Sonuç görüldükten SONRA "referansı SPY
   yapalım" türü değişiklik kriter-alışverişidir (criterion-shopping) ve **D2-US için
   bu turda ve GELECEK turlarda YASAKTIR** — SPY'ın yalnız bilgilendirici olması
   kalıcı bir sınırdır.
3. **Karar kuralı (önceden):** 4 kriterin (1, 2, 3a, 3b) TAMAMI geçerse D2-US **US-kabul
   ADAYIdır**; herhangi biri kalırsa **US-referansta reddedilir.** Kabul kararı yine
   kullanıcının/baş danışmanın.
4. **Grid/varyant seçimi YASAK:** bu spike TEK mühürlü paketi ölçer. Ablasyon/komşuluk
   ölçülür ama karar onlara göre alınmaz.

*Mühür sonu. Bu dosyadaki hiçbir eşik/sabit strateji sonucuna göre değiştirilemez.
Spike koşumu (item 4) bu commit'ten SONRA yapılır.*

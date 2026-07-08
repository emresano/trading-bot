# EXPANSION_E4B.md — D1-US Nakit Bacağı Ölçüm-Tamamlama (S1→S1b emsali)

> **Ne bu:** E4'ün (US adil test, `EXPANSION_E4.md`) nakit-getiri düzeltmeli
> TEKRARI — D1-US ailesinin aynı tarihçeye **İKİNCİ ve SON bakışı**
> (`E4_CRITERIA.md` §4 SON-BAKIŞ KURALI). **Tek davranış değişikliği: nakit
> tahakkuku** (US 3-aylık T-bill). Mühürlü tablo, eşikler ve referans (SEPET)
> **AYNEN geçerli — yeniden mühürleme/benchmark değişikliği YOK.** Offline;
> `mode: paper` + tüm canlı bot modülleri DOKUNULMADI; N/b/M mühürlü; v7.1-golden
> 3/3 bayt-bayt. **Karar kullanıcının/baş danışmanın; Claude Code hüküm vermez.**

Tarih/commit: 2026-07-08. Para birimi: USD.

---

## 1. Seri Envanteri — US Kısa Faiz

- **Kaynak:** FRED `DGS3MO` (3-Month Treasury Constant Maturity Rate, GÜNLÜK, %).
  Herkese açık, kimlik-doğrulamasız CSV. Dondurulmuş: `data/snapshots/aux_us/
  2026-07-08/DGS3MO.parquet` (sha256 `d8c9ebe6…b8ba9e10`, manifest'li).
- **Kapsam/kalite:** 2005-01-03 → 2026-07-06. 5380 geçerli gözlem; 231 FRED
  tatil-"." işareti düşürüldü (beklenen). **Max boşluk 4 gün, >7 gün boşluk: 0**
  (uzun/anormal boşluk YOK — TRY serisindeki 9-aylık 2023 boşluğunun US karşılığı
  yok). Değer aralığı %0.0–5.63. Kullanım noktasında günlük takvime forward-fill.
- **Tahakkuk:** TRY (S1b) emsaliyle AYNI yapı — `r_net = max(rate − haircut, 0)`,
  ACT/365, nakitte geçen takvim günü kadar. **Haircut = 50bp (MUHAFAZAKÂR):**
  perakende para-piyasası fonu/nakit-sweep, T-bill politika oranının ALTINDA
  getirir (fon gider oranı ~15-40bp + bid/ask/sürtünme için tampon). TRY'nin
  200bp'sinden dar çünkü USD faiz/spread'i küçük. Gerekçe koşumdan ÖNCE
  mühürlendi (manifest + commit `19abf92`).
- **Bağlam:** sadece-nakit (US-faizli, tüm dönem) CAGR ≈ **%1.51** (Sharpe
  anlamsız — monoton eğri). Yani US nakit getirisi KÜÇÜK; S1b'deki TRY'nin
  yüksek-faiz ortamının (nakit-only CAGR ~%13.77) tam tersi.

---

## 2. AYRIŞTIRMA — Faizin İzole Katkısı (tek-değişiklik)

Anahtarlama tarihleri **BİREBİR AYNI** (57, nakit sinyali etkilemez — tek-değişiklik
izolasyonu; `test_e4b_us.py`). Strateji **%24.3** gün nakitte.

| Metrik | E4 (%0) | **E4b (US-faizli)** | Δ (faizin izole katkısı) |
|---|---|---|---|
| Toplam getiri | +443.3% | **+488.8%** | +45.5 puan |
| CAGR | +8.19% | **+8.60%** | **+0.41 puan** |
| Max drawdown | -23.11% | -23.11% | ~0 (−4e-5, ihmal — bkz. not) |
| Sharpe | 0.726 | **0.758** | **+0.032** |

*Not (S1b topoloji-gözlemi emsali):* nakit getirisi burada max DD'yi HAFİFÇE
DERİNLEŞTİRDİ (−4e-5) — çünkü düşüş-öncesi tepe equity'yi az miktarda yükseltip
aynı dip'i biraz daha derin bir % yaptı. Büyüklük ihmal edilebilir; kriter 2
sonucu değişmiyor. (S1b'de tersi olmuştu — TRY yüksek faizi düşüş-İÇİ epizotları
bölmüştü; US faizi çok küçük olduğundan o etki yok.)

**Faiz, beklendiği gibi KÜÇÜK bir iyileşme getirdi** (US kısa faizi ~%1.3 ort,
50bp haircut sonrası ~%0.8 net, üstelik nakitte yalnız %24.3 gün). Bu, S1b'deki
TRY etkisinin (2/4 kriteri FLIP etmişti) **niceliksel karşıtıdır**.

---

## 3. MÜHÜRLÜ TABLO — E4b faizli (MEKANİK; referans=SEPET, DEĞİŞMEZ)

| # | Kriter | Mühürlü eşik | E4 (%0) | **E4b (faizli)** | Sonuç |
|---|---|---|---|---|---|
| 1 | USD Sharpe > sepet | > 0.8561 | 0.726 | **0.758** | ❌ FAIL |
| 2 | Tam-dönem \|maxDD\| ≤ 23.14% | ≤ 23.14% | 23.11% | **23.11%** | ✅ PASS |
| 3a | OOS aylık-Sharpe > sepet | > 0.9154 | 0.669 | **0.692** | ❌ FAIL |
| 3b | OOS \|maxDD\| ≤ 14.96% | ≤ 14.96% | 20.41% | **20.42%** | ❌ FAIL |

MC (faizli): dd_p5 **-32.61%**, median -21.62%, dd_p95 -15.67%. OOS (faizli, 38
pencere/218 ay): Sharpe 0.692, maxDD -20.42%. Cliff (faizli): komşulukta uçurum
YOK (E4 ile aynı yapı; nakit switch'leri değiştirmiyor).

**MEKANİK SONUÇ: 4 kriterden yalnız 1'i (kriter 2) GEÇTİ — E4 ile AYNI tablo.**
Faiz Sharpe'ları yukarı itti (0.726→0.758; OOS 0.669→0.692) ama kriter 1/3a/3b'yi
GEÇİRMEYE YETMEDİ (sepet Sharpe çıtası 0.8561; açık ~0.10 puan).

**→ SON-BAKIŞ KURALININ (E4_CRITERIA.md §4) MEKANİK UYGULAMASI: herhangi bir
kriter kaldığından, D1-US ailesi US-referansta KESİN reddedilir. ÜÇÜNCÜ BAKIŞ
YOKTUR.** Bu bir HÜKÜM değil, önceden (koşumdan önce) mühürlenmiş kuralın mekanik
sonucudur; nihai kayıt kullanıcının/baş danışmanın.

---

## 4. ⚠ Örneklem / Anahtarlama-Adedi UYARISI (disiplin #6 — karar bölümünden ÖNCE)

Tek tarihçe, tek koşum, tek evren. **57 anahtarlama** (~28 round-trip, 21 yıl) —
istatistiksel olarak ince. Referans SEPET **survivorship-şişirilmiş** (E4 §1:
gerçek-üstü yüksek çıta). Faiz serisi FRED (US Hazinesi'nin kendi yayını olmakla
birlikte constant-maturity türev), 50bp haircut tek sabit varsayım. Bu uyarılar,
aşağıdaki sonucun mekanik olduğunu, bir "hüküm" olmadığını vurgular.

---

## 5. Dürüst Çekinceler

1. Kriter 2 hâlâ **razor-thin** geçiyor (23.11% vs 23.14%); faiz onu marj -4e-5
   DERİNLEŞTİRDİ ama eşiğin altında kaldı — genel sonuç zaten 1/3a/3b'den değişmez.
2. Faizli SPY kıyası (referans DEĞİL, yalnız bilgi): E4b Sharpe 0.758, SPY 0.640'ı
   yine GEÇER — ama SON-BAKIŞ KURALI referansı SEPETe sabitler, SPY'a geçiş YASAK
   (kriter-alışverişi). Bu kayıt tutarlılık için, sonuç DEĞİŞMEZ.
3. Gerçek bir nakit-sweep'in getirisi ürün/broker'a göre değişir; 50bp haircut
   muhafazakâr ama tek nokta. Daha yüksek/düşük haircut sonucu FLIP ETMEZ (faizin
   toplam katkısı +0.03 Sharpe; çıta açığı ~0.10).
4. Bulgu BIST-USD (S1b (f)) ile TUTARLI: regime-filtre drawdown'ı sepetin ~yarısına
   indiriyor (sermaye-koruma tutuyor) ama survivorship-şişirilmiş sepetin Sharpe'ını
   geçmiyor — para birimi USD olunca (hem BIST hem US) aynı yapı.

---

## 6. Sonuç (mekanik, hüküm değil)

E4b, E4'ün sonucunu **teyit ve tamamlar**: US kısa faizi eklendiğinde D1-US
metrikleri hafifçe iyileşir (Sharpe +0.032, CAGR +0.41pp) ama **mühürlü 4-kriter
tablosu 1/4'te kalır** (kriter 2 tek geçen). Önceden mühürlenmiş SON-BAKIŞ KURALI
gereği bu, **D1-US ailesinin US-referansta KESİN reddi** anlamına gelir — dönüş
yolu kapalıdır; D1 mantığı ancak gelecekte AYRI bir tasarımın (farklı çekirdek/
evren) risk-katmanı adayı olarak, YENİ ve ayrıca mühürlenmiş kriterlerle gündeme
gelebilir. Bu, D1-US ailesinin kendisinin yeniden değerlendirilmesi değildir.

**Nihai kayıt kullanıcının/baş danışmanın.** Bu turda hiçbir eşik/parametre/
benchmark değiştirilmedi, varyant seçilmedi, canlı bot modülüne dokunulmadı; iki
durma noktası aynen kullanıcıda.

### Tekrarlanabilirlik
```
python -m tools.build_us_rate_snapshot        # DGS3MO dondur (bir kez; commit'li)
python -m tools.run_regime_core_us_e4b        # %0 vs faizli ayrıştırma + mühürlü tablo
python -m pytest tests/test_e4b_us.py -q      # 5 test (tek-değişiklik izolasyonu vb.)
```
Çıktı: `runtime/e4/regime_core_us_e4b/summary.json`. Snapshot'lar dondurulmuş → deterministik.

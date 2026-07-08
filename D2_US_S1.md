# D2_US_S1.md — Kesitsel Momentum (D2-US) Spike Değerlendirme Raporu

**Tur:** D2US-S1 (kesitsel momentum ailesi tasarım + spike). **Tarih:** 2026-07-08.
**Tür:** offline araştırma spike'ı — üretim implementasyonu DEĞİL. **Karar:** yok
(HÜKÜM YOK — kabul/red kullanıcının/baş danışmanın; bu rapor yalnız mekanik girdi).

> **İzolasyon (E4 emsali, korundu):** `mode: paper` + TÜM canlı bot modülleri
> (strategy/regime_core.py, execution/, safety/, data/live_*, notify/, main.py,
> config/config.yaml, config/regime_core.yaml) + S1/S1b/E4 araçları
> (backtest/regime_core*.py, tools/run_regime_core*.py, tools/e4_common.py,
> config/regime_core_us.yaml) DEĞİŞTİRİLMEDİ. Yeni aile BAĞIMSIZ modülde
> (backtest/xsec_momentum.py) — `costs/` + `data/cleaning.py` yeniden kullanıldı
> (değişmeden). BIST v7.1-golden her commit 3/3 bayt-bayt. Grid/varyant SEÇİMİ
> YOK — tasarım TEK paket olarak koşumdan ÖNCE mühürlendi (D2US_CRITERIA.md).

---

## 0. Veri Envanteri + ⚠ Survivorship (KARARDAN ÖNCE)

**Evren:** US2 = 50 sembol, 10 GICS sektörü (E4'ün 20'si korundu + 30 yeni),
`data/snapshots/us2/2026-07-08/` (dondurulmuş, sha256 manifest). Kapsam
**2005-01-03 → 2026-07-08, 5411 işlem günü**; 50 sembolün TAMAMI tam/yinelenmesiz,
0 FAIL; kompozit temizlik **0 hayalet-bar / 0 forward-fill** (E4 ile AYNI
`load_and_clean_universe` yolu). Tam denetim: **DATA_AUDIT_US2.md**.

**⚠ Survivorship yanlılığı (bilinen, KABUL EDİLEN — DATA_AUDIT_US2.md §2):** bu 50
sembol bugün likit oldukları için seçildi; 2005-2026'da delisting/iflas eden
firmalar (Lehman, WaMu, Bear Stearns, GM 2009…) evrende YOK. Sonuç: **eşit-ağırlık
sepet gerçek-üstü yüksek bir kabul çıtasıdır** → kriterleri sepete koymak
muhafazakâr. Kesitsel-momentuma özgü nüans: strateji de AYNI hayatta-kalan
evrenden seçtiği ve iflasa gideni short'lamadığı (LONG-only) için yanlılık hem
sepeti hem stratejiyi yukarı çeker; ama sepet daima %100 yatırımda olduğundan net
etki **kabul kıyasında yine strateji ALEYHİNE / muhafazakâr**. Gerçek
(hayatta-kalmayanları içeren) evrende momentumun kaybedenden kaçınma avantajı daha
belirgin olabilirdi → ölçülen sonuç momentumun ALT sınırıdır.

---

## 1. Mühürlü Tasarım Paketi (D2US_CRITERIA.md §1 — özet)

12-1 momentum (formation 12 ay, son ay atlanır) · aylık rebalans (ay-sonu sinyal →
**t+1** kapanış yürütme) · ön-seçim top-20 momentum → **FIP** information-discreteness
ile en sürekli **10** (ID = sign(mom)×(%neg−%pos), düşük ID) · eşit ağırlık 1/10 ·
pozisyon-bazlı **mutlak-momentum nakit kapısı** (12-1 ≤ T-bill formation-penceresi
getirisi → slot nakit; ham DGS3MO, ACT/365) · **vol-hedefleme** (maruziyet =
min(1, target_vol/realize_6ay_book_vol), **target_vol=0.182326** = sepet tam-dönem
realize vol, kaldıraçsız) · US CostModel devir · nakit DGS3MO−50bp · LONG-only.
**Tasarım literatür varsayılanlarıyla, koşumdan ÖNCE, tarama YAPILMADAN mühürlendi.**

---

## 2. Benchmark (D2US_CRITERIA.md §2 — mühürlü, strateji koşulmadan)

| Benchmark | CAGR | Max DD | Sharpe (√252) | OOS aylık-Sharpe | OOS max DD |
|---|---|---|---|---|---|
| **Eşit-ağırlık US2 sepeti al-tut** (MÜHÜR REFERANSI, maliyetsiz) | **+13.84%** | **-45.54%** | **0.8035** | **0.8310** | -33.98% |
| SPY al-tut (endeks proxy, BİLGİLENDİRİCİ) | +10.85% | -55.19% | 0.6394 | 0.6656 | -41.99% |

- OOS: 39 walk-forward penceresi (train=24ay/test=6ay/step=6ay, S1b şablonu), 231 OOS ayı.
- Sepet, SPY'ı belirgin geçiyor (survivorship + eşit-ağırlık) → yüksek/zorlu çıta.

---

## 3. MÜHÜRLÜ TABLO — MEKANİK SONUÇ (referans = eşit-ağırlık US2 sepeti)

> Bu tablo `D2US_CRITERIA.md` §3'ün mekanik doldurmasıdır — HÜKÜM DEĞİL. Kabul kuralı
> önceden mühürlendi: **1+2+3a+3b TAMAMI geçerse US-kabul ADAYI; herhangi biri
> kalırsa red — "dar fark" YOK.**

| # | Kriter | Mühürlü eşik | Strateji | Sonuç |
|---|---|---|---|---|
| **1** | USD Sharpe > sepet Sharpe | > 0.8035 | **0.7254** | **FAIL** |
| **2** | CAGR > sepet CAGR (getiri-arayan varlık şartı) | > 13.836% | **10.87%** | **FAIL** |
| **3a** | OOS aylık-Sharpe > sepet OOS aylık-Sharpe | > 0.8310 | **0.7697** | **FAIL** |
| **3b** | Tam-dönem \|maxDD\| ≤ sepet \|maxDD\| | ≤ 45.54% | **32.61%** | **PASS** |

→ **1/4 geçti (yalnız 3b).** `all_4_pass = False`. **Önceden mühürlenen kurala göre
D2-US, US-referansta kabul adayı DEĞİLDİR** — bu Claude Code'un hükmü değil,
kullanıcının koyduğu kuralın MEKANİK sonucudur. **Nihai kayıt kullanıcının/baş
danışmanın.**

---

## 4. Ana Koşum + Risk (tam dönem, mühürlü tam paket)

- **CAGR +10.87%**, toplam getiri +821.0%, **Sharpe 0.7254**, **max DD -32.61%**,
  246 aylık rebalans. Nihai equity 921,043 (100k'dan).
- **OOS (39 pencere):** aylık-Sharpe 0.7697, max DD -25.20%, 224 OOS ayı.
- **Monte Carlo (aylık getiri permütasyonu, seed=42, 500 koşu):** dd_p5 **-36.12%**,
  medyan -23.65%, p95 -17.48%. (dd_p5, sepet maxDD'sinden sığ; gözlemsel.)
- **En derin 5 drawdown epizodu:** 2020-02→03 **-32.6%** (COVID, global maks);
  2007-12→2008-10 -27.4% (GFC — kapı kademeli nakde geçtiği için COVID'den SIĞ);
  2021-11→2022-09 -18.7%; 2006 -14.9%; 2018-Q4 -14.5%. (≥%10 epizot: 11 adet.)

---

## 5. (a) Momentum-Crash Epizotları — 2009 ve 2020 dip-dönüşleri

Momentum aileleri dip-dönüşlerinde yapısal olarak zorlanır (Daniel-Moskowitz 2016):
LONG-only'de bu, "önceki kaybedenlerin şiddetli toparlanmasını KAÇIRMA" biçiminde
görünür. D2-US'in savunma katmanları (abs-kapı + vol-hedefleme) düşüşü korudu ama
tam da bu yüzden keskin geri dönüşleri kaçırdı:

| Pencere | Strateji | Sepet | Fark | Strateji davranışı |
|---|---|---|---|---|
| **2009 rebound** (03-09→09-30) | **-0.8%** | **+51.0%** | **-51.8pp** | abs-kapı ~**8.9/10 slot NAKİT** (tüm 12-1'ler negatif); pencere-içi DD yalnız -1.0% |
| 2009 tam yıl | +9.9% | +24.1% | -14.2pp | ort. 6.75 nakit-slot; ilk yarı ağırlıkla nakit |
| **2020 rebound** (03-23→08-31) | **+26.6%** | **+68.7%** | **-42.1pp** | vol-hedefleme maruziyeti ~**0.42**'ye indi (Mart vol şoku); kapı az tetikledi |
| 2020 tam yıl | -7.6% | +27.0% | -34.6pp | global maks DD (-32.6%) buradan; önce çöküşte yakalandı, sonra de-risk'te toparlanmayı kaçırdı |

**Yorum (mekanik, hüküm değil):** iki epizot iki FARKLI katmanın nasıl "koruma =
kaçırma" ürettiğini gösteriyor. 2009'da **abs-kapı** (yavaş GFC dibinde tüm momentum
negatif → neredeyse tam nakit → +51% rebound kaçtı). 2020'de **vol-hedefleme** (hızlı
COVID vol-şoku maruziyeti yarıya indirdi → V-toparlanma yarı yakalandı). Bu, tasarımın
sermaye-korumasının (max DD sepetin ~%72'si) BEDELİdir ve getiri-arayan kritere (2, 1,
3a) doğrudan zarar verir. Aylık rebalans + t+1 gecikmesi COVID gibi hızlı olaylarda
GFC'ye göre daha zayıf tepki verdi (max DD COVID'de daha derin).

---

## 6. (b) Turnover + Maliyet Sürüklemesi

- **Ortalama yıllık turnover: 5.88×** (588%/yıl) — aylık momentum için tipik/yüksek;
  ortalama aylık devir 0.50. Yıllara göre 2.2×–7.7× (kriz yıllarında düşer: 2009 = 2.7×).
- **Maliyet sürüklemesi: ~33 bps/yıl** (sıfır-maliyet karşı-olgusu: CAGR 11.21% →
  10.87%, Δ=33.4 bps; ort-equity yöntemi 30.0 bps). Toplam $ maliyet ~21,217.
- **Yorum:** US komisyonsuz + düşük SEC/TAF + 5bps slippage sayesinde 588% turnover'a
  RAĞMEN maliyet ILIMLI (~33bps/yıl). Yani zayıf sonuç maliyet kaynaklı DEĞİL — devir
  maliyeti stratejinin sepet-altı Sharpe/CAGR'ını açıklamıyor (ana sürücü momentum
  edge'inin bu dar large-cap evreninde zayıflığı, §10).

---

## 7. (c) Ablasyon — YALNIZ BİLGİ/ATIF (bileşen SEÇİMİ YAPILMAZ)

> Kabul YALNIZ tam pakete (V3) uygulanır. Aşağıdaki tablo her katmanın marjinal
> etkisini ŞEFFAF gösterir; bir bileşeni "seçmek" için DEĞİL (disiplin #3).

| Varyant | CAGR | Max DD | Sharpe |
|---|---|---|---|
| V0 yalın 12-1 top-10 | 10.22% | -43.48% | 0.602 |
| V1 +FIP | 12.27% | -45.25% | 0.738 |
| V2 +abs-kapı | 11.94% | **-32.60%** | **0.761** |
| **V3 tam +vol (MÜHÜRLÜ)** | 10.87% | -32.61% | 0.725 |

**Gözlem (mekanik):** FIP Sharpe'ı belirgin itiyor (0.60→0.74) — information-discreteness
bu evrende sinyal taşıyor. abs-kapı max DD'yi -45%→-33%'e çekiyor (sermaye-koruma) ve
Sharpe'ı 0.76'ya çıkarıyor. vol-hedefleme bu ÖRNEKLEMDE Sharpe/CAGR'ı hafif DÜŞÜRÜYOR
(0.76→0.725) — çünkü 2020 gibi vol-şoklarında de-risk edip toparlanmayı kaçırdı (§5).
**KRİTİK NOT (seçim değil, dürüstlük):** en yüksek-Sharpe varyant (V2, 0.761) BİLE
kriter 1'i (0.8035) geçmiyor → bileşen cherry-pick'i kabul/red sonucunu DEĞİŞTİRMEZDİ.
Bu, kararın tek bir katmanın hassas ayarına bağlı OLMADIĞINI gösterir.

---

## 8. (d) Komşuluk — GÖZLEMSEL (seçim aracı değil)

| Boyut | Değerler → Sharpe (maxDD) |
|---|---|
| formation ay | 9 → 0.743 (-28.4%) · **12 → 0.725 (-32.6%)** · 15 → 0.560 (-36.2%) |
| final N | 8 → 0.676 · **10 → 0.725** · 12 → 0.699 |
| vol penceresi (gün) | 84 → 0.733 · **126 → 0.725** · 168 → 0.729 |

**Gözlem:** mühürlü nokta (12/10/126) komşularında UÇURUM YOK. vol-penceresi neredeyse
düz (0.729–0.733). final_n = 10 yerel olarak en iyi (marjinal). formation: 9↔12 yakın;
15 daha zayıf (uzun lookback momentumu seyreltir) — bu bir uçurum değil, pürüzsüz
düşüş. **Mühürlü 12-1 literatür varsayılanıdır ve komşuluğun ZİRVESİ DEĞİL** (9 hafif
üstün) → overfitting-karşıtı işaret (nokta sonuca göre seçilmedi).

---

## 9. Bağlam (BİLGİLENDİRİCİ — mühürlü değil, karar etkilenmez)

- **D1-US (E4b) kıyası:** D1-US (regime_core) US-referansta mühürlü tabloda 1/4 →
  KESİN RED (KALICI KAYIT 16; CAGR 8.60%, Sharpe 0.758, maxDD -23.11%). D2-US AYRI
  bir ailedir (kesitsel momentum ≠ rejim-filtre), D1'in "geri dönüşü" değil. İkisi de
  survivorship-şişirilmiş sepeti Sharpe/CAGR'da geçemedi — farklı mekanizmalar, AYNI
  yapısal engel (yüksek sepet çıtası).
- **SPY kıyası (referans DEĞİL — E4 §4 kilidi: SPY'a geçiş YASAK):** D2-US, SPY'ı
  Sharpe'ta (0.725 > 0.639) ve max DD'de (-32.6% vs -55.2%) GEÇİYOR, CAGR eşit
  (10.87% vs 10.85%). Yani "gerçekçi/kurulabilir endekse" karşı savunmacı bir profil
  var — ama **mühürlü referans SEPET, değiştirilemez** (kriter-alışverişi yasak).

---

## 10. ⚠ ÖRNEKLEM + Survivorship UYARISI (KARARDAN ÖNCE — disiplin #6)

1. **Survivorship (tekrar, §0):** referans sepet gerçek-üstü yüksek → çıta muhafazakâr;
   ama momentumun kaybedenden-kaçınma avantajı da bu evrende ölçülemiyor. Sonuç bir
   ALT sınırdır; gerçek point-in-time evrende yön belirsiz (ayrı metodoloji turu gerekir).
2. **Dar large-cap evreni:** kesitsel momentum, GENİŞ evrenlerde (küçük/orta ölçek dahil,
   yüzlerce isim) en güçlüdür; 50 mega-cap arasında kesitsel dağılım ve momentum edge'i
   YAPISAL olarak zayıftır. Bu sonuç literatürle tutarlı (mega-cap momentum zayıf) —
   D2-US'in "kötü" olması değil, evrenin momentuma elverişsizliği baskın olabilir.
3. **Örneklem/olay adedi:** 21 yıl, 246 aylık rebalans, ~2 büyük momentum-crash rejimi
   (2009, 2020). Sharpe/CAGR farkları birkaç kriz epizoduna duyarlı; istatistiksel güç
   sınırlı. OOS (39 pencere) bunu bir ölçüde hafifletir ama aynı iki krizi paylaşır.
4. **Tek örneklem, tek evren:** bu bir SPIKE'tır (üretim değil). Farklı evren (geniş),
   farklı rebalans (haftalık/kademeli), veya short-bacak (Bölüm 17 #10) sonucu
   değiştirebilir — ama bunların HİÇBİRİ bu turda test EDİLMEDİ ve grid/varyant seçimi
   YASAK olduğu için test edilMEYECEK. Kabul kararı yalnız MÜHÜRLÜ tam pakete dairdir.
5. **Vol-katmanı in-sample bedeli (§7):** tam paket, vol-hedefleme nedeniyle V2'den
   düşük Sharpe verdi — bu bir tasarım seçimidir (kaldıraçsız sermaye-koruma), sonuca
   göre "düzeltilmedi" (aksi criterion-shopping olurdu).

---

## 11. Kapanış (HÜKÜM YOK)

**Mekanik sonuç:** mühürlü 4-kriter tablosunda **1/4** geçti (yalnız 3b, tam-dönem
maxDD). Önceden mühürlenen kurala göre (`D2US_CRITERIA.md` §3/§5) bu, **D2-US ailesini
US-referansta bir kabul adayı YAPMAZ.** Bu bir HÜKÜM değil — kullanıcının koyduğu
kuralın mekanik uygulamasıdır.

Dürüst özet (mekanik, karar değil): D2-US, savunma katmanları sayesinde sepetin
yarısı-üçte-ikisi derinliğinde bir düşüş profili ve SPY'ı geçen bir Sharpe üretti; ama
survivorship-şişirilmiş eşit-ağırlık sepetin Sharpe (0.80), CAGR (%13.84) ve OOS Sharpe
(0.83) çıtalarının ALTINDA kaldı. Ana sürücü maliyet DEĞİL (~33bps/yıl); dar large-cap
evreninde momentum edge'inin zayıflığı + dip-dönüşlerinde savunma katmanlarının
toparlanmayı kaçırması (§5) baskın. Ablasyon, sonucun tek bir katmanın ayarına
bağlı olmadığını gösterdi (en iyi varyant bile kriter 1'i geçmiyor); komşuluk uçurumsuz
ve mühürlü nokta zirve değil (overfitting-karşıtı).

**Karar (kabul / red / farklı-evren iterasyonu) kullanıcının/baş danışmanındır.** Bu
turda hiçbir eşik esnetilmedi, bileşen/varyant seçilmedi, canlı bot modülüne
dokunulmadı; Faz 6 / go_live / launchd / real adımı YOK. İki durma noktası kullanıcıda.

*Rapor sonu.*

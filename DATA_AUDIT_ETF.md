# Veri Denetimi — ETF Evreni (DATA_AUDIT_ETF.md)

D4US-S1 (varlık-sınıfı ETF dual-momentum ailesi) turunun **item 1** çıktısı. Salt-okunur
denetim — hiçbir motor/sinyal/risk kodu ve hiçbir canlı bot modülü bu adımda yazılmadı/
değiştirilmedi; BIST v7.1-golden 3/3 korundu (golden-yolu dosyası dokunulmadı → construction).

Snapshot: **`data/snapshots/etf_us/2026-07-08/`** (`manifest.json` sha256
`5e80ada2…260d935b`; `tools/build_etf_snapshot.py` ile bir kez üretildi, sonrası
deterministik/offline). Adaptör: `data/adapters/yf_us.py` (yfinance, **`auto_adjust=True`
→ TOTAL-RETURN**). Temizlik borusu **S1b/E4/D2US ile AYNI**
(`data/cleaning.py::load_and_clean_universe` — `normalize_bist_dates` US 00:00-UTC
verisinde NO-OP, hayalet-bar filtresi piyasa-agnostiktir).

**Kapsam:** 9 ETF **2005-01-03 → 2026-07-08 (5411 gün)**; **DBC 2006-02-06 → 2026-07-08
(5136 gün)** — DBC evrenin en geç başlayanı, kompozit `t0`'ı bağlar. Kompozit (10-ETF
eşit-ağırlık) **2006-02-06 → 2026-07-08, 5136 işlem günü**, hayalet-bar **0** /
forward-fill **0**. Strateji ilk-sinyali (t0 + 12 ay formation ısınması) ≈ **2007-02**.

---

## 1. Evren (10 varlık-sınıfı ETF, SABİT — ikame YASAK)

Evren KALICI KAYIT 20 / D4US_CRITERIA.md ile **DONDURULDU**: aşağıdaki 10 sembol sabittir,
ikame/çıkarma/ekleme YASAKTIR (D2 Ders-2'nin evren-sınıfı yanıtı — tek-hisse kesitsel
dağılım yerine varlık-sınıfları arası dağılım). Semboller **geçmiş getiriye göre
SEÇİLMEDİ** — her biri kendi varlık sınıfının kanonik, uzun-ömürlü, likit ETF'idir.

### Kimlik doğrulaması (US3 dersi — DATA_FEASIBILITY_US3)

Fiyat indirmeden ÖNCE her sembol için yfinance `longName` + `quoteType` çekildi ve
beklenen fon-adı anahtar kelimesiyle eşleştiği doğrulandı (`identity.json`). **US3'te
görülen "ticker sessizce başka bir enstrümanın verisini döndürüyor" riskine karşı zorunlu
kapı: eşleşmezse İKAME YOK, snapshot yazılmaz, DUR-ve-sor.** 10/10 GEÇTİ:

| # | Sembol | Varlık sınıfı | yfinance `longName` (doğrulandı) | quoteType |
|---|---|---|---|---|
| 1 | SPY | US Large-Cap Hisse | State Street SPDR S&P 500 ETF Trust | ETF |
| 2 | IWM | US Small-Cap Hisse | iShares Russell 2000 ETF | ETF |
| 3 | EFA | Gelişmiş Uluslararası Hisse | iShares MSCI EAFE ETF | ETF |
| 4 | EEM | Gelişen Piyasa Hissesi | iShares MSCI Emerging Markets ETF | ETF |
| 5 | VNQ | US GYO (Gayrimenkul) | Vanguard Real Estate Index Fund ETF Shares | ETF |
| 6 | TLT | US 20+ Yıl Hazine Tahvili | iShares 20+ Year Treasury Bond ETF | ETF |
| 7 | IEF | US 7-10 Yıl Hazine Tahvili | iShares 7-10 Year Treasury Bond ETF | ETF |
| 8 | LQD | US Yatırım-Yapılabilir Kredi | iShares iBoxx $ Investment Grade Corporate Bond ETF | ETF |
| 9 | GLD | Altın | SPDR Gold Shares | ETF |
| 10 | DBC | Geniş Emtia | Invesco DB Commodity Index Tracking Fund | ETF |

**Varlık-sınıfı dağılımı:** hisse 4 (US large/small + gelişmiş/gelişen uluslararası),
tahvil 3 (uzun/orta Hazine + kredi), reel varlık 3 (GYO + altın + geniş emtia) =
düşük-korelasyonlu, farklı rejim-duyarlı 10 segment. Bu, D2'nin dar 50-mega-cap hisse
evreninin (tümü aynı varlık sınıfı → kesitsel dağılım dar) yapısal karşıtıdır.

---

## 2. TOTAL-RETURN kararı (tahvil ETF'lerinde zorunlu)

`auto_adjust=True` → kapanış serisi temettü + bölünme düzeltmeli (**total-return**):
temettüler geriye-düzeltmeyle örtük yeniden-yatırılır. **Tahvil/kredi ETF'lerinde
(TLT/IEF/LQD) fiyat-only seri CİDDİ hata verir** — bu fonların getirisinin büyük kısmı
kupon (temettü) dağıtımıdır; fiyat-only kullanmak momentum sinyalini ve sepet referansını
sistematik olarak yanıltırdı. **Strateji VE benchmark AYNI total-return seride** ölçülür
(tutarlılık). VNQ (GYO, yüksek temettü) ve GLD/DBC (temettüsüz) için de aynı boru kullanılır.

**auto_adjust sınırlaması (bilinen, E4/US2 ile aynı):** ham (düzeltilmemiş) fiyat
saklanmaz → bir sıçramanın gerçek hareket mi adjustment artefaktı mı olduğu ham veriyle
kesin ayrıştırılamaz. ETF'lerde bu risk hisselere göre çok düşüktür (ETF'ler
sepet-fiyatlıdır, tek-isim kurumsal-işlem şoku yaşamaz — §4'te 0 sıçrama bunu doğruluyor).

---

## 3. Kapsam + Bütünlük Denetimi

Kaynak: `tools/data_audit.py` (HARDENING A2 deseni), DEĞİŞTİRİLMEDEN yalnız
`--snapshot data/snapshots/etf_us/2026-07-08` argümanıyla yeniden kullanıldı.

**Özet: 10 sembolün TAMAMI FAIL-SIZ; 9'u PASS, DBC WARN (yalnız geç-başlangıç).**

| Metrik | Sonuç |
|---|---|
| Sembol sayısı | 10 |
| Satır (9 ETF) | 5411 (2005-01-03 → 2026-07-08) |
| Satır (DBC) | 5136 (2006-02-06 → 2026-07-08) |
| Sıfır/negatif fiyat | 0 (tüm semboller) |
| Yinelenen tarih | 0 (tüm semboller) |
| Kalite kontrolü (OHLC tutarlılık) | PASS (tüm semboller) |
| **≥%25 günlük sıçrama** | **0 (TÜM 10 sembol)** |
| FAIL sayısı | **0** |
| WARN sayısı | 1 (yalnız DBC — aşağıda) |

**DBC WARN'ının tek nedeni:** DBC 2006-02-06'da kurulmuştur; 2005-01-03…2006-02-03
aralığındaki 275 "eksik gün" (denetimin diğer 9 sembolde var olup DBC'de olmayan
tarihleri) DBC'nin GERÇEK kuruluş tarihinden öncedir — **veri hatası DEĞİL, kuruluş
sınırı.** `build_composite` `t0`'ı en geç başlayana (DBC = 2006-02-06) çektiği için bu
275 gün kompozite/stratejiye HİÇ girmez.

**⚠ DBC → kompozit başlangıç sınırı (dürüst not):** kompozit 2006-02-06'da başlar çünkü
2006'dan önce geniş bir emtia ETF'i (yatırılabilir) mevcut DEĞİLDİ. Bu bir seçim değil,
**veri-mevcudiyeti sınırıdır** — evrene emtia dahil etmenin bedeli ~13 aylık daha kısa
tarihçedir. Alternatif (DBC'yi çıkarıp 2005'te başlamak) bir bileşen-seçimi olurdu ve
evren SABİT olduğu için YAPILMADI.

**Kompozit temizlik (`load_and_clean_universe` + `build_composite`, E4/D2US ile AYNI
kod):** hayalet-bar **0 elendi**, forward-fill **0** — 10 ETF, t0'dan (2006-02-06)
itibaren 5136 günde tam hizalı. **≥%25 sıçrama 0** (ETF'ler diversifiye → tek-isim
şoku yok; US2 hisse evreninde 9 WARN-sembol vardı, burada 0 → varlık-sınıfı evreninin
sinyal-temizliği).

---

## 4. ⚠ Survivorship — bu evrende YAPISAL olarak küçük (D2/E4'ten temel fark)

**Bu turun en önemli metodolojik iyileştirmesi.** D2-US ve E4'te mühürlü referans
(eşit-ağırlık US-hisse sepeti) survivorship-şişirilmişti: 2005'te var olup sonra iflas
eden hisseler (Lehman, WaMu, GM…) evrende olmadığı için sepet gerçek-üstü yüksek bir
çıtaydı (bilinen sorun #13). **ETF varlık-sınıfı evreninde bu yanlılık YAPISAL olarak
çok daha küçüktür:**

- **Bir varlık SINIFI "iflas etmez".** SPY = US hisse senedi piyasasının kendisi; TLT =
  20+ yıl Hazine; GLD = altın. Bu ETF'ler tek-isim değil, bir varlık sınıfının
  yatırılabilir temsilcisidir → "hayatta kalan seçildi, batan gizlendi" mekanizması
  (tek-hisse survivorship'inin kaynağı) burada YOKTUR.
- **Sepet referansı GERÇEKTEN YATIRILABİLİR.** Eşit-ağırlık 10-ETF al-tut, 2006'dan bugüne
  fiilen kurulabilir bir portföydür (hepsi o gün de vardı, likitti). D2/E4'ün
  "gerçek-üstü" sepetinin aksine bu, dürüst/uygulanabilir bir çıtadır → kabul kıyası
  ARTIK muhafazakâr-şişirme ile bozulmuyor.

**Hafif ETF-düzeyi survivorship (dürüstçe, tam olması için):** yine de küçük bir seçim
etkisi vardır — bu 10, kendi sınıflarının BUGÜN baskın/likit fonlarıdır; 2005-2026'da
açılıp kapanan niş/kaldıraçlı/rakip ETF'ler (ör. bazı emtia veya sektör ürünleri) evrende
yok. Ama (a) bu 10, sınıflarının kanonik ve o dönemde de dominant fonlarıdır (rastgele
"kazanan fon" seçimi değil), (b) bir sınıfın getirisi, o sınıfı temsil eden fonun
kapanıp-kapanmamasından bağımsızdır (kapanan bir rakip S&P-500 ETF'i SPY'ın getirdiğini
değiştirmez). **Net: survivorship yönü D2/E4'e göre niceliksel olarak çok daha zayıf ve
sepet çıtası dürüsttür** — bu, D4-US'in D2 Ders-2'ye getirdiği yapısal iyileşmenin
çekirdeğidir. (Tam-titizlik: point-in-time ETF evreni/kapanan-fon dahil bir metodoloji
turu D4US-S1 kapsamı DIŞINDA; bu çekince D4_US_S1.md karar bölümünden ÖNCE tekrarlanır.)

---

## 5. Nakit/aux serisi (E4b DGS3MO — AYNEN yeniden kullanıldı)

Nakit bacağı + mutlak-momentum kapısı için **`data/snapshots/aux_us/2026-07-08/DGS3MO.parquet`**
(FRED 3-aylık T-bill, E4b'de dondurulmuş, sha256 `d8c9ebe6…`) **DEĞİŞTİRİLMEDEN** yeniden
kullanıldı — yeni indirme/snapshot YOK.

**Kapsam teyidi (zorunlu):** DGS3MO first_obs **2005-01-03**, evren `t0` − 12 ay =
**2005-02-06**. `2005-01-03 < 2005-02-06` → **aux, evren başlangıcı −12 aydan ÖNCEYE
uzanıyor** ✓ (ilk rebalans ≈ 2007-02'nin formation penceresi [2006-02, 2007-02] ve
öncesindeki tüm nakit tahakkuku tam kapsanır). last_obs 2026-07-06 (evren bitişi
2026-07-08'den 2 gün önce → `_build_daily_rate` ffill ile taşır, E4b emsali).

---

## 6. Kaynak / Adaptör / İzolasyon Notları

- `data/adapters/yf_us.py`: yfinance, `auto_adjust=True` (total-return), tz-aware index
  (America/New_York → UTC; negatif ofset → BIST'in bir-gün-geri kayması burada yapısal
  olarak yok). Kütüphane sürümü manifest'te (`0.2.66`).
- **Snapshot dondurma:** `tools/build_etf_snapshot.py` (YENİ araç; kimlik-doğrulama kapısı
  gömülü). Mevcut hiçbir snapshot'a (BIST/us/us2/aux/aux_us/us_bench/fx) DOKUNMADI, yalnız
  yeni `etf_us/` dizini + `identity.json` yazdı. sha256 manifest her parquet için ayrı hash
  tutar → determinizm/offline.
- **İZOLASYON:** bu adımda `mode: paper`, canlı bot modülleri (strategy/regime_core.py,
  execution/, safety/, data/live_*, notify/, main.py, config/config.yaml,
  config/regime_core.yaml) ve S1/S1b/E4/D2US araçları (backtest/regime_core*.py,
  backtest/xsec_momentum.py, tools/run_regime_core*.py, tools/e4_common.py,
  tools/run_xsec_momentum_us2.py, config/regime_core*.yaml, config/momentum_us2.yaml)
  DEĞİŞTİRİLMEDİ. `data/cleaning.py`, `data/adapters/yf_us.py`, `tools/data_audit.py`,
  `tools/build_snapshot.py` DEĞİŞTİRİLMEDEN yeniden kullanıldı. BIST v7.1-golden 3/3
  (golden-yolu dosyası dokunulmadı).

*Denetim sonu. Bu evren, D4US_CRITERIA.md'nin (item 2+3) benchmark referansının ve D4-US
spike'ının (item 4) tek veri kaynağıdır; koşumdan önce dondurulmuştur.*

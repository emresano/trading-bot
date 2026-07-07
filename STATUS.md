# Proje Durumu
> Tarihsel tur detayları: **STATUS_ARCHIVE.md** (tamamlanmış turların tam blokları + çözülmüş sorun/blok maddeleri).

Son güncelleme: 2026-07-07T16:00:00+03:00 (Europe/Istanbul)
Şu an: **P1 (D1 Rejim-Filtreli Çekirdek ÜRETİM PORTU) KOD İŞİ TAMAMLANDI —
kullanıcı/baş danışman değerlendirmesi bekliyor** (bkz. `BACKTEST_REVIEW_D1_PROD.md`,
KALICI KAYIT 8). D1 ailesi spike'tan üretim yığınına taşındı ("backtest=canlı aynı
fonksiyon"): `strategy/regime_core.py` (spike'a BAĞIMSIZ) + `strategy/family_registry.py`
(iki aile config'ten seçilebilir) + breaker (ALARM -%25/FREEZE -%40). MÜHÜRLÜ
kriterler A/B/C/D **4/4 GEÇTİ**: S1b'nin 67 anahtarlama tarihi BİREBİR, metrikler
bit-bit özdeş (CAGR/maxDD/Sharpe Δ=0), v7.1-golden 3/3 bayt-bayt, tarihsel FREEZE=0.
Faz 5'e geçilmedi, `mode`'a dokunulmadı, config/config.yaml DEĞİŞMEDİ.

Tamamlanan fazlar: Faz 1-3, Faz 4 (Backtest Harness — v1→v7, v7.1-golden) +
HARDENING.md Bölüm A + Teşhis v6 + Motor+veri v7 + EXPANSION.md E1 (Veri Temeli)
+ Portföy ablasyon (+ R1) + S1 + S1b (D1 spike'ları) + **EXPANSION.md E2 (Motor
Genelleştirme)** + **P1 (D1 üretim portu)**. (Her turun tam detayı: STATUS_ARCHIVE.md.)

## Şu an neredeyiz (özet)
- D1 ailesi KABUL EDİLDİ (KALICI KAYIT 6) ve ÜRETİM PORTU tamamlandı (P1, KALICI
  KAYIT 8) — S1b'yle bit-bit özdeş, v7.1-golden korundu, tam süit 378 passed.
- Sıradaki iş **kullanıcı onayına bağlı**: canlı/paper emir katmanı Faz 5
  (HARDENING B onayı) — PaperBroker/AlgoLab hem 10-gate hem regime_core ailesini
  sürebilmeli. E-hattında sıradaki adım E3 (broker spike + karar), "E3 onaylandı"
  ayrı gerekir.
- İki durma noktası (Faz 4 backtest değerlendirmesi + gerçek sermaye) kullanıcıda;
  hiçbir eşik/parametre değiştirilmedi.

## KALICI KAYIT 1 — Başarı Çıtası (kullanıcı kararı, 2026-07-06)
USD bazında CAGR > 0 taban şart; Sharpe > XU100 al-tut Sharpe VE max DD ≤
endeks max DD'sinin yarısı. Resmi walk-forward kabul kriterleri değişmedi;
güncellemesi yeniden-tasarım turunda ayrı onayla.

**Durum (ABLATION_PORTFOLIO.md'den, 2026-07-06 ölçümü): hiçbir varyant
(baseline dahil) bu çıtayı geçmiyor** — tüm varyantlar USD CAGR ≈ -%15.7 ile
-%16.2 arası (TRY'nin USD karşısındaki yapısal değer kaybı baskın; stratejinin
TRY-bazlı performansından bağımsız). max DD/endeks-DD oranı ise ÇOK iyi
(0.106-0.172 — endeksin altıda/beşte biri) — bu kısım geçiyor, USD-CAGR
kısmı geçmiyor.

## KALICI KAYIT 2 — Haber/Olay Politikası Güncellemesi (kullanıcı kararı, 2026-07-06)
Yapılandırılmamış haber (LLM/Tier 1) veto-only kalır. Deterministik olay
verisi (earnings takvimi/sürprizi, Tier 0) giriş tarafında KULLANILABİLİR —
yalnızca backtest edilebilir, tek-değişiklik-turu ve aynı kabul
kriterlerinden geçen bir gate/özellik olarak; ilk aday US sleeve (E1: earnings
tarihçesi 2001'e kadar mevcut, bkz. DATA_AUDIT_US.md). İmplementasyon
yeniden-tasarım/E-fazlarında, şimdi değil.

## KALICI KAYIT 3 — BIST Hükmü (2026-07-06, kullanıcı delegasyonuyla baş danışman kararı)
Mevcut 10-gate ailesi BIST'te başarı çıtası (B) yolu olarak REDDEDİLDİ; huni
DONDURULDU (eşik değişikliği yok, referans + E4/ABD adil testi için
saklanıyor); yeni yön: rejim-filtreli çekirdek maruziyet (D1 tasarımı); E2 ön
şartı AÇILDI. İki durma noktası kullanıcıda.

## KALICI KAYIT 4 — S1 Spike Sonucu (2026-07-06)
D1 tasarımının (rejim-filtreli çekirdek) tek-tur değerlendirme spike'ı
tamamlandı — bkz. `REGIME_CORE_S1.md`. **Mühürlü kabul tablosu: 4 kriterden
2'si GEÇTİ (TRY Sharpe>XU100 Sharpe; uçurum kontrolü temiz), 2'si DAR
FARKLA GEÇMEDİ** (tam-dönem max DD -%33.50, gerekli ≤-%31.72; OOS
aylık-Sharpe VE OOS max DD, 12-sembol sepeti al-tut'a karşı her ikisi de
başarısız). USD CAGR bilgilendirici olarak POZİTİF (+%5.08) ama USD max DD
çok kötü (-%75.03 — nakit dönemlerinde bile TRY devalüasyonu USD değerini
eritiyor). Bu bir üretim implementasyonu DEĞİL, bir spike'tı — kabul/red/
iterasyon kararı kullanıcının/baş danışmanın; bu turda hiçbir parametre
ayarı yapılmadı.

## KALICI KAYIT 5 — S1b Ölçüm Tamamlama Sonucu (2026-07-07)
Nakit-getiri düzeltmesi (rejim KAPALI günlerde TRY gecelik faizi tahakkuku,
200bp kırpmalı) eklendi — **tek davranış değişikliği**, N=200/b=%1/M=3 ve
maliyetler AYNEN kaldı. Sonuç — bkz. `REGIME_CORE_S1B.md`: **Mühürlü kabul
tablosunun 4 kriterinin TAMAMI GEÇTİ** (S1'de 2/4 idi):
1) TRY Sharpe 1.215 > XU100 Sharpe 0.851 — GEÇTİ (S1'de de geçmişti).
2) Max DD -%28.43 ≤ gerekli -%31.72 — **YENİ GEÇTİ** (S1'de -%33.50 ile dar
   farkla geçmemişti).
3) OOS aylık-Sharpe 1.068>0.972 VE OOS max DD -%24.55≤-%28.12 — **YENİ
   GEÇTİ** (S1'de ikisi de başarısızdı).
4) Uçurum kontrolü temiz — GEÇTİ (S1'de de geçmişti).

**Kullanıcının ÖNCEDEN belirlediği kurala göre** ("4/4 geçerse aile kabul
adayı, herhangi biri kalırsa aile reddedilir — üçüncü bakış yok"): **bu
mekanik sonuç D1 ailesini bir KABUL ADAYI yapıyor.** Bu, Claude Code'un
kendi hükmü DEĞİL — kullanıcının önceden koyduğu kuralın mekanik
uygulanmasıdır. **Nihai kabul/red/üretime geçiş kararı hâlâ kullanıcının/
baş danışmanın** — otomatik olarak Faz 5'e/E2'ye geçilmedi, geçilmeyecek.

Önemli nüanslar (dürüst rapor, karar etkilenmeden): (a) USD-terimde
filtrenin Sharpe üstünlüğü TERSİNE dönüyor — 12-sembol sepeti al-tut'un USD
Sharpe'ı (0.577) stratejininkinden (0.435) yüksek; "başarı" tanımı para
birimine göre değişebilir. (b) TRY_ON_RATE kaynağı TCMB'nin kendisi değil,
OECD/FRED rebroadcast'i (TCMB EVDS'ye erişim yok — kimlik bilgisi
bulunamadı); 9 aylık bir veri boşluğu (2023) forward-fill ile dolduruldu.
(c) Drawdown epizot TOPOLOJİSİ nakit getirisiyle değişti (bazı epizotlar
ikiye ayrıldı, en kötü epizodun kimliği değişti) — bu METODOLOJİK bir
gözlem, veri hatası değil.

## KALICI KAYIT 6 — D1 Ailesi KABUL EDİLDİ (2026-07-07, baş danışman kararı)
D1 (rejim-filtreli çekirdek) ailesi, önceden mühürlenen kurala göre (S1b
4/4) baş danışman kararıyla **KABUL EDİLDİ** (2026-07-07). Bu, KALICI KAYIT
5'in mekanik "kabul adayı" tespitinin RESMİ, otoriter sonucudur — Claude
Code'un kendi hükmü değil, kullanıcının/baş danışmanın kararı. Ölçüm:
`REGIME_CORE_S1B.md` (nakit-getiri düzeltmeli).

**Kabulle kayda giren çekinceler**:
(a) USD Sharpe'ta 12-sembol sepeti al-tut üstün — BIST-içi çözülemez, US
    sleeve gündemi (EXPANSION.md).
(b) Faiz kaynağı FRED/OECD (TCMB'nin kendisi değil) — real öncesi EVDS
    çapraz doğrulaması kuyruğa alındı (bkz. aşağı, madde 1).
(c) Bilgilendirici -%20 DD hedefi (KALICI KAYIT 5'teki mühürlü tablonun
    "bilgi" satırı) tutmadı — mühürlü/resmi kriter değil, yalnızca not.

**Yeni ailenin operasyonel breaker kararı** (D1 üretim implementasyonu için):
- **ALARM eşiği: -%25** (bildirim, işlem durdurmaz).
- **FREEZE eşiği: -%40** (yeni ENTER yok; reset yalnızca kullanıcı elle).
- Gerekçe: S1/S1b birleşik tarihsel zarf (en kötü gözlenen -%33.5, S1'in
  faizsiz ana koşumu) + ~6.5 puanlık marj FREEZE eşiğine kadar. Tarihsel
  tetiklenme sayısı: **0** (ne S1 ne S1b'de -%40'a yaklaşan bir epizot yok).

**Üretim implementasyonu AYRI bir onaylı turdur** (E2 sonrası,
"backtest=canlı aynı fonksiyon" ilkesiyle, CLAUDE.md Bölüm 3.1). **İki
durma noktası kullanıcıda kalmaya devam ediyor** — bu kabul kaydı Faz 5'e
veya E2'ye otomatik geçiş anlamına GELMEZ.
[NOT: Üretim portu P1 turunda tamamlandı — bkz. KALICI KAYIT 8.]

**Kuyruğa eklenen iki madde** (real-öncesi / üretim-turu gündemi):
1. EVDS API anahtarı temin edilip TRY_ON_RATE'in TCMB'nin resmi kaynağıyla
   çapraz doğrulanması — real moda geçmeden ÖNCE tamamlanmalı.
2. Üretim turunda nakit bacağının GERÇEK enstrümanı netleştirilecek
   (AlgoLab'da para piyasası fonu/repo süpürme mekanizması var mı, hangi
   oranla, hangi likidite/vade kısıtlarıyla) — şu anki %0/faizli model
   yalnızca bir YAKLAŞIKLIK, gerçek enstrüman farklı davranabilir.

## KALICI KAYIT 7 — EXPANSION E2 (Motor Genelleştirme) tamamlandı (2026-07-07)
Çok-piyasa çekirdeği kuruldu (bkz. `EXPANSION_E2.md`), **DEMİR KURAL korundu:
her E2 commit'i BIST v7.1-golden'ıyla BAYT-BAYT aynı** (tests/test_golden_bist.py,
iki katman: cost_model=None + BIST CostModel carry=0). Tam süit 364 passed
(E2 öncesi 309). Kod işi tamam, kullanıcı/baş danışman değerlendirmesi bekliyor;
E3/E4/Faz 5'e geçilmedi.

**Kalıcı düzeltmeler/kararlar** (gelecek oturumlar için):
- **Hayalet-bar tarihi düzeltmesi**: EXPANSION 15.2 (04-08) ve E2 talimatı (04-09)
  "XIST tatili" varsayımı HATALI; gerçek 2024 Ramazan Bayramı XIST tatilleri
  **04-10/11/12**. Repodaki gerçek hayalet bar EREGL 2024-04-09 bir volume=0
  phantom'dur (data/cleaning.py yakalar), takvim katmanının sınıfı değil. Test
  gerçek tatilleri çapa aldı.
- **Bilinçli kapsam kararı (Bölüm 8'e uygun)**: run_backtest LONG-only bırakıldı;
  engine-seviyesi SHORT execution short-gate tasarımından (Bölüm 17 #10) sonra.
  Short MEKANİĞİ risk/direction.py'de tam test edilerek kuruldu (ayna simetrisi,
  quote-ccy, marjin). two_sided profiller short-gate tanımlanana dek aktive edilmez.
- **Ertelenenler (Faz 5 modülleri henüz yok)**: PaperBroker daily_carry, journal
  market/currency kolonları. İnşa edilince eklenecek.
- **exchange_calendars==4.13.2** eklendi (req.txt + lock birlikte). lxml eklenmedi.
- **FX boyutlama IEEE754 float duyarlı** (belgelendi): EURUSD-direkt 9374 vs
  USDJPY-conv 9375 (±1 birim, ikisi de mekanik doğru).

## KALICI KAYIT 8 — D1 üretim portu (P1) tamamlandı (2026-07-07)
KALICI KAYIT 6 ile kabul edilen D1 ailesi, spike'tan (`backtest/regime_core.py`,
REFERANS kalır) üretim yığınına taşındı ("backtest=canlı aynı fonksiyon").
Referans ölçüm REGIME_CORE_S1B.md. Bkz. `BACKTEST_REVIEW_D1_PROD.md`.
- `strategy/regime_core.py`: üretim regime-core, spike'a BAĞIMSIZ. Saf sinyal +
  saf boyutlama (TAM-LOT/artık nakit) + cash-yield + breaker.
- `strategy/family_registry.py`: StrategyFamily soyutlaması (ten_gate/regime_core,
  config'ten seçilebilir; ten_gate run_backtest'i delege eder → golden korunur).
- `backtest/run_family.py`: aile-dispatch + S1b mutabakatı.
- **Breaker (bu aile)**: ALARM -%25 (bildirim), FREEZE -%40 (yeni ENTER yok,
  çıkış serbest, reset yalnız kullanıcı). Tarihsel FREEZE=0; ALARM 4 sığ epizot
  (bildirim-only, davranış değişmez).

**MÜHÜRLÜ KRİTERLER 4/4 GEÇTİ** (mekanik doldurma; kabul kararı kullanıcının):
A) 67 anahtarlama tarihi S1b ile BİREBİR. B) CAGR/maxDD/Sharpe Δ=0 (bit-bit;
tam-lot spike'ta zaten modelli → sapma yok). C) v7.1-golden 3/3 bayt-bayt. D)
tarihsel FREEZE 0 + kuru-test yeşil. Hiçbir eşik/parametre değişmedi; Faz 5'e
geçilmedi, mode'a dokunulmadı. İki durma noktası kullanıcıda.

## Son tur (P1) — kısa özet
- Üretim modülü + family registry + sürücü + breaker + 14 test (kriter A/B/D +
  breaker kuru-test + tam-lot boyutlama + family registry), her commit golden-kanıtlı.
- Kapanış: BACKTEST_REVIEW_D1_PROD.md, STATUS güncelleme (KALICI KAYIT 8 + kuyruk
  eki), tam süit 378 passed, git push. Tag: `regime-core-d1-prod`.

## Sırada
**P1 (D1 üretim portu) KOD İŞİ TAMAMLANDI** — kullanıcı/baş danışman
değerlendirmesi bekliyor (`BACKTEST_REVIEW_D1_PROD.md`, KALICI KAYIT 8). Otomatik
GEÇİŞ YOK. Üç paralel konu:
(a) **BIST hattı**: D1 KABUL EDİLDİ (KAYIT 6) + ÜRETİM PORTU TAMAM (P1, KAYIT 8);
S1b'yle bit-bit özdeş, golden korundu. **Sıradaki iş kullanıcı onayına bağlı**:
canlı/paper emir katmanı Faz 5 (HARDENING B onayı) — PaperBroker/AlgoLab
regime_core ailesini de sürebilmeli. **[real-öncesi kuyruk, B1] Canlı takvim
gerçeği**: yarım-gün seanslar ve idari-izin köprü tatilleri için canlıda takvim
kütüphanesine (exchange_calendars) GÜVENİLMEZ — resmî kaynak (BIST/Borsa İstanbul
duyuruları) + veri-yok toleransı gerekir; canlı döngü bir günü yanlış "işlem günü"
sayarsa regime-core o gün hatalı sinyal/yürütme üretebilir.
(b) **EXPANSION.md**: E1 + E2 TAMAMLANDI. Sıradaki E-fazı **E3 (broker adapter
spike + karar)** — "E3 onaylandı" AYRI gerekir. E3/E4'e taşınan açık maddeler:
SEC/TAF+swap resmî doğrulama, US hesap tipi kararı, short gate seti tasarımı
(Bölüm 17 #10, FX aktivasyonu öncesi), US instruments[] config'e girişi,
econ/earnings gerçek parquet dosyaları. Ertelenenler (Faz 5 modülleri inşa
edilince): PaperBroker daily_carry, journal market/currency kolonları,
engine-seviyesi SHORT execution (short-gate sonrası).
(c) **Ablasyon + S1/S1b + P1**: TAMAMLANDI. Kalan işler (EVDS çapraz doğrulama,
üretim nakit bacağı enstrümanı) real-öncesi/üretim kuyruğunda (KAYIT 6 + aşağıda 18-19).

## Bilinen sorun/blok (aktif)
> Çözülmüş / üstü çizili maddeler (2, 3, 4, 8, 10, 14, 16) **STATUS_ARCHIVE.md**'ye
> taşındı. Orijinal numaralandırma korundu (boşluklar bilinçli).

1. **Kullanıcı onayı bekleniyor (Durma Noktası 1, BIST)** — kasıtlı, aşılamaz kapı.
5. Breaker (10-gate), mevcut sıkı parametrelerle gerçekleşmiş max drawdown'u
   SINIRLAMIYOR (yalnızca sonraki girişleri engelliyor) — tasarım gereği
   (FREEZE≠FLATTEN); v7'de max DD zaten breaker eşiğinin altında, breaker hiç
   tetiklenmiyor. (D1 ailesinin AYRI breaker'ı: KALICI KAYIT 6/8.)
6. **10-gate walk-forward kabul kriteri GEÇMEDİ, MC worst-5% (dd_p5=-%10.29)
   breaker eşiğine yakın** — motor/veri bug'ı değil, 10-gate stratejisinin kendi
   zayıflığı (huni DONDURULDU, KALICI KAYIT 3). D1 ailesi bu yolun yerine geçti.
7. KCHOL 2007-06-08 hâlâ açıklanamadı (DATA_AUDIT_v2.md "açıklanamayan gap" —
   dış BIST/KAP doğrulaması gerekiyor).
9. `.gitignore`'da genel `.env`/`*.log` deseni eksikliği (A3'ten, düşük öncelik).
11. **`oanda.py` hiçbir practice hesapla test edilmedi** (referans implementasyon)
    — E3'te doğrulanacak. E1'in FX snapshot'ı `yf_fx.py`'den üretildi.
12. **Ekonomik takvim vetosu (FX) backtest'te modellenemez** — tarihsel arşiv yok
    (Bölüm 10.4 fallback devrede; is_blackout altyapısı E2'de kuruldu, veri yoksa
    (False,"…") döner → backtest vetosuz).
13. US evreni survivorship yanlılığı taşıyor (bilinen, kabul edilen — DATA_AUDIT_US.md).
15. **Hiçbir 10-gate varyant USD-CAGR>0 başarı çıtasını geçmiyor** (KALICI KAYIT 1)
    — TRY'nin USD karşısındaki yapısal değer kaybı baskın. max DD/endeks-DD oranı İYİ.
17. Golden regresyon çapası `backtest-v7.1-golden` — `runtime/backtest_reports_v7_1/
    trades.csv` (commitli, `.gitignore` istisnası). E2+ her commit bayt-bayt kıyaslar.
18. **[real-öncesi kuyruk] EVDS API anahtarı + TRY_ON_RATE'in TCMB resmi kaynağıyla
    çapraz doğrulanması** — şu an FRED/OECD rebroadcast'i (KALICI KAYIT 6), gerçek
    paraya geçmeden ÖNCE tamamlanmalı.
19. **[üretim-turu kuyruğu] D1 nakit bacağının GERÇEK enstrümanı** netleştirilecek
    (AlgoLab para piyasası fonu/repo süpürme; oran/likidite/vade). Şu anki
    %0/faizli model yalnızca bir yaklaşıklık.

## Önceki fazlardan taşınan varsayımlar
pandas-ta yerine pandas-ta-classic + numpy 2.2 (e31e401); BIST seans saatleri
yaklaşık; backtest degrade modda; compute_target max(resistance, fallback)
(67d2dd6); gate_trigger_4h degrade modda son-3-bar-pattern VEYA breakout (67d2dd6);
walk-forward date_range/precomputed_features (60a6d3f); adx_min=25 (d6ea8fc); 12
sembol evreni + 2005-01-01 + OHLC tolerans fix'i (dc56ed2); HARDENING.md Bölüm A
(eb3b21d); breaker backtest entegrasyonu + MC dd_p5 düzeltmesi (c906d10, 53ba4b3);
v7 motor+veri düzeltme turu (5227438); EXPANSION.md eklendi (d0ab81d); E1 veri
temeli (US/FX adapter'ları, snapshot'lar, DATA_AUDIT_US/FX.md, data/events.py);
portföy ablasyon (disabled_gates + pending_exits determinizm düzeltmesi);
EXPANSION E2 (MarketSpec/CostModel/gate_registry/calendars/Direction, golden çapa,
exchange_calendars); P1 (strategy/regime_core.py + family_registry, D1 üretim portu).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

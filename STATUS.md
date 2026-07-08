# Proje Durumu
> Tarihsel tur detayları: **STATUS_ARCHIVE.md** (tamamlanmış turların tam blokları + çözülmüş sorun/blok maddeleri).

Son güncelleme: 2026-07-08T20:10:00+03:00 (Europe/Istanbul)
Şu an (EXPANSION hattı): **D2US-S1 (KESİTSEL MOMENTUM AİLESİ tasarım+spike) TAMAMLANDI —
kullanıcı/baş danışman değerlendirmesi bekliyor** (bkz. `D2_US_S1.md` + `D2US_CRITERIA.md`
+ KALICI KAYIT 18). Yeni US-only aile **D2-US (12-1 kesitsel momentum + FIP + mutlak-
momentum kapısı + vol-hedefleme)** koşumdan ÖNCE TEK paket mühürlendi; MEKANİK doldurma
(referans=sepet): **mühürlü tablo 1/4** (yalnız 3b tam-dönem maxDD; Sharpe 0.725<0.804,
CAGR 10.87%<13.84%, OOS Sharpe 0.770<0.831) → **önceden mühürlenen kurala göre D2-US
US-referansta kabul adayı DEĞİL** (HÜKÜM değil — karar kullanıcının/baş danışmanın).
Offline; `mode: paper` + TÜM canlı bot modülleri + S1/S1b/E4 araçları DOKUNULMADI;
grid/varyant seçimi YOK; v7.1-golden her commit 3/3. Faz 6/real/launchd/go_live'a adım
YOK. (E4b kapanışı: KAYIT 16. F5 paper hattı ayrı.)

--- Önceki oturum (F5 paper hattı, bu turda DOKUNULMADI) ---
Mikro-düzeltme (yalnız EOD gösterimi): `notify/eod_summary.py`'de "Rejim" (compute_regime_
signal çıktısı) ve "Pozisyon" (broker'da sepet var mı) tek, yanlış birleştirilmiş satırda
karışıyordu — observe modda pozisyon HER ZAMAN NAKİT olduğu için rejim ON iken bile "NAKİT
(rejim OFF)" basılıp üstteki [GÖZLEM] başlığıyla çelişiyordu. Artık iki AYRI satır: "Rejim:
ON/OFF" + "Pozisyon: NAKİT/SEPETTE (observe — hesap başlatılmadı)". `strategy/regime_core.py`
DOKUNULMADI; 4 yeni test; tam süit 511 passed, golden 3/3.

Operatör aksiyonu (kod değişikliği YOK): ilk gerçek DATA_DRIFT vakası (2026-07-07, 3 bar —
ASELS/EREGL/TUPRS, temettü/split izi YOK) `--resync` ile giderildi (4 sembol 1'er bar,
kompozit parite ≈0); doğrulama cycle'ı DATA_DRIFT'siz + EOD Telegram'a gitti. Detay:
`PHASE5B2A_REVIEW.md` "B2a.1 Eki — İlk gerçek DATA_DRIFT vakası + resync sonucu".
Şu an: **FAZ 5 (PAPER) — F5-B2a.1 (TELEGRAM TEŞHİS + SESSİZ DÜŞÜŞ SERTLEŞTİRME) TAMAMLANDI —
kullanıcı/baş danışman değerlendirmesi bekliyor** (bkz. `PHASE5B2A_REVIEW.md` "B2a.1 Eki").
Kök neden: gerçek Telegram kimlik bilgileri kodun okuduğu `config/secrets.env` DEĞİL, repo
kökündeki farklı bir `secrets.env`'e yazılmıştı (3 kez tekrarlandı — OPERATOR_GUIDE §0'a
belirgin uyarı eklendi) + token değerinde 2 kez BotFather kopyalama artefaktı (gömülü
boşluk). `--test-telegram` CLI eklendi + GERÇEK uçtan-uca doğrulandı (kullanıcı telefonunda
onayladı) + manuel observe cycle EOD özeti gerçekten Telegram'a gitti. Sessiz-düşüş
sertleştirmesi: `telegram.enabled=true` ama token/chat_id okunamazsa artık belirgin WARN +
EOD/heartbeat_status.json'da kalıcı "TELEGRAM: ACTIVE/LOG-ONLY(neden)" satırı. `.gitignore`
genel `secrets.env`/`*.env`/`runtime/manual/` deseni (STATUS #9 KAPANDI). **Güvenlik notu:**
bir teşhis komutu yanlışlıkla gerçek token'ı bu oturumun çıktısına yazdırdı → kullanıcı
BotFather'da token'ı iptal edip yeniledi (kullanıcı kararıyla). `mode: paper` DOKUNULMADI;
N/b/M mühürlü; D1 fonksiyonları + `data/snapshots/` DEĞİŞMEDİ; v7.1-golden her commit 3/3
bayt-bayt. Gelen Telegram komutu/long-poll YOK; ManualExecutionAdapter TASARIMI F5-B2'ye
kaldı. Faz 6 BAŞLATILMADI; go_live_date=null; launchd etkinleştirilmedi; Durma Noktası 2
kapalı. Tam süit: **507 passed** (F5-B2a 494 + 13 yeni).

**F5-B2a (önceki alt-tur, TAMAMLANDI):** 6 madde — gerçek Bot API sendMessage (m1), alarm+EOD
kablolama kuru-testi (m2), launchd K5-grace saat doğrulaması (m3), "bayat=muhafazakâr"
genelleme düzeltmesi (m4), GERÇEK EVDS CSV kıyası (m5), kapanış (m6). Detay: KALICI KAYIT 12.

**F5-B1.1 (gölge sertleştirme, K1-K9) daha önce tamamlandı** (bkz. `PHASE5B11_REVIEW.md`,
KALICI KAYIT 11): 9 madde, 485 passed.

**F5-B1 (gölge paper, GERÇEK yfinance EOD) daha önce tamamlandı** (bkz. `PHASE5B1_REVIEW.md`):
canlı depo↔backtest kompozit bit-bit 0.0; snapshot↔yfinance 66132 bar-günde ~1e-7; 470 passed.
**AlgoLab İPTAL** (2025-12-31; F5-B2=ManualExecutionAdapter — EK KAYIT aşağıda).

**F5-A (offline runtime iskeleti) daha önce tamamlandı** (bkz. `PHASE5A_REVIEW.md`):
9 aşama, fixture/kuru-testli, 456 passed.

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

## KALICI KAYIT 9 — Faz 5 (paper) kullanıcı onayıyla AÇILDI (2026-07-07)
Kullanıcı 2026-07-07'de **Durma Noktası 1'i AÇTI** — Faz 5 (paper) onaylandı.
**Kapsam yalnızca paper.** Durma Noktası 2 (paper→real) AYNEN kapalı — "real'e geç"
yolu kod/komut olarak **HİÇBİR ZAMAN var olmayacak** (HARDENING B6). Bağlayıcı spec:
HARDENING.md Bölüm B (B1-B7) + CLAUDE.md Bölüm 14. Koşulan aile: `regime_core` (D1,
KALICI KAYIT 6/8) — 10-gate ailesi (`ten_gate`) donmuş referans, paper'da KOŞULMAZ.

**F5-A ↔ F5-B kırılımı** (`PHASE5_PLAN.md`): F5-A'da AlgoLab'a CANLI BAĞLANTI YOK —
tüm modüller offline, fixture/kuru-testli. Kimlik bilgisi gerektiren canlı akış F5-B.
Aşamalar: F5A-0 plan/kayıt · F5A-1 canlı veri deposu · F5A-2 PaperBroker (t+1 kapanış
yürütme) · F5A-3 mutabakat+kurtarma · F5A-4 kill-switch hiyerarşisi · F5A-5 karar
günlüğü (JSONL) · F5A-6 parite · F5A-7 izleme+Telegram iskeleti · F5A-8 AlgoLab adapter
iskeleti · F5A-9 seans/takvim · F5A-Z kapanış (PHASE5A_REVIEW.md). Her aşama: commit +
golden kanıtı + push + STATUS.

**F5-A İLERLEME (canlı takip):**
- [x] F5A-0 plan/kayıt (0b6f600) — PHASE5_PLAN.md.
- [x] F5A-1 canlı veri deposu (cf26836) — `data/live_store.py` (LiveHistoryStore),
      8 test. SQLite; snapshot bootstrap + EOD arayüzü + çapraz-kaynak tutarlılık.
- [x] F5A-2 PaperBroker + runner (18406cf) — `execution/{broker_adapter,paper_broker,
      regime_core_runner}.py`, 11 test. **PARİTE KANITI**: runner switch'leri
      run_regime_core_prod ile BİREBİR, equity rel=1e-9. Nakit tahakkuku = regime_core
      formülü (modellenmiş faiz ayrı). Restart state kurtarma. Bracket stop-önceliği.
- [x] F5A-3 mutabakat + kurtarma (a1e44ef) — `safety/reconciliation.py` (LocalLedger +
      reconcile → FREEZE, adopt yalnız kullanıcı), "emir gönderildi/yanıt yok/çöküş"
      mock testli. 5 test.
- [x] F5A-4 kill-switch hiyerarşisi (b60ede0) — `safety/kill_switch.py` (5 switch),
      eşikler `config/regime_core.yaml::safety` (D1-uyarlı, ÖNERİ). 9 kuru-test.
- [x] F5A-5 karar günlüğü (2cec791) — `journal/{masking,decision_journal}.py`, D1-uyarlı
      JSONL şema, merkezî maskeleme, runner hook. 6 test.
- [x] F5A-6 parite (4335e21) — `safety/parity.py`, offline↔canlı anahtarlama diff =
      kırmızı alarm; equity farkı parite başarısızlığı sayılmaz. 3 test.
- [x] F5A-7 izleme + Telegram (2fda861) — `notify/{telegram_bot,eod_summary}.py`,
      `safety/heartbeat.py`. config-gated, token'sız, read-only vs çift-onay, 'real'
      komutu YOK, watchdog. 16 test.
- [x] F5A-8 AlgoLab adapter iskeleti (f1e8aab) — `execution/algolab/{auth,client,
      adapter}.py`, DOĞRULANMAMIŞ (F5-B'de resmî doküman), CANLI ÇAĞRI YOK, fixture. 12 test.
- [x] F5A-9 seans/takvim (970caa2) — `config/bist_calendar.yaml` + `core/bist_calendar.py`
      (2026 doğrulandı; sürekli 10:00-18:00; yarım-gün; kütüphane tek-otorite değil;
      veri-yok toleransı). clock.py 09:55→10:00 düzeltildi. 8 test.
- [x] F5A-Z kapanış — `PHASE5A_REVIEW.md` (aşama tablosu, B1-B7 kapsama, kuru-test
      sonuçları, F5-B kullanıcı-aksiyon listesi), tam süit 456, golden bayt-bayt, push.
**F5-A TAMAMLANDI — kullanıcı/baş danışman değerlendirmesi bekliyor. F5-B onayı AYRI.**

## KALICI KAYIT 10 — F5-B1 (Gölge Paper, AlgoLab'SIZ) tamamlandı (2026-07-07)
Gölge paper döngüsü broker olmadan GERÇEK veriyle çalışır hale getirildi (bkz.
`PHASE5B1_REVIEW.md`). Teslimatlar + commit'ler:
- **(1) yfinance veri bağlama** (`data/live_feed.py`, 8d1ca1c): LiveHistoryStore'u
  yfinance EOD'a bağlar; snapshot bootstrap'ı backtest-pariteli temizlikle
  (normalize_bist_dates + evren-ghost); snapshot↔yfinance çapraz-tutarlılık. **KANIT:**
  canlı depo↔backtest kompozit 5511 günde bit-bit 0.0; snapshot↔yfinance 66132 bar-günde
  ~1e-7; kompozit+MA(200) BUGÜNE (07-07) kadar hesaplanıyor. 6 test.
- **(2) gölge scheduler** (`main.py` PaperScheduler): observe (go_live=null: sinyal/
  journal/heartbeat, İŞLEM YOK, hesap başlatılmaz) / active (operatör kararı). yfinance
  EOD retry + 'bar yok' zarafeti; kill-switch + parite işi + EOD özet + Telegram (token'sız
  log-only) bağlandı. Mutabakat GÖLGE modda harici çekimi ATLAR + loglar (iç recon çalışır).
  8 test.
- **(3) ilk-başlatma** (`initialize_flat(adopt_regime_on)`): go-live'da rejim AÇIKSA t+1
  kapanışta INITIAL_ENTER (journal özel etiket), KAPALIYSA nakit+faiz. Geriye uyumlu şema
  migration. **Gerçek-veri dry-run:** go_live=07-06 → 07-07 INITIAL_ENTER (12 sembol,
  parite OK).
- **(4) launchd + log rot. + kılavuz** (`deploy/*.plist`, `deploy/tradingbot.newsyslog.conf`,
  `OPERATOR_GUIDE.md`): bot + watchdog servisleri, log rotasyonu (journal döndürülmez),
  başlat/durdur/durum/FREEZE-temizle + observe→active geçişi (Faz 6 başlangıcı ayrı karar).
- **(5) B7-D1 önerisi** (`B7_D1_PROPOSAL.md`): 'değerlendirilen sinyal'=günlük rejim
  değerlendirmesi; D1 karne alanları. Hiçbir eşik mühürlenmedi; ÖNERİ.
- **(6) EVDS** (`tools/evds_compare.py`, `EVDS_COMPARISON.md`): anahtar VAR ama REST endpoint
  evds2→evds3 SPA'ya yönlendiriyor → BLOCKED. **Snapshot DEĞİŞMEDİ.** endpoint doğrulanınca
  script yeniden koşulur (kuyruk #18).
- **(7) gözetimli ilk koşu:** gerçek CLI observe (işlem yok) + **oluşmakta olan bar bulgusu**
  → kod-düzeyi koruma eklendi (sinyal yalnız FİNAL bardan; provisional işareti).

**Kod-düzeyi yeni koruma (F5-B1):** oluşmakta olan (kapanmamış) bar üzerinde sinyal
finalize edilmez / active'de yürütme son FİNAL güne sınırlanır. t+1 yürütmeye EK katman.
Faz 6 BAŞLATILMADI (go_live_date=null); iki durma noktası kullanıcıda; mode/eşikler/D1
fonksiyonları + v7.1-golden korundu.

## EK KAYIT — AlgoLab KAPATILDI, F5-B2 yeniden tanımlandı (2026-07-07)
**AlgoLab 2025-12-31'de KAPATILDI** (resmî mail teyidi, 2026-07-07). Sonuçlar:
- **AlgoLab canlı entegrasyonu İPTAL.** `execution/algolab/` SİLİNMEDİ — "kapatılmış-broker
  referansı" docstring notuyla işaretlendi (BrokerAdapter/throttle/maskeleme deseni emsali).
- **F5-B2 yeniden tanımı:** `ManualExecutionAdapter` — bot sinyali → Telegram bildirimi →
  kullanıcı elle yürütür → fill'ler kullanıcı onayıyla kaydedilir; B2 mutabakatı bu kayıtlara
  karşı çalışır. (Tasarım F5-B2'de.)
- **Kuyruğa eklendi:** "BIST broker REST API pazarını periyodik izle — uygun API çıkarsa
  BrokerAdapter ile entegre edilebilir."
- Bu turda başka kapsam değişikliği YOK; Faz 6 başlatılmadı, real'e adım yok.

## KALICI KAYIT 11 — F5-B1.1 (Gölge Sertleştirme, K1 kapanış) tamamlandı (2026-07-08)
Gölge paper döngüsü sertleştirildi (bkz. `PHASE5B11_REVIEW.md`). 9 madde:
- **K1** `data/cash_rate_feed.py`: TRY_ON_RATE canlı ileri besleme (snapshot READ-ONLY +
  SQLite uzantı; bayat>35g→FRED, başarısız→son değer+WARN; formül backtest ile AYNI). EOD
  özet+heartbeat_status.json'a faiz+kaynak tarihi+bayatlık. GERÇEK: FRED de 2026-03'te
  bitiyor → faiz tasarım gereği bayat (muhafazakâr); zamanlı için EVDS (#18). tz bug düzeltildi.
- **K2** Kill-switch mutabakatı (`KILLSWITCH_RECONCILIATION.md`, ölçüm runtime/f5b1/
  killswitch_measurement.json): prod backtest worst gün −11.60%, max ardışık kaybeden RT=5,
  max DD −28.43. **consecutive_losses_freeze 4→7** (maks+2), **daily_loss_limit_pct 0.08→0.12**
  (worst altı) — config+kill_switch senkron; tarihsel tetik 0. (Bunlar operasyonel SAFETY
  eşiği, ÖNERİ; strateji parametresi/kabul eşiği DEĞİL — DEĞİŞMEZLER ihlali yok.)
- **K3** catch-up: downtime'da kaçan anahtarlama → DELAYED_SIGNAL alarmı+journal etiketi.
- **K4** veri kayması: detect_drift (son 30 bar) → DATA_DRIFT (finalize yok); operatör
  `--resync` (yedek+tam çekim+force-overwrite+otomatik kompozit parite). replace_bars eklendi.
- **K5** provisional-bar iki-yön + active erteleme testleri (grace=3600s).
- **K6** INITIAL_ENTER maliyet mutabakatı: 99943.96 KUSUR DEĞİL (kısmi basket/forming-bar);
  tam barda 99852.29 = 100000−comm−slip bit-bit. **Kök-neden hardening: veri-tamlığı yürütme
  kapısı** (tüm sembollerde bar yoksa yürütme ertelenir → kısmi basket yasağı).
- **K7** OPERATOR_GUIDE §7 resync + §8 bakım penceresi + dokunulmaz modül listesi.
- **K8** `tools/evds_compare.py --csv` elle-export modu (kuyruk #18 endpoint'siz kapatılabilir).
- **K9** B7_D1_PROPOSAL iki katmanlı karne (mekanik ≥4hafta + olay ≥2 tatbikat); tatbikat
  implementasyonu YAPILMADI (öneri).
Tam süit **485 passed** (F5-B1 470 + 15); golden 3/3 her commit. mode/N/b/M/snapshot/D1
fonksiyonları DEĞİŞMEDİ. Faz 6/real/launchd'ye adım YOK; iki durma noktası kullanıcıda.

## KALICI KAYIT 12 — F5-B2a (Telegram canlı bildirim + operasyon) tamamlandı (2026-07-08)
F5-B2'nin **bildirim yarısı** (bkz. `PHASE5B2A_REVIEW.md`). 6 madde, her biri ayrı commit:
- **m1** `notify/telegram_bot.py`: `make_http_sender` (Bot API sendMessage, timeout + 3 deneme
  + üstel bekleme; kalıcı hatada istisna). `TelegramNotifier` enabled+token(env)+chat_id ise
  HTTP kurar; hata YAKALANIR → logger WARN, send False → **günlük döngü ASLA kırılmaz**. Token
  YOKSA log-only AYNEN. main.py + watchdog logger bağlandı. 7 test (mock HTTP). Gerçek test
  mesajı: secrets.env TELEGRAM_TOKEN BOŞ → atlandı.
- **m2** Alarm+EOD kablolaması zaten mevcut (F5-B1); kuru-test eklendi (mock FREEZE + mock
  DATA_DRIFT → gönderim + journal alarm kanıtı; EOD gönderimi). 2 test.
- **m3** launchd K5-grace doğrulaması: paper plist 19:30 Istanbul (18:00+3600s=19:00 final,
  25dk marj; TR kalıcı UTC+3). Hatalı "~1.5s grace" yorumu düzeltildi. OPERATOR_GUIDE §2a
  zaman çizelgesi + 'bar yok' veri-tamlığı ertelemesi + koşu-içi retry yokluğu.
- **m4** "bayat=muhafazakâr" GENELLEME DEĞİL: yön faiz patikasına bağlı (yükseliş→muhafazakâr,
  DÜŞÜŞ→abartır/agresif). PHASE5B11_REVIEW + STATUS #18 düzeltildi. Kod değişikliği YOK.
- **m5** GERÇEK EVDS CSV (`runtime/manual/evds_export.csv`, TLREF 1860 satır) koşuldu.
  BULGU: EVDS sistematik ~2-6p YÜKSEK (seri-tanım farkı); 2023 boşluğu EVDS'de 12/12 DOLU
  (2023-11 baseline ff 23.5 vs EVDS 41.45); 2022-10 %9.0 baseline dip'i EVDS'de YOK (artefakt
  teyit). **Snapshot DEĞİŞMEDİ.** Araç fix: value_col otomatik seçimi boş 'Unnamed' kolonu
  alıp sessizce 0 satır okuyordu → sayısal-değerli son kolon (+1 test). Rapor: EVDS_COMPARISON.md.
- **m6** kapanış: bu kayıt + PHASE5B2A_REVIEW.md, tam süit 494 passed, golden 3/3, push.
Faz 6/real/launchd'ye adım YOK; iki durma noktası kullanıcıda.

## KALICI KAYIT 13 — F5-B2a.1 (Telegram teşhis + sessiz düşüş sertleştirme) tamamlandı (2026-07-08)
Kullanıcı gerçek Telegram token+chat_id'yi girdikten sonra bot bunları BOŞ görüyordu.
Teşhis + düzeltme + sertleştirme (bkz. `PHASE5B2A_REVIEW.md` "B2a.1 Eki"):
- **Kök neden**: kod (main.py/safety/heartbeat.py/tools/evds_compare.py/core/config.py)
  yalnızca `config/secrets.env`'i okur (hard-code path); kullanıcı değerleri **repo
  kökündeki farklı bir `secrets.env`'e** yazmıştı — format sorunu değil, YANLIŞ KONUM.
  Bu, oturum boyunca **3 kez tekrarlandı** (her BotFather güncellemesinde tekrar kök
  dizine yazıldı) → OPERATOR_GUIDE §0'a "doldurulacak dosya BUDUR, kök değil" uyarısı
  eklendi. Ayrıca token değerinde **2 ayrı seferde gömülü boşluk** bulundu (muhtemelen
  BotFather sohbet balonundan satır-kaydırmalı kopyalama artefaktı) — programatik
  temizlendi (değer hiçbir zaman yazdırılmadan).
- **`--test-telegram` CLI** (main.py): config yükler, `notifier_status()` ile durumu
  raporlar (ACTIVE/LOG-ONLY+neden), ACTİFse maskeli test mesajı gönderir, exit code
  yansıtır. OPERATOR_GUIDE §5a.
- **Sessiz-düşüş sertleştirme**: `telegram.enabled=true` ama token/chat_id okunamazsa
  artık (a) başlangıçta belirgin WARN journal'a düşer, (b) her EOD özetinde ve
  `heartbeat_status.json`'da kalıcı `TELEGRAM: ACTIVE` / `TELEGRAM: LOG-ONLY (neden)`
  satırı var — konfig-niyet ↔ çalışma-durumu uyuşmazlığı bir daha SESSİZ kalamaz.
  13 yeni test (notifier_status, EOD satırı, scheduler silent-drop, CLI 4 senaryo).
- **Secrets hijyeni (STATUS #9 KAPANDI)**: `.gitignore`'a genel `secrets.env`/`*.env`/
  `runtime/manual/` deseni eklendi (`config/secrets.env.example` istisna);
  `git log --all -- secrets.env` (+ `config/secrets.env`) ile hiçbir secrets dosyasının
  hiçbir commit'te yer almadığı doğrulandı.
- **GERÇEK uçtan-uca kanıt**: `--test-telegram` BAŞARILI (kullanıcı telefonunda mesajı
  doğruladı). Ardından gerçek bir manuel `--refresh --cycle` (observe, 2026-07-08) koşuldu:
  EOD özeti gerçekten Telegram'a gönderildi (`heartbeat_status.json`: `telegram.state=
  ACTIVE`, journal'da gönderim-hatası WARN'ı YOK). **Yan gözlem** (kapsam DIŞI, K4'ün
  ÖNCEDEN VAR olan davranışı): aynı cycle'da ASELS 2026-07-07 için 3 bar sapması
  DATA_DRIFT (CRITICAL) alarmı tetiklendi ve Telegram'a gitti — sinyal bu yüzden
  FİNALİZE EDİLMEDİ (observe modda zaten işlem yok, etkisi yok). Operatör isterse
  OPERATOR_GUIDE §7 `--resync` uygulayabilir; bu turun kapsamı dışında, aksiyon
  alınmadı.
- **Güvenlik olayı (dürüstçe kayıt)**: bir teşhis komutu (`xxd` ham dosya kontrolü)
  yanlışlıkla gerçek token değerini bu oturumun çıktısına yazdırdı (kural ihlali,
  fark edilir edilmez durduruldu). Kullanıcıya hemen bildirildi; kullanıcı BotFather'da
  token'ı **iptal edip yeniledi** (kendi kararıyla). Sonraki tüm teşhis yalnızca
  yapısal/maskeli kontrollerle (uzunluk, karakter sınıfı, HTTP durum kodu) yapıldı —
  değer bir daha hiçbir çıktıya yazılmadı.
Tam süit **507 passed** (F5-B2a 494 + 13 yeni); golden 3/3 her commit. `mode`/eşikler/
`regime_core.py`/`data/snapshots/` DEĞİŞMEDİ. Faz 6/real/launchd'ye adım YOK; iki durma
noktası kullanıcıda.

## KALICI KAYIT 14 — US otonomi hattı önceliklendirildi (kullanıcı kararı, 2026-07-08)
Kullanıcı 2026-07-08'de sıralamayı belirledi:
**US otonomi hattı önceliklendirildi: sıra E4 (US adil test) → geçerse US gölge
paper → geçerse E3 broker adapter (tam otonomi hedefi).**
- **BIST D1'de risk artırımı talebi disiplin #10 gereği REDDEDİLDİ**; D2 agresif
  profil, D1 GERÇEK sicili oluşana dek KAPALI.
- **BIST yarı-otomatik hat (ManualExecutionAdapter, F5-B2) DEĞİŞMEDİ** — bu karar
  onu ne hızlandırır ne değiştirir.
- E4 kapsamı: (A) dondurulmuş 10-gate ailesinin ABD'de adil referans testi
  (donmuş huni, hüküm yok), (B) D1'in (regime_core mantığı) US sepetinde spike'ı
  — USD-cinsi sleeve'in temeli. Offline araştırma; canlı bot modüllerine (mode:
  paper dahil) dokunulmaz; N/b/M mühürlü; v7.1-golden korunur.
- **Bu kayıt otomatik geçiş anlamına GELMEZ**: E4 sonrası US gölge paper'a geçiş,
  ve sonrasında E3, AYRI kullanıcı/baş danışman onayları gerektirir. İki durma
  noktası (Faz 4 backtest değerlendirmesi + gerçek sermaye) aynen kullanıcıda.

## KALICI KAYIT 15 — EXPANSION E4 (US ADİL TEST) tamamlandı (2026-07-08)
Offline araştırma turu (bkz. `EXPANSION_E4.md` + `E4_CRITERIA.md`). İki amaç:
(A) dondurulmuş 10-gate ailesinin ABD'de adil referansı, (B) D1 (regime_core)
mantığının US sepetinde spike'ı. **Mühürleme koşumdan ÖNCE** (ayrı commit
`cdf8100`, strateji kodu HENÜZ yokken); mühürlü tablo ESNETİLMEDİ.

**Kararlar/değişmezler:** N/b/M = 200/%1/3 mühürlü (S1b), AYNEN kullanıldı —
parametre taraması/varyant seçimi YOK (disiplin #3). Nakit bacağı = **%0
(muhafazakâr, madde 1)**: mevcut US aux faiz serisi yok → `cash_rate=None`
(S1b mekanizmasıyla %0'da bayt-eşdeğer). Referans benchmark = **eşit-ağırlık
US sepeti** (survivorship-şişirilmiş → yüksek çıta; SPY yalnız bilgilendirici).

**Veri:** US snapshot 2026-07-06 (20 sembol, 2005-01-03→2026-07-02, 5408 gün,
0 hayalet-bar). `load_and_clean_universe` DEĞİŞMEDEN reuse (normalize_bist_dates
US 00:00-UTC'de NO-OP; test'le çapa). SPY dondurulmuş snapshot (us_bench/
2026-07-08, sha256+manifest, deterministik).

**MEKANİK SONUÇ — mühürlü 4-kriter (referans=sepet):**
1) USD Sharpe > sepet 0.8561 → 0.726 **FAIL**.
2) tam-dönem |maxDD| ≤ 23.14% → 23.11% **PASS** (razor-thin).
3a) OOS aylık-Sharpe > sepet 0.9154 → 0.669 **FAIL**.
3b) OOS |maxDD| ≤ 14.96% → 20.41% **FAIL**.
→ **1/4 geçti; D1-US US-referansta kabul adayı DEĞİL** (önceden mühürlenen
"4/4 yoksa red, dar-fark yok" kuralının mekanik uygulaması — HÜKÜM değil).
4) Uçurum kontrolü: N/b/M komşuluğunda süreklilik, uçurum YOK; mühürlü nokta
komşuluğun ALT tarafında (US'e optimize EDİLMEDİ — overfitting-karşıtı gözlem).
D1-US ana: CAGR +8.19%, maxDD -23.11%, Sharpe 0.726, 57 switch; MC dd_p5 -33.5%.

**Bulgu (BIST-USD ile tutarlı):** regime-filtre drawdown'ı sepetin ~yarısına
indiriyor (sermaye-koruma tutuyor) ama survivorship-şişirilmiş sepetin
Sharpe'ını GEÇMİYOR — S1b (f)'deki USD-terim yapının birebir tekrarı. Not:
D1-US, SPY'a karşı (gerçekçi/kurulabilir endeks) Sharpe'ı GEÇİYOR (0.726>0.640)
ve DD çok daha sığ — ama mühürlü referans SEPET, değiştirilemez.

**10-gate US adil referansı (RAPOR-only, kabul kapısı DEĞİL):** 21 yılda
~düz-negatif (CAGR -%0.11, Sharpe -0.089, PF 0.88, %94.5 nakit) → BIST'te
reddedilen ailenin US'te de zayıf olduğunun teyidi (bilinen-sorun #6 tutarlı).

**İzolasyon:** `mode: paper` + canlı bot modülleri (strategy/regime_core.py,
execution/, safety/, data/live_*, notify/, main.py, config/regime_core.yaml,
config/config.yaml) DOKUNULMADI. S1/S1b simülatörü (backtest/regime_core.py)
DEĞİŞMEDİ — yeni US döngüsü (backtest/regime_core_us.py) onu İTHAL eder; parite
~3e-15. v7.1-golden 3/3; tam süit **517 passed** (511+6). **Karar
kullanıcının/baş danışmanın; otomatik geçiş YOK; iki durma noktası kullanıcıda.**

## KALICI KAYIT 16 — EXPANSION E4b (D1-US nakit bacağı ölçüm-tamamlama) tamamlandı (2026-07-08)
E4'ün (KAYIT 15) S1→S1b emsali nakit-getiri düzeltmesi (bkz. `EXPANSION_E4B.md`).
**Tek davranış değişikliği = nakit tahakkuku:** US 3-aylık T-bill (FRED DGS3MO,
günlük, dondurulmuş `data/snapshots/aux_us/2026-07-08/`, sha256'lı; 5380 gözlem,
max boşluk 4g, uzun boşluk 0), **50bp haircut** (muhafazakâr — para-piyasası fonu
gider+sürtünme; gerekçe koşumdan ÖNCE mühürlendi). Tahakkuk = S1b/TRY yapısı
(r_net=max(rate−haircut,0), ACT/365).

**SON-BAKIŞ KURALI** (koşumdan ÖNCE `E4_CRITERIA.md` §4'e mühürlendi, ayrı commit):
D1-US'in aynı tarihçeye İKİNCİ ve SON bakışı; E4 mühürlü tablosu/eşikleri/referansı
(SEPET) AYNEN; benchmark değişikliği/SPY'a geçiş YASAK (kriter-alışverişi). 4/4
geçerse US-kabul adayı; herhangi biri kalırsa KESİN RED, üçüncü bakış YOK.

**AYRIŞTIRMA (faizin izole katkısı, tek-değişiklik — switch'ler 57'de BİREBİR AYNI):**
nakitte %24.3 gün; CAGR 8.19→**8.60%** (+0.41pp); Sharpe 0.726→**0.758** (+0.032);
maxDD ~değişmedi (−4e-5 marj daha derin — düşüş-öncesi tepe yükseldi). US nakit-only
CAGR ~%1.51 (S1b'deki TRY ~%13.77'nin niceliksel karşıtı — faiz KÜÇÜK).

**MÜHÜRLÜ TABLO (E4b faizli, MEKANİK, referans=sepet):** 1) Sharpe 0.758 > 0.8561?
**FAIL**. 2) |maxDD| 23.11% ≤ 23.14%? **PASS** (razor-thin). 3a) OOS Sharpe 0.692 >
0.9154? **FAIL**. 3b) OOS |maxDD| 20.42% ≤ 14.96%? **FAIL**. → **1/4 (E4 ile AYNI
tablo).** Faiz Sharpe'ları itti ama survivorship-şişirilmiş sepetin ~0.10 puan
çıta açığını kapatmadı. MC(faizli) dd_p5 -32.6%.

**→ MEKANİK SONUÇ (SON-BAKIŞ KURALININ uygulaması): D1-US ailesi US-referansta
KESİN REDDEDİLDİ. Dönüş yolu KAPALI.** D1 mantığı ancak gelecekte AYRI bir
tasarımın (farklı çekirdek/evren) risk-katmanı adayı olarak, YENİ ve ayrıca
mühürlenmiş kriterlerle gündeme gelebilir — D1-US ailesinin kendisinin yeniden
değerlendirilmesi DEĞİL. Bu bir HÜKÜM değil, önceden mühürlenen kuralın mekanik
sonucudur; nihai kayıt kullanıcının/baş danışmanın.

**İzolasyon:** `mode: paper` + canlı bot modülleri + `backtest/regime_core.py`
(S1/S1b simülatörü) + config/config.yaml + config/regime_core.yaml DOKUNULMADI.
Yeni: `tools/build_us_rate_snapshot.py`, `tools/run_regime_core_us_e4b.py`,
`backtest/regime_core_us.py`'ye haircut param (default 0.02=S1b; cash_rate=None iken
etkisiz → E4 %0 reprodüksiyonu korundu). v7.1-golden 3/3; tam süit **522 passed**
(517+5). Faz 6/real/launchd/go_live'a adım YOK; iki durma noktası kullanıcıda.

## KALICI KAYIT 17 — D2-US (kesitsel momentum ailesi) tasarım+spike turu AÇILDI (2026-07-08)
**Baş danışman kaydı (2026-07-08): D1-US KESİN RED onaylandı (E4b, son-bakış kuralı).
D2-US (kesitsel momentum) tasarım+spike turu AÇILDI — US-only, otonomi hedefli hat.**

D1-US'in (rejim-filtreli çekirdek) US-referansta kesin reddi (KAYIT 16, mühürlü tablo
1/4) üzerine, D1 mantığının US'e "geri dönüşü" DEĞİL — YAPISAL YENİ bir aile açıldı:
**D2-US = 12-1 kesitsel (cross-sectional) momentum + FIP information-discreteness seçimi
+ pozisyon-bazlı mutlak-momentum (dual-momentum) nakit kapısı + 6-ay realize vol hedefleme.**
Getiri-arayan bir aile (D1 sermaye-koruma odaklıydı); bu yüzden kriter 2 = CAGR>sepet
bir VARLIK şartıdır (E4/D1'de yoktu).

**Turun disiplini (E4 izolasyonu AYNEN):**
- Offline araştırma. `mode: paper` + TÜM canlı bot modülleri (strategy/regime_core.py,
  execution/, safety/, data/live_*, notify/, main.py, config/config.yaml,
  config/regime_core.yaml) + S1/S1b/E4 araçları (backtest/regime_core.py,
  backtest/regime_core_us.py, tools/run_regime_core*.py, tools/e4_common.py,
  config/regime_core_us.yaml) DOKUNULMAZ.
- BIST v7.1-golden her commit 3/3 bayt-bayt. Her madde AYRI commit + push.
- **Grid/varyant SEÇİMİ YASAK** (disiplin #3): tasarım TEK paket olarak, koşumdan ÖNCE
  mühürlenir; koşum sonucuna göre bileşen seçilmez. Ablasyon YALNIZ bilgi/atıf amaçlı.
- **Benchmark referansı koşumdan ÖNCE mühürlenir, sonradan DEĞİŞTİRİLEMEZ** (E4 §4 emsali).
- HÜKÜM YOK; kabul kararı kullanıcının/baş danışmanın. Faz 6/real/launchd/go_live adımı YOK;
  iki durma noktası kullanıcıda.

Sıra (her biri ayrı commit): (0) bu kayıt → (1) US2 evreni ~50 sembol dondurma +
DATA_AUDIT_US2.md + survivorship → (2) benchmark (US2 eşit-ağırlık sepet + SPY bilgi) +
D2US_CRITERIA.md MÜHÜR → (3) tasarım sabitleri (aynı mühür commit'i) → (4) spike koşumu +
mekanik tablo + crash/turnover/ablasyon/komşuluk → (5) D2_US_S1.md + kapanış. **DUR.**

## KALICI KAYIT 18 — D2US-S1 (kesitsel momentum spike) TAMAMLANDI (2026-07-08)
D2-US (kesitsel momentum) ailesinin tek-tur değerlendirme spike'ı tamamlandı (bkz.
`D2_US_S1.md`, `D2US_CRITERIA.md`, `DATA_AUDIT_US2.md`). Tasarım koşumdan ÖNCE TEK
paket olarak mühürlendi (E4 §4 kilidi emsali); grid/varyant seçimi YAPILMADI.

**Mühürleme (koşumdan ÖNCE, ayrı commit `c081b19`):** referans = eşit-ağırlık US2
sepeti al-tut (maliyetsiz; SPY yalnız bilgi, SPY'a geçiş KALICI YASAK). Mühürlü 4
kriter: (1) Sharpe>sepet 0.8035; (2) CAGR>sepet 0.13836 (getiri-arayan VARLIK şartı,
D1/E4'te yoktu); (3a) OOS aylık-Sharpe>sepet 0.8310; (3b) tam-dönem |maxDD|≤sepet
45.54%. Kural: 1+2+3a+3b TAMAMI→aday; biri kalırsa red, dar-fark YOK.

**MEKANİK SONUÇ (referans=sepet):** D2-US ana: CAGR 10.87%, Sharpe 0.7254, maxDD
-32.61%, 246 rebalans; OOS aylık-Sharpe 0.7697, OOS maxDD -25.20% (39 pencere); MC
dd_p5 -36.1%. **MÜHÜRLÜ TABLO: (1) FAIL (0.725<0.804); (2) FAIL (10.87%<13.84%);
(3a) FAIL (0.770<0.831); (3b) PASS (32.6%≤45.5%) → 1/4.** → önceden mühürlenen
kurala göre **D2-US US-referansta kabul adayı DEĞİL** (HÜKÜM değil; karar kullanıcının).

**Zorunlu analizler:** (a) crash — 2009 rebound strat -0.8% vs sepet +51% (abs-kapı
~8.9/10 nakit); 2020 rebound strat +26.6% vs sepet +68.7% (vol maruziyet ~0.42) →
savunma katmanları toparlanmayı kaçırdı. (b) turnover ~588%/yıl ama maliyet sürüklemesi
yalnız ~33bps/yıl (zayıflık maliyet kaynaklı DEĞİL). (c) ablasyon (yalın 0.60→+FIP 0.74
→+kapı 0.76→+vol 0.73) BİLGİ-only — en iyi varyant (V2, 0.76) BİLE kriter 1'i geçmiyor
(karar tek katmana bağlı değil). (d) komşuluk uçurumsuz, mühürlü nokta zirve değil
(overfitting-karşıtı). Dürüst çekince: dar large-cap evreninde momentum edge'i zayıf +
survivorship (sepet gerçek-üstü) — sonuç bir ALT sınır.

**İzolasyon:** `mode: paper` + canlı bot modülleri + S1/S1b/E4 araçları
(backtest/regime_core*.py, tools/run_regime_core*.py, tools/e4_common.py,
config/regime_core*.yaml) DOKUNULMADI. Yeni BAĞIMSIZ: `backtest/xsec_momentum.py`,
`tools/{build_us2_snapshot,run_xsec_momentum_us2}.py`, `config/momentum_us2.yaml`,
`data/snapshots/us2/2026-07-08/`. v7.1-golden her commit 3/3; tam süit **530 passed**
(522+8). Faz 6/real/launchd/go_live'a adım YOK; iki durma noktası kullanıcıda.
**Kabul kararı kullanıcının/baş danışmanın; otomatik geçiş YOK.**

## KALICI KAYIT 19 — D2-US baş danışman kaydı: RED onaylandı, US2 tarihçesi KAPALI (2026-07-08)
Baş danışman kaydı (2026-07-08): D2-US (kesitsel momentum) US-referansta RED onaylandı
(D2US-S1 mühürlü tablo 1/4; D2US_CRITERIA.md §3/§5 kuralının uygulaması). Ölçüm tek
turda TAMDI (maliyet+nakit+OOS+MC+crash+turnover dahil) → E4b-tarzı ikinci ölçüm-bakışı
YOKTUR; bu tarihçede her yeniden-koşum tasarım değişikliği sayılır ve varyant-seçimi
yasağına girer. US2 tarihçesine bakış sayacı: 1 kullanıldı, D2 ailesi bu tarihçede
KAPALI. Ders-1 (metodoloji): target_vol'un sepet TAM-DÖNEM realize volünden türetilmesi
hafif look-ahead'dir (mühür-öncesi ve strateji-bağımsız olsa da); gelecek tasarımlarda
trailing/expanding vol veya ex-ante sabit kullanılacak — bu turun sonucunu DEĞİŞTİRMEZ
(en iyi ablasyon varyantı V2 bile kriter 1'i geçmiyor). Ders-2 (yapısal): V0 yalın 12-1
top-10 seçimi sepetin ALTINDA (CAGR 10.22%<13.84%, Sharpe 0.602<0.804) → dar 50'lik
mega-cap evrende kesitsel seçim alfası NEGATİF; zayıflık savunma katmanlarında değil
evren genişliğinde. Sıradaki adım: US3 point-in-time evren VERİ FİZİBİLİTESİ (strateji
tasarımı değil).

## K1.5 Mekanik Teyit — 1/2 (2026-07-08)
2026-07-08 akşam koşusu denetlendi (not: launchd servisleri bu makinede henüz kurulu
DEĞİL — `launchctl list` boş, `runtime/paper/logs/` yok; "akşam koşusu" = günün son
manuel `--refresh --cycle` çağrısı, `runtime/paper/decision_journal.jsonl` +
`heartbeat_status.json`'da 2026-07-08T17:05:41Z / 20:05 Istanbul damgalı). Dört kalem:
- **(a) DATA_DRIFT yok** — PASS. Günün TEK DATA_DRIFT alarmı 12:03 cycle'ındaydı (ASELS
  3-bar sapması); 12:56'da `--resync` ile giderildi (kompozit parite max_abs_diff≈5.4e-5);
  sonraki tüm cycle'larda (12:56, 13:11, 17:05) DATA_DRIFT YOK.
- **(b) provisional yok** — PASS. 17:05:41 cycle'ının `signal_eval` kaydı
  `"provisional": false` (as_of barı zaman-final + veri tam; önceki 3 cycle 12:03-13:11
  hâlâ oluşmakta olan bar yüzünden `provisional: true`'ydu — beklenen davranış).
- **(c) TELEGRAM: ACTIVE** — PASS. `heartbeat_status.json` (aynı ts):
  `telegram.state="ACTIVE"`, `reason="token+chat_id mevcut"`.
- **(d) EOD'de "Rejim"/"Pozisyon" AYRI satır + tutarlı** — PASS (kod-yolu doğrulamasıyla;
  ham EOD metni hiçbir yere journal'lanmıyor, yalnız stdout/Telegram'a gönderiliyor —
  bu yüzden literal string değil `main.py`/`notify/eod_summary.py` kod-yolu + bu
  cycle'ın girdileri izlendi). `main.py` observe dalı (satır ~354-366): `res.regime_on`
  DOĞRUDAN `evaluate_signal` çıktısından (composite/MA/band, bugünün gerçek rejim
  durumu) atanıyor — bu cycle için `True`. `build_eod_summary` çağrısında
  `in_position=bool(self.broker.quantities())`; observe modda hesap hiç başlatılmadığı
  için bu her zaman `False` → "Pozisyon: NAKİT (observe — hesap başlatılmadı)". İki alan
  BAĞIMSIZ kaynaklardan geliyor (F5-B2a.1 düzeltmesi, KALICI KAYIT 13) → "Rejim: ON" +
  "Pozisyon: NAKİT (observe...)" birlikte basılması ÇELİŞKİ değil, tasarım gereği
  (observe'da rejim ON iken pozisyon her zaman nakittir çünkü hesap yok).
**Dördü de sağlandı → K1.5 temiz koşu 1/2 (2026-07-08).** İkinci temiz koşu (2/2) için
farklı bir güne ait bağımsız bir gözlem gerekir; kod değişikliği YAPILMADI.

## Son tur (P1) — kısa özet
- Üretim modülü + family registry + sürücü + breaker + 14 test (kriter A/B/D +
  breaker kuru-test + tam-lot boyutlama + family registry), her commit golden-kanıtlı.
- Kapanış: BACKTEST_REVIEW_D1_PROD.md, STATUS güncelleme (KALICI KAYIT 8 + kuyruk
  eki), tam süit 378 passed, git push. Tag: `regime-core-d1-prod`.

## Sırada
**F5-B1 (gölge paper) KOD İŞİ TAMAMLANDI** — kullanıcı/baş danışman değerlendirmesi
bekliyor (`PHASE5B1_REVIEW.md`, KALICI KAYIT 10). Otomatik GEÇİŞ YOK. Sıradaki adımlar
kullanıcı kararına bağlı:
- **go_live kararı:** döngü birkaç gün stabil koştuktan sonra `config/regime_core.yaml`
  `paper.go_live_date` set edilir → active mod + Faz 6 resmi başlangıcı (AYRI karar).
- **F5-B2 (AlgoLab İPTAL, yeniden tanımlı):** `ManualExecutionAdapter` tasarımı (bot
  sinyali→Telegram→elle yürütme→onaylı fill kaydı; B2 mutabakatı) + gerçek Telegram HTTP/
  long-poll komut alıcısı. AlgoLab canlı akışı YAPILMAYACAK.
- **Real-öncesi kuyruk:** EVDS endpoint doğrulama (#18), gerçek nakit bacağı enstrümanı
  (#19), B1 kalanı (T+2/tick-lot/tedbir — manuel yürütmede kullanıcı gözetiminde).
- **Kuyruk (yeni):** BIST broker REST API pazarını periyodik izle — uygun API çıkarsa
  BrokerAdapter ile entegre edilebilir.

**Önceki tur (P1 D1 üretim portu) TAMAMLANDI** — `BACKTEST_REVIEW_D1_PROD.md`, KALICI
KAYIT 8. Üç paralel konu (referans):
(a) **BIST hattı**: D1 KABUL EDİLDİ (KAYIT 6) + ÜRETİM PORTU TAMAM (P1, KAYIT 8);
S1b'yle bit-bit özdeş, golden korundu. **Sıradaki iş kullanıcı onayına bağlı**:
canlı/paper emir katmanı Faz 5 (HARDENING B onayı) — PaperBroker/AlgoLab
regime_core ailesini de sürebilmeli. **[real-öncesi kuyruk, B1] Canlı takvim
gerçeği**: yarım-gün seanslar ve idari-izin köprü tatilleri için canlıda takvim
kütüphanesine (exchange_calendars) GÜVENİLMEZ — resmî kaynak (BIST/Borsa İstanbul
duyuruları) + veri-yok toleransı gerekir; canlı döngü bir günü yanlış "işlem günü"
sayarsa regime-core o gün hatalı sinyal/yürütme üretebilir.
(b) **EXPANSION.md**: E1 + E2 + **E4 + E4b (US ADİL TEST + nakit-tamamlama)
TAMAMLANDI** (KALICI KAYIT 15+16, `EXPANSION_E4.md` + `EXPANSION_E4B.md`). Mekanik
sonuç: D1-US mühürlü 4-kriterden **1/4** geçti (E4 %0 ve E4b faizli AYNI tablo) →
**SON-BAKIŞ KURALI gereği D1-US US-referansta KESİN RED, üçüncü bakış YOK** (karar
kullanıcının). **Kullanıcı sıralaması (KAYIT 14): E4 → geçerse US gölge paper →
geçerse E3.** E4/E4b "geçmediğinden" **US gölge paper hattı AÇILMADI**; D1-US için
dönüş yolu kapalı. Sıradaki E-fazı seçimi (E3 broker adapter mı, farklı çekirdek/
evren tasarımı mı) kullanıcı/baş danışman kararı — otomatik ilerleme YOK. E3'e
taşınan açık
maddeler (değişmedi): SEC/TAF+swap resmî doğrulama, US hesap tipi kararı, short
gate seti tasarımı (Bölüm 17 #10, FX aktivasyonu öncesi), US instruments[] config'e
girişi, econ/earnings gerçek parquet dosyaları. Ertelenenler (Faz 5 modülleri inşa
edilince): PaperBroker daily_carry, journal market/currency kolonları,
engine-seviyesi SHORT execution (short-gate sonrası).
(c) **Ablasyon + S1/S1b + P1**: TAMAMLANDI. Kalan işler (EVDS çapraz doğrulama,
üretim nakit bacağı enstrümanı) real-öncesi/üretim kuyruğunda (KAYIT 6 + aşağıda 18-19).

## Bilinen sorun/blok (aktif)
> Çözülmüş / üstü çizili maddeler (2, 3, 4, 8, 9, 10, 14, 16) **STATUS_ARCHIVE.md**'ye
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
11. **`oanda.py` hiçbir practice hesapla test edilmedi** (referans implementasyon)
    — E3'te doğrulanacak. E1'in FX snapshot'ı `yf_fx.py`'den üretildi.
12. **Ekonomik takvim vetosu (FX) backtest'te modellenemez** — tarihsel arşiv yok
    (Bölüm 10.4 fallback devrede; is_blackout altyapısı E2'de kuruldu, veri yoksa
    (False,"…") döner → backtest vetosuz).
13. US evreni survivorship yanlılığı taşıyor (bilinen, kabul edilen — DATA_AUDIT_US.md).
    **E4'te belirginleşti:** yanlılık, mühürlü referans olan eşit-ağırlık US sepetini
    gerçek-üstü yükseltiyor (CAGR %16.31, SPY %10.86'ya karşı) → D1-US kabul çıtası
    gerçekte-mümkün-olandan yüksek. Düzeltme (hayatta kalmayanları içeren evren) E4
    kapsamı dışı; yeniden-tasarım/US sleeve turunda ele alınır.
15. **Hiçbir 10-gate varyant USD-CAGR>0 başarı çıtasını geçmiyor** (KALICI KAYIT 1)
    — TRY'nin USD karşısındaki yapısal değer kaybı baskın. max DD/endeks-DD oranı İYİ.
17. Golden regresyon çapası `backtest-v7.1-golden` — `runtime/backtest_reports_v7_1/
    trades.csv` (commitli, `.gitignore` istisnası). E2+ her commit bayt-bayt kıyaslar.
18. **[real-öncesi kuyruk] EVDS↔TRY_ON_RATE çapraz doğrulama — DENENDİ, BLOCKED** (F5-B1,
    `EVDS_COMPARISON.md`): EVDS_API_KEY VAR ama REST endpoint evds2→evds3 geçişiyle SPA
    döndürüyor (JSON yok). **F5-B1.1 K8: `tools/evds_compare.py --csv` elle-export modu
    eklendi** → endpoint düzelmeden kullanıcı EVDS CSV export'uyla kapatabilir (kolon eşleme +
    çoklu tarih formatı). Snapshot DEĞİŞMEZ; hâlâ FRED/OECD (KAYIT 6). Ayrıca F5-B1.1 K1:
    canlı faiz FRED'den beslenir ama FRED de ~4 ay gecikmeli → faiz kronik bayat.
    2023 boşluğu ff → cash-yield MUHAFAZAKÂR sapma. **F5-B2a m4 düzeltmesi:** "bayat =
    muhafazakâr" GENELLEME DEĞİL — yön faiz patikasına bağlı; yükseliş döngüsünde muhafazakâr
    (eksik tahakkuk), DÜŞÜŞ döngüsünde nakit getirisini ABARTIR (agresif). **F5-B2a m5:** GERÇEK
    EVDS CSV (TLREF) kıyası koşuldu (EVDS_COMPARISON.md) — EVDS sistematik ~2-6p YÜKSEK (seri-tanım
    farkı), 2023 boşluğu EVDS'de 12/12 DOLU, 2022-10 %9.0 baseline artefaktı teyit. Snapshot
    DEĞİŞMEDİ. Bu madde artık "veri yok" DEĞİL, "tanım-uyumlu seri + S1b yeniden ölçüm turu"
    bekliyor. Real öncesi tamamlanmalı.
19. **[üretim-turu kuyruğu] D1 nakit bacağının GERÇEK enstrümanı** netleştirilecek
    (AlgoLab para piyasası fonu/repo süpürme; oran/likidite/vade). Şu anki
    %0/faizli model yalnızca bir yaklaşıklık.
20. **[KAPANDI — E4b] US nakit bacağı ölçüldü.** E4'teki %0 boşluğu E4b'de gerçek
    US kısa faiziyle (FRED DGS3MO 3-aylık T-bill, dondurulmuş aux_us snapshot, 50bp
    haircut) S1b formülüyle tamamlandı (bkz. KAYIT 16, `EXPANSION_E4B.md`). Sonuç:
    faiz Sharpe'ı 0.726→0.758, CAGR +0.41pp itti ama mühürlü tablo 1/4'te kaldı →
    D1-US KESİN RED. **%0 kararı doğrulandı: US faizi küçük (nakit-only CAGR ~%1.51),
    sonucu iyimser saptırmamıştı.** SPY-vs-sepet referans sorusu SON-BAKIŞ KURALIYLA
    kapatıldı (D1-US için SPY'a geçiş YASAK; sepet kalıcı referans).

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
exchange_calendars); P1 (strategy/regime_core.py + family_registry, D1 üretim portu);
F5-B1 (data/live_feed.py yfinance EOD + main.py PaperScheduler observe/active +
INITIAL_ENTER + oluşmakta-olan-bar koruması; AlgoLab İPTAL, F5-B2=ManualExecutionAdapter).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

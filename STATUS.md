# Proje Durumu
Son güncelleme: 2026-07-06T23:55:00+03:00 (Europe/Istanbul)
Şu an: **S1 — Rejim-Filtreli Çekirdek spike backtest'i (REGIME_CORE_S1.md,
D1 tasarımının tek-tur değerlendirmesi) tamamlandı — Durma Noktası 1'de
duruluyor. Hiçbir eşik/gate/parametre değiştirilmedi, `backtest/engine.py`/
`strategy/`/`risk/`/`config/config.yaml` DOKUNULMADI (git diff boş —
v7.1-golden çapası otomatik korunuyor). Faz 5'e/E2'ye geçilmedi. Mühürlü
kabul tablosunda 4 kriterden 2'si GEÇTİ, 2'si dar farkla GEÇMEDİ — karar
kullanıcının/baş danışmanın.**
Tamamlanan fazlar: Faz 1-3, Faz 4 (Backtest Harness — v1→v7, v7.1-golden) +
HARDENING.md Bölüm A (kalite/güvenilirlik sertleştirme, CLAUDE.md'ye ek) +
Teşhis turu v6 + Motor+veri düzeltme turu v7 + EXPANSION.md E1 (Veri Temeli)
+ Portföy ablasyon turu (+ kapanış R1) + S1 rejim-filtreli çekirdek spike'ı.

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

Bu oturumda yapılan (onaylı S1 spike backtest'i — D1 tasarımının tek-tur testi):
- **Madde 1 — `backtest/regime_core.py`** (YENİ, tamamen bağımsız
  simülatör — `backtest/engine.py`/`strategy/`/`risk/`/`config/config.yaml`'a
  dokunmuyor/bağımlı değil): 12 sembol eşit ağırlık kompozit (t0=2005-01-03,
  0 forward-fill olayı), asimetrik histerezis rejim sinyali (giriş MA(200)×
  1.01 üstünde 3 gün teyitli, çıkış MA(200)×0.99 altında tek gün), t+1
  KAPANIŞ yürütme (ana motorun t+1 AÇILIŞ kuralından kasıtlı farklı — bu
  spike'ın kendi kuralı), breaker yok (bilinçli). `config/regime_core.yaml`
  (YENİ) + `tools/run_regime_core.py` (YENİ CLI). 23 yeni birim testi
  (kompozit, histerezis, t+1 yürütme, komisyon, negatif-cash yokluğu,
  determinizm — hepsi yeşil).
- **Madde 2 — 4 koşum + 3 benchmark**: Ana koşum (N=200/b=%1/M=3, tam
  dönem): CAGR %23.94, Sharpe 1.064, max DD -%33.50, time-in-market %72.4,
  67 anahtarlama. Benchmark'lar: XU100 al-tut (Sharpe 0.851, maxDD -%63.43),
  12-sembol sepeti al-tut/filtresiz (Sharpe 1.184, maxDD -%64.22 — filtrenin
  katma değerinin asıl ölçüsü). Walk-forward: 39 pencere (config'teki AYNI
  24ay/6ay/6ay takvimi, parametre optimizasyonu YOK), OOS aylık-Sharpe
  0.9505 (sepete karşı 0.9723), OOS max DD -%30.30 (sepete karşı -%56.23).
  Monte Carlo (aylık getiri permütasyonu): dd_p5 -%48.57. Uçurum kontrolü
  grid'i (36 kombinasyon, seçim için değil): komşuluk sürekli, uçurum yok.
- **Madde 3 — En kötü 5 DD epizodu, 6 bilinen kriz yılının (2008, 2011,
  2013, 2018, 2020, 2021) TAMAMIYLA örtüştüğü doğrulandı** (2008 ve 2020,
  daha büyük epizotların İÇİNDE 2006-2009 ve 2018-2020 olarak birleşik
  görünüyor). En kötü epizot (2024-2025, -%26.90) bilinen kriz takviminde
  YOK — yeni/güncel, ayrıca not edildi.
- `REGIME_CORE_S1.md` yazıldı (a-g bölümleri + mühürlü kabul tablosu).
- 299 test yeşil (23 yeni regime_core/run_regime_core testi dahil,
  regresyon yok). `git diff backtest/engine.py strategy/ risk/
  config/config.yaml` BOŞ — bağımsızlık kanıtlandı.

Önceki oturumda yapılan (onaylı ablasyon kapanış turu — R1: breaker adli
incelemesi + golden yeniden mühürleme, hâlâ geçerli):
- **Madde 1 — Breaker adli incelemesi (read-only, `trace=` ile 4 varyantın
  ana koşumu yeniden çalıştırıldı — walk-forward/MC/sweep DEĞİL):** 4/4
  tetiklenme **"GERÇEK DRAWDOWN"** olarak sınıflandırıldı — hiçbiri v7'nin
  EREGL hayalet-bar deseniyle (tek gün/tek sembol/volume=0/ani sıçrama)
  eşleşmiyor. no_regime (2018-10-18) ve no_trend_regime_rsi (2008-09-17,
  Lehman Brothers iflasından 2 gün sonra) bilinen makro-stres dönemleriyle
  doğrudan örtüşüyor — breaker'ın tasarlandığı gibi çalıştığının kanıtı.
  no_trend (2020-08-18) ve no_rsi (2015-11-10) kademeli çok-günlü aşınmanın
  son halkası. Detay + çekinceler: `ABLATION_PORTFOLIO.md`'nin "Breaker Adli
  İnceleme (R1 eki)" bölümü (mevcut içeriğe dokunulmadı, yalnızca eklendi).
- **Madde 2 — Golden yeniden mühürleme**: ablasyon baseline'ın kanonik
  (sıra-deterministik) `trades.csv`'si `runtime/backtest_reports_v7_1/`e
  kopyalandı (SHA256: `08fa8ea8...` — tam hash `runtime/backtest_reports_v7_1/MANIFEST.json`'da),
  `.gitignore`'a hedefli istisna eklendi (bu dosya artık commitli — diğer
  `backtest_reports_v*` dizinleri ephemeral kalmaya devam ediyor), git tag
  `backtest-v7.1-golden` atıldı. `EXPANSION.md` Bölüm 0.2 güncellendi: E2+
  regresyon çapası artık v7 değil **v7.1-golden**'a bayt-bayt kıyaslanacak
  (v7 tarihsel kayıt olarak kalıyor, 2 satırlık sıra farkının nedeni
  ABLATION_PORTFOLIO.md'de belgeli). `CLAUDE.md` Bölüm 12.8'e tek satır
  eklendi: "Aynı-gün çoklu giriş VE çıkış sırası alfabetik-deterministiktir."
  Başka hiçbir yer değiştirilmedi.
- 276 test yeşil (regresyon yok — bu turda motor koduna dokunulmadı, yalnızca
  belgeler + golden dosya kopyalandı).

Önceki oturumda yapılan (onaylı portföy-seviyesi gate ablasyon turu, hâlâ geçerli):
- **Madde 1 — `run_backtest`'e `disabled_gates: Optional[list[str]] = None`
  parametresi eklendi** (geç bağlama — None-varsayılan, call-time'da
  `set()`'e çevriliyor). Verilmediğinde davranış BİREBİR aynı — kanıt: kısa
  3-sembollü koşuda trades.csv bayt-bayt aynı (hem sentetik testte hem gerçek
  A1 snapshot verisiyle doğrulandı). `strategy/signal_engine.py::evaluate_entry`
  ve `backtest/walkforward.py::run_walk_forward` ile `backtest/cli.py::generate_report`
  fonksiyonlarına da aynı ilkeyle (None-varsayılan, geriye dönük uyumlu)
  iletildi.
- **ÖNEMLİ YAN BULGU — yeni bir determinizm bug'ı bulundu ve düzeltildi:**
  baseline'ın v7 ile "bayt-bayt aynı" olması doğrulanırken, `backtest/engine.py`'de
  `pending_exits`'in bir `set[str]` olması nedeniyle, Python'ın string
  hash'lerinin `PYTHONHASHSEED`'e göre SÜREÇ BAŞINA rastgeleleştiği fark
  edildi — aynı veriyle çalıştırılan İKİ AYRI SÜREÇ, aynı güne denk gelen
  birden fazla sembol çıkışını FARKLI SIRADA üretebiliyordu (finansal sonuç
  aynı, yalnızca trades.csv satır SIRASI değişiyordu). **Düzeltme**:
  `for symbol in sorted(pending_exits):` — giriş huninin v7'deki alfabetik
  sıra ilkesiyle tutarlı. Kanıt: yeni regresyon testi + 4 farklı
  `PYTHONHASHSEED` değeriyle manuel doğrulama (hepsi aynı, alfabetik sırayı
  üretti). Bu düzeltme SONRASI baseline, v7 ile İÇERİK olarak (sort sonrası)
  TAM AYNI — yalnızca tüm tarihçedeki 2 "aynı-gün-çoklu-çıkış" çakışmasının
  (ARCLK/TOASO 2010-12-10, ASELS/TCELL 2026-06-04) SIRASI, v7'nin dondurulmuş
  (rastgele hash tohumlu) dosyasından farklı — bu beklenen ve dokümante
  edilmiş bir fark, v7 DEĞİŞTİRİLMEDİ.
- **Madde 2 — USDTRY bilgilendirici snapshot**: `data/snapshots/aux/2026-07-06/USDTRY.parquet`
  (manifest hash'li). Yalnızca raporlama, hiçbir sinyal/risk hesabına girmiyor.
- **Madde 3 — `tools/portfolio_ablation.py`** (YENİ, read-only): A1
  snapshot'ından, 12 sembol, 2005+, `data/cleaning.py` açık, 5 varyant
  (`baseline`, `no_trend`, `no_regime`, `no_rsi`, `no_trend_regime_rsi`) —
  her biri tam süit + walk-forward + MC + XU100 benchmark (sweep yok).
  ~6 saat sürdü (5 × ~70dk).
- **Madde 4/5 — Ek metrikler + gap-proximity**: time-in-market, ortalama
  sermaye kullanımı, USD çevrimi (CAGR/toplam getiri), DD/endeks-DD oranı,
  Sharpe-vs-endeks, gap-proximity (DATA_AUDIT_v2.md'nin 79 "açıklanamayan
  gap" gününe ±5 bar) — hepsi `ABLATION_PORTFOLIO.md`'de.
- **Madde 6 — Ana bulgu: izole (DIAGNOSTICS_v6.md Paket 3) ile portföy
  sonuçları ÇELİŞİYOR.** no_trend ve no_rsi portföy düzeyinde BELİRGİN DAHA
  KÖTÜ (no_rsi: TRY getirisi negatife dönüyor, PF<1, OOS max DD -31%'e
  fırlıyor — baseline'ın 2 katı; no_trend: max DD -10.04%, breaker
  tetikleniyor). no_regime karma (getiri/Sharpe/OOS-PF iyileşiyor ama DD
  kötüleşiyor, breaker tetikleniyor). Üçü birden kaldırılınca (no_trend_regime_rsi)
  TÜM metriklerde EN KÖTÜ sonuç (Sharpe negatif, OOS max DD -32.87%) — gate'lerin
  portföy düzeyinde birbirini TAMAMLAYAN bir risk-azaltma işlevi gördüğünü
  düşündürüyor, izole ölçümün yakalayamadığı bir etkileşim.
- 276 test yeşil (yeni disabled_gates + determinizm testleri dahil,
  regresyon yok).

Önceki oturumda yapılan (onaylı EXPANSION.md E1 — "E1 onaylandı, başlat" talimatı, hâlâ geçerli):
- **US evren önerisi**: 20 sembol, 8 sektör (Teknoloji, Sağlık, Finans,
  Enerji, Temel Tüketim, Tüketici Takdiri, İletişim, Sanayi), 2005-01-03'ten
  itibaren tam tarihçe doğrulandı. Getiriye göre seçim YAPILMADI. Survivorship
  yanlılığı notu düşüldü (2005'ten bu yana küçülen/iflas eden şirketler
  evrende YOK — bilinen, kabul edilen sınırlama, gelecekteki backtest
  sonuçları bunu hesaba katarak yorumlanmalı).
- **FX seti**: EUR_USD, GBP_USD, USD_JPY (EXPANSION.md Bölüm 1/11.3'ten,
  spec'in kendi kararı — altın Bölüm 17 #8'e tabi, dahil edilmedi).
- **`data/adapters/` iskeleti** (YENİ, BIST'e dokunmadan): `base.py`
  (DataAdapter ABC + AdapterMeta + `relabel_to_local_calendar_day` — v7'nin
  Istanbul tarih-kayması düzeltmesinin genelleştirilmiş, BAĞIMSIZ hali: NYSE
  UTC-negatif olduğundan kaymıyor, Londra/FX DST'ye göre bazen kayıyor,
  fonksiyon her iki rejimi de doğru işliyor); `yf_us.py` (çalışan, testli);
  `yf_fx.py` (çalışan, testli — **belgelenmiş kaynak sapması**, bkz. aşağı);
  `oanda.py` (REFERANS implementasyon, CLAUDE.md'nin AlgoLab auth.py
  emsaliyle tutarlı — practice hesap YOK, canlı test edilmedi, yalnızca
  fixture'lı JSON-ayrıştırma testi var).
- **Kaynak kararı (belgelenmiş sapma, Bölüm 17 protokolü)**: OANDA practice
  hesabı yok, Dukascopy'nin tick endpoint'i bu ortamdan erişilemedi (bağlantı
  kurulamadı), histdata.com etkileşimli/otomatikleştirilemez. **E1'in FX
  snapshot'ı `yf_fx.py` (yfinance) ile üretildi** — teknik, konservatif bir
  karar, dur/sor değil, dokümante edilip ilerlendi (DATA_AUDIT_FX.md'de tam
  gerekçe).
- **Snapshot'lar donduruldu**: `data/snapshots/us/2026-07-06/` (20 sembol,
  5408 satır/sembol) ve `data/snapshots/fx/2026-07-06/` (3 sembol) —
  `tools/build_snapshot.py` (YENİ, piyasa-parametrik, HARDENING A1'in
  genelleştirilmiş hali) ile, manifest + sha256 hash'li.
- **A2 denetimleri**: `tools/data_audit.py` DEĞİŞTİRİLMEDEN (zaten
  piyasa-parametrik) yeniden kullanıldı. **US: 20/20 PASS/WARN, hiç FAIL yok**
  — WARN'ların tamamı (BAC 2008-09 kriz dönemi, INTC 2024-08 post-kazanç
  çöküşü, JPM 2009-01 banka rallisi) gerçek, açıklanabilir piyasa olayları;
  BIST'teki "bedelli" kör noktasının ABD karşılığı yok (yapısal olarak
  mevcut değil). **FX: EUR_USD ve GBP_USD FAIL** — İKİSİ DE aynı tarihte
  (2010-07-01) OHLC iç tutarlılık ihlali (close>high), USD_JPY etkilenmedi.
  Tesadüf değil, yfinance'in FX veri hattına özgü bir kaynak kusuru — OANDA'nın
  neden tercih edildiğinin somut kanıtı. DÜZELTİLMEDİ (E1 kapsamı dışı, E2'ye
  not düşüldü: bu iki sembol backtest'e girmeden önce ele alınmalı).
- **`data/events.py`** (YENİ, iskelet + örnek çekim): US earnings için
  `yfinance.get_earnings_dates` test edildi (4 sembol) — **2001-2002'ye kadar
  tarihçe var, "sığdır" endişesi bu örneklemde DOĞRULANMADI** (Bölüm 17 #4
  çözüldü). Ekonomik takvim için ForexFactory'nin ücretsiz widget feed'i
  çalışıyor ama **yalnızca içinde bulunulan hafta, tarihsel arşiv YOK**
  (Bölüm 17 #5 çözüldü — Bölüm 10.4 fallback protokolü FX ekonomik vetosu
  için devrede: backtest'te modellenemez, yalnızca canlı/paper'da).
- **BIST hattında sıfır değişiklik**: `git status`/`git diff` doğrulandı —
  `data/historical.py`, `data/cleaning.py`, `data/quality.py`, `backtest/`,
  `strategy/`, `risk/`, `config/config.yaml`, mevcut BIST snapshot'ı ve
  `requirements.txt`/`.lock` HİÇBİRİ değişmedi (yalnızca yeni dosyalar
  eklendi). `tools/data_audit.py` da değiştirilmeden yeniden kullanıldı.
- DATA_AUDIT_US.md + DATA_AUDIT_FX.md yazıldı (evren tablosu, denetim
  sonuçları, kaynak kararı gerekçesi, events.py bulguları dahil).
- 256 test yeşil (12 yeni adapter/snapshot/events testi dahil, regresyon yok).

Önceki oturumda yapılan (onaylı motor+veri düzeltme turu — v7, DIAGNOSTICS_v6.md'nin
Paket 1 bulgularının düzeltmesi, hâlâ geçerli):
- **Madde 1 — Equity forward-fill** (`backtest/engine.py`): açık pozisyonun o
  gün fiyatı yoksa artık son bilinen kapanışla taşınıyor, 0 sayılmıyor. Test:
  sentetik eksik-gün senaryosunda equity sabit kalıyor.
- **Madde 2 — Aynı-gün-çoklu-onay düzeltmesi**: gün içi onaylar artık pseudo-
  Position olarak `positions_snapshot`'a HEMEN eklenip kalan slotu düşürüyor;
  aday sırası deterministik (alfabetik — Faz 5 canlı döngüsü aynı sırayı
  kullanmalı, koda not düşüldü). Test: aynı gün 3 aday + limit 2 → yalnızca
  ilk 2 (alfabetik) onaylanıyor.
- **Madde 3 — Veri temizleme katmanı** (`data/cleaning.py`, YENİ): (a)
  hayalet-bar filtresi (tarih yalnızca 1 sembolde + volume=0 + OHLC≈önceki
  kapanış → elenir, loglanır), (b) UTC→Istanbul tarih normalizasyonu
  (yfinance'in Istanbul yerel gece yarısını UTC'ye çevirirken tarih etiketini
  bir gün geriye kaydırdığı bug düzeltildi). Snapshot parquet dosyalarına
  DOKUNULMADI — yalnızca `backtest/cli.py`'nin YÜKLEME anında bellek-içi
  düzeltmesi (`--no-clean` ile atlanabilir, varsayılan: temizlenir).
- **Madde 4 — `DATA_AUDIT_v2.md`** (`tools/data_audit_v2.py`, YENİ, read-only):
  sıçrama eşiği %25→%10, 12 sembolün tamamı tarandı, ham Dividends/Stock
  Splits ile çapraz kontrol: 179 gün (%10+), 97 hacim destekli gerçek hareket,
  79 açıklanamayan gap (muhtemel bedelli), 3 kayıtlı kurumsal işlem. **Ek
  bulgu**: 2023-02-15 (deprem sonrası piyasa-çapında yeniden açılış) 12
  sembolün TAMAMINDA görünüyor — sınıflandırıcının yakalayamadığı,
  piyasa-çapında/açıklanabilir bir olay; "açıklanamayan gap" sayısının üst
  sınır olduğunu gösteriyor.
- **Madde 5 — Veri kaynağı keşfi** (read-only, `DATA_AUDIT_v2.md`'ye eklendi):
  AlgoLab (`execution/algolab/` henüz boş) yalnızca ~300 barlık canlı pencere
  için tasarlanmış, çok yıllı backtest verisi sağlamıyor — yfinance'in kör
  noktaları AlgoLab'a geçilerek çözülmez.
- **Madde 6 — Performans**: breaker artık CLI çağrısı başına TEK paylaşılan
  geçici dizin kullanıyor (`run_backtest`/`run_walk_forward`/`_write_sweep_csv`
  artık opsiyonel `breaker_file`/`breaker_dir` parametresi kabul ediyor; breaker
  durumu çağrılar arasında yine tam izole). Kanıt: kısa 3-sembollü koşuda
  `trades.csv` bayt-bayt aynı (eski per-call-tempdir davranışına karşı).
- **Madde 7 — v7 tam süit**: A1 snapshot'ından, 12 sembol, 2005+,
  `runtime/backtest_reports_v7/`. **~1 saat 49 dakika sürdü** (v6'nın ~6.5
  saatine göre ~3.6× hızlanma — madde 6 performans düzeltmesi).
  - **Trade 119→121.** **Maks. drawdown -%20.74 → -%6.71 — DRAMATİK
    İYİLEŞME.** Bu, DIAGNOSTICS_v6.md Paket 1'in "eski -%20.74 rakamı gerçek
    değil, veri+engine artefaktı" öngörüsünü DOĞRULUYOR.
  - **Breaker artık HİÇ tetiklenmiyor** (`breaker_trips=[]`) — v6'daki tek
    tetiklenme (eski "2024-04-08", normalize edilince gerçek gün
    **2024-04-09**) tamamen o artefaktın sonucuymuş.
  - **max_open_positions ihlali sıfırlandı**: tüm tarihçe boyunca gözlenen
    maks. eşzamanlı pozisyon artık 2 (limit=2), 0 ihlal günü (önceden en az
    3 bağımsız ihlal dönemi vardı).
  - Hayalet bar filtresi tam olarak beklenen tek barı eledi: EREGL,
    2024-04-09.
  - **Walk-forward kabul kriteri hâlâ GEÇMEDİ, MC kırmızı bayrağı hâlâ
    tetikleniyor** (dd_p5=-%10.29, v6'nın -%12.08'inden iyileşti ama sınırda) —
    bunlar motor/veri bug'ı DEĞİL, stratejinin kendi (parametre/gate) zayıflığı
    olarak duruyor, ayrı bir konu.
  - Sweep: 27 kombinasyonun TAMAMINDA max DD artık tek-haneli/düşük-çift-haneli
    (v5/v6'daki bazı kombinasyonların -%25'e varan drawdown'ları kayboldu —
    veri artefaktı sweep'in TAMAMINI aynı şekilde etkiliyordu).
  - `BACKTEST_REVIEW_v7.md` yazıldı: v6 yan yana karşılaştırma, kök-neden
    doğrulaması, iki bug'ın düzeltildiğinin kanıtı, walk-forward/MC'nin hâlâ
    kırmızı bayrak olmasının ayrı bir bulgu olduğu açıklaması.
  - **Not**: v1-v6 raporları artık yalnızca tarihsel kayıt — v7 tek geçerli
    taban çizgisi, v1-v4 yeniden koşulmadı/koşulmayacak.
- 223 test yeşil (tüm yeni testler dahil, regresyon yok).

Önceki oturumda yapılan (onaylı read-only teşhis turu — DIAGNOSTICS_v6.md, hâlâ geçerli):
- **Paket 1 (EN ÖNEMLİ) — iki motor bug'ı bulundu, DÜZELTİLMEDİ (raporlandı):**
  1. **Equity hesaplama bug'ı:** `backtest/engine.py`'nin equity formülü, o gün
     fiyat verisi eksik olan açık pozisyonları toplamdan TAMAMEN dışlıyor
     (0 sayıyor), son bilinen fiyatla taşımıyor. 2024-04-08'de EREGL'de
     piyasa tatildeyken tek bir "hayalet bar" (sentetik, volume=0) olması,
     `all_dates` birleşiminin bu günü geçerli işlem günü sanmasına yol açtı;
     o gün SAHOL'un fiyatı yoktu, formül SAHOL'u sıfırladı, equity 97,631'den
     84,290'a "düştü" (aslında düşmedi). **v5 VE v6'nın raporladığı -%20.74
     max drawdown büyük olasılıkla gerçek değil, bir veri+bug artefaktı.**
     Gerçek max DD muhtemelen ~%8-9 mertebesinde.
  2. **Aynı-gün-çoklu-onay bug'ı:** risk motoru günlük TEK bir `acct`
     snapshot'ı üzerinden aday sembolleri sırayla değerlendiriyor; aynı gün
     2 sembol de gate'leri geçerse `max_open_positions=2` iken ikisi de
     onaylanabiliyor (gözlenen maks. eşzamanlı pozisyon: 3). En az 3 örnek
     bulundu: 2006-03-30, 2010-12-02→08, 2013-06-30.
  - Nakit/notional disiplini sağlam: negatif cash yok, toplam notional hiç
    equity'yi aşmamış (maks %49.6), tek pozisyon tavanı yalnızca giriş-sonrası
    fiyat artışıyla marjinal aşılmış (%26.0, beklenen davranış).
  - Yeni `run_backtest(..., trace=...)` parametresi eklendi (salt-okunur
    gözlem kancası — sonucu değiştirmez, testle kanıtlandı).
- **Paket 2 — WARN günleri adli inceleme:** ham (auto_adjust=False) veri ayrı
  klasöre indirildi. UTC/Istanbul tarih kayması netleştirildi (gerçek tarihler
  KCHOL 2007-06-08, TCELL 2005-05-17). KCHOL: ham veride de aynı ~-26.8%
  sıçrama var → adjustment artefaktı değil, gerçek hareket ya da kaynak hatası
  (belirsiz, dış doğrulama gerekiyor). TCELL: ham veride Dividends+Stock
  Splits kaydı var → doğrulanmış kurumsal aksiyon, ama yfinance ayarlaması
  eksik (snapshot hâlâ +%25.96 gösteriyor). v6'nın 119 trade'i bu tarihlerden
  337-442 gün uzakta → etki sınırlı.
- **Paket 3 — Gate ablasyon (counterfactual, izole sinyal-kalite ölçümü):**
  yeni `tools/gate_ablation.py` (+ testleri). Aktif 6 gate için "yalnızca bu
  gate'ten elenen" adaylar izole modda (portföy/nakit/breaker YOK, sabit 1R)
  simüle edildi, gerçek 119 trade aynı yöntemle yeniden ölçüldü (baseline
  n=117, win rate 43.6%, PF 1.11). Bulgu: **trend/regime/rsi**'nin elediği
  adaylar baseline'dan DAHA İYİ (örn. trend PF 1.54) — izole ölçümde değer
  katmıyor gibi görünüyorlar. **macd/volume/trigger_4h**'nin elediği adaylar
  baseline'dan DAHA KÖTÜ (örn. volume PF 0.86, n=944) — değer katıyorlar.
  Önemli çekince: bu ölçüm portföy-seviyesi etkileri (rejim filtresinin
  dolaylı risk yönetimi işlevi gibi) yok sayıyor — tek başına eşik
  değiştirmeye yeterli kanıt değil.
- **Paket 4:** dört paketin bulguları `DIAGNOSTICS_v6.md`'de "yeniden tasarım
  konuşması için girdiler" başlığı altında sentezlendi.
- Yardımcı CSV'ler: `runtime/diagnostics_v6/` (gitignored, ephemeral).
- Tam test süiti: 199 passed (yeni trace + gate_ablation testleri dahil,
  regresyon yok).

Önceki oturumda yapılan (onaylı harness düzeltme turu, hâlâ geçerli):
- **Madde 1 — Breaker entegrasyonu:** `risk_engine.check_and_trip_breaker()`
  artık `backtest/engine.py`'nin event loop'una bağlı — her gün equity/peak
  hesaplandıktan hemen sonra, giriş değerlendirmesinden ÖNCE çağrılıyor
  (paper/real modun yapacağının BİREBİR aynısı, aynı fonksiyon çağrısıyla).
  Her `run_backtest` çağrısı kendi izole geçici breaker dosyasını kullanıyor
  (`tempfile.TemporaryDirectory`) — paper/real'in paylaştığı gerçek
  `runtime/BREAKER_TRIPPED`'e dokunmuyor. `risk_engine.py`'de `breaker_file`
  parametresi None-varsayılanlı (geç bağlama) eklendi — early-binding
  bug'ına düşülmedi (fark edildi, düzeltildi). Kanıt testi: sentetik seride
  breaker doğru barda tetikleniyor VE sonrasında hiçbir yeni pozisyon
  açılmıyor. Yan bulgu: `runtime/BREAKER_TRIPPED` altında Faz 3'ten kalma
  bir test artığı bulundu ve temizlendi (gitignored, hiç commit edilmemişti).
- **Madde 2 — MC kırmızı bayrağı:** kontrol `dd_p95`'ten `dd_p5`'e (en kötü
  %5 senaryo / worst-5%) çevrildi. Rapor satırları netleştirildi. CLAUDE.md
  Bölüm 12.6'daki tek ilgili satır (yorum kuralı) düzeltildi, başka hiçbir
  yere dokunulmadı.
- **Madde 3 — Tam süit (v6):** A1 snapshot'ından (`--snapshot`, ağdan indirme
  yok), 12 sembol, 2005+, `runtime/backtest_reports_v6/`. **~6.5 saat sürdü**
  (v5'in ~2.3 saatine göre belirgin yavaşlama — breaker'ın her `run_backtest`
  çağrısında geçici dizin oluşturup silmesinin yükü; düzeltilmedi, kapsam
  dışı, gelecekte performans turu için not edildi).
  - Trade 125→119 (breaker 6 trade'i engelledi). **Max DD DEĞİŞMEDİ (-%20.74)**
    — breaker yalnızca YENİ girişleri durduruyor, zaten açık pozisyonun
    mark-to-market kaybını önlemiyor (HARDENING.md B3'ün FREEZE/FLATTEN
    ayrımıyla tutarlı). Breaker **1 kez, 2024-04-08'de** tetiklendi (o gün
    equity zaten %20.74 drawdown'daydı — hasar tetiklenmeden önce olmuştu).
  - **Sweep verisi çok farklı bir hikaye anlatıyor:** gevşek parametrelerle
    (adx_min=15, çok daha sık trade) breaker drawdown'u DRAMATİK azaltıyor
    (bazı kombinasyonlarda -25.86%→-10.07%) — çünkü sık trading, breaker'ın
    erken tetiklenip sonraki kötü girişleri önleme şansını artırıyor. Mevcut
    sıkı varsayılan (adx_min=25, az trade) için bu etki yok.
  - **MC kırmızı bayrağı artık doğru tetikleniyor:** dd_p5=-%12.08, breaker
    eşiğinin (%10) üzerinde.
- **Madde 5/EK — Gate Katkı Analizi:** `tools/gate_analysis.py` (read-only)
  + `GATE_ANALYSIS.md`. 63.013 aday-günden yalnızca 147'si (%0.23) 10 gate'i
  geçiyor. `atr_anomaly`/`structure_rr`/`bb_overextension`/`mtf` neredeyse
  hiç eleme yapmıyor (yapısal nedenlerle). **Yeni bulgu:** `rsi` (%76.6 eleme)
  ve `regime`/ADX (%54.6 eleme) aktif eleme yapıyor ama geçirdikleri
  adaylarda kazanan/kaybeden ayrımı göstermiyor (küçük örneklem, ön-bulgu).
- `BACKTEST_REVIEW_v6.md` ve `GATE_ANALYSIS.md` yazıldı.

**Sırada:** D1 tasarımının S1 spike'ı sonuçlandı (KALICI KAYIT 4) — 2/4
mühürlü kriter geçti, 2/4 dar farkla geçmedi. **Bu, D1'i otomatik olarak
kabul VEYA red ETMİYOR** — sonuç kullanıcının/baş danışmanın değerlendirmesini
bekliyor: (i) mevcut parametrelerle kabul (dar farkla kaçırılan kriterler
göz ardı edilebilir mi?), (ii) D2 iterasyonu (farklı bir tasarım denemesi —
bu turun uçurum-kontrolü grid'i SEÇİM için kullanılamaz, yeni bir D-tasarımı
gerekir), (iii) üretim implementasyonuna geçiş (kabul edilirse, ayrı onaylı
turda "backtest=canlı" ilkesiyle). Hiçbiri OTOMATİK değil. Üç paralel konu:
(a) **BIST hattı**: D1'in S1 spike'ı bitti, sonucu değerlendirme bekliyor.
Kabul edilirse bile üretim implementasyonu (main.py/PaperBroker entegrasyonu)
ayrı bir onaylı tur.
(b) **EXPANSION.md**: E1 tamamlandı. E2 ön şartı (v7 + BIST karar) sağlandı,
ama "E2 onaylandı" talimatı hâlâ ayrı gerekiyor. E1'in açık maddeleri: FX
OHLC-ihlali düzeltmesi (2010-07-01, EUR_USD/GBP_USD), lxml kararı.
(c) **Ablasyon turu (R1 dahil) + S1 spike**: TAMAMLANDI. Açık madde yok.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1, BIST)** — kasıtlı, aşılamaz kapı.
2. ~~v5/v6'nın -%20.74 max drawdown rakamı güvenilir değildi~~ **DÜZELTİLDİ
   (v7): equity forward-fill + hayalet-bar filtresi sonrası gerçek max DD
   -%6.71.** Breaker artık hiç tetiklenmiyor.
3. ~~max_open_positions limiti aşılabiliyordu~~ **DÜZELTİLDİ (v7): tüm
   tarihçe boyunca 0 ihlal günü, doğrulandı.**
4. ~~Breaker entegrasyonu backtest'i ~3× yavaşlatıyordu~~ **DÜZELTİLDİ (v7):
   CLI çağrısı başına tek paylaşılan geçici dizin, v7 koşumu v6'ya göre
   ~3.6× hızlandı (~1sa49dk vs ~6.5sa).**
5. Breaker, mevcut sıkı parametrelerle gerçekleşmiş max drawdown'u
   SINIRLAMIYOR (yalnızca sonraki girişleri engelliyor) — bu tasarım gereği
   (FREEZE≠FLATTEN) ama artık pratikte önemsiz: v7'de max DD zaten breaker
   eşiğinin altında, breaker hiç tetiklenmiyor.
6. **Walk-forward kabul kriteri hâlâ GEÇMEDİ, MC worst-5% (dd_p5=-%10.29)
   hâlâ breaker eşiğine yakın/aşkın** (v6'dan iyileşti ama sınırda) — v7'de
   doğrulandı ki bunlar motor/veri bug'ı DEĞİL, stratejinin kendi zayıflığı.
7. KCHOL 2007-06-08 hâlâ açıklanamadı (DATA_AUDIT_v2.md'de "açıklanamayan
   gap" — dış BIST/KAP doğrulaması gerekiyor, bu turda yapılmadı).
8. ~~Gate ablasyon (DIAGNOSTICS_v6.md Paket 3): trend/regime/rsi izole
   ölçümde değer katmıyor gibi görünüyor~~ **PORTFÖY SEVİYESİNDE TEST EDİLDİ
   (ABLATION_PORTFOLIO.md) VE ÇELİŞTİĞİ BULUNDU** — no_trend/no_rsi belirgin
   daha kötü (özellikle no_rsi: OOS max DD -31%'e fırlıyor), no_regime karma
   (getiri/Sharpe iyileşiyor ama DD kötüleşiyor). "Bu gate'ler gereksiz"
   hükmü artık DESTEKLENMİYOR — izole ölçüm portföy-seviyesi risk azaltma
   etkileşimini yakalayamamış.
9. `.gitignore`'da genel `.env`/`*.log` deseni eksikliği (A3'ten, düşük öncelik).
10. **FX snapshot'ında EUR_USD/GBP_USD 2010-07-01'de OHLC ihlali** (close>high,
    yfinance kaynaklı, USD_JPY etkilenmedi) — DÜZELTİLMEDİ (E1 read-only
    kapsamı dışı), E2'ye not düşüldü: bu iki sembol backtest'e girmeden önce
    ele alınmalı (aksi halde `data/quality.py::check_quality` bu günü FAIL
    sayıp o sembolü işlemsiz bırakır — kendi içinde güvenli ama not edilmeli).
11. **`oanda.py` hiçbir practice hesapla test edilmedi** (referans
    implementasyon, CLAUDE.md'nin AlgoLab auth.py emsaliyle tutarlı) — E3'te
    doğrulanacak. E1'in FX snapshot'ı bu modülden değil `yf_fx.py`'den üretildi.
12. **Ekonomik takvim vetosu (FX) backtest'te modellenemez** — yalnızca
    içinde bulunulan haftayı veren ücretsiz bir kaynak bulundu, tarihsel
    arşiv yok (Bölüm 10.4 fallback protokolü devrede, E2+'ta uygulanacak).
13. US evreni survivorship yanlılığı taşıyor (bilinen, kabul edilen sınırlama
    — bkz. DATA_AUDIT_US.md).
14. **YENİ (bu tur) — `pending_exits` set-iteration determinizm bug'ı
    DÜZELTİLDİ**: `backtest/engine.py`'de aynı güne denk gelen çoklu sembol
    çıkışlarının sırası PYTHONHASHSEED'e göre süreç başına değişebiliyordu
    (finansal sonuç etkilenmez, yalnızca trades.csv satır sırası). Düzeltme
    `sorted(pending_exits)`. v7'nin dondurulmuş trades.csv'si bu yüzden yeni
    koşumlarla artık İÇERİK olarak (sort sonrası) aynı ama BAYT-BAYT aynı
    DEĞİL (2 bilinen aynı-gün-çoklu-çıkış çakışmasında sıra farklı) — v7
    DEĞİŞTİRİLMEDİ, bu beklenen bir fark.
15. **Hiçbir varyant (baseline dahil) USD-CAGR>0 başarı çıtasını geçmiyor**
    (bkz. KALICI KAYIT 1) — TRY'nin USD karşısındaki yapısal değer kaybı
    baskın. max DD/endeks-DD oranı kısmı İYİ (0.106-0.172).
16. ~~4/5 varyantta breaker 1 kez tetiklendi — kök nedeni İNCELENMEDİ~~
    **İNCELENDİ (R1): 4/4 "gerçek drawdown"** — veri artefaktı değil (bkz.
    ABLATION_PORTFOLIO.md "Breaker Adli İnceleme" eki).
17. Golden regresyon çapası artık v7 değil `backtest-v7.1-golden` —
    `runtime/backtest_reports_v7_1/trades.csv` (bu dosya özel olarak
    commitlenmiş, `.gitignore` istisnası ile). v7 tarihsel kayıt olarak
    kalıyor.

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (e31e401); BIST seans saatleri yaklaşık; backtest degrade modda;
compute_target max(resistance, fallback) (67d2dd6); gate_trigger_4h degrade
modda son-3-bar-pattern VEYA breakout (67d2dd6); walk-forward date_range/
precomputed_features (60a6d3f); adx_min=25 (d6ea8fc); 12 sembol evreni +
2005-01-01 + OHLC tolerans fix'i (dc56ed2); HARDENING.md Bölüm A (eb3b21d);
breaker backtest entegrasyonu + MC dd_p5 düzeltmesi (c906d10, 53ba4b3); v7
motor+veri düzeltme turu — equity forward-fill + aynı-gün-çoklu-onay +
data/cleaning.py + DATA_AUDIT_v2.md + performans (5227438); EXPANSION.md
eklendi (d0ab81d); E1 veri temeli — US/FX adapter'ları, snapshot'lar,
DATA_AUDIT_US/FX.md, data/events.py; portföy ablasyon turu — disabled_gates
parametresi + pending_exits determinizm düzeltmesi + ABLATION_PORTFOLIO.md
(bu tur).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

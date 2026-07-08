# STATUS Arşivi — Tamamlanmış Tur Detayları

> Bu dosya, `STATUS.md`'den arşivlenen tamamlanmış turların TAM detay
> bloklarını (kronolojik sırayla, en eski → en yeni) ve çözülmüş/üstü çizili
> "Bilinen sorun/blok" maddelerini içerir. HİÇBİR ŞEY SİLİNMEDİ — yalnızca
> güncel `STATUS.md`'yi kısa tutmak için buraya taşındı. Güncel durum, KALICI
> KAYITLAR ve aktif kuyruk için `STATUS.md`'ye bakın.

---

## 1) Harness düzeltme turu (onaylı, hâlâ geçerli)
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

## 2) Read-only teşhis turu — DIAGNOSTICS_v6.md (onaylı, hâlâ geçerli)
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

## 3) Motor+veri düzeltme turu — v7 (onaylı, hâlâ geçerli)
DIAGNOSTICS_v6.md Paket 1 bulgularının düzeltmesi.
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

## 4) EXPANSION.md E1 — Veri Temeli (onaylı "E1 onaylandı, başlat", hâlâ geçerli)
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

## 5) Portföy-seviyesi gate ablasyon turu (onaylı, hâlâ geçerli)
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

## 6) Ablasyon kapanış turu — R1 (breaker adli incelemesi + golden yeniden mühürleme, onaylı, hâlâ geçerli)
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

## 7) S1 spike backtest — D1 tasarımının tek-tur testi (onaylı, hâlâ geçerli)
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

## 8) S1b ölçüm tamamlama turu — nakit-getiri düzeltmesi (onaylı, hâlâ geçerli)
- **Madde 1 — TRY gecelik faiz aux snapshot**: `data/snapshots/aux/2026-07-07/TRY_ON_RATE.parquet`.
  Kaynak merdiveni denendi: (a) EVDS API yok/başarısız, (b) TCMB statik
  indirme başarısız (302 login yönlendirmesi), (c) FRED/OECD
  `IRSTCI01TRM156N` kullanıldı (herkese açık, doğrulanmış, TCMB'nin kendisi
  değil ama gerçek veri — hiçbir şey uydurulmadı). 2005-01→2026-03, aylık,
  9 ay boşluk (2023, muhtemelen deprem sonrası OECD veri aksaması).
- **Madde 2 — `backtest/regime_core.py`'ye nakit getirisi eklendi** (tek
  davranış değişikliği): `r_net=max(faiz-200bp,0)`, ACT/365,
  `cash*=(1+r_net/365)^gün_farkı`. Pozisyon günlerinde/EXIT gününde
  tahakkuk yok. Zorunlu regresyon kanıtı: `cash_rate=None` VE
  `cash_rate=<tümü sıfır>` ikisi de S1 ile bayt-bayt aynı (hem kütüphane
  hem CLI seviyesinde doğrulandı). 22 yeni birim testi, hepsi yeşil.
- **Madde 3 — S1 süiti nakit getirisiyle yeniden koşuldu**: `tools/run_regime_core.py`'ye
  `--cash-yield` bayrağı eklendi (verilmezse S1 davranışı korunur).
  `REGIME_CORE_S1B.md` yazıldı (a-j bölümleri, mühürlü tablo MEKANİK
  dolduruldu, hüküm verilmedi).
- 307+ test yeşil (regresyon yok). `git diff` korunan dosyalarda (motor,
  strateji, risk, config, mevcut snapshot'lar) BOŞ.

## 9) S1b kapanış turu — eksik MC bölümü + resmi kabul kaydı (onaylı, hâlâ geçerli)
- **Madde 1 — Eksik MC satırı düzeltildi**: S1b'nin ana koşumu sırasında
  ZATEN üretilmiş olan (ama ilk yazımda REGIME_CORE_S1B.md'ye eklenmemiş)
  Monte Carlo sonucu (`runtime/regime_core_s1b/summary.json::monte_carlo_monthly`,
  500 koşum, seed=42 — S1 ile AYNI yöntem/örnek sayısı) rapora "(g) Monte
  Carlo" bölümü olarak eklendi (mevcut içerik değiştirilmedi, yalnızca
  ekleme yapıldı). dd_p5: S1 -%48.57 → S1b -%44.68 (üç persentilde de
  tutarlı iyileşme). Yeni bir koşum ÇALIŞTIRILMADI — veri zaten vardı.
- **Madde 2 — KALICI KAYIT 6 eklendi**: D1 ailesinin resmi kabulü + yeni
  ailenin operasyonel breaker kalibrasyonu (ALARM -%25, FREEZE -%40) +
  kuyruğa iki madde (EVDS çapraz doğrulama, üretim nakit bacağı enstrümanı).
- **Madde 3 — Git tag**: `regime-core-s1b-accepted` bu kapanış commit'ine atıldı.
- Hiçbir eşik/parametre değiştirilmedi. `git diff backtest/engine.py
  strategy/ risk/ config/config.yaml` BOŞ.

## 10) EXPANSION.md E2 — Motor Genelleştirme turu (onaylı, hâlâ geçerli)
Çok-piyasa çekirdeği kuruldu (bkz. `EXPANSION_E2.md`), **DEMİR KURAL korundu:
her E2 commit'i BIST v7.1-golden'ıyla BAYT-BAYT aynı** (tests/test_golden_bist.py,
iki katman: cost_model=None + BIST CostModel carry=0). Tam süit 364 passed
(E2 öncesi 309). Golden regresyon çapası (İLK İŞ), MarketSpec + registry,
takvimler (XIST/XNYS/FX_24_5 + DST), gate_registry (bist davranış-nötr göç),
CostModel katmanı (bist/us/fx) + daily_carry hook, yön farkındalığı (Direction
mekaniği — short GATE tasarımı KAPSAM DIŞI), config yükleyici (portfolio+markets,
11.4 eşdeğerlik), FX OHLC onarımı + earnings/econ veto altyapısı.
- E2.0–E2.9 sırayla, her biri golden-kanıtlı ayrı commit (git log).
- Kapanış: EXPANSION_E2.md raporu, tam süit 364 passed, son golden bayt-bayt.
- (Kalıcı E2 bulguları/kararları KALICI KAYIT 7'de — STATUS.md'de kalır.)

---

## Bilinen sorun/blok — çözülmüş / tarihsel maddeler (arşiv)

Bu maddeler STATUS.md'nin aktif "Bilinen sorun/blok" listesinden buraya taşındı
(çözüldü ya da artık tarihsel). Orijinal numaralar korunmuştur.

2. ~~v5/v6'nın -%20.74 max drawdown rakamı güvenilir değildi~~ **DÜZELTİLDİ
   (v7): equity forward-fill + hayalet-bar filtresi sonrası gerçek max DD
   -%6.71.** Breaker artık hiç tetiklenmiyor.
3. ~~max_open_positions limiti aşılabiliyordu~~ **DÜZELTİLDİ (v7): tüm
   tarihçe boyunca 0 ihlal günü, doğrulandı.**
4. ~~Breaker entegrasyonu backtest'i ~3× yavaşlatıyordu~~ **DÜZELTİLDİ (v7):
   CLI çağrısı başına tek paylaşılan geçici dizin, v7 koşumu v6'ya göre
   ~3.6× hızlandı (~1sa49dk vs ~6.5sa).**
8. ~~Gate ablasyon (DIAGNOSTICS_v6.md Paket 3): trend/regime/rsi izole
   ölçümde değer katmıyor gibi görünüyor~~ **PORTFÖY SEVİYESİNDE TEST EDİLDİ
   (ABLATION_PORTFOLIO.md) VE ÇELİŞTİĞİ BULUNDU** — no_trend/no_rsi belirgin
   daha kötü (özellikle no_rsi: OOS max DD -31%'e fırlıyor), no_regime karma
   (getiri/Sharpe iyileşiyor ama DD kötüleşiyor). "Bu gate'ler gereksiz"
   hükmü artık DESTEKLENMİYOR — izole ölçüm portföy-seviyesi risk azaltma
   etkileşimini yakalayamamış.
10. **FX snapshot'ında EUR_USD/GBP_USD 2010-07-01'de OHLC ihlali** (close>high)
    — **ÇÖZÜLDÜ (E2)**: `data/cleaning.py::repair_fx_ohlc` (FX-özel, loglanan,
    bellek-içi onarım; snapshot'a dokunmaz). Bkz. DATA_AUDIT_FX.md E2 notu.
14. **`pending_exits` set-iteration determinizm bug'ı DÜZELTİLDİ**:
    `backtest/engine.py`'de aynı güne denk gelen çoklu sembol çıkışlarının
    sırası PYTHONHASHSEED'e göre süreç başına değişebiliyordu (finansal sonuç
    etkilenmez, yalnızca trades.csv satır sırası). Düzeltme `sorted(pending_exits)`.
    v7'nin dondurulmuş trades.csv'si bu yüzden yeni koşumlarla İÇERİK olarak
    (sort sonrası) aynı ama BAYT-BAYT aynı DEĞİL (2 aynı-gün-çoklu-çıkış
    çakışması) — v7 DEĞİŞTİRİLMEDİ, beklenen fark; golden artık v7.1-golden.
16. ~~4/5 varyantta breaker 1 kez tetiklendi — kök nedeni İNCELENMEDİ~~
    **İNCELENDİ (R1): 4/4 "gerçek drawdown"** — veri artefaktı değil (bkz.
    ABLATION_PORTFOLIO.md "Breaker Adli İnceleme" eki).
9. ~~`.gitignore`'da genel `.env`/`*.log` deseni eksikliği (A3'ten, düşük
   öncelik)~~ **KAPANDI (F5-B2a.1, 2026-07-08)**: genel `secrets.env` / `*.env`
   / `runtime/manual/` deseni eklendi (`config/secrets.env.example` istisna);
   `git log --all` ile hiçbir secrets dosyasının hiçbir commit'te yer almadığı
   doğrulandı. Bkz. `PHASE5B2A_REVIEW.md` "B2a.1 Eki".

# Proje Durumu
Son güncelleme: 2026-07-06T11:55:00+03:00 (Europe/Istanbul)
Şu an: **Motor+veri düzeltme turu (v7) tamamlandı — DURMA NOKTASI 1'de
duruluyor (Bölüm 0.1). Faz 5'e geçilmedi, hiçbir strateji eşiği/gate/parametre
değiştirilmedi, kullanıcı onayı bekleniyor. HARDENING.md Bölüm B/C'ye
başlanmadı. v7, v1-v6'nın yerini alan TEK geçerli backtest taban çizgisidir.**
Tamamlanan fazlar: Faz 1-3, Faz 4 (Backtest Harness — v1→v7) + HARDENING.md
Bölüm A (kalite/güvenilirlik sertleştirme, CLAUDE.md'ye ek) + Teşhis turu v6
+ Motor+veri düzeltme turu v7.

Bu oturumda yapılan (onaylı motor+veri düzeltme turu — v7, DIAGNOSTICS_v6.md'nin
Paket 1 bulgularının düzeltmesi):
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

**Sırada:** Hiçbir şey — burada duruluyor (Durma Noktası 1). Kullanıcının
kararı bekleniyor. Önerilen (kullanıcı onayı gerekir): Paket 1'in iki bug'ı
artık DÜZELTİLDİ ve v7'de doğrulandı; kalan gerçek (bug olmayan) zayıflıklar
— walk-forward OOS performansı ve MC worst-5% sınırda kalması — ile
DIAGNOSTICS_v6.md Paket 3'ün gate ablasyon bulgusu (trend/regime/rsi izole
ölçümde değer katmıyor gibi görünüyor) birlikte, artık bir gate/parametre
yeniden tasarım konuşmasının girdisi olabilir.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1)** — kasıtlı, aşılamaz kapı.
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
8. Gate ablasyon (DIAGNOSTICS_v6.md Paket 3): trend/regime/rsi izole ölçümde
   değer katmıyor gibi görünüyor (counterfactual PF > baseline PF); portföy-
   seviyesi etkiler ölçülmedi — eşik değiştirmeye tek başına yeterli kanıt
   değil, ama artık (v7'nin temiz taban çizgisiyle) bir tasarım konuşmasının
   girdisi olabilir.
9. `.gitignore`'da genel `.env`/`*.log` deseni eksikliği (A3'ten, düşük öncelik).

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (e31e401); BIST seans saatleri yaklaşık; backtest degrade modda;
compute_target max(resistance, fallback) (67d2dd6); gate_trigger_4h degrade
modda son-3-bar-pattern VEYA breakout (67d2dd6); walk-forward date_range/
precomputed_features (60a6d3f); adx_min=25 (d6ea8fc); 12 sembol evreni +
2005-01-01 + OHLC tolerans fix'i (dc56ed2); HARDENING.md Bölüm A (eb3b21d);
breaker backtest entegrasyonu + MC dd_p5 düzeltmesi (c906d10, 53ba4b3); v7
motor+veri düzeltme turu — equity forward-fill + aynı-gün-çoklu-onay +
data/cleaning.py + DATA_AUDIT_v2.md + performans (5227438).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

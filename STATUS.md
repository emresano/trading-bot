# Proje Durumu
Son güncelleme: 2026-07-06T14:30:00+03:00 (Europe/Istanbul)
Şu an: **Teşhis turu v6 (read-only, DIAGNOSTICS_v6.md) tamamlandı — DURMA
NOKTASI 1'de duruluyor (Bölüm 0.1). Faz 5'e geçilmedi, hiçbir eşik/parametre
değiştirilmedi, kullanıcı onayı bekleniyor. HARDENING.md Bölüm B/C'ye
başlanmadı.**
Tamamlanan fazlar: Faz 1-3, Faz 4 (Backtest Harness — v1→v6) + HARDENING.md
Bölüm A (kalite/güvenilirlik sertleştirme, CLAUDE.md'ye ek) + Teşhis turu v6.

Bu oturumda yapılan (onaylı read-only teşhis turu — DIAGNOSTICS_v6.md):
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
kararı bekleniyor. Önerilen (kullanıcı onayı gerekir): (a) Paket 1'deki iki
motor bug'ını (equity forward-fill + aynı-gün-çoklu-onay) ayrı bir onaylı
turda düzelt, (b) veri katmanına "tüm-sembollerde-eksik-tek-sembolde-var"
tatil/anomali kontrolü ekle, (c) düzeltmelerle v1-v6 sweep'ini yeniden koş,
(d) ancak o zaman gate eşiklerini (Paket 3 bulgusu ışığında) yeniden tasarım
konuşmasına aç.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1)** — kasıtlı, aşılamaz kapı.
2. **v5 VE v6'nın -%20.74 max drawdown rakamı güvenilir değil** (Paket 1) —
   EREGL'deki tek günlük hayalet-bar veri artefaktı + engine'in eksik fiyatlı
   pozisyonları sıfırlayan equity formülü. DÜZELTİLMEDİ, ayrı onaylı tur
   bekliyor. Bu düzeltilene kadar raporlanan max DD/MC sonuçlarına güvenmeyin.
3. **max_open_positions limiti aşılabiliyor** (gözlenen maks. 3, limit 2) —
   aynı-gün-çoklu-onay bug'ı (Paket 1). DÜZELTİLMEDİ, ayrı onaylı tur
   bekliyor.
4. Breaker entegrasyonu backtest'i ~3× yavaşlattı (tempfile per-call yükü) —
   performans turu gerekebilir (düşük öncelik, işlevsellik doğru).
5. Breaker, mevcut sıkı parametrelerle gerçekleşmiş max drawdown'u
   SINIRLAMIYOR (yalnızca sonraki girişleri engelliyor) — bu tasarım gereği
   (FREEZE≠FLATTEN) ama kullanıcının bilmesi gereken bir sınırlama.
6. v5'ten taşınan bulgular hâlâ açık: adx_min=25 geniş sweep'te desteklenmiyor
   (adx_min=15 daha iyi PF gösterebiliyor, ama artık breaker'la daha düşük
   drawdown'la); walk-forward DD kriteri hâlâ geçmiyor.
7. Gate ablasyon (Paket 3): trend/regime/rsi izole ölçümde değer katmıyor
   gibi görünüyor (counterfactual PF > baseline PF); portföy-seviyesi
   etkiler ölçülmedi — eşik değiştirmeye tek başına yeterli kanıt değil.
8. `.gitignore`'da genel `.env`/`*.log` deseni eksikliği (A3'ten, düşük öncelik).

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (e31e401); BIST seans saatleri yaklaşık; backtest degrade modda;
compute_target max(resistance, fallback) (67d2dd6); gate_trigger_4h degrade
modda son-3-bar-pattern VEYA breakout (67d2dd6); walk-forward date_range/
precomputed_features (60a6d3f); adx_min=25 (d6ea8fc); 12 sembol evreni +
2005-01-01 + OHLC tolerans fix'i (dc56ed2); HARDENING.md Bölüm A (eb3b21d);
breaker backtest entegrasyonu + MC dd_p5 düzeltmesi (c906d10, 53ba4b3).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

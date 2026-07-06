# Proje Durumu
Son güncelleme: 2026-07-06T08:55:00+03:00 (Europe/Istanbul)
Şu an: **Harness düzeltme turu (v6) + Gate Katkı Analizi tamamlandı — DURMA
NOKTASI 1'de duruluyor (Bölüm 0.1). Faz 5'e geçilmedi, kullanıcı onayı
bekleniyor. HARDENING.md Bölüm B/C'ye başlanmadı.**
Tamamlanan fazlar: Faz 1-3, Faz 4 (Backtest Harness — v1→v6) + HARDENING.md
Bölüm A (kalite/güvenilirlik sertleştirme, CLAUDE.md'ye ek).

Bu oturumda yapılan (onaylı harness düzeltme turu):
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
kararı bekleniyor.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1)** — kasıtlı, aşılamaz kapı.
2. Breaker entegrasyonu backtest'i ~3× yavaşlattı (tempfile per-call yükü) —
   performans turu gerekebilir (düşük öncelik, işlevsellik doğru).
3. Breaker, mevcut sıkı parametrelerle gerçekleşmiş max drawdown'u
   SINIRLAMIYOR (yalnızca sonraki girişleri engelliyor) — bu tasarım gereği
   (FREEZE≠FLATTEN) ama kullanıcının bilmesi gereken bir sınırlama.
4. v5'ten taşınan bulgular hâlâ açık: adx_min=25 geniş sweep'te desteklenmiyor
   (adx_min=15 daha iyi PF gösterebiliyor, ama artık breaker'la daha düşük
   drawdown'la); walk-forward DD kriteri hâlâ geçmiyor.
5. `.gitignore`'da genel `.env`/`*.log` deseni eksikliği (A3'ten, düşük öncelik).

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (e31e401); BIST seans saatleri yaklaşık; backtest degrade modda;
compute_target max(resistance, fallback) (67d2dd6); gate_trigger_4h degrade
modda son-3-bar-pattern VEYA breakout (67d2dd6); walk-forward date_range/
precomputed_features (60a6d3f); adx_min=25 (d6ea8fc); 12 sembol evreni +
2005-01-01 + OHLC tolerans fix'i (dc56ed2); HARDENING.md Bölüm A (eb3b21d);
breaker backtest entegrasyonu + MC dd_p5 düzeltmesi (c906d10, 53ba4b3).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

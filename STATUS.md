# Proje Durumu
Son güncelleme: 2026-07-06T02:30:00+03:00 (Europe/Istanbul)
Şu an: **HARDENING.md Bölüm A (A1-A4) tamamlandı — DURMA NOKTASI 1'de
duruluyor (Bölüm 0.1). Faz 5'e geçilmedi, kullanıcı onayı bekleniyor.
Bölüm B/C'ye başlanmadı.**
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal
Motoru), Faz 3 (Risk Motoru), Faz 4 (Backtest Harness — v1→v5, bkz. önceki
girdiler) + **HARDENING.md Bölüm A** (kalite/güvenilirlik sertleştirme —
CLAUDE.md'ye ek, onu geçersiz kılmaz).

Bu oturumda yapılan (HARDENING.md kurulum + Bölüm A):
- `HARDENING.md` repoya eklendi (kullanıcı sağladı); `CLAUDE.md`'ye tek satır
  işaret eklendi: Faz 5'te Bölüm B bağlayıcı olacak. Başka hiçbir değişiklik yok.
- **A1 (Snapshot + damgalama):** `data/snapshots/2026-07-06/` — v5 evreninin
  (12 sembol) 2005-01-01 sonrası verisi donduruldu (data/historical cache'inden,
  yeniden indirilmedi — v5'in fiilen kullandığı bytes). `manifest.json`: SHA256
  + tarih aralığı + yfinance sürümü + indirme parametreleri. `backtest/cli.py`:
  `--snapshot <dizin>` (ağdan indirme yok, yalnızca parquet okur; verilmezse
  eski davranış aynen korunur) + rapor başlığına 3 damga (git commit + config
  hash + snapshot manifest hash). **Kanıtlandı:** aynı snapshot+config ile
  tek-sembollü koşu 2× çalıştırıldı, trades.csv + report.md bayt-bayt aynı.
  Git tag'leri (yerel): backtest-v1..v5, ilgili commit'lere iğnelendi.
- **A2 (Veri bütünlüğü denetimi, read-only):** `tools/data_audit.py` +
  `DATA_AUDIT.md`. Eksik bar (sembol-çapraz), sıfır/negatif fiyat, yinelenen
  tarih, OHLC tutarlılığı, şüpheli sıçrama taraması (>%25, sınıflandırma
  DENEMESİ — kesin hüküm yok). **Sonuç: 12/12 sembol PASS/WARN, 0 FAIL.** 2 WARN
  (KCHOL 2007-06-07 -%26.8, TCELL 2005-05-16 +%26.0 — hacimle net açıklanamıyor,
  sınıflandırılamadı). v5 sonuçları karantinada DEĞİL. Ek madde: dc56ed2'deki
  OHLC rtol/atol toleransı sentetik sınır örnekleriyle kanıtlandı (epsilon ve
  %0.3 PASS, %5 gerçek ihlal hâlâ FAIL — 10× güvenlik marjı).
- **A3 (Sır/anahtar güvenlik denetimi):** `SECURITY_AUDIT.md`. Git geçmişi
  regex ile tarandı — **TEMİZ**, hiç sır bulunamadı (secrets.env hiçbir
  commit'te hiç var olmamış). `.gitignore` gerçek sır dosyasını kapsıyor;
  genel `.env`/`*.log` deseni eksikliği tespit edildi (düşük risk, UYGULANMADI,
  ayrı onay gerektirir). Faz 5 hedef tasarımı belgelendi (.env+600 izin,
  loglarda otomatik maskeleme).
- **A4 (Ortam sabitleme):** `requirements.lock` (pip freeze, Python 3.11.6) +
  `README.md` (yalnızca "temiz kurulumdan yeniden üretim" bölümü — tam kılavuz
  Faz 5'te). **Kanıtlandı:** tamamen temiz bir venv'de yalnızca lock dosyasından
  kurulum + tam test süiti — 180/180 yeşil.
- `HARDENING_STATUS.md` yazıldı (A1-A4 durum tablosu).

**Sırada:** Hiçbir şey — burada duruluyor (Durma Noktası 1 + HARDENING.md'nin
kendi "Bölüm A bitince dur" kuralı). Kullanıcının kararı bekleniyor: Bölüm B
(Faz 5 bağlayıcı spesifikasyonu) veya C'ye (sonrası) geçiş, veya Faz 4'ün
v5 bulgusuna (adx_min sıkılaştırmasının geniş örneklemde tutmadığı) dönük bir
karar.

Bilinen sorun/blok:
1. **Kullanıcı onayı bekleniyor (Durma Noktası 1 + HARDENING.md Bölüm A
   kapanışı)** — kasıtlı, aşılamaz kapı.
2. v5'in üç kapsam-dışı bulgusu hâlâ açık: backtest motoru drawdown breaker'ı
   simüle etmiyor; Monte Carlo kırmızı bayrağı muhtemelen yanlış persentili
   (dd_p95 yerine dd_p5) kontrol ediyor; adx_min=25 geniş örneklemde
   desteklenmiyor.
3. A3'te tespit edilen `.gitignore` iyileştirmeleri (genel `.env`/`*.log`
   deseni) uygulanmadı — düşük öncelik, ayrı onay gerektirir.
4. `indicators.engine.build_features`, çok kısa DataFrame'de çöküyor (önceki
   turlardan taşınan, düşük öncelikli).

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (e31e401); BIST seans saatleri yaklaşık; `data.historical.
download_bars` `period="max"` zorunlu; resmi tatil takvimi MVP dışı; MACD
"son 2 bar yükseliş" = `hist[t]>hist[t-1]`; exit "3 bar düşüş" = kesin azalan
üçlü sıralama; backtest degrade modda çalışıyor; compute_target
max(resistance, fallback) (67d2dd6); gate_trigger_4h degrade modda son-3-bar-
pattern VEYA breakout (67d2dd6); walk-forward date_range/precomputed_features
ile tam tarihçe warm-up (60a6d3f); adx_min=25 (d6ea8fc); 12 sembol evreni +
2005-01-01 başlangıç + OHLC tolerans fix'i (dc56ed2); HARDENING.md Bölüm A
tamamlandı, Bölüm B Faz 5'te bağlayıcı (eb3b21d).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 + HARDENING.md Bölüm A
kapanışı nedeniyle duruldu.

# PHASE5B1_REVIEW.md — Faz 5 / F5-B1 Kapanış Raporu

**Tarih:** 2026-07-07 (Europe/Istanbul)
**Kapsam:** F5-B1 — **Gölge paper başlatma (AlgoLab'SIZ).** yfinance EOD veri kaynağı +
gölge scheduler + ilk-başlatma tasarımı + launchd/operatör kılavuzu + B7-D1 önerisi +
EVDS deneme + gözetimli ilk koşu. **Faz 6 BAŞLATILMADI; real'e adım YOK.**

**EK KAYIT (bağlayıcı):** AlgoLab 2025-12-31'de kapatıldı (resmî mail teyidi). F5-B2
yeniden tanımlandı: **AlgoLab canlı entegrasyonu İPTAL**; yerine `ManualExecutionAdapter`
(sinyal → Telegram → kullanıcı elle yürütür → fill'ler onayla kaydedilir; B2 mutabakatı
bu kayıtlara karşı). `execution/algolab/` **silinmedi**, "kapatılmış-broker referansı"
olarak docstring'le işaretlendi.

**DEĞİŞMEZLER korundu:** `config/config.yaml` `mode: paper` + eşikler DEĞİŞMEDİ;
`v7.1-golden` her commit 3/3 bayt-bayt; D1 üretim sinyal/boyutlama fonksiyonları
(`strategy/regime_core.py`) DEĞİŞMEDİ — canlı runner ÇAĞIRIR.

**Tam süit: 470 passed** (F5-A 456 + F5-B1 14: live_feed 6 + scheduler 8), golden 3/3.

---

## 1. Teslimat tablosu

| # | Madde | Teslimat | Commit | Kanıt |
|---|---|---|---|---|
| 1 | yfinance veri bağlama | `data/live_feed.py` (LiveDataFeed) | 8d1ca1c | 6 test + canlı kanıt |
| 2 | gölge scheduler | `main.py` (PaperScheduler) | (f5b1-2) | 8 test |
| 3 | ilk-başlatma (INITIAL_ENTER) | runner `initialize_flat(adopt)` | (f5b1-2) | active dry-run |
| 4 | launchd + log rot. + kılavuz | `deploy/*`, `OPERATOR_GUIDE.md` | (f5b1-4) | watchdog CLI koştu |
| 5 | B7-D1 önerisi | `B7_D1_PROPOSAL.md` | (f5b1-5) | — |
| 6 | EVDS deneme | `tools/evds_compare.py`, `EVDS_COMPARISON.md` | (f5b1-6) | BLOCKED (endpoint) |
| 7 | gözetimli ilk koşu | canlı CLI + injected-clock örnekleri | bu rapor | aşağıda |

---

## 2. Çapraz-veri raporu (madde 1)

**Snapshot ↔ yfinance tam-tarihçe uyumu:** 12 sembol, 2005→2026-07-03 örtüşen
**66.132 bar-günün TAMAMINDA** kapanış farkı ≤ ~1e-7 (max 6.3e-7); **0 çakışma**.
Snapshot yfinance'e sadık, düzeltme (split/temettü) kayması yok. (`runtime/f5b1/
cross_consistency_full.csv`.)

**Canlı depo ↔ backtest kompozit paritesi (parite ön şartı):** live store'dan hesaplanan
kompozit, backtest snapshot'ından (`load_and_clean_universe`) hesaplananla **5511 ortak
günde max fark = 0.0** (bit-bit). Temizlik paritesi (normalize_bist_dates + evren-düzeyi
ghost filtre; bootstrap'ta 1 ghost = EREGL 2024-04-09, backtest ile aynı) kanıtlandı.

**Kompozit bugüne (2026-07-07) kadar hesaplanabiliyor:** MA(200) hazır (tüm 12 sembol
5513 bar); bootstrap (snapshot→07-03) + yfinance EOD (07-06/07-07, +24 bar, 0 çakışma).

## 3. Gözetimli ilk koşu (madde 7)

**A) Gerçek CLI (seans-içi koştu):** `main.py --bootstrap --refresh --cycle`. Sonuç:
observe mod, `regime_on=True`, **işlem YOK** (equity 100.000 sabit), heartbeat yazıldı,
`signal_eval` günlüğe düştü. **Kritik bulgu — oluşmakta olan bar:** koşum 18:00 kapanışı
ÖNCESİNDE yapıldığından bugünün barı henüz FİNAL değildi → scheduler bunu yakaladı:
`WARN SIGNAL: as_of barı henüz KAPANMADI → PROVISIONAL` + journal `provisional: true`.
(Aynı gün iki farklı saatte yfinance 07-07 kapanışını farklı verdi — 12 sembolde de tek
fark bu bardaydı; eski barlar bit-bit aynı. Bu, "son bar kapanmış olmalı" kuralının canlı
kanıtıdır; **kod-düzeyi koruma eklendi** — sinyal/yürütme yalnız FİNAL bardan.)

**B) Seans SONRASI (injected saat):** aynı gün kapanış+grace sonrası → `provisional=False`,
`regime_on=True`, kompozit ~706.5. Final bar → temiz.

**C) Active dry-run (scratch; gerçek go-live DEĞİL):** `go_live_date=2026-07-06`, rejim
AÇIK → 2026-07-07 t+1 kapanışında **INITIAL_ENTER** (12 sembol basket, equity 99.943.96
= giriş komisyon/slippage maliyeti), **parite OK** (temiz replay ↔ canlı journal 1
anahtarlama özdeş). (`runtime/f5b1/supervised_samples.json`.)

Maskeli journal örneği (gerçek koşu):
```json
{"type":"signal_eval","mode":"observe","provisional":true,"date":"2026-07-07 00:00:00+00:00",
 "regime":{"composite":706.47,"ma":567.33,"ma_period":200,"upper_band":573.0,
 "lower_band":561.65,"confirm_count":3,"confirm_days":3,"regime_on":true},"in_position":false}
```

## 4. Mimari kararlar / dürüst çekinceler

1. **observe vs active + Faz 6.** `go_live_date=null` → observe (sinyal/journal/heartbeat,
   işlem YOK, hesap başlatılmaz). Faz 6 ölçüm penceresi BAŞLATILMADI — resmi başlangıç =
   operatörün `go_live_date` set etmesi (döngü birkaç gün stabil koştuktan sonra).
2. **Oluşmakta olan bar koruması (yeni).** Sinyal yalnız FİNAL (kapanmış) bardan hesaplanır;
   bugünün barı seans-içindeyse observe'da `provisional` işaretlenir, active'de yürütme son
   FİNAL güne sınırlanır. t+1 yürütme zaten (dünün kapanmış sinyaliyle) korumalıydı; bu
   ek katman sinyal KAYDINI da provisional bardan finalize etmez.
3. **Mutabakat GÖLGE modda.** Harici broker YOK (AlgoLab iptal) → harici pozisyon çekimi
   ATLANIR + açıkça loglanır; iç PaperBroker↔LocalLedger mutabakatı (F5A-3) çalışır.
4. **Parite (B5) gölge tanımı.** TEMİZ runner-replay (go-live'dan) ↔ canlı journal
   anahtarlama diff'i; fark = KIRMIZI ALARM. Üretim kodunu birebir kullanır → veri/state/kod
   kaymasını yakalar. Yalnız active modda anlamlı.
5. **Nakit bacağı** modellenmiş faiz (TRY_ON_RATE−200bp) — backtest'le AYNI formül; gerçek
   enstrüman real-öncesi kuyrukta (STATUS #19).
6. **EVDS BLOCKED (madde 6).** Anahtar VAR ama REST endpoint evds2→evds3 geçişiyle SPA
   döndürüyor (JSON yok). Snapshot DEĞİŞMEDİ; `tools/evds_compare.py` endpoint doğrulanınca
   yeniden koşulur (bkz. EVDS_COMPARISON.md). 2023 boşluğu ff → cash-yield MUHAFAZAKÂR sapma.

## 5. F5-B2 (yeniden tanımlı — AlgoLab İPTAL) açık maddeler

- **ManualExecutionAdapter tasarımı:** bot sinyali → Telegram bildirimi → kullanıcı elle
  yürütür → fill'ler kullanıcı onayıyla kaydedilir; B2 mutabakatı bu kayıtlara karşı çalışır.
- **Gerçek Telegram HTTP + gelen-komut long-poll alıcısı** (F5-A/B1 iskeleti token'sız).
- **BIST broker REST API pazarını periyodik izle** — uygun API çıkarsa `BrokerAdapter` ile
  entegre edilebilir (kuyruk).
- **EVDS endpoint doğrulama** (kuyruk #18, real-öncesi).
- **Gerçek nakit bacağı enstrümanı** (kuyruk #19, real-öncesi).
- B1 kalanı: T+2 takas nakit muhasebesi, tick/lot yuvarlama, tedbir listesi (gölge EOD'de
  pratik etki sınırlı; manuel yürütmede kullanıcı gözetiminde).

## 6. Değerlendirme (Claude Code — karar kullanıcının)

F5-B1, paper döngüsünü AlgoLab olmadan GERÇEK veriyle (yfinance EOD) uçtan uca çalışır hale
getirdi: canlı depo↔backtest kompozit paritesi bit-bit, snapshot↔yfinance 66k bar-günde
temiz, gözetimli koşu sinyal/journal/heartbeat üretti, ilk-başlatma (INITIAL_ENTER) gerçek
veriyle doğrulandı. Gözetimli koşu ayrıca gerçek bir riski (oluşmakta olan bar) ortaya
çıkardı ve kod-düzeyi koruma eklendi. `mode`/eşikler/D1 fonksiyonları ve v7.1-golden
korundu; Faz 6/real'e adım atılmadı. Sıradaki adım (go_live kararı / F5-B2 ManualExecution
tasarımı) kullanıcının.

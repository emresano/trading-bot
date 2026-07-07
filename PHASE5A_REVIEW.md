# PHASE5A_REVIEW.md — Faz 5 / F5-A Kapanış Raporu

**Tarih:** 2026-07-07 (Europe/Istanbul)
**Kapsam:** Faz 5 (paper) — **F5-A** (AlgoLab'a CANLI BAĞLANTI YOK; tüm modüller
offline, fixture/kuru-testli). Onay: Durma Noktası 1 kullanıcı tarafından açıldı
(STATUS KALICI KAYIT 9). Koşulan aile: `regime_core` (D1, KALICI KAYIT 6/8).

**DEĞİŞMEZLER korundu:** `config/config.yaml` `mode: paper` ve eşikler DEĞİŞMEDİ;
`v7.1-golden` her commit'te 3/3 bayt-bayt yeşil; D1 üretim sinyal/boyutlama
fonksiyonları (`strategy/regime_core.py`) DEĞİŞMEDİ — canlı runner onları ÇAĞIRIR.

**Durma Noktası 2 (paper→real) AYNEN kapalı** — "real'e geç" yolu kod/komut olarak
hiçbir yerde yok; Telegram'da bile tüm 'real' varyantları açıkça reddedilir (test edildi).

---

## 1. Aşama tablosu (F5-A)

| Aşama | Teslimat | Commit | Test | Durum |
|---|---|---|---|---|
| F5A-0 | PHASE5_PLAN.md + STATUS KAYIT 9 | 0b6f600 | — | ✅ |
| F5A-1 | `data/live_store.py` (LiveHistoryStore) | cf26836 | 8 | ✅ |
| F5A-2 | `execution/{broker_adapter,paper_broker,regime_core_runner}.py` | 18406cf | 11 | ✅ |
| F5A-3 | `safety/reconciliation.py` (B2) | a1e44ef | 5 | ✅ |
| F5A-4 | `safety/kill_switch.py` + config safety (B3) | b60ede0 | 9 | ✅ |
| F5A-5 | `journal/{masking,decision_journal}.py` (B4) | 2cec791 | 6 | ✅ |
| F5A-6 | `safety/parity.py` (B5) | 4335e21 | 3 | ✅ |
| F5A-7 | `notify/{telegram_bot,eod_summary}.py`, `safety/heartbeat.py` (B6) | 2fda861 | 16 | ✅ |
| F5A-8 | `execution/algolab/{auth,client,adapter}.py` (fixture) | f1e8aab | 12 | ✅ |
| F5A-9 | `config/bist_calendar.yaml` + `core/bist_calendar.py` (B1) | 970caa2 | 8 | ✅ |
| F5A-Z | bu rapor + STATUS + tam süit + push | — | tümü | ✅ |

**Yeni test:** +78 (F5-A). Baseline 378 → **456 passed** (tam süit, aşağıda).
Her commit v7.1-golden 3/3 bayt-bayt doğrulanarak atıldı.

---

## 2. HARDENING B1–B7 kapsama durumu

| Madde | Gereksinim | F5-A durumu | Not / F5-B'ye kalan |
|---|---|---|---|
| **B1** | Seans/takvim resmî kaynakla doğrula; müzayedede emir yok; T+2; tick/lot; tedbir listesi | **Kısmî ✅** | Seans saatleri + 2026 tatil/yarım-gün DOĞRULANDI (config'e taşındı); müzayede-emir-yok tasarlandı (PaperBroker session guard + calendar). **F5-B:** T+2 takas nakit muhasebesi, tick/lot yuvarlama tablosu, tedbir/brüt-takas listesi günlük kontrolü — AlgoLab kuralından doğrulanacak. |
| **B2** | Başlangıç mutabakatı + durum kurtarma; uyuşmazlık→FREEZE; "emir gönderildi/yanıt yok/çöküş" | **✅** | `safety/reconciliation.py`; LocalLedger; çöküş senaryosu mock testli; adopt yalnız kullanıcı. **F5-B:** broker=AlgoLab gerçek pozisyon/emir çekimiyle bağlanacak. |
| **B3** | Kill-switch hiyerarşisi (günlük zarar, ardışık-N, DD breaker, veri, API) | **✅** | 5 switch; eşikler config (D1-uyarlı ÖNERİ); tümü kuru-testli; FREEZE çıkışı yalnız kullanıcı. |
| **B4** | Karar günlüğü (JSONL), kimlik maskeli | **✅** | D1-uyarlı şema; merkezî maskeleme; emir olayları maskeli. |
| **B5** | Günlük parite (canlı↔offline yeniden-koşum) | **✅** | `safety/parity.py`; anahtarlama diff = kırmızı alarm. Ayrıca F5A-2 runner↔backtest BİREBİR parite kanıtı. **F5-B:** EOD cron/scheduler'a bağlanacak. |
| **B6** | İzleme (heartbeat + EOD özet + Telegram; komut güvenliği) | **✅** | heartbeat+watchdog; EOD özet; Telegram config-gated (token'sız test); read-only vs çift-onay; 'real' komutu YOK. **F5-B:** gerçek Telegram HTTP + long-poll komut alıcısı. |
| **B7** | Faz 6 paper sayısal kabul kriterleri | **Altyapı ✅** | F5-A'da UYGULANMAZ (Faz 6 takvim işi). Altyapı hazır: tüm kill-switch'ler kuru-testli, parite kontrolü var, mutabakat var. |

---

## 3. Kuru-test sonuçları (kill-switch + kritik yollar)

- **Günlük zarar limiti** → tetik + FREEZE + CRITICAL alarm ✅
- **Ardışık N zarar** (kalıcı sayaç, restart-korumalı) → tetik ✅; kazançta sıfırlama ✅
- **Drawdown breaker** → ALARM -%25 (bildirim, freeze YOK) + FREEZE -%40 ✅
- **Veri donması / fiyat sıçraması** → tetik ✅
- **API hata oranı** (pencere + üstel backoff) → tetik + pencere-düşürme ✅
- **FREEZE çıkışı yalnız kullanıcı** → yeniden-değerlendirme kaldırmaz; `clear()` kaldırır ✅
- **Mutabakat** → "emir gönderildi/yanıt yok/çöküş" → FREEZE; adopt yalnız kullanıcı ✅
- **Parite** → offline↔canlı özdeş; bozuk-defter → kırmızı alarm ✅
- **Watchdog** → bayat heartbeat → CRITICAL (latch) ✅
- **Telegram** → yetkisiz chat reddi; çift-onay; 'real' komutu reddi (5 varyant) ✅
- **Runner↔backtest parite** → 60-günlük sentetik: anahtarlama tarihleri/aksiyonları
  BİREBİR, final equity rel=1e-9 ✅

---

## 4. Önemli mimari kararlar / dürüst çekinceler

1. **backtest=canlı aynı fonksiyon KANITLANDI.** `RegimeCoreRunner` saf fonksiyonları
   (`build_composite`/`compute_regime_signal`/`plan_enter`/`plan_exit`) çağırır;
   `run_regime_core_prod` ile anahtarlama parite testi bunu doğrular.
2. **t+1 kapanış yürütme sapması izlenen kalem.** Canlıda işlem kapanışa-yakın
   (müzayede öncesi) yürütülecek; backtest tam-kapanış fiyatı kullanır. Fark bir
   HATA değil, parite raporunda izlenen sapma kalemidir (PHASE5_PLAN #3). Parite
   kontrolü DECISION düzeyindedir (equity float farkı başarısızlık sayılmaz).
3. **AlgoLab adapter DOĞRULANMAMIŞ (oanda.py emsali).** Endpoint/alan adları F5-B'de
   resmî dokümanla doğrulanana kadar GÜVENİLİR SAYILMAZ. Parse mantığı fixture'la
   test edildi (format doğru YORUMLANIYOR, API'nin onu döndürdüğü DEĞİL). transport
   yoksa canlı çağrı bloklu.
4. **Nakit bacağı modellenmiş faiz.** Paper'da nakit `TRY_ON_RATE−200bp` ile tahakkuk
   eder (backtest'le AYNI formül) ve raporlarda AYRI "modellenmiş faiz" gösterilir.
   Gerçek enstrüman (para piyasası fonu/repo süpürme) real-öncesi kuyrukta (STATUS #19).
5. **Kill-switch eşikleri ÖNERİ.** `config/regime_core.yaml::safety` değerleri D1'e
   uyarlı muhafazakâr önerilerdir; kullanıcı/baş danışman gözden geçirmesine tabidir.
   Özellikle `daily_loss_limit_pct` D1'de pratik etkisi sınırlıdır (ENTER nadir).
6. **Takvim kütüphanesi tek otorite değil.** config otoriter; idari-izin köprüleri
   duyuruldukça `admin_leave_bridges_2026`'ya eklenmeli; uyuşmazlık loglanır.

---

## 5. F5-B kullanıcı-aksiyon listesi (canlı bağlantı öncesi)

**Kullanıcının ELLE yapacakları (değerler asla sohbete/koda yazılmaz):**
1. `cp config/secrets.env.example config/secrets.env`, değerleri doldur, `chmod 600`.
   Gerekenler: `ALGOLAB_API_KEY` (API-...), `ALGOLAB_USERNAME` (TC/müşteri no),
   `ALGOLAB_PASSWORD`, (opsiyonel) `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.
2. Faz 5 onayı geldiğinde AlgoLab **resmî API dokümanını** temin et (Bölüm 16 #1) —
   endpoint/alan adları doğrulaması için.

**F5-B'de yapılacak kod işi (ayrı onaylı tur):**
3. AlgoLab adapter endpoint/alan adlarını resmî dokümanla doğrula; `execution/algolab/`
   içine düzeltme notları ekle (CLAUDE.md 11 kuralı).
4. Canlı login akışı (`python -m execution.algolab.auth login`, SMS interaktif) +
   session yenileme sıklığı gözlemi.
5. Veri kaynağını (`LiveHistoryStore.eod_update`) AlgoLab GetCandleData / yfinance'e
   bağla + kaynaklar-arası çapraz tutarlılık canlı doğrulaması.
6. B1 kalanı: T+2 takas nakit muhasebesi, tick/lot yuvarlama, tedbir listesi kontrolü.
7. `main.py` scheduler (bar-kapanışı + grace; EOD parite işi; heartbeat; reconciliation)
   + launchd plist'leri (bot + watchdog) + gerçek Telegram HTTP/komut alıcısı.
8. **[real-öncesi kuyruk, değişmedi]** EVDS ile TRY_ON_RATE çapraz doğrulama (STATUS #18);
   D1 nakit bacağının gerçek enstrümanı (STATUS #19).

---

## 6. Değerlendirme (Claude Code — karar kullanıcının)

F5-A, paper runtime'ının tüm iskeletini offline ve fixture/kuru-testli olarak kurdu;
"backtest=canlı aynı fonksiyon" ilkesi runner↔backtest parite testiyle kanıtlandı.
Golden invariant her commit'te korundu, `mode`/eşikler ve D1 sinyal fonksiyonları
değişmedi. Canlı akışa kalan tek büyük belirsizlik AlgoLab API'sinin gerçek
davranışıdır (F5-B, resmî doküman ile). **Faz 6'ya / real'e dair hiçbir adım
atılmadı.** Bir sonraki adım (F5-B onayı / kill-switch eşik gözden geçirmesi) kullanıcının.

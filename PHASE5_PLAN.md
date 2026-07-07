# PHASE5_PLAN.md — Faz 5 (Paper) Aşama Kırılımı

**Tarih:** 2026-07-07 (Europe/Istanbul)
**Onay kaydı:** Durma Noktası 1 kullanıcı tarafından AÇILDI (2026-07-07). Kapsam
**yalnızca paper**. Durma Noktası 2 (paper→real) AYNEN kapalı — "real'e geç" yolu
kod/komut olarak **hiçbir zaman var olmayacak** (HARDENING B6, STATUS KALICI KAYIT 9).

**Bağlayıcı spec:** HARDENING.md Bölüm B (B1–B7) + CLAUDE.md Bölüm 14, birlikte
okunur. Çelişkide CLAUDE.md + kullanıcı kararı kazanır.

**Koşulan aile:** `regime_core` (D1, KALICI KAYIT 6/8). 10-gate ailesi (`ten_gate`)
DONMUŞ referans olarak kalır, paper'da **koşulmaz**.

**DEĞİŞMEZLER (her aşamada geçerli):**
- `config/config.yaml` içindeki `mode: paper` ve tüm eşikler DEĞİŞMEZ.
- `v7.1-golden` her commit'te bayt-bayt korunur (`tests/test_golden_bist.py`).
- D1 üretim sinyal/boyutlama fonksiyonları (`strategy/regime_core.py`) DEĞİŞMEZ.
  Canlı döngü bu SAF fonksiyonları **çağırır**, kopyalamaz (backtest=canlı).
- Faz 6'ya / real'e dair hiçbir adım yok.

---

## F5-A ↔ F5-B sınırı

**F5-A (bu tur):** AlgoLab'a **canlı bağlantı YOK**. Kimlik bilgisi gerektiren her
şey F5-B'ye. Tüm modüller offline, fixture-testli, kuru-testli. Amaç: paper
runtime'ının tüm iskeletini (veri deposu, PaperBroker, mutabakat, kill-switch,
karar günlüğü, parite, izleme, AlgoLab adapter iskeleti, takvim) kurmak ve
kanıtlamak — canlı akışa sadece kimlik bilgisi + tek "kaynak bağlama" adımı kalsın.

**F5-B (sonraki onaylı tur):** AlgoLab canlı login (SMS akışı), canlı veri
kaynağının (AlgoLab GetCandleData / yfinance) veri deposuna bağlanması, gerçek
throttle'lı HTTP, ilk canlı seans, session yenileme gözlemi. F5-A'nın ürettiği
"F5-B kullanıcı-aksiyon listesi" (PHASE5A_REVIEW.md) buranın girdisidir.

---

## Aşama tablosu

| Aşama | Ad | Teslimat | Test/kuru-test kanıtı | HARDENING |
|---|---|---|---|---|
| F5A-0 | Plan + kayıt | PHASE5_PLAN.md, STATUS KALICI KAYIT 9 | doküman + golden yeşil | — |
| F5A-1 | Canlı veri deposu | `data/live_store.py` (kalıcı günlük tarihçe, bootstrap + EOD güncelleme arayüzü + çapraz-tutarlılık) | fixture testleri; 200+ gün MA(200) beslenebiliyor | B1/B5 girdisi |
| F5A-2 | PaperBroker (regime_core) | `execution/broker_adapter.py` (ABC), `execution/paper_broker.py`, `execution/regime_core_runner.py` (t+1 KAPANIŞ yürütme + basket enter/exit; cash accrual) | deterministik fiyat dizisi; full-lot/artık nakit/komisyon/faiz; restart state kurtarma | B1 |
| F5A-3 | Mutabakat + durum kurtarma | `safety/reconciliation.py` | broker↔yerel diff→FREEZE; "emir gönderildi, yanıt yok, çöküş" mock testi | B2 |
| F5A-4 | Kill-switch hiyerarşisi | `safety/kill_switch.py` (breaker bağla + günlük zarar + veri-donması + API-hata + ardışık-N-zarar) | her switch kuru-test; FREEZE çıkışı yalnız kullanıcı | B3 |
| F5A-5 | Karar günlüğü (JSONL) | `journal/decision_journal.py` (D1 şema, maskeleme) | şema testi; kimlik maskeleme testi | B4 |
| F5A-6 | Parite kontrolü | `safety/parity.py` (EOD offline yeniden-koşum ↔ canlı karar diff) | eşleşme + kasıtlı sapma→alarm testi | B5 |
| F5A-7 | İzleme + Telegram iskeleti | `notify/telegram_bot.py` (config-gated, token'sız fixture-test), `safety/watchdog.py`, EOD özet | heartbeat testi; read-only vs çift-onay; 'real' komutu YOK testi | B6 |
| F5A-8 | AlgoLab adapter iskeleti | `execution/algolab/{auth,client,adapter}.py` (dokümante API'ye karşı, CANLI ÇAĞRI YOK), `config/secrets.env.example` | fixture/mock testleri; maskeleme; canlı çağrı YOK asserti | B1/B2 |
| F5A-9 | Seans/takvim gerçeği | `config/bist_calendar.yaml` (2026 seans saatleri + tatiller), `core/clock.py` config'ten okur; yarım-gün + veri-yok toleransı | takvim testleri; veri-yok günü zarafetle atlanır | B1 |
| F5A-Z | Kapanış | PHASE5A_REVIEW.md, STATUS güncelleme, tam süit + golden, push | tüm testler yeşil + golden bayt-bayt | B7 hazırlık |

**Her aşama sonunda:** commit + golden kanıtı (`pytest tests/test_golden_bist.py -q`)
+ push + STATUS güncelleme. Oturum kesilirse bir sonraki oturum STATUS'tan kaldığı
aşamadan devam eder.

---

## Mimari kararlar (bu turda sabitlenen)

1. **regime_core canlı akışı = SAF fonksiyon çağrısı.** Canlı/paper döngü
   `strategy/regime_core.py`'nin `build_composite` / `compute_regime_signal` /
   `plan_enter` / `plan_exit` / `mark_to_market` fonksiyonlarını doğrudan çağırır.
   `run_regime_core_prod` backtest sürücüsüdür; canlı runner aynı adımları
   gün-gün, kalıcı state ile yürütür (aynı fonksiyonlar → parite garanti, B5).

2. **BrokerAdapter sözleşmesi (CLAUDE.md 4.3) korunur + genişletilir.** regime_core
   bracket kullanmaz (per-sembol stop/target yok; "stop" = rejim çıkışı). ABC'ye
   `submit_market_order(symbol, side, quantity)` **eklenir** (additive, geriye
   uyumlu). `submit_bracket_order` 10-gate için kalır. regime_core basket
   enter/exit'i market emirleriyle yürütür.

3. **t+1 KAPANIŞ yürütme politikasının canlı karşılığı (B1).** Backtest: sinyal t
   kapanışı → işlem t+1 KAPANIŞ fiyatı. Canlı: t günü seans kapanışından sonra
   (grace) sinyal hesaplanır; işlem **t+1 seans kapanışına yakın** (müzayede
   penceresinden ÖNCE, sürekli seansın son dakikaları) yürütülür. Müzayede
   pencerelerinde emir YOK. Kapanışa-yakın yürütme fiyatı ile backtest'in tam-
   kapanış fiyatı arasındaki fark **parite raporunda izlenen bir sapma kalemidir**
   (hata değil, modellenmiş beklenen fark).

4. **Nakit bacağı paper'da tahakkuk (KALICI KAYIT 6, madde 19).** Rejim KAPALI
   günlerde nakit `TRY_ON_RATE − 200bp` ile (ACT/365, backtest'le AYNI model)
   tahakkuk eder ve raporlarda **"modellenmiş faiz"** olarak AYRI gösterilir.
   Gerçek enstrüman kararı (para piyasası fonu/repo süpürme) real-öncesi kuyrukta.

5. **Kaynaklar arası çapraz tutarlılık (F5A-1).** Veri deposu birden fazla kaynağı
   (snapshot bootstrap, F5-B'de AlgoLab + yfinance) destekler; aynı sembol-gün için
   kaynaklar arası fiyat farkı eşiği aşarsa WARN + o gün "şüpheli" işaretlenir.

6. **Kimlik bilgisi maskeleme (her yerde).** Karar günlüğü, event log, Telegram,
   AlgoLab adapter — API key / hash / TC no / şifre HİÇBİR çıktıya düz metin
   yazılmaz; merkezî `mask_secret()` yardımcısı.

---

## B1–B7 kapsam haritası (F5-A'da nereye düşüyor)

- **B1** (mikro-yapı): F5A-2 (müzayede/yürütme politikası) + F5A-9 (seans/takvim).
  T+2 takas, tick/lot yuvarlama, tedbir listesi → tasarımda not, canlı doğrulama F5-B.
- **B2** (mutabakat + kurtarma): F5A-3 tam.
- **B3** (kill-switch): F5A-4 tam (breaker F5A-2'de bağlanır).
- **B4** (karar günlüğü): F5A-5 tam.
- **B5** (parite): F5A-6 tam.
- **B6** (izleme): F5A-7 tam.
- **B7** (paper sayısal kabul): F5-A'da UYGULANMAZ — Faz 6 takvim işi. F5-A yalnızca
  altyapıyı ("tüm kill-switch'ler kuru-testle doğrulandı" vb.) hazırlar.

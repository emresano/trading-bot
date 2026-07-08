# PHASE5B2A_REVIEW — Telegram Canlı Bildirim + Operasyon

**Tarih:** 2026-07-08 (Europe/Istanbul)
**Kapsam:** F5-B2a — F5-B2'nin **bildirim yarısı**. `ManualExecutionAdapter` TASARIMI bu
turda YOKTUR (F5-B2'ye kalır). Gelen Telegram komutu / long-poll YOKTUR. `mode: paper`,
mühürlü parametreler/eşikler, `strategy/regime_core.py`, `data/snapshots/` DEĞİŞMEDİ.
Golden 3/3 bayt-bayt her commit. Faz 6 / real / launchd etkinleştirme adımı YOK.

---

## Madde tablosu

| # | Madde | Teslimat | Kanıt |
|---|---|---|---|
| 1 | Telegram gerçek HTTP gönderim | `make_http_sender` + `TelegramNotifier` HTTP yolu | 7 test (mock HTTP) |
| 2 | Alarm+özet kablolama | (mevcut) `_alarm→send`; kuru-test eklendi | 2 test (mock FREEZE+DATA_DRIFT) |
| 3 | launchd saat doğrulaması | plist yorum düzeltme + OPERATOR_GUIDE §2a | — (doküman) |
| 4 | Rapor düzeltmesi | "bayat=muhafazakâr" genelleme düzeltildi | — (doküman) |
| 5 | EVDS CSV kıyası (koşullu) | GERÇEK CSV koşuldu + value_col fix | 1 test + rapor |
| 6 | Kapanış | bu dosya + STATUS + push | 494 passed |

---

## 1 — Telegram gerçek Bot API sendMessage
`notify/telegram_bot.py`:
- **`make_http_sender(token, chat_id, ...)`**: Bot API `sendMessage` POST. **timeout + 3 deneme
  + üstel bekleme** (`base_backoff × 2^attempt`). Kalıcı başarısızlıkta son istisnayı yükseltir.
  `poster`/`sleep` enjekte edilebilir → testte gerçek HTTP/uyku YOK.
- **`TelegramNotifier`**: `sender` enjekte edilmediyse + `enabled` + token(env) + `chat_id` varsa
  gerçek HTTP göndericisini kurar. **Token YOKSA log-only davranış AYNEN korunur** (`enabled`
  zaten `telegram.enabled AND token_present`). Gönderim hatası çağırana **YANSIMAZ**: yakalanır,
  `logger` varsa WARN düşer, `send` False döner → **günlük döngü ASLA bildirim yüzünden kırılmaz.**
- Maskeleme mevcut merkezî katmandan (`journal.masking`); giden metin daima maskeli.
- main.py + watchdog `logger` bağlandı.
- **Gerçek test mesajı:** her iki `secrets.env`'de `TELEGRAM_TOKEN` BOŞ → gerçek gönderim
  atlandı (token temin edilince operatör bir test mesajı görebilir; kanıt maskeli olur).

## 2 — Alarm + EOD kablolama
Kablolama F5-B1/B1.1'de zaten mevcuttu (tüm kill-switch ALARM/FREEZE, DATA_DRIFT,
DELAYED_SIGNAL, watchdog bayat-heartbeat → `_alarm`/`notifier.send`; EOD özeti faiz+kaynak
tarihi+bayatlık satırı ile — K1). Bu tur **kanıt** ekledi: mock FREEZE + mock DATA_DRIFT
alarmları enjekte Telegram göndericisine ulaşır + journal alarm kaydı düşer; EOD gönderilir.

## 3 — launchd saat doğrulaması (K5 grace uyumu)
paper plist **19:30 Istanbul** koşar. Kapanış 18:00 + `bar_close_grace_sec`=3600s = **19:00
bar final**; 19:30 → 19:05 alt-sınırına **25 dk marj**. Türkiye kalıcı **UTC+3 (DST yok)** →
yıl boyu sabit güvenli. Plist yorumundaki hatalı "~1.5s grace" düzeltildi. OPERATOR_GUIDE §2a:
beklenen günlük zaman çizelgesi + 'bar yok' → veri-tamlığı ertelemesi (K6) + K3 catch-up +
**koşu-içi yfinance retry YOKTUR** (transient hata sonraki günlük koşu + catch-up ile telafi).

## 4 — "bayatlık = muhafazakâr" genellemesi düzeltildi
Bayat oran = ESKİ oranla tahakkuk; sapmanın **yönü faiz patikasına bağlıdır**. Faiz
YÜKSELİŞ döngüsünde (2023 boşluğu) eski oran düşük → eksik tahakkuk = muhafazakâr. Faiz
DÜŞÜŞ döngüsünde eski (yüksek) oran → nakit getirisini **ABARTIR = agresif**. PHASE5B11_REVIEW
K1 + çekince #1 + STATUS #18 düzeltildi. **Kod değişikliği YOK.**

## 5 — GERÇEK EVDS CSV kıyası koşuldu
`runtime/manual/evds_export.csv` (seri **TP_BISTTLREF_ORAN** = TLREF, 1860 satır) MEVCUTTU →
koşuldu. **Snapshot DEĞİŞMEDİ.**
- **Genel fark:** EVDS sistematik **~2-6 puan YÜKSEK** (ort. 2.13, max 6.00 @ 2020-10) — yön
  hep aynı → **seri-TANIM farkı** (secured TLREF vs OECD interbank call money). İkame basit değil.
- **2023 boşluğu:** baseline'da 9 ay NaN; **EVDS'de 12/12 DOLU**. Fark dramatik (2023-11
  baseline ff 23.5 vs EVDS 41.45) → yükseliş döngüsünde ff'in gerçeğin altında kaldığını
  doğrular (m4 ile tutarlı).
- **2022-10 %9.0 anomalisi:** baseline 10.5→**9.0**→7.5 dip'i EVDS'de (11.38→11.46→10.04) YOK
  → baseline serisinin tanımsal/veri artefaktı olduğu teyit edildi.
- **Araç kusuru düzeltildi:** otomatik `value_col` seçimi sondaki boş `Unnamed: 2` kolonunu
  alıp **sessizce 0 satır** okuyordu → sayısal-değeri olan son kolon seçilir (+1 test). Operatör
  artık `--value-col` vermek zorunda değil.
- **Karar:** tanım-uyumlu seriye geçiş + S1b yeniden ölçümü **ayrı onaylı tur** ister; kuyruk
  #18 açık kalır (artık "veri yok" değil, "tanım-uyumlu seri + yeniden ölçüm" bekliyor).

---

## Değişmezler doğrulaması
- `config/config.yaml` `mode: paper` — DOKUNULMADI.
- Mühürlü N/b/M + eşikler, `strategy/regime_core.py`, `data/snapshots/` — DEĞİŞMEDİ.
- v7.1-golden **3/3 bayt-bayt** (her commit + tam süit içinde).
- Gelen Telegram komutu / long-poll implement EDİLMEDİ; 'real' komutu hiçbir biçimde YOK.
- Faz 6 başlatılmadı; `go_live_date` = null; launchd etkinleştirilmedi; Durma Noktası 2 kapalı.

## Test durumu
Tam süit: **494 passed** (F5-B1.1 485 + 9 yeni: m1 6, m2 2, m5 1). Golden 3/3.

## Değerlendirme (Claude Code — karar kullanıcının/baş danışmanın)
Bildirim katmanı artık token verildiğinde canlı çalışır ve mimarinin en kritik güvencesini
korur: **bir bildirim hatası günlük döngüyü asla kıramaz.** EVDS kıyası, mevcut faiz serisinin
iki bilinen zayıflığını (2023 boşluğu + 2022-10 artefaktı) nicel olarak ortaya koydu ve bunların
bir **seri-tanım farkı** olduğunu gösterdi — bu, gelecekteki düzeltme turunun kapsamını netleştirir
ama bu turda hiçbir ölçüm/parametre değiştirilmedi. F5-B2 (ManualExecutionAdapter + gelen komut
alıcısı) ve go-live kararı ayrı, onaylı adımlardır.

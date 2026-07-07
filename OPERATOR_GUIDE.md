# OPERATÖR KILAVUZU — Gölge Paper Bot (Faz 5, F5-B1)

**Kapsam:** BIST regime_core (D1) gölge paper döngüsünü Mac Mini'de `launchd` ile
işletmek. **Sadece PAPER.** Gerçek para yolu kod/komut olarak YOKTUR (Durma Noktası 2).

**Gölge mod ne demek:** AlgoLab (broker) 2025-12-31'de kapatıldı. Bu döngü EOD
stratejide broker'a muhtaç değildir: veri **yfinance** günlük kapanışlarından gelir,
emirler dahili **PaperBroker** simülatöründe dolar. Canlı emir iletimi YOKTUR.

---

## 0. Tek seferlik kurulum

```bash
cd /Users/sano/trading-bot
# 1) (opsiyonel) secrets — Telegram bildirimi istiyorsan:
cp config/secrets.env.example config/secrets.env    # TELEGRAM_TOKEN + TELEGRAM_CHAT_ID doldur
chmod 600 config/secrets.env
# 2) Canlı depoyu snapshot'tan bootstrap et (bir kez; ~20 yıl günlük tarihçe):
.venv/bin/python main.py --config config/regime_core.yaml --bootstrap
# 3) İlk veri çekimi + gözlem döngüsü (elle doğrulama):
.venv/bin/python main.py --config config/regime_core.yaml --refresh --cycle
```

Beklenen: bootstrap 12 sembolü doldurur; `--refresh` bugüne kadar eksik günleri
yfinance'ten çeker; `--cycle` **observe** modda (aşağı bkz.) bir gün değerlendirir —
işlem AÇMAZ, sinyali `runtime/paper/decision_journal.jsonl`'a yazar.

---

## 1. observe → active (Faz 6 resmi başlangıcı = AYRI karar)

- **observe** (varsayılan, `paper.go_live_date: null`): bot her gün rejim/kompoziti
  hesaplar, `signal_eval` günlüğü + heartbeat + EOD özet üretir; **paper hesabı
  başlatmaz, işlem açmaz.** Faz 6 ölçümü BAŞLAMIŞ SAYILMAZ.
- **active**: yalnızca döngü birkaç gün stabil koştuktan sonra, **operatör kararıyla**.
  `config/regime_core.yaml` içinde:
  ```yaml
  paper:
    go_live_date: "2026-07-10"   # son tamamlanmış işlem günü (YYYY-MM-DD)
  ```
  O gün rejim **AÇIK**sa: bir sonraki işlem günü kapanışında **INITIAL_ENTER**
  (mevcut rejim benimsenir, t+1 yürütme). **KAPALI**sa: nakitte beklenir + modellenmiş
  faiz tahakkuku başlar. Bu bir kez olur; sonrası normal rejim anahtarlamalarıdır.

> Faz 6'nın resmi ölçüm penceresini başlatmak `go_live_date` set etmekle eşdeğerdir —
> bu, döngünün stabilliğini gözlemledikten sonra senin bilinçli kararındır.

---

## 2. Günlük servis (launchd)

```bash
# Başlat:
cp deploy/com.tradingbot.paper.plist     ~/Library/LaunchAgents/
cp deploy/com.tradingbot.watchdog.plist  ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tradingbot.paper.plist
launchctl load ~/Library/LaunchAgents/com.tradingbot.watchdog.plist
# Durdur:
launchctl unload ~/Library/LaunchAgents/com.tradingbot.paper.plist
# Durum bak:
launchctl list | grep tradingbot
```

- **paper servisi**: her iş günü 19:30 yerel saatte (kapanış 18:00 + grace) `--refresh
  --cycle` koşar. Tatil/hafta sonu bot içeride `bist_calendar` ile atlar.
- **watchdog servisi**: her 15 dk heartbeat yaşını kontrol eder; bayatsa (>15 dk yerine
  config `heartbeat_stale_sec`) Telegram CRITICAL. Bottan bağımsızdır.
- **Log rotasyonu**: `deploy/tradingbot.newsyslog.conf` → `/etc/newsyslog.d/`.

> Mac saati **Istanbul** varsayılıyor. Farklıysa plist'teki `Hour` alanını ayarla.

---

## 3. Günlük ne beklemeli / nereye bakmalı

| Ne | Nerede |
|---|---|
| Karar günlüğü (sinyal/işlem/alarm, JSONL, maskeli) | `runtime/paper/decision_journal.jsonl` |
| stdout/stderr (servis logları) | `runtime/paper/logs/paper.*.log` |
| Son çalışma zamanı (heartbeat) | `runtime/paper/heartbeat` |
| Aktif FREEZE dosyaları | `runtime/paper/freeze/` |
| Scheduler durumu (equity, faiz) | `runtime/paper/scheduler_state.json` |

**Normal bir observe günü:** `signal_eval` satırı (regime_on true/false), heartbeat
tazelenir, işlem yok. **Normal bir active günü:** çoğu gün `HOLD_POSITION`/`HOLD_CASH`;
rejim anahtarlaması nadir (yılda ~3-4). Telegram varsa EOD özeti gelir.

---

## 4. FREEZE (yeni ENTER durur) — nasıl temizlenir

FREEZE dosyaları `runtime/paper/freeze/` altında oluşur (drawdown breaker, günlük zarar,
ardışık-N zarar, veri anomalisi, API hatası). **Otomatik reset YOKTUR** — yalnız sen
temizlersin, sebebi inceledikten sonra:

```bash
ls runtime/paper/freeze/                 # hangi switch tetiklendi
cat runtime/paper/freeze/BREAKER         # sebep/detay
rm runtime/paper/freeze/<SWITCH_ADI>     # incelendikten SONRA elle temizle
```

- **BREAKER (drawdown -%40)**: en ciddi; equity tepeden %40 düştü. İncele, gerekçesiz
  değilse bekle.
- **CONSEC_LOSS**: 4 ardışık zararlı round-trip. Temizlerken sayaç sıfırlanır.
- Çıkışlar (pozisyon kapatma) FREEZE'den ETKİLENMEZ — her zaman serbesttir.

---

## 5. Telegram komutları (token varsa)

Yalnız izinli `chat_id`'den kabul edilir. `/status`, `/report` (read-only);
`/pause CONFIRM`, `/resume CONFIRM`, `/kill CONFIRM` (çift onay). **'real'/gerçek-para
komutu YOKTUR** — router açıkça reddeder.

> F5-B1'de Telegram **giden** bildirim iskeleti hazırdır; gerçek HTTP gönderim +
> gelen-komut long-poll alıcısı bir sonraki turda bağlanır (token'sız log-only çalışır).

---

## 6. Sorun giderme

- **"bar yok" logu:** yfinance gün barı gecikmiş/tatil → bot o günü zarafetle atlar;
  ertesi gün toparlar. Endişe yok (ardışık 2 gün+ ise `DATA_ANOMALY` FREEZE devreye girer).
- **Watchdog CRITICAL "bot sessiz":** paper servisi koşmuyor/asılmış → `launchctl list`,
  `runtime/paper/logs/paper.err.log`.
- **Parite KIRMIZI ALARM:** temiz yeniden-koşum canlı günlükten ayrıştı (veri/state
  kayması) → `decision_journal.jsonl`'da `PARITY` alarmı; state'i inceleyip gerekiyorsa
  baş danışmana danış. Otomatik düzeltme yapılmaz.

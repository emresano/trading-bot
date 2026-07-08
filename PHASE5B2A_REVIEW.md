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

---

## B2a.1 Eki — Telegram Teşhis + Sessiz Düşüş Sertleştirme (2026-07-08)

**Tetikleyici:** F5-B2a'da "token verilince gerçek gönderim çalışır" öngörülmüştü; kullanıcı
bu turdan önce gerçek TELEGRAM_TOKEN + TELEGRAM_CHAT_ID'yi girip curl ile başarılı test
mesajı gönderebildiğini bildirdi — ama koşan bot kodu bunları BOŞ görmeye devam etti.

### 1 — Teşhis
Repodaki/launchd'nin kullandığı secrets dosyaları taranarak karşılaştırıldı:
- `config/secrets.env` — kodun **tek** okuduğu dosya (hard-code: `main.py:547`
  `_load_secrets()`, `safety/heartbeat.py:79` `_watchdog_main()`, `tools/evds_compare.py:161`,
  `core/config.py:257` `load_secrets()`). Anahtar adları: `ALGOLAB_API_KEY/USERNAME/PASSWORD`,
  `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `EVDS_API_KEY`.
- `./secrets.env` (repo kökü) — **hiçbir kod yolu bu dosyayı okumaz.** Kullanıcının gerçek
  değerleri buraya yazılmıştı.
- Anahtar ADLARI iki dosyada da BİREBİR aynıydı (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`) —
  uyuşmazlık isim farkı DEĞİL, **konum** farkıydı. OPERATOR_GUIDE zaten doğru yolu
  (`config/secrets.env`) belirtiyordu; kılavuz↔kod arasında ad tutarsızlığı yoktu.
- Format kontrolleri (tırnak, `=` etrafı boşluk, CRLF, BOM, `export` öneki, dosya izinleri):
  hepsi temiz — kök dizindeki dosya `python-dotenv` ile sorunsuz parse ediliyordu, sadece
  yanlış dosyaydı.
- Bu desen **turun ilerleyişinde 3 kez tekrarlandı**: kullanıcı iki ayrı BotFather
  güncellemesinde de (token rotasyonu sonrası) yine kök dizine yazdı — tek seferlik yanlış
  anlama değil, kalıcı bir alışkanlık deseni olarak değerlendirilip OPERATOR_GUIDE §0'a
  açık, öne çıkan bir uyarı eklendi ("doldurulacak dosya BUDUR — repo kökünde bir
  secrets.env DEĞİL").
- Ayrıca bağımsız bir ikinci kusur bulundu: token değerinin İÇİNDE (uçlarda değil, ortada)
  **gömülü bir boşluk karakteri** vardı — bu **iki ayrı BotFather-kaynaklı değerde de aynı
  şekilde** görüldü, muhtemelen BotFather'ın sohbet balonunda satır-kaydırdığı metni
  kopyalarken oluşan bir artefakt. Telegram Bot API bu durumda `404 Not Found` (bozuk
  URL/token biçimi) döndürüyordu; boşluk temizlenince `401 Unauthorized`'a (token biçimi
  doğru ama Telegram tarafından tanınmıyor) geçti — bu, URL-biçimlendirme sorununun
  gerçekten çözüldüğünü, kalan sorunun token'ın kendisi olduğunu doğruladı.

### 2 — Düzeltme
Konum farkı olduğu için (isim farkı değil): kullanıcının kök dizindeki `secrets.env`
değerleri `config/secrets.env`'e **taşındı** (anahtar adları değişmedi, yalnız `TELEGRAM_TOKEN`/
`TELEGRAM_CHAT_ID` satırları güncellendi), kök dosya silindi, `chmod 600` uygulandı. Bu
işlem 3 kez tekrarlandı (her yeni token için) — hepsi programatik bir script ile (dosyadan
dosyaya, değer hiçbir ara adımda `print`/`echo` edilmeden) yapıldı. Gömülü boşluk da aynı
şekilde programatik temizlendi (uzunluk/karakter-sınıfı raporlanır, değerin kendisi asla).

### 3 — `--test-telegram` komutu
`main.py::_cmd_test_telegram` + `--test-telegram` bayrağı: config yükler, `notify.
telegram_bot.notifier_status(enabled_cfg, token_present, chat_id)` ile durumu hesaplar
(`ACTIVE` / `LOG-ONLY (neden)`), yazdırır; **ACTİF**se maskeli bir test mesajı gönderir
(gerçek gönderim sonucu BAŞARILI/BAŞARISIZ + exit code 0/1). `notifier` parametresi test
için enjekte edilebilir (gerçek HTTP YOK). OPERATOR_GUIDE §5a.

### 4 — Sessiz düşüş sertleştirme
Kök sorunun bir benzerinin **fark edilmeden** tekrarlanmasını önlemek için:
`notify/telegram_bot.py::notifier_status()` tek doğruluk kaynağı; `PaperScheduler.__init__`
bunu hesaplar (`self.telegram_status`) ve `telegram.enabled=true` iken çalışma-durumu
`LOG-ONLY` ise **başlangıçta belirgin WARN** journal'a düşer. `notify/eod_summary.py::
build_eod_summary` yeni `telegram_status` parametresiyle her özete kalıcı bir satır ekler:
`TELEGRAM: ACTIVE` veya `TELEGRAM: LOG-ONLY (<neden>)`. Aynı durum `heartbeat_status.json`'a
da (`telegram: {state, reason}`) her döngüde yazılır. 13 yeni test: `notifier_status` 5
senaryo, EOD satırı 2 senaryo, scheduler silent-drop + active-no-warn 2 senaryo,
`--test-telegram` CLI 4 senaryo (LOG-ONLY/disabled/ACTIVE/gönderim-hatası).

### 5 — Secrets hijyeni (STATUS #9 kapanışı)
`.gitignore`'a genel desen eklendi: `secrets.env`, `*.env`, `runtime/manual/`
(`config/secrets.env.example` açık istisna). Kanıt: `git log --all -- secrets.env` ve
`git log --all -- config/secrets.env` **boş** (hiçbir commit'te hiçbir zaman yer almadı);
`git log --all --diff-filter=A --name-only` taramasında yalnız `config/secrets.env.example`
bulundu. `git status` çalışma ağacında secrets dosyası bırakmıyor.

### 6 — Gerçek uçtan-uca test
`--test-telegram` çalıştırıldı: `TELEGRAM durumu: ACTIVE (token+chat_id mevcut)` →
`gönderim sonucu: BAŞARILI`. **Kullanıcı telefonunda mesajı doğruladı.** Ardından gerçek
bir manuel döngü koşuldu (`--refresh --cycle`, observe mod, 2026-07-08): EOD özeti
gönderildi, `heartbeat_status.json` → `"telegram": {"state": "ACTIVE", "reason":
"token+chat_id mevcut"}`, journal'da gönderim-hatası WARN'ı yok (maskeli kanıt — token/
chat_id DEĞERİ hiçbir çıktıya yazılmadı). **Yan gözlem (kapsam DIŞI):** aynı cycle'da
ASELS 2026-07-07 için 3 bar sapması nedeniyle mevcut K4 mekanizması bir `DATA_DRIFT`
(CRITICAL) alarmı üretti ve bu da Telegram'a gitti (K4 önceden var olan, bu turda
değiştirilmeyen davranış) — sinyal bu yüzden finalize edilmedi (observe modda zaten
işlem yok, etkisi yok). Operatör isterse OPERATOR_GUIDE §7 `--resync` uygulayabilir; bu
turun kapsamında aksiyon alınmadı.

### Güvenlik olayı — dürüst kayıt
Teşhis sürecinde bir komut (`xxd` ile ham dosya kontrolü) **yanlışlıkla gerçek token
değerini bu oturumun çıktısına yazdırdı** — bu turun "değer hiçbir çıktıya yazılmaz"
kuralının ihlaliydi. Fark edilir edilmez kullanıcıya hemen bildirildi. Kullanıcı,
token'ın bu oturumda bir kez göründüğünü göz önünde bulundurarak **BotFather'da token'ı
iptal edip yeniledi** (kendi kararıyla — iki seçenek sunuldu, "revoke+regenerate" seçildi).
Bu olaydan sonraki tüm teşhis adımları yalnızca **yapısal/maskeli** kontrollerle yapıldı
(uzunluk, karakter sınıfı/pozisyonu, HTTP durum kodu + hata açıklaması — bunların hiçbiri
secret değer içermez); değerin kendisi bir daha hiçbir çıktıya yazılmadı.

### Değişmezler doğrulaması (B2a.1)
- `config/config.yaml` `mode: paper` — DOKUNULMADI.
- Mühürlü N/b/M + eşikler, `strategy/regime_core.py`, `data/snapshots/` — DEĞİŞMEDİ.
- v7.1-golden **3/3 bayt-bayt** (her commit).
- Faz 6 başlatılmadı; `go_live_date` = null; launchd etkinleştirilmedi; Durma Noktası 2 kapalı.
- Gelen Telegram komutu/long-poll implement EDİLMEDİ; 'real' komutu YOK.

### Test durumu
Tam süit: **507 passed** (F5-B2a 494 + 13 yeni: notifier_status 5, EOD satırı 2, scheduler
silent-drop 2, CLI 4). Golden 3/3.

### Değerlendirme (Claude Code — karar kullanıcının/baş danışmanın)
Kök sorun bir kod hatası değil bir **operasyonel konum hatası** idi (yanlış dosya) — ama
3 kez tekrarlanması, bunun tek seferlik bir yanlış anlama değil kalıcı bir alışkanlık
riski olduğunu gösterdi; OPERATOR_GUIDE + `--test-telegram` + sessiz-düşüş sertleştirmesi
bunu artık **görünür** kılıyor (bir daha sessizce tekrarlanamaz). Güvenlik olayı (yanlışlıkla
token yazdırma) ciddiye alınıp hemen düzeltildi; kullanıcının token rotasyon kararı doğru
bir tedbirdi. F5-B2 (ManualExecutionAdapter + gelen komut alıcısı) ve go-live kararı ayrı,
onaylı adımlardır.

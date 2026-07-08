# PHASE5B11_REVIEW.md — Faz 5 / F5-B1.1 (Gölge Sertleştirme) Kapanış Raporu

**Tarih:** 2026-07-08 (Europe/Istanbul)
**Kapsam:** F5-B1.1 — gölge paper döngüsünün K1 kapanış/sertleştirme turu. 9 sertleştirme
maddesi + kapanış. **Faz 6 BAŞLATILMADI; go_live_date=null; real'e adım YOK; launchd
etkinleştirilmedi.**

**DEĞİŞMEZLER korundu:** `config/config.yaml` `mode: paper` DOKUNULMADI; mühürlü strateji
parametreleri (N=200, b=%1, M=3) ve kabul eşikleri DEĞİŞMEDİ; `strategy/regime_core.py` D1
üretim fonksiyonları DEĞİŞMEDİ; `data/snapshots/` DEĞİŞMEDİ; **v7.1-golden her commit'te
3/3 bayt-bayt** kanıtlandı.

---

## 1. Madde tablosu

| # | Madde | Teslimat | Commit türü | Kanıt |
|---|-------|----------|-------------|-------|
| K1 | TRY_ON_RATE canlı ileri besleme | `data/cash_rate_feed.py` + main entegrasyon | feat | 5 test + gerçek FRED + EOD faiz satırı |
| K2 | Kill-switch mutabakat tablosu | ölçüm + config/kill_switch senkron + `KILLSWITCH_RECONCILIATION.md` | feat | prod backtest ölçümü + 9 kuru-test |
| K3 | Catch-up + gecikmiş sinyal | main.py DELAYED_SIGNAL tespiti | feat | 2 test (gaplı/gapsız) |
| K4 | Veri kayması + resync | `detect_drift`/`resync`/`replace_bars` + guide | feat | sentetik temettü uçtan uca test |
| K5 | Provisional-bar regresyonu | 3 test (iki yön + active erteleme) | test | grace=3600s gerekçesi |
| K6 | INITIAL_ENTER maliyet mutabakatı | veri-tamlığı yürütme kapısı | fix | aritmetik bit-bit + 2 test |
| K7 | Bakım penceresi | OPERATOR_GUIDE §8 + dokunulmaz modül listesi | docs | — |
| K8 | evds_compare --csv | CSV girdi modu + kolon eşleme | feat | 3 test |
| K9 | B7_D1_PROPOSAL revizyonu | iki katmanlı karne (mekanik + olay) | docs | — |

Tam süit: **485 passed** (F5-B1 470 + F5-B1.1 15: cash_rate 5 + evds 3 + scheduler +7),
golden 3/3 her commit.

---

## 2. Kanıtlar ve önemli bulgular

### K1 — faiz ileri besleme
- `CashRateFeed`: snapshot READ-ONLY + canlı uzantı (SQLite). Bayatlık > 35g → FRED
  (IRSTCI01TRM156N); çekim başarısız/boşsa son değer + WARN (tahakkuk durmaz). Formül/
  haircut backtest ile AYNI. EOD özet + `heartbeat_status.json`'a faiz+kaynak tarihi+bayatlık.
- **GERÇEK DURUM:** FRED/OECD serisi de 2026-03'te bitiyor (~4 ay gecikme) → canlı faiz
  **tasarım gereği bayat** kalır (35.5%, ⚠️BAYAT). Zamanlı TCMB için EVDS (kuyruk #18).
- **DÜZELTME (F5-B2a m4):** "bayatlık = muhafazakâr" bir GENELLEME DEĞİLDİR; sapmanın YÖNÜ
  faiz patikasına bağlıdır. Bayat oran = ESKİ oranla tahakkuk. **Faiz YÜKSELİŞ döngüsünde**
  (2023 boşluğu) eski oran güncelden düşüktür → tahakkuku EKSİK gösterir = muhafazakâr.
  **Faiz DÜŞÜŞ döngüsünde** eski (yüksek) oran güncelden yüksektir → nakit getirisini
  ABARTIR = muhafazakâr DEĞİL (agresif). Şu anki gecikme, faiz düşerse aleyhe çalışır.
- **Bug düzeltildi:** FRED index `.values` tz'yi siliyordu → `since` karşılaştırması
  TypeError → hep fetch_failed. tz-aware DatetimeIndex korunarak düzeltildi.

### K2 — kill-switch mutabakatı (ölçümlü)
Prod backtest tam dönem (5510 gün, 33 round-trip): en kötü tek gün **−11.60%** (2013-06-03);
max ardışık kaybeden round-trip **5**; max DD **−28.43%**.
- `consecutive_losses_freeze`: 4 → **7** (tarihsel maks 5 + 2 → tarihsel tetik 0).
- `daily_loss_limit_pct`: 0.08 → **0.12** (worst −11.6% altı, 0.40pt marj → tetik 0).
- Drawdown breaker −25/−40 doğrulandı (max DD −28.43 → FREEZE 0, ALARM 4).
- 5-switch tablo + kuru-test kanıtı: `KILLSWITCH_RECONCILIATION.md`.

### K3 — catch-up + gecikmiş sinyal
Downtime'da process_up_to kaçan günleri sırayla işler (kanıtlandı). Kaçan günde anahtarlama
→ **DELAYED_SIGNAL** (WARN) alarmı + journal etiketi + catch-up yürütme. İlk aktivasyon
(go-live) işaretlenmez.

### K4 — veri kayması + resync
yfinance auto_adjust temettü/split GEÇMİŞ kapanışları değiştirir → her döngü son 30 bar
kaynağa karşı doğrulanır; tolerans-üstü tarihsel sapma → **DATA_DRIFT (CRITICAL)** + o gün
sinyal FİNALİZE EDİLMEZ + journal. Operatör `--resync`: yedek + tam yeniden çekim +
force-overwrite + **otomatik kompozit parite** (canlı↔backtest). Sentetik temettü uçtan uca test.

### K5 — provisional-bar
Seans-içi → `provisional=true` + işlem yok; kapanış+grace sonrası → `provisional=false`;
active seans-içi → yürütme son yürütülebilir güne sınırlı. **grace=3600s**: BIST 18:00
kapanış sonrası yfinance gün barının oturması için (19:00 Istanbul'da final).

### K6 — INITIAL_ENTER maliyet mutabakatı (kusur DEĞİL + kök-neden hardening)
Önceki tur 99943.96 bir kusur değil: seans-içi fetch'te bazı sembollerin 07-07 barı henüz
yayınlanmamıştı → **KISMİ basket** (az sembol/notional/maliyet). Tam final barda (12 sembol)
figür **99852.29**, aritmetikle bit-bit: `100000 − komisyon(98.49) − slippage_drag(49.22)`;
broker yolu = `plan_enter` formülü (< 1e-9). **Kök-neden hardening:** FİNAL bar artık
zaman-final VE **veri-tam** (tüm sembollerde bar) VE drift-yok → kısmi basket yürütmesi
engellendi (backtest paritesi korunur).

### K7 / K9 — operatör + karne
- OPERATOR_GUIDE §7 resync prosedürü, §8 bakım penceresi (durdur→değiştir→test→başlat) +
  araştırma turlarının **dokunamayacağı modül listesi**.
- B7_D1_PROPOSAL iki katmanlı: K1 mekanik (≥4 hafta, 0 çökme/fark, kuru-test) + K2 olay
  (≥2 tatbikat 1 ENTER + 1 EXIT). Tatbikat İMPLEMENTASYONU bu turda YAPILMADI (öneri).

### K8 — EVDS CSV modu
`--csv` ile elle export edilen EVDS CSV (kolon eşleme + çoklu tarih formatı + Türkçe
ondalık) TRY_ON_RATE ile karşılaştırılabilir → endpoint (evds3 SPA) düzelmeden kuyruk #18
kapatılabilir. Snapshot DEĞİŞMEZ (yalnız rapor).

---

## 3. Dürüst çekinceler

1. **Faiz kaynağı gecikmesi:** TRY_ON_RATE (FRED/OECD) ~4 ay gecikmeli → canlı faiz kronik
   bayat. **Sapma yönü faiz patikasına bağlı** (m4 düzeltmesi): yükseliş döngüsünde bayat
   oran muhafazakâr (eksik tahakkuk), DÜŞÜŞ döngüsünde nakit getirisini ABARTIR (agresif).
   Uzun nakit + faiz-düşüş döneminde aleyhe sapabilir; kalıcı çözüm EVDS (kuyruk #18).
2. **Kill-switch eşikleri tarihsel-0-tetik konumlu:** paper döneminde bir switch tetiklenirse
   gerçekten görülmemiş bir koşuldur. Eşikler ÖNERİ; kullanıcı/baş danışman onayına tabi.
3. **Veri kayması ilk temettüde kesin oluşacak:** mevcut "0 çakışma" ilk BIST temettüsünde
   bozulur; DATA_DRIFT + resync bunu bekliyor ve gölge dönemde ilk kez GERÇEK veriyle sınanacak.
4. **Tatbikat mekanizması implemente edilmedi** (K9 öneri) — Faz 6 başında tasarlanacak.
5. **Parite tautoloji sınırı:** runner-replay ↔ journal aynı kod olduğundan parite esasen
   veri/state kaymasını yakalar (kod hatasını değil); K4 drift dedektörü bunu tamamlar.

## 4. Değişmeyenler (doğrulama)
- `mode: paper` (config.yaml) ✓; N/b/M mühürlü ✓; D1 üretim fonksiyonları ✓;
  `data/snapshots/` ✓; v7.1-golden 3/3 her commit ✓; Faz 6/real/launchd'ye adım YOK ✓.

## 5. Sıradaki adımlar (kullanıcı kararına bağlı — hüküm vermiyorum)
- go_live kararı (observe→active; Faz 6 resmi başlangıcı).
- F5-B2 ManualExecutionAdapter tasarımı (AlgoLab İPTAL).
- Kill-switch eşik onayı (K2 tablosu); B7 iki-katmanlı karne + tatbikat çerçevesi onayı.
- Real-öncesi kuyruk: EVDS (CSV veya endpoint), gerçek nakit bacağı enstrümanı.

**Değerlendirme kullanıcının/baş danışmanın. Bu tur hiçbir hüküm vermedi.**

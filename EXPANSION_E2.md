# EXPANSION E2 — Motor Genelleştirme Raporu

Tarih: 2026-07-07 (Europe/Istanbul) · Faz: EXPANSION.md E2 (Motor Genelleştirme)
Ön şartlar (hepsi sağlandı): v7.1-golden mühürlü · BIST hükmü (KALICI KAYIT 3) ·
D1 ailesi kabul (KALICI KAYIT 6) · "E2 onaylandı".

> **DURUM: E2 kod işi tamamlandı, kullanıcı/baş danışman değerlendirmesi bekliyor.**
> E4'e, Faz 5'e, regime_core üretim portuna GEÇİLMEDİ. Hiçbir BIST eşiği/gate'i/
> parametresi değiştirilmedi. Golden çapası her commit'te bayt-bayt YEŞİL.

---

## 1. DEMİR KURAL kanıtı (EXPANSION.md 0.2)

`tests/test_golden_bist.py` — BIST profili + v7 snapshot (`data/snapshots/2026-07-06`)
+ v7 config (`config/config.yaml`) → `run_backtest` → trades.csv, `tests/golden/
bist_v7_trades.csv` (SHA256 `08fa8ea8…`, 121 trade) ile **BAYT-BAYT** karşılaştırma.

Bu turdaki **HER commit** golden'ı yeşil bıraktı (kanıt: her commit mesajında).
İki katmanlı kanıt:
- `test_bist_backtest_byte_identical_to_golden` — cost_model=None (varsayılan yol).
- `test_daily_carry_hook_is_bist_safe` — BIST CostModel'iyle (carry=0) de bayt-bayt
  (daily_carry motor hook'unun BIST-güvenliği).

Ayrıca `python -m strategy.signal_engine --symbol THYAO --date 2024-06-03` çıktısı
E2 öncesiyle birebir aynı (evaluate_entry varsayılan yolu ENTRY_GATES/GATE_NAMES;
yeni gates/gate_names paramları None → değişiklik yok).

---

## 2. Yapılanlar (commit sırası)

| # | İş | Ana dosyalar | Golden |
|---|---|---|---|
| E2.0 | Golden çapa (İLK İŞ) | tests/golden/, backtest/golden_bist.py, tests/test_golden_bist.py | kuruldu |
| E2.1 | models.py yön/piyasa ekleri | core/models.py (Direction, ENTER/EXIT_SHORT, 4 RejectReason, alan ekleri) | ✓ |
| E2.2 | MarketSpec + registry | core/markets.py | ✓ |
| E2.3 | Takvimler + clock delegasyonu | core/calendars.py, core/clock.py, data/quality.py, +exchange_calendars | ✓ |
| E2.4 | gate_registry + bist göçü | strategy/gate_registry.py, signal_engine.py | ✓ |
| E2.5 | CostModel katmanı | costs/{base,bist,us_equities,fx}.py | ✓ |
| E2.6 | daily_carry motor hook | backtest/engine.py (additif 0b adımı) | ✓ |
| E2.7 | Yön farkındalığı + risk genişlemesi | risk/direction.py, risk/account_rules.py | ✓ |
| E2.8 | Config yükleyici | config/portfolio.yaml, config/markets/*.yaml, core/portfolio_config.py | ✓ |
| E2.9 | FX OHLC onarımı + veto altyapısı | data/cleaning.py, data/events.py | ✓ |

Tüm yeni alanlar VARSAYILANLI (CLAUDE.md Bölüm 4 / EXPANSION 0.3: yalnızca ekleme).
Çekirdekte `if market == "fx"` dallanması YOK — piyasa farkı yalnızca MarketSpec +
CostModel + gate profilinde soğuruldu (Bölüm 3.2).

---

## 3. Test planı sonucu (Bölüm 15)

- **15.1 Regresyon çapası**: `tests/test_golden_bist.py` — YEŞİL (bayt-bayt, 3 test).
- **15.2 Takvim/DST**: `tests/test_calendars.py` — YEŞİL. XNYS DST kapanış kayması
  (golden UTC değerleri), XIST resmî tatiller, FX_24_5 hafta sonu/yıl geçişi,
  next_eval, clock delegasyonu.
- **15.3 Yön/boyutlama**: `tests/test_direction.py` — YEŞİL. Ayna simetrisi
  (LONG P vs SHORT 2·P0−P: aynı R/|PnL|), sayısal boyutlama, quote-ccy, marjin,
  stop-önceliği SHORT, settlement, PDT.
- **15.4 Adapter/veri/events**: `tests/test_cleaning_fx.py`, `tests/test_events.py`
  — YEŞİL (earnings/econ pencere sınırları + FX onarımı).
- **Tam süit**: `pytest -q` → **364 passed, 0 failed** (261s). E2 öncesi 309'du;
  +55 test (golden, calendars, gate_registry, costs, direction, portfolio_config,
  cleaning_fx, events genişlemesi). Hiçbir mevcut test kırılmadı.

---

## 4. DÜRÜST BULGULAR / KIRMIZI BAYRAKLAR (Bölüm 17 protokolü)

1. **Takvim hayalet-bar tarihi tutarsızlığı** (belgelendi, çözüldü): EXPANSION 15.2
   (2024-04-08) ve E2 talimatı (2024-04-09) hayalet-bar tarihini "XIST tatili"
   sayıyordu; `exchange_calendars` 4.13.2'ye göre 2024 Ramazan Bayramı XIST
   tatilleri **04-10/11/12**'dir — 04-08/09 GERÇEK seans. Repodaki gerçek hayalet
   bar EREGL 2024-04-09'dur ve `volume=0` phantom bar'dır (data/cleaning.py
   yakalar), takvim katmanının sınıfı DEĞİL. İki mekanizma FARKLI hata sınıfları
   için; test gerçek tatilleri çapa aldı (tests/test_calendars.py).

2. **FX boyutlama IEEE754 float duyarlılığı**: spec'in "9375"i tam aritmetik
   varsayar; 0.008 double'da temsil edilemez → EURUSD-direkt 9374, USDJPY-conv
   9375 (±1 birim float komşusu). İkisi de mekanik doğru; testlerde belgelendi.
   Not: FX qty ölçekleri büyük olduğundan tek-birim fark maddi değil, ama E4 FX
   raporlarında determinizm için sabit-tohum + snapshot disiplini korunmalı.

3. **Engine SHORT ana-döngüsü E2'de AÇILMADI (bilinçli)**: Bölüm 8 gereği
   `direction_mode: two_sided` profiller short gate seti tanımlanana kadar
   backtest'te aktive edilmez. Bu yüzden run_backtest LONG-only bırakıldı (ölü
   kod yasağı); short MEKANİĞİ saf/tam-test-edilmiş fonksiyonlar olarak
   (risk/direction.py) kuruldu. Engine-seviyesi short EXECUTION, short-gate
   tasarım turundan (Bölüm 17 #10) sonra, FX aktivasyonuyla eklenecek.

4. **daily_carry PaperBroker entegrasyonu ertelendi**: PaperBroker (Faz 5) henüz
   YOK; carry hook backtest motoruna eklendi (BIST=0). PaperBroker inşa edilince
   aynı CostModel arayüzüyle carry orada da tahakkuk edecek (Bölüm 7.1).

5. **Journal market/currency kolonları ertelendi**: `journal/journal.py` (Faz 5
   modülü) henüz YOK; ALTER edilecek tablo yok. Journal inşa edilince `market
   TEXT` + `currency TEXT` kolonları geriye-uyumlu eklenecek (Bölüm 12).

6. **FX/econ tarihsel derinlik (Bölüm 10.4 devrede)**: EventCalendar altyapısı
   hazır ama `data/events/*.parquet` gerçek dosyaları henüz yok (E1 yalnızca
   örnekledi). Veri gelene dek is_blackout (False, "…veri yok…") döner → backtest
   vetosuz; canlı/paper'da veri bağlanınca aktif. Her E4 FX/US raporuna sınırlama
   notu ZORUNLU.

7. **swap oranları sabit muhafazakâr tahmin**: costs/fx.py swap'ları config'ten
   placeholder; her FX backtest raporuna "swap: sabit muhafazakâr tahmin" notu
   zorunlu (Bölüm 7.2). Güncel oranlar E1/E3'te doğrulanacak.

---

## 5. Bağımlılık değişikliği

`exchange_calendars==4.13.2` eklendi (requirements.txt + requirements.lock
BİRLİKTE, Bölüm 18). Gerekçe: XIST/XNYS resmî tatil + DST-doğru kapanış anları.
lxml EKLENMEDİ — earnings/econ VETO altyapısı (parquet okuma + pencere mantığı)
lxml gerektirmez; yalnızca veri FETCH (yfinance earnings) gerektirir, o E1/E3 işi.

---

## 6. Açık maddeler (E3/E4 kuyruğu)

- E3: broker adapter kararı (BROKER_SPIKE.md), SEC/TAF + swap resmî doğrulama,
  US hesap tipi (cash/margin) kararı.
- E4: US tam süiti (earnings vetosu 10.4 protokolüyle), FX yalnızca short-gate
  tasarımı + 9.1 testleri yeşilse.
- Short gate seti tasarımı (Bölüm 17 #10) — BIST yeniden-tasarım sonrası, FX
  aktivasyonu öncesi, kullanıcıyla ayrı tur.
- E1 açık maddeleri (değişmedi): FX veri temeli tamam; US evren instruments[]
  E4'te config'e girer.

---

*E2 kod işi burada biter. Kullanıcı/baş danışman değerlendirmesi bekleniyor —
E3/E4/Faz 5 için ayrı onay kapıları geçerlidir (EXPANSION.md Bölüm 16).*

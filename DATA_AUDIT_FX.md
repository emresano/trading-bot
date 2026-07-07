# Veri Denetimi — Forex (DATA_AUDIT_FX.md)

EXPANSION.md E1 (Veri Temeli) çıktısı. Salt-okunur denetim — hiçbir motor/
sinyal/risk kodu bu turda yazılmadı, BIST hattına dokunulmadı.

Snapshot: `data/snapshots/fx/2026-07-06/` (manifest hash'li, `tools/build_snapshot.py`
ile üretildi). Enstrüman seti: EUR_USD, GBP_USD, USD_JPY (EXPANSION.md Bölüm 1/11.3
— altın Bölüm 17 madde 8'e tabi, bu sette YOK).

## Kaynak Kararı — Belgelenmiş Sapma (Bölüm 17 belirsizlik protokolü)

EXPANSION.md Bölüm 6.2: *"oanda.py: v20 REST practice ... Hesap yoksa E1 yedek
yolu: Dukascopy/histdata CSV."* Bu E1 turunda:

1. **OANDA practice hesabı YOK** — `secrets.env`'de kimlik bilgisi bulunmuyor.
2. **Dukascopy'nin ham tick endpoint'i bu ortamdan ERİŞİLEMEDİ** (`curl` bağlantı
   kuramadı — muhtemelen ağ kısıtı; test edildi, kanıt: bağlantı zaman aşımı).
3. **histdata.com'un CSV indirme akışı etkileşimli** (JS/token tabanlı), otomatik/
   güvenilir bir programatik indirme sağlamıyor.

**Karar (teknik, konservatif, Bölüm 17 genel kuralına göre — dur/sor değil,
ilerle/dokümante et):** E1'in dondurulmuş FX snapshot'ı `data/adapters/yf_fx.py`
(yfinance: EURUSD=X, GBPUSD=X, USDJPY=X) üzerinden üretildi — projede zaten
güvenilen, BIST'te aynı rolü oynayan bir kütüphane. `data/adapters/oanda.py`
yine de Bölüm 6.2'nin öngördüğü ABC implementasyonu olarak YAZILDI (referans
implementasyon, CLAUDE.md'nin AlgoLab `auth.py` emsaliyle tutarlı) — **hiçbir
practice hesapla test edilmedi**, E3'te doğrulanacak. Bu, Bölüm 17 madde 7'nin
("OANDA veri derinliği / backtest başlangıcı") E3'e kadar açık kalan kısmıdır.

## Veri Bütünlüğü Denetimi (HARDENING A2 deseni, `tools/data_audit.py`)

| Sembol | Durum | Satır | Kalite | Sıçrama (≥%25) |
|---|---|---|---|---|
| EUR_USD | **FAIL** | 5578 | FAIL | 0 |
| GBP_USD | **FAIL** | 5590 | FAIL | 0 |
| USD_JPY | PASS | 5577 | PASS | 0 |

### FAIL kök nedeni — çapraz-sembol tesadüf değil, gerçek bulgu

Her iki FAIL de **AYNI tarihte** (2010-07-01), OHLC iç tutarlılık ihlali
(`close > high`):

| Sembol | open | high | low | **close** | İhlal |
|---|---|---|---|---|---|
| EUR_USD | 1.223197 | 1.224260 | 1.219899 | **1.250750** | close > high |
| GBP_USD | 1.494590 | 1.497342 | 1.487852 | **1.516576** | close > high |
| USD_JPY | 88.426 | 88.540 | 86.980 | 87.600 | yok (bu sembol etkilenmedi) |

**Bu iki farklı para çiftinde AYNI takvim gününde ortaya çıkan bir ihlal —
tesadüf değil, yfinance'in FX veri hattında bu tarihe özgü sistematik bir
kaynak sorunu olduğunu gösteriyor** (muhtemelen bir sağlayıcı/agregasyon
hatası; 2010-07-01 çeyrek başlangıcına denk geliyor, bu bir ipucu olabilir
ama kesin kök neden dışarıdan doğrulanmadı). USD_JPY aynı tarihte etkilenmedi
— sorun tüm FX verisini değil, seçici olarak bazı çiftleri/günleri etkiliyor.

**Bu, EXPANSION.md'nin OANDA'yı FX için neden tercih ettiğini somut olarak
doğruluyor** — yfinance'in FX verisi BIST/US hisse verisinden daha az
güvenilir görünüyor (merkezi bir borsa/takas olmadığından, sağlayıcılar
arası mid-price agregasyonu bu tür tekil-gün tutarsızlıklarına daha açık).

**Bu turda DÜZELTİLMEDİ** (E1 read-only/veri-temeli kapsamı; düzeltme —
örn. bu tek barın forward-fill'i veya elenmesi — E2'nin motor entegrasyonu
sırasında, `data/cleaning.py`'nin BIST hayalet-bar filtresine benzer bir
FX-özel kural olarak ele alınmalı). **E2 için not: bu iki sembol backtest'e
sokulmadan önce bu tekil-gün ihlali ele alınmalı, aksi halde
`data/quality.py::check_quality` bu günü (ve o günü içeren pencereyi) FAIL
olarak işaretleyip işlemi durdurur** (CLAUDE.md Bölüm 7.2 tasarımı gereği —
bu kendi içinde doğru/güvenli davranış, ama sembol o gün için tamamen
işlemsiz kalır).

## auto_adjust / Kurumsal Aksiyon Notu

FX'te kurumsal aksiyon (split/temettü) kavramı yapısal olarak yok —
`auto_adjust=True` FX indirmelerinde etkisiz bir bayraktır (zarar vermez,
işlevsiz). `AdapterMeta.correction_policy`: "yok (FX'te kurumsal aksiyon/
ayarlama kavramı yok)."

## Takvim Vetosu Veri Kaynağı Değerlendirmesi (Bölüm 10, madde 5/13)

`data/events.py::fetch_economic_calendar_current_week_sample()` ForexFactory'nin
herkese açık, kimlik doğrulamasız widget feed'ini (`nfs.faireconomy.media/
ff_calendar_thisweek.json`) test etti — **çalışıyor, şemaya uygun veri
döndürüyor (title/country/date/impact), ama YALNIZCA İÇİNDE BULUNULAN HAFTA**
için. Test anında 74 satır döndürdü (örnek: "MI Inflation Gauge m/m",
country=AUD, impact=Low).

**Bulgu (Bölüm 17 belirsizlik #5'in çözümü): ücretsiz, programatik bir
TARİHSEL ekonomik takvim arşivi bulunamadı.** FMP/AlphaVantage'ın ücretsiz
katmanları API anahtarı gerektiriyor, bu oturumda değerlendirilemedi (kimlik
bilgisi yok). **Sonuç: Bölüm 10.4 fallback protokolü ekonomik takvim vetosu
için DEVREDE** — FX ekonomik-olay vetosu backtest'te MODELLENEMEYECEK,
yalnızca canlı/paper'da aktif olacak (E2+ implementasyonu); her FX backtest
raporuna şu sınırlama notu ZORUNLU düşülecek: *"ekonomik takvim vetosu
backtest'te modellenemedi; canlıda ek koruma olarak devrededir."*

## Swap Oranları (Bölüm 17 belirsizlik #6)

Bu turda değerlendirilmedi — E1 kapsamı veri temeliyle sınırlı, swap
oranlarının güncel değerleri E3'te broker'dan alınacak (EXPANSION.md
Bölüm 7.2'deki muhafazakâr placeholder'lar hâlâ geçerli, config/markets/fx.yaml
henüz oluşturulmadı — bu E2 işi).

## BIST Hattında Sıfır Değişiklik

`git diff` bu turda `data/historical.py`, `data/cleaning.py`, `data/quality.py`,
`backtest/`, `strategy/`, `risk/`, `config/config.yaml` dosyalarının HİÇBİRİNİ
değiştirmediğini gösteriyor (bkz. commit). `tools/data_audit.py`
DEĞİŞTİRİLMEDEN, yalnızca farklı `--snapshot`/`--out` argümanlarıyla yeniden
kullanıldı.

---

## E2 NOTU — 2010-07-01 OHLC ihlali ele alındı (2026-07-07, Motor Genelleştirme turu)

E1'de tespit edilen ve "E2'ye bırakılan" tekil-gün OHLC ihlali (EUR_USD &
GBP_USD 2010-07-01, `close > high`) E2'de çözüldü:

- **`data/cleaning.py::repair_fx_ohlc(df, symbol)`** — BIST hayalet-bar
  filtresine benzer, FX-özel, LOGLANAN, BELLEK-İÇİ bir kural. Snapshot
  parquet'lerine DOKUNMAZ. Onarım: `high = max(high, open, close)`,
  `low = min(low, open, close)` — `close` (en önemli fiyat) korunur, OHLC
  tutarlı hale gelir. Aksi halde `data/quality.py::check_quality` o günü FAIL
  işaretleyip sembolü o gün işlemsiz bırakırdı.
- **Kanıt**: `tests/test_cleaning_fx.py::test_real_snapshot_2010_07_01_repaired`
  gerçek snapshot'ta iki sembol için de 2010-07-01'in onarım logunda olduğunu
  ve onarım sonrası barın tutarlı olduğunu doğrular; `test_repair_makes_quality_pass`
  onarımın check_quality'yi FAIL→PASS'a çevirdiğini gösterir.
- Kaynak snapshot DEĞİŞMEDİ; onarım yalnızca yükleme anında (E4 FX backtest'i
  bu fonksiyonu çağıracak). Genel kural (tarihe bağlı değil): `close`/`open`,
  `[low, high]` dışına çıkan HER FX barını onarır ve loglar.

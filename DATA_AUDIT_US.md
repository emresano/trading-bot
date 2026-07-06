# Veri Denetimi — ABD Hisseleri (DATA_AUDIT_US.md)

EXPANSION.md E1 (Veri Temeli) çıktısı. Salt-okunur denetim — hiçbir motor/
sinyal/risk kodu bu turda yazılmadı, BIST hattına dokunulmadı (kanıt: bu
raporun sonunda ve commit'te `git diff` ile gösterilir).

Snapshot: `data/snapshots/us/2026-07-06/` (manifest hash'li, `tools/build_snapshot.py`
ile üretildi). Adaptör: `data/adapters/yf_us.py` (yfinance, `auto_adjust=True`).

## Evren Önerisi (20 sembol, 8 sektör)

Seçim kriterleri (EXPANSION.md Bölüm 16, E1): likidite + 2005'ten itibaren
tarihçe + sektör çeşitliliği. **Geçmiş getiriye göre seçim YAPILMADI** —
semboller yalnızca "bugün hâlâ büyük/likit, uzun süredir işlem gören ABD
hissesi" kriteriyle seçildi.

| Sembol | Şirket | Sektör (GICS yaklaşık) |
|---|---|---|
| AAPL | Apple | Bilgi Teknolojisi |
| MSFT | Microsoft | Bilgi Teknolojisi |
| INTC | Intel | Bilgi Teknolojisi |
| CSCO | Cisco | Bilgi Teknolojisi |
| JNJ | Johnson & Johnson | Sağlık |
| PFE | Pfizer | Sağlık |
| MRK | Merck | Sağlık |
| JPM | JPMorgan Chase | Finans |
| BAC | Bank of America | Finans |
| XOM | ExxonMobil | Enerji |
| CVX | Chevron | Enerji |
| PG | Procter & Gamble | Temel Tüketim |
| KO | Coca-Cola | Temel Tüketim |
| WMT | Walmart | Temel Tüketim |
| HD | Home Depot | Tüketici Takdiri |
| MCD | McDonald's | Tüketici Takdiri |
| NKE | Nike | Tüketici Takdiri |
| DIS | Disney | İletişim Hizmetleri |
| VZ | Verizon | İletişim Hizmetleri |
| CAT | Caterpillar | Sanayi |

**Survivorship (hayatta kalma) yanlılığı notu — bilinen ve KABUL EDİLEN bir
sınırlama:** Bu 20 sembol BUGÜN büyük/likit oldukları için seçildi; 2005'te
benzer büyüklükte olup o tarihten bu yana küçülen, birleşen veya iflas eden
şirketler (örn. Lehman Brothers, Washington Mutual, General Motors'un 2009
iflası, Kodak) evrene dahil EDİLMEDİ. Bu, gerçekte 2005'te mevcut olan tam
"büyük ABD hissesi" evreninden DAHA İYİMSER bir performans tablosu üretebilir
— gelecekteki backtest sonuçları bu yanlılığı hesaba katarak yorumlanmalı.
Düzeltme (hayatta kalmayan şirketleri de içeren bir evren inşası) bu turun
kapsamı dışında; E4 öncesi bir metodoloji notu olarak STATUS.md'ye işlendi.

## Veri Derinliği ve Bütünlük Denetimi (HARDENING A2 deseni, `tools/data_audit.py`)

| Sembol | Durum | Satır | Kalite | Sıfır/Negatif Fiyat | Yinelenen Tarih | Eksik Gün | Sıçrama (≥%25) |
|---|---|---|---|---|---|---|---|
| AAPL | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| BAC | WARN | 5408 | PASS | 0 | 0 | 0 | 9 |
| CAT | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| CSCO | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| CVX | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| DIS | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| HD | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| INTC | WARN | 5408 | PASS | 0 | 0 | 0 | 1 |
| JNJ | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| JPM | WARN | 5408 | PASS | 0 | 0 | 0 | 1 |
| KO | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| MCD | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| MRK | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| MSFT | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| NKE | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| PFE | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| PG | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| VZ | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| WMT | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |
| XOM | PASS | 5408 | PASS | 0 | 0 | 0 | 0 |

**Hiçbir FAIL yok.** Tüm 20 sembol 2005-01-03 → 2026-07-02 arası tam,
yinelenmesiz, monotonik veriye sahip; sıfır/negatif fiyat veya eksik gün
bulunamadı (BIST'in EREGL hayalet-bar deneyiminin ABD verisinde bir karşılığı
görülmedi).

### WARN detayları (≥%25 günlük sıçrama)

- **BAC (9 gün, hepsi 2008-10 → 2009-04 arası)**: 2008 küresel finans krizinin
  doruk noktası — Bank of America'nın gerçek, iyi belgelenmiş aşırı
  oynaklık dönemi (hükümet kurtarma müzakereleri, Merrill Lynch birleşmesi
  sonrası belirsizlik). 6/9 gün "hacim destekli gerçek hareket" sınıfında;
  3/9 "sınıflandırılamadı" (hacim oranı sınıra yakın, ~1.0-1.3× — kesin
  hüküm için elle inceleme önerilir, ama kriz döneminin doğası göz önüne
  alındığında veri hatasından çok gerçek oynaklık olması muhtemel).
- **INTC (2024-08-02, -%26.1)**: Intel'in gerçek, kamuya mal olmuş post-kazanç
  çöküşü (2024 Q2 sonuçları + temettü kesintisi duyurusu) — hacim destekli
  (4.13× 20-gün ortalama), gerçek hareket.
- **JPM (2009-01-21, +%25.1)**: 2009 banka rallisi döneminde gerçek, hacim
  destekli bir hareket.

**Genel değerlendirme: ABD verisinde BIST'te görülen türden bir "bedelli
sermaye artırımı kör noktası" YOK** — ABD şirketleri hisse geri alımı/bölünme
yaparlar ama Türkiye'ye özgü "bedelli sermaye artırımı" enstrümanı ABD
piyasasında yapısal olarak mevcut değil; `auto_adjust=True` klasik
bölünme/temettüyü güvenilir şekilde düzeltir. Yukarıdaki tüm WARN'lar gerçek,
açıklanabilir piyasa olaylarıyla örtüşüyor — DATA_AUDIT_v2.md'nin BIST'te
bulduğu türden "açıklanamayan gap" sınıfına giren bir ABD günü YOK.

## Kaynak/Adaptör Notları

- `data/adapters/yf_us.py`: yfinance, `auto_adjust=True`, tz-aware index
  (America/New_York → UTC; negatif ofset nedeniyle BIST'in yaşadığı bir-gün-
  geri kayması buradaki veride YAPISAL OLARAK yok, bkz. `data/adapters/base.py`
  docstring'i ve `tests/test_adapters_base.py`).
- `AdapterMeta.correction_policy`: "auto_adjust=True (yfinance) — kurumsal
  işlemler (split/temettü) düzeltilir."

## Takvim Vetosu Veri Kaynağı Değerlendirmesi (Bölüm 10, madde 5/13)

`data/events.py` yazıldı (iskelet + örnek çekim). **Bulgu (Bölüm 17 belirsizlik
#4'ün çözümü): `yfinance.Ticker.get_earnings_dates(limit=100)` test edilen 4
sembolde (AAPL, JPM, XOM, CAT) 2001-2002'ye kadar giden tarihçe döndürdü —
2005-01-01 backtest başlangıcından ÖNCESİNE geçiyor.** CLAUDE.md/EXPANSION.md'nin
öngördüğü "yfinance earnings geçmişi sığdır" endişesi bu örneklemde
DOĞRULANMADI. Zaman damgasından (ET saatine göre) kaba bir BMO/AMC çıkarımı
yapılabiliyor (`data/events.py::_infer_session`). **Sonuç: E2'de ABD earnings
vetosu backtest'te TAM olarak modellenebilir** (Bölüm 10.4'ün "tam tarihçe
bulunamazsa" fallback senaryosu ABD için gerekmiyor gibi görünüyor — 20
sembolün TAMAMI E2'de doğrulanmalı, bu yalnızca 4 sembollük bir örneklem).

**Not:** `get_earnings_dates()` `lxml` paketini gerektiriyor — şu an
`requirements.txt`'e eklenmedi (yalnızca bu değerlendirme için venv'e geçici
kuruldu). E2'de gerçek implementasyon kararlaştırılırsa Bölüm 18 kuralına göre
`requirements.txt` + `requirements.lock` birlikte güncellenecek.

## BIST Hattında Sıfır Değişiklik

`git diff` bu turda `data/historical.py`, `data/cleaning.py`,
`data/quality.py`, `backtest/`, `strategy/`, `risk/`, `config/config.yaml`
dosyalarının HİÇBİRİNİ değiştirmediğini gösteriyor (bkz. commit).
`tools/data_audit.py` DEĞİŞTİRİLMEDEN, yalnızca farklı `--snapshot`/`--out`
argümanlarıyla yeniden kullanıldı.

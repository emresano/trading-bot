# Veri Denetimi — US2 Evreni (DATA_AUDIT_US2.md)

D2US-S1 (kesitsel momentum ailesi) turunun **item 1** çıktısı. Salt-okunur denetim
— hiçbir motor/sinyal/risk kodu ve hiçbir canlı bot modülü bu adımda yazılmadı/
değiştirilmedi; BIST v7.1-golden 3/3 korundu (kanıt: commit `git diff`).

Snapshot: **`data/snapshots/us2/2026-07-08/`** (manifest sha256
`7f34c669…a3032b34`, `tools/build_us2_snapshot.py` ile bir kez üretildi, sonrası
deterministik/offline). Adaptör: `data/adapters/yf_us.py` (yfinance,
`auto_adjust=True`). Temizlik borusu **S1b/E4 ile AYNI**
(`data/cleaning.py::load_and_clean_universe` — E4'te kanıtlandığı gibi
`normalize_bist_dates` US 00:00-UTC verisinde NO-OP, hayalet-bar filtresi
piyasa-agnostiktir).

**Kapsam:** 50 sembolün TAMAMI **2005-01-03 → 2026-07-08, 5411 işlem günü**,
tam/yinelenmesiz/monotonik. Mevcut E4 US evreni (20 sembol) KORUNDU; 30 yeni
sembol eklendi (E4'ün `us/2026-07-06` snapshot'ı DEĞİŞTİRİLMEDİ — us2 ayrı,
bağımsız bir dizindir).

---

## 1. Evren (50 sembol, 10 GICS sektörü)

Seçim kriteri (E1/EXPANSION.md Bölüm 16 emsali): **likidite + 2005'ten itibaren
kesintisiz tarihçe + sektör çeşitliliği. Geçmiş getiriye göre seçim YAPILMADI** —
semboller yalnızca "bugün hâlâ büyük/likit, 2005'ten beri sürekli işlem gören ABD
hissesi" kriteriyle seçildi. İlk 20 (★) = E4 US evreni, aynen korundu.

| # | Sembol | Şirket | Sektör (GICS yaklaşık) |
|---|---|---|---|
| 1 | AAPL ★ | Apple | Bilgi Teknolojisi |
| 2 | MSFT ★ | Microsoft | Bilgi Teknolojisi |
| 3 | INTC ★ | Intel | Bilgi Teknolojisi |
| 4 | CSCO ★ | Cisco | Bilgi Teknolojisi |
| 5 | ORCL | Oracle | Bilgi Teknolojisi |
| 6 | IBM | IBM | Bilgi Teknolojisi |
| 7 | TXN | Texas Instruments | Bilgi Teknolojisi |
| 8 | QCOM | Qualcomm | Bilgi Teknolojisi |
| 9 | JNJ ★ | Johnson & Johnson | Sağlık |
| 10 | PFE ★ | Pfizer | Sağlık |
| 11 | MRK ★ | Merck | Sağlık |
| 12 | ABT | Abbott | Sağlık |
| 13 | AMGN | Amgen | Sağlık |
| 14 | MDT | Medtronic | Sağlık |
| 15 | LLY | Eli Lilly | Sağlık |
| 16 | GILD | Gilead Sciences | Sağlık |
| 17 | JPM ★ | JPMorgan Chase | Finans |
| 18 | BAC ★ | Bank of America | Finans |
| 19 | WFC | Wells Fargo | Finans |
| 20 | GS | Goldman Sachs | Finans |
| 21 | AXP | American Express | Finans |
| 22 | C | Citigroup | Finans |
| 23 | XOM ★ | ExxonMobil | Enerji |
| 24 | CVX ★ | Chevron | Enerji |
| 25 | COP | ConocoPhillips | Enerji |
| 26 | SLB | Schlumberger | Enerji |
| 27 | PG ★ | Procter & Gamble | Temel Tüketim |
| 28 | KO ★ | Coca-Cola | Temel Tüketim |
| 29 | WMT ★ | Walmart | Temel Tüketim |
| 30 | PEP | PepsiCo | Temel Tüketim |
| 31 | CL | Colgate-Palmolive | Temel Tüketim |
| 32 | MO | Altria | Temel Tüketim |
| 33 | HD ★ | Home Depot | Tüketici Takdiri |
| 34 | MCD ★ | McDonald's | Tüketici Takdiri |
| 35 | NKE ★ | Nike | Tüketici Takdiri |
| 36 | SBUX | Starbucks | Tüketici Takdiri |
| 37 | LOW | Lowe's | Tüketici Takdiri |
| 38 | TGT | Target | Tüketici Takdiri |
| 39 | DIS ★ | Disney | İletişim Hizmetleri |
| 40 | VZ ★ | Verizon | İletişim Hizmetleri |
| 41 | CMCSA | Comcast | İletişim Hizmetleri |
| 42 | T | AT&T | İletişim Hizmetleri |
| 43 | CAT ★ | Caterpillar | Sanayi |
| 44 | HON | Honeywell | Sanayi |
| 45 | UNP | Union Pacific | Sanayi |
| 46 | BA | Boeing | Sanayi |
| 47 | DUK | Duke Energy | Kamu Hizmetleri |
| 48 | SO | Southern Company | Kamu Hizmetleri |
| 49 | NEM | Newmont | Malzeme |
| 50 | APD | Air Products | Malzeme |

**Sektör dağılımı (denge):** Bilgi Teknolojisi 8 · Sağlık 8 · Finans 6 · Temel
Tüketim 6 · Tüketici Takdiri 6 · Enerji 4 · İletişim 4 · Sanayi 4 · Kamu
Hizmetleri 2 · Malzeme 2 = **50** (E4'ün 8 sektörüne Kamu Hizmetleri + Malzeme
eklendi). Tek sektörün ağırlığı ≤ %16 (8/50).

---

## 2. ⚠ ZORUNLU — Survivorship (hayatta kalma) yanlılığı

**Bilinen ve KABUL EDİLEN bir sınırlama (E4 emsali).** Bu 50 sembol **BUGÜN**
büyük/likit oldukları için seçildi. 2005'te benzer büyüklükte olup o tarihten bu
yana iflas eden, birleşen, küçülen veya endeksten düşen şirketler (Lehman
Brothers, Washington Mutual, Bear Stearns, General Motors'un 2009 iflası, Kodak,
Sun Microsystems, Sprint/Nextel, Wachovia, Countrywide…) evrene **DAHİL DEĞİL.**

**Kesitsel momentum ailesi için bu yanlılığın YÖNÜ ve neden MUHAFAZAKÂR olduğu
(kritik):**
- Benchmark = US2 **eşit-ağırlık sepet al-tut**. Bu sepet yalnızca hayatta
  kalanlardan oluştuğu için gerçekte-mümkün-olandan **daha yüksek** getiri/Sharpe
  üretir → **kabul çıtası gerçek-üstü yüksektir.** Stratejiyi bu şişirilmiş sepete
  karşı koymak, kabul bakımından **muhafazakâr** (zorlu) bir seçimdir (E4 §0 ile
  birebir aynı gerekçe).
- **Kesitsel momentuma ÖZGÜ ek nüans (dürüstçe):** momentum stratejisi de AYNI
  hayatta-kalan evrenden seçim yapar; iflasa giden bir "kaybeden"in nihai çöküşünü
  short'lamaz (aile LONG-only) ve o ismi zaten elde tutmaz. Yani survivorship,
  hem benchmark'ı hem stratejiyi YUKARI çeker — ama benchmark daima %100
  yatırımda olduğu ve stratejinin kaçırdığı hiçbir "büyük kaybeden temizliği"
  avantajı olmadığı için, **net etki kabul-kriteri kıyasında yine strateji
  ALEYHİNE / muhafazakârdır.** Gerçek (hayatta-kalmayanları içeren) bir evrende
  kesitsel momentumun kaybedenlerden kaçınma avantajı DAHA belirgin olabilirdi;
  bu evren o avantajı ölçmez → ölçülen sonuç, momentumun gerçek potansiyelinin
  ALT sınırıdır.
- **Sonuç:** ölçülen her "geçer/kalır" mekanik sonucu, bu yanlılık ışığında
  yorumlanmalı. Düzeltme (delisting/iflas dahil tam tarihsel evren, ör.
  CRSP/point-in-time üyelik) bu turun kapsamı DIŞINDA; ayrı bir metodoloji turu
  gerektirir ve D2_US_S1.md karar bölümünden ÖNCE bir çekince olarak yazılır.

---

## 3. Veri Derinliği ve Bütünlük Denetimi

Kaynak: `tools/data_audit.py` (HARDENING A2 deseni), DEĞİŞTİRİLMEDEN yalnız
`--snapshot data/snapshots/us2/2026-07-08` argümanıyla yeniden kullanıldı.

**Özet: 50 sembolün TAMAMI PASS/WARN — hiçbir FAIL yok.**

| Metrik | Sonuç |
|---|---|
| Sembol sayısı | 50 |
| Satır sayısı (her sembol) | 5411 (2005-01-03 → 2026-07-08) |
| Sıfır/negatif fiyat | 0 (tüm semboller) |
| Yinelenen tarih | 0 (tüm semboller) |
| Eksik gün | 0 (tüm semboller) |
| Kalite kontrolü (OHLC tutarlılık) | PASS (tüm semboller) |
| FAIL sayısı | **0** |
| WARN sayısı (≥%25 günlük sıçrama) | 9 sembol |

**Kompozit temizlik (`load_and_clean_universe` + `build_composite`, E4 ile aynı
kod):** hayalet-bar **0 elendi**, forward-fill **0** — US verisi temiz, 50 sembol
5411 günde tam hizalı (BIST'in EREGL phantom deneyiminin US karşılığı yok).

### WARN detayları (≥%25 günlük sıçrama) — hepsi gerçek, açıklanabilir olaylar

| Sembol | Sıçrama sayısı | Dönem / açıklama |
|---|---|---|
| BAC | 9 | 2008-10 → 2009-04 küresel finans krizi doruğu (Merrill birleşmesi, kurtarma) |
| C | 7 | 2008-11 → 2009-04 kriz (Citi'nin en oynak dönemi; 2011 ters-bölünme auto_adjust ile düzeltilmiş, süreklilik korundu) |
| WFC | 3 | 2008-07 / 2009-01 / 2009-04 kriz rallileri (hacim destekli) |
| GS | 1 | 2008-11-24 kriz rallisi |
| JPM | 1 | 2009-01-21 banka rallisi (hacim destekli) |
| INTC | 1 | 2024-08-02 gerçek post-kazanç çöküşü (-%26.1, 4.13× hacim, temettü kesintisi) |
| COP | 1 | 2020-03-24 COVID dip-toparlanması |
| SLB | 1 | 2020-03-09 COVID petrol şoku (-%27.4, 4.65× hacim) |
| NEM | 1 | 2008-11-21 kriz-dönemi hareket (hacim destekli) |
| ORCL | 1 | 2025-09-10 gerçek AI-bulut kaynaklı sıçrama (+%35.9, 7.05× hacim) |

Tüm WARN'lar 2008-09 finans krizi, 2020 COVID çöküşü veya kamuya mal olmuş
gerçek şirket olaylarıyla (kazanç, AI rallisi) örtüşüyor — **DATA_AUDIT_v2.md'nin
BIST'te bulduğu türden "açıklanamayan gap" sınıfına giren bir US günü YOK.** WARN
semboller (özellikle 2008-09 bankaları) kesitsel momentum için ilginçtir: kriz
momentum-crash epizotları D2_US_S1.md'de ayrı analiz edilecek (item 4a).

**auto_adjust sınırlaması (bilinen):** `auto_adjust=True` temettü/bölünmeyi OHLC'ye
işler; ham (düzeltilmemiş) fiyat saklanmaz → bir sıçramanın gerçek hareket mi
adjustment artefaktı mı olduğu ham veriyle KESİN ayrıştırılamaz. Yukarıdaki hacim
destekli sınıflandırma bir DENEME'dir. Spinoff-ağırlıklı isimler (MO: 2007 Kraft /
2008 PMI ayrışması; T: medya ayrışmaları) süreklilik açısından temiz (eksik gün 0,
FAIL yok) ama fiyat serileri auto_adjust'ın spinoff işleme kalitesine tabidir —
kesitsel momentumda tek bir ismin artefaktı 1/50 ağırlıkla sınırlıdır (kompozit
seyreltme).

---

## 4. Kaynak / Adaptör / İzolasyon Notları

- `data/adapters/yf_us.py`: yfinance, `auto_adjust=True`, tz-aware index
  (America/New_York → UTC; negatif ofset nedeniyle BIST'in yaşadığı bir-gün-geri
  kayması burada YAPISAL OLARAK yok). `AdapterMeta.correction_policy`:
  "auto_adjust=True — kurumsal işlemler (split/temettü) düzeltilir."
- **Snapshot dondurma:** `tools/build_us2_snapshot.py` (yeni araç); mevcut hiçbir
  snapshot'a (BIST/us/aux/aux_us/us_bench/fx) DOKUNMADI, yalnız yeni `us2/` dizini
  yazdı. sha256 manifest her parquet için ayrı hash tutar → determinizm/offline.
- **İZOLASYON:** bu adımda `mode: paper`, canlı bot modülleri
  (strategy/regime_core.py, execution/, safety/, data/live_*, notify/, main.py,
  config/config.yaml, config/regime_core.yaml) ve S1/S1b/E4 araçları
  (backtest/regime_core*.py, tools/run_regime_core*.py, tools/e4_common.py,
  config/regime_core_us.yaml) DEĞİŞTİRİLMEDİ. `data/cleaning.py`,
  `data/adapters/yf_us.py`, `tools/data_audit.py`, `tools/build_snapshot.py`
  DEĞİŞTİRİLMEDEN yeniden kullanıldı. BIST v7.1-golden 3/3 (kanıt: commit).

*Denetim sonu. Bu evren, D2US_CRITERIA.md'nin (item 2) benchmark referansının ve
D2-US spike'ının (item 4) tek veri kaynağıdır; koşumdan önce dondurulmuştur.*

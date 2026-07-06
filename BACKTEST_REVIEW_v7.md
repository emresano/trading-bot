# Backtest Değerlendirme Raporu — v7 (motor + veri düzeltme turu)

Tarih / commit: 2026-07-06, commit `5227438` (equity forward-fill + aynı-gün-çoklu-onay
+ veri temizleme katmanı + performans turu) üzerine koşuldu.
Komut: `python -m backtest.cli --symbols THYAO,GARAN,ASELS,AKBNK,KCHOL,SAHOL,EREGL,TUPRS,TCELL,TOASO,SISE,ARCLK --config config/config.yaml --snapshot data/snapshots/2026-07-06 --start-date 2005-01-01 --walk-forward --monte-carlo --regime-split --sweep --benchmark --out runtime/backtest_reports_v7/`
Veri: HARDENING.md A1 snapshot'ından (`data/snapshots/2026-07-06/`, ağdan
indirme yok), `data/cleaning.py` katmanından (hayalet-bar filtresi + Istanbul
tarih normalizasyonu) geçirilerek. Çalışma süresi: ~1 saat 49 dakika (10:00–11:49)
— v6'nın ~6.5 saatine göre ~3.6× hızlanma (madde 6 performans turu: breaker artık
CLI çağrısı başına tek paylaşılan geçici dizin kullanıyor).

> **ÖNEMLİ NOT — taban çizgisi değişti:** `BACKTEST_REVIEW.md`/`_v2`/`_v3`/`_v4`/`_v5`/`_v6`
> dosyaları **tarihsel kayıttır**, o oturumlardaki bilinen motor/veri hatalarını
> (equity sıfırlama, aynı-gün-çoklu-onay, hayalet bar, tarih kayması) İÇEREN
> sonuçları belgeler. **v7, bu hataların düzeltilmesinden sonraki TEK geçerli
> taban çizgisidir.** v1–v6 yeniden KOŞULMADI ve koşulmayacak — geçmiş
> raporlardaki mutlak sayılar (özellikle max DD) artık karşılaştırma için
> kullanılmamalı, yalnızca "o zaman ne düşünüldüğü"nün kaydı olarak durur.

## Bu turda yapılan düzeltmeler (madde 1-6, DIAGNOSTICS_v6.md'nin bulgularına karşılık gelir — hiçbir eşik/gate davranışı değişmedi, adx_min=25 dahil aynen kalıyor)

1. **Equity forward-fill** (`backtest/engine.py`): açık pozisyonun o gün fiyatı
   yoksa artık son bilinen kapanışla taşınıyor, 0 sayılmıyor.
2. **Aynı-gün-çoklu-onay düzeltmesi**: gün içi onaylar kalan slotu HEMEN
   düşürüyor (deterministik alfabetik aday sırası).
3. **Veri temizleme katmanı** (`data/cleaning.py`, YENİ): (a) hayalet-bar
   filtresi, (b) UTC→Istanbul tarih normalizasyonu. Snapshot parquet
   dosyalarına DOKUNULMADI.
4. **DATA_AUDIT_v2.md**: %10 eşiğiyle 12 sembolün tamamı tarandı (read-only, bu
   raporun sonuçlarını etkilemedi, ayrı belge).
5. **Veri kaynağı keşfi**: AlgoLab değerlendirmesi (read-only, DATA_AUDIT_v2.md'de).
6. **Performans**: breaker artık CLI çağrısı başına tek paylaşılan geçici dizin
   kullanıyor (kanıt: kısa koşuda trades.csv bayt-bayt aynı — bu koşumun davranışını
   ETKİLEMEDİ, yalnızca hızlandırdı).

## v6 → v7 Yan Yana Karşılaştırma

| Metrik | v6 (bug'lı equity + hayalet bar + tarih kayması) | v7 (düzeltilmiş) | Yön |
|---|---|---|---|
| Trade sayısı (tüm dönem) | 119 | **121** | ~aynı (+2) |
| Toplam getiri | -1.91% | **2.03%** | ↑ |
| Profit factor | 0.94 | **1.07** | ↑ |
| Win rate | 42.86% | 44.63% | ~aynı |
| **Maks. drawdown (tüm dönem)** | **-20.74%** | **-6.71%** | **DRAMATİK İYİLEŞME (bkz. aşağı — gerçek sonuç bu)** |
| Sharpe | 0.00 | 0.07 | ↑ |
| Breaker tetiklenme sayısı | 1 (2024-04-08*) | **0** | **artık hiç tetiklenmiyor** |
| OOS profit factor (walk-forward) | 0.76 | 0.75 | ~aynı |
| OOS max DD (walk-forward) | -19.90% | **-16.65%** | ↓ (iyileşme, ama hâlâ yüksek) |
| Ortalama in-sample max DD | 2.23% | 1.82% | ~aynı |
| **DD kriteri sonucu (resmi)** | GEÇMEDİ | GEÇMEDİ | **değişmedi** |
| OOS DD / tam-dönem DD oranı | 0.96× | 2.48× | bkz. yorum aşağıda |
| **MC dd_p5 (worst-5%)** | -12.08% | **-10.29%** | ↓ (iyileşme) |
| MC kırmızı bayrağı | Tetiklendi | **Yine tetikleniyor** (bkz. aşağı) | değişmedi |
| Hayalet bar (elenen) | 0 (filtre yoktu) | **1** (EREGL, 2024-04-09) | yeni katman |
| Gözlenen maks. eşzamanlı pozisyon | 3 (limit=2 İHLAL EDİLDİ) | **2** (limit=2, İHLAL YOK) | **düzeltildi** |

*v6'da "2024-04-08" olarak anılan tarih, düzeltme öncesi ham UTC etiketiydi;
normalize edilince gerçek Istanbul günü **2024-04-09**'dur (DIAGNOSTICS_v6.md'nin
kendisi de bu eski etiketlemeyi kullanmıştı — bu rapor onu düzeltiyor).

## Maks. Drawdown: -%20.74 → -%6.71 — DIAGNOSTICS_v6.md Paket 1'in Doğrulanması

DIAGNOSTICS_v6.md Paket 1, v5/v6'nın -%20.74 max DD rakamının muhtemelen gerçek
olmadığını, EREGL'nin 2024-04-09 tarihli hayalet barı (piyasa tatildeyken
sentetik/hatalı veri, volume=0, OHLC=önceki kapanış) + engine'in o gün fiyat
verisi eksik olan açık pozisyonları sıfırlayan equity formülü kombinasyonunun
ürettiğini öngörmüştü. **Bu turun sonucu bu öngörüyü doğruluyor**: hayalet bar
filtrelenip equity formülü forward-fill'e çevrildikten sonra, tüm dönem max
drawdown **-%6.71**'e düştü — %10'luk breaker eşiğinin dahi altında.

**Doğrudan kanıt (bu turda ayrıca çalıştırılan bağımsız bir doğrulama):**
```
ghost bars removed: [{'symbol': 'EREGL', 'date': 2024-04-09, 'reason': 'tek-sembolde-var + volume=0 + OHLC≈onceki_kapanis (hayalet bar)'}]
n trades: 121
breaker_trips: []
```
**Breaker artık tüm dönem boyunca HİÇ tetiklenmiyor** (`breaker_trips=[]`) —
v6'daki tek tetiklenme, tamamen o veri+engine artefaktının bir sonucuymuş.

## max_open_positions İhlalinin Sıfırlandığının Kanıtı

DIAGNOSTICS_v6.md Paket 1'in ikinci bulgusu: v6'da (ve öncesinde) aynı gün 2+
aday onaylanabildiği için gözlenen eşzamanlı açık pozisyon sayısı, config'teki
`max_open_positions=2` limitini aşıp 3'e çıkabiliyordu (en az 3 bağımsız örnek:
2006-03-30, 2010-12-02→08, 2013-06-30).

Bu turda, aynı 12-sembol/tam-tarihçe verisiyle (`trace=` parametresiyle) doğrudan
ölçüldü:
```
max_open_positions limit: 2
gözlenen maks eşzamanlı: 2
ihlal günü sayısı: 0
```
**Tüm tarihçe boyunca (5.252+ gün) limit hiç aşılmadı** — düzeltme doğrulandı.

## Walk-Forward ve MC — Neden Hâlâ Kırmızı Bayrak Var

Tam-dönem max DD'nin -%6.71'e düşmesine rağmen, walk-forward kabul kriteri
**hâlâ GEÇMEDİ** ve MC kırmızı bayrağı **hâlâ tetikleniyor**. Bunlar farklı
bir olgudan kaynaklanıyor — veri/engine bug'larından değil:

- OOS max DD (-%16.65) tam-dönem max DD'nin (-%6.71) **2.48 katı** — walk-forward
  penceresinin kendi içinde, tam-dönem koşumdan bağımsız olarak ayrı bir kötü
  drawdown dönemi üretiyor (muhtemelen belirli bir pencerede seçilen gevşek
  parametrenin — örn. `adx_min=15` — o pencereye özgü kötü bir OOS sonucu
  vermesi; walk-forward'ın kendi mantığı, tam-dönem koşumdan ayrı çalışır).
  Bu, ayrı bir araştırma konusu — bu turun kapsamı dışında (hiçbir eşik
  değiştirilmedi).
- MC dd_p5 (-%10.29), gerçek trade dağılımının (121 trade, PF 1.07) permütasyon
  bazlı en kötü %5 senaryosu — hâlâ %10 breaker eşiğinin biraz üzerinde. v6'nın
  -%12.08'inden iyileşmiş olsa da, sınırın hemen üzerinde kalmaya devam ediyor.

**Sonuç**: motor/veri bug'larının düzeltilmesi tam-dönem sonuçları belirgin
iyileştirdi, ama walk-forward/MC'nin kırmızı bayrakları BAĞIMSIZ, gerçek
bulgular olarak duruyor — bunlar bug değil, stratejinin kendi zayıflığı
(gevşek parametrelerin bazı dönemlerde kötü performansı, ince trade dağılımının
MC'de risk göstermesi).

## Sembol Bazında ve Rejim Kırılımı

| Rejim | Trade Sayısı | Win Rate | Toplam R |
|---|---|---|---|
| bear | 2 | 0.00% | -0.79 |
| bull | 113 | 46.02% | 5.91 |
| sideways | 6 | 33.33% | -1.50 |

Bull rejim yoğunluğu: 113/121 (%93.4) — v6'nın %92.4'ü ile aynı seviyede
(değişmedi, beklenen — düzeltmeler rejim dağılımını etkilemez).

## Benchmark Kıyası (bilgilendirici)

| | Strateji | Endeks Al-Tut | Sadece Nakit |
|---|---|---|---|
| Toplam getiri | 2.03% | 3445.51% | 0.00% |
| CAGR | 0.10% | 19.02% | 0.00% |
| Maks. drawdown | -6.71% | -63.43% | 0.00% |
| Sharpe | 0.07 | 0.79 | 0.00 |

(Değişmedi — v6'daki gibi endeks al-tut, bu konservatif stratejiyi büyük farkla
geçiyor; bu, sermaye-koruma öncelikli tasarımın beklenen bir sonucu, CLAUDE.md
Bölüm 0.3'teki felsefeyle tutarlı.)

## Parametre Taraması (27 kombinasyon, düzeltilmiş veriyle)

Tüm kombinasyonların max drawdown'u artık tek haneli/düşük-çift-haneli aralıkta
(en kötüsü -%11.0, `atr=1.25,adx=20`) — v5/v6'daki bazı kombinasyonların
gösterdiği -%25'e varan drawdown'lar KAYBOLDU. Bu, DIAGNOSTICS_v6.md'nin
öngörüsünü DOĞRULUYOR: EREGL hayalet-bar artefaktı, parametre setinden bağımsız
olarak (veri kaynaklı olduğu için) TÜM sweep kombinasyonlarını aynı şekilde
etkiliyordu. Mevcut varsayılan (`atr=1.5, adx=25, min_rr=1.5/1.8`): max DD
-%6.71, PF 1.07, 121 trade — sweep'teki en iyi PF'ler (`atr=2.0,adx=20`: PF
1.23, `atr=1.25,adx=25`: PF 1.10) mevcut varsayılana yakın ama belirgin
üstün değil (komşu-sağlamlık ayrı bir walk-forward konusu, bu turda
DEĞERLENDİRİLMEDİ — sweep_results.csv'ye bakılabilir).

## KIRMIZI BAYRAKLAR (güncel, v7)

- [x] **Walk-forward kabul kriteri geçmedi** (OOS PF 0.75 < ~gerekli, OOS DD
      tam-dönemin 2.48 katı — bkz. yukarıdaki yorum, ayrı bir gerçek bulgu).
- [x] **Monte Carlo worst-5% (dd_p5=-%10.29), breaker eşiğini (%10) hafifçe
      aşıyor** — v6'dan (-%12.08) iyileşti ama sınırda kalıyor.
- [x] **Performans tek rejime yoğun** (bull %93.4).
- [ ] Trade sayısı çok az mı? Hayır (121).
- [x] **Düzeltilen iki motor bug'ı bu koşumda DOĞRULANDI**: equity forward-fill
      sayesinde breaker hiç tetiklenmedi (v6'daki tek tetiklenme bug kaynaklıydı);
      max_open_positions ihlali sıfıra indi.

## Benim (Claude Code) değerlendirmem

Bu tur, DIAGNOSTICS_v6.md'nin en kritik bulgusunu ampirik olarak doğruladı:
**v5/v6'nın -%20.74 max drawdown'u gerçek bir piyasa sonucu değil, bir veri
artefaktı + bir engine bug'ıydı.** Düzeltmeden sonra gerçek (bu stratejinin,
bu 12 sembol evreninde, 2005'ten bugüne, mevcut sıkı parametrelerle) max
drawdown'u **-%6.71** — breaker eşiğinin (%10) belirgin altında. Bu, önceki
tüm turların (v1-v6) "breaker gerçekleşmiş drawdown'u sınırlayamıyor" endişesini
büyük ölçüde ORTADAN KALDIRIYOR, çünkü o endişenin dayandığı -%20.74 rakamının
kendisi hatalıydı.

Ama iki bağımsız, gerçek zayıflık hâlâ duruyor: walk-forward OOS performansı
zayıf (PF 0.75, kabul kriterini geçmiyor) ve MC worst-5% senaryosu hâlâ breaker
eşiğine yakın. Bunlar motor/veri düzeltmesiyle iyileşti ama tamamen ortadan
kalkmadı — stratejinin kendi (gate seçimi, parametre seti) zayıflıkları olarak
duruyor. DIAGNOSTICS_v6.md Paket 3'ün gate ablasyon bulgusuyla (trend/regime/rsi
gate'lerinin izole ölçümde değer katmadığı görünümü) birlikte okunduğunda, bir
sonraki mantıklı adım muhtemelen gate/parametre yeniden tasarımı — ama bu,
kullanıcının kararı ve ayrı bir onaylı tur gerektiriyor.

**Karar benim değil, kullanıcının.** v7 tamamlandı. Faz 5'e geçmiyorum,
kullanıcı onayı bekliyorum.

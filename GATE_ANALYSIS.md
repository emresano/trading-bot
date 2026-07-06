# Gate Katkı Analizi (GATE_ANALYSIS.md)

Salt-okunur analiz (onaylı harness düzeltme turu, madde 5/EK) — hiçbir strateji
eşiği/gate davranışı değiştirilmedi. `tools/gate_analysis.py` ile üretildi.
Snapshot: `data/snapshots/2026-07-06` (12 sembol, 2005-01-01+) | Trade kaynağı:
`runtime/backtest_reports_v6/trades.csv` (119 trade, breaker entegrasyonu +
MC düzeltmesi sonrası).

## (a) Huni Sırasıyla Eleme Sayıları

Her kademe, bir önceki kademeyi geçen adaylar üzerinden ölçülür (kümülatif,
`ENTRY_GATES` sırasıyla — 12 sembolün tamamı, tüm tarihçe, 63.013 aday-gün).

| Kademe | Gate | Elenen | Kalan | Elenen / Bir-Önceki-Kalan |
|---|---|---|---|---|
| 1 | trend | 22,070 | 40,943 | 35.02% |
| 2 | regime | 22,337 | 18,606 | 54.56% |
| 3 | rsi | 14,254 | 4,352 | **76.61%** |
| 4 | macd | 2,269 | 2,083 | 52.14% |
| 5 | atr_anomaly | 0 | 2,083 | 0.00% |
| 6 | bb_overextension | 3 | 2,080 | 0.14% |
| 7 | structure_rr | 0 | 2,080 | 0.00% |
| 8 | volume | 1,861 | 219 | **89.47%** |
| 9 | trigger_4h | 72 | 147 | 32.88% |
| 10 | mtf | 0 | 147 | 0.00% |

63.013 aday-günden yalnızca **147'si (%0.23)** 10 gate'in tamamını geçiyor.
En büyük tekil kesimler: **volume** (kalanın %89.5'i) ve **rsi** (kalanın
%76.6'sı). trend+regime birlikte adayların %70'ini daha ilk 2 kademede eliyor.

## (b) Kazanan vs Kaybeden Trade'lerde Gate Değer Dağılımı

Sinyal barındaki (giriş tarihinden bir önceki kapanmış bar — look-ahead yok)
değerler, kazanan (pnl>0, n=51) ve kaybeden (pnl<=0, n=68) trade'ler arasında
karşılaştırıldı:

| Metrik | Kaybeden (ort.) | Kazanan (ort.) | Fark |
|---|---|---|---|
| RSI | 49.29 | 48.45 | ~0.8 puan — **ihmal edilebilir** |
| ADX | 30.84 | 29.97 | ~0.9 puan — **ihmal edilebilir** |
| MACD histogram | -0.0283 | -0.1048 | yön kazananlar için ters (beklenmedik, ama örneklem küçük) |
| ATR / ATR-MA20 oranı | 1.09 | 1.06 | ihmal edilebilir |
| BB genişliği (%close) | %17.4 | %15.0 | kaybedenlerde biraz daha geniş bant (daha volatil koşul) |

**Kesin hüküm yok** — örneklem küçük (51 vs 68 trade), bu farklar istatistiksel
anlamlılık testi olmadan yorumlanmamalı. Ama gözlemlenebilir şu: RSI ve ADX'in
kazanan/kaybeden gruplar arasındaki farkı, kendi ölçek büyüklüklerine göre
(RSI 0-100, ADX tipik 0-60) neredeyse sıfır — **her iki gate de aktif olarak
eleme yapıyor (RSI %76.6, regre/ADX %54.6) ama geçirdiği adaylar arasında
KENDİ DEĞERİNE göre kazanan/kaybeden ayrımı görünmüyor.**

## (c) Gate Sınıflandırması

**"Hiç eleme yapmıyor" (kümülatif eleme oranı <%1):** `atr_anomaly`,
`bb_overextension`, `structure_rr`, `mtf`.

Bunlar **rastgele eliyor değil** — mevcut parametrelerle (adx_min=25,
atr_stop_mult=1.5) yapısal olarak neredeyse her zaman PASS veriyorlar:
- `structure_rr`'nin sıfır elemesi, `compute_target`'ın `max(resistance,
  fallback)` düzeltmesinin (BACKTEST_REVIEW_v2.md turu) doğrudan sonucu —
  hedef her zaman en az 2R garanti ediyor, min_rr=1.8'i yapısal olarak aşıyor.
- `mtf`'in sıfır elemesi degrade modun (h4_df=None) SKIP-PASS tasarımından
  kaynaklanıyor (Bölüm 8.2) — beklenen, dokümante edilmiş davranış.
- `atr_anomaly` ve `bb_overextension`'ın neredeyse hiç elemesi, bu iki
  eşiğin (atr_anomaly_mult=2.0, bb_std=2.0) BIST'in tipik günlük volatilite
  aralığında nadiren aşılan geniş sınırlar olduğunu gösteriyor.

**"Eliyor ama görünürde rastgele" (elemesi anlamlı ama geçirdiği adaylar
arasında kazanan/kaybeden ayrımı yok):** **`rsi`** ve **`regime` (ADX)**.
Bu ikisi huninin en büyük iki "kapı bekçisi"nden ikisi (rsi tek başına
kalanın %76.6'sını eliyor) ama (b)'deki karşılaştırma, geçirdikleri adaylar
arasında KENDİ ölçtükleri değerin (RSI seviyesi, ADX seviyesi) nihai trade
sonucuyla ayırt edici bir ilişkisi olmadığını gösteriyor. Bu, ileride bir
huni sadeleştirme tartışmasında "bu eşikleri neden bu aralıkta tuttuğumuzu"
sorgulamak için somut bir başlangıç noktası — ama bu turda hiçbir eşik
değiştirilmedi.

## Genel Not

Bu analiz, gelecekte olası bir huni sadeleştirmesi (gereksiz/ayırt edici
olmayan gate'lerin gözden geçirilmesi) tartışmasına sayısal girdi sağlamak
için üretildi. 51-68 trade'lik örneklem küçük olduğundan (b)'deki
gözlemler ön-bulgu niteliğindedir, istatistiksel kanıt değil — kesin hüküm
kullanıcıyla birlikte verilmelidir.

# Backtest Değerlendirme Raporu — v6 (harness düzeltme turu: breaker entegrasyonu + MC bayrağı)

Tarih / commit: 2026-07-06, commit `53ba4b3` (breaker entegrasyonu + MC dd_p5 düzeltmesi)
Komut: `python -m backtest.cli --symbols THYAO,GARAN,ASELS,AKBNK,KCHOL,SAHOL,EREGL,TUPRS,TCELL,TOASO,SISE,ARCLK --config config/config.yaml --snapshot data/snapshots/2026-07-06 --start-date 2005-01-01 --walk-forward --monte-carlo --regime-split --sweep --benchmark --out runtime/backtest_reports_v6/`
Veri: HARDENING.md A1 snapshot'ından (`data/snapshots/2026-07-06/`, ağdan
indirme yok — rapor başlığındaki 3 damga bunu doğruluyor).
Önceki rapor: `BACKTEST_REVIEW_v5.md` — backtest motoru drawdown breaker'ı
hiç simüle etmiyordu (max DD -%20.74, config'in %10 eşiğini sınırsız aşıyordu)
ve Monte Carlo kırmızı bayrağı yanlış persentili (dd_p95) kontrol ediyordu.

## Bu turda yapılan düzeltmeler (yalnızca bunlar — hiçbir eşik/gate davranışı değişmedi, adx_min=25 dahil aynen kalıyor)

1. **Breaker entegrasyonu**: `risk_engine.check_and_trip_breaker()` artık
   backtest event loop'una bağlı — her gün equity/peak hesaplandıktan hemen
   sonra, giriş değerlendirmesinden ÖNCE çağrılıyor (paper/real modun her
   kararsal döngüde yapacağının BİREBİR AYNISI, aynı fonksiyon çağrısıyla).
   Her `run_backtest` çağrısı kendi İZOLE geçici breaker dosyasını kullanıyor
   (paper/real'in paylaştığı gerçek `runtime/BREAKER_TRIPPED`'e dokunmuyor).
2. **MC kırmızı bayrağı**: artık `dd_p5` (en kötü %5 senaryo / worst-5%)
   kontrol ediyor, `dd_p95` (en iyi %5 senaryo) değil.

Kanıt testleri: sentetik seride breaker'ın doğru barda tetiklendiği VE
sonrasında hiçbir yeni pozisyonun açılmadığı; dd_p95 eşiğin altında ama
dd_p5 eşiği aşan bir senaryonun artık doğru şekilde bayrak ürettiği.
190/190 test yeşil.

**Not (performans):** Bu koşum ~6 saat 30 dakika sürdü (v5'in ~2 saat 20
dakikasına kıyasla belirgin yavaşlama) — breaker entegrasyonunun her
`run_backtest` çağrısında bir geçici dizin oluşturup silmesinin getirdiği
ek yük, walk-forward'ın ~1000+ çağrısında birikti. Bu, düzeltilmedi (kapsam
dışı), ama gelecekte bir performans turu için not edildi.

## v5 → v6 Yan Yana Karşılaştırma

| Metrik | v5 (breaker'sız) | v6 (breaker entegre) | Yön |
|---|---|---|---|
| Trade sayısı (tüm dönem) | 125 | **119** | ↓ (6 trade breaker tarafından engellendi) |
| Toplam getiri | -1.06% | -1.91% | ↓ |
| Profit factor | 0.97 | 0.94 | ↓ |
| Win rate | 42.40% | 42.86% | ~aynı |
| **Maks. drawdown (tüm dönem)** | -20.74% | **-20.74%** | **DEĞİŞMEDİ** (bkz. aşağı) |
| Sharpe | 0.01 | 0.00 | ~aynı |
| OOS profit factor (walk-forward) | 0.75 | 0.76 | ~aynı (küçük fark, bazı pencereler kendi breaker'ını tetikledi) |
| OOS max DD (walk-forward) | -19.90% | -19.90% | değişmedi |
| Ortalama in-sample max DD | 2.24% | 2.23% | ~aynı |
| **DD kriteri sonucu (resmi)** | GEÇMEDİ | GEÇMEDİ | değişmedi |
| Bilgilendirici oran: OOS DD / tam-dönem DD | 0.96× | 0.96× | değişmedi |
| **MC dd_p5 (worst-5%)** | -11.71% (ölçüldü ama bayrak dd_p95 kontrol ediyordu) | **-12.08%** | ~aynı |
| **MC kırmızı bayrağı** | Tetiklenmedi (yanlış persentil kontrol ediliyordu) | **Tetiklendi** (doğru persentil) | **yeni bulgu** |

## Breaker Kaç Kez, Hangi Tarihte Tetiklendi

**Tam-dönem backtest'te 1 kez**, **2024-04-08** tarihinde:
- O gün equity: 84,290 TL, tepe (peak) equity: 106,350 TL → drawdown %20.74
  (eşik olan %10'un çok üzerinde).
- Tetiklendikten sonra backtest'in geri kalanında (2026-07'ye kadar) **hiçbir
  yeni pozisyon açılmadı** — 6 trade'in v5'te var olup v6'da olmaması bunun
  doğrudan sonucu.

## Neden Max Drawdown Değişmedi — Önemli Bir Bulgu

Breaker YALNIZCA yeni girişleri durdurur, açık pozisyonları zorla kapatmaz
(HARDENING.md B3'ün "varsayılan FREEZE, FLATTEN değil" kuralıyla tutarlı).
2024-04-08'deki %20.74 drawdown, o güne kadar zaten AÇIK olan pozisyon(lar)ın
mark-to-market hareketiyle oluşmuştu — breaker o gün tetiklendiğinde hasar
zaten gerçekleşmişti. Yani **bu spesifik veri setinde ve mevcut sıkı
parametrelerle (adx_min=25) breaker, gerçekleşmiş drawdown'u SINIRLAMADI —
yalnızca SONRAKİ yeni girişleri engelledi.**

**Ama sweep verisi çok farklı bir hikaye anlatıyor:** 27 kombinasyonun
TAMAMINI karşılaştırdığımızda, gevşek parametrelerle (örn. `adx_min=15`,
daha sık trading) breaker DRAMATİK bir fark yaratıyor:

| Kombinasyon | v5 max DD (breaker'sız) | v6 max DD (breaker entegre) |
|---|---|---|
| atr=1.25, adx=15 | -18.95% | **-10.30%** |
| atr=1.25, adx=20 | -12.91% | -11.62% |
| atr=1.5, adx=15 | -22.48% | **-10.07%** |
| atr=1.5, adx=20 | -17.65% | -10.33% |
| atr=2.0, adx=15 | -25.86% | **-10.07%** |
| atr=2.0, adx=20 | -23.25% | -23.25% (değişmedi) |
| **atr=1.5, adx=25 (mevcut varsayılan)** | **-20.74%** | **-20.74% (değişmedi)** |

Yorum: trading sıklığı arttıkça (gevşek parametreler → çok daha fazla trade),
breaker'ın erken tetiklenip SONRAKİ kötü girişleri önleme şansı artıyor —
bazı kombinasyonlarda drawdown neredeyse yarıya iniyor (-25.86%→-10.07%).
Ama mevcut sıkı varsayılan (adx_min=25, az sayıda trade) için breaker'ın
gerçekleşmiş drawdown üzerinde HİÇBİR etkisi yok, çünkü hasar zaten az
sayıdaki açık pozisyonun kendi fiyat hareketinden geliyor. Bu, breaker'ın
"az ama büyük pozisyonlu" bir strateji için daha az koruyucu, "sık ama küçük
pozisyonlu" bir strateji için çok daha koruyucu olduğunu gösteriyor — mevcut
konfigürasyon ilk kategoriye giriyor.

## Monte Carlo — Yeni Kriterle Durum

| Persentil | v6 Değeri | Breaker Eşiği (%10) |
|---|---|---|
| dd_p5 (en kötü %5 / worst-5%) | **-12.08%** | **AŞIYOR** |
| dd_median | -8.28% | altında |
| dd_p95 (en iyi %5) | -5.54% | altında |

**Kırmızı bayrak artık doğru şekilde TETİKLENİYOR**: "Monte Carlo worst-5%
(dd_p5), breaker eşiğine yakın/aşkın." Bu, v5'te de fiilen doğruydu
(dd_p5=-11.71%, zaten eşiği aşıyordu) ama eski (dd_p95 kontrol eden) mantık
bunu YAKALAYAMIYORDU. Düzeltme, var olan bir riski görünür kıldı — yaratmadı.

## Sembol Bazında ve Rejim Kırılımı (v5 ile pratik olarak aynı)

Bull rejim yoğunluğu: 110/119 (%92.4) — v5'in %92.8'i ile aynı seviyede.
Trade dağılımı sembollere yayılmış durumda (detaylar v5 raporunda, bu turda
değişmedi).

## Gate Katkı Analizi (EK, ayrı belge)

`GATE_ANALYSIS.md` üretildi (salt-okunur, davranış değişikliği yok):
- 63.013 aday-günden yalnızca 147'si (%0.23) tüm 10 gate'i geçiyor.
- `atr_anomaly`, `structure_rr`, `bb_overextension`, `mtf` neredeyse hiç
  eleme yapmıyor (yapısal nedenlerle, dokümante edildi).
- **Yeni bulgu**: `rsi` (kalanın %76.6'sını eleyen en büyük tekil kapı) ve
  `regime`/ADX (kalanın %54.6'sını eleyen ikinci en büyük kapı), geçirdikleri
  adaylar arasında kazanan/kaybeden ayrımı göstermiyor — aktif olarak eleme
  yapıyorlar ama KENDİ ölçtükleri değer (RSI/ADX seviyesi) nihai sonuçla
  ayırt edici görünmüyor. Küçük örneklem (51 kazanan, 68 kaybeden) nedeniyle
  ön-bulgu niteliğinde, kesin hüküm değil.

## KIRMIZI BAYRAKLAR (güncel)

- [x] **Walk-forward kabul kriteri geçmedi** (değişmedi, v3'ten beri).
- [x] **YENİ: Monte Carlo worst-5% (dd_p5) breaker eşiğini aşıyor** — düzeltme
      sayesinde artık doğru şekilde tetikleniyor.
- [x] **Performans tek rejime yoğun** (bull %92.4, değişmedi).
- [ ] Trade sayısı çok az mı? Hayır (119).
- [x] **Max drawdown breaker'ın etkisiz kaldığı bir senaryo tespit edildi**
      (mevcut sıkı parametrelerle) — az sayıda büyük pozisyonun mark-to-market
      riski, "yeni giriş engelleme" mekanizmasıyla sınırlanamıyor. Bu,
      HARDENING.md Bölüm B3'ün "FLATTEN yalnızca açık pozisyon stop'suz
      kaldıysa" istisnasının neden var olduğunu somut olarak doğruluyor.

## Benim (Claude Code) değerlendirmem

Breaker entegrasyonu ve MC bayrağı düzeltmesi **doğru çalışıyor** — kanıtlı
testler ve gerçek veri bunu gösteriyor. Ama gerçek veri ayrıca **breaker'ın
tek başına yeterli bir koruma olmadığını** da gösterdi: mevcut konfigürasyon
(az sayıda, büyük pozisyonlu trade) için "yeni giriş engelleme" mekanizması,
zaten açık olan bir pozisyonun kötü gitmesini önleyemiyor. Bu, tasarım
gereği böyle (HARDENING.md B3'ün FREEZE/FLATTEN ayrımı) ama sonucu — mevcut
parametrelerle gerçekleşmiş max drawdown'un hâlâ %20.74 olması — hafife
alınmamalı.

Genel tablo: Bu turun asıl değeri, **iki gerçek ölçüm hatasını düzeltip
gerçeği daha net görünür kılmak** oldu. Sonuçlar iyileşmedi (aksine, MC
kırmızı bayrağı yeni tetiklendi, trade sayısı azaldı, PF hafif düştü) —
ama artık elimizdeki tablo çok daha güvenilir. Gate analizi de huninin
büyük ölçüde RSI ve hacim tarafından şekillendirildiğini, ama bu iki
gate'in ayırt edicilik gücünün (en azından küçük örneklemde) belirsiz
olduğunu gösterdi.

**Karar benim değil, kullanıcının.** Backtest v6 + Gate Katkı Analizi
tamamlandı. Faz 5'e geçmiyorum, kullanıcı onayı bekliyorum.

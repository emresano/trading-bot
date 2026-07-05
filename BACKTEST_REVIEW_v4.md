# Backtest Değerlendirme Raporu — v4 (onaylı revizyon: adx_min sıkılaştırma)

Tarih / commit: 2026-07-05, commit `d6ea8fc` (adx_min: 20→25, tek izole değişiklik)
Komut: `python -m backtest.cli --symbols THYAO,GARAN,ASELS --config config/config.yaml --walk-forward --monte-carlo --regime-split --sweep --out runtime/backtest_reports_v4/`
Veri aralığı: 2000-05-09 → 2026-07-02 (~26 yıl), degrade mod (h4_df=None) — v1-v3 ile aynı.
Önceki rapor: `BACKTEST_REVIEW_v3.md` — walk-forward artık gerçek bir OOS ölçümü
üretiyordu, ama DD kriteri geçmedi (OOS max DD, kabul eşiğinin ~5.66 katı).

## Bu turda yapılan değişiklik (yalnızca bu — başka hiçbir eşik/parametre/kod davranışı değişmedi)

`config/config.yaml`: `signal.adx_min: 20` → `25`. Gerekçe: v2/v3'te gözlemlenen
eğilim — sweep verisinde `adx_min` sıkılaştıkça profit factor iyileşiyordu.

Ek (rapor-iyileştirme, davranış değişikliği değil): `backtest/cli.py`'nin
walk-forward bölümüne bilgilendirici bir satır eklendi — "Birleşik OOS max DD /
tam-dönem in-sample max DD" oranı. Bu satır **kabul kriterine dahil değil**;
`passed` hesabı hâlâ yalnızca `avg_in_sample_max_drawdown × 1.5` eşiğine
dayanıyor, değişmedi.

159/159 test yeşil (davranış değişikliği yok, yalnızca config değeri + 2 yeni
raporlama satırı).

## v3 → v4 Yan Yana Karşılaştırma

| Metrik | v3 (adx_min=20) | v4 (adx_min=25) | Yön |
|---|---|---|---|
| Trade sayısı (tüm dönem) | 89 | **47** | ↓ (daha seçici) |
| Toplam getiri | 4.17% | 4.68% | ↑ |
| CAGR | 0.16% | 0.18% | ↑ |
| Maks. drawdown (tüm dönem) | -3.78% | **-2.71%** | ↑ (iyileşti) |
| Sharpe | 0.14 | 0.20 | ↑ |
| Win rate | 38.20% | **46.81%** | ↑ |
| Profit factor | 1.20 | **1.48** | ↑ |
| Expectancy | 46.89 TL/trade | 99.53 TL/trade | ↑ |
| **OOS profit factor (walk-forward)** | 1.13 | **1.13** | değişmedi |
| **OOS max DD (walk-forward)** | -6.37% | **-6.37%** | değişmedi |
| Ortalama in-sample max DD (walk-forward) | 0.75% | 0.75% | değişmedi |
| **DD kriteri sonucu (resmi)** | GEÇMEDİ | **GEÇMEDİ** | değişmedi |
| Bilgilendirici oran: OOS DD / tam-dönem DD | ~1.69× | **2.35×** | ↓ (kötüleşti) |

**Neden walk-forward sayıları birebir aynı:** Walk-forward'ın 27-kombinasyonluk
grid taraması zaten `adx_min ∈ {15, 20, 25}`'in hepsini her pencerede ayrı ayrı
dener (`apply_params` her kombinasyonda cfg'nin varsayılanını override eder) —
yani walk-forward'ın sonucu, config.yaml'daki "varsayılan" `adx_min` değerinden
zaten bağımsızdır. Bu, `sweep_results.csv`'nin de v3 ile bayt-bayt aynı
çıkmasıyla doğrulandı. **Yalnızca ANA backtest (tek bir sabit parametre
setiyle, tüm tarihçe üzerinde tek geçiş) etkilendi** — beklenen ve doğru
davranış.

## Bilgilendirici oranın kötüleşmesi — neden ve ne anlama geliyor

OOS max DD sabit kaldı (-6.37%, walk-forward etkilenmediği için), ama
tam-dönem in-sample max DD iyileşti (-3.78%→-2.71%, payda küçüldü) — bu da
oranı **1.69×'ten 2.35×'e yükseltti.** Bu, "adx_min sıkılaştırma stratejiyi
daha güvenli yaptı" hikayesini karmaşıklaştırıyor: ana backtest tek başına
daha iyi görünüyor, ama walk-forward'ın yakaladığı OOS-kırılganlığı (in-sample
DD'ye kıyasla orantısız kötü OOS DD) aslında **göreli olarak büyüdü**, çünkü
in-sample referans daha da "sakin" hale geldi. Bu satır kabul kriterine dahil
değil ama gözden kaçırılmaması gereken bir uyarı işareti.

## Trade sayısı kontrolü (istenen kırmızı bayrak kontrolü)

**47 ≥ 30 — trade sayısı eşiğin altına düşmedi, bu kırmızı bayrak tetiklenmedi.**
Ama v3'ün 89'undan v4'ün 47'sine düşüş (%47 azalma), örneklemin daha da
inceldiğini gösteriyor; 26 yıl/3 sembolde 47 trade hâlâ istatistiksel olarak
ince bir taban.

## Rejim Kırılımı — bull yoğunluğu değişti mi?

| Rejim | v3 (adx_min=20) | v4 (adx_min=25) |
|---|---|---|
| bull | 81/89 (%91.0) | 42/47 (**%89.4**) |
| bear | 1/89 (%1.1) | 1/47 (%2.1) |
| sideways | 7/89 (%7.9) | 4/47 (%8.5) |

**Bull yoğunluğu pratikte değişmedi** (%91.0 → %89.4, ~1.6 puanlık fark,
gürültü seviyesinde). Sıkılaştırma, trade sayısını ve kalitesini (PF, win
rate) iyileştirdi ama rejim-konsantrasyonu sorununu çözmedi — strateji hâlâ
neredeyse tamamen bull rejiminde çalışıyor, bear'da anlamlı bir test hâlâ yok
(1 trade). Bull rejimindeki toplam R de orantılı düştü (8.14→7.38), win rate
ise iyileşti (37.04%→45.24%).

## Monte Carlo

| Persentil | v3 | v4 |
|---|---|---|
| dd_p5 | -7.81% | **-4.68%** |
| dd_median | -5.18% | -3.03% |
| dd_p95 | -3.47% | -2.01% |

Monte Carlo'nun kötü-senaryo ucu (dd_p5) belirgin iyileşti (-7.81%→-4.68%),
breaker eşiğinden (%10) daha güvenli bir mesafede. Bu, ana backtest'in
iyileşmesiyle tutarlı.

## KIRMIZI BAYRAKLAR (güncel)

- [x] **Walk-forward kabul kriteri geçmedi** (değişmedi) — DD kriteri hâlâ
      başarısız, OOS max DD hâlâ -6.37%, bilgilendirici oran kötüleşti (2.35×).
- [ ] **Trade sayısı 30'un altına düştü mü?** HAYIR — 47 ≥ 30. Ayrı kırmızı
      bayrak olarak istenmişti, tetiklenmedi.
- [x] **Performans tek rejime yoğun** (değişmedi) — bull %89.4, pratikte v3
      ile aynı.
- [x] **4H degrade dönem karşılaştırması N/A** (v1'den taşındı, değişmedi).

## Benim (Claude Code) değerlendirmem

Sıkılaştırma, **ana backtest'i** her ölçütte iyileştirdi: daha az ama daha
kaliteli trade (47, PF 1.48, win rate %46.8), daha düşük drawdown (-2.71%),
daha iyi Monte Carlo kötü-senaryo profili. Ama iki şey değişmedi/kötüleşti:

1. **Walk-forward'ın DD kriteri hâlâ geçmiyor** — çünkü walk-forward zaten
   `adx_min=25`'i kendi grid'inde deniyordu, config'teki varsayılanı
   değiştirmek walk-forward sonucunu etkilemedi. Overfitting bulgusu (v3'te
   tespit edilen) hâlâ geçerli ve çözülmedi.
2. **Bilgilendirici OOS/in-sample DD oranı kötüleşti** (1.69×→2.35×) — ana
   backtest'in "sakinleşmesi", walk-forward'ın gösterdiği kırılganlığı göreli
   olarak daha çarpıcı hale getirdi.
3. **Bull-rejim konsantrasyonu çözülmedi** (%91→%89, gürültü seviyesinde) —
   sıkılaştırma trade kalitesini artırdı ama stratejinin rejim-bağımlılığını
   azaltmadı.

Özetle: **tek bir backtest çalıştırıp bakıldığında** (walk-forward'sız) v4, v3'ten
belirgin biçimde daha iyi görünüyor. Ama walk-forward'ın (v3'te düzeltilen,
şimdi güvenilir) OOS ölçümü hâlâ aynı "hayır" cevabını veriyor — ve bu tek
parametre değişikliğiyle iyileşmedi, çünkü walk-forward zaten bu parametreyi
kendi arama uzayının bir parçası olarak deniyordu. Bu, **adx_min sıkılaştırmanın
walk-forward'ın tespit ettiği temel overfitting sorununu çözen bir müdahale
olmadığını**, yalnızca tek-geçişlik (in-sample) görünümü iyileştiren bir
müdahale olduğunu gösteriyor.

**Karar benim değil, kullanıcının.** Backtest v4 tamamlandı, BACKTEST_REVIEW_v4.md
hazır. Faz 5'e geçmiyorum, kullanıcı onayı bekliyorum.

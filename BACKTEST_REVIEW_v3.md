# Backtest Değerlendirme Raporu — v3 (walk-forward test-harness düzeltmesi)

Tarih / commit: 2026-07-05, commit `60a6d3f` (walk-forward test-harness bug düzeltmesi)
Komut: `python -m backtest.cli --symbols THYAO,GARAN,ASELS --config config/config.yaml --walk-forward --monte-carlo --regime-split --sweep --out runtime/backtest_reports_v3/`
Veri aralığı: 2000-05-09 → 2026-07-02 (~26 yıl), degrade mod (h4_df=None) — v1/v2 ile aynı.
Önceki rapor: `BACKTEST_REVIEW_v2.md` — strateji artık 89 trade üretiyordu (iki hedefli
düzeltme sayesinde), ama walk-forward'ın 48 penceresinin TAMAMINDA OOS trade sayısı
sıfırdı — bir test-harness kusuru tespit edilmişti, bu turda o kusur düzeltildi.

## Bu turda yapılan düzeltme (yalnızca bu — hiçbir eşik/parametre değişmedi)

`backtest/walkforward.py`, her pencerede `build_features`'ı YALNIZCA o pencerenin
veri dilimi üzerinde hesaplıyordu. Test dilimi (`test_months=6` ay ≈ 131 işlem
günü) `min_history_bars=260`'ın altında kaldığından, her test dilimi huniye hiç
girmeden elleniyordu — 48/48 pencerede OOS trade sayısı sıfırdı.

**Düzeltme:** `backtest/engine.py`'ye `date_range` ve `precomputed_features`
parametreleri eklendi. `build_features` artık TAM tarihçe üzerinde **bir kez**
hesaplanıyor (sweep grid'in 3 parametresi — `atr_stop_mult`, `adx_min`, `min_rr`
— indikatör hesaplamasını etkilemediğinden tüm kombinasyonlar aynı özellik
DataFrame'ini güvenle paylaşıyor). `min_history_bars` kontrolü artık dilimlenmiş
pencereye değil **tam tarihçedeki mutlak konuma** göre uygulanıyor; `date_range`
yalnızca hangi barların simüle edileceğini kısıtlıyor. Bir test dilimindeki gün,
kendinden önceki tam tarihçeyi (train dönemi dahil) warm-up olarak kullanabiliyor
— bu look-ahead değil, yalnızca geçmişe bakıyor.

Kanıt testi (`tests/test_backtest_engine.py::test_date_range_restricts_simulation_but_uses_full_history_for_warmup`):
kendi başına `min_history_bars`'tan (15) çok kısa bir pencerede (3 gün) bile,
öncesindeki tam tarihçe warm-up olarak kullanıldığından bir trade üretilebildiğini
kanıtlıyor. 159/159 test yeşil.

## Etki: Walk-Forward artık gerçekten çalışıyor

| | v2 (bozuk harness) | v3 (düzeltilmiş) |
|---|---|---|
| OOS trade üreten pencere sayısı | 0 / 48 | **23 / 48** |
| Toplam OOS trade (pencereler toplamı) | 0 | **54** |
| Komşu-sağlamlık kriterini geçen pencere | 0 / 48 (anlamsız, hiç ölçülmedi) | **23 / 48** |
| Birleşik OOS profit factor | 0.00 (ölçülemedi) | **1.13** |
| Birleşik OOS max DD | 0.00% (ölçülemedi) | **-6.37%** |
| Kabul kriteri (Bölüm 12.5) | GEÇMEDİ (anlamsız) | GEÇMEDİ (**şimdi gerçek bir ölçüm**) |

**Ana tam-dönem backtest, rejim kırılımı, Monte Carlo ve 27-kombinasyonluk sweep
sonuçları v2 ile bayt-bayt aynı** (`trades.csv` `diff` ile doğrulandı) — bu
düzeltme yalnızca walk-forward'ı etkiledi, beklendiği gibi başka hiçbir şeye
dokunmadı.

## Walk-Forward — şimdi anlamlı bir ölçüm

- 48 pencerenin 23'ünde en az 1 OOS trade üretildi (dağılım: 0'dan 7'ye kadar).
- **Birleşik OOS profit factor: 1.13** — Bölüm 12.5'in `> 1.1` eşiğini **geçiyor**.
- **Birleşik OOS max DD: -6.37%**
- **Kabul kriteri sonucu: GEÇMEDİ** — `passed = pf_ok AND dd_ok` olduğundan ve
  `pf_ok` (1.13 > 1.1) sağlandığından, başarısızlık mantıksal olarak **dd_ok**
  kriterinden geliyor (OOS max DD, ortalama in-sample max DD'nin 1.5 katından
  kötü). Tam sayısal `avg_in_sample_max_drawdown` değeri şu an raporda ayrıca
  basılmıyor (`cli.py`'nin walk-forward bölümü bunu şu an satıra yazmıyor) —
  bunu görmek için ~30 dakikalık walk-forward'ı tekrar koşturmak yerine, bunu
  bir sonraki küçük bir rapor-geliştirme olarak öneriyorum (eşik/davranış
  değişikliği değil, yalnızca zaten hesaplanan bir sayının basılması).

**Yorum:** Bu, v2'deki "GEÇMEDİ" ile aynı ibare olsa da anlamı tamamen farklı.
v2'de bu ibare bir ölçüm hatasıydı (hiç veri yoktu). v3'te bu, **gerçek bir OOS
ölçümü** ve gerçek bir bulgu: strateji, in-sample'da gördüğü drawdown'a kıyasla
OOS'ta orantısız derecede kötü drawdown yaşıyor — overfitting'in klasik
belirtisi. Kabul kriterinin PF tarafını geçmesi (1.13) cesaret verici, ama DD
tarafının başarısız olması, walk-forward'ın seçtiği parametrelerin train
döneminde görünenden daha kırılgan olduğunu gösteriyor.

## Özet metrikler (tüm dönem — v2 ile aynı, değişmedi)

| Metrik | Değer |
|---|---|
| Toplam getiri | 4.17% |
| CAGR | 0.16% |
| Maks. drawdown | -3.78% |
| Sharpe | 0.14 |
| Win rate | 38.20% |
| Profit factor | 1.20 |
| Trade sayısı | 89 |

## Rejim kırılımı (v2 ile aynı)

81/89 trade bull rejiminde (toplam R +8.14); bear'da yalnızca 1 trade.
Bu bulgu ve ona bağlı kırmızı bayrak (v2'de belirtildiği gibi) hâlâ geçerli.

## Monte Carlo (v2 ile aynı)

dd_p5=-7.81%, dd_median=-5.18%, dd_p95=-3.47%. Breaker eşiği (%10) altında
ama yakın.

## KIRMIZI BAYRAKLAR (güncel)

- [x] **Walk-forward kabul kriteri geçmedi** — ama artık **gerçek bir ölçüme
      dayanıyor** (v2'deki gibi bir harness artefaktı değil). OOS profit factor
      kriteri geçti (1.13>1.1); drawdown kriteri geçmedi. Bu, parametrelerin
      train döneminde görünenden daha kırılgan olabileceğine işaret ediyor.
- [x] **Performans tek rejime yoğun** (v2'den taşındı, değişmedi).
- [ ] **Trade sayısı çok az mı?** Ana backtest için hayır (89≥30). OOS
      tarafında 54 trade / 23 pencere — ince ama artık ölçülebilir.
- [x] **4H degrade dönem karşılaştırması N/A** (v1/v2'den taşındı, değişmedi).

## Benim (Claude Code) değerlendirmem

Walk-forward artık gerçekten çalışıyor ve gerçek bir bulgu üretti: **strateji
in-sample'da göründüğünden daha kırılgan** — OOS drawdown, in-sample drawdown'a
oranla beklenenden kötü. Bu, önceki "0 trade" ya da "bozuk harness" durumlarından
çok daha değerli bir sinyal, çünkü artık gerçek bir overfitting emaresiyle
karşı karşıyayız, bir ölçüm boşluğuyla değil.

Toparlarsak, üç aşamalı bu revizyon sürecinin sonunda elimizdeki tablo:
1. **Motor doğru çalışıyor** (v1'den beri: look-ahead yasağı, determinizm,
   stop-önceliği, komisyon/slippage — hepsi test kanıtlı).
2. **Sinyal hunisi artık gerçekten trade üretiyor** (v2: iki hedefli düzeltme,
   0→89 trade, hafif pozitif PF).
3. **Walk-forward artık gerçekten OOS doğruluyor** (v3: harness düzeltmesi,
   0→23/48 pencerede trade) — **ve bu doğrulama stratejinin zayıf yönünü
   ortaya çıkardı**: DD kriterinde başarısız.

Bu noktada Faz 5'e geçmeyi önermiyorum — walk-forward'ın kendisi net bir
"hayır" diyor (DD kriteri geçmedi), ve bu artık güvenilir bir ölçüme dayanıyor.
Olası yollar:
- **(A)** `avg_in_sample_max_drawdown` sayısını rapora ekleyip (küçük, davranış
  değiştirmeyen bir iyileştirme) tam görüntüyü netleştir, sonra karar ver.
- **(B)** Sweep'in gösterdiği eğilimi (adx_min sıkılaştırma, v2'de gözlemlendi)
  ayrı bir onaylı revizyon turunda dene — daha az ama daha kaliteli trade,
  potansiyel olarak DD kriterini de iyileştirebilir.
- **(C)** Mevcut haliyle kabul etmeyip stratejiyi bu şekliyle terk et / yeniden
  tasarla.

**Karar benim değil, kullanıcının.** Backtest v3 tamamlandı, BACKTEST_REVIEW_v3.md
hazır. Faz 5'e geçmiyorum, kullanıcı onayı bekliyorum.

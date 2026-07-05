# Backtest Değerlendirme Raporu — v2 (revizyon turu)

Tarih / commit: 2026-07-05, commit `67d2dd6` (iki hedefli düzeltme sonrası)
Komut: `python -m backtest.cli --symbols THYAO,GARAN,ASELS --config config/config.yaml --walk-forward --monte-carlo --regime-split --sweep --out runtime/backtest_reports_v2/`
Veri aralığı: 2000-05-09 → 2026-07-02 (~26 yıl), degrade mod (h4_df=None) — v1 ile aynı.
Önceki rapor: `BACKTEST_REVIEW.md` (v1) — 0 trade, hiçbir metrik değerlendirilebilir değildi.

## Bu turda yapılan düzeltmeler (yalnızca bu ikisi — başka hiçbir eşiğe dokunulmadı)

1. **`compute_target()`**: hedef artık `max(nearest_resistance, entry + 2×(entry-stop))`.
   Gerekçe: pullback girişinde en-yakın-direnç tanım gereği girişe yakındır; onu
   doğrudan hedef almak R:R'yi yapısal olarak neredeyse her zaman düşürüyordu.
2. **`gate_trigger_4h()` degrade mod genişletmesi**: tetik artık "son 3 barda mum
   formasyonu OLUŞTU **VEYA** bugünkü kapanış önceki barın high'ının üstünde"
   ise geçerli. Gerçek 4H modu (h4_df dolu) davranışı değişmedi.

**Ölçülen etki (gate_diagnostics.py ile önce/sonra karşılaştırma):**

| Gate | v1 kümülatif geçiş | v2 kümülatif geçiş |
|---|---|---|
| structure_rr (kademe 7) | %0.23 | **%6.95** (kademe 6'dan kayıpsız) |
| trigger_4h (kademe 9) | **%0.00** (3 sembolde de tam sıfır) | %0.52 |

## Özet metrikler (tüm dönem, varsayılan parametreler: atr_stop_mult=1.5, adx_min=20, min_rr=1.8)

| Metrik | v1 | v2 |
|---|---|---|
| Toplam getiri | 0.00% | **4.17%** |
| CAGR | 0.00% | **0.16%** |
| Maks. drawdown | 0.00% | **-3.78%** |
| Sharpe | 0.00 | **0.14** |
| Win rate | — | **38.20%** |
| Profit factor | — | **1.20** |
| Ortalama R-multiple | — | **0.07** |
| Expectancy | — | **46.89 TL/trade** |
| Trade sayısı | **0** | **89** |
| Nakitte kalma oranı | %100 | **%93.6** |

Trade sayısı artık Bölüm 15'in "istatistiksel anlam için <30" eşiğinin üstünde
(89 ≥ 30) — bu kırmızı bayrak otomatik olarak düştü.

**Dürüst okuma:** Strateji artık ölçülebilir, ama sonuç güçlü değil. 26 yılda
%4.17 toplam getiri, yıllık %0.16 CAGR'a denk düşüyor — enflasyon/fırsat
maliyeti bir kenara, pratikte "sıfıra çok yakın, hafif pozitif" bir performans.
Sharpe 0.14 çok düşük. Asıl olumlu sinyal profit factor'ün 1'in üzerinde olması
(1.20) — kazananlar kaybedenlerden ortalama daha büyük — ama win rate %38 ile
"sık kazanmayan, seyrek büyük kazanan" trend-takip profiline uyuyor.

## Rejim kırılımı

| Rejim | Trade Sayısı | Win Rate | Toplam R |
|---|---|---|---|
| bull | 81 | 37.04% | **+8.14** |
| sideways | 7 | 57.14% | -1.99 |
| bear | 1 | 0.00% | -0.32 |

**Performans neredeyse tamamen bull rejimine yoğunlaşmış** (81/89 trade,
toplam R'nin tamamı oradan geliyor). Bear rejiminde yalnızca 1 trade var —
stratejinin düşüş piyasalarında nasıl davrandığına dair pratikte hiç veri yok
(gate_trend zaten close>ema_slow şartı koştuğu için bu felsefi olarak tutarlı:
strateji zaten düşüş rejiminde long pozisyon aramıyor — ama bu aynı zamanda
"tüm getiri tek rejime yoğun mu" kırmızı bayrağının doğrudan EVET olduğu
anlamına geliyor).

## Walk-Forward — ⚠️ metodolojik bir sorun tespit edildi

**48 pencerenin TAMAMINDA test (OOS) trade sayısı sıfır** — bu, düzeltmelerin
başarısız olduğu anlamına gelmiyor; araştırdım ve nedeni buldum:

`backtest/walkforward.py`, her pencerede `build_features`'ı YALNIZCA o pencerenin
veri dilimi üzerinde sıfırdan hesaplıyor (Faz 4'te bilinçli bir basitleştirme
olarak dokümante edilmişti). Test dilimi `test_months=6` ay ≈ **~131 işlem günü**.
`config.yaml`'daki `min_history_bars=260` şartı nedeniyle, `run_backtest` içindeki
`all_dates` hesaplaması yalnızca `len(df) > min_history_bars` olan sembolleri
dahil ediyor — 131 < 260 olduğundan **her test dilimi, her sembol için, huniye
hiç girmeden baştan eleniyor.** Bu, train dilimleri için sorun değil (24 ay ≈
~500 gün > 260), yalnızca test dilimlerini etkiliyor.

**Sonuç: Bölüm 12.5'in "OOS profit factor > 1.1" kabul kriteri, bu iki raporda
(v1 ve v2) da GEÇERLİ biçimde hiç ölçülmedi** — "GEÇMEDİ" sonucu stratejinin
genelleme yapamadığını göstermiyor, test harness'inin OOS değerlendirmesini
hiç çalıştıramadığını gösteriyor. Bu, bugünkü iki düzeltmeden bağımsız,
Faz 4'ten kalma bir kapsam eksikliği; bugünün "tek revizyon turu" kuralı
gereği **düzeltmedim**, sadece tespit edip raporluyorum. Öncelikli bir sonraki
adım olarak öneriyorum: `build_features`'ı tam tarihçe üzerinde bir kez
hesaplayıp pencereleri SONRADAN dilimlemek (ya da `test_months`'u
`min_history_bars`'ı aşacak kadar büyütmek — ama bu, Bölüm 6'nın
`walk_forward.test_months=6` değerini değiştirmeyi gerektirir, yani ayrı bir
onay konusu).

Walk-forward'ın TRAIN tarafı (parametre seçimi) çalıştı — 48 pencerenin
~18'inde komşu-sağlamlık kriterini geçen bir kombinasyon bulundu (`robust=True`)
— ama seçilen parametrenin gerçekten iyi olup olmadığı hiç test edilemediğinden
bu bilgi de sınırlı değerde.

## Monte Carlo

| Persentil | Değer |
|---|---|
| dd_p5 (kötü senaryo) | **-7.81%** |
| dd_median | -5.18% |
| dd_p95 (iyi senaryo) | -3.47% |

`max_drawdown_breaker_pct = %10` eşiğiyle karşılaştırıldığında: dd_p5 (-7.81%)
eşiğin altında kalıyor ama **eşiğin %78'ine kadar yaklaşıyor** — rahat bir marj
yok. Trade sırası kötü giderse (permütasyonla simüle edilen senaryolardan
biri), breaker'ın canlıda tetiklenmesi olası bir ihtimal.

## Parametre Taraması (27 kombinasyon, tam tarihçe)

Yalnızca ölçüm — bu turda hiçbir parametre değiştirilmedi. Gözlem: `adx_min`
sıkılaştıkça (20→25) profit factor iyileşiyor (1.20→1.48) ama trade sayısı
azalıyor (89→47). `adx_min=15` (gevşek) daha çok trade (130-135) ama profit
factor'ü 1'in altına düşürüyor (0.91-1.11) — yani rejim filtresi gerçekten
işe yarıyor gibi görünüyor. Bu bir gözlem, öneri değil — kullanıcı onayı
olmadan hiçbir eşik değiştirilmedi.

## KIRMIZI BAYRAKLAR (dürüstçe)

- [x] **Performans tek rejime yoğun mu?** EVET — 89 trade'in 81'i (%91) bull
      rejiminde; bear rejiminde pratikte hiç veri yok (1 trade).
- [ ] **Seçilen parametrenin komşuları çöküyor mu?** Değerlendirilemedi
      (walk-forward'ın OOS tarafı yukarıdaki nedenle çalışmadı); ANCAK
      tam-tarihçe sweep'te komşu kombinasyonlar (adx_min 15/20/25,
      atr_stop_mult 1.25/1.5/2.0) tutarlı bir yön gösteriyor (sıkılaştıkça
      PF artıyor, gevşedikçe düşüyor) — bu, izole bir spike değil, kademeli
      bir eğilim; overfitting işareti değil.
- [x] **OOS, in-sample'dan belirgin kötü mü?** Ölçülemedi — walk-forward
      metodoloji sorunu nedeniyle OOS hiç üretilemedi (yukarıda detaylı).
- [ ] **MC dd_p95, breaker eşiğine yakın/aşkın mı?** dd_p5 (-7.81%), eşiğin
      (%10) altında ama %78'ine kadar yaklaşıyor — sınırda, izlenmeli.
- [ ] **Trade sayısı istatistiksel anlam için çok mu az (<30)?** HAYIR —
      89 ≥ 30. Ama 26 yıl / 3 sembol için 89 trade (~1.1 trade/sembol/yıl)
      hâlâ ince bir örneklem; güven aralıkları geniş olacaktır.
- [x] **4H degrade dönem sonuçları tam-veri dönemden anlamlı sapıyor mu?**
      Hâlâ N/A — tüm dönem degrade modda koştu (bu turda değişmedi).
- [x] **YENİ — Walk-forward test harness'i yapısal olarak bozuk** (yukarıda
      detaylandırıldı) — bu rapordaki "Kabul kriteri: GEÇMEDİ" ibaresi
      yanıltıcı olabilir, gerçek bir ölçüm değil.

## Benim (Claude Code) değerlendirmem

İki hedefli düzeltme işe yaradı — huni artık gerçekten trade üretiyor (0→89) ve
sonuç hafif pozitif (PF 1.20, toplam getiri +%4.17). Ama bu, "kanıtlanmış kârlı
bir strateji" değil: CAGR (%0.16/yıl) neredeyse anlamsız küçük, Sharpe (0.14)
zayıf, performans neredeyse tamamen bull rejimine ve THYAO/ASELS ağırlıklı
(GARAN daha az trade) bir döneme yoğunlaşmış. En önemlisi, **walk-forward'ın
OOS doğrulaması hiç çalışmadığı için stratejinin gerçekten "genelleştiğine"
dair elimde hâlâ bağımsız bir kanıt yok** — yalnızca in-sample (tüm tarihçe
üzerinde, aynı veriyle hem tasarlanıp hem test edilen) bir sonuç var.

Bu durumda üç makul yol görüyorum:
- **(A)** Walk-forward test-harness bug'ını düzelt (build_features'ı tam
  tarihçede bir kez hesaplayıp dilimlemek) ve GERÇEK bir OOS ölçümü elde
  ettikten sonra tekrar değerlendir — Faz 5'e geçmeden önce bunu önerdiğim
  öncelikli adım olarak görüyorum.
- **(B)** Mevcut haliyle (in-sample kanıtla) kabul edip Faz 5'e geç — ama bu,
  "backtest'ten geçmemiş bir parametre setini deploy etme" ilkesine (Bölüm 0.2)
  teknik olarak aykırı olabilir, çünkü OOS doğrulaması fiilen hiç yapılmadı.
  Ben bunu önermiyorum.
- **(C)** Sweep'in gösterdiği eğilimi (adx_min sıkılaştırma) ayrı bir onaylı
  revizyon turunda dene.

**Karar benim değil, kullanıcının.** Backtest v2 tamamlandı, BACKTEST_REVIEW_v2.md
hazır. Faz 5'e geçmiyorum, kullanıcı onayı bekliyorum — bu turda ek eşik
değişikliği yapmadım (talimat gereği).

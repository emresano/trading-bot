# Backtest Değerlendirme Raporu

Tarih / commit: 2026-07-05, commit `abfab2c` (Faz 4 tamamlandı)
Komut: `python -m backtest.cli --symbols THYAO,GARAN,ASELS --config config/config.yaml --walk-forward --monte-carlo --regime-split --sweep --out runtime/backtest_reports/`
Veri aralığı: 2000-05-09 → 2026-07-02 (~26 yıl, THYAO/GARAN/ASELS günlük barları, yfinance)
Mod: **tamamen degrade** (h4_df=None) — Faz 4 kapsamında gerçek 4H entegrasyonu bilinçli olarak
ertelendi (STATUS.md'de gerekçelendirildi); huninin tamamı günlük kademelerle çalıştı.

## Seçilen parametre seti ve gerekçe

**Ana rapor, config.yaml'daki varsayılan parametrelerle koştu** (`atr_stop_mult=1.5`,
`adx_min=20`, `min_rr=1.8`) — bu kombinasyon **26 yıllık tüm tarihçede tam olarak 0 trade
üretti.** Dolayısıyla "komşu-sağlamlık kanıtıyla seçilmiş bir parametre seti" burada
sunulamıyor: seçilecek bir şey yok, çünkü hiçbir işlem gerçekleşmedi.

Walk-forward'ın kendi iç grid taraması (her pencere için ayrı ayrı) genellikle en gevşek
uçtaki kombinasyonu (`atr_stop_mult=1.25, adx_min=15, min_rr=1.5`) seçti — ama bu seçim
**hiçbir pencerede** komşu-sağlamlık kriterini geçemedi (`robust=False`, 48 pencerenin
tamamında). Yani model "en iyi görüneni" bulmaya çalıştı ama bulduğu şey 0-1 trade'lik
gürültüden ibaret, sağlam bir sinyal değil.

Ek diyagnostik: üst düzey `--sweep` (27 kombinasyon, tam tarihçe üzerinde) çıktısı
(`runtime/backtest_reports/sweep_results.csv`) şunu gösteriyor: `adx_min` gevşetildikçe
(20→15) ve `atr_stop_mult` küçüldükçe (2.0→1.25) az sayıda trade (1-3 adet) ortaya çıkıyor;
`adx_min=25` veya `atr_stop_mult=2.0` gibi daha sıkı/geniş kombinasyonlarda trade sayısı
tamamen sıfıra iniyor. Bu, huninin darlığının belirli bir gate'e değil, 10 koşulun
**aynı anda** sağlanması gerekliliğine dayandığını doğruluyor — 27 kombinasyonun HİÇBİRİ
3'ten fazla trade üretmedi.

## Özet metrikler (tüm dönem, varsayılan parametreler)

| Metrik | Değer |
|---|---|
| Toplam getiri | 0.00% |
| CAGR | 0.00% |
| Maks. drawdown | 0.00% |
| Sharpe | 0.00 |
| Win rate | 0.00% (trade yok) |
| Profit factor | 0.00 (trade yok) |
| Ortalama R-multiple | 0.00 |
| Expectancy | 0.00 TL/trade |
| Trade sayısı | **0** |
| Nakitte kalma oranı | **%100** |

## Rejim kırılımı

Uygulanamadı — 0 trade olduğundan bull/bear/sideways kırılımı için veri yok.

## Walk-forward

- Pencere sayısı: 48 (train=24 ay, test=6 ay, step=6 ay; 2000-05 → 2026-05 arası)
- Robust (komşu-sağlamlık kriterini geçen) pencere sayısı: **0 / 48**
- Test (OOS) dilimlerinin trade sayısı: tüm pencerelerde **0**
- Birleşik OOS profit factor: 0.00
- Birleşik OOS max DD: 0.00%
- **Kabul kriteri (Bölüm 12.5): GEÇMEDİ** (OOS profit factor > 1.1 şartı sağlanamadı —
  çünkü hiç OOS trade'i yok)

## Monte Carlo

Uygulanamadı (anlamlı biçimde) — permüte edilecek trade getiri serisi boş olduğundan
`dd_p5 = dd_median = dd_p95 = 0.00%` döndü. Bu, "düşük risk" anlamına gelmiyor; sadece
"hiç pozisyon açılmadı, dolayısıyla hiç drawdown riski gerçekleşmedi" anlamına geliyor.

## KIRMIZI BAYRAKLAR (dürüstçe)

- [x] **Trade sayısı istatistiksel anlam için çok mu az (<30)?** EVET — 0 trade.
      Bu, listedeki en ciddi bayrak: strateji fiilen hiç test edilmedi.
- [x] **Performans tek rejime/tek yıla mı yoğun?** Değerlendirilemez (trade yok).
- [x] **Seçilen parametrenin komşuları çöküyor mu (overfitting işareti)?** Tersine bir
      bulgu: walk-forward'ın seçtiği "en iyi" kombinasyonlar zaten hiçbir pencerede
      komşu-sağlamlık testini geçemedi (48/48 robust=False) — bu, overfitting'in kendisi
      değil, "anlamlı bir sinyal yok" bulgusunun bir başka görünümü.
- [x] **OOS, in-sample'dan belirgin kötü mü?** Her ikisi de sıfır/anlamsız; karşılaştırma
      yapılamıyor.
- [ ] **MC dd_p95, breaker eşiğine yakın/aşkın mı?** Hayır (0.00%, ama yalnızca trade
      olmadığı için — yanlış güven vermemeli).
- [x] **4H degrade dönem sonuçları tam-veri dönemden anlamlı sapıyor mu?** N/A —
      **tüm dönem degrade modda koştu** (gerçek 4H entegrasyonu bu fazda uygulanmadı,
      bkz. STATUS.md). Bu karşılaştırma hiç yapılamadı; ayrı bir bilinen sınırlama olarak
      not edildi, kırmızı bayrak listesindeki orijinal soru cevaplanamıyor.

## Kod tarafı doğrulamalar (bunlar başarılı — sorun stratejide, motorda değil)

Bunlar backtest motorunun DOĞRU çalıştığına dair kanıt, stratejinin karlı olduğuna dair
kanıt değil:
- Look-ahead yasağı: sentetik testlerde giriş/çıkışın her zaman sinyal barından bir
  sonraki barın açılışında gerçekleştiği doğrulandı (`tests/test_backtest_engine.py`).
- Determinizm: aynı komut iki kez çalıştırıldığında `report.md`/`trades.csv`/
  `sweep_results.csv` bayt-bayt aynı çıktı (`tests/test_backtest_cli.py`).
- Stop-önceliği, komisyon/slippage uygulanması, fill mekaniği: sentetik senaryolarla
  doğrulandı.
- 142/142 birim/entegrasyon testi yeşil.

## Benim (Claude Code) değerlendirmem

Motor doğru ve dürüst çalışıyor; sorun motorun kendisinde değil, **Faz 2'de tasarlanan
sinyal hunisinin aşırı seçici olması.** 10 gate'in TÜMÜNÜN aynı anda sağlanması
gerekliliği (trend + rejim + RSI bandı + MACD + ATR anomali + Bollinger + R:R + hacim +
mum formasyonu + MTF uyum), 26 yıllık günlük veri + 27 parametre kombinasyonunun
TAMAMINDA en fazla 3 trade üretti. Bu, CLAUDE.md'nin "sermaye koruma > getiri" felsefesi
açısından bir bakıma tutarlı (asla kötü bir işlem yapmıyor çünkü hemen hiç işlem
yapmıyor) ama pratik açıdan **değerlendirilebilir bir strateji değil** — 0 trade'lik bir
backtest ne "iyi" ne "kötü"dür, sadece "yok"tur.

Bunun olası nedenleri (öncelik sırasıyla, spec'i bozmadan araştırılabilir):
1. **RSI bandı (40-55) çok dar** — trend-takip + pullback stratejisinde makul bir
   aralık, ama ADX≥20 (güçlü trend) ile RSI 40-55 (nötr/hafif pullback) aynı anda
   gerçekleşmesi istatistiksel olarak seyrek bir kesişim.
2. **MACD "above_signal OR hist_rising" ile RSI bandının kesişimi** dar bir pencere.
3. **Gate sırası/AND mantığı**: 10 koşulun HİÇBİRİ "yeterli çoğunluk" değil, hepsi
   zorunlu — bu bilinçli bir tasarım kararıydı (Bölüm 8.2), ama sonucu bu.
4. Degrade modun mum formasyonu ve MTF-skip mantığı, gerçek 4H verisiyle koşulsa
   farklı (muhtemelen biraz daha sık) sinyal üretebilir — ama bu, sorunun büyüklüğünü
   (26 yılda <5 trade) açıklayacak ölçekte değil.

**Karar benim değil, kullanıcının.** Üç somut yol var:
- **(A)** Huniyi olduğu gibi kabul edip Faz 5'e geç — bot fiilen çok uzun süre nakitte
  kalacak, bu Bölüm 0.3'ün "nakitte kal birinci sınıf bir karardır" ilkesiyle tutarlı,
  ama pratik fayda tartışmalı.
- **(B)** Gate eşiklerini gözden geçir (örn. RSI bandını genişlet, ADX eşiğini düşür) —
  bu, Bölüm 0.2'nin "risk limitlerini kullanıcı onayı olmadan gevşetmeme" kuralına
  girmez (RSI/ADX sinyal eşiği, risk limiti değil) ama yine de mimari bir strateji
  değişikliği olduğundan kullanıcı onayı istiyorum.
- **(C)** Daha fazla sembol/enstrüman ekle (BIST30'un geri kalanı, altın) — trade
  sayısını artırabilir ama huninin darlığı sorununu gizler, çözmez.

Backtest tamamlandı, BACKTEST_REVIEW.md hazır. Faz 5'e geçmiyorum, kullanıcı onayı
bekliyorum.

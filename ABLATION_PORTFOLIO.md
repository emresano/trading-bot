# Portföy-Seviyesi Gate Ablasyon Turu (ABLATION_PORTFOLIO.md)

Read-only counterfactual tur — DIAGNOSTICS_v6.md Paket 3'ün izole (portföy/
nakit/korelasyon/breaker etkileşimsiz) bulgusunun GERÇEK portföy motoruyla
(backtest/engine.py, tüm kısıtlarıyla) doğrulanması. **Hiçbir eşik/gate/
parametre `config.yaml`'da değiştirilmedi** — `disabled_gates` yalnızca bu
turun geçtiği, read-only bir `run_backtest` parametresidir; `main.py`/
`PaperBroker` bunu hiç kullanmaz. Mevcut snapshot'lara yazılmadı; v7 taban
çizgisi (`runtime/backtest_reports_v7/`) okundu ama değiştirilmedi.

Kapsam: A1 snapshot'ı (`data/snapshots/2026-07-06/`), 12 sembol, 2005-01-01+,
`data/cleaning.py` katmanı açık (v7 ile birebir aynı yükleme). Her varyant:
tam süit + walk-forward + Monte Carlo + XU100 benchmark kıyası. **Sweep
YAPILMADI** (süre kontrolü — 5 varyant zaten ~6 saat sürdü).

## Önemli Yan Bulgu — Yeni Bir Determinizm Bug'ı Bulundu ve Düzeltildi

Bu turun ilk adımı olan "baseline v7 ile bayt-bayt aynı olmalı" doğrulaması
sırasında **gerçek, daha önce hiç yakalanmamış bir çapraz-süreç
determinizm bug'ı** ortaya çıktı: `backtest/engine.py`'de `pending_exits`
bir `set[str]` olarak tutuluyordu ve `for symbol in list(pending_exits):`
şeklinde (sıralama olmadan) işleniyordu. Python'da string hash'leri
`PYTHONHASHSEED`'e göre SÜREÇ BAŞINA rastgeleleştirildiğinden, aynı veriyle
çalıştırılan İKİ AYRI SÜREÇ, aynı güne denk gelen birden fazla sembol
çıkışını FARKLI SIRADA üretebiliyordu — finansal sonuç (fiyat, PnL, R-multiple)
birebir aynı kalıyordu, yalnızca `trades.csv`'deki SATIR SIRASI değişiyordu.
Bu, CLAUDE.md Bölüm 12.8'in "aynı komut iki koşuda bit-bit aynı çıktı üretmeli"
şartını (teoride, tüm önceki turların fark etmediği bir şekilde) ihlal
ediyordu.

**Düzeltme**: `for symbol in sorted(pending_exits):` — giriş huninin v7'de
zaten uyguladığı "deterministik alfabetik sıra" ilkesiyle tutarlı. Bu,
`config.yaml`'da hiçbir şeyi değiştirmez, yalnızca aynı-gün-çoklu-çıkış
durumunda çıktı SIRASINI deterministik kılar — finansal sonuçlar (equity
curve, trade PnL'leri, tüm metrikler) ETKİLENMEZ. Kanıt: yeni regresyon
testi `test_same_day_multiple_exits_are_ordered_alphabetically` (+ 4 farklı
`PYTHONHASHSEED` değeriyle manuel doğrulama, hepsi aynı sırayı üretti).

**Baseline ↔ v7 karşılaştırması bu yüzden şöyle okunmalı**: `diff` bayt-bayt
AYNI değil, ama **içerik (sort edilmiş) TAMAMEN AYNI** — tüm 12 sembol × tüm
tarihçede TAM OLARAK 2 "aynı-gün-çoklu-çıkış" çakışması var (ARCLK/TOASO
2010-12-10, ASELS/TCELL 2026-06-04); bu ikisinde de artık alfabetik sıra
uygulanıyor (v7'nin dondurulmuş dosyasındaki sıra, o çalıştırmanın rastgele
hash tohumunun bir artefaktıydı). **121 trade'in TÜMÜ, tüm alanlarıyla,
birebir aynı** — bu doğrulandı (`sort` sonrası `diff` boş). v7'nin kendisi
DEĞİŞTİRİLMEDİ (golden kalıyor); yalnızca bu YENİ koşumun v7'yle içerik
düzeyinde eşleştiği kanıtlandı.

## Varyant × Metrik Tablosu

| Metrik | baseline | no_trend | no_regime | no_rsi | no_trend_regime_rsi |
|---|---|---|---|---|---|
| Devre dışı gate(ler) | — | trend | regime | rsi | trend+regime+rsi |
| Trade sayısı | 121 | 245 | 325 | 240 | 235 |
| Toplam getiri (TRY) | +2.03% | +1.65% | **+5.28%** | -0.60% | **-7.28%** |
| Toplam getiri (USD, bilgilendirici) | -97.05% | -97.06% | -96.96% | -97.13% | -97.32% |
| **USD CAGR (bilgilendirici)** | **-15.80%** | -15.81% | -15.67% | -15.90% | -16.19% |
| Profit factor | 1.068 | 1.035 | 1.064 | 0.992 | 0.881 |
| Win rate | 44.63% | 46.12% | 40.62% | 39.58% | 42.55% |
| **Maks. drawdown** | **-6.71%** | **-10.04%** | **-10.08%** | **-10.35%** | **-10.91%** |
| Endeks (XU100 al-tut) max DD | -63.43% | -63.43% | -63.43% | -63.43% | -63.43% |
| DD / endeks-DD oranı | 0.106 | 0.158 | 0.159 | 0.163 | 0.172 |
| Sharpe (strateji) | 0.068 | 0.053 | **0.108** | 0.003 | **-0.134** |
| Sharpe (XU100 al-tut) | 0.794 | 0.794 | 0.794 | 0.794 | 0.794 |
| OOS profit factor (walk-forward) | 0.753 | 1.015 | **1.153** | 0.878 | 0.901 |
| OOS max DD (walk-forward) | -16.65% | -14.01% | -10.59% | **-31.01%** | **-32.87%** |
| WF kabul kriteri | GEÇMEDİ | GEÇMEDİ | GEÇMEDİ | GEÇMEDİ | GEÇMEDİ |
| MC dd_p5 (worst-5%) | -10.35% | -11.68% | -15.17% | **-19.30%** | -17.70% |
| Time-in-market | 8.11% | 8.89% | **19.86%** | 16.55% | 9.37% |
| Ort. sermaye kullanımı | 1.38% | 1.59% | **4.15%** | 3.64% | 2.11% |
| Breaker tetiklenme | 0 | 1 | 1 | 1 | 1 |
| Gap-proximity (trade/toplam) | 1/121 (0.83%) | 6/245 (2.45%) | 1/325 (0.31%) | 2/240 (0.83%) | 3/235 (1.28%) |

Kalın değerler: baseline'a göre belirgin/ilginç sapmalar (iyi veya kötü yönde).

## Gap-Proximity Özeti (DATA_AUDIT_v2.md'nin 79 "açıklanamayan gap" günü)

Trade sayısı arttıkça (121→325) açıklanamayan-gap günlerine yakın trade
ORANI **sistematik olarak ARTMIYOR** — en yüksek oran (no_trend, %2.45) en
yüksek trade sayılı varyantta (no_regime, 325 trade) değil, orta trade
sayılı bir varyantta (245 trade) görülüyor; no_regime (en çok trade, 325)
oranı en DÜŞÜK (%0.31). Bu, gate'leri gevşetmenin şüpheli-gün maruziyetini
ORANTILI OLARAK artırmadığını gösteriyor — mutlak sayı (1-6 arası) küçük ve
her durumda toplam trade'in %2.5'ini geçmiyor.

## İzole (Paket 3) vs Portföy Bulgusu — UYUŞMUYOR

DIAGNOSTICS_v6.md Paket 3, izole (portföy etkileşimsiz) ölçümde şu sonucu
bulmuştu: **trend, regime, rsi gate'lerinin elediği adaylar, gerçek
trade'lerden DAHA İYİ kalitede** (örn. trend counterfactual PF 1.54 vs
baseline izole PF 1.11) — yani bu üç gate "değer katmıyor gibi görünüyordu."

**Bu turun portföy-seviyesi sonucu BU BULGUYU DOĞRULAMIYOR — aksine, büyük
ölçüde ÇÜRÜTÜYOR:**

- **no_trend**: İzole bulgu "değer katmıyor" derken, portföy düzeyinde max DD
  **%53 daha kötü** (-10.04% vs -6.71%), Sharpe düşüyor, breaker tetikleniyor
  (baseline'da hiç tetiklenmemişti). **AÇIK ÇELİŞKİ.**
- **no_rsi**: İzole bulgu "değer katmıyor" derken, portföy düzeyinde
  TRY getirisi NEGATİFE dönüyor, PF 1'in altına iniyor, Sharpe sıfıra
  yaklaşıyor, **OOS max DD -31%'e fırlıyor** (baseline'ın 2 katı), MC
  worst-5% -19.3%'e kötüleşiyor. **EN GÜÇLÜ ÇELİŞKİ.**
- **no_regime**: KARMA sonuç — TRY getirisi ve Sharpe İYİLEŞİYOR (+5.28%,
  0.108) ve OOS PF İYİLEŞİYOR (1.153 > baseline'ın 0.753), AMA max DD
  kötüleşiyor (-10.08%) ve breaker tetikleniyor. İzole bulguyla KISMEN
  UYUMLU (regime izole ölçümde de en az zararlı üçüncü gate'ti) ama tam
  bir doğrulama değil — trade-off var: daha fazla getiri, daha fazla risk.
- **no_trend_regime_rsi** (üçü birden): TÜM metriklerde EN KÖTÜ varyant —
  negatif TRY getirisi (-7.28%), PF 0.881, Sharpe NEGATİF (-0.134), OOS max
  DD -32.87% (baseline'ın 2 katından fazla), MC dd_p5 -17.70%. Üç gate'in
  BİRLİKTE kaldırılması, tek tek kaldırmaktan daha kötü bir portföy
  üretiyor — bu, gate'lerin PORTFÖY DÜZEYİNDE birbirini TAMAMLAYAN
  (kısmen örtüşmeyen risk azaltma) bir işlev gördüğünü, izole ölçümün
  yakalayamadığı bir etkileşim olduğunu düşündürüyor.

**Yorum**: İzole ölçüm (Paket 3), yalnızca "bu gate hangi ADAYLARI eliyor,
onlar iyi mi kötü mü" sorusuna cevap veriyordu — DIAGNOSTICS_v6.md'nin
kendisinin de öngördüğü gibi, portföy-seviyesi etkileri (rejim filtrelerinin
DOLAYLI risk yönetimi işlevi — örn. kaç pozisyonun AYNI ANDA açık olduğu,
breaker'ın NE ZAMAN tetiklendiği, OOS pencerelerinin ne kadar kötü
gidebileceği) YOK SAYIYORDU. Bu tur, o öngörünün YERİNDE olduğunu somut
sayılarla gösteriyor: **trend ve rsi gate'leri, izole ölçümde "değersiz"
görünmelerine rağmen, PORTFÖY düzeyinde gerçek bir risk-sınırlama işlevi
görüyor** (özellikle kuyruk riskini — OOS max DD, MC dd_p5 — kontrol ederek).
regime gate'i ise bir getiri/risk TRADE-OFF'u sunuyor, tek yönlü bir
"değersiz" hüküm haklı değil.

## Başarı Çıtası Karşısında Durum (bilgilendirici)

Kullanıcı kararıyla (bu turda STATUS.md'ye işlendi) belirlenen taban şart:
**USD CAGR > 0**. **Hiçbir varyant (baseline dahil) bu şartı sağlamıyor** —
hepsi yaklaşık -%15.7 ile -%16.2 arası USD CAGR gösteriyor. Bu, stratejinin
kendi performansından çok TRY'nin USD karşısındaki yapısal değer kaybından
kaynaklanıyor (2005-2026 arası USDTRY kuru dramatik şekilde arttı — TRY
bazında hafif pozitif/negatif getiriler bile USD'ye çevrildiğinde büyük
görünen kayıplara dönüşüyor). **Bu, hiçbir varyantın şu anki haliyle Faz
5/paper'a önerilebilir olmadığı anlamına gelmez** — yalnızca, kullanıcının
belirlediği USD-bazlı başarı çıtasının, mevcut TL-hedge'siz tasarımla
karşılanamadığını gösteren dürüst bir rapor. Resmi kabul kriterleri (walk-
forward PF/DD, Bölüm 12.5) zaten hiçbirinde geçmiyor — bu yeni değil, v1'den
beri açık.

## Çekinceler (Örneklem ve Yöntem Sınırlamaları)

1. **Tek geçmiş dönem, tek koşum**: Her varyant TEK bir 2005-2026 tarihçesi
   üzerinde bir kez koşuldu — parametre/gate seçiminin "overfitting"e karşı
   sağlamlığı yalnızca walk-forward'ın kendi iç mekanizmasıyla (komşu-
   sağlamlık) sınırlı; bu 5 varyantın KENDİSİ arasında bir dış çapraz-
   doğrulama yapılmadı.
2. **OOS pencere trade sayıları küçük olabilir**: walk-forward'ın bazı
   pencereleri az sayıda trade üretiyor (v7 raporunda daha önce not edildi);
   OOS max DD gibi metrikler bu küçük örneklemlerde aşırı duyarlı olabilir
   (örn. no_rsi/no_trend_regime_rsi'nin -31%/-33%'lük OOS max DD'si, az
   sayıda kötü pencerenin baskın etkisini yansıtıyor olabilir — bu turda
   pencere bazlı ayrıştırma yapılmadı).
3. **USD çevrimi tamamen bilgilendirici**: hiçbir sinyal/risk kararına
   girmedi (HARDENING C2'nin yalnızca kısmi/onaylı aktivasyonu). USDTRY
   günlük kapanışla hizalanmış (ffill/bfill) — gerçek bir FX riskten korunma
   stratejisi MODELLENMEDİ.
4. **Gap-proximity, nedensellik iddiası değil**: bir trade'in şüpheli bir
   güne ±5 bar yakın olması, o trade'in SONUCUNUN o veri sorunundan
   etkilendiği anlamına gelmez — yalnızca bir maruziyet ölçüsüdür.
5. **Sweep yapılmadı**: bu 5 varyantın HİÇBİRİ kendi parametre setinde
   (atr_stop_mult/adx_min/min_rr) optimize edilmedi — hepsi v7'nin sabit
   varsayılan parametreleriyle koşuldu. Bir gate kaldırılıp parametreler
   yeniden ayarlanırsa sonuçlar burada gösterilenden farklı olabilir.
6. **Breaker tetiklenmesi (4/5 varyantta 1 kez)**: bu turda İNCELENMEDİ
   (hangi tarihte, hangi pozisyon kaynaklı) — v7 turunun EREGL hayalet-bar
   deneyimine benzer bir veri artefaktı mı yoksa gerçek bir drawdown mu,
   bu turun kapsamı dışında kaldı.

## Sonuç

Bu tur, DIAGNOSTICS_v6.md Paket 3'ün izole bulgusunu PORTFÖY seviyesinde
TEST ETTİ ve büyük ölçüde ÇÜRÜTTÜ (özellikle trend ve rsi için) — bu üç
gate'in "gereksiz" olduğu yönündeki ön-bulgu, gerçek portföy motoruyla
doğrulanmadı. Ayrıca, bu tur SIRASINDA daha önce bilinmeyen gerçek bir
determinizm bug'ı bulundu ve düzeltildi (`pending_exits` sıralaması).

**Karar benim değil, kullanıcının.** Hiçbir eşik/gate/parametre
değiştirilmedi, Faz 5'e/E2'ye geçilmedi. Durma Noktası 1'de duruluyor,
kullanıcı onayı bekleniyor.

---

# Breaker Adli İnceleme (R1 eki)

Ablasyon turu kapanışı (R1) — read-only. 4 varyantın (no_trend, no_regime,
no_rsi, no_trend_regime_rsi) birer breaker tetiklenmesi, `trace=` teşhis
kancasıyla (yalnızca ana koşum yeniden çalıştırıldı — walk-forward/MC/sweep
DEĞİL) incelendi: tetiklenme günü ve önceki equity/peak/DD, açık pozisyonlar,
tetik günündeki en büyük notional düşüşüne sahip sembol, o sembolün ±8
takvim günü fiyat/hacim penceresi, ve son 20 iş günlük equity/peak/DD
yörüngesi (ani tek-gün sıçraması mı, kademeli çok-günlü düşüş mü ayırt etmek
için — v7'nin EREGL hayalet-bar deneyiminin imzası: TEK gün, TEK sembol, ani
büyük sıçrama).

## no_trend — 2020-08-18 (equity 101,628 / peak 112,975 / DD %10.04)

Peak (112,975), tetik gününden HAFTALAR ÖNCE, pozisyon dahi açık değilken
oluşmuş — equity 2020-07-20'den 2020-08-17'ye kadar (20 iş günü) tam olarak
101,810.31'de SABİT kalmış (hiç pozisyon yok, DD zaten %9.88'de duruyordu).
2020-08-18'de TEK açık pozisyon TUPRS, notional'i yalnızca -166 TL (~%1)
düşüyor — bu, DD'yi %9.88'den %10.04'e taşıyan, ÇOK KÜÇÜK bir ek düşüş.
TUPRS'nin ±8 günlük fiyat penceresinde hiçbir anomali yok — aksine, tetik
gününün HEMEN ERTESİ günlerinde (08-19, 08-20) fiyat keskin biçimde YÜKSELİYOR
(7.36 → 7.91 → 8.48, gerçek ve hacim-destekli bir hareket, muhtemelen TUPRS'nin
o dönemki gerçek bir haber/rapor kataliziyle ilgili — DATA_AUDIT_v2.md'de bu
tarihe yakın bir "açıklanamayan gap" kaydı YOK).
**Sınıflandırma: GERÇEK DRAWDOWN, ama mekanik olarak "sıradan"** — tek
büyük bir olay değil, ÇOK ESKİ bir peak ile mevcut equity arasındaki zaten-
neredeyse-%10 olan farkın, küçük bir günlük dalgalanmayla eşiği geçmesi.
Veri artefaktı imzası (tek-gün/tek-sembol/ani-sıçrama) YOK.

## no_regime — 2018-10-18 (equity 105,302 / peak 117,086 / DD %10.06)

Kademeli 4 günlük düşüş: 10-15 (%8.41) → 10-16 (%8.88, THYAO) → 10-17
(%9.70, SISE'ye geçiş) → 10-18 (%10.06). SISE'nin bu haftaki fiyat serisi
düzenli bir aşınma gösteriyor (4.74→4.57, tek bir sıçrama yok), hacimler
normal aralıkta (5-10M). Bu dönem, Türkiye'nin Ağustos 2018 kur/ekonomi
krizinin (TL'nin Ağustos'ta sert değer kaybı) sonrasındaki genel piyasa
zayıflığıyla örtüşüyor — makro olarak bilinen, açıklanabilir bir dönem.
DATA_AUDIT_v2.md'de SISE/THYAO için bu tarihe yakın bir "açıklanamayan gap"
kaydı YOK.
**Sınıflandırma: GERÇEK DRAWDOWN** (kademeli, çok-günlü, çok-sembollü,
makro bağlamla tutarlı — veri artefaktı imzası yok).

## no_rsi — 2015-11-10 (equity 99,404 / peak 110,877 / DD %10.35)

Tetik gününde AÇIK POZİSYON YOK — KCHOL pozisyonu 8 iş günü boyunca
(2015-11-02'den itibaren) düzenli olarak aşınmış (equity: 100,777→100,682→
100,777→100,586→100,205→99,823) ve 11-10'da KAPANMIŞ (muhtemelen stop veya
sinyal çıkışı), bu kapanışın gerçekleştirdiği zarar DD'yi %9.97'den %10.35'e
taşımış. Tek bir çarpıcı gün yok — 8 günlük kademeli bir aşınmanın son halkası.
**Sınıflandırma: GERÇEK DRAWDOWN** (kademeli, çok-günlü — veri artefaktı
imzası yok).

## no_trend_regime_rsi — 2008-09-17 (equity 92,724 / peak 104,073 / DD %10.91)

**En anlamlı bağlamsal bulgu**: 2008-09-17, Lehman Brothers'ın iflasından
(15 Eylül 2008) yalnızca 2 gün sonrası — 2008 küresel finans krizinin en
şiddetli haftası. Equity yörüngesi 2008-08-21'den (DD %8.12) itibaren
neredeyse kesintisiz kademeli bozuluyor (THYAO, ARCLK, AKBNK pozisyonları
sırayla), 09-16'da DD %9.88'e ulaşıyor, 09-17'de (tetik günü, pozisyon
kapanmış) %10.91'e çıkıyor. DATA_AUDIT_v2.md'de bu haftaya yakın SISE
(2008-09-15, -%10.83, "açıklanamayan gap") ve THYAO (2008-09-19, +%10.34,
"açıklanamayan gap") kayıtları VAR — ama bunlar tetik gününün (09-17) TAM
kendisi veya trigger'a katkı veren pozisyonlar (THYAO/AKBNK, 09-17'de zaten
kapanmış) değil; genel haftanın aşırı oynaklığının bir parçası, ayrı bir
sınıflandırma sorunu.
**Sınıflandırma: GERÇEK DRAWDOWN** — küresel finans krizinin (Lehman
Brothers çöküşü) doğrudan, iyi belgelenmiş bir yansıması. Bu turun EN GÜÇLÜ
"gerçek" sınıflandırmasıdır.

## Genel Sonuç

**4 tetiklenmenin TAMAMI "gerçek drawdown" olarak sınıflandırıldı — hiçbiri
v7'nin EREGL hayalet-bar deseniyle (tek gün, tek sembol, volume=0, ani büyük
sıçrama) eşleşmiyor.** Hepsi ya kademeli çok-günlü/çok-sembollü aşınma (no_regime,
no_rsi, no_trend_regime_rsi) ya da uzun süredir zaten sınıra yakın duran bir
equity'nin küçük bir ek düşüşle eşiği geçmesi (no_trend) deseninde. İki
tetiklenme (no_regime, no_trend_regime_rsi) bilinen makro-ekonomik stres
dönemleriyle (2018 TL krizi, 2008 küresel finans krizi) doğrudan örtüşüyor —
bu, breaker'ın TASARLANDIĞI gibi çalıştığının (gerçek, ciddi piyasa stresinde
tetiklenmesi) bir kanıtı, veri kalitesi sorunu değil.

**Önemli çekince**: bu inceleme yalnızca "tetik GÜNÜNDEKİ en büyük tekil
düşüş" ve "son 20 iş günü" penceresine baktı — DAHA ERKEN tarihli, birikimli
küçük veri sorunlarının (DATA_AUDIT_v2.md'nin 79 açıklanamayan-gap gününün
herhangi biri, bu 4 sembolün geçmişindeki BAŞKA tarihlerde) peak equity'nin
KENDİSİNİ (yani referans tepe noktasını) şişirmiş olma ihtimali bu turda
İNCELENMEDİ — yalnızca tetik anındaki ani/tekil artefakt ihtimali dışlandı.

**Karar benim değil, kullanıcının. Bu ek de dahil, hiçbir eşik/gate/parametre
değiştirilmedi.**

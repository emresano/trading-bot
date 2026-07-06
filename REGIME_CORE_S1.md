# S1 — Rejim-Filtreli Çekirdek Spike Backtest'i (REGIME_CORE_S1.md)

D1 tasarımının (STATUS.md KALICI KAYIT 3) tek-tur DEĞERLENDİRME spike'ı.
**Bu bir üretim implementasyonu DEĞİLDİR** — kabul edilirse gerçek
implementasyon ayrı bir onaylı turda, "backtest=canlı aynı fonksiyon"
ilkesiyle yeniden yapılır.

**Bağımsızlık kanıtı**: `backtest/regime_core.py` (yeni, bağımsız simülatör)
`backtest/engine.py`, `strategy/`, `risk/`, `config/config.yaml`'a
DOKUNMADI/BAĞIMLI DEĞİL — `git diff` bu dosyaların hiçbirini göstermiyor
(v7.1-golden çapası otomatik korunuyor).

Kapsam: A1 snapshot'ı (`data/snapshots/2026-07-06`), 12 sembol (mevcut BIST
evreni), 2005-01-01+, `data/cleaning.py` katmanı açık. Kompozit t0 =
**2005-01-03** (tüm 12 sembolün ortak ilk günü — hiçbiri diğerinden geç
başlamıyor). Kompozit forward-fill olayı: **0** (post-cleaning veride tekil
eksik gün yok — EREGL'in tek hayalet barı zaten `data/cleaning.py` tarafından
elenmiş durumda, bkz. `ghost_bars_removed`).

Parametreler (D1, test-öncesi mühürlü, bu turda değiştirilmedi): **N=200,
b=%1, M=3**. Maliyetler: komisyon 10bp, slippage 5bp (config.yaml'dan elle
kopyalandı, `config/regime_core.yaml`).

## (a) Ana Koşum — Özet Metrikler

| Metrik | Değer |
|---|---|
| Toplam getiri (TRY) | **+9,978%** (~101×) |
| CAGR (TRY) | **%23.94** |
| Maks. drawdown | **-%33.50** |
| Sharpe | **1.064** |
| Time-in-market | **%72.4** |
| Anahtarlama sayısı | 67 (34 ENTER, 33 EXIT — son pozisyon dönem sonunda hâlâ açık) |
| Ort. pozisyonda kalma süresi | 154.9 gün (**medyan: 29 gün** — dağılım çarpık, birkaç çok uzun tutuş ortalamayı yukarı çekiyor; medyan daha temsili) |
| Toplam işlem maliyeti | ~90,066 TL (başlangıç 100,000 TL sermaye üzerinden, komisyon+slippage) |

**Not (toplam getiri büyüklüğü)**: %9,978 (~101 kat) rakamı BIST'in 2005-2026
arası nominal TRY enflasyonu/devalüasyonu bağlamında değerlendirilmeli —
bkz. (f) USD satırı, gerçek satın alma gücü tablosu çok daha mütevazı.

## (b) Üç Benchmark Yan Yana

| Metrik | **Strateji (rejim-filtreli)** | XU100 al-tut | 12-sembol sepeti al-tut (filtresiz) | Sadece nakit |
|---|---|---|---|---|
| Toplam getiri (TRY) | +9,978% | +5,658% | **+72,074%** | 0% |
| CAGR | %23.94 | %20.76 | **%35.83** | %0 |
| Maks. drawdown | **-%33.50** | -%63.43 | -%64.22 | %0 |
| Sharpe | **1.064** | 0.851 | **1.184** | 0.0 |

**Yorum (filtrenin katma değeri — asıl karşılaştırma 12-sembol sepeti
al-tut'a karşı)**: Filtre, ham sepetin CAGR'ının (%35.83) ve Sharpe'ının
(1.184) BİR KISMINDAN vazgeçiyor (%23.94 CAGR, 1.064 Sharpe) ama karşılığında
maks. drawdown'u YARIYA YAKIN indiriyor (-%64.22 → -%33.50). Bu, D1'in
"sermaye koruma > getiri" felsefesiyle (CLAUDE.md Bölüm 0.3) tutarlı bir
trade-off — filtre gerçek bir risk-azaltma işlevi görüyor, ama XU100'e karşı
(değil sepete karşı) Sharpe üstünlüğü daha ince bir marj (1.064 vs 0.851).

## (c) En Kötü 5 Drawdown Epizodu + Kriz Takvimi Örtüşmesi

| # | Peak | Trough | Recovery | Derinlik | Bilinen kriz örtüşmesi |
|---|---|---|---|---|---|
| 1 | 2006-02-28 | 2007-01-17 | 2009-07-30 | **-%33.50** | 2006 EM türbülansı + **2008 küresel finans krizi** (tek, kesintisiz bir epizotta birleşmiş — equity 2008 boyunca hiç yeni tepe yapmamış) |
| 2 | 2018-02-26 | 2020-03-12 | 2020-12-29 | -%31.59 | **2018 TL krizi** + **2020 COVID çöküşü** (yine tek epizotta birleşmiş) |
| 3 | 2013-05-22 | 2014-04-09 | 2015-01-26 | -%29.25 | **2013 Fed "taper tantrum" / GOÇ EM satışı** |
| 4 | 2015-05-19 | 2016-02-12 | 2017-04-24 | -%28.05 | 2015-16 EM zayıflığı (emtia çöküşü, jeopolitik gerginlik) |
| 5 | 2024-07-11 | 2025-03-21 | 2025-09-22 | -%26.90 | **Bilinen kriz takviminde YOK** — yeni/güncel bir epizot, ayrıca araştırılmalı |

**Kalan iki bilinen kriz yılı (2011, 2021), %10+ epizot listesinde (ayrı,
daha sığ epizotlar olarak) buluyor**: 2011 (Euro bölgesi krizi), 2010-11-09
→ 2012-06-11 epizodunun (derinlik -%23.93) İÇİNDE; 2021 (TL/CBRT krizi) iki
ayrı epizotta (2021-01-13→04-21, derinlik -%18.64 VE 2021-12-16→2022-03-30,
derinlik -%22.51). **Sonuç: 6 bilinen kriz yılının TAMAMI, stratejinin
kendi drawdown epizotlarıyla örtüşüyor** — filtre bu dönemlerin hiçbirinde
"görünmez" bir şekilde tamamen kaçınamadı (beklenen — rejim filtresi ancak
MA(200) sinyali TEYİT ettikten sonra devreye giriyor, ani/keskin krizlerin
İLK vuruşunu her zaman yakalar).

## (d) %10+ Drawdown Epizotları

**19 epizot** toplam dönemde (2005-2026). Süre/derinlik dağılımı geniş: en
uzun (recovery'siz epizot dahil) 2006-2009 arası (~3.4 yıl), en kısa birkaç
hafta (örn. 2022-09-12→2022-10-17, 5 hafta, derinlik -%15.31). Tam liste
`runtime/regime_core_s1/summary.json`'da. **Bu sayı/derinlik dağılımı, yeni
ailenin breaker eşiği kararı için ham girdi — bu turda KARAR VERİLMEDİ**
(görev kapsamı dışı, ayrı bir tasarım kararı).

## (e) MÜHÜRLÜ KABUL TABLOSU

| # | Kriter | Sonuç | Durum |
|---|---|---|---|
| 1 | TRY Sharpe > XU100 al-tut Sharpe | 1.064 > 0.851 | ✅ **GEÇTİ** |
| 2 | Max DD ≤ endeks max DD'nin yarısı (≤ -%31.72); hedef ≤ -%20 (bilgi) | -%33.50 (gerekli: ≤ -%31.72) | ❌ **GEÇMEDİ** (dar farkla — ~1.8 puan; bilgi hedefi olan -%20'den de belirgin uzak) |
| 3 | OOS aylık-Sharpe > al-tut (12-sepet) OOS aylık-Sharpe VE OOS max DD ≤ al-tut OOS DD'nin yarısı | Sharpe: 0.9505 vs 0.9723 (FAIL) — DD: -%30.30 vs gerekli ≤-%28.12 (FAIL) | ❌ **GEÇMEDİ** (her iki alt-koşul da başarısız) |
| 4 | Uçurum kontrolü: 200/%1/3 komşuluğunda performans uçurumu yok | Komşu 8 kombinasyon: Sharpe 1.02-1.18 aralığında, maxDD -%26.5 ile -%40.2 arasında — ani/keskin bir kopuş YOK | ✅ **GEÇTİ** |

**Genel sonuç: 4 kriterden 2'si GEÇTİ, 2'si GEÇMEDİ.** D1 tasarımı,
XU100'e karşı ANLAMLI bir Sharpe üstünlüğü ve makul bir parametre-sağlamlığı
gösteriyor, ama hem tam-dönem hem OOS drawdown kontrolünde MÜHÜRLENEN
eşiklerin (endeksin yarısı) dar bir farkla GERİSİNDE kalıyor. Bu bir
"başarısızlık" değil, dürüst bir ölçüm — karar kullanıcının/baş danışmanın.

## (f) Bilgilendirici: USD Çevrimi + Gap-Proximity

**USD çevrimi (USDTRY aux snapshot ile, HARDENING C2'nin onaylı kısmi
aktivasyonu)**:

| Metrik | Değer |
|---|---|
| USD toplam getiri | **+189.9%** (~2.9×) |
| **USD CAGR** | **+%5.08** |
| USD Sharpe | 0.315 |
| USD max DD | **-%75.03** |

**Önemli metodolojik not**: Bu stratejide time-in-market %72.4 (BIST'in
orijinal 10-gate ailesinin ~%8'ine karşı ÇOK daha yüksek) — bu yüzden USD
satırı burada İLK KEZ stratejinin GERÇEK dayanıklılığını (nakit-%0 modelinin
USD'ye yapay bir "sıfır risk" katmadığı bir rejimde) ölçüyor. **USD max
DD'nin (-%75.03) TRY max DD'den (-%33.50) çok daha kötü olması KRİTİK bir
gözlem**: rejim KAPALI (nakit) dönemlerde bile TRY cinsinden nakit, USD
karşısında değer kaybetmeye devam ediyor — "sermaye koruma" TRY'de sağlanıyor
ama USD'de SAĞLANMIYOR. **USD CAGR pozitif (+%5.08) olsa da**, bu USD max DD
figürü, "başarı çıtası" tartışmasında (STATUS.md KALICI KAYIT 1: USD CAGR>0
+ Sharpe/DD kriterleri) ayrıca değerlendirilmeli — bu turda o çıtaya karşı
resmi bir GEÇTİ/GEÇMEDİ hükmü verilmedi (o kayıt BIST'in ESKİ 10-gate ailesi
içindi; D1 ayrı bir strateji ailesi, kendi çıtası ayrı belirlenmeli).

**Gap-proximity**: 67 anahtarlamadan **3'ü (%4.48)**, DATA_AUDIT_v2.md'nin
45 benzersiz "açıklanamayan gap" tarihinden (79 sembol-gün kaydının, kompozit
tek bir seri olduğundan sembol ayrımı yapılmadan tekilleştirilmiş hali) birine
±5 bar mesafede. Düşük, orantısız olmayan bir maruziyet — nedensellik iddiası
değil, yalnızca bir maruziyet ölçüsü.

## (g) Çekinceler

1. **Tek tarihçe, tek koşum**: Bu turun TÜM sonuçları 2005-2026 arası TEK bir
   geçmiş üzerinde üretildi — gelecekteki performansın bir garantisi değil.
2. **Anahtarlama sayısının azlığı (istatistiksel örneklem uyarısı)**: 67
   anahtarlama (34 ENTER/33 EXIT), 21 yıllık bir dönemde — Sharpe/DD gibi
   metrikler bu KADAR AZ bağımsız "olay"la yüksek belirsizlik taşır; MC
   dd_p5 (-%48.57) bu belirsizliği kısmen yansıtıyor (aylık getiri
   permütasyonu, ~252 ay üzerinden — daha büyük bir örneklem ama yine de
   tek bir tarihsel dönemin aylarının permütasyonu, BAĞIMSIZ yeni veri değil).
3. **Maliyet duyarlılığı** (tek satır): komisyon 2× (10bp→20bp, slippage
   sabit) → CAGR %23.94→%23.55, Sharpe 1.064→1.050, max DD -%33.50→-%34.03.
   **Küçük bir bozulma** — düşük anahtarlama sıklığı nedeniyle strateji
   maliyet artışına nispeten dayanıklı.
4. **Walk-forward pencere sayısı**: görev talimatında "48-pencere" anıldı,
   gerçek üretilen pencere sayısı (config/config.yaml'daki AYNI train=24ay/
   test=6ay/step=6ay takvimiyle, 2005-2026 tam tarihçesi üzerinde) **39**
   çıktı — muhtemelen görevin kendi tahmini farklı bir tarih aralığına
   dayanıyordu; kullanılan takvim/parametreler AYNI, yalnızca gerçek pencere
   SAYISI farklı, bu bir hata değil.
5. **Kompozit inşası basitleştirilmiş**: eşit ağırlık, rebalance yok, tutma
   sırasında ağırlık kayması (bir sembol diğerlerinden çok performans
   gösterirse portföy o sembole doğru kayar) MODELLENDİ (gerçekçi) ama
   HİÇBİR ZAMAN düzeltilmiyor (yalnızca ENTER'da eşitleniyor) — uzun tutuş
   sürelerinde (medyan 29 gün ama bazıları çok daha uzun) bu kayma birikebilir,
   bu turda ayrıca ölçülmedi.

---

**Karar benim değil, kullanıcının/baş danışmanın.** Hiçbir eşik/gate/
parametre değiştirilmedi (`config/config.yaml`, `backtest/engine.py`,
`strategy/`, `risk/` dokunulmadı — v7.1-golden çapası korunuyor). Faz 5'e/
E2'ye geçilmedi. Bu turda hiçbir ek koşum/parametre ayarı yapılmadı. Durma
Noktası 1'de duruluyor, kullanıcı/baş-danışman değerlendirmesi bekleniyor.

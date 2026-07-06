# Teşhis Raporu v6 (read-only) — yeniden tasarım kararı öncesi

Tarih: 2026-07-06
Kapsam: Bu rapor salt-okunur bir teşhis turudur. **Hiçbir eşik/gate/parametre
değiştirilmedi, `data/snapshots/2026-07-06/` snapshot'ına yazılmadı, Faz 5'e
geçilmedi.** Bulunan iki motor bug'ı (Paket 1) yalnızca raporlanmıştır —
düzeltme ayrı, onaylı bir turda yapılacaktır.

Yardımcı CSV'ler: `runtime/diagnostics_v6/` (gitignored, `runtime/*` kuralına
tabi — bu dosya ve üstündeki bulgular kalıcı kayıt, CSV'ler üretim çıktısıdır).

---

## PAKET 1 — Breaker/DD tutarlılık soruşturması

### 1. Realized mi mark-to-market mi? Breaker ve max-DD aynı equity'yi mi kullanıyor?

Evet, **ikisi de aynı değeri kullanıyor**: `equity_today` (cash + açık
pozisyonların günlük mark-to-market piyasa değeri), hem
`risk_engine.check_and_trip_breaker()`'a hem de equity curve'e (max-DD
hesabının girdisi) besleniyor. Bu anlamda "farklı equity kaynağı" bug'ı YOK.

Ancak `equity_today`'nin hesaplanma biçiminde ayrı ve daha ciddi bir bug var
(bkz. madde 3).

### 2. 2024-01-01→2024-06-30 günlük seri — DD ilk ne zaman %10'u geçti?

CSV: `runtime/diagnostics_v6/paket1_equity_jan_jun_2024.csv` (121 gün).

DD **ilk kez 2024-04-08'de** %10'u geçti — ve aynı gün doğrudan **%20.74**'e
sıçradı (önceki gün, 2024-04-07: %8.20). Breaker kontrolü o gün ÇALIŞTI ve
DOĞRU tetiklendi (`breaker_tripped=True`) — "kontrol çalışmadı" ya da "gecikme"
bug'ı yok. Sorun tetiklemenin kendisinde değil, o günün equity DEĞERİNİN
gerçek olmamasında.

| Tarih | Cash | Equity | Peak | DD | Breaker |
|---|---|---|---|---|---|
| 2024-04-07 | 84,290 | 97,631 | 106,350 | 8.20% | Hayır |
| **2024-04-08** | 84,290 | **84,290** | 106,350 | **20.74%** | **Evet** |
| 2024-04-14 | 84,290 | 97,198 | 106,350 | 8.60% | Evet (durum kalıcı) |

### 3. Trigger günü ve önceki 5 gün — hangi pozisyon(lar) %20.74'ü açıkladı?

CSV: `runtime/diagnostics_v6/paket1_positions_around_trigger.csv`.

O aralıkta açık olan **tek** pozisyon SAHOL'du (165 lot, giriş 2024-04-03,
entry_price=75.38). Günlük notional/close değerleri:

| Tarih | Symbol | Close | Notional |
|---|---|---|---|
| 2024-04-03 | SAHOL | 79.02 | 13,038 |
| 2024-04-04 | SAHOL | 82.23 | 13,568 |
| 2024-04-07 | SAHOL | 80.85 | 13,341 |
| **2024-04-08** | SAHOL | **NaN** | **NaN (→ 0 sayıldı)** |
| 2024-04-14 | SAHOL | 78.24 | 12,909 |

**Kök neden bulundu:** 2024-04-08, BIST çapında bir tatil günüydü — snapshot'taki
diğer 11 sembolün hiçbirinde bu tarih için veri yok (04-07'den 04-14'e temiz
atlama). Ancak **EREGL'de bu tarih için "hayalet" (ghost) bir bar var**: open=
high=low=close=20.246977 (önceki kapanışla birebir aynı), volume=0 — yani
piyasa kapalıyken sentetik/hatalı tek bir satır. `backtest/engine.py`'nin
`all_dates` listesi TÜM sembollerin tarihlerinin BİRLEŞİMİ olduğu için, bu tek
sahte EREGL satırı 2024-04-08'i "geçerli bir işlem günü" olarak tüm sembollere
dayattı.

O günde SAHOL için fiyat verisi olmadığından, engine'in equity formülü:
```
equity_today = cash + sum(close[s] * qty[s] for s in positions if date in daily_features[s].index)
```
SAHOL'u toplamdan **tamamen dışladı** (fiyatı 0 saymadı, satırı hiç dahil
etmedi) — son bilinen fiyatla taşımak yerine. Bu, o gün gerçekte OLMAYAN
~13,341 TL'lik bir "kayıp" yarattı ve equity'yi cash'e (84,290) düşürdü.
Bir sonraki gerçek işlem gününde (04-14) SAHOL'un fiyatı geri geldi, equity
~97,198'e döndü — yani pozisyon hiç zarar etmemişti, sadece bir günlüğüne
"görünmez" oldu.

**Sonuç: -%20.74 max drawdown rakamı (v5 ve v6 raporlarının ikisinde de)
büyük olasılıkla gerçek bir piyasa olayı DEĞİL — bir veri artefaktı + bir
engine bug'ının bileşimi.** Gerçek max DD muhtemelen bu tek günün etkisi
çıkarılınca daha düşük (kabaca %8-9 mertebesinde, 04-07 ve 04-14 civarındaki
değerlerden anlaşıldığı kadarıyla) olurdu. Bu, DÜZELTİLMEDİ — yalnızca
raporlanıyor. İki ayrı, bağımsız düzeltme gerekiyor: (a) veri katmanında
"tüm sembollerde eksik + tek sembolde şüpheli tekil bar" durumunu tatil/anomali
olarak eleyen bir kontrol, (b) engine equity formülünde eksik fiyatı 0 saymak
yerine son bilinen fiyatla taşımak (forward-fill) ya da o günü o sembol için
"pozisyon donmuş" saymak.

### 4. Tüm dönem — eşzamanlılık ve nakit kısıtı

CSV: `runtime/diagnostics_v6/paket1_full_concentration_stats.csv` (5,252 gün).

- **Maks. eşzamanlı açık pozisyon: 3** — config `max_open_positions=2`'yi AŞIYOR.
  Bulunan en az 3 bağımsız dönem: 2006-03-30, 2010-12-02→2010-12-08,
  2013-06-30.
  **Kök neden (ikinci bug):** Giriş değerlendirme döngüsü, her gün için TEK
  bir `acct` snapshot'ı (mevcut açık pozisyon sayısıyla) oluşturuyor, sonra
  aday sembolleri bu SABİT snapshot'a karşı sırayla değerlendiriyor
  (`risk/risk_engine.py:111`, `len(acct.positions) >= cfg.risk.max_open_positions`).
  Eğer aynı gün 2 farklı sembol tüm gate'leri geçer ve o an yalnızca 1 pozisyon
  açıksa, HER İKİSİ de bağımsız olarak "1 < 2, onaylanır" görür ve ikisi de
  onaylanır — ikisi de ertesi gün dolunca eşzamanlı pozisyon sayısı 3'e
  çıkıyor. Örnek: 2006-03-30'da GARAN+ARCLK aynı gün onaylanıp ASELS'e
  katılıyor; 2010-12-02'de KCHOL+ARCLK aynı gün onaylanıp TOASO'ya katılıyor.
  DÜZELTİLMEDİ — raporlanıyor.
- **Maks. toplam notional/equity oranı: %49.6** (2016-09-22) — nakit kısıtı
  (`backtest/engine.py:178`, `if cost <= cash:`) ve `max_position_notional_pct`
  (tek pozisyon %25 tavanı) doğru çalışıyor gibi görünüyor; 2 pozisyon ×
  ~%25-%25 ile %49.6'ya ulaşmak beklenen bir üst sınır (yapısal, bug değil).
- **Maks. tek pozisyon notional/equity oranı: %26.0** (2017-07-16) — %25
  tavanının hafifçe üzerinde, ancak giriş ANINDA kırpma zaten uygulanıyor;
  aşım, giriş SONRASI fiyat yükselişinden kaynaklanıyor (pozisyon büyüklüğü
  sabit, fiyat arttıkça notional/equity oranı da artar) — beklenen davranış,
  bug değil.
- Negatif cash günü: 0. Toplam notional > equity günü: 0. Nakit kısıtı hiçbir
  gün ihlal edilmemiş.

---

## PAKET 2 — WARN günleri adli inceleme

Ham (auto_adjust=False) veri `runtime/diagnostics_v6/raw_unadjusted/` altına,
snapshot'a dokunmadan ayrıca indirildi.

**Önemli metodolojik not:** yfinance'in günlük UTC timestamp'leri Istanbul
yerel günün BİR GÜN ÖNCESİNE denk düşüyor (`data/historical.py`'nin UTC
dönüşümünden dolayı — örn. UTC "21:00" = Istanbul "00:00, ertesi gün"). Bu
yüzden DATA_AUDIT.md'deki "KCHOL 2007-06-07" ve "TCELL 2005-05-16" tarihleri,
gerçek Istanbul işlem günlerinde sırasıyla **2007-06-08** ve **2005-05-17**'ye
karşılık geliyor. Aşağıdaki bulgular gerçek işlem günlerine göredir.

### KCHOL (gerçek tarih: 2007-06-08)

Ham veride de aynı büyüklükte düşüş var (~-26.8%), Dividends/Stock Splits
kolonlarında kayıt YOK. **Sınıflandırma: adjustment artefaktı DEĞİL** (ham
veri zaten sıçramayı gösteriyor). -26.8%, BIST'in tipik ±%10 günlük tavan/taban
limitini aşıyor — bu ya bir işlem-durdurma-sonrası-açılış gap'i (halka arz/
büyük kurumsal olay sonrası ilk işlem günü) ya da bir kaynak/veri hatası
olabilir; kesin sınıflandırma için resmi BIST/KAP kaydı ile doğrulama önerilir
(kod-içi bir düzeltme YAPILMADI).

### TCELL (gerçek tarih: 2005-05-17)

Ham veride `Dividends=0.143002`, `Stock Splits=1.257858` — **doğrulanmış bir
kurumsal aksiyon** (birleşik split + temettü). Bu, ham verideki +%23 sıçramayı
açıklıyor. Ancak snapshot'taki (auto_adjust=True) veri HÂLÂ +%25.96 sıçrama
gösteriyor — yani yfinance'in otomatik ayarlaması bu aksiyonu TAM
düzeltmemiş. **Sınıflandırma: doğrulanmış kurumsal aksiyon, muhtemelen
yfinance'in eksik/kusurlu ayarlaması.** Metodolojik çıkarım: ham verinin
Dividends/Stock Splits kolonları, hacim-oranı sezgisel yöntemlerinden çok
daha kesin bir sınıflandırma aracı.

### v6'nın 119 trade'i bu tarihlere yakın mı?

En yakın trade'ler bu tarihlerden **442 gün (KCHOL)** ve **337 gün (TCELL)**
uzakta. **Etki sınırlı** — v6 sonuçlarını bu iki WARN günü anlamlı ölçüde
etkilemiyor.

---

## PAKET 3 — Gate ablasyon (counterfactual, sinyal-kalite ölçümü — backtest DEĞİL)

Yöntem: `tools/gate_ablation.py`. Aktif 6 gate için, "diğer 9 gate'i geçip
YALNIZCA bu gate'ten elenen" adaylar bulundu, izole modda (portföy/nakit/
breaker/korelasyon etkileşimi YOK, sabit 1R risk normalizasyonu, aynı stop/
hedef/stop-önceliği kuralları) simüle edildi. Gerçek 119 trade de AYNI izole
simülatörle adil kıyas için yeniden ölçüldü (119'dan 117'si ölçülebildi — 2
trade veri sınırı/hizalama nedeniyle atlandı).

CSV'ler: `runtime/diagnostics_v6/paket3_*.csv` (gate matrisi, her gate için
counterfactual trade listesi, baseline izole trade listesi, özet tablo).

### Sonuç tablosu (izole ölçüm)

| Grup | n | Win rate | Ort. R | PF |
|---|---|---|---|---|
| **BASELINE** (gerçek 119 trade, izole yeniden ölçüm) | 117 | 43.6% | 0.036 | 1.11 |
| trend (yalnızca bu gate'ten elenenler) | 233 | 52.4% | 0.087 | 1.54 |
| regime/ADX (yalnızca bu gate'ten elenenler) | 455 | 41.1% | 0.119 | 1.42 |
| rsi (yalnızca bu gate'ten elenenler) | 610 | 42.0% | 0.079 | 1.19 |
| macd (yalnızca bu gate'ten elenenler) | 57 | 42.1% | -0.021 | 0.93 |
| volume (yalnızca bu gate'ten elenenler) | 944 | 38.9% | -0.044 | 0.86 |
| trigger_4h (yalnızca bu gate'ten elenenler) | 70 | 47.1% | -0.018 | 0.94 |

### Yorum (sinyal-kalite düzeyinde, portföy etkisi hariç)

- **trend, regime, rsi**: counterfactual grupları BASELINE'dan daha yüksek
  ortalama R ve PF gösteriyor (özellikle trend: PF 1.54 vs 1.11). Bu, izole
  ölçümde, bu üç gate'in eleyip geçtiği "reddedilen" adayların, gerçekte
  gate'i geçip trade edilen sinyallerden DAHA İYİ kalitede olduğu anlamına
  gelir. Yani bu üç eşik, en azından bu tek-sinyal ölçüm çerçevesinde,
  **değer katmıyor gibi görünüyor** — potansiyel olarak zarar bile veriyor
  olabilir (iyi sinyalleri eliyorlar).
- **macd, volume, trigger_4h**: counterfactual grupları BASELINE'dan daha
  DÜŞÜK ortalama R ve PF<1 gösteriyor (özellikle volume: PF 0.86, n=944 —
  büyük örneklem, güvenilir). Bu üç gate, gerçekten düşük kaliteli adayları
  eleyip **değer katıyor**.
- **Örneklem büyüklüğü uyarısı**: macd (n=57) ve trigger_4h (n=70) küçük
  örneklemler — yorumları temkinli okunmalı. volume (n=944) ve rsi (n=610)
  istatistiksel olarak daha güvenilir.
- **Kritik metodolojik sınırlama**: Bu ölçüm PORTFÖY ETKİLERİNİ (nakit
  kısıtı, korelasyon, max_open_positions, breaker) YOK SAYIYOR. trend/regime/
  rsi gate'lerinin gerçek işlevi yalnızca "iyi sinyal seçmek" olmayabilir —
  örn. rejim filtreleri (trend, regime) portföyün YANLIŞ zamanda (geniş
  çaplı ayı piyasası) çok sayıda pozisyon açmasını önleyerek DOLAYLI bir risk
  yönetimi işlevi görüyor olabilir; bu etki izole ölçümde görünmez. Bu
  nedenle "değer katmıyor" bulgusu **hiçbir eşiği değiştirmek için tek
  başına yeterli kanıt değildir** — yalnızca yeniden tasarım konuşmasına bir
  girdidir.

---

## PAKET 4 — Tek sayfalık sentez: yeniden tasarım konuşması için girdiler

1. **-%20.74 max drawdown rakamı güvenilir değil.** Kök neden: EREGL'deki tek
   günlük "hayalet bar" (2024-04-08, piyasa tatildeyken sentetik/hatalı veri)
   + engine'in eksik fiyat verisi olan açık pozisyonları o gün için sıfır
   sayan equity formülü. Gerçek max DD muhtemelen daha düşük. **Yeniden
   tasarım kararları bu rakama dayandırılmamalı** — önce veri+engine
   düzeltmesi, sonra yeniden koşu gerekiyor (ayrı onaylı tur).
2. **Risk motorunda ikinci bir bug var**: aynı gün 2+ sembol gate'leri geçerse
   `max_open_positions` limiti aşılabiliyor (gözlenen maks: 3, limit: 2). Bu
   da düzeltme gerektiren, ayrı bir bulgu.
3. **Nakit/notional disiplini sağlam**: negatif cash yok, toplam notional
   equity'yi hiç aşmamış, tek pozisyon tavanı yalnızca giriş-sonrası fiyat
   hareketiyle marjinal aşılmış (beklenen davranış).
4. **KCHOL 2007-06-08 WARN günü hâlâ açıklanamadı** (gerçek büyük hareket mi,
   kaynak hatası mı — belirsiz, dış doğrulama gerektiriyor); **TCELL
   2005-05-17 doğrulanmış bir kurumsal aksiyon ama yfinance'in ayarlaması
   eksik**. İkisinin de v6'nın 119 trade'i üzerindeki etkisi ihmal edilebilir
   düzeyde (en yakın trade 337-442 gün uzakta).
5. **Gate ablasyon, üç aktif gate'in (trend, regime, rsi) izole sinyal-kalite
   düzeyinde değer katmadığını, üç gate'in ise (macd, volume, trigger_4h)
   kattığını gösteriyor** — ancak bu ölçüm portföy-seviyesi risk yönetimi
   etkilerini (rejim filtresinin dolaylı volatilite/korelasyon koruması gibi)
   hesaba katmıyor, dolayısıyla tek başına eşik değiştirmeye yeterli kanıt
   değil.

**Bu beş bulgunun ortak çıkarımı**: mevcut backtest sonuçlarının (v1-v6, tüm
BACKTEST_REVIEW dosyaları) hem risk metriklerinde (max DD) hem de motor
mekaniklerinde (pozisyon limiti) düzeltilmemiş hatalar içerdiği ve gate
seçiminin izole ölçümde beklenenden zayıf olduğu ortaya çıktı. Önerilen sıra
(karar kullanıcının): (a) önce iki motor bug'ını (equity forward-fill +
same-day çoklu onay) ayrı bir onaylı turda düzelt, (b) veri katmanına
"tüm-sembollerde-eksik-tek-sembolde-var" tatil/anomali kontrolü ekle, (c) bu
düzeltmelerle TÜM v1-v6 sweep'ini yeniden koş, (d) yalnızca o zaman gate
eşiklerini (trend/regime/rsi konusunda Paket 3 bulgusu ışığında) yeniden
tasarım konuşmasına aç.

---

**Bitti. Faz 5'e geçilmedi, hiçbir eşik/parametre değiştirilmedi. Kullanıcı
onayı bekleniyor.**

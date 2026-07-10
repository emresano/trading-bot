# Proje Durumu
> Tarihsel tur detayları: **STATUS_ARCHIVE.md** (tamamlanmış turların tam blokları + çözülmüş sorun/blok maddeleri).

Son güncelleme: 2026-07-10T13:40:00+03:00 (Europe/Istanbul)
Şu an: **D5-BIST CHALLENGER SPIKE TAMAMLANDI (KALICI KAYIT 23+24) — mühürlü
tablo 2/4 → mekanik RED (HÜKÜM DEĞİL; karar kullanıcının/baş danışmanın).**
Kapı (trailing 252g hisse-getirisi vs ham TRY faizi) Sharpe'ı ve OOS aylık-Sharpe'ı
iyileştirdi (1.274>1.215; 1.161>1.068) ama **CAGR'ı düşürdü** (%27.15<%28.21) ve
— asıl kritik — **realize max DD'yi DERİNLEŞTİRDİ** (-%35.22 vs -%28.43), çünkü
kapı toparlanmalara katılımı bastırıp D1'in iki ayrı DD epizodunu tek, daha derin
bir epizoda kaynaştırıyor. Rapor: `D5_BIST_S1.md`. D1 paper hattı, `mode: paper`,
N/b/M ve TÜM canlı modüller DOKUNULMADI; aktif kuyruk (K1.5 2/2 → G1) etkilenmedi.

--- Önceki kayıt (2026-07-10T10:55, PERIOD_COMPARISON doğrulama mini-turu) ---
Şu an: **PERIOD_COMPARISON DOĞRULAMA MİNİ-TURU TAMAMLANDI — "sepet al-tut"
metodolojisi netleştirildi + "Son 1 Yıl bilmecesi" sayısal ayrıştırıldı.**
Bir önceki turda D1 (+45.3%) ile "sepet" (+105.8%) arasındaki büyük Son-1-Yıl
farkının kaynağı belirsizdi (0 anahtarlama + rejim-ON %100 iken). Kök neden
bulundu: mevcut **"sepet"** satırı `build_composite()`'in (mühürlü, S1b'nin
kendi tanımı) TEK bir serisidir — 12 sembol t0=2005'te eşit-dolar yatırılıp
**BİR KEZ BİLE dengelenmemiş**; pencere tabloları bu seriyi yalnızca KESER,
pencere başında ağırlıkları sıfırlamaz. 21 yıllık sürüklenme yüzünden
`ASELS` tek başına bu pencerenin başında sepetin **%58.3**'ünü oluşturuyordu
— "sepet"in Son-1-Yıl getirisi esasen TEK sembolün performansıydı, 12
sembolün dengeli ortalaması değil. **Sayısal ayrıştırma:** toplam fark
+60.5pp = ağırlık-sürüklenmesi etkisi (+71.2pp, taze pencere-başı eşit-ağırlık
sepetin getirisi +34.55% olurdu — 2005-ağırlıklı +105.8%'in çok altında) +
kalan fark (−10.8pp, D1'in son ENTER'ı pencere başlamadan önce olduğu için
D1'in ağırlıkları da pencere-başı-taze değil, biraz daha erken sabitlenmiş —
küçük komisyon/slipaj kalıntısı da dahil). **Düzeltme (kod davranışı
DEĞİŞMEDİ, yalnız rapor):** her pencereye AYRI, `build_composite()`'in AYNEN
reuse edildiği yeni bir **"sepet — PENCERE-BAŞI eşit ağırlık"** satırı
eklendi (`tools/period_comparison.py::build_window_start_basket()` — o
pencerenin başlangıcına kısıtlanmış kapanış serileriyle build_composite'i
çağırır, iç t0 = pencere başlangıcı); mevcut "sepet" satırı KALDI, etiketi
netleşti ("2005 AĞIRLIKLI, HİÇ dengelenmemiş"). Yeni teşhis fonksiyonu
`symbol_weight_shares()` her pencerede en büyük payı gösteriyor (rapor
notu). PERIOD_COMPARISON.md'ye: Metodoloji Notu (item 1, tek paragraf),
"Son 1 Yıl Bilmecesi: Sayısal Ayrıştırma" bölümü (dinamik hesaplanır, sayı
sabit YAZILMADI), her pencere tablosuna ağırlık-payı notu, kriz-yılı
tablosuna açıklayıcı dipnot eklendi. Tam-dönem penceresinde yeni satır ile
eski satır BİREBİR AYNI (window start = global t0 = 2005 olduğunda iki
yöntem matematiksel olarak özdeş — tutarlılık kanıtı, rapor içinde
gözlemlenebilir). 3 yeni test (`symbol_weight_shares` konsantrasyon,
`build_window_start_basket` pencere-öncesi sürüklenmeyi YOK sayması,
tam-dönem'de `build_composite`'le birebir eşleşme) — toplam 11 test
`tests/test_period_comparison.py`'de. Strateji/motor/risk/karar kodu
DOKUNULMADI (yalnız rapor/teşhis katmanı); hiçbir mühürlü eşik/parametre
etkilenmedi. Faz 6/go_live/launchd/real'e adım YOK; iki durma noktası
kullanıcıda.

--- Önceki kayıt (2026-07-10T10:20, PERIOD_COMPARISON ilk sürüm) ---
Şu an: **DÖNEMSEL KARŞILAŞTIRMA RAPORU (PERIOD_COMPARISON.md) TAMAMLANDI —
BİLGİLENDİRME, kriter/kabul/karar YOK, hiçbir mühürlü eşik etkilenmedi.**
Yeni araç `tools/period_comparison.py` (+ `tools/period_comparison_report.py`):
mühürlü S1b konfigürasyonuyla (N=200/b=%1/M=3, `config/regime_core.yaml`,
`backtest/regime_core.py` + `tools/run_regime_core.py` — YALNIZ import, kod
kopyalama/değiştirme YOK) D1 equity eğrisini 2005-01-03→2026-07-08'e kadar
yeniden üretti. Frozen S1b snapshot'ı (`data/snapshots/2026-07-06`) son barı
~07-02'de bitiyordu; eksik kuyruk (07-03→07-08, 12 sembol + USDTRY) canlı
yfinance çekimiyle tamamlandı ve `data/snapshots/aux_cmp/2026-07-10/` altına
sha256 manifest'li dondu (mevcut hiçbir snapshot değiştirilmedi; örtüşen
barlarda kaynak-tutarlılık farkı **0.00e+00**, 12/12 sembol — bu turda
DATA_DRIFT YOK). Pencereler (1y/3y/5y/10y/tam-dönem) için: D1 vs 12-sembol
sepet al-tut vs XU100 (bilgi) vs TRY faizi (haircut'lı S1b modeli + ham) vs
USD al-tut vs best-effort altın/TÜFE (TÜFE: FRED TURCPIALLMINMEI, son gözlem
2025-04-01, bilinen ~15 aylık gecikme — rapor bunu açıkça işaretliyor) + USD
paneli (D1/sepet USD-terim CAGR/maxDD; tam-dönem D1 USD CAGR +8.53%, S1b'nin
kendi +%8.70 bulgusuna çok yakın/tutarlı — kısa "DÜRÜST DEĞERLENDİRME" tutarlılık
notu raporda) + kriz-yılı ayrıştırması (2008/2013/2018/2021-23, D1 vs sepet vs
faiz). Bir yan-bulgu-düzeltmesi: `data.historical.build_gold_try_proxy()`
GC=F (~04:00 UTC) ile USDTRY=X (~00:00/23:00 UTC) barlarını saat-hizasız ham
index'te iç-birleştirdiği için 0 satır üretiyordu (mevcut, DEĞİŞTİRİLMEYEN bir
ön-koşul kusuru — fonksiyonun kendisi DOKUNULMADI); best-effort altın serisi
bu yüzden yerel olarak `normalize_bist_dates` (mevcut, reuse) ile takvim-günü
hizalı ayrıca birleştirildi (yalnızca bu BİLGİ turunun yerel mantığı).
`freeze_aux_cmp()` aynı `run_tag` için birden fazla çağrıda (D1 evreni + USDTRY)
manifest'i ÜZERİNE YAZMAK yerine BİRLEŞTİRİR (`files`/`groups`) — ilk sürümde
bulunup düzeltilen bir kayıp-kayıt riski, testle sabitlendi. 8 yeni test
(`tests/test_period_comparison.py`): freeze/manifest/sha256 + merge, pencere
sınırları (tam/kısmi kapsama), forward-fill, switch/regime-ratio, extend_one
(no-op + mock canlı çekim). Tam süit **552 passed**, v7.1-golden 3/3 bayt-bayt.
Strateji/motor/risk/karar kodu (`strategy/
regime_core.py`, `backtest/regime_core.py`, `config/regime_core.yaml`, `mode:
paper`, canlı bot modülleri) DOKUNULMADI; hiçbir grid/varyant seçimi YAPILMADI.
Faz 6/go_live/launchd/real'e adım YOK; iki durma noktası kullanıcıda; K1.5
2/2 doğrulaması (bir sonraki temiz gün) hâlâ aktif kuyruğun ilk adımı — bu
tur onu NE ilerletir NE geciktirir (paralel, bağımsız bir bilgi turu).

--- Önceki kayıt (2026-07-09T21:05, DRIFT çözümü + EOD görünürlük — bu turdan ÖNCE tamamlandı) ---
Şu an: **DRIFT ÇÖZÜLDÜ + EOD görünürlük düzeltmesi TAMAM — launchd (G1) hâlâ
KURULMADI, K1.5 hâlâ 1/2.** 2026-07-09 akşam cycle'ındaki 10-bar DATA_DRIFT
(kök neden: yfinance geç bar-revizyonu, 07-08 ASELS emsali — temettü/split İZİ YOK)
`--resync` ile giderildi (kompozit parite max_abs_diff=1.74e-05, ≈0); resync SONRASI
07-08 VE 07-09 rejim kararları (regime_on=true, ikisi de) DEĞİŞMEDİ → "K1.5 1/2
(07-08) geçerliliğini korur". Ayrı teşhis: Telegram CRITICAL alarmı zaten
gönderiliyordu (kod yolu koşulsuz) ama **EOD özeti veri-finallik durumunu hiç
göstermiyordu** (tasarım değil, eksik) — operatör bugün EOD'yi "temiz" okudu, journal
`provisional=true`'ydu. **FIX (yalnız notify-katmanı):** `build_eod_summary()`'ye
`data_final`/`data_final_reason`; EOD'de artık "Veri: FINAL ✓" veya "Veri: PROVISIONAL
⚠ (…)" satırı var; karar/sinyal kodu DOKUNULMADI; 9 yeni/genişletilmiş test. Bu fix
K1.5 sayacını SIFIRLAMAZ (ölçülen boru hattı değişmedi). 2026-07-09 akşam koşusu
resmi K1.5 kaydı: **TEMİZ DEĞİL** (savunma katmanı doğru çalıştı) → sayaç 1/2'de;
sıradaki deneme 2026-07-10 akşam. Detay: aşağı "DRIFT ÇÖZÜMÜ + ALARM-GÖRÜNÜRLÜK
TEŞHİSİ + K1.5 kaydı" bölümü.

--- Önceki kayıt (2026-07-09T20:45, K1.5 2/2 FAIL tespiti — bu turda çözüldü) ---
Şu an: **K1.5 2/2 denemesi (2026-07-09) FAIL — launchd (G1) KURULMADI.** Bugünün tek
akşam cycle'ında (17:32:38Z/20:32 Istanbul) DATA_DRIFT (10 bar sapması, resync
yapılmamış) + `provisional=true` bulundu → görev kuralı gereği kurulum adımı
atlandı, yalnız bulgu raporlandı ve STATUS'a işlendi (bkz. "K1.5 Mekanik Teyit —
2/2 DENEMESİ: FAIL" bölümü). K1.5 hâlâ 1/2; G1 launchd kurulumu farklı, temiz bir
günün cycle'ı bekliyor. Kod/config/launchd DEĞİŞMEDİ.

--- Önceki kayıt (2026-07-09T10:15, değişmedi) ---
Şu an: **D4-US baş danışman kararıyla KESİN RED (KALICI KAYIT 22) — US AKTİF AİLE
ARAMASI ASKIDA.** D4US-S1 (KALICI KAYIT 20+21) mühürlü tabloda 1/4 idi; baş danışman
kaydı bunu onayladı (kriter 2'nin 0.03pp'lik dar farkı kural gereği FAIL, sonucu
değiştirmez — kriter 1/3a zaten geniş farkla kalmıştı). ETF tarihçesine bakış sayacı
1 kullanıldı; D4 ailesi ve TÜM varyantları bu tarihçede KAPALI. Üç aile (D1-US/D2-US/
D4-US) üç farklı mekanizma, üçü de 1/4 — meta bulgu: 3b (DD-kesme) hep PASS, 1/3a
(risk-ayarlı getiri edge'i, dürüst diversifiye referansa karşı) hep FAIL; BIST-D1'in
4/4'ü istisna değil (yüksek TL nakit faizi + BIST rejim yapısı USD'de yok). **US
yeniden açılması yalnız kullanıcı kararıyla ve yalnız iki yapısal kaldıraçtan biriyle:**
(i) kuyruk #21 tek-hisse point-in-time yolu (EODHD kapsam doğrulaması, satın alma
DEĞİL), (ii) short-gate tasarım turu. **Ana odak artık BIST Faz 6: K1.5 2/2 → G1
(kullanıcı) → Faz 6 başlangıç kriterleri.** Detay: aşağı "KALICI KAYIT 22" bölümü.

Ayrıca bu turda **K1.5 mekanik teyidi 1/2** kaydedildi (2026-07-08 akşam koşusu:
DATA_DRIFT yok, provisional yok, TELEGRAM ACTIVE, EOD Rejim/Pozisyon ayrı+tutarlı —
dördü de PASS; bkz. yukarı "K1.5 Mekanik Teyit" bölümü). Offline/kayıt turu; `mode: paper`
+ TÜM canlı bot modülleri + S1/S1b/E4/D2US araçları DOKUNULMADI; grid/varyant seçimi YOK;
v7.1-golden her commit 3/3; tam süit **530 passed** (değişmedi — bu tur kod davranışı
değiştirmedi). Faz 6/real/launchd/go_live'a adım YOK. (Önceki: D2US-S1 spike KAYIT 18,
D1-US kesin red KAYIT 16, E4/E4b KAYIT 15/16. F5 paper hattı ayrı.)

--- Önceki oturum (F5 paper hattı, bu turda DOKUNULMADI) ---
Mikro-düzeltme (yalnız EOD gösterimi): `notify/eod_summary.py`'de "Rejim" (compute_regime_
signal çıktısı) ve "Pozisyon" (broker'da sepet var mı) tek, yanlış birleştirilmiş satırda
karışıyordu — observe modda pozisyon HER ZAMAN NAKİT olduğu için rejim ON iken bile "NAKİT
(rejim OFF)" basılıp üstteki [GÖZLEM] başlığıyla çelişiyordu. Artık iki AYRI satır: "Rejim:
ON/OFF" + "Pozisyon: NAKİT/SEPETTE (observe — hesap başlatılmadı)". `strategy/regime_core.py`
DOKUNULMADI; 4 yeni test; tam süit 511 passed, golden 3/3.

Operatör aksiyonu (kod değişikliği YOK): ilk gerçek DATA_DRIFT vakası (2026-07-07, 3 bar —
ASELS/EREGL/TUPRS, temettü/split izi YOK) `--resync` ile giderildi (4 sembol 1'er bar,
kompozit parite ≈0); doğrulama cycle'ı DATA_DRIFT'siz + EOD Telegram'a gitti. Detay:
`PHASE5B2A_REVIEW.md` "B2a.1 Eki — İlk gerçek DATA_DRIFT vakası + resync sonucu".
Şu an: **FAZ 5 (PAPER) — F5-B2a.1 (TELEGRAM TEŞHİS + SESSİZ DÜŞÜŞ SERTLEŞTİRME) TAMAMLANDI —
kullanıcı/baş danışman değerlendirmesi bekliyor** (bkz. `PHASE5B2A_REVIEW.md` "B2a.1 Eki").
Kök neden: gerçek Telegram kimlik bilgileri kodun okuduğu `config/secrets.env` DEĞİL, repo
kökündeki farklı bir `secrets.env`'e yazılmıştı (3 kez tekrarlandı — OPERATOR_GUIDE §0'a
belirgin uyarı eklendi) + token değerinde 2 kez BotFather kopyalama artefaktı (gömülü
boşluk). `--test-telegram` CLI eklendi + GERÇEK uçtan-uca doğrulandı (kullanıcı telefonunda
onayladı) + manuel observe cycle EOD özeti gerçekten Telegram'a gitti. Sessiz-düşüş
sertleştirmesi: `telegram.enabled=true` ama token/chat_id okunamazsa artık belirgin WARN +
EOD/heartbeat_status.json'da kalıcı "TELEGRAM: ACTIVE/LOG-ONLY(neden)" satırı. `.gitignore`
genel `secrets.env`/`*.env`/`runtime/manual/` deseni (STATUS #9 KAPANDI). **Güvenlik notu:**
bir teşhis komutu yanlışlıkla gerçek token'ı bu oturumun çıktısına yazdırdı → kullanıcı
BotFather'da token'ı iptal edip yeniledi (kullanıcı kararıyla). `mode: paper` DOKUNULMADI;
N/b/M mühürlü; D1 fonksiyonları + `data/snapshots/` DEĞİŞMEDİ; v7.1-golden her commit 3/3
bayt-bayt. Gelen Telegram komutu/long-poll YOK; ManualExecutionAdapter TASARIMI F5-B2'ye
kaldı. Faz 6 BAŞLATILMADI; go_live_date=null; launchd etkinleştirilmedi; Durma Noktası 2
kapalı. Tam süit: **507 passed** (F5-B2a 494 + 13 yeni).

**F5-B2a (önceki alt-tur, TAMAMLANDI):** 6 madde — gerçek Bot API sendMessage (m1), alarm+EOD
kablolama kuru-testi (m2), launchd K5-grace saat doğrulaması (m3), "bayat=muhafazakâr"
genelleme düzeltmesi (m4), GERÇEK EVDS CSV kıyası (m5), kapanış (m6). Detay: KALICI KAYIT 12.

**F5-B1.1 (gölge sertleştirme, K1-K9) daha önce tamamlandı** (bkz. `PHASE5B11_REVIEW.md`,
KALICI KAYIT 11): 9 madde, 485 passed.

**F5-B1 (gölge paper, GERÇEK yfinance EOD) daha önce tamamlandı** (bkz. `PHASE5B1_REVIEW.md`):
canlı depo↔backtest kompozit bit-bit 0.0; snapshot↔yfinance 66132 bar-günde ~1e-7; 470 passed.
**AlgoLab İPTAL** (2025-12-31; F5-B2=ManualExecutionAdapter — EK KAYIT aşağıda).

**F5-A (offline runtime iskeleti) daha önce tamamlandı** (bkz. `PHASE5A_REVIEW.md`):
9 aşama, fixture/kuru-testli, 456 passed.

Tamamlanan fazlar: Faz 1-3, Faz 4 (Backtest Harness — v1→v7, v7.1-golden) +
HARDENING.md Bölüm A + Teşhis v6 + Motor+veri v7 + EXPANSION.md E1 (Veri Temeli)
+ Portföy ablasyon (+ R1) + S1 + S1b (D1 spike'ları) + **EXPANSION.md E2 (Motor
Genelleştirme)** + **P1 (D1 üretim portu)**. (Her turun tam detayı: STATUS_ARCHIVE.md.)

## Şu an neredeyiz (özet)
- D1 ailesi KABUL EDİLDİ (KALICI KAYIT 6) ve ÜRETİM PORTU tamamlandı (P1, KALICI
  KAYIT 8) — S1b'yle bit-bit özdeş, v7.1-golden korundu, tam süit 378 passed.
- Sıradaki iş **kullanıcı onayına bağlı**: canlı/paper emir katmanı Faz 5
  (HARDENING B onayı) — PaperBroker/AlgoLab hem 10-gate hem regime_core ailesini
  sürebilmeli. E-hattında sıradaki adım E3 (broker spike + karar), "E3 onaylandı"
  ayrı gerekir.
- İki durma noktası (Faz 4 backtest değerlendirmesi + gerçek sermaye) kullanıcıda;
  hiçbir eşik/parametre değiştirilmedi.

## KALICI KAYIT 1 — Başarı Çıtası (kullanıcı kararı, 2026-07-06)
USD bazında CAGR > 0 taban şart; Sharpe > XU100 al-tut Sharpe VE max DD ≤
endeks max DD'sinin yarısı. Resmi walk-forward kabul kriterleri değişmedi;
güncellemesi yeniden-tasarım turunda ayrı onayla.

**Durum (ABLATION_PORTFOLIO.md'den, 2026-07-06 ölçümü): hiçbir varyant
(baseline dahil) bu çıtayı geçmiyor** — tüm varyantlar USD CAGR ≈ -%15.7 ile
-%16.2 arası (TRY'nin USD karşısındaki yapısal değer kaybı baskın; stratejinin
TRY-bazlı performansından bağımsız). max DD/endeks-DD oranı ise ÇOK iyi
(0.106-0.172 — endeksin altıda/beşte biri) — bu kısım geçiyor, USD-CAGR
kısmı geçmiyor.

## KALICI KAYIT 2 — Haber/Olay Politikası Güncellemesi (kullanıcı kararı, 2026-07-06)
Yapılandırılmamış haber (LLM/Tier 1) veto-only kalır. Deterministik olay
verisi (earnings takvimi/sürprizi, Tier 0) giriş tarafında KULLANILABİLİR —
yalnızca backtest edilebilir, tek-değişiklik-turu ve aynı kabul
kriterlerinden geçen bir gate/özellik olarak; ilk aday US sleeve (E1: earnings
tarihçesi 2001'e kadar mevcut, bkz. DATA_AUDIT_US.md). İmplementasyon
yeniden-tasarım/E-fazlarında, şimdi değil.

## KALICI KAYIT 3 — BIST Hükmü (2026-07-06, kullanıcı delegasyonuyla baş danışman kararı)
Mevcut 10-gate ailesi BIST'te başarı çıtası (B) yolu olarak REDDEDİLDİ; huni
DONDURULDU (eşik değişikliği yok, referans + E4/ABD adil testi için
saklanıyor); yeni yön: rejim-filtreli çekirdek maruziyet (D1 tasarımı); E2 ön
şartı AÇILDI. İki durma noktası kullanıcıda.

## KALICI KAYIT 4 — S1 Spike Sonucu (2026-07-06)
D1 tasarımının (rejim-filtreli çekirdek) tek-tur değerlendirme spike'ı
tamamlandı — bkz. `REGIME_CORE_S1.md`. **Mühürlü kabul tablosu: 4 kriterden
2'si GEÇTİ (TRY Sharpe>XU100 Sharpe; uçurum kontrolü temiz), 2'si DAR
FARKLA GEÇMEDİ** (tam-dönem max DD -%33.50, gerekli ≤-%31.72; OOS
aylık-Sharpe VE OOS max DD, 12-sembol sepeti al-tut'a karşı her ikisi de
başarısız). USD CAGR bilgilendirici olarak POZİTİF (+%5.08) ama USD max DD
çok kötü (-%75.03 — nakit dönemlerinde bile TRY devalüasyonu USD değerini
eritiyor). Bu bir üretim implementasyonu DEĞİL, bir spike'tı — kabul/red/
iterasyon kararı kullanıcının/baş danışmanın; bu turda hiçbir parametre
ayarı yapılmadı.

## KALICI KAYIT 5 — S1b Ölçüm Tamamlama Sonucu (2026-07-07)
Nakit-getiri düzeltmesi (rejim KAPALI günlerde TRY gecelik faizi tahakkuku,
200bp kırpmalı) eklendi — **tek davranış değişikliği**, N=200/b=%1/M=3 ve
maliyetler AYNEN kaldı. Sonuç — bkz. `REGIME_CORE_S1B.md`: **Mühürlü kabul
tablosunun 4 kriterinin TAMAMI GEÇTİ** (S1'de 2/4 idi):
1) TRY Sharpe 1.215 > XU100 Sharpe 0.851 — GEÇTİ (S1'de de geçmişti).
2) Max DD -%28.43 ≤ gerekli -%31.72 — **YENİ GEÇTİ** (S1'de -%33.50 ile dar
   farkla geçmemişti).
3) OOS aylık-Sharpe 1.068>0.972 VE OOS max DD -%24.55≤-%28.12 — **YENİ
   GEÇTİ** (S1'de ikisi de başarısızdı).
4) Uçurum kontrolü temiz — GEÇTİ (S1'de de geçmişti).

**Kullanıcının ÖNCEDEN belirlediği kurala göre** ("4/4 geçerse aile kabul
adayı, herhangi biri kalırsa aile reddedilir — üçüncü bakış yok"): **bu
mekanik sonuç D1 ailesini bir KABUL ADAYI yapıyor.** Bu, Claude Code'un
kendi hükmü DEĞİL — kullanıcının önceden koyduğu kuralın mekanik
uygulanmasıdır. **Nihai kabul/red/üretime geçiş kararı hâlâ kullanıcının/
baş danışmanın** — otomatik olarak Faz 5'e/E2'ye geçilmedi, geçilmeyecek.

Önemli nüanslar (dürüst rapor, karar etkilenmeden): (a) USD-terimde
filtrenin Sharpe üstünlüğü TERSİNE dönüyor — 12-sembol sepeti al-tut'un USD
Sharpe'ı (0.577) stratejininkinden (0.435) yüksek; "başarı" tanımı para
birimine göre değişebilir. (b) TRY_ON_RATE kaynağı TCMB'nin kendisi değil,
OECD/FRED rebroadcast'i (TCMB EVDS'ye erişim yok — kimlik bilgisi
bulunamadı); 9 aylık bir veri boşluğu (2023) forward-fill ile dolduruldu.
(c) Drawdown epizot TOPOLOJİSİ nakit getirisiyle değişti (bazı epizotlar
ikiye ayrıldı, en kötü epizodun kimliği değişti) — bu METODOLOJİK bir
gözlem, veri hatası değil.

## KALICI KAYIT 6 — D1 Ailesi KABUL EDİLDİ (2026-07-07, baş danışman kararı)
D1 (rejim-filtreli çekirdek) ailesi, önceden mühürlenen kurala göre (S1b
4/4) baş danışman kararıyla **KABUL EDİLDİ** (2026-07-07). Bu, KALICI KAYIT
5'in mekanik "kabul adayı" tespitinin RESMİ, otoriter sonucudur — Claude
Code'un kendi hükmü değil, kullanıcının/baş danışmanın kararı. Ölçüm:
`REGIME_CORE_S1B.md` (nakit-getiri düzeltmeli).

**Kabulle kayda giren çekinceler**:
(a) USD Sharpe'ta 12-sembol sepeti al-tut üstün — BIST-içi çözülemez, US
    sleeve gündemi (EXPANSION.md).
(b) Faiz kaynağı FRED/OECD (TCMB'nin kendisi değil) — real öncesi EVDS
    çapraz doğrulaması kuyruğa alındı (bkz. aşağı, madde 1).
(c) Bilgilendirici -%20 DD hedefi (KALICI KAYIT 5'teki mühürlü tablonun
    "bilgi" satırı) tutmadı — mühürlü/resmi kriter değil, yalnızca not.

**Yeni ailenin operasyonel breaker kararı** (D1 üretim implementasyonu için):
- **ALARM eşiği: -%25** (bildirim, işlem durdurmaz).
- **FREEZE eşiği: -%40** (yeni ENTER yok; reset yalnızca kullanıcı elle).
- Gerekçe: S1/S1b birleşik tarihsel zarf (en kötü gözlenen -%33.5, S1'in
  faizsiz ana koşumu) + ~6.5 puanlık marj FREEZE eşiğine kadar. Tarihsel
  tetiklenme sayısı: **0** (ne S1 ne S1b'de -%40'a yaklaşan bir epizot yok).

**Üretim implementasyonu AYRI bir onaylı turdur** (E2 sonrası,
"backtest=canlı aynı fonksiyon" ilkesiyle, CLAUDE.md Bölüm 3.1). **İki
durma noktası kullanıcıda kalmaya devam ediyor** — bu kabul kaydı Faz 5'e
veya E2'ye otomatik geçiş anlamına GELMEZ.
[NOT: Üretim portu P1 turunda tamamlandı — bkz. KALICI KAYIT 8.]

**Kuyruğa eklenen iki madde** (real-öncesi / üretim-turu gündemi):
1. EVDS API anahtarı temin edilip TRY_ON_RATE'in TCMB'nin resmi kaynağıyla
   çapraz doğrulanması — real moda geçmeden ÖNCE tamamlanmalı.
2. Üretim turunda nakit bacağının GERÇEK enstrümanı netleştirilecek
   (AlgoLab'da para piyasası fonu/repo süpürme mekanizması var mı, hangi
   oranla, hangi likidite/vade kısıtlarıyla) — şu anki %0/faizli model
   yalnızca bir YAKLAŞIKLIK, gerçek enstrüman farklı davranabilir.

## KALICI KAYIT 7 — EXPANSION E2 (Motor Genelleştirme) tamamlandı (2026-07-07)
Çok-piyasa çekirdeği kuruldu (bkz. `EXPANSION_E2.md`), **DEMİR KURAL korundu:
her E2 commit'i BIST v7.1-golden'ıyla BAYT-BAYT aynı** (tests/test_golden_bist.py,
iki katman: cost_model=None + BIST CostModel carry=0). Tam süit 364 passed
(E2 öncesi 309). Kod işi tamam, kullanıcı/baş danışman değerlendirmesi bekliyor;
E3/E4/Faz 5'e geçilmedi.

**Kalıcı düzeltmeler/kararlar** (gelecek oturumlar için):
- **Hayalet-bar tarihi düzeltmesi**: EXPANSION 15.2 (04-08) ve E2 talimatı (04-09)
  "XIST tatili" varsayımı HATALI; gerçek 2024 Ramazan Bayramı XIST tatilleri
  **04-10/11/12**. Repodaki gerçek hayalet bar EREGL 2024-04-09 bir volume=0
  phantom'dur (data/cleaning.py yakalar), takvim katmanının sınıfı değil. Test
  gerçek tatilleri çapa aldı.
- **Bilinçli kapsam kararı (Bölüm 8'e uygun)**: run_backtest LONG-only bırakıldı;
  engine-seviyesi SHORT execution short-gate tasarımından (Bölüm 17 #10) sonra.
  Short MEKANİĞİ risk/direction.py'de tam test edilerek kuruldu (ayna simetrisi,
  quote-ccy, marjin). two_sided profiller short-gate tanımlanana dek aktive edilmez.
- **Ertelenenler (Faz 5 modülleri henüz yok)**: PaperBroker daily_carry, journal
  market/currency kolonları. İnşa edilince eklenecek.
- **exchange_calendars==4.13.2** eklendi (req.txt + lock birlikte). lxml eklenmedi.
- **FX boyutlama IEEE754 float duyarlı** (belgelendi): EURUSD-direkt 9374 vs
  USDJPY-conv 9375 (±1 birim, ikisi de mekanik doğru).

## KALICI KAYIT 8 — D1 üretim portu (P1) tamamlandı (2026-07-07)
KALICI KAYIT 6 ile kabul edilen D1 ailesi, spike'tan (`backtest/regime_core.py`,
REFERANS kalır) üretim yığınına taşındı ("backtest=canlı aynı fonksiyon").
Referans ölçüm REGIME_CORE_S1B.md. Bkz. `BACKTEST_REVIEW_D1_PROD.md`.
- `strategy/regime_core.py`: üretim regime-core, spike'a BAĞIMSIZ. Saf sinyal +
  saf boyutlama (TAM-LOT/artık nakit) + cash-yield + breaker.
- `strategy/family_registry.py`: StrategyFamily soyutlaması (ten_gate/regime_core,
  config'ten seçilebilir; ten_gate run_backtest'i delege eder → golden korunur).
- `backtest/run_family.py`: aile-dispatch + S1b mutabakatı.
- **Breaker (bu aile)**: ALARM -%25 (bildirim), FREEZE -%40 (yeni ENTER yok,
  çıkış serbest, reset yalnız kullanıcı). Tarihsel FREEZE=0; ALARM 4 sığ epizot
  (bildirim-only, davranış değişmez).

**MÜHÜRLÜ KRİTERLER 4/4 GEÇTİ** (mekanik doldurma; kabul kararı kullanıcının):
A) 67 anahtarlama tarihi S1b ile BİREBİR. B) CAGR/maxDD/Sharpe Δ=0 (bit-bit;
tam-lot spike'ta zaten modelli → sapma yok). C) v7.1-golden 3/3 bayt-bayt. D)
tarihsel FREEZE 0 + kuru-test yeşil. Hiçbir eşik/parametre değişmedi; Faz 5'e
geçilmedi, mode'a dokunulmadı. İki durma noktası kullanıcıda.

## KALICI KAYIT 9 — Faz 5 (paper) kullanıcı onayıyla AÇILDI (2026-07-07)
Kullanıcı 2026-07-07'de **Durma Noktası 1'i AÇTI** — Faz 5 (paper) onaylandı.
**Kapsam yalnızca paper.** Durma Noktası 2 (paper→real) AYNEN kapalı — "real'e geç"
yolu kod/komut olarak **HİÇBİR ZAMAN var olmayacak** (HARDENING B6). Bağlayıcı spec:
HARDENING.md Bölüm B (B1-B7) + CLAUDE.md Bölüm 14. Koşulan aile: `regime_core` (D1,
KALICI KAYIT 6/8) — 10-gate ailesi (`ten_gate`) donmuş referans, paper'da KOŞULMAZ.

**F5-A ↔ F5-B kırılımı** (`PHASE5_PLAN.md`): F5-A'da AlgoLab'a CANLI BAĞLANTI YOK —
tüm modüller offline, fixture/kuru-testli. Kimlik bilgisi gerektiren canlı akış F5-B.
Aşamalar: F5A-0 plan/kayıt · F5A-1 canlı veri deposu · F5A-2 PaperBroker (t+1 kapanış
yürütme) · F5A-3 mutabakat+kurtarma · F5A-4 kill-switch hiyerarşisi · F5A-5 karar
günlüğü (JSONL) · F5A-6 parite · F5A-7 izleme+Telegram iskeleti · F5A-8 AlgoLab adapter
iskeleti · F5A-9 seans/takvim · F5A-Z kapanış (PHASE5A_REVIEW.md). Her aşama: commit +
golden kanıtı + push + STATUS.

**F5-A İLERLEME (canlı takip):**
- [x] F5A-0 plan/kayıt (0b6f600) — PHASE5_PLAN.md.
- [x] F5A-1 canlı veri deposu (cf26836) — `data/live_store.py` (LiveHistoryStore),
      8 test. SQLite; snapshot bootstrap + EOD arayüzü + çapraz-kaynak tutarlılık.
- [x] F5A-2 PaperBroker + runner (18406cf) — `execution/{broker_adapter,paper_broker,
      regime_core_runner}.py`, 11 test. **PARİTE KANITI**: runner switch'leri
      run_regime_core_prod ile BİREBİR, equity rel=1e-9. Nakit tahakkuku = regime_core
      formülü (modellenmiş faiz ayrı). Restart state kurtarma. Bracket stop-önceliği.
- [x] F5A-3 mutabakat + kurtarma (a1e44ef) — `safety/reconciliation.py` (LocalLedger +
      reconcile → FREEZE, adopt yalnız kullanıcı), "emir gönderildi/yanıt yok/çöküş"
      mock testli. 5 test.
- [x] F5A-4 kill-switch hiyerarşisi (b60ede0) — `safety/kill_switch.py` (5 switch),
      eşikler `config/regime_core.yaml::safety` (D1-uyarlı, ÖNERİ). 9 kuru-test.
- [x] F5A-5 karar günlüğü (2cec791) — `journal/{masking,decision_journal}.py`, D1-uyarlı
      JSONL şema, merkezî maskeleme, runner hook. 6 test.
- [x] F5A-6 parite (4335e21) — `safety/parity.py`, offline↔canlı anahtarlama diff =
      kırmızı alarm; equity farkı parite başarısızlığı sayılmaz. 3 test.
- [x] F5A-7 izleme + Telegram (2fda861) — `notify/{telegram_bot,eod_summary}.py`,
      `safety/heartbeat.py`. config-gated, token'sız, read-only vs çift-onay, 'real'
      komutu YOK, watchdog. 16 test.
- [x] F5A-8 AlgoLab adapter iskeleti (f1e8aab) — `execution/algolab/{auth,client,
      adapter}.py`, DOĞRULANMAMIŞ (F5-B'de resmî doküman), CANLI ÇAĞRI YOK, fixture. 12 test.
- [x] F5A-9 seans/takvim (970caa2) — `config/bist_calendar.yaml` + `core/bist_calendar.py`
      (2026 doğrulandı; sürekli 10:00-18:00; yarım-gün; kütüphane tek-otorite değil;
      veri-yok toleransı). clock.py 09:55→10:00 düzeltildi. 8 test.
- [x] F5A-Z kapanış — `PHASE5A_REVIEW.md` (aşama tablosu, B1-B7 kapsama, kuru-test
      sonuçları, F5-B kullanıcı-aksiyon listesi), tam süit 456, golden bayt-bayt, push.
**F5-A TAMAMLANDI — kullanıcı/baş danışman değerlendirmesi bekliyor. F5-B onayı AYRI.**

## KALICI KAYIT 10 — F5-B1 (Gölge Paper, AlgoLab'SIZ) tamamlandı (2026-07-07)
Gölge paper döngüsü broker olmadan GERÇEK veriyle çalışır hale getirildi (bkz.
`PHASE5B1_REVIEW.md`). Teslimatlar + commit'ler:
- **(1) yfinance veri bağlama** (`data/live_feed.py`, 8d1ca1c): LiveHistoryStore'u
  yfinance EOD'a bağlar; snapshot bootstrap'ı backtest-pariteli temizlikle
  (normalize_bist_dates + evren-ghost); snapshot↔yfinance çapraz-tutarlılık. **KANIT:**
  canlı depo↔backtest kompozit 5511 günde bit-bit 0.0; snapshot↔yfinance 66132 bar-günde
  ~1e-7; kompozit+MA(200) BUGÜNE (07-07) kadar hesaplanıyor. 6 test.
- **(2) gölge scheduler** (`main.py` PaperScheduler): observe (go_live=null: sinyal/
  journal/heartbeat, İŞLEM YOK, hesap başlatılmaz) / active (operatör kararı). yfinance
  EOD retry + 'bar yok' zarafeti; kill-switch + parite işi + EOD özet + Telegram (token'sız
  log-only) bağlandı. Mutabakat GÖLGE modda harici çekimi ATLAR + loglar (iç recon çalışır).
  8 test.
- **(3) ilk-başlatma** (`initialize_flat(adopt_regime_on)`): go-live'da rejim AÇIKSA t+1
  kapanışta INITIAL_ENTER (journal özel etiket), KAPALIYSA nakit+faiz. Geriye uyumlu şema
  migration. **Gerçek-veri dry-run:** go_live=07-06 → 07-07 INITIAL_ENTER (12 sembol,
  parite OK).
- **(4) launchd + log rot. + kılavuz** (`deploy/*.plist`, `deploy/tradingbot.newsyslog.conf`,
  `OPERATOR_GUIDE.md`): bot + watchdog servisleri, log rotasyonu (journal döndürülmez),
  başlat/durdur/durum/FREEZE-temizle + observe→active geçişi (Faz 6 başlangıcı ayrı karar).
- **(5) B7-D1 önerisi** (`B7_D1_PROPOSAL.md`): 'değerlendirilen sinyal'=günlük rejim
  değerlendirmesi; D1 karne alanları. Hiçbir eşik mühürlenmedi; ÖNERİ.
- **(6) EVDS** (`tools/evds_compare.py`, `EVDS_COMPARISON.md`): anahtar VAR ama REST endpoint
  evds2→evds3 SPA'ya yönlendiriyor → BLOCKED. **Snapshot DEĞİŞMEDİ.** endpoint doğrulanınca
  script yeniden koşulur (kuyruk #18).
- **(7) gözetimli ilk koşu:** gerçek CLI observe (işlem yok) + **oluşmakta olan bar bulgusu**
  → kod-düzeyi koruma eklendi (sinyal yalnız FİNAL bardan; provisional işareti).

**Kod-düzeyi yeni koruma (F5-B1):** oluşmakta olan (kapanmamış) bar üzerinde sinyal
finalize edilmez / active'de yürütme son FİNAL güne sınırlanır. t+1 yürütmeye EK katman.
Faz 6 BAŞLATILMADI (go_live_date=null); iki durma noktası kullanıcıda; mode/eşikler/D1
fonksiyonları + v7.1-golden korundu.

## EK KAYIT — AlgoLab KAPATILDI, F5-B2 yeniden tanımlandı (2026-07-07)
**AlgoLab 2025-12-31'de KAPATILDI** (resmî mail teyidi, 2026-07-07). Sonuçlar:
- **AlgoLab canlı entegrasyonu İPTAL.** `execution/algolab/` SİLİNMEDİ — "kapatılmış-broker
  referansı" docstring notuyla işaretlendi (BrokerAdapter/throttle/maskeleme deseni emsali).
- **F5-B2 yeniden tanımı:** `ManualExecutionAdapter` — bot sinyali → Telegram bildirimi →
  kullanıcı elle yürütür → fill'ler kullanıcı onayıyla kaydedilir; B2 mutabakatı bu kayıtlara
  karşı çalışır. (Tasarım F5-B2'de.)
- **Kuyruğa eklendi:** "BIST broker REST API pazarını periyodik izle — uygun API çıkarsa
  BrokerAdapter ile entegre edilebilir."
- Bu turda başka kapsam değişikliği YOK; Faz 6 başlatılmadı, real'e adım yok.

## KALICI KAYIT 11 — F5-B1.1 (Gölge Sertleştirme, K1 kapanış) tamamlandı (2026-07-08)
Gölge paper döngüsü sertleştirildi (bkz. `PHASE5B11_REVIEW.md`). 9 madde:
- **K1** `data/cash_rate_feed.py`: TRY_ON_RATE canlı ileri besleme (snapshot READ-ONLY +
  SQLite uzantı; bayat>35g→FRED, başarısız→son değer+WARN; formül backtest ile AYNI). EOD
  özet+heartbeat_status.json'a faiz+kaynak tarihi+bayatlık. GERÇEK: FRED de 2026-03'te
  bitiyor → faiz tasarım gereği bayat (muhafazakâr); zamanlı için EVDS (#18). tz bug düzeltildi.
- **K2** Kill-switch mutabakatı (`KILLSWITCH_RECONCILIATION.md`, ölçüm runtime/f5b1/
  killswitch_measurement.json): prod backtest worst gün −11.60%, max ardışık kaybeden RT=5,
  max DD −28.43. **consecutive_losses_freeze 4→7** (maks+2), **daily_loss_limit_pct 0.08→0.12**
  (worst altı) — config+kill_switch senkron; tarihsel tetik 0. (Bunlar operasyonel SAFETY
  eşiği, ÖNERİ; strateji parametresi/kabul eşiği DEĞİL — DEĞİŞMEZLER ihlali yok.)
- **K3** catch-up: downtime'da kaçan anahtarlama → DELAYED_SIGNAL alarmı+journal etiketi.
- **K4** veri kayması: detect_drift (son 30 bar) → DATA_DRIFT (finalize yok); operatör
  `--resync` (yedek+tam çekim+force-overwrite+otomatik kompozit parite). replace_bars eklendi.
- **K5** provisional-bar iki-yön + active erteleme testleri (grace=3600s).
- **K6** INITIAL_ENTER maliyet mutabakatı: 99943.96 KUSUR DEĞİL (kısmi basket/forming-bar);
  tam barda 99852.29 = 100000−comm−slip bit-bit. **Kök-neden hardening: veri-tamlığı yürütme
  kapısı** (tüm sembollerde bar yoksa yürütme ertelenir → kısmi basket yasağı).
- **K7** OPERATOR_GUIDE §7 resync + §8 bakım penceresi + dokunulmaz modül listesi.
- **K8** `tools/evds_compare.py --csv` elle-export modu (kuyruk #18 endpoint'siz kapatılabilir).
- **K9** B7_D1_PROPOSAL iki katmanlı karne (mekanik ≥4hafta + olay ≥2 tatbikat); tatbikat
  implementasyonu YAPILMADI (öneri).
Tam süit **485 passed** (F5-B1 470 + 15); golden 3/3 her commit. mode/N/b/M/snapshot/D1
fonksiyonları DEĞİŞMEDİ. Faz 6/real/launchd'ye adım YOK; iki durma noktası kullanıcıda.

## KALICI KAYIT 12 — F5-B2a (Telegram canlı bildirim + operasyon) tamamlandı (2026-07-08)
F5-B2'nin **bildirim yarısı** (bkz. `PHASE5B2A_REVIEW.md`). 6 madde, her biri ayrı commit:
- **m1** `notify/telegram_bot.py`: `make_http_sender` (Bot API sendMessage, timeout + 3 deneme
  + üstel bekleme; kalıcı hatada istisna). `TelegramNotifier` enabled+token(env)+chat_id ise
  HTTP kurar; hata YAKALANIR → logger WARN, send False → **günlük döngü ASLA kırılmaz**. Token
  YOKSA log-only AYNEN. main.py + watchdog logger bağlandı. 7 test (mock HTTP). Gerçek test
  mesajı: secrets.env TELEGRAM_TOKEN BOŞ → atlandı.
- **m2** Alarm+EOD kablolaması zaten mevcut (F5-B1); kuru-test eklendi (mock FREEZE + mock
  DATA_DRIFT → gönderim + journal alarm kanıtı; EOD gönderimi). 2 test.
- **m3** launchd K5-grace doğrulaması: paper plist 19:30 Istanbul (18:00+3600s=19:00 final,
  25dk marj; TR kalıcı UTC+3). Hatalı "~1.5s grace" yorumu düzeltildi. OPERATOR_GUIDE §2a
  zaman çizelgesi + 'bar yok' veri-tamlığı ertelemesi + koşu-içi retry yokluğu.
- **m4** "bayat=muhafazakâr" GENELLEME DEĞİL: yön faiz patikasına bağlı (yükseliş→muhafazakâr,
  DÜŞÜŞ→abartır/agresif). PHASE5B11_REVIEW + STATUS #18 düzeltildi. Kod değişikliği YOK.
- **m5** GERÇEK EVDS CSV (`runtime/manual/evds_export.csv`, TLREF 1860 satır) koşuldu.
  BULGU: EVDS sistematik ~2-6p YÜKSEK (seri-tanım farkı); 2023 boşluğu EVDS'de 12/12 DOLU
  (2023-11 baseline ff 23.5 vs EVDS 41.45); 2022-10 %9.0 baseline dip'i EVDS'de YOK (artefakt
  teyit). **Snapshot DEĞİŞMEDİ.** Araç fix: value_col otomatik seçimi boş 'Unnamed' kolonu
  alıp sessizce 0 satır okuyordu → sayısal-değerli son kolon (+1 test). Rapor: EVDS_COMPARISON.md.
- **m6** kapanış: bu kayıt + PHASE5B2A_REVIEW.md, tam süit 494 passed, golden 3/3, push.
Faz 6/real/launchd'ye adım YOK; iki durma noktası kullanıcıda.

## KALICI KAYIT 13 — F5-B2a.1 (Telegram teşhis + sessiz düşüş sertleştirme) tamamlandı (2026-07-08)
Kullanıcı gerçek Telegram token+chat_id'yi girdikten sonra bot bunları BOŞ görüyordu.
Teşhis + düzeltme + sertleştirme (bkz. `PHASE5B2A_REVIEW.md` "B2a.1 Eki"):
- **Kök neden**: kod (main.py/safety/heartbeat.py/tools/evds_compare.py/core/config.py)
  yalnızca `config/secrets.env`'i okur (hard-code path); kullanıcı değerleri **repo
  kökündeki farklı bir `secrets.env`'e** yazmıştı — format sorunu değil, YANLIŞ KONUM.
  Bu, oturum boyunca **3 kez tekrarlandı** (her BotFather güncellemesinde tekrar kök
  dizine yazıldı) → OPERATOR_GUIDE §0'a "doldurulacak dosya BUDUR, kök değil" uyarısı
  eklendi. Ayrıca token değerinde **2 ayrı seferde gömülü boşluk** bulundu (muhtemelen
  BotFather sohbet balonundan satır-kaydırmalı kopyalama artefaktı) — programatik
  temizlendi (değer hiçbir zaman yazdırılmadan).
- **`--test-telegram` CLI** (main.py): config yükler, `notifier_status()` ile durumu
  raporlar (ACTIVE/LOG-ONLY+neden), ACTİFse maskeli test mesajı gönderir, exit code
  yansıtır. OPERATOR_GUIDE §5a.
- **Sessiz-düşüş sertleştirme**: `telegram.enabled=true` ama token/chat_id okunamazsa
  artık (a) başlangıçta belirgin WARN journal'a düşer, (b) her EOD özetinde ve
  `heartbeat_status.json`'da kalıcı `TELEGRAM: ACTIVE` / `TELEGRAM: LOG-ONLY (neden)`
  satırı var — konfig-niyet ↔ çalışma-durumu uyuşmazlığı bir daha SESSİZ kalamaz.
  13 yeni test (notifier_status, EOD satırı, scheduler silent-drop, CLI 4 senaryo).
- **Secrets hijyeni (STATUS #9 KAPANDI)**: `.gitignore`'a genel `secrets.env`/`*.env`/
  `runtime/manual/` deseni eklendi (`config/secrets.env.example` istisna);
  `git log --all -- secrets.env` (+ `config/secrets.env`) ile hiçbir secrets dosyasının
  hiçbir commit'te yer almadığı doğrulandı.
- **GERÇEK uçtan-uca kanıt**: `--test-telegram` BAŞARILI (kullanıcı telefonunda mesajı
  doğruladı). Ardından gerçek bir manuel `--refresh --cycle` (observe, 2026-07-08) koşuldu:
  EOD özeti gerçekten Telegram'a gönderildi (`heartbeat_status.json`: `telegram.state=
  ACTIVE`, journal'da gönderim-hatası WARN'ı YOK). **Yan gözlem** (kapsam DIŞI, K4'ün
  ÖNCEDEN VAR olan davranışı): aynı cycle'da ASELS 2026-07-07 için 3 bar sapması
  DATA_DRIFT (CRITICAL) alarmı tetiklendi ve Telegram'a gitti — sinyal bu yüzden
  FİNALİZE EDİLMEDİ (observe modda zaten işlem yok, etkisi yok). Operatör isterse
  OPERATOR_GUIDE §7 `--resync` uygulayabilir; bu turun kapsamı dışında, aksiyon
  alınmadı.
- **Güvenlik olayı (dürüstçe kayıt)**: bir teşhis komutu (`xxd` ham dosya kontrolü)
  yanlışlıkla gerçek token değerini bu oturumun çıktısına yazdırdı (kural ihlali,
  fark edilir edilmez durduruldu). Kullanıcıya hemen bildirildi; kullanıcı BotFather'da
  token'ı **iptal edip yeniledi** (kendi kararıyla). Sonraki tüm teşhis yalnızca
  yapısal/maskeli kontrollerle (uzunluk, karakter sınıfı, HTTP durum kodu) yapıldı —
  değer bir daha hiçbir çıktıya yazılmadı.
Tam süit **507 passed** (F5-B2a 494 + 13 yeni); golden 3/3 her commit. `mode`/eşikler/
`regime_core.py`/`data/snapshots/` DEĞİŞMEDİ. Faz 6/real/launchd'ye adım YOK; iki durma
noktası kullanıcıda.

## KALICI KAYIT 14 — US otonomi hattı önceliklendirildi (kullanıcı kararı, 2026-07-08)
Kullanıcı 2026-07-08'de sıralamayı belirledi:
**US otonomi hattı önceliklendirildi: sıra E4 (US adil test) → geçerse US gölge
paper → geçerse E3 broker adapter (tam otonomi hedefi).**
- **BIST D1'de risk artırımı talebi disiplin #10 gereği REDDEDİLDİ**; D2 agresif
  profil, D1 GERÇEK sicili oluşana dek KAPALI.
- **BIST yarı-otomatik hat (ManualExecutionAdapter, F5-B2) DEĞİŞMEDİ** — bu karar
  onu ne hızlandırır ne değiştirir.
- E4 kapsamı: (A) dondurulmuş 10-gate ailesinin ABD'de adil referans testi
  (donmuş huni, hüküm yok), (B) D1'in (regime_core mantığı) US sepetinde spike'ı
  — USD-cinsi sleeve'in temeli. Offline araştırma; canlı bot modüllerine (mode:
  paper dahil) dokunulmaz; N/b/M mühürlü; v7.1-golden korunur.
- **Bu kayıt otomatik geçiş anlamına GELMEZ**: E4 sonrası US gölge paper'a geçiş,
  ve sonrasında E3, AYRI kullanıcı/baş danışman onayları gerektirir. İki durma
  noktası (Faz 4 backtest değerlendirmesi + gerçek sermaye) aynen kullanıcıda.

## KALICI KAYIT 15 — EXPANSION E4 (US ADİL TEST) tamamlandı (2026-07-08)
Offline araştırma turu (bkz. `EXPANSION_E4.md` + `E4_CRITERIA.md`). İki amaç:
(A) dondurulmuş 10-gate ailesinin ABD'de adil referansı, (B) D1 (regime_core)
mantığının US sepetinde spike'ı. **Mühürleme koşumdan ÖNCE** (ayrı commit
`cdf8100`, strateji kodu HENÜZ yokken); mühürlü tablo ESNETİLMEDİ.

**Kararlar/değişmezler:** N/b/M = 200/%1/3 mühürlü (S1b), AYNEN kullanıldı —
parametre taraması/varyant seçimi YOK (disiplin #3). Nakit bacağı = **%0
(muhafazakâr, madde 1)**: mevcut US aux faiz serisi yok → `cash_rate=None`
(S1b mekanizmasıyla %0'da bayt-eşdeğer). Referans benchmark = **eşit-ağırlık
US sepeti** (survivorship-şişirilmiş → yüksek çıta; SPY yalnız bilgilendirici).

**Veri:** US snapshot 2026-07-06 (20 sembol, 2005-01-03→2026-07-02, 5408 gün,
0 hayalet-bar). `load_and_clean_universe` DEĞİŞMEDEN reuse (normalize_bist_dates
US 00:00-UTC'de NO-OP; test'le çapa). SPY dondurulmuş snapshot (us_bench/
2026-07-08, sha256+manifest, deterministik).

**MEKANİK SONUÇ — mühürlü 4-kriter (referans=sepet):**
1) USD Sharpe > sepet 0.8561 → 0.726 **FAIL**.
2) tam-dönem |maxDD| ≤ 23.14% → 23.11% **PASS** (razor-thin).
3a) OOS aylık-Sharpe > sepet 0.9154 → 0.669 **FAIL**.
3b) OOS |maxDD| ≤ 14.96% → 20.41% **FAIL**.
→ **1/4 geçti; D1-US US-referansta kabul adayı DEĞİL** (önceden mühürlenen
"4/4 yoksa red, dar-fark yok" kuralının mekanik uygulaması — HÜKÜM değil).
4) Uçurum kontrolü: N/b/M komşuluğunda süreklilik, uçurum YOK; mühürlü nokta
komşuluğun ALT tarafında (US'e optimize EDİLMEDİ — overfitting-karşıtı gözlem).
D1-US ana: CAGR +8.19%, maxDD -23.11%, Sharpe 0.726, 57 switch; MC dd_p5 -33.5%.

**Bulgu (BIST-USD ile tutarlı):** regime-filtre drawdown'ı sepetin ~yarısına
indiriyor (sermaye-koruma tutuyor) ama survivorship-şişirilmiş sepetin
Sharpe'ını GEÇMİYOR — S1b (f)'deki USD-terim yapının birebir tekrarı. Not:
D1-US, SPY'a karşı (gerçekçi/kurulabilir endeks) Sharpe'ı GEÇİYOR (0.726>0.640)
ve DD çok daha sığ — ama mühürlü referans SEPET, değiştirilemez.

**10-gate US adil referansı (RAPOR-only, kabul kapısı DEĞİL):** 21 yılda
~düz-negatif (CAGR -%0.11, Sharpe -0.089, PF 0.88, %94.5 nakit) → BIST'te
reddedilen ailenin US'te de zayıf olduğunun teyidi (bilinen-sorun #6 tutarlı).

**İzolasyon:** `mode: paper` + canlı bot modülleri (strategy/regime_core.py,
execution/, safety/, data/live_*, notify/, main.py, config/regime_core.yaml,
config/config.yaml) DOKUNULMADI. S1/S1b simülatörü (backtest/regime_core.py)
DEĞİŞMEDİ — yeni US döngüsü (backtest/regime_core_us.py) onu İTHAL eder; parite
~3e-15. v7.1-golden 3/3; tam süit **517 passed** (511+6). **Karar
kullanıcının/baş danışmanın; otomatik geçiş YOK; iki durma noktası kullanıcıda.**

## KALICI KAYIT 16 — EXPANSION E4b (D1-US nakit bacağı ölçüm-tamamlama) tamamlandı (2026-07-08)
E4'ün (KAYIT 15) S1→S1b emsali nakit-getiri düzeltmesi (bkz. `EXPANSION_E4B.md`).
**Tek davranış değişikliği = nakit tahakkuku:** US 3-aylık T-bill (FRED DGS3MO,
günlük, dondurulmuş `data/snapshots/aux_us/2026-07-08/`, sha256'lı; 5380 gözlem,
max boşluk 4g, uzun boşluk 0), **50bp haircut** (muhafazakâr — para-piyasası fonu
gider+sürtünme; gerekçe koşumdan ÖNCE mühürlendi). Tahakkuk = S1b/TRY yapısı
(r_net=max(rate−haircut,0), ACT/365).

**SON-BAKIŞ KURALI** (koşumdan ÖNCE `E4_CRITERIA.md` §4'e mühürlendi, ayrı commit):
D1-US'in aynı tarihçeye İKİNCİ ve SON bakışı; E4 mühürlü tablosu/eşikleri/referansı
(SEPET) AYNEN; benchmark değişikliği/SPY'a geçiş YASAK (kriter-alışverişi). 4/4
geçerse US-kabul adayı; herhangi biri kalırsa KESİN RED, üçüncü bakış YOK.

**AYRIŞTIRMA (faizin izole katkısı, tek-değişiklik — switch'ler 57'de BİREBİR AYNI):**
nakitte %24.3 gün; CAGR 8.19→**8.60%** (+0.41pp); Sharpe 0.726→**0.758** (+0.032);
maxDD ~değişmedi (−4e-5 marj daha derin — düşüş-öncesi tepe yükseldi). US nakit-only
CAGR ~%1.51 (S1b'deki TRY ~%13.77'nin niceliksel karşıtı — faiz KÜÇÜK).

**MÜHÜRLÜ TABLO (E4b faizli, MEKANİK, referans=sepet):** 1) Sharpe 0.758 > 0.8561?
**FAIL**. 2) |maxDD| 23.11% ≤ 23.14%? **PASS** (razor-thin). 3a) OOS Sharpe 0.692 >
0.9154? **FAIL**. 3b) OOS |maxDD| 20.42% ≤ 14.96%? **FAIL**. → **1/4 (E4 ile AYNI
tablo).** Faiz Sharpe'ları itti ama survivorship-şişirilmiş sepetin ~0.10 puan
çıta açığını kapatmadı. MC(faizli) dd_p5 -32.6%.

**→ MEKANİK SONUÇ (SON-BAKIŞ KURALININ uygulaması): D1-US ailesi US-referansta
KESİN REDDEDİLDİ. Dönüş yolu KAPALI.** D1 mantığı ancak gelecekte AYRI bir
tasarımın (farklı çekirdek/evren) risk-katmanı adayı olarak, YENİ ve ayrıca
mühürlenmiş kriterlerle gündeme gelebilir — D1-US ailesinin kendisinin yeniden
değerlendirilmesi DEĞİL. Bu bir HÜKÜM değil, önceden mühürlenen kuralın mekanik
sonucudur; nihai kayıt kullanıcının/baş danışmanın.

**İzolasyon:** `mode: paper` + canlı bot modülleri + `backtest/regime_core.py`
(S1/S1b simülatörü) + config/config.yaml + config/regime_core.yaml DOKUNULMADI.
Yeni: `tools/build_us_rate_snapshot.py`, `tools/run_regime_core_us_e4b.py`,
`backtest/regime_core_us.py`'ye haircut param (default 0.02=S1b; cash_rate=None iken
etkisiz → E4 %0 reprodüksiyonu korundu). v7.1-golden 3/3; tam süit **522 passed**
(517+5). Faz 6/real/launchd/go_live'a adım YOK; iki durma noktası kullanıcıda.

## KALICI KAYIT 17 — D2-US (kesitsel momentum ailesi) tasarım+spike turu AÇILDI (2026-07-08)
**Baş danışman kaydı (2026-07-08): D1-US KESİN RED onaylandı (E4b, son-bakış kuralı).
D2-US (kesitsel momentum) tasarım+spike turu AÇILDI — US-only, otonomi hedefli hat.**

D1-US'in (rejim-filtreli çekirdek) US-referansta kesin reddi (KAYIT 16, mühürlü tablo
1/4) üzerine, D1 mantığının US'e "geri dönüşü" DEĞİL — YAPISAL YENİ bir aile açıldı:
**D2-US = 12-1 kesitsel (cross-sectional) momentum + FIP information-discreteness seçimi
+ pozisyon-bazlı mutlak-momentum (dual-momentum) nakit kapısı + 6-ay realize vol hedefleme.**
Getiri-arayan bir aile (D1 sermaye-koruma odaklıydı); bu yüzden kriter 2 = CAGR>sepet
bir VARLIK şartıdır (E4/D1'de yoktu).

**Turun disiplini (E4 izolasyonu AYNEN):**
- Offline araştırma. `mode: paper` + TÜM canlı bot modülleri (strategy/regime_core.py,
  execution/, safety/, data/live_*, notify/, main.py, config/config.yaml,
  config/regime_core.yaml) + S1/S1b/E4 araçları (backtest/regime_core.py,
  backtest/regime_core_us.py, tools/run_regime_core*.py, tools/e4_common.py,
  config/regime_core_us.yaml) DOKUNULMAZ.
- BIST v7.1-golden her commit 3/3 bayt-bayt. Her madde AYRI commit + push.
- **Grid/varyant SEÇİMİ YASAK** (disiplin #3): tasarım TEK paket olarak, koşumdan ÖNCE
  mühürlenir; koşum sonucuna göre bileşen seçilmez. Ablasyon YALNIZ bilgi/atıf amaçlı.
- **Benchmark referansı koşumdan ÖNCE mühürlenir, sonradan DEĞİŞTİRİLEMEZ** (E4 §4 emsali).
- HÜKÜM YOK; kabul kararı kullanıcının/baş danışmanın. Faz 6/real/launchd/go_live adımı YOK;
  iki durma noktası kullanıcıda.

Sıra (her biri ayrı commit): (0) bu kayıt → (1) US2 evreni ~50 sembol dondurma +
DATA_AUDIT_US2.md + survivorship → (2) benchmark (US2 eşit-ağırlık sepet + SPY bilgi) +
D2US_CRITERIA.md MÜHÜR → (3) tasarım sabitleri (aynı mühür commit'i) → (4) spike koşumu +
mekanik tablo + crash/turnover/ablasyon/komşuluk → (5) D2_US_S1.md + kapanış. **DUR.**

## KALICI KAYIT 18 — D2US-S1 (kesitsel momentum spike) TAMAMLANDI (2026-07-08)
D2-US (kesitsel momentum) ailesinin tek-tur değerlendirme spike'ı tamamlandı (bkz.
`D2_US_S1.md`, `D2US_CRITERIA.md`, `DATA_AUDIT_US2.md`). Tasarım koşumdan ÖNCE TEK
paket olarak mühürlendi (E4 §4 kilidi emsali); grid/varyant seçimi YAPILMADI.

**Mühürleme (koşumdan ÖNCE, ayrı commit `c081b19`):** referans = eşit-ağırlık US2
sepeti al-tut (maliyetsiz; SPY yalnız bilgi, SPY'a geçiş KALICI YASAK). Mühürlü 4
kriter: (1) Sharpe>sepet 0.8035; (2) CAGR>sepet 0.13836 (getiri-arayan VARLIK şartı,
D1/E4'te yoktu); (3a) OOS aylık-Sharpe>sepet 0.8310; (3b) tam-dönem |maxDD|≤sepet
45.54%. Kural: 1+2+3a+3b TAMAMI→aday; biri kalırsa red, dar-fark YOK.

**MEKANİK SONUÇ (referans=sepet):** D2-US ana: CAGR 10.87%, Sharpe 0.7254, maxDD
-32.61%, 246 rebalans; OOS aylık-Sharpe 0.7697, OOS maxDD -25.20% (39 pencere); MC
dd_p5 -36.1%. **MÜHÜRLÜ TABLO: (1) FAIL (0.725<0.804); (2) FAIL (10.87%<13.84%);
(3a) FAIL (0.770<0.831); (3b) PASS (32.6%≤45.5%) → 1/4.** → önceden mühürlenen
kurala göre **D2-US US-referansta kabul adayı DEĞİL** (HÜKÜM değil; karar kullanıcının).

**Zorunlu analizler:** (a) crash — 2009 rebound strat -0.8% vs sepet +51% (abs-kapı
~8.9/10 nakit); 2020 rebound strat +26.6% vs sepet +68.7% (vol maruziyet ~0.42) →
savunma katmanları toparlanmayı kaçırdı. (b) turnover ~588%/yıl ama maliyet sürüklemesi
yalnız ~33bps/yıl (zayıflık maliyet kaynaklı DEĞİL). (c) ablasyon (yalın 0.60→+FIP 0.74
→+kapı 0.76→+vol 0.73) BİLGİ-only — en iyi varyant (V2, 0.76) BİLE kriter 1'i geçmiyor
(karar tek katmana bağlı değil). (d) komşuluk uçurumsuz, mühürlü nokta zirve değil
(overfitting-karşıtı). Dürüst çekince: dar large-cap evreninde momentum edge'i zayıf +
survivorship (sepet gerçek-üstü) — sonuç bir ALT sınır.

**İzolasyon:** `mode: paper` + canlı bot modülleri + S1/S1b/E4 araçları
(backtest/regime_core*.py, tools/run_regime_core*.py, tools/e4_common.py,
config/regime_core*.yaml) DOKUNULMADI. Yeni BAĞIMSIZ: `backtest/xsec_momentum.py`,
`tools/{build_us2_snapshot,run_xsec_momentum_us2}.py`, `config/momentum_us2.yaml`,
`data/snapshots/us2/2026-07-08/`. v7.1-golden her commit 3/3; tam süit **530 passed**
(522+8). Faz 6/real/launchd/go_live'a adım YOK; iki durma noktası kullanıcıda.
**Kabul kararı kullanıcının/baş danışmanın; otomatik geçiş YOK.**

## KALICI KAYIT 19 — D2-US baş danışman kaydı: RED onaylandı, US2 tarihçesi KAPALI (2026-07-08)
Baş danışman kaydı (2026-07-08): D2-US (kesitsel momentum) US-referansta RED onaylandı
(D2US-S1 mühürlü tablo 1/4; D2US_CRITERIA.md §3/§5 kuralının uygulaması). Ölçüm tek
turda TAMDI (maliyet+nakit+OOS+MC+crash+turnover dahil) → E4b-tarzı ikinci ölçüm-bakışı
YOKTUR; bu tarihçede her yeniden-koşum tasarım değişikliği sayılır ve varyant-seçimi
yasağına girer. US2 tarihçesine bakış sayacı: 1 kullanıldı, D2 ailesi bu tarihçede
KAPALI. Ders-1 (metodoloji): target_vol'un sepet TAM-DÖNEM realize volünden türetilmesi
hafif look-ahead'dir (mühür-öncesi ve strateji-bağımsız olsa da); gelecek tasarımlarda
trailing/expanding vol veya ex-ante sabit kullanılacak — bu turun sonucunu DEĞİŞTİRMEZ
(en iyi ablasyon varyantı V2 bile kriter 1'i geçmiyor). Ders-2 (yapısal): V0 yalın 12-1
top-10 seçimi sepetin ALTINDA (CAGR 10.22%<13.84%, Sharpe 0.602<0.804) → dar 50'lik
mega-cap evrende kesitsel seçim alfası NEGATİF; zayıflık savunma katmanlarında değil
evren genişliğinde. Sıradaki adım: US3 point-in-time evren VERİ FİZİBİLİTESİ (strateji
tasarımı değil).

## KALICI KAYIT 20 — D4-US (varlık-sınıfı ETF dual-momentum ailesi) tasarım+spike turu AÇILDI (2026-07-08)
**Baş danışman kararı (2026-07-08):** US3 tek-hisse point-in-time yolu ERTELENDİ
(DATA_FEASIBILITY_US3 bulgusu: ücretsiz kurulamıyor; ücretli yol seçilirse satın alma
ÖNCESİ EODHD paket-kapsam doğrulaması zorunlu — kuyruğa eklendi, madde #21). Yerine
**D4-US açıldı: varlık-sınıfı ETF dual-momentum ailesi** — D2 Ders-2'nin (kesitsel
dağılım yokluğu; KALICI KAYIT 19) evren-SINIFI değişikliğiyle cevabı: tek-hisse dar
mega-cap evreni yerine 10 varlık-sınıfı ETF'i (US large/small-cap, gelişmiş/gelişen
uluslararası, GYO, uzun/orta vadeli Hazine, yatırım-yapılabilir kredi, altın, geniş emtia).

**Neden bu aile (yapısal gerekçe):**
- **D2 Ders-2'ye doğrudan yanıt:** dar 50-mega-cap evrende kesitsel seçim alfası
  NEGATİFTİ (V0 yalın seçim sepetin altında); varlık sınıfları ARASINDA (düşük
  korelasyonlu, farklı rejim-duyarlı) momentum dağılımı literatürde (Faber "GTAA",
  Antonacci "GEM") YAPISAL olarak daha güçlüdür — zayıflık savunma katmanlarında değil
  EVREN GENİŞLİĞİNDEYDİ, bu tur o eksene müdahale eder.
- **Survivorship'siz + yatırılabilir dürüst referans:** 10 ETF bugün de dün de var olan,
  gerçekten AL-tut edilebilir enstrümanlar → eşit-ağırlık sepet referansı
  survivorship-şişirilmiş DEĞİL (D2/E4'ün US-hisse sepetinin en büyük zaafı — bilinen
  sorun #13 — bu evren-sınıfında YAPISAL olarak kapanır; hafif ETF-düzeyi survivorship
  notu DATA_AUDIT_ETF.md'de).
- **Disiplin #10 meşru kaldıracı:** YENİ örneklem/evren-sınıfı — geçmiş turların (D1-US,
  D2-US) reddine "geri dönüş" değil, ayrıca ve yeniden mühürlenen bir ailedir.
- **Ders-1 uygulandı (KALICI KAYIT 19):** D2'de target_vol'ün sepet tam-dönem realize
  volünden türetilmesi hafif look-ahead'di → **vol-hedefleme katmanı bu pakette YOK.**
  Yalın dual-momentum (12-0 mutlak+göreli momentum), kaldıraçsız, LONG-only.

**Turun disiplini (E4/D2US izolasyonu AYNEN):**
- Offline araştırma. `mode: paper` + TÜM canlı bot modülleri (strategy/regime_core.py,
  execution/, safety/, data/live_*, notify/, main.py, config/config.yaml,
  config/regime_core.yaml) + S1/S1b/E4/D2US araçları (backtest/regime_core*.py,
  backtest/xsec_momentum.py, tools/run_regime_core*.py, tools/e4_common.py,
  tools/run_xsec_momentum_us2.py, config/regime_core*.yaml, config/momentum_us2.yaml)
  + TÜM mevcut snapshot'lar DEĞİŞTİRİLMEZ. e4_common/run_regime_core fonksiyonları
  YALNIZ import edilerek yeniden kullanılır (D2US emsali — drift imkânsız).
- BIST v7.1-golden her commit 3/3 bayt-bayt. Her madde AYRI commit + push.
- **Grid/varyant SEÇİMİ YASAK** (disiplin #3): tasarım TEK paket, koşumdan ÖNCE
  mühürlenir; ablasyon/komşuluk YALNIZ bilgi. Benchmark referansı koşumdan ÖNCE
  mühürlenir, sonradan DEĞİŞTİRİLEMEZ (E4 §4 emsali).
- **Ölçüm bu turda TAM** (maliyet+nakit+OOS+MC dahil); D2 emsali — E4b-tarzı ikinci
  ölçüm-bakışı bu aile için YOKTUR (her yeniden-koşum tasarım değişikliği sayılır,
  varyant-seçimi yasağına girer). Mühre yazılır.
- HÜKÜM YOK; kabul kararı kullanıcının/baş danışmanın. Faz 6/real/launchd/go_live
  adımı YOK; iki durma noktası kullanıcıda.

**Evren (10 sembol, SABİT — ikame YASAK):** SPY (US large-cap), IWM (US small-cap),
EFA (gelişmiş uluslararası), EEM (gelişen piyasalar), VNQ (US GYO), TLT (20+ yıl
Hazine), IEF (7-10 yıl Hazine), LQD (yatırım-yapılabilir kredi), GLD (altın), DBC
(geniş emtia). Total-return (temettü-dahil) — tahvil ETF'lerinde fiyat-only ciddi hata.

Sıra (her biri ayrı commit): (0) bu kayıt → (1) ETF evreni dondurma + DATA_AUDIT_ETF.md
(longName kimlik doğrulaması + kapsam + aux teyidi) → (2+3) benchmark (10-ETF
eşit-ağırlık sepet al-tut + SPY bilgi) + D4US_CRITERIA.md MÜHÜR + tasarım sabitleri
(koşumdan ÖNCE, ayrı commit — commit sırası kanıt) → (4) spike koşumu (BAĞIMSIZ
backtest/dual_momentum_etf.py modülü) + mekanik tablo + crash/turnover/ablasyon/
komşuluk → (5) D4_US_S1.md + kapanış. **DUR.**

## KALICI KAYIT 21 — D4US-S1 (varlık-sınıfı ETF dual-momentum spike) TAMAMLANDI (2026-07-08)
D4-US (varlık-sınıfı ETF dual-momentum) ailesinin tek-tur değerlendirme spike'ı tamamlandı
(bkz. `D4_US_S1.md`, `D4US_CRITERIA.md`, `DATA_AUDIT_ETF.md`). Tasarım koşumdan ÖNCE TEK
paket olarak mühürlendi (E4 §4 / D2US §5 kilidi emsali); grid/varyant seçimi YAPILMADI.

**Mühürleme (koşumdan ÖNCE, ayrı commit `caa21f5` — strateji kodu HENÜZ yokken):** referans
= eşit-ağırlık 10-ETF sepeti al-tut (maliyetsiz, total-return; SPY yalnız bilgi, SPY'a geçiş
KALICI YASAK). Mühürlü 4 kriter: (1) Sharpe>sepet 0.6164; (2) CAGR>sepet 0.066957
(getiri-arayan VARLIK şartı); (3a) OOS aylık-Sharpe>sepet 0.5796; (3b) tam-dönem
|maxDD|≤sepet 34.53%. Kural: 1+2+3a+3b TAMAMI→aday; biri kalırsa red, dar-fark YOK,
üçüncü-bakış YOK (ölçüm bu turda TAM: maliyet+nakit+OOS+MC dahil; E4b-tarzı ikinci
ölçüm-bakışı bu ailede YOK).

**Evren (10 ETF, SABİT, kimlik longName ile doğrulandı 10/10):** SPY IWM EFA EEM VNQ TLT
IEF LQD GLD DBC; TOTAL-RETURN (auto_adjust; tahvil ETF'lerinde fiyat-only ciddi hata);
kompozit t0=2006-02-06 (DBC bağlar), 5136 gün, 0 hayalet/0 ffill/0 sıçrama. Survivorship
YAPISAL olarak küçük (varlık sınıfı iflas etmez → dürüst/yatırılabilir sepet çıtası; bilinen
sorun #13 bu evren-sınıfında büyük ölçüde kapanır). aux DGS3MO (2005-01-03) evren t0-12ay
(2005-02-06) öncesine uzanıyor ✓ (AYNEN reuse).

**MEKANİK SONUÇ (referans=sepet):** D4-US ana: CAGR 6.667%, Sharpe 0.5462, maxDD -25.72%,
233 rebalans, nihai equity 373,449; OOS aylık-Sharpe 0.3987 (36 pencere, 216 ay); MC dd_p5
-38.67%. **MÜHÜRLÜ TABLO: (1) FAIL (0.546<0.616); (2) FAIL (6.667%<6.696%, 0.03pp); (3a)
FAIL (0.399<0.580); (3b) PASS (25.7%≤34.5%) → 1/4.** → önceden mühürlenen kurala göre
**D4-US US-referansta kabul adayı DEĞİL** (HÜKÜM değil; karar kullanıcının).

**Zorunlu analizler:** (a) kriz — GERÇEK savunmacı rotasyon (D2'nin AKSİNE): GFC -8.0% vs
sepet -18.5% (GLD/TLT/IEF/DBC güvenli-liman rotasyonu), COVID +5.0% vs +2.5%, 2022 -4.7%
vs -17.0% (DBC/emtia rotasyonu — dual-momentum tezi ÇALIŞIYOR); bedel 2009 rebound gecikmesi
(+11% vs +34%). (b) turnover 4.84×/yıl, maliyet ~26bps/yıl (zayıflık maliyet kaynaklı DEĞİL).
(c) ablasyon V0 yalın 0.565→V1 +kapı 0.546 (kapı hafif zararlı; kapısız V0 BİLE kriter 1'i
geçmiyor → karar tek katmana bağlı değil). (d) komşuluk uçurumsuz + mühürlü nokta ZİRVE
DEĞİL (formation-6=0.671, top-4=0.593 daha iyi → overfitting-karşıtı); yapısal örüntü:
top-N↑→Sharpe↑ (diversifiye evrende KONSANTRASYON çeşitlendirmeyi kaybettiriyor). Dürüst
çekince: diversifiye varlık-sınıfı sepetini risk-ayarlı geçmek zor + varlık-sınıfı
momentumunun 2015-sonrası zayıflaması. **Üç aile (D1/D2/D4-US) da mekanik 1/4; D4-US
referansa EN YAKIN + EN SAVUNMACI** (bilgilendirici, kabul değil).

**İzolasyon:** `mode: paper` + canlı bot modülleri + S1/S1b/E4/D2US araçları
(backtest/regime_core*.py, backtest/xsec_momentum.py, tools/run_regime_core*.py,
tools/e4_common.py, tools/run_xsec_momentum_us2.py, config/regime_core*.yaml,
config/momentum_us2.yaml) DOKUNULMADI. Yeni BAĞIMSIZ: backtest/dual_momentum_etf.py,
tools/{build_etf_snapshot,run_dual_momentum_etf}.py, config/dual_momentum_etf.yaml,
data/snapshots/etf_us/2026-07-08/. e4_common/run_regime_core fonksiyonları YALNIZ import
edilerek reuse (drift imkânsız). v7.1-golden her commit 3/3; tam süit **541 passed** (530+11).
Faz 6/real/launchd/go_live'a adım YOK; iki durma noktası kullanıcıda. **Kabul kararı
kullanıcının/baş danışmanın; otomatik geçiş YOK.**

## KALICI KAYIT 22 — D4-US baş danışman hüküm kaydı + US hattı askı kaydı (2026-07-09)
**Baş danışman kaydı (2026-07-09):** D4-US US-referansta RED onaylandı (D4US-S1 mühürlü
tablo 1/4; kriter 2'nin 0.03pp'lik dar farkı kural gereği FAIL'dir ve sonucu değiştirmez
— kriter 1 ve 3a geniş farkla kalmıştır). İkinci ölçüm-bakışı YOK (mühürde kapalı). ETF
tarihçesine bakış sayacı: 1 kullanıldı; D4 ailesi ve TÜM varyantları bu tarihçede
KAPALI. Komşuluk gözlemi (formation-6: Sharpe 0.671 / CAGR 8.68% / maxDD -23.6%; top-4:
0.593) İN-SAMPLE'dır — sonuç görüldükten sonra komşuluğun en iyisini yeni-aile diye aynı
tarihçede koşmak varyant-seçimi yasağının ihlalidir; meşru tek test ileri-zaman yeni
örneklemdir, o da kabul edilmemiş stratejiye açılmaz.

**ÜÇ-AİLE META BULGUSU:** D1-US/D2-US/D4-US üç farklı mekanizma, üçü de 1/4; üçünde de
3b PASS (DD-kesme gerçek), 1 ve 3a FAIL (dürüst diversifiye referansa karşı risk-ayarlı
getiri edge'i yok). BIST-D1'in 4/4'ü istisna değil açıklamalı: yüksek TL nakit faizi +
BIST rejim yapısı filtreye gerçek değer veriyor; USD'de bu iki koşul yok.

**KARAR:** US AKTİF AİLE ARAMASI ASKIDA. Yeniden açılma yalnız kullanıcı kararıyla ve
yalnız iki yapısal kaldıraçtan biriyle olur: (i) kuyruk #21 tek-hisse point-in-time yolu
(ücretli veri; ilk adım satın alma DEĞİL, EODHD kapsam doğrulaması), (ii) short-gate
tasarım turu. **Ana odak: BIST Faz 6 (K1.5 2/2 → G1 launchd → ölçüm dönemi).**

Kod/koşum/snapshot değişikliği YOK bu turda — yalnız STATUS.md kaydı. İzolasyon aynen
(canlı bot modülleri + S1/S1b/E4/D2US/D4US araçları + tüm snapshot'lar dokunulmadı);
v7.1-golden 3/3; tam süit değişmedi (541 passed). Faz 6/real/launchd/go_live'a adım YOK;
iki durma noktası kullanıcıda.

## KALICI KAYIT 23 — D5-BIST CHALLENGER turu AÇILDI (2026-07-10, açılış kaydı)
**Kullanıcı kararı (2026-07-10):** D1'e karşı TEK yapısal ek katman test edilir —
"D1 + fırsat-maliyeti (mutlak-momentum / faiz) kapısı" = **D5-BIST**. Offline
araştırma spike'ı; **üretim DEĞİL, HÜKÜM YOK.**

### DÜRÜST KAYNAK BEYANI (sonuç-bilgili tasarım — bu turun en önemli çekincesi)
Fikir, `PERIOD_COMPARISON.md`'nin **son-3-yıl gözleminden doğdu**: D1'in bu
pencerede TL nakit faizinin gerisinde kaldığı görüldükten SONRA "hisse ≤ faiz
ise nakitte kal" kapısı tasarlandı. Bu, tanımı gereği **sonuç-bilgili (result-
informed) bir tasarımdır** ve BIST tarihçesine bu proje boyunca defalarca
bakılmıştır. Dolayısıyla:
- **In-sample kirlenme riski KABUL EDİLEREK** challenger protokolü uygulanır:
  mühürlü kriterler "sepeti yenmek" değil, **D1'in KENDİSİNİ yenmek**tir
  (kendi kabul edilmiş ailemiz eşiktir — çıta yukarı çekilmiştir, aşağı değil).
- Sonuç **OOS-ağırlıklı okunur**: tam-dönem tablosu in-sample kirlenmiş sayılır;
  walk-forward OOS kriteri (3a) daha yüksek kanıt değeri taşır.
- **Kabul bile canlıya alma demek DEĞİLDİR.** ADAY çıksa dahi, önce ayrı bir
  gölge/paralel gözlem dönemi + ayrı kullanıcı kararı gerekir
  (tek-davranış-değişikliği disiplini, CLAUDE.md Bölüm 0.2 + disiplin #10).

### Tur disiplini (D4US-S1 izolasyonu AYNEN + ek)
- **DOKUNULMAZ:** `mode: paper`, D1 paper hattı ve TÜM canlı bot modülleri
  (`strategy/regime_core.py`, `execution/`, `safety/`, `data/live_*`, `notify/`,
  `main.py`, `config/config.yaml`, `config/regime_core.yaml`), S1/S1b/E4/D2US/D4US
  araçları (`backtest/regime_core*.py`, `backtest/xsec_momentum.py`,
  `backtest/dual_momentum_etf.py`, `tools/run_regime_core*.py`, `tools/e4_common.py`,
  `tools/run_xsec_momentum_us2.py`, `tools/run_dual_momentum_etf.py`,
  `config/regime_core*.yaml`, `config/momentum_us2.yaml`,
  `config/dual_momentum_etf.yaml`) + **TÜM snapshot'lar**.
- **D1'in mühürlü parametreleri (N/b/M = 200/0.01/3) AYNEN kalır** — hiçbir
  parametre ayarı yok; test edilen TEK EK yapısal katman kapının kendisidir.
- **Yeni, BAĞIMSIZ modüller:** `backtest/regime_core_gated.py`,
  `tools/run_d5_bist.py`, `config/d5_bist.yaml`, `tests/test_d5_bist.py`.
  Mevcut loader/maliyet/S1b araçları **YALNIZ import** edilir (drift imkânsız).
- **Veri:** S1b frozen snapshot (`data/snapshots/2026-07-06`) + S1b'nin tarihsel
  `TRY_ON_RATE` serisi (`data/snapshots/aux/2026-07-07/`) **AYNEN**. Yeni indirme
  YOK → D1 baseline'ıyla bit-bit kıyaslanabilirlik.
- **Grid/varyant seçimi YASAK** (disiplin #3): tasarım TEK paket, koşumdan ÖNCE
  mühürlenir. Komşuluk/MC/ablasyon YALNIZ bilgi.
- **İkinci ölçüm-bakışı YOK** (D2US/D4US emsali) — mühre yazılır.
- BIST v7.1-golden her commit 3/3 bayt-bayt. Her madde AYRI commit + push.
- Faz 6/go_live/launchd/real adımı YOK; iki durma noktası kullanıcıda.

Sıra: (0) bu kayıt → (1) `config/d5_bist.yaml` + D1-baseline yeniden üretimi +
`D5_CRITERIA.md` MÜHÜR (strateji kodu HENÜZ YOKKEN — commit sırası kanıttır) →
(2) spike koşumu + birim testleri + mekanik tablo + zorunlu analizler (a-g) →
(3) `D5_BIST_S1.md` + kapanış kaydı. **DUR.**

## KALICI KAYIT 24 — D5-BIST CHALLENGER spike TAMAMLANDI (2026-07-10, kapanış kaydı)
D5-BIST ("D1 + fırsat-maliyeti/faiz kapısı") tek-tur değerlendirme spike'ı tamamlandı
(bkz. `D5_BIST_S1.md`, `D5_CRITERIA.md`). Tasarım koşumdan ÖNCE TEK paket olarak
mühürlendi (commit `5376aad`; o commit'te `backtest/regime_core_gated.py` HENÜZ YOKTU
— commit sırası kanıttır). Grid/varyant seçimi YAPILMADI.

**Mühürleme:** referans **D1'in KENDİSİ** (sepet/endeks DEĞİL — challenger turu; çıta
yukarı çekildi). D1, aynı frozen veriyle deterministik yeniden üretildi ve S1b
kayıtlarına karşı **9/9 alanda BİREBİR (Δ=0.0)** doğrulandı. Mühürlü 4 kriter:
(1) Sharpe>1.2152648; (2) CAGR>0.2821140; (3a) OOS aylık-Sharpe>1.0677568;
(3b) |maxDD|≤%28.4278. Kural: TAMAMI→ADAY; biri kalırsa RED, dar-fark YOK, ikinci
ölçüm-bakışı YOK.

**MEKANİK SONUÇ:** D5 ana: CAGR %27.150, Sharpe 1.27376, maxDD -%35.224, 69 anahtarlama,
OOS aylık-Sharpe 1.16089, OOS maxDD -%35.633, MC dd_p5 -%39.88. **MÜHÜRLÜ TABLO:
(1) PASS (+0.0585); (2) FAIL (-1.061pp); (3a) PASS (+0.0931); (3b) FAIL (-6.796pp)
→ 2/4.** → önceden mühürlenen kurala göre **D5-BIST kabul adayı DEĞİL** (HÜKÜM değil;
karar kullanıcının/baş danışmanın).

**KRİTİK BULGU — kapı realize drawdown'ı DERİNLEŞTİRDİ.** Kapı maruziyeti yalnızca
AZALTABİLDİĞİ halde (`effective_on ⊆ regime_on`, testle çapalanmış) maxDD -%28.43 →
-%35.22'ye kötüleşti. Mekanizma **toparlanma bastırması**: D1'in iki AYRI epizodu
(2013-05→11 ve 2015-05→2016-02) D5'te TEK, daha derin bir epizoda KAYNAŞIYOR
(2013-05-22→2016-01-08, toparlanma 2017-07-11) çünkü D5 aradaki toparlanmaya katılıp
yeni zirve YAPAMIYOR. Ölçüm (2013-11-11→2015-05-19 bacağı): kompozit +%55.6, D1 equity
+%45.8, **D5 yalnız +%20.0**. En uzun kesintisiz sualtı: D5 1078 işlem günü vs D1 514.
Trailing-12ay mutlak momentum tanımı gereği dip sonrası geç açılır; TL'nin çift haneli
faiz eşiği gecikmeyi UZATIR.

**Zorunlu analizler:** (a) **ÖNCEDEN yazılan beklenti KISMEN ÇÜRÜDÜ** — kapı 2005-2020'de
"seyrek" olmadı (2007 %33.5, 2009 %35.2, 2012 %33.3, 2019 %22.3, 2020 %25.4 bağladı);
**2022-2023'te kapı %100 AÇIK, 0 gün bağladı** (fikri doğuran gözlemin iki yılına hiç
dokunmuyor); 2024-25 yoğun (%26.5/%54.2) kısmı doğrulandı. Düşük-faiz yıllarında da yoğun
bağlaması → bu katman pratikte "fırsat-maliyeti filtresi" değil, **toparlanma-gecikmesi
filtresi**. (b) pencere kıyasları **in-sample kirlenmeyi ÖLÇTÜ**: D5, 3y/5y/10y'de D1'i
geçiyor (fikrin doğduğu dönem) ama **Son-1-Yıl'da (%30.2 vs %46.5) ve tam dönemde
kaybediyor**. (c) yıllık: en büyük bedel **2009 −70.5pp**, en büyük katkı **2024 +43.1pp**;
ayrıca 2014 −23.9pp, 2020 +29.9pp, 2018 +10.8pp. (d) turnover 69 vs 67; maliyet sürüklemesi
farkı **0.013pp/yıl** = CAGR açığının %1.2'si → **zayıflık maliyet kaynaklı DEĞİL, maruziyet
kaybı kaynaklı**. (e) komşuluk uçurumsuz AMA **mühürlü nokta Sharpe ZİRVESİ** (overfitting
şüphesi, mühürde önceden böyle tanımlanmıştı); yine de **6 noktanın HİÇBİRİ kriter 2'yi
geçmiyor** (en yüksek CAGR %27.75) → karar tek parametreye bağlı değil. (f) MC: D5 dd_p5
-%39.88 D1'in -%44.68'inden İYİ — **ama bu MC'nin permütasyonla patika-bağımlılığını yok
etmesindendir; kapının zararı tam da patika-bağımlıdır** → bu ailede MC gerçek DD riskini
sistematik olarak iyi gösterir. (§10) **Isınma artefaktı DEĞİL**: ortak ısınma-sonrası
pencerede (2005-12-21 renorm, koşumdan ÖNCE mühürlü yan-ölçüm) maxDD kötüleşmesi
(-6.80pp) AYNEN duruyor.

**DERS (metodoloji, kayda geçer):** `D5_CRITERIA.md` §0.2 sonucun "OOS-ağırlıklı" okunacağını
mühürlemişti ve **3a geçti**. Ancak bu walk-forward'da **hiçbir parametre optimize edilmiyor**
→ "OOS", aynı sabit stratejinin aynı 21 yılın dilimlerinde ölçülmesidir ve **tasarım-kökeni
kirlenmesine karşı KORUMA SAĞLAMAZ**. Üstelik OOS'un diğer yarısı D5 aleyhinedir (OOS maxDD
-%35.63 vs -%24.55). Bu düzeltme sonucu DEĞİŞTİRMİYOR (kriter 2+3b zaten kaldı) — bu yüzden
"sonuca göre yorum" değil, gelecek turlar için bir derstir: **sonuç-bilgili tasarımlarda
tek meşru koruma ileri-zaman yeni örneklemdir.**

**DÖRT-AİLE META BULGUSU (güncelleme):** D1-US/D2-US/D4-US üçünde de 3b (DD-kesme) PASS,
1/3a FAIL idi. **D5-BIST bu örüntüyü KIRIYOR ama ters yönde:** Sharpe'ta referansını geçen
İLK aile oldu, buna karşılık **3b'de KALAN ilk aile** — savunma katmanı eklendiği halde
realize DD derinleşti. Yapısal ders (üçüncü teyit): trailing-12ay mutlak momentum çöküşü
keser, toparlanmayı kaçırır; BIST'te bu, D1'in en güçlü özelliğini (hızlı yeniden-giriş →
epizot sıfırlanması) bozdu.

**Operasyonel kayıt (#18):** Backtest'te `TRY_ON_RATE` tarihsel olarak tamdır; **canlıda
kapı BAYAT faizle karar verirdi** (FRED/OECD ~130 gün gecikmeli; son gerçek gözlem
2026-03-01, sonrası ffill). Sonuç RED olduğu için ön koşul devreye girmedi; **kayda geçer:
faiz-EŞİKLİ herhangi bir kapı ileride kabul edilirse, #18'in çözümü canlıya almanın ÖN
KOŞULudur.** Ayrıca: eşikte seri-tanım hatası birinci derecedendir (tahakkukta ikinci
derecedendir) — faiz-eşikli her tasarım için yapısal kırılganlık.

**İzolasyon:** `mode: paper` + D1 paper hattı + TÜM canlı bot modülleri + S1/S1b/E4/D2US/D4US
araçları + `config/regime_core.yaml` (salt-okunur) + TÜM snapshot'lar DOKUNULMADI. Yeni
BAĞIMSIZ: `backtest/regime_core_gated.py`, `tools/run_d5_bist.py`, `config/d5_bist.yaml`,
`tests/test_d5_bist.py`. D1 sabitleri kopyalanmadı, `inherit_from` ile DEVRALINDI (N/b/M
sapması yapısal olarak imkânsız). `run_regime_core`/`compute_cash_only_curve`/loader'lar
YALNIZ import edilerek reuse. **Sadakat çapası:** `gate_cfg=None` → `run_regime_core` ile
BİT-BİT özdeş (test). Spike iki koşumda BAYT-BAYT aynı (determinizm). v7.1-golden her commit
3/3; tam süit **574 passed** (556 + 18 yeni). Faz 6/go_live/launchd/real'e adım YOK; iki
durma noktası kullanıcıda. **Kabul kararı kullanıcının/baş danışmanın; otomatik geçiş YOK.**

## K1.5 Mekanik Teyit — 1/2 (2026-07-08)
2026-07-08 akşam koşusu denetlendi (not: launchd servisleri bu makinede henüz kurulu
DEĞİL — `launchctl list` boş, `runtime/paper/logs/` yok; "akşam koşusu" = günün son
manuel `--refresh --cycle` çağrısı, `runtime/paper/decision_journal.jsonl` +
`heartbeat_status.json`'da 2026-07-08T17:05:41Z / 20:05 Istanbul damgalı). Dört kalem:
- **(a) DATA_DRIFT yok** — PASS. Günün TEK DATA_DRIFT alarmı 12:03 cycle'ındaydı (ASELS
  3-bar sapması); 12:56'da `--resync` ile giderildi (kompozit parite max_abs_diff≈5.4e-5);
  sonraki tüm cycle'larda (12:56, 13:11, 17:05) DATA_DRIFT YOK.
- **(b) provisional yok** — PASS. 17:05:41 cycle'ının `signal_eval` kaydı
  `"provisional": false` (as_of barı zaman-final + veri tam; önceki 3 cycle 12:03-13:11
  hâlâ oluşmakta olan bar yüzünden `provisional: true`'ydu — beklenen davranış).
- **(c) TELEGRAM: ACTIVE** — PASS. `heartbeat_status.json` (aynı ts):
  `telegram.state="ACTIVE"`, `reason="token+chat_id mevcut"`.
- **(d) EOD'de "Rejim"/"Pozisyon" AYRI satır + tutarlı** — PASS (kod-yolu doğrulamasıyla;
  ham EOD metni hiçbir yere journal'lanmıyor, yalnız stdout/Telegram'a gönderiliyor —
  bu yüzden literal string değil `main.py`/`notify/eod_summary.py` kod-yolu + bu
  cycle'ın girdileri izlendi). `main.py` observe dalı (satır ~354-366): `res.regime_on`
  DOĞRUDAN `evaluate_signal` çıktısından (composite/MA/band, bugünün gerçek rejim
  durumu) atanıyor — bu cycle için `True`. `build_eod_summary` çağrısında
  `in_position=bool(self.broker.quantities())`; observe modda hesap hiç başlatılmadığı
  için bu her zaman `False` → "Pozisyon: NAKİT (observe — hesap başlatılmadı)". İki alan
  BAĞIMSIZ kaynaklardan geliyor (F5-B2a.1 düzeltmesi, KALICI KAYIT 13) → "Rejim: ON" +
  "Pozisyon: NAKİT (observe...)" birlikte basılması ÇELİŞKİ değil, tasarım gereği
  (observe'da rejim ON iken pozisyon her zaman nakittir çünkü hesap yok).
**Dördü de sağlandı → K1.5 temiz koşu 1/2 (2026-07-08).** İkinci temiz koşu (2/2) için
farklı bir güne ait bağımsız bir gözlem gerekir; kod değişikliği YAPILMADI.

## K1.5 Mekanik Teyit — 2/2 DENEMESİ: FAIL (2026-07-09) — launchd KURULMADI
2026-07-09 akşam koşusu denetlendi (tek cycle bugün: `--refresh --cycle`,
`decision_journal.jsonl` + `heartbeat_status.json`'da 2026-07-09T17:32:38-42Z /
20:32 Istanbul damgalı). Dört kalem:
- **(a) DATA_DRIFT yok** — **FAIL.** 17:32:41Z'de `CRITICAL DATA_DRIFT`: 10 tarihsel
  bar kaydı sapması (örn. THYAO 2026-07-08: stored 336.0 vs fresh 332.0, %1.19).
  Günün tek cycle'ı bu; ardından **`--resync` UYGULANMADI** (07-08'in aksine — o gün
  drift erken bir cycle'daydı ve günün son cycle'ından önce giderilmişti).
- **(b) provisional yok** — **FAIL.** Bu cycle'ın `signal_eval` kaydı
  `"provisional": true` — kod yolu gereği (`main.py`: `final = time_final and
  data_complete and not drift`) DATA_DRIFT tek başına `final=False` yapıyor; (a)
  ile aynı kök neden, bağımsız ikinci bulgu değil.
- **(c) TELEGRAM: ACTIVE** — PASS (`heartbeat_status.json` aynı ts:
  `telegram.state="ACTIVE"`).
- **(d) EOD tutarlılığı** — denetlenmedi (kural gereği: ilk FAIL'de dur).
**Sonuç: 4 kalemden 2'si FAIL → bu cycle K1.5 için "temiz koşu" SAYILMAZ.** Kural
gereği (görev talimatı) **launchd KURULMADI** — madde 2/3/4 (G1 kurulumu, doğrulama,
STATUS "G1 TAMAM" kaydı) bu turda YAPILMADI. K1.5 hâlâ **1/2**; ikinci temiz koşu
için ayrı, bağımsız bir güne ait denetim gerekiyor (bugünkü drift giderilip yarının
cycle'ı temiz gelirse ya da operatör bugün elle `--resync` çalıştırıp aynı gün içinde
DEĞİL — kural "farklı bir gün" diyor, bkz. 1/2 kaydı — yeni bir günün cycle'ı
denetlenmeli). Kod/config/launchd değişikliği YOK; yalnız STATUS kaydı.

**Ek not (K1.5 kalemi DEĞİL, engel DEĞİL — bilinen sorun #18/F5-B1'e bağlı):**
Aynı cycle'da `CASH_RATE` WARN: FRED serisi 130 gün bayat, son değer %35.5 ile
sürülüyor (kaynak tarihi 2026-03-01). observe modunda / rejim-ON'da etkisi sıfır
(nakit faizi yalnız active/pozisyon-nakit döneminde equity hesabına girer).

## DRIFT ÇÖZÜMÜ + ALARM-GÖRÜNÜRLÜK TEŞHİSİ + K1.5 kaydı (2026-07-09, aynı gün — takip turu)

**1) Drift çözümü (10 bar, 07-08 ASELS emsali):**
- **Sapan barların tam listesi** (`detect_drift`, resync ÖNCESİ, hepsi 2026-07-08 tarihli,
  `stored`→`fresh`): THYAO 336.00→332.00 (−%1.19), GARAN 131.60→130.40 (−%0.91), ASELS
  381.00→377.00 (−%1.05), AKBNK 71.45→70.65 (−%1.12), KCHOL 185.80→184.00 (−%0.97),
  SAHOL 90.75→90.00 (−%0.83), TUPRS 259.50→256.50 (−%1.16), TOASO 299.50→297.75 (−%0.58),
  SISE 41.90→41.62 (−%0.67), ARCLK 97.55→96.80 (−%0.77). AKBNK+SISE+ARCLK/eksiği hariç
  evrenin **10/12'si**, hepsi **AYNI tek gün**, hepsi **AYNI yönde** (stored>fresh) küçük
  (~%0.6-1.2) sapma.
- **Kök neden notu:** `yfinance` `actions` (Dividends/Stock Splits) 10 sembolün TÜMÜNDE
  2026-06-15…2026-07-09 penceresinde TARANDI — hiçbirinde kayıt yok → temettü/split
  ayarlaması DEĞİL. 07-08 ASELS vakasıyla (`PHASE5B2A_REVIEW.md` B2a.1 Eki) KIYAS: o vaka
  3 sembol/1 gün/karışık-işaretli küçük yüzdelerdi ve "gün-içi önbelleklenmiş kapanışın gün
  sonunda resmi kapanışla güncellenmesi" (geç bar revizyonu) olarak teşhis edilmişti. Bugünkü
  desen AYNI mekanizmanın DAHA GENİŞ hali: 10/12 sembol, tek gün (07-08 — dünkü koşunun o an
  en-güncel barı), tutarlı TEK yönde (~%1 aşağı) — BIST'in o günkü resmi/nihai kapanış
  baskısının yfinance'e geç yansımasıyla tutarlı; evren-çapında tek-yönlü hareket dağınık
  temettü/split izini DEĞİL, ortak bir geç-revizyon partisini işaret ediyor.
- **`--resync` uygulandı:** yedek `runtime/paper/backups/live_history_20260709T175137Z.sqlite`;
  66,180 bar yeniden yazıldı; **10 sembolde 1'er bar değişti** (yukarıdaki liste, tam-tarihçe
  taramasında ek sembol YAKALANMADI — 07-08 vakasının aksine burada alarm zaten 10/12'yi
  kapsıyordu). **Kompozit parite: `max_abs_diff=1.740e-05`** (5511 ortak gün) — kompozit
  ölçeği (~570-700 TL) göz önüne alındığında göreli ~2.5e-8, pratikte ≈0 (07-08 vakasının
  5.42e-05/~7.7e-8'iyle aynı büyüklük mertebesi — beklenen aralık).
- **Resync SONRASI yeniden hesaplama (2026-07-08 VE 2026-07-09):** her iki gün de
  `provisional=false` (DATA_DRIFT temizlendi, veri tam, zaman-final) VE **regime_on=true,
  her iki günde de DEĞİŞMEDİ** (07-08: composite 699.82→692.85 resync ile hafif değişti ama
  karar aynı kaldı, ON; 07-09: composite 671.775→671.775 pratik-özdeş, ON). **→ "K1.5 1/2
  (07-08) geçerliliğini korur"** (karar değişmedi, yalnız veri hassasiyeti düzeldi).
  Journal'a drift-çözüm kaydı zaten `resync()` içinde otomatik düşüyor (`RESYNC` kategorisi,
  07-08 emsal formatıyla birebir — INFO "başladı" + CRITICAL "bitti: N bar; kompozit parite
  max_abs_diff=…") — ek bir kayıt gerekmedi.

**2) Alarm-görünürlük teşhisi:**
- **Telegram'a AYRI CRITICAL alarmı gönderildi mi?** Kod yolu: `_alarm()` KOŞULSUZ
  `self.notifier.send(...)` çağırıyor (main.py:169-171) — DATA_DRIFT alarmı bu yoldan geçti
  (17:32:41-42). `heartbeat_status.json` aynı ts'de `telegram.state=ACTIVE`; journal'da
  `TELEGRAM` kategorisinde HİÇBİR WARN yok (gönderim hatası olsaydı `TelegramNotifier.send`
  içinde loglanırdı) → **alarmın gerçekten gönderildiğine dair dolaylı ama tutarlı kanıt.**
  Dürüst çekince: `send()` BAŞARI durumunu hiçbir yere kalıcı yazmıyor (yalnız hata WARN
  düşüyor) — pozitif dispatch-kanıtı journal'da YOK, bu ayrı, küçük bir gözlenebilirlik
  boşluğu (bu turun kapsamı dışı; görev yalnız "gönderilmiyorsa ekle" dedi — gönderiliyor,
  o yüzden bu maddede kod değişikliği YAPILMADI).
- **EOD'de drift/provisional görünmemesi: TASARIM DEĞİL, EKSİKti.** `run_cycle` içinde
  `final` (=time_final and data_complete and not drift) hesaplanıyordu ama
  `build_eod_summary` çağrısına HİÇ geçirilmiyordu — EOD metni yalnız Rejim/Pozisyon/Equity/
  faiz/breaker/Telegram gösteriyordu, veri-finallik durumuna dair SIFIR iz yoktu. Bu yüzden
  operatör bugün EOD'yi (Telegram'a giden asıl özet) "temiz" okudu, oysa journal aynı
  cycle'ı `provisional=true` olarak kaydetmişti — **gözetimsiz (launchd) dönem öncesi bu fark
  kapatılmalı**, çünkü launchd sonrası kimse günlük olarak journal'ı elle açıp
  `provisional` alanını kontrol etmeyecek; tek görülen şey EOD/Telegram metni olacak.
- **FIX (yalnız notify-katmanı):** `notify/eod_summary.py` `build_eod_summary()`'ye iki
  opsiyonel parametre eklendi: `data_final: Optional[bool]`, `data_final_reason:
  Optional[str]`. `data_final` verilmişse EOD'ye tek satır: `data_final=True` →
  `"Veri: FINAL ✓"`; `False` → `"Veri: PROVISIONAL ⚠ ({reason})"` (reason yoksa jenerik
  "sinyal kesinleşmedi"). `main.py` `run_cycle` çağrı noktasında `final` + nedene göre
  sıralı bir metin (`DATA_DRIFT — sinyal kesinleşmedi` > `veri eksik — sinyal
  kesinleşmedi` > `bar henüz kapanmadı — sinyal kesinleşmedi`) geçiriliyor — `strategy/
  regime_core.py`, karar/sinyal kodu, `final`/`drift`/`data_complete` HESABI DOKUNULMADI;
  yalnız zaten hesaplanan değerler EOD metnine TAŞINDI. 9 yeni/genişletilmiş test
  (`tests/test_notify.py` 4 yeni, `tests/test_scheduler.py` 4 mevcut teste satır eklendi)
  — FINAL/PROVISIONAL+DATA_DRIFT/PROVISIONAL+bar-kapanmadı/parametre-verilmezse-sessiz
  (geriye uyumluluk) senaryoları.
- **Bu değişiklik K1.5 sayacını SIFIRLAMAZ:** ölçülen boru hattı (data→sinyal→karar→journal)
  DEĞİŞMEDİ; yalnızca zaten var olan `final` durumu EOD METNİNE eklendi (bildirim katmanı,
  karar katmanı değil). K1.5'in ölçtüğü şey journal'daki `provisional` alanı ve gerçek
  DATA_DRIFT/Telegram/EOD-tutarlılık davranışıdır — bunların hiçbiri bu fix'le değişmedi,
  yalnız operatörün GÖRDÜĞÜ metin zenginleşti.

**3) K1.5 kaydı (nihai, bu tur):** 2026-07-09 akşam koşusu: **TEMİZ DEĞİL** (DATA_DRIFT,
provisional) — **savunma katmanı doğru çalıştı** (tespit + kesinleştirmeme + red; sinyal
finalize edilmedi, observe modda zaten işlem etkisi yoktu). **Sayaç 1/2'de.** Sıradaki
deneme: **2026-07-10 akşam** (farklı, bağımsız bir gün — bugünkü resync bu günü
"düzeltilmiş" say(dır)maz, kural `--refresh --cycle`'ın kendi normal akışında DATA_DRIFT'siz
+ provisional=false gelmesini gerektiriyor). CASH_RATE bayatlığı zaten kayıtlı (#18).

**İzolasyon/değişmezler:** `strategy/regime_core.py`, karar/risk/motor kodu DOKUNULMADI;
`config/regime_core.yaml`, `mode: paper` DEĞİŞMEDİ. Tek olası kod değişikliği (izin verilen)
notify-katmanı (`notify/eod_summary.py` + `main.py` çağrı noktası) — uygulandı. v7.1-golden
3/3 (aşağı bkz.). Faz 6/go_live/launchd/real adımı YOK; iki durma noktası kullanıcıda.
launchd (G1) bu turda da KURULMADI — bir sonraki temiz koşu (2026-07-10 veya sonrası)
bekleniyor; önceki turun 2-4. maddeleri (kurulum/doğrulama/STATUS "G1 TAMAM") aynen geçerli.

## Son tur (P1) — kısa özet
- Üretim modülü + family registry + sürücü + breaker + 14 test (kriter A/B/D +
  breaker kuru-test + tam-lot boyutlama + family registry), her commit golden-kanıtlı.
- Kapanış: BACKTEST_REVIEW_D1_PROD.md, STATUS güncelleme (KALICI KAYIT 8 + kuyruk
  eki), tam süit 378 passed, git push. Tag: `regime-core-d1-prod`.

## Sırada
**Aktif kuyruk sırası (KALICI KAYIT 22 ile netleşti, KAYIT 24 onu DEĞİŞTİRMEDİ):
K1.5 2/2 doğrulaması → G1 (kullanıcı eylemi: launchd kurulumu) → Faz 6 başlangıç
kriterleri.** US hattı ASKIDA (aşağıdaki iki madde) — yeniden açılma yalnız kullanıcı
kararıyla.

- **[D5-BIST — mekanik RED, kullanıcı/baş danışman kaydı bekleniyor]** D5-BIST
  challenger spike'ı mühürlü tabloda **2/4** ile kaldı (KALICI KAYIT 24,
  `D5_BIST_S1.md`). **İkinci ölçüm-bakışı YOK** (mühürde kapalı). BIST tarihçesine D5
  bakış sayacı: **1 kullanıldı**; kapı ailesinin TÜM varyantları (farklı pencere/teyit/
  haircut) bu tarihçede **KAPALI**. D1 paper hattı ve aktif kuyruk bu turdan etkilenmedi.

- **[K1.5] ikinci temiz koşu (2/2) bekleniyor — 2026-07-09 denemesi FAIL oldu**
  (DATA_DRIFT + provisional, bkz. "K1.5 Mekanik Teyit — 2/2 DENEMESİ: FAIL" bölümü);
  launchd bu yüzden KURULMADI. Farklı bir güne ait, DATA_DRIFT'siz + provisional=false
  bir cycle ile tekrar denenecek. **Aktif kuyruğun ilk adımı.**
- **[G1, kullanıcı eylemi] launchd servis kurulumu** — K1.5 2/2 tamamlanınca sırada;
  bot + watchdog servislerinin gerçek launchd altında koşması (bkz. `deploy/*.plist`,
  `OPERATOR_GUIDE.md`). Faz 6 resmi başlangıcı bu + go_live kararına bağlı.
- **[ASKIDA — EXPANSION/US hattı, KALICI KAYIT 22] D4-US KESİN RED (baş danışman
  onayı):** D4US-S1 mühürlü tabloda 1/4 → RED. **US aktif aile araması ASKIDA** — üç
  aile (D1/D2/D4-US) hepsi 1/4 (meta bulgu: DD-kesme PASS, risk-ayarlı getiri edge'i
  FAIL). Yeniden açılma yalnız iki yapısal kaldıraçtan biriyle: (i) kuyruk #21 (EODHD
  kapsam doğrulaması), (ii) short-gate tasarım turu.
- **[ASKIDA, koşullu-bekliyor — EXPANSION/US3 kuyruğu #21] US3 tek-hisse point-in-time
  yolu:** yeniden açılırsa satın-alma ÖNCESİ EODHD paket-kapsam doğrulaması zorunlu
  (bkz. sorun/blok #21, `DATA_FEASIBILITY_US3.md`). Hiçbir satın alma/kayıt YAPILMADI —
  US-hattı-yeniden-açılışının iki kaldıracından biri (KALICI KAYIT 22).

**F5-B1 (gölge paper) KOD İŞİ TAMAMLANDI** — kullanıcı/baş danışman değerlendirmesi
bekliyor (`PHASE5B1_REVIEW.md`, KALICI KAYIT 10). Otomatik GEÇİŞ YOK. Sıradaki adımlar
kullanıcı kararına bağlı:
- **go_live kararı:** döngü birkaç gün stabil koştuktan sonra `config/regime_core.yaml`
  `paper.go_live_date` set edilir → active mod + Faz 6 resmi başlangıcı (AYRI karar).
- **F5-B2 (AlgoLab İPTAL, yeniden tanımlı):** `ManualExecutionAdapter` tasarımı (bot
  sinyali→Telegram→elle yürütme→onaylı fill kaydı; B2 mutabakatı) + gerçek Telegram HTTP/
  long-poll komut alıcısı. AlgoLab canlı akışı YAPILMAYACAK.
- **Real-öncesi kuyruk:** EVDS endpoint doğrulama (#18), gerçek nakit bacağı enstrümanı
  (#19), B1 kalanı (T+2/tick-lot/tedbir — manuel yürütmede kullanıcı gözetiminde).
- **Kuyruk (yeni):** BIST broker REST API pazarını periyodik izle — uygun API çıkarsa
  BrokerAdapter ile entegre edilebilir.

**Önceki tur (P1 D1 üretim portu) TAMAMLANDI** — `BACKTEST_REVIEW_D1_PROD.md`, KALICI
KAYIT 8. Üç paralel konu (referans):
(a) **BIST hattı**: D1 KABUL EDİLDİ (KAYIT 6) + ÜRETİM PORTU TAMAM (P1, KAYIT 8);
S1b'yle bit-bit özdeş, golden korundu. **Sıradaki iş kullanıcı onayına bağlı**:
canlı/paper emir katmanı Faz 5 (HARDENING B onayı) — PaperBroker/AlgoLab
regime_core ailesini de sürebilmeli. **[real-öncesi kuyruk, B1] Canlı takvim
gerçeği**: yarım-gün seanslar ve idari-izin köprü tatilleri için canlıda takvim
kütüphanesine (exchange_calendars) GÜVENİLMEZ — resmî kaynak (BIST/Borsa İstanbul
duyuruları) + veri-yok toleransı gerekir; canlı döngü bir günü yanlış "işlem günü"
sayarsa regime-core o gün hatalı sinyal/yürütme üretebilir.
(b) **EXPANSION.md**: E1 + E2 + **E4 + E4b (US ADİL TEST + nakit-tamamlama)
TAMAMLANDI** (KALICI KAYIT 15+16, `EXPANSION_E4.md` + `EXPANSION_E4B.md`). Mekanik
sonuç: D1-US mühürlü 4-kriterden **1/4** geçti (E4 %0 ve E4b faizli AYNI tablo) →
**SON-BAKIŞ KURALI gereği D1-US US-referansta KESİN RED, üçüncü bakış YOK** (karar
kullanıcının). **Kullanıcı sıralaması (KAYIT 14): E4 → geçerse US gölge paper →
geçerse E3.** E4/E4b "geçmediğinden" **US gölge paper hattı AÇILMADI**; D1-US için
dönüş yolu kapalı. Sıradaki E-fazı seçimi (E3 broker adapter mı, farklı çekirdek/
evren tasarımı mı) kullanıcı/baş danışman kararı — otomatik ilerleme YOK. E3'e
taşınan açık
maddeler (değişmedi): SEC/TAF+swap resmî doğrulama, US hesap tipi kararı, short
gate seti tasarımı (Bölüm 17 #10, FX aktivasyonu öncesi), US instruments[] config'e
girişi, econ/earnings gerçek parquet dosyaları. Ertelenenler (Faz 5 modülleri inşa
edilince): PaperBroker daily_carry, journal market/currency kolonları,
engine-seviyesi SHORT execution (short-gate sonrası).
(c) **Ablasyon + S1/S1b + P1**: TAMAMLANDI. Kalan işler (EVDS çapraz doğrulama,
üretim nakit bacağı enstrümanı) real-öncesi/üretim kuyruğunda (KAYIT 6 + aşağıda 18-19).

## Bilinen sorun/blok (aktif)
> Çözülmüş / üstü çizili maddeler (2, 3, 4, 8, 9, 10, 14, 16) **STATUS_ARCHIVE.md**'ye
> taşındı. Orijinal numaralandırma korundu (boşluklar bilinçli).

1. **Kullanıcı onayı bekleniyor (Durma Noktası 1, BIST)** — kasıtlı, aşılamaz kapı.
5. Breaker (10-gate), mevcut sıkı parametrelerle gerçekleşmiş max drawdown'u
   SINIRLAMIYOR (yalnızca sonraki girişleri engelliyor) — tasarım gereği
   (FREEZE≠FLATTEN); v7'de max DD zaten breaker eşiğinin altında, breaker hiç
   tetiklenmiyor. (D1 ailesinin AYRI breaker'ı: KALICI KAYIT 6/8.)
6. **10-gate walk-forward kabul kriteri GEÇMEDİ, MC worst-5% (dd_p5=-%10.29)
   breaker eşiğine yakın** — motor/veri bug'ı değil, 10-gate stratejisinin kendi
   zayıflığı (huni DONDURULDU, KALICI KAYIT 3). D1 ailesi bu yolun yerine geçti.
7. KCHOL 2007-06-08 hâlâ açıklanamadı (DATA_AUDIT_v2.md "açıklanamayan gap" —
   dış BIST/KAP doğrulaması gerekiyor).
11. **`oanda.py` hiçbir practice hesapla test edilmedi** (referans implementasyon)
    — E3'te doğrulanacak. E1'in FX snapshot'ı `yf_fx.py`'den üretildi.
12. **Ekonomik takvim vetosu (FX) backtest'te modellenemez** — tarihsel arşiv yok
    (Bölüm 10.4 fallback devrede; is_blackout altyapısı E2'de kuruldu, veri yoksa
    (False,"…") döner → backtest vetosuz).
13. US evreni survivorship yanlılığı taşıyor (bilinen, kabul edilen — DATA_AUDIT_US.md).
    **E4'te belirginleşti:** yanlılık, mühürlü referans olan eşit-ağırlık US sepetini
    gerçek-üstü yükseltiyor (CAGR %16.31, SPY %10.86'ya karşı) → D1-US kabul çıtası
    gerçekte-mümkün-olandan yüksek. Düzeltme (hayatta kalmayanları içeren evren) E4
    kapsamı dışı; yeniden-tasarım/US sleeve turunda ele alınır.
15. **Hiçbir 10-gate varyant USD-CAGR>0 başarı çıtasını geçmiyor** (KALICI KAYIT 1)
    — TRY'nin USD karşısındaki yapısal değer kaybı baskın. max DD/endeks-DD oranı İYİ.
17. Golden regresyon çapası `backtest-v7.1-golden` — `runtime/backtest_reports_v7_1/
    trades.csv` (commitli, `.gitignore` istisnası). E2+ her commit bayt-bayt kıyaslar.
18. **[real-öncesi kuyruk] EVDS↔TRY_ON_RATE çapraz doğrulama — DENENDİ, BLOCKED** (F5-B1,
    `EVDS_COMPARISON.md`): EVDS_API_KEY VAR ama REST endpoint evds2→evds3 geçişiyle SPA
    döndürüyor (JSON yok). **F5-B1.1 K8: `tools/evds_compare.py --csv` elle-export modu
    eklendi** → endpoint düzelmeden kullanıcı EVDS CSV export'uyla kapatabilir (kolon eşleme +
    çoklu tarih formatı). Snapshot DEĞİŞMEZ; hâlâ FRED/OECD (KAYIT 6). Ayrıca F5-B1.1 K1:
    canlı faiz FRED'den beslenir ama FRED de ~4 ay gecikmeli → faiz kronik bayat.
    2023 boşluğu ff → cash-yield MUHAFAZAKÂR sapma. **F5-B2a m4 düzeltmesi:** "bayat =
    muhafazakâr" GENELLEME DEĞİL — yön faiz patikasına bağlı; yükseliş döngüsünde muhafazakâr
    (eksik tahakkuk), DÜŞÜŞ döngüsünde nakit getirisini ABARTIR (agresif). **F5-B2a m5:** GERÇEK
    EVDS CSV (TLREF) kıyası koşuldu (EVDS_COMPARISON.md) — EVDS sistematik ~2-6p YÜKSEK (seri-tanım
    farkı), 2023 boşluğu EVDS'de 12/12 DOLU, 2022-10 %9.0 baseline artefaktı teyit. Snapshot
    DEĞİŞMEDİ. Bu madde artık "veri yok" DEĞİL, "tanım-uyumlu seri + S1b yeniden ölçüm turu"
    bekliyor. Real öncesi tamamlanmalı.
    **D5 eki (KALICI KAYIT 24):** faizi **EŞİK** olarak kullanan herhangi bir tasarımda bu
    madde birinci-derece kritiktir (nakit tahakkukunda ikinci-derece): seri-tanım farkı
    (~2-6 puan) karar sınırını kaydırır, canlı besleme ~130 gün bayattır (son gerçek gözlem
    2026-03-01, sonrası ffill). **Faiz-eşikli bir kapı ileride kabul edilirse #18'in çözümü
    canlıya almanın ÖN KOŞULudur.** (D5 bu turda RED aldığı için ön koşul devreye girmedi.)
19. **[üretim-turu kuyruğu] D1 nakit bacağının GERÇEK enstrümanı** netleştirilecek
    (AlgoLab para piyasası fonu/repo süpürme; oran/likidite/vade). Şu anki
    %0/faizli model yalnızca bir yaklaşıklık.
20. **[KAPANDI — E4b] US nakit bacağı ölçüldü.** E4'teki %0 boşluğu E4b'de gerçek
    US kısa faiziyle (FRED DGS3MO 3-aylık T-bill, dondurulmuş aux_us snapshot, 50bp
    haircut) S1b formülüyle tamamlandı (bkz. KAYIT 16, `EXPANSION_E4B.md`). Sonuç:
    faiz Sharpe'ı 0.726→0.758, CAGR +0.41pp itti ama mühürlü tablo 1/4'te kaldı →
    D1-US KESİN RED. **%0 kararı doğrulandı: US faizi küçük (nakit-only CAGR ~%1.51),
    sonucu iyimser saptırmamıştı.** SPY-vs-sepet referans sorusu SON-BAKIŞ KURALIYLA
    kapatıldı (D1-US için SPY'a geçiş YASAK; sepet kalıcı referans).
21. **[EXPANSION/US3 kuyruğu — KOŞULLU-BEKLİYOR, ASKIDA] EODHD paket-kapsam
    ÖN-doğrulaması (satın-alma öncesi zorunlu).** US3 tek-hisse point-in-time evren yolu
    (delisted-dahil, 2005+) ücretsiz kaynaklarla kurulamıyor (`DATA_FEASIBILITY_US3.md`);
    en ucuz güvenilir ücretli yol EODHD (~$200-300/yıl). Baş danışman ERTELEDİ (KALICI
    KAYIT 20); D4-US RED sonrası US aktif aile araması TAMAMEN ASKIYA alındı (KALICI
    KAYIT 22) — bu madde artık US hattının yeniden açılması için İKİ yapısal kaldıraçtan
    biri (diğeri: short-gate tasarım turu, Bölüm 17 #10). **Bu hat yeniden açılırsa:**
    herhangi bir satın alma/abonelik ÖNCESİ, EODHD'nin gerçekten (a) delisted/defunct
    ticker fiyat tarihçesi, (b) point-in-time endeks üyeliği, (c) 2005'e uzanan derinliği
    tek pakette sağladığı DOĞRULANMALI (deneme/dokümantasyon ile) — aksi halde para
    harcanmaz. Hiçbir satın alma/kayıt YAPILMADI.
22. **[EXPANSION/US hattı — ASKIDA, KALICI KAYIT 22] short-gate tasarım turu.** US
    hattının yeniden açılması için ikinci yapısal kaldıraç (madde #21'in alternatifi):
    engine-seviyesi SHORT execution + short-gate seti tasarımı (Bölüm 17 #10, FX
    aktivasyonu öncesi — kısa mekaniği risk/direction.py'de zaten test edilerek kurulu,
    ayna simetrisi/quote-ccy/marjin). Bu turda BAŞLATILMADI; yalnız kuyruğa kayıt.

## Önceki fazlardan taşınan varsayımlar
pandas-ta yerine pandas-ta-classic + numpy 2.2 (e31e401); BIST seans saatleri
yaklaşık; backtest degrade modda; compute_target max(resistance, fallback)
(67d2dd6); gate_trigger_4h degrade modda son-3-bar-pattern VEYA breakout (67d2dd6);
walk-forward date_range/precomputed_features (60a6d3f); adx_min=25 (d6ea8fc); 12
sembol evreni + 2005-01-01 + OHLC tolerans fix'i (dc56ed2); HARDENING.md Bölüm A
(eb3b21d); breaker backtest entegrasyonu + MC dd_p5 düzeltmesi (c906d10, 53ba4b3);
v7 motor+veri düzeltme turu (5227438); EXPANSION.md eklendi (d0ab81d); E1 veri
temeli (US/FX adapter'ları, snapshot'lar, DATA_AUDIT_US/FX.md, data/events.py);
portföy ablasyon (disabled_gates + pending_exits determinizm düzeltmesi);
EXPANSION E2 (MarketSpec/CostModel/gate_registry/calendars/Direction, golden çapa,
exchange_calendars); P1 (strategy/regime_core.py + family_registry, D1 üretim portu);
F5-B1 (data/live_feed.py yfinance EOD + main.py PaperScheduler observe/active +
INITIAL_ENTER + oluşmakta-olan-bar koruması; AlgoLab İPTAL, F5-B2=ManualExecutionAdapter).

Limit nedeniyle durdu mu: hayır — Durma Noktası 1 nedeniyle duruldu.

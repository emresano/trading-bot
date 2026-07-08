# EVDS ↔ TRY_ON_RATE Çapraz Doğrulama Raporu (F5-B1, kuyruk #18)

**Tarih:** 2026-07-07 · **Karar:** yalnızca RAPOR — snapshot DEĞİŞTİRİLMEDİ.
**Bağlam:** KALICI KAYIT 6 çekince (b) + STATUS bilinen-sorun #18 (real-öncesi kuyruk).

## Neden bu kontrol
`TRY_ON_RATE` (S1b nakit-getiri modeline giren tek faiz serisi; **hiçbir sinyal/gate
hesabına girmez**) TCMB'nin kendisi değil, **FRED/OECD** rebroadcast'idir
(`IRSTCI01TRM156N`, OECD MEI — Türkiye bankalar arası gecelik/call money, aylık).
Real paraya geçmeden önce TCMB'nin resmî kaynağıyla (EVDS API) doğrulanmalı.

## Sonuç: BLOCKED (anahtar VAR, endpoint ulaşılamadı)
- `EVDS_API_KEY` `secrets.env`'de **mevcut** (bu tur ilk kez erişilebilir).
- EVDS REST endpoint'i (`/service/evds/series=...`) **JSON döndürmedi**: `evds2.tcmb.gov.tr`
  isteği **302 ile `evds3.tcmb.gov.tr`** web-app SPA'sına yönlendiriyor; `evds3` de
  aynı `/service/evds/` yolunda HTML (SPA) veriyor. Yani EVDS **evds2→evds3 geçişiyle
  API yüzeyi değişmiş** görünüyor; belgelenen yol artık programatik JSON vermiyor.
  Denenen: header-`key` + query-`key`, `type=json`/`type=csv`, User-Agent varyantları,
  bilinen kontrol serisi (`TP.DK.USD.A.YTL`) — hepsi SPA HTML. (Tanı: `runtime/f5b1/
  evds_comparison.json::evds_diagnostics`.)
- **Kimlik bilgisi hiçbir çıktıya yazılmadı** (maskeleme + `.gitignore`'lı runtime).

## Mevcut TRY_ON_RATE tabanı (EVDS gelince kıyas için hazır)
- Kapsam: 2005-01-01 → 2026-03-01, aylık, 255 nokta, **9 NaN ay**.
- **2023 boşluğu** (forward-fill'lenen): Şubat–Haziran + Eylül–Aralık 2023.
- **Yön analizi (dürüst):** 2023 TCMB'nin **agresif faiz artırım** dönemidir (Haziran'da
  ~%8.5'ten yıl sonunda ~%42.5'e). FRED serisi bu aylarda boş; forward-fill son bilinen
  düşük değeri (ör. Ağu 2023 %23.5) taşır → **gerçeğin ALTINDA** kalır → nakit dönemde
  faiz tahakkuku **DÜŞÜK** hesaplanır. Bu, strateji sonucunu **abartmaz** (muhafazakâr
  sapma); yani hata varsa yönü güvenli taraftadır. Yine de real öncesi düzeltilmeli.
- Not: bazı 2022 değerleri (2022-10=%9.0) TCMB politika faiziyle birebir örtüşmüyor —
  serinin "call money/interbank" tanımı politika faizinden farklı olabilir; EVDS
  karşılaştırması bu tanım farkını da netleştirecek.

## Öneri (karar AYRI onaylı tur — bu tur uygulanmaz)
1. **Endpoint doğrula:** evds3 üzerinden EVDS REST API'nin güncel taban URL'i/auth'u
   TCMB dokümanından (giriş yapılmış hesapla) teyit edilmeli. Doğrulanınca
   `tools/evds_compare.py::EVDS_HOSTS/EVDS_SERIES_CANDIDATES` güncellenip yeniden koşulur
   (script hazır: JSON gelirse aylık hizalar, farkı `runtime/f5b1/evds_compare_*.csv`'ye yazar).
2. **Alternatif (F5-B1.1 K8 ile HAZIR):** politika/gecelik faiz serisi evds3 arayüzünden
   **CSV export** edilip script'e verilir — endpoint gerekmez:
   ```bash
   .venv/bin/python -m tools.evds_compare --csv <export.csv>
   # kolon eşleme otomatik (Tarih/Date + değer); gerekirse --date-col / --value-col
   ```
   Script CSV'yi aylık hizalar, TRY_ON_RATE ile farkı `runtime/f5b1/evds_compare_csv.csv`'ye
   ve özeti `evds_comparison.json`'a yazar; **2023 boşluk dönemini** ayrıca raporlar
   (EVDS'nin o ayları doldurup dolduramadığı). Çoklu tarih formatı (2024-1, 2024-01,
   ISO) ve Türkçe ondalık virgül desteklenir. **Snapshot yine DEĞİŞMEZ** — yalnız rapor.
3. **Düzeltme kararı:** fark anlamlıysa (özellikle 2023 boşluğunda) TRY_ON_RATE'in
   TCMB-kaynaklı sürümüyle değiştirilmesi **ayrı, onaylı bir turda** yapılır; S1b
   ölçümü o zaman yeniden üretilir (mühürlü kriterler yeniden kontrol edilir).

**Reçete:** `tools/evds_compare.py` (yeniden koşulabilir), `runtime/f5b1/evds_comparison.json`.

---

## F5-B2a — GERÇEK EVDS CSV KIYASI KOŞULDU (2026-07-08)

Kullanıcı `runtime/manual/evds_export.csv` sağladı (seri **TP_BISTTLREF_ORAN** = TLREF,
BIST TL Gecelik Referans Faizi; 1860 günlük satır, 2018-12 … ). `evds_compare --csv` ile
aylık hizalandı. **Snapshot DEĞİŞMEDİ — yalnız rapor.** (`runtime/f5b1/evds_comparison.json`
+ `evds_compare_csv.csv`.)

**Araç düzeltmesi (bu tur):** otomatik `value_col` seçimi export'un sondaki virgülünden
doğan boş `Unnamed: 2` kolonunu alıp **sessizce 0 satır** okuyordu → en az bir sayısal
değeri olan son kolon seçilecek şekilde sertleştirildi (operatör artık `--value-col`
vermek zorunda değil). +1 test.

### Bulgular
| Ölçüt | Değer |
|---|---|
| Örtüşen ay | 79 |
| Ortalama mutlak fark | **2.13 puan** |
| En büyük fark | **6.00 puan @ 2020-10** (bir başka faiz-geçiş ayı) |
| 2023 boşluk ayları (baseline NaN) | 9 |
| 2023 ayları EVDS'de dolu mu | **12/12 — TAMAMEN DOLU** |

1. **Genel fark:** EVDS TLREF, baseline'dan (FRED interbank call money) **sistematik olarak
   ~2-6 puan YÜKSEK** — rastgele değil, yön hep aynı → **seri-TANIM farkı** (secured TLREF vs
   OECD interbank call money) + geçiş aylarında zamanlama farkı. İki seri AYNI enstrüman
   DEĞİLDİR; birebir ikame edilemezler.

2. **2023 boşluğu EVDS'de tam dolu:** baseline'ın forward-fill'lediği 9 ay EVDS'de gerçek
   değerlerle mevcut ve fark DRAMATİK: 2023-11 baseline ff **23.5** vs EVDS **41.45**;
   2023-12 baseline ff 23.5 vs EVDS **43.63**. Bu, faiz YÜKSELİŞ döngüsünde bayat/ff'in
   gerçeğin çok altında kaldığını doğrular (m4 tespitiyle tutarlı: yükselişte muhafazakâr).

3. **2022-10 %9.0 anomalisi teyit edildi:** baseline 2022-09→10→11 = 10.5→**9.0**→7.5 (düşüş);
   EVDS aynı aylarda 11.38→11.46→10.04. Baseline'daki **9.0 dip'i EVDS'de YOK** — bu, baseline
   serisinin tanımsal/veri artefaktı olduğuna işaret eder (o dönem para-piyasası faizi ~11%'e
   yakın seyrediyordu).

### Sonuç / karar (değişmez)
Fark hem seviye (~2 puan taban) hem de kritik 2023 boşluğunda anlamlıdır — ancak bu **seri-tanım
farkı** olduğu için EVDS TLREF'i doğrudan TRY_ON_RATE yerine koymak **basit bir yama değildir**;
tam seri yeniden-inşası + S1b mühürlü kriterlerinin yeniden üretilmesi gerektiren **ayrı, onaylı
bir tur** ister (yukarıda madde 3). Bu turda snapshot'a, mühürlü parametrelere, S1b ölçümüne
DOKUNULMADI. Real-öncesi kuyruk #18 açık kalır (artık "veri yok" değil, "tanım-uyumlu seri +
yeniden ölçüm turu" bekliyor).

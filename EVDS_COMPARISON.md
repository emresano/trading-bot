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
2. **Alternatif:** politika/gecelik faiz serisi evds3 arayüzünden **CSV export** edilip
   `data/snapshots/aux/<tarih>/`'ye eklenir; script onunla da karşılaştırabilir.
3. **Düzeltme kararı:** fark anlamlıysa (özellikle 2023 boşluğunda) TRY_ON_RATE'in
   TCMB-kaynaklı sürümüyle değiştirilmesi **ayrı, onaylı bir turda** yapılır; S1b
   ölçümü o zaman yeniden üretilir (mühürlü kriterler yeniden kontrol edilir).

**Reçete:** `tools/evds_compare.py` (yeniden koşulabilir), `runtime/f5b1/evds_comparison.json`.

# BACKTEST_REVIEW_D1_PROD — Rejim-Filtreli Çekirdek (D1) Üretim Portu

Tarih: 2026-07-07 (Europe/Istanbul) · Tur: P1 (D1 üretim portu) · "P1 onaylandı".
Referans ölçüm: `REGIME_CORE_S1B.md` (nakit-getiri düzeltmeli, KALICI KAYIT 6 kabul).
Üretim çıktısı: `runtime/regime_core_prod/summary.json`.

> **DURUM: P1 kod işi tamamlandı — kullanıcı/baş danışman değerlendirmesi bekliyor.**
> Faz 5'e geçilmedi, `mode`'a dokunulmadı, hiçbir eşik/parametre değiştirilmedi.
> v7.1-golden her commit'te bayt-bayt korundu.

---

## 1. Ne yapıldı

KALICI KAYIT 6 ile kabul edilen D1 ailesi, spike'tan (`backtest/regime_core.py`,
REFERANS olarak kalır) üretim yığınına "backtest=canlı aynı fonksiyon" ilkesiyle
(CLAUDE.md 3.1) taşındı:

- `strategy/regime_core.py` — ÜRETİM regime-core. Spike'a **BAĞIMSIZ** (import yok).
  Saf sinyal (`build_composite`, `compute_regime_signal`) + saf boyutlama
  (`plan_enter` TAM-LOT, `plan_exit`) + cash-yield tahakkuk + breaker. Backtest
  sürücüsü ve gelecekteki canlı döngü (Faz 5) AYNI saf fonksiyonları çağırır.
- `strategy/family_registry.py` — StrategyFamily soyutlaması + registry: `ten_gate`
  (10-gate huni, `run_backtest`'i delege eder → golden korunur) ve `regime_core`,
  config'ten seçilebilir iki aile. Seçim TEK sınırda; çekirdekte aile-özel `if` yok.
- `backtest/run_family.py` — aile-dispatch sürücü + S1b mutabakatı.
- `config/regime_core.yaml` — `strategy_family: regime_core` (config.yaml DOKUNULMADI).

**Spike semantiği BİREBİR korundu** (hiçbir parametre/eşik değişmedi): 12 sembol
eşit ağırlık kompozit, MA(200)×(1+0.01) üstünde 3 gün teyitli GİRİŞ /
MA(200)×(0.99) altında tek gün ÇIKIŞ, sinyal t kapanışı → yürütme t+1 KAPANIŞ,
komisyon 10bp + slippage 5bp, TAM-LOT + artık nakit, nakit dönemde TRY_ON_RATE −
200bp (ACT/365, takvim-günü üssü, ENTER günü dahil / EXIT günü hariç).

---

## 2. S1b yan yana kıyas + mutabakat

| Metrik | S1b (referans) | D1 ÜRETİM | Δ | Tolerans (mühürlü) |
|---|---|---|---|---|
| Toplam getiri | 207.8666 (×) | 207.8666 (×) | **0.0** | — |
| CAGR | 28.211% | 28.211% | **0.0 puan** | ±0.5 puan |
| Max drawdown | −28.428% | −28.428% | **0.0 puan** | ±1.0 puan |
| Sharpe (günlük, √252) | 1.21526 | 1.21526 | **0.0** | ±0.05 |
| Anahtarlama sayısı | 67 | 67 | **0** | — |

**Anahtarlama tarihleri: 67/67 BİREBİR aynı** (liste diff'i BOŞ).

### Mutabakat — sapma neden 0?
Kriter B "sapmalar tam-lot/artık-nakit kaynaklı olarak satır satır gerekçelendirilir"
der. Fiili sonuç: **sapma yok (bit-bit özdeş)**. Gerekçe: spike (`backtest/
regime_core.py`) ZATEN tam-sayı lot (`int(np.floor(...))`) + artık nakit +
cash-yield tahakkuku modelliyordu; üretim portu AYNI algoritmayı BAĞIMSIZ kodla
yeniden ürettiği için, üretim gerçekliği (tam-lot) kaynaklı ek bir sapma OLUŞMADI.
Yani "spike→üretim" geçişi bu ailede metrik-nötr; tek meşru sapma kaynağı (tam-lot)
zaten spike'ta içeriliydi. Bağımsızlık + özdeşlik, `tests/test_regime_core_prod.py`
(kriter A/B) ile her koşuda doğrulanır.

---

## 3. Breaker (KALICI KAYIT 6) — tarihsel davranış

Eşikler: **ALARM −%25** (log + bildirim kancası, DAVRANIŞ DEĞİŞTİRMEZ),
**FREEZE −%40** (yeni ENTER yok; rejim ÇIKIŞI devam eder; reset yalnız kullanıcı —
`runtime/.../FREEZE_TRIPPED` dosyasını elle siler).

| Ölçüm | Değer |
|---|---|
| Tarihsel **FREEZE** tetiklenme | **0** (kriter D ✓) |
| FREEZE nedeniyle bloklanan ENTER | 0 |
| **ALARM** epizodu (bildirim-only) | 4 |

**ALARM epizotları** (hepsi sığ, ~−%25…−%26; davranış değiştirmez):
2006-12-13 (−25.15%), 2013-11-05 (−25.50%), 2015-12-31 (−25.52%), 2016-11-04 (−25.45%).

Dürüst not: strateji max DD'si −%28.43 olduğundan ALARM eşiği (−%25) tarihsel
olarak aşıldı — bu **beklenen** ve **bildirim-only** (metrikler değişmez, kriter
A/B mutabakatı bozulmaz). FREEZE eşiği (−%40) hiç yaklaşılmadı → **tarihsel
tetiklenme 0**, yani breaker eklenmesi tarihsel davranışı DEĞİŞTİRMEDİ. KALICI
KAYIT 6'daki "birleşik tarihsel zarf −%33.5 + ~6.5 puan marj" gerekçesiyle tutarlı.

Kuru-test (sentetik seri, `tests/test_regime_core_prod.py`): tek-bar −%57 uçurumda
FREEZE tetiklenir, freeze dosyası yazılır, sonraki ENTER bloklanır, çıkış serbest
kalır — mekanik doğrulandı.

---

## 4. MÜHÜRLÜ P1 KABUL KRİTERLERİ — sonuç tablosu

| # | Kriter (koşum öncesi sabit) | Sonuç | Durum |
|---|---|---|---|
| **A** | Üretim yolu S1b'nin 67 anahtarlama tarihini BİREBİR üretir (diff boş) | 67/67 identical=true | **GEÇTİ** |
| **B** | CAGR ±0.5 / maxDD ±1.0 / Sharpe ±0.05; sapmalar gerekçeli | Δ = 0.0 / 0.0 / 0.0 (bit-bit) | **GEÇTİ** |
| **C** | v7.1-golden bayt-bayt korunur (her commit) | `tests/test_golden_bist.py` 3/3 YEŞİL | **GEÇTİ** |
| **D** | Breaker: tarihsel FREEZE tetiklenme 0 + kuru-test yeşil | FREEZE=0; kuru-test yeşil | **GEÇTİ** |

**Tam test süiti:** `pytest -q` → **378 passed, 0 failed** (P1 öncesi 364; +14
D1 üretim testi). Golden 3/3 bayt-bayt.

**Not:** Bu tablo MEKANİK olarak doldurulmuştur — kabul/red/üretime-alma kararı
kullanıcının/baş danışmanın. Bu rapor "port teknik olarak S1b'yle özdeş ve
golden korundu" der; strateji hükmü KALICI KAYIT 6'da zaten verildi.

---

## 5. Kapsam dışı (bu tur DEĞİL)

- PaperBroker/AlgoLab emir katmanı (Faz 5 — HARDENING B onayı gerekir).
- Short, US/FX aktivasyonu.
- `backtest/regime_core.py` spike dosyalarının silinmesi — spike REFERANS olarak
  kalır; üretim kodu ondan bağımsızdır.

## 6. Açık maddeler / kuyruk (real-öncesi)

- **Takvim gerçeği (canlı, B1)**: yarım-gün seanslar ve idari-izin köprü tatilleri
  için canlıda takvim kütüphanesine güvenilmez — resmî kaynak + veri-yok toleransı
  gerekir (STATUS kuyruğuna eklendi).
- EVDS çapraz doğrulama (TRY_ON_RATE) + üretim nakit bacağı gerçek enstrümanı —
  KALICI KAYIT 6 kuyruğu (real-öncesi), değişmedi.

---

*P1 kod işi burada biter. Faz 5'e geçilmedi, mode'a dokunulmadı. İki durma
noktası kullanıcıda. Değerlendirme bekleniyor.*

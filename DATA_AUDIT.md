# Veri Bütünlüğü Denetimi (DATA_AUDIT.md)

Salt-okunur denetim (HARDENING.md A2) — hiçbir veri değiştirilmedi.
Snapshot: `data/snapshots/2026-07-06`

## Özet Tablo

| Sembol | Durum | Satır | Kalite Kontrolü | Sıfır/Negatif Fiyat | Yinelenen Tarih | Eksik Gün | Sıçrama (>%25) |
|---|---|---|---|---|---|---|---|
| AKBNK | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| ARCLK | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| ASELS | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| EREGL | PASS | 5512 | PASS | 0 | 0 | 0 | 0 |
| GARAN | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| KCHOL | WARN | 5511 | PASS | 0 | 0 | 0 | 1 |
| SAHOL | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| SISE | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| TCELL | WARN | 5511 | PASS | 0 | 0 | 0 | 1 |
| THYAO | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| TOASO | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |
| TUPRS | PASS | 5511 | PASS | 0 | 0 | 0 | 0 |

## Sembol Detayları

### AKBNK — PASS
- Bulgu yok.

### ARCLK — PASS
- Bulgu yok.

### ASELS — PASS
- Bulgu yok.

### EREGL — PASS
- Bulgu yok.

### GARAN — PASS
- Bulgu yok.

### KCHOL — WARN
- 1 şüpheli sıçrama (>%25):
  - 2007-06-07: getiri=-26.8%, hacim=3859185, 20g_hacim_oranı=1.03x — sınıflandırılamadı — elle incelenmeli

### SAHOL — PASS
- Bulgu yok.

### SISE — PASS
- Bulgu yok.

### TCELL — WARN
- 1 şüpheli sıçrama (>%25):
  - 2005-05-16: getiri=26.0%, hacim=1528496, 20g_hacim_oranı=0.67x — sınıflandırılamadı — elle incelenmeli

### THYAO — PASS
- Bulgu yok.

### TOASO — PASS
- Bulgu yok.

### TUPRS — PASS
- Bulgu yok.

## auto_adjust Durumu

Tüm veri `yfinance` üzerinden `auto_adjust=True` ile indirildi (`data/historical.py`). Bu, temettü ve bölünme düzeltmelerinin OHLC sütunlarına doğrudan işlendiği, ayrı bir `Adj Close` sütununun TUTULMADIĞI anlamına gelir — pipeline'ımız yalnızca düzeltilmiş fiyatı saklıyor, ham (düzeltilmemiş) fiyatla karşılaştırma yapılamıyor. Bu, projenin bilinen bir sınırlaması: bir günün 'sıçraması' gerçek bir fiyat hareketi mi yoksa auto_adjust'ın bir kurumsal işlemi hatalı düzeltmesi mi, ham veri olmadan kesin olarak ayırt edilemez.

## Ek: OHLC Tolerans Sınır Kanıtı (dc56ed2 denetimi)

`data/quality.py`'nin OHLC toleransı (rtol=%0.5, atol=1e-6) sentetik sınır durumlarıyla test edildi:
- epsilon (-1e-13, kayan nokta gürültüsü) → PASS
- %0.3 sapma (tolerans içinde, rtol=%0.5) → PASS
- %0.5 sapma (tolerans sınırında) → PASS
- %5 sapma (gerçek ihlal, rtol'un 10 katı) → FAIL

Sonuç: tolerans, kayan nokta gürültüsünü (epsilon) ve küçük adjustment-yuvarlama sapmalarını (%0.3'e kadar) doğru şekilde geçiriyor, ama %5'lik gerçek bir ihlali hâlâ doğru şekilde reddediyor. Sınır (rtol=%0.5) ile gerçek ihlal arasında 10 kat güvenlik marjı var — makul.

## Genel Değerlendirme

Hiçbir sembol FAIL almadı. Bazı semboller WARN aldı (şüpheli sıçrama ve/veya eksik gün) — bunlar aşağıda listelendi ve sınıflandırma DENEMESİ yapıldı, ama kesin hüküm verilmedi (kullanıcıyla birlikte değerlendirilmeli). v5 sonuçları karantinada DEĞİL, ama bu WARN'lar dikkate alınmalı.
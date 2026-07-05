# Proje Durumu
Son güncelleme: 2026-07-05T15:45:00+03:00 (Europe/Istanbul)
Şu an: Faz 3 tamamlandı — Faz 4'e (backtest harness) başlanacak
Tamamlanan fazlar: Faz 1 (İskelet + Veri Katmanı), Faz 2 (İndikatörler + Sinyal
Motoru), Faz 3 (Risk Motoru)

Bu oturumda yapılan (Faz 3):
- `risk/risk_engine.py`: Bölüm 9.2 referans implementasyonu birebir —
  `size_and_approve(sig, acct, cfg, corr_fn)` kapı sırası: kill_switch →
  breaker → daily/weekly loss limit → max_positions → min_rr → correlation →
  boyutlama (risk_amount/per_share_risk, notional tavanı, nakit kırpması,
  qty<1 → POSITION_TOO_SMALL).
- `kill_switch_active(cfg)` / `breaker_tripped()`: dosya varlığı kontrolü.
  `check_and_trip_breaker(acct, cfg)`: equity, peak_equity'den
  `max_drawdown_breaker_pct` kadar düştüğünde `runtime/BREAKER_TRIPPED`'i
  yazar; dosya varsa dokunmaz (yalnızca kullanıcı elle siler).
- `historical_correlation(symbol, positions, price_loader, lookback_days)`:
  adayın son N günlük getirisiyle her açık pozisyonun getirisi arasındaki
  Pearson korelasyonun (mutlak değer) maksimumunu döner. `price_loader`
  dependency-injection ile alınıyor — risk_engine kendi IO yapmıyor (saf
  çekirdek ilkesi korunuyor).
- `tests/test_risk_engine.py`: baseline tam-onay + Bölüm 9.3'ün birebir
  sayısal örneği (equity=100.000, entry=100, stop=94 → qty=125), risk
  motorunun ürettiği 8 RejectReason'ın her biri için izole test
  (KILL_SWITCH, DRAWDOWN_BREAKER, DAILY_LOSS_LIMIT, WEEKLY_LOSS_LIMIT,
  MAX_POSITIONS, MIN_RR_FAILED, CORRELATION_LIMIT, POSITION_TOO_SMALL),
  notional-tavanı ve nakit kırpma senaryoları, `historical_correlation`
  için 3 test.
- Faz 3 Bitti Tanımı doğrulandı: `pytest -q` → 99 passed (81 önceki + 18
  risk motoru); risk_engine'in kapsamındaki 8 RejectReason'ın hepsi en az
  bir testte üretiliyor (kalan 4 değer — INSUFFICIENT_CASH,
  PRETRADE_CHECK_FAILED, MARKET_CLOSED, NEWS_BLACKOUT — Faz 5
  safety/pretrade modülüne ait, Bölüm 9 kapsamı dışında).

Sırada: Faz 4 — `backtest/` (Bölüm 12). İlk somut adım: `backtest/engine.py`'de
event-driven döngüyü yazmak (Bölüm 12.2'deki 4 adım: stop/target kontrolü
→ evaluate_exit → evaluate_entry+risk_engine → equity snapshot), look-ahead
yasağını garanti eden testleri (Bölüm 12.3) önce yazıp sonra motoru buna
göre doğrulamak. Ardından `backtest/metrics.py`, `backtest/walkforward.py`
(Bölüm 12.5, komşu-sağlamlık kriteri), `backtest/montecarlo.py` (Bölüm 12.6,
zaten spesifikasyonda hazır kod var), `backtest/cli.py` (Bölüm 12.8, sabit
`--seed` ile bit-bit determinizm testi dahil). Parametre taraması yalnızca
Bölüm 12.7'deki dar grid (27 kombinasyon): atr_stop_mult×adx_min×min_rr.

**HATIRLATMA — Faz 4 sonunda DURMA NOKTASI 1 var (Bölüm 0.1):** CLI tek
komutla rapor üretip determinizm/look-ahead testleri geçtiğinde
`BACKTEST_REVIEW.md` üretilip Faz 5'e GEÇİLMEDEN durulacak, kullanıcı onayı
beklenecek. Sonuçlar iyi görünse bile bu kural esnetilmez.

Bilinen sorun/blok: yok.

Varsayımlar/kararlar (Faz 3'te eklenenler):
- `BREAKER_FILE` yolu (`runtime/BREAKER_TRIPPED`) config'e alınmadı, Bölüm
  9.1'deki gibi sabit tutuldu — yalnızca `kill_switch_file` config'te
  (Bölüm 6 şeması zaten yalnızca onu listeliyor).
- `size_and_approve`'un `sig` argümanının yalnızca ENTER_LONG aksiyonlu ve
  suggested_stop/target dolu bir Signal olduğu varsayıldı (çağıranın
  sorumluluğu) — fonksiyon içinde bunun için ekstra None-guard eklenmedi,
  spec'in referans koduna sadık kalındı (iç sözleşmelere güven ilkesi).

Önceki fazlardan taşınan varsayımlar: pandas-ta yerine pandas-ta-classic +
numpy 2.2 (commit e31e401); BIST seans saatleri yaklaşık (Faz 5'te
doğrulanacak); `data.historical.download_bars` `period="max"` zorunlu;
resmi tatil takvimi MVP dışı; MACD "son 2 bar yükseliş" =
`hist[t]>hist[t-1]`; exit'in "3 bar düşüş" = kesin azalan üçlü sıralama.

Limit nedeniyle durdu mu: hayır.

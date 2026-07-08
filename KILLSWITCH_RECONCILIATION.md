# Kill-Switch Mutabakat Tablosu (F5-B1.1 K2)

**Tarih:** 2026-07-08 · **Kaynak ölçüm:** prod backtest (`backtest/run_family.py`,
`regime_core`, tam dönem 2005→2026, 5510 gün, 33 round-trip) —
`runtime/f5b1/killswitch_measurement.json`.

**İlke:** Kill-switch bir ANOMALİ dedektörüdür, normal drawdown yönetimi değil. Eşikler
tarihsel maksimumun ÖTESİNE konur → tarihsel tetiklenme 0; yalnız GÖRÜLMEMİŞ koşulda
fener yakar. Bu bir "ayar" değil, önceden kararlaştırılan mutabakat formülünün ölçümle
tamamlanmasıdır. **mode:paper ve mühürlü strateji parametreleri (N/b/M) DEĞİŞMEDİ** —
bunlar `config/regime_core.yaml::safety` operasyonel eşikleridir (ÖNERİ; kullanıcı/baş
danışman onayına tabi).

## Ölçüm özeti (prod backtest, tam dönem)
- En kötü tek gün: **−11.60%** (2013-06-03); günlük std %1.394; p1 −%3.94; p0.1 −%8.35.
- Max ardışık zarar-günü: 8 (bağlam); max ardışık KAYBEDEN round-trip: **5** (33 RT'de).
- Prod max drawdown: **−28.43%** (2013-11-11); tarihsel FREEZE tetiklenme: **0**; ALARM: 4.

## Tablo (5 switch)

| # | Switch | Eşik | Gerekçe / ölçüm mutabakatı | Kuru-test kanıtı |
|---|--------|------|-----------------------------|------------------|
| 1 | **Drawdown breaker** | ALARM −25% / FREEZE −40% | Tarihsel max DD −28.43%. FREEZE −40% bunun ~11.6 puan ALTINDA → tarihsel FREEZE=0 (doğrulandı). ALARM −25% tarihsel 4 kez (bildirim-only, davranış değişmez). KALICI KAYIT 6/8 ile tutarlı. | `test_kill_switch.py::test_drawdown_*` (ALARM/FREEZE ayrımı, latch) ✅ |
| 2 | **Günlük zarar** | −12% | Tarihsel en kötü tek gün −11.60% (2013-06-03). −12% bunun **0.40 puan altında** → tarihsel tetiklenme 0. (Eski 0.08 worst günü yakalayıp gereksiz FREEZE üretirdi — tek volatil gün D1 rejim filtresi başarısızlığı değil.) | `test_kill_switch.py::test_daily_loss_*` ✅ |
| 3 | **Ardışık kaybeden round-trip** | 7 | Mutabakat formülü "tarihsel maks + 2": max ardışık kaybeden RT = **5** → 5+2 = **7**. Tarihsel tetiklenme 0; görülmemiş kayıp serisi (filtre bozulması / yapı değişimi) sinyali. (Eski 4, tarihsel 5-streak'i yakalayıp tetiklenirdi.) | `test_kill_switch.py::test_consecutive_losses_*` (kalıcı sayaç, kazançta reset) ✅ |
| 4 | **Veri anomalisi** | stale > 172800s (~2 gün) VEYA tek-gün ham sıçrama > 20% | D1 günlük kadans: >2 takvim günü yeni bar yok = feed donması. Günlük getiri std %1.39, worst −11.6% → tek-sembol tek-gün ham >%20 sıçrama piyasa hareketi değil, bozuk/split veri şüphesi (data drift K4 ile tamamlayıcı). | `test_kill_switch.py::test_data_*` (stale + jump) ✅ |
| 5 | **API hata oranı** | ≥5 hata / 300s | Operasyonel (backtest-türevi değil): geçici ağ/servis hatası olağan; 5 dk'da ≥5 hata sistemik arıza sinyali → yeni ENTER durdur. Üstel geri çekilme istemcide (F5-A). | `test_kill_switch.py::test_api_error_*` (pencere + reset) ✅ |

## Not
- Tüm FREEZE çıkışları YALNIZCA kullanıcı komutuyla (otomatik reset YOK) — F5-A/B3 kuralı.
- Eşikler tarihsel-0-tetik ile konumlandığından, paper döneminde bir switch tetiklenirse
  bu GERÇEKTEN görülmemiş bir koşuldur ve operatör müdahalesi gerektirir (OPERATOR_GUIDE §4).
- 1-3 backtest-ölçümlü; 4-5 operasyonel. Değerler `config/regime_core.yaml::safety`'de
  ve `safety/kill_switch.py` fallback'lerinde senkron.

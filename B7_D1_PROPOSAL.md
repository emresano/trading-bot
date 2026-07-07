# B7'nin D1 (regime_core) Uyarlaması — ÖNERİ (karar kullanıcının)

**Statü:** ÖNERİ. Bu belge B7 (Faz 6 paper sayısal kabul kriterleri, HARDENING.md)
kriterlerini D1 rejim-filtreli çekirdek ailesine uyarlamayı **önerir** — hiçbir eşiği
mühürlemez, Faz 6 ölçümünü BAŞLATMAZ. Faz 6'nın resmi başlangıcı + bu kriterlerin
mühürlenmesi AYRI bir kullanıcı kararıdır (döngü birkaç gün stabil koştuktan sonra).

---

## 1. Sorun: "değerlendirilen sinyal" tanımı D1'de belirsiz

HARDENING B7: *"Süre ≥ 2 hafta VE değerlendirilen sinyal sayısı ≥ 10."*

- **10-gate ailesinde** "değerlendirilen sinyal" = bir ENTER **adayının huniden
  geçirilmesi** (her gün her sembol için funnel değerlendirmesi) → doğal olarak boldur.
- **D1'de** strateji tek bir **kompozit-rejim** kararıdır ve anahtarlama NADİRDİR
  (tarihsel ~yılda 3-4 round-trip). "Değerlendirilen sinyal = anahtarlama olayı" dersek,
  ≥10 olay ~3 yıl sürer — B7'nin "≥2 hafta" ruhunu kırar. Tanım uyarlanmalı.

## 2. ÖNERİLEN tanım (iki katman, farklı rol)

| Terim | D1 tanımı | B7'deki rolü |
|---|---|---|
| **Değerlendirilen sinyal** (öneri) | **Her işlem günü yapılan rejim değerlendirmesi** (kompozit vs MA(200)±bant → ON/OFF kararı). Her işlem günü = 1 değerlendirilen sinyal. | **≥10 sayımı BUNUNLA karşılanır** — 2 haftada ~10 işlem günü. D1'in "sinyali" sürekli günlük bir durumdur, kesikli bir funnel-geçişi değil. |
| **Anahtarlama olayı** | ENTER / INITIAL_ENTER / EXIT (rejim durumu değişimi). | Ayrı izlenir; **sayısı kabul kapısı DEĞİL** (nadir olması stratejinin doğası). Her anahtarlamanın paritesi (offline↔canlı) 0-fark olmalı. |

**Gerekçe:** D1'de "bot her gün doğru rejim kararını verdi mi + doğru yürüttü mü" sorusu
her işlem günü yanıtlanabilir (observe modda `signal_eval`, active modda `decision`
günlüğü). Kabul, işlem SAYISINA değil, günlük değerlendirmenin DOĞRULUĞUNA + operasyonel
sağlığa dayanmalı.

## 3. ÖNERİLEN D1 karne alanları (paper ↔ backtest beklentisi)

Faz 6 sonunda `PAPER_REVIEW.md` şu alanları raporlar (öneri):

**A. Operasyonel sağlık (B7 çekirdeği — hepsi bağlayıcı öneri):**
- Süre ≥ 2 hafta VE **değerlendirilen sinyal (işlem günü) ≥ 10**.
- 0 açıklanamayan mutabakat uyuşmazlığı (B2) — GÖLGE modda iç PaperBroker↔ledger.
- 0 çökme; heartbeat kesinti toplamı < eşik (öneri: tek kesinti ≤ 1 gün, toplam ≤ 2 gün).
- **B5 paritesi: 0 açıklanamayan anahtarlama farkı** (temiz replay ↔ canlı journal).
- Tüm kill-switch'ler ≥1 kez kuru-testle doğrulanmış (F5-A'da yapıldı; Faz 6'da korunur).
- Veri sağlığı: çapraz-kaynak çakışma sayısı raporlanır; "bar yok" günleri açıklanabilir
  (tatil/gecikme); ardışık veri-donması FREEZE'i tetiklenmemiş.

**B. D1-özel doğruluk (bilgilendirici + öneri kapıları):**
- **Kompozit/MA paritesi:** canlı depodan hesaplanan kompozit & MA(200), backtest
  snapshot'ından hesaplananla aynı günlerde ≤ ULP/tolerans farkı (veri kayması yok).
- **Anahtarlama paritesi:** paper döneminde gerçekleşen her anahtarlama tarihi/aksiyonu,
  aynı closes'la offline `run_regime_core_prod` ile BİREBİR (fark = kırmızı).
- **Yürütme sapması (izlenen, kapı DEĞİL):** t+1 kapanışa-yakın canlı fiyat vs backtest
  tam-kapanış fiyatı arasındaki equity sapması — beklenen, PHASE5_PLAN #3'te modellendi.
- **Nakit bacağı:** modellenmiş faiz tahakkuku formül-tutarlı (raporda AYRI satır);
  gerçek enstrüman kararı hâlâ real-öncesi kuyrukta (STATUS #19).

**C. Bilgilendirici (kabul kriteri DEĞİL — C2 ile uyumlu):**
- TRY/USD/enflasyon bazlı getiri satırları; rejim ON/OFF gün dağılımı; drawdown izi.

## 4. Ne YAPILMADI (bilinçli)
- Hiçbir eşik mühürlenmedi; Faz 6 ölçüm penceresi **başlatılmadı**.
- `go_live_date` null bırakıldı (observe mod) — resmi başlangıç ayrı karar.
- Kabul kriterleri D1'e uyarlanırken 10-gate'in orijinal B7 metni GEVŞETİLMEDİ;
  yalnızca "değerlendirilen sinyal" tanımı D1'in doğasına oturtuldu (öneri).

**Karar kullanıcının/baş danışmanın:** bu tanım + karne alanları kabul edilir mi,
hangi eşikler mühürlenir, Faz 6 ne zaman resmen başlar.

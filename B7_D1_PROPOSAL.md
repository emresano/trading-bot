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

## 2. Neden tek başına "günlük değerlendirme" yetersiz (F5-B1.1 K9 revizyonu)

İlk revizyon "değerlendirilen sinyal = günlük rejim değerlendirmesi" dedi. Bu, ≥10
sayımını 2 haftada karşılar AMA **yalnızca sürekliliği** ölçer: bot her gün doğru rejim
durumunu HESAPLADI mı? Bir kabul kriteri olarak zayıf, çünkü D1'de kritik risk
YÜRÜTME anındadır (nadir ENTER/EXIT) ve gölge dönemde hiç gerçek anahtarlama OLMAYABİLİR
— o zaman yürütme yolu HİÇ sınanmamış olarak "geçer". Bu yüzden **iki katmanlı karne**:

## 2.1 Katman K1 — MEKANİK KARNE (süreklilik/operasyonel sağlık)

Hepsi sağlanmadan geçilmez (öneri; mühürleme Faz 6 başında):
- **Süre ≥ 4 hafta KESİNTİSİZ** koşu (eski "2 hafta" yerine — yürütme yolunun sınanma
  olasılığını artırmak + operasyonel güveni pekiştirmek için).
- **0 çökme**; heartbeat kesinti toplamı < eşik (öneri: tek kesinti ≤ 1 gün, toplam ≤ 2 gün).
- **B5 paritesinde 0 AÇIKLANAMAYAN fark** (temiz replay ↔ canlı journal; anahtarlama diff'i).
- **Mutabakatta 0 AÇIKLANAMAYAN uyuşmazlık** (B2; GÖLGE iç PaperBroker↔ledger).
- **Tüm kill-switch'ler ≥1 kez kuru-testle** doğrulanmış (F5-A + K2 mutabakat tablosu; korunur).
- **Veri sağlığı:** çapraz-kaynak çakışma / DATA_DRIFT / "bar yok" günleri AÇIKLANABİLİR;
  faiz bayatlığı beklenen sınırda (K1); resync gerektiyse temiz kapanmış.
- **Günlük rejim değerlendirme sayısı** burada bir **MEKANİK SAĞLIK METRİĞİ** olarak kalır
  (bot her işlem günü çalıştı mı) — kabul kapısı değil, süreklilik göstergesi.

## 2.2 Katman K2 — OLAY KARNESİ (yürütme yolunun kanıtı)

Süreklilik yürütmeyi kanıtlamaz. Bu yüzden **en az 2 TATBİKAT** (öneri):
- **1 ENTER tatbikatı + 1 EXIT tatbikatı:** geçmiş GERÇEK bir anahtarlama gününün
  verisiyle tam akış provası (sinyal → boyutlama → paper fill → journal → parite →
  mutabakat), sonuçların beklenenle birebir tutması.
- **+ varsa GERÇEK anahtarlama:** gölge dönemde doğal bir ENTER/EXIT oluşursa o da olay
  karnesine sayılır (ve pariteyle doğrulanır).
- Amaç: "yürütme yolu gerçek bir anahtarlamada doğru davrandı" en az iki kez KANITLANSIN
  — sadece "her gün sinyal hesaplandı" değil.

> **Tatbikat İMPLEMENTASYONU bu turda YAPILMADI** (F5-B1.1 kapsamı değil). Bu, Faz 6
> başlangıcında tasarlanıp koşulacak bir prova mekanizmasının ÖNERİSİDİR. Not: F5-B1.1'de
> INITIAL_ENTER + EXIT akışları (K3/K6) gerçek+sentetik veriyle zaten uçtan uca sınandı —
> tatbikat mekanizması bunları Faz 6 kabul sürecine bağlayan resmi bir çerçevedir.

## 3. D1 karne alanları (paper ↔ backtest beklentisi — her iki katmanda raporlanır)

- **Kompozit/MA paritesi:** canlı depo kompoziti & MA(200), backtest snapshot'ıyla ortak
  günlerde ≤ tolerans (F5-B1'de **bit-bit 0.0** kanıtlandı; resync sonrası otomatik yeniden koşulur).
- **Anahtarlama paritesi:** her anahtarlama tarihi/aksiyonu offline `run_regime_core_prod`
  ile BİREBİR (fark = kırmızı).
- **Yürütme sapması (izlenen, kapı DEĞİL):** t+1 kapanışa-yakın canlı fiyat vs backtest
  tam-kapanış; ayrıca **veri-tamlığı** (kısmi basket yasağı, K6) yürütme öncesi doğrulanır.
- **Nakit bacağı:** modellenmiş faiz (K1 canlı besleme; bayatlık raporlanır); gerçek
  enstrüman real-öncesi kuyrukta (STATUS #19).
- **Bilgilendirici (kabul DEĞİL, C2):** TRY/USD/enflasyon getiri satırları; rejim ON/OFF
  gün dağılımı; drawdown izi.

## 4. Ne YAPILMADI (bilinçli)
- Hiçbir eşik mühürlenmedi; Faz 6 ölçüm penceresi **başlatılmadı**; `go_live_date` null.
- Tatbikat mekanizması İMPLEMENTE EDİLMEDİ (yalnız öneri).
- 10-gate'in orijinal B7 metni gevşetilmedi; D1'e uyarlandı + **sıkılaştırıldı** (2→4 hafta,
  olay karnesi eklendi).

**Karar kullanıcının/baş danışmanın:** iki-katmanlı karne + tatbikat çerçevesi kabul
edilir mi, hangi eşikler mühürlenir, Faz 6 ne zaman resmen başlar.

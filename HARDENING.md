# HARDENING.md — Kalite ve Güvenilirlik Sertleştirme Planı

**Konum:** Bu dosya `~/trading-bot/HARDENING.md` olarak kaydedilecek.
**Statü:** CLAUDE.md'ye EK'tir, onu geçersiz kılmaz. Çelişki durumunda CLAUDE.md + kullanıcı kararı geçerlidir.
**Tarih:** 2026-07-06

---

## 0. Yürütme Kuralları (önce bunu oku)

1. **İki zorunlu durma noktası aynen geçerlidir:** (a) hiçbir backtest sonucu ne kadar iyi görünürse görünsün, Faz 5'e geçiş yalnızca kullanıcı onayıyla olur; (b) `config.yaml`'daki `mode: paper` değeri hiçbir koşulda kod veya ajan tarafından `real` yapılmaz. Bu dosyadaki hiçbir madde bu iki kuralı gevşetmez.
2. Bu plan üç bölümdür: **A** (şimdi uygulanır — davranış değiştirmez), **B** (Faz 5 için bağlayıcı spesifikasyon — şimdi UYGULANMAZ, Faz 5'te uygulanır), **C** (sonrası — ayrı kullanıcı onayı gerektirir).
3. **v5 backtest koşusu tamamen bitmeden A bölümüne başlama.** Koşu sürerken repoya hiçbir yazma işlemi yapma.
4. Hiçbir görev sinyal motorunun, eşiklerin, gate'lerin veya risk motorunun davranışını değiştirmez. Bir A-görevi bulgusu veri düzeltmesi gerektirirse: düzeltme YAPILMAZ, raporlanır — düzeltme ayrı bir onaylı tur olur ve tam yeniden koşu (v6, "data-corrected" etiketiyle) gerektirir.
5. Her bölümün sonunda DUR: raporları üret, STATUS.md'yi güncelle, kullanıcı onayı bekle.
6. Kurulum adımı: bu dosyayı repoya ekle; CLAUDE.md'ye tek satır işaret koy: *"Faz 5 uygulamasında HARDENING.md Bölüm B gereksinimleri bağlayıcıdır."* CLAUDE.md'de başka hiçbir değişiklik yapma.

---

## BÖLÜM A — Şimdi (v5 raporu üretildikten sonra, davranış değişikliği yok)

### A1. Veri Dondurma (Snapshot) + Damgalama — tekrarlanabilirlik

**Neden:** yfinance geçmiş veriyi geriye dönük değiştirebilir (düzeltme katsayıları güncellenir). Bugünkü sonuçlar bir ay sonra aynı komutla yeniden üretilemeyebilir. Tekrarlanabilirlik olmadan hiçbir backtest bulgusu kalıcı kanıt değildir.

**Yapılacaklar:**
- 12 sembolün tam tarihçesini bir kez indir, `data/snapshots/<YYYY-MM-DD>/<SEMBOL>.parquet` olarak dondur.
- Snapshot manifest'i yaz: her dosyanın SHA256 hash'i + indirme zamanı + yfinance sürümü + indirme parametreleri (`auto_adjust` dahil).
- Backtest CLI'a `--snapshot <yol>` parametresi ekle: verildiğinde ağdan indirme YOK, yalnızca snapshot okunur. Parametre verilmezse mevcut davranış aynen korunur (geriye dönük uyumlu — v5 sonuçları etkilenmez).
- Her rapor başlığına üç damga: git commit (zaten var) + config hash + snapshot manifest hash.
- Git tag alışkanlığı: her backtest raporu için `backtest-vN` tag'i at (v1–v5 için geriye dönük, ilgili commit'ler belirlenebiliyorsa).

**Kabul kriteri:** Aynı snapshot + aynı commit + aynı config → bayt-bayt aynı `trades.csv`. Kanıt için tam süit gerekmez: tek sembollü kısa bir koşuyu iki kez çalıştırıp `diff` ile göster.

### A2. Veri Bütünlüğü Denetimi (read-only) — EN YÜKSEK BULGU DEĞERİ

**Neden:** BIST'te bedelli/bedelsiz sermaye artırımı ve temettü çok sıktır. Veri sağlayıcı bu kurumsal işlemleri hatalı düzelttiyse, backtest var olmayan kazanç/kayıplar üretir ve bunu hiçbir metrik göstermez. Bu, projenin şu anki en büyük sessiz riskidir.

**Yapılacaklar:** `tools/data_audit.py` — yalnızca okur, hiçbir veriyi değiştirmez. A1'de dondurulan snapshot üzerinde çalışır (tek indirme, iki iş). Her sembol için:
- Bar eksikliği: BIST işlem takvimine karşı eksik günler (semboller arası çapraz kontrol: bir sembolde var, diğerlerinde yok olan günler şüphelidir).
- Sıfır/negatif fiyat, yinelenen tarih, OHLC tutarlılığı (`low ≤ open,close ≤ high`).
- Şüpheli sıçrama taraması: |günlük getiri| > %25 olan tüm günler; her biri için tarih + getiri + hacim listele. Her sıçramayı sınıflandırmayı DENE: "muhtemel kurumsal işlem (düzeltme hatası olabilir)" / "muhtemel veri hatası" / "muhtemel gerçek hareket (hacim destekli)". Kesin hüküm verme, işaretle — hüküm kullanıcıyla birlikte verilecek.
- `auto_adjust` durumu ve Close vs Adj Close farkının nasıl ele alındığını açıkça raporla.

**Çıktı:** `DATA_AUDIT.md` — sembol başına PASS / WARN / FAIL özet tablosu + şüpheli gün listeleri + genel değerlendirme paragrafı.

**Kabul kriteri:** Rapor üretildi; `git status` yalnızca yeni tool + rapor gösteriyor, mevcut hiçbir dosya değişmedi.

**Önemli:** Bu denetim FAIL/ciddi WARN üretirse, v5 sonuçları veri düzeltilene kadar karantinadadır — raporda bunu açıkça yaz.

### A3. Sır ve Anahtar Güvenliği Denetimi

- Git geçmişinde sır taraması (anahtar/parola/token desenleri, basit regex taraması yeterli; harici araç kurma). Bulgu varsa RAPORLA — kendiliğinden geçmiş yeniden yazma YOK, karar kullanıcının.
- `.gitignore` denetimi: `.env`, `runtime/`, `data/snapshots/` (büyük dosyalar), log dosyaları kapsanıyor mu.
- Faz 5 için hedef tasarımı yaz (şimdi uygulama yok): AlgoLab kimlik bilgileri `.env` (izin 600) veya macOS Keychain; kodda ve loglarda asla düz metin; log çıktılarında otomatik maskeleme.

**Çıktı:** `SECURITY_AUDIT.md` (kısa).

### A4. Ortam Sabitleme

- `requirements.lock` üret (pip freeze) + Python sürümünü kaydet.
- README'ye "temiz kurulumdan yeniden üretim" bölümü ekle.

**Kabul kriteri:** Temiz bir venv'de lock dosyasından kurulum + tüm test süitinin yeşil geçtiğinin kanıtı.

### A Bölümü kapanışı
`HARDENING_STATUS.md` üret (A1–A4 durum tablosu), `STATUS.md`'yi güncelle, DUR — kullanıcı onayı bekle. B'ye başlama.

---

## BÖLÜM B — Faz 5 Bağlayıcı Spesifikasyonu (şimdi uygulanmaz; Faz 5 uygulamasında zorunlu)

Bu bölümdeki her madde, Faz 5'in "bitti" tanımının parçasıdır. Faz 5'e başlama onayı geldiğinde bu maddeler CLAUDE.md Bölüm 14 ile birlikte okunur.

### B1. BIST Mikro-Yapı Kuralları
- Seans takvimi: güncel işlem saatlerini, açılış/kapanış müzayede pencerelerini, yarım günleri ve resmi tatilleri **resmi BIST kaynağından doğrula** (varsayma), config'e taşı. Tüm zaman damgaları `Europe/Istanbul`.
- Müzayede pencerelerinde varsayılan davranış: yeni emir gönderme YOK; yalnızca sürekli işlem seansında emir.
- Tek-hisse volatilite tedbirleri / işlem durdurmaları: emir reddedilir veya askıda kalırsa davranış tanımlı olmalı — bekle → zaman aşımı → iptal → logla → o sembolde gün boyu yeni deneme yok.
- Fiyat adımı (tick) tablosuna göre yuvarlama; lot büyüklüğü doğrulaması.
- T+2 takas: satıştan gelen nakdin ne zaman yeniden kullanılabilir olduğunu **AlgoLab/aracı kurum kuralından doğrula** ve nakit muhasebesine işle. Bot hiçbir koşulda henüz kullanılabilir olmayan nakitle emir vermemeli.
- Tedbir/brüt takas listesindeki semboller: günlük kontrol, listedeyse yeni işlem AÇMA.

### B2. Başlangıç Mutabakatı ve Durum Kurtarma
- Her başlangıçta: broker'dan pozisyonlar + açık emirler çekilir, yerel durumla karşılaştırılır.
- Herhangi bir uyuşmazlık → **FREEZE** (yeni emir yok) + Telegram alarmı. İnsan onayı olmadan otomatik "düzeltme" YOK.
- Emir yaşam döngüsü kalıcı kayıt altında (gönderildi / kısmi doldu / doldu / reddedildi / iptal). "Emir gönderildi ama yanıt gelmeden çöküş" senaryosu için yeniden başlatmada broker'daki gerçek durum esas alınır — bu senaryo test edilecek.

### B3. Kill-Switch Hiyerarşisi
Her biri bağımsız, tetiklenince loglanır ve Telegram'a bildirir:
1. Günlük zarar limiti (config) → FREEZE (gün sonuna kadar).
2. Ardışık N zarar (config) → FREEZE.
3. Toplam DD breaker %10 (mevcut kural) → varsayılan FREEZE; FLATTEN (tüm pozisyonları kapat) yalnızca açık pozisyon stop'suz/korumasız kaldıysa.
4. Veri anomalisi: feed donması (X dakika yeni bar/fiyat yok) veya anlık fiyat sıçraması eşik üstü → FREEZE.
5. API hata oranı eşiği (ardışık/dakikadaki hata) → FREEZE.

Tüm FREEZE durumlarından çıkış **yalnızca kullanıcı komutuyla** (Telegram onaylı veya elle). Otomatik reset yok.

### B4. Karar Günlüğü (Decision Journal)
- Değerlendirilen her bar için: 10 gate'in sayısal değerleri + geçti/elendi + eleyen gate + nihai karar + pozisyon boyutu hesabı — yapılandırılmış JSONL.
- Her emir olayı: istek/yanıt özeti (kimlik bilgileri maskeli).
- Amaç: canlı dönemin her kararı sonradan denetlenebilir olsun; "bot neden bu işlemi açtı/açmadı" sorusu her zaman sayılarla yanıtlanabilsin.

### B5. Günlük Parite Kontrolü (canlı ↔ backtest determinizmi)
- Her gün kapanıştan sonra otomatik iş: günün verisi snapshot'lanır, sinyal motoru bu veriyle offline koşulur, üretilen kararlar canlıda alınan kararlarla diff'lenir.
- Fark = kırmızı alarm. Aynı kod + aynı veri → aynı karar olmak zorunda. Açıklanamayan fark, paper fazını başarısız sayar (B7).

### B6. İzleme ve Raporlama
- Heartbeat (mevcut plan) + günlük EOD özeti: pozisyonlar, günün kararları ve eleyen gate istatistikleri, hata sayaçları, ertesi gün takvim notları.
- Telegram komut güvenliği: durum komutları read-only; eylem komutları (pause/resume) ikinci bir onay ister; **"real moda geç" komutu hiçbir biçimde var olmayacak** (durma noktası 2'nin uzantısı).

### B7. Faz 6 (Paper) Sayısal Kabul Kriterleri — takvim değil, ölçüm
Paper dönemi "geçti" sayılır ancak şunların TAMAMI sağlanırsa:
- Süre ≥ 2 hafta VE değerlendirilen sinyal sayısı ≥ 10 (sinyal azsa süre uzatılır — süre doldu diye geçilmez).
- 0 açıklanamayan mutabakat uyuşmazlığı (B2).
- 0 çökme; heartbeat kesintisi toplamı tanımlı eşiğin altında.
- Emir reddi oranı < %5 ve her red açıklanabilir (B1 kuralları kapsamında).
- B5 parite kontrolünde 0 açıklanamayan fark.
- Tüm kill-switch'ler en az bir kez kuru-testle (simüle tetikleme) doğrulanmış.

Bu kriterlerin tamamı sağlansa bile real'e geçiş OTOMATİK DEĞİLDİR — yalnızca kullanıcı kararı (durma noktası 2 aynen geçerli).

---

## BÖLÜM C — Sonrası (ayrı kullanıcı onayı olmadan başlanmaz)

- **C1. Gate katkı analizi (read-only):** hangi gate kaç adayı eliyor; kazanan/kaybeden trade'lerde gate değer dağılımları. v5 kararından sonra, olası sadeleştirme (huni budama) tartışmasına sayısal girdi olarak.
- **C2. Enflasyon/USD bazlı bilgilendirici getiri satırları:** raporlara eklenecek, kabul kriterlerine dahil edilmeyecek.
- **C3. Likidite tavanı:** pozisyon ≤ 20 günlük medyan hacmin %X'i. Küçük sermayede pratik etkisi yok; real-para öncesi değerlendirilir.
- **C4. Real-para öncesi kontrol listesi:** Faz 6 sonunda kullanıcıyla birlikte yazılacak. Taslak başlıklar: başlangıç sermayesi tutarı, tek pozisyon max riski, acil durum elle müdahale prosedürü, izleme sıklığı taahhüdü, geri çekilme (bot'u durdurma) kriterleri.

---

## Raporlama Özeti

| Aşama | Çıktı | Sonrası |
|---|---|---|
| Kurulum | HARDENING.md repoda + CLAUDE.md'ye 1 satır işaret | A'ya geç (v5 bittiyse) |
| Bölüm A | HARDENING_STATUS.md, DATA_AUDIT.md, SECURITY_AUDIT.md, requirements.lock, snapshot altyapısı | DUR — kullanıcı onayı |
| Bölüm B | (şimdi çıktı yok — Faz 5'te bağlayıcı) | Faz 5 onayıyla birlikte devreye girer |
| Bölüm C | (onaysız başlanmaz) | — |

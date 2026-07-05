# Güvenlik Denetimi (SECURITY_AUDIT.md)

HARDENING.md A3 kapsamında yapılan sır/anahtar güvenlik denetimi. Salt-okunur —
hiçbir dosya değiştirilmedi, git geçmişi yeniden yazılmadı.

## 1. Git Geçmişinde Sır Taraması

**Yöntem:** `git log --all -p` üzerinden basit regex taraması (harici araç
kurulmadı) — şu desenler arandı:
- `(api_key|password|secret|token|access_key|private_key) [:=] "..."` şeklinde
  8+ karakterlik atamalar
- AWS-tarzı anahtarlar (`AKIA[0-9A-Z]{16}`)
- Özel anahtar (private key) başlıkları (`BEGIN ... PRIVATE KEY`)
- `config/secrets.env` (gerçek, dolu sır dosyası) veya herhangi bir `.env`
  dosyasının tüm dallardaki commit geçmişinde hiç var olup olmadığı

**Sonuç: TEMİZ.** Hiçbir gerçek sır bulunamadı.
- `config/secrets.env.example`'ın tüm geçmişteki tek hali: `ALGOLAB_API_KEY=API-XXXXXXXX`
  (yer tutucu, gerçek anahtar değil) + boş `USERNAME`/`PASSWORD`/`TOKEN`/`CHAT_ID` alanları.
- `config/secrets.env` (gerçek dosya) hiçbir commit'te hiç var olmamış.
- Hiçbir `.env` dosyası (herhangi bir isimle) hiçbir commit'te hiç var olmamış.
- AWS-tarzı anahtar, private key bloğu veya genel "uzun token" deseni bulunamadı.

## 2. `.gitignore` Denetimi

Mevcut `.gitignore`:
```
.venv/
__pycache__/
*.pyc
config/secrets.env
data/historical/*.parquet
*.sqlite
runtime/*
!runtime/.gitkeep
.DS_Store
```

| Kontrol | Durum | Not |
|---|---|---|
| `config/secrets.env` (gerçek sır dosyası) | ✅ Kapsanıyor | Tam yol olarak ignore edilmiş |
| `runtime/` (heartbeat, KILL_SWITCH, BREAKER_TRIPPED, algolab_session.json) | ✅ Kapsanıyor | `runtime/*` + `.gitkeep` istisnası |
| `*.sqlite` (journal, paper_state) | ✅ Kapsanıyor | |
| `data/historical/*.parquet` (yeniden üretilebilir cache) | ✅ Kapsanıyor | |
| **Genel `.env` deseni** | ⚠️ **KISMİ** | Yalnızca `config/secrets.env` tam yolu ignore edilmiş. Biri repo kökünde düz bir `.env` dosyası oluşturursa (yaygın bir alışkanlık) **ignore edilmez**. Öneri: `.gitignore`'a `*.env` (ve `!config/secrets.env.example` istisnası) eklenmeli — bu bir davranış değişikliği olmadığından ayrı bir onaylı görev olarak yapılabilir. |
| `data/snapshots/` (büyük dosyalar) | ℹ️ **Kasıtlı olarak ignore EDİLMEDİ** | A1'de v5 snapshot'ı (2.9 MB, 12 sembol) bilinçli olarak repoya committed edildi — tekrarlanabilirlik kanıtının kendisi bu. Risk: gelecekte çok daha fazla sembol/daha yüksek frekanslı veri dondurulursa repo boyutu hızla büyüyebilir. Öneri: belirli bir boyut eşiğinin (örn. 50 MB) üzerine çıkarsa Git LFS'e geçiş değerlendirilmeli. |
| Log dosyaları (`*.log`) | ℹ️ **Şu an geçerli değil** | Kod tabanında henüz dosyaya log yazan bir bileşen yok (Faz 5'te `notify/`, `main.py` ile gelecek). `.gitignore`'a `*.log` eklemek şimdiden ucuz bir önlem olur. |

**Genel değerlendirme:** Kritik bir gap yok (gerçek sır dosyası zaten kapsanıyor),
ama genel `*.env` deseni ve `*.log` deseni eklenerek savunma bir kademe daha
sağlamlaştırılabilir. Bunlar davranış değiştirmeyen, düşük riskli eklemeler —
ayrı bir onaylı görev olarak önerilir (A3 kapsamında UYGULANMADI, yalnızca
tespit edildi).

## 3. Faz 5 Hedef Tasarımı (şimdi UYGULANMADI — yalnızca tasarım)

Faz 5'te AlgoLab kimlik bilgileri devreye girdiğinde bağlayıcı olacak hedefler:

- **Saklama:** `config/secrets.env` dosyasında (repo dışı, `.gitignore`'da zaten
  kapsanıyor), dosya izni `600` (yalnızca sahibi okur/yazar) zorunlu — `auth.py`
  başlangıçta bu izni kontrol etmeli, izin gevşekse uyarı verip durmalı. Alternatif:
  macOS Keychain (`security` CLI aracılığıyla) — ikinci bir seçenek olarak
  değerlendirilebilir, MVP için `.env` + 600 izin yeterli.
- **Kod içinde asla düz metin:** API anahtarı/şifre/session hash hiçbir zaman
  kaynak koduna, commit mesajına veya yorum satırına yazılmaz (CLAUDE.md Bölüm
  0.2'de zaten yasak — burada yalnızca teyit ediliyor).
- **Loglarda asla düz metin:** `journal/journal.py`'nin `events` tablosuna veya
  `notify/telegram_bot.py`'nin gönderdiği herhangi bir mesaja API anahtarı/şifre/
  session hash asla yazılmaz. Hata mesajlarında (örn. AlgoLab API hata yanıtı)
  bu alanlar otomatik maskelenir (örn. `Authorization` header'ı loglanırken
  `***MASKED***` ile değiştirilir).
- **Otomatik maskeleme:** Faz 5'te bir log/hata-mesajı yardımcı fonksiyonu
  (`mask_secrets(text: str) -> str`) yazılacak — bilinen alan adlarını
  (`ALGOLAB_API_KEY`, `ALGOLAB_PASSWORD`, session hash deseni) regex ile
  tarayıp maskeler. Bu fonksiyon, `events` tablosuna ve Telegram'a giden HER
  mesajın son adımında zorunlu olarak çağrılır.

## Genel Sonuç

Git geçmişi temiz (sır bulunamadı). `.gitignore` gerçek sır dosyasını
kapsıyor; genel `.env`/`*.log` desenleri için küçük bir iyileştirme önerisi
var (uygulanmadı, ayrı onay gerektirir). Faz 5 hedef tasarımı yukarıda
belgelendi, bağlayıcı olacağı zaman (Faz 5 onayı) CLAUDE.md Bölüm 14 ile
birlikte okunmalı.

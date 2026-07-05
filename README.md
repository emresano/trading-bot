# trading-bot

BIST hisseleri + altın için konservatif, tam otomatik trading botu. Proje
spesifikasyonu, mimari ve çalışma kuralları için bkz. `CLAUDE.md` (tek kaynak
doküman). Kalite/güvenilirlik sertleştirme planı için bkz. `HARDENING.md`.
Güncel durum için bkz. `STATUS.md`.

> Bu README, henüz yalnızca **HARDENING.md A4**'ün istediği "temiz kurulumdan
> yeniden üretim" bölümünü içerir. Kurulum + işletme kılavuzunun tamamı Faz
> 5'te yazılacak (CLAUDE.md Bölüm 14).

## Temiz Kurulumdan Yeniden Üretim

Bu proje, `requirements.lock` ile tam olarak sabitlenmiş bir Python ortamında
test edildi. Aynı sonuçları yeniden üretmek için:

```bash
# Python 3.11 gerekli (test edilen: 3.11.6)
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.lock   # tam kilitli sürümler (requirements.txt'in üst kümesi)

pytest -q                          # tüm test süiti yeşil geçmeli (180/180, bu yazıldığında)
```

`requirements.lock`, `pip freeze` ile üretilmiş tam bağımlılık kilididir
(transitive bağımlılıklar dahil). Gündelik geliştirme için `requirements.txt`
(üst düzey, gevşek sabitlenmiş sürümler) kullanılır; `requirements.lock`
yalnızca **tekrarlanabilirlik kanıtı** içindir (HARDENING.md A4).

**Doğrulama:** Yukarıdaki adımlar temiz bir `venv`'de çalıştırılıp tüm test
süitinin yeşil geçtiği doğrulandı (bkz. `HARDENING_STATUS.md`).

## Backtest Verisini Yeniden Üretme (dondurulmuş snapshot ile)

Ağdan yeniden indirmeden, tam olarak v5 raporunun kullandığı veriyle bir
backtest koşturmak için:

```bash
python -m backtest.cli --symbols THYAO,GARAN,ASELS,AKBNK,KCHOL,SAHOL,EREGL,TUPRS,TCELL,TOASO,SISE,ARCLK \
    --config config/config.yaml \
    --snapshot data/snapshots/2026-07-06 \
    --start-date 2005-01-01 \
    --walk-forward --monte-carlo --regime-split --sweep --benchmark \
    --out runtime/backtest_reports/
```

`data/snapshots/2026-07-06/manifest.json`, her dosyanın SHA256 hash'ini
içerir — indirilen/kopyalanan verinin bozulmadığını doğrulamak için kullanılabilir.

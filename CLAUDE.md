# CLAUDE.md — BIST Trading Bot: Tam Otonom Geliştirme Spec'i (v3)

> **Bu dosya nedir:** Bu repo üzerinde çalışan her Claude Code oturumunun okuduğu tek kaynak dokümandır. Ürün spec'i, yazılım mimarisi, modül sözleşmeleri, referans kodlar, test gereksinimleri, faz planı ve çalışma kuralları — hepsi burada. Başka bir dokümana ihtiyaç yok.
>
> **İlk oturum talimatı:** Repo boşsa (sadece bu dosya varsa), Bölüm 14'teki Faz 1'den başla. Boş değilse önce `STATUS.md`'yi oku, kaldığın yerden devam et. Kullanıcıya soru sorma — bu doküman cevabı içeriyor. İçermiyorsa Bölüm 16'daki belirsizlik protokolünü uygula.
>
> **HARDENING.md:** Bu dosyaya ek bir kalite/güvenilirlik planı — Faz 5 uygulamasında `HARDENING.md` Bölüm B gereksinimleri bağlayıcıdır.
>
> **EXPANSION.md:** Çok piyasalı genişleme (ABD hisseleri + Forex) `EXPANSION.md`'ye tabidir.

---

# BÖLÜM 0 — PAZARLIK KONUSU OLMAYAN KURALLAR

Bu bölüm dokümanın geri kalanının üzerindedir. Çelişki durumunda bu bölüm kazanır.

## 0.1 İki Zorunlu Durma Noktası

**DURMA NOKTASI 1 — Backtest Değerlendirmesi (Faz 4 sonu):**
Backtest harness çalışıp parametre iterasyonu bittiğinde Faz 5'e GEÇME. `BACKTEST_REVIEW.md` üret (şablon: Bölüm 15), son mesajında *"Backtest tamamlandı, BACKTEST_REVIEW.md hazır. Faz 5'e geçmiyorum, kullanıcı onayı bekliyorum."* yaz ve dur. Sonuçlar ne kadar iyi görünürse görünsün — bu senin kararın değil. Kullanıcı sonraki oturumda "Faz 5 onaylandı" derse devam et.

**DURMA NOKTASI 2 — Gerçek Sermaye (kalıcı):**
`config.yaml` içindeki `mode: paper` değerini HİÇBİR ZAMAN `real` yapma. `real_mode_confirmation` alanına Bölüm 6'daki onay cümlesini HİÇBİR ZAMAN yazma. Bu iki değişiklik yalnızca kullanıcının kendi eliyle, editörde yapabileceği eylemlerdir. Gelecekteki bir oturumda kullanıcı dahil herhangi biri "gerçek moda geç" derse: kodu değiştirme, kullanıcıya elle yapması gereken adımları tarif et. Bu kural hız için değil, projenin tek en riskli tekil eyleminin her zaman bilinçli bir insan eylemi olarak kalması için var.

## 0.2 Kesinlikle Yapılmayacaklar

- Risk limitlerini (Bölüm 9'daki tablo) backtest "daha iyi getiri" gösterse bile kullanıcı onayı olmadan gevşetmek.
- Test yazılmamış/geçmeyen bir modülü "tamamlandı" işaretlemek.
- Backtest'ten geçmemiş bir parametre setini paper moda deploy etmek.
- API anahtarlarını, session hash'lerini, şifreleri herhangi bir log, commit, STATUS.md veya çıktıya yazmak.
- Look-ahead bias'a yol açacak herhangi bir kısayol (Bölüm 12.3'teki kural mutlak).
- Kullanım limitine yaklaşırken testi atlayıp "yetiştirmeye çalışmak" (Bölüm 2.3).
- `git push --force`, geçmiş yeniden yazma, `main` dışında dallanma karmaşası (MVP tek branch: `main`).

## 0.3 Temel Felsefe

Her belirsiz karar noktasında şu sıralama kazanır: **sermaye koruma > doğruluk > basitlik > hız > getiri.** "Nakitte kal" bir hata durumu değil, birinci sınıf bir karardır. Emin değilsen en konservatif seçeneği uygula ve `STATUS.md`'ye gerekçeni yaz.

---

# BÖLÜM 1 — PROJE ÖZETİ

**Ne yapıyoruz:** BIST hisseleri (2-3 likit BIST30 hissesi) + Altın için, sermaye korumayı birincil hedef alan, düşük-orta getirili, konservatif, tam otomatik bir trading botu. Trend-takip + pullback giriş stratejisi, 10 bileşenli sinyal hunisi, katı risk motoru, kapsamlı backtest altyapısı, paper-trading modu ve operasyonel güvenlik katmanı.

**Platform:** AlgoLab (Deniz Yatırım/DenizBank) REST API + WebSocket. Ücretsiz, bulut tabanlı. Ancak — kritik mimari karar — **backtest veri katmanı AlgoLab'dan tamamen bağımsızdır** (yfinance ile), böylece Faz 1-4 API onayı olmadan yürür. AlgoLab yalnızca Faz 5'te (canlı veri + emir iletimi) devreye girer.

**Deploy hedefi:** Kullanıcının Mac Mini M4'ü (7/24 açık), `launchd` ile servis olarak.

**Kapsam dışı (MVP):** Kredili işlem, açığa satış, forex (mimari hazır, adapter sonra), klasik grafik formasyonları (OBO, üçgen vb.), ML tabanlı sinyaller, web dashboard.

---

# BÖLÜM 2 — ÇALIŞMA PROTOKOLÜ

## 2.1 Oturum Akışı

1. Oturum başında `STATUS.md` oku (yoksa Faz 1'den başla).
2. Fazları Bölüm 14'teki sırayla, otonom, durma noktaları dışında durmadan yürüt.
3. Her fazın sonunda: o fazın "Bitti Tanımı"ndaki her maddeyi **çalıştırarak** doğrula (varsayma), `STATUS.md` güncelle, anlamlı commit'ler at.
4. Her mantıksal değişiklik = tek commit, açıklayıcı mesaj (`feat(risk): add daily loss limit breaker` formatı).

## 2.2 STATUS.md Şablonu

```markdown
# Proje Durumu
Son güncelleme: <ISO tarih-saat, Europe/Istanbul>
Şu an: Faz X — <görev>
Tamamlanan fazlar: <liste>
Bu oturumda yapılan: <madde madde>
Sırada: <bir sonraki somut adım — dosya/fonksiyon düzeyinde>
Bilinen sorun/blok: <yoksa "yok">
Varsayımlar/kararlar: <spec'te net olmayan yerlerde yapılan seçimler + gerekçe>
Limit nedeniyle durdu mu: <hayır | evet: ne zaman, hangi dosyada, yarım iş var mı>
```

## 2.3 Kullanım Limiti Protokolü

Rate-limit / kullanım limiti hatası alırsan veya yaklaştığını fark edersen:
1. Üzerindeki değişikliği ya tamamla ya da çalışan son duruma geri al — yarım, test edilmemiş kod commitlenmez.
2. `STATUS.md`'yi yukarıdaki formatla güncelle; amaç, sonraki oturumun tek kelimelik "devam et" ile hiçbir bağlam kaybı olmadan sürdürebilmesi.
3. Kullanıcıya net son mesaj: ne bitti, ne kaldı.
4. Limit sıfırlanınca kendiliğinden devam edemezsin; yeni oturumu kullanıcı başlatır — `STATUS.md` bunun için var.

## 2.4 Token Tasarrufu ve Dar Kapsamlı Çalışma

Bu proje tek oturumda bitmeyecek — **5 saatlik pencereye sığdırmaya çalışma, parça parça ilerle.** Aşağıdaki disiplin, hem token hem netlik için zorunlu:

- Oturum başında sadece `CLAUDE.md` ve `STATUS.md` oku. Repo'nun tamamını tarama.
- Bir dosyaya ihtiyacın varsa, önce onu bul (`rg`, `find`, `ls` ile dar kapsamlı arama), sonra sadece o dosyayı aç. Büyük dosyaları baştan sona, "ne olduğunu anlamak için" komple okuma — CLAUDE.md zaten her modülün ne yapması gerektiğini tarif ediyor, kodun kendisini keşfetmene çoğu zaman gerek yok.
- Mevcut mimariyi (Bölüm 3-4'teki sözleşmeler) bozmadan ilerle; geriye dönük uyumluluğu koru — bir dataclass alanını silmek/yeniden adlandırmak yerine ekle.
- **Her 4-5 anlamlı adımdan sonra** (tüm faz bitmese bile) `STATUS.md`'ye kısa bir not düş — bir sonraki oturumun (senin ya da başka bir Claude Code oturumunun) hiçbir ek bağlam olmadan kaldığın yerden anlayabileceği netlikte.
- İş beklediğinden büyürse (örn. bir faz içinde öngörülmeyen bir alt problem çıktıysa): olduğun yerde dur, `STATUS.md`'ye tam olarak nerede kaldığını ve neden durduğunu yaz, oturumu burada bitir. Zorla bitirmeye çalışıp kalite feda etme.
- Anlamlı ilerleme kaydettikten sonra commit at ve pushla (`git push`) — bir sonraki oturum güncel commit'ten devam etsin.

**Bunun Bölüm 0'daki iki durma noktasıyla ilişkisi:** Yukarıdakiler günlük çalışma temposu kuralları — ne zaman durup devam edeceğine dair. Durma Noktası 1 (Faz 4 sonu, backtest değerlendirmesi) ve Durma Noktası 2 (gerçek sermaye geçişi) bunlardan farklı ve daha üsttedir: onlar "iş büyüdü" ya da "token azaldı" gibi bir gerekçeyle değil, kullanıcı onayı gelmeden hiçbir koşulda geçilmeyen sabit kapılardır. Token tasarrufu için sık sık durman, bu iki noktayı ne gevşetir ne de onlara ek bir esneklik kazandırır.

## 2.5 Ortam

- Python **3.11+**, `venv` (`python3 -m venv .venv`), `requirements.txt` sabit sürümlü (`==`).
- Test: `pytest`. Her faz sonunda `pytest -q` temiz geçmeli.
- Zaman: **tüm iç temsil ve DB kayıtları UTC**; kullanıcıya gösterim ve piyasa-saat mantığı `Europe/Istanbul` (`zoneinfo`). Naive datetime yasak.
- `.gitignore`: `.venv/`, `__pycache__/`, `secrets.env`, `data/historical/*.parquet`, `*.sqlite`, `runtime/`.

---

# BÖLÜM 3 — MİMARİ

## 3.1 Tasarım İlkeleri

1. **Broker-agnostic çekirdek.** Sinyal, risk, backtest, journal hiçbir zaman "AlgoLab" bilmez; yalnızca `BrokerAdapter` soyut arayüzüyle konuşur. AlgoLab'a özgü her şey `execution/algolab/` altında hapistir.
2. **Saf fonksiyon çekirdeği, kirli kenarlar.** İndikatörler ve sinyal hunisi saf fonksiyonlardır (DataFrame girer, DataFrame/dataclass çıkar; IO yok, global state yok). IO (broker, DB, Telegram) yalnızca kenar modüllerde. Bu, backtest ile canlının **aynı sinyal kodunu** çalıştırmasını garanti eder — tutarlı sonuçların tek güvencesi budur.
3. **Config-driven.** Eşik, periyot, limit, sembol listesi — hepsi `config.yaml`. Kodda magic number yasak.
4. **Tek doğruluk kaynağı.** Bot'un state'i SQLite'tadır; broker'daki gerçeklikle düzenli mutabakat yapılır (reconciliation). Bellek-içi state çökmede kaybolabilir varsayılır.
5. **Genişletilebilirlik kancaları.** Yeni indikatör = registry'ye fonksiyon eklemek; yeni gate = huni listesine eklemek; yeni broker = ABC'yi implemente etmek; yeni enstrüman = config'e satır eklemek. (Bölüm 17'de adım adım rehber.)

## 3.2 Dizin Yapısı

```
trading-bot/
├── CLAUDE.md                    # bu dosya
├── STATUS.md                    # oturumlar arası durum
├── requirements.txt
├── config/
│   ├── config.yaml              # tüm parametreler (Bölüm 6'daki tam şema)
│   └── secrets.env              # API key, TC no, şifre, Telegram token (commitlenmez)
├── core/
│   ├── models.py                # dataclass'lar, enum'lar (Bölüm 4)
│   ├── config.py                # YAML+env yükleyici, doğrulayıcı
│   └── clock.py                 # timezone yardımcıları, BIST seans takvimi
├── data/
│   ├── historical.py            # yfinance indirici + parquet cache (backtest için)
│   ├── quality.py               # veri kalite kontrolleri
│   └── resample.py              # 1h → 4H, seans hizalı
├── indicators/
│   └── engine.py                # 10 bileşen, saf fonksiyonlar + registry (Bölüm 7)
├── strategy/
│   └── signal_engine.py         # 5 kademeli karar hunisi (Bölüm 8)
├── risk/
│   └── risk_engine.py           # pozisyon boyutu, limitler, circuit breaker (Bölüm 9)
├── execution/
│   ├── broker_adapter.py        # soyut arayüz (Bölüm 4.3)
│   ├── paper_broker.py          # dahili simülatör — paper modun kalbi (Bölüm 10)
│   └── algolab/
│       ├── auth.py              # login + SMS + session yönetimi (Bölüm 11.2)
│       ├── client.py            # throttle'lı HTTP istemci (Bölüm 11.3)
│       └── adapter.py           # BrokerAdapter implementasyonu (Bölüm 11.4)
├── safety/
│   ├── pretrade.py              # emir-öncesi sağlık kontrolleri (Bölüm 13.1)
│   ├── reconciliation.py        # bot-state ↔ broker mutabakatı (Bölüm 13.2)
│   └── watchdog.py              # heartbeat gözcüsü, ayrı süreç (Bölüm 13.3)
├── backtest/
│   ├── engine.py                # event-driven backtester (Bölüm 12)
│   ├── metrics.py               # performans metrikleri
│   ├── walkforward.py           # walk-forward doğrulama
│   ├── montecarlo.py            # Monte Carlo drawdown analizi
│   └── cli.py                   # tek komutluk arayüz
├── journal/
│   └── journal.py               # SQLite audit trail (Bölüm 5)
├── notify/
│   └── telegram_bot.py          # bildirim + komutlar (Bölüm 13.4)
├── main.py                      # canlı/paper döngüsü (Bölüm 13.5)
├── deploy/
│   └── com.tradingbot.plist     # macOS launchd servis tanımı
└── tests/
    ├── fixtures/                # sabit CSV'ler (golden test verisi)
    ├── test_indicators.py
    ├── test_signal_engine.py
    ├── test_risk_engine.py
    ├── test_backtest_engine.py
    ├── test_paper_broker.py
    └── test_safety.py
```

## 3.3 Veri Akışı (canlı/paper mod)

```
scheduler (bar kapanışı + 1dk)
  → data: son N bar çek (broker.get_bars)
  → data/quality: doğrula (bozuksa işlem yok + alert)
  → indicators/engine: özellik DataFrame'i üret
  → strategy/signal_engine: huni → Signal (ENTER_LONG | EXIT_LONG | HOLD_*)
  → risk/risk_engine: Signal + AccountState → TradeDecision (approved? qty? stop? target?)
  → safety/pretrade: son sağlık kontrolleri
  → execution/broker.submit_bracket_order  (paper → PaperBroker, real → AlgoLab)
  → journal: her adımı (reddedilenler dahil, gerekçeleriyle) SQLite'a yaz
  → notify: Telegram bildirimi
```

Backtest aynı zinciri kullanır; tek fark: `broker` yerine `backtest/engine.py`'nin simüle fill mekanizması ve `scheduler` yerine tarihsel bar iterasyonu. **Sinyal ve risk kodu bire bir aynıdır** — ayrı "backtest stratejisi" yazmak yasaktır.

---

# BÖLÜM 4 — ÇEKİRDEK SÖZLEŞMELER (core/models.py)

Bu dataclass'lar modüller arası tek konuşma dilidir. Alan ekleyebilirsin; alan silme/yeniden adlandırma tüm testlerin gözden geçirilmesini gerektirir.

```python
# core/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalAction(str, Enum):
    ENTER_LONG = "ENTER_LONG"
    EXIT_LONG = "EXIT_LONG"          # trend bozulması / momentum çöküşü kaynaklı çıkış
    HOLD_CASH = "HOLD_CASH"          # birinci sınıf karar: koşullar uygun değil
    HOLD_POSITION = "HOLD_POSITION"  # pozisyon var, koşullar hâlâ geçerli


class RejectReason(str, Enum):
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    WEEKLY_LOSS_LIMIT = "WEEKLY_LOSS_LIMIT"
    DRAWDOWN_BREAKER = "DRAWDOWN_BREAKER"
    MAX_POSITIONS = "MAX_POSITIONS"
    CORRELATION_LIMIT = "CORRELATION_LIMIT"
    MIN_RR_FAILED = "MIN_RR_FAILED"
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    POSITION_TOO_SMALL = "POSITION_TOO_SMALL"
    KILL_SWITCH = "KILL_SWITCH"
    PRETRADE_CHECK_FAILED = "PRETRADE_CHECK_FAILED"
    MARKET_CLOSED = "MARKET_CLOSED"
    NEWS_BLACKOUT = "NEWS_BLACKOUT"


@dataclass(frozen=True)
class Signal:
    symbol: str
    ts: datetime                      # sinyalin dayandığı barın kapanış zamanı (UTC)
    action: SignalAction
    reasons: list[str]                # her gate'in kararı, insan-okur formatta
    features: dict[str, float]        # karar anındaki indikatör değerleri (journal için)
    entry_ref_price: float            # sinyal barının kapanışı (boyutlama referansı)
    suggested_stop: Optional[float] = None
    suggested_target: Optional[float] = None


@dataclass(frozen=True)
class TradeDecision:
    signal: Signal
    approved: bool
    reject_reasons: list[RejectReason] = field(default_factory=list)
    quantity: int = 0
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    risk_amount_try: float = 0.0      # bu işlemde riske edilen TL


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    stop_price: float
    target_price: float
    opened_at: datetime
    broker_order_ids: list[str] = field(default_factory=list)


@dataclass
class AccountState:
    equity: float                     # nakit + pozisyonların piyasa değeri
    cash: float
    positions: list[Position]
    peak_equity: float                # circuit breaker referansı (journal'dan beslenir)
    realized_pnl_today: float
    realized_pnl_week: float
```

## 4.3 BrokerAdapter Soyut Arayüzü

```python
# execution/broker_adapter.py
from abc import ABC, abstractmethod
import pandas as pd
from core.models import AccountState, Position, Side


class BrokerAdapter(ABC):
    """Çekirdeğin dış dünyayla tek temas noktası.
    Implementasyonlar: PaperBroker (dahili simülatör), AlgoLabAdapter.
    Tüm metodlar senkron; hata durumunda BrokerError fırlatır (sessiz None dönmek yasak)."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def get_account_state(self) -> AccountState: ...

    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        """DataFrame index=UTC DatetimeIndex, kolonlar: open, high, low, close, volume.
        timeframe ∈ {"1d", "4h", "1h"}. Son bar KAPANMIŞ bar olmalı (oluşmakta olan bar dahil edilmez)."""

    @abstractmethod
    def get_last_price(self, symbol: str) -> float: ...

    @abstractmethod
    def submit_bracket_order(self, symbol: str, side: Side, quantity: int,
                             stop_price: float, target_price: float) -> list[str]:
        """Piyasa emri + broker tarafında bekleyen stop ve hedef emirleri.
        Dönen değer: broker order id listesi. Broker bracket'ı native desteklemiyorsa
        adapter bunu üç ayrı emirle taklit eder ama ÇAĞIRAN bunu bilmez."""

    @abstractmethod
    def close_position(self, symbol: str) -> None: ...

    @abstractmethod
    def cancel_all_orders(self, symbol: str) -> None: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_open_orders(self) -> list[dict]: ...

    @abstractmethod
    def is_market_open(self) -> bool: ...


class BrokerError(Exception):
    pass
```

---

# BÖLÜM 5 — JOURNAL ŞEMASI (journal/journal.py)

SQLite, dosya: `runtime/journal.sqlite`. Her tabloda `created_at` UTC ISO string.

```sql
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL, symbol TEXT NOT NULL, action TEXT NOT NULL,
    reasons_json TEXT NOT NULL, features_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER REFERENCES signals(id),
    approved INTEGER NOT NULL, reject_reasons_json TEXT,
    quantity INTEGER, stop_price REAL, target_price REAL, risk_amount_try REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER REFERENCES decisions(id),
    broker_order_id TEXT, symbol TEXT, side TEXT, quantity INTEGER,
    order_type TEXT, status TEXT,          -- SUBMITTED/FILLED/CANCELLED/REJECTED
    fill_price REAL, filled_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL, equity REAL, cash REAL, open_positions INTEGER,
    realized_pnl_today REAL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL, level TEXT,          -- INFO/WARN/ERROR/CRITICAL
    category TEXT,                          -- HEARTBEAT/RECON/BREAKER/AUTH/DATA/...
    message TEXT, created_at TEXT NOT NULL
);
```

Kurallar: reddedilen kararlar da yazılır (gerekçeleriyle) — "neden işlem YAPMADIN" sorusu da cevaplanabilir olmalı. `peak_equity`, `equity_snapshots`'tan türetilir. Journal yazma hatası işlemi durdurmaz ama `events`'e ERROR düşer ve Telegram'a bildirilir.

---

# BÖLÜM 6 — CONFIG ŞEMASI (config/config.yaml — tam hali)

Bu dosyayı Faz 1'de aynen oluştur. `core/config.py` bunu yükler, tipleri ve aralıkları doğrular (örn. `risk_per_trade_pct` 0'dan büyük, 0.02'den küçük olmalı — değilse başlatma reddedilir).

```yaml
mode: paper                # paper | real — Bölüm 0.1 Durma Noktası 2'ye tabidir
real_mode_confirmation: "" # real mod için kullanıcının ELLE yazması gereken cümle:
                           # "GERCEK PARA RISKINI ANLIYORUM VE KABUL EDIYORUM"
                           # Kod bu cümleyi birebir doğrular; Claude Code bu alanı ASLA doldurmaz.

timezone: "Europe/Istanbul"

instruments:
  - symbol: "THYAO"        # AlgoLab sembol kodu
    yf_symbol: "THYAO.IS"  # backtest veri kaynağı
    type: equity
    lot_step: 1
  - symbol: "GARAN"
    yf_symbol: "GARAN.IS"
    type: equity
    lot_step: 1
  - symbol: "ASELS"
    yf_symbol: "ASELS.IS"
    type: equity
    lot_step: 1
  # Altın: Faz 5'te AlgoLab sembol listesinden gerçek kod doğrulanınca eklenecek (Bölüm 16).
  # Backtest proxy'si: XAUUSD × USDTRY / 31.1035 (gram altın TL) — data/historical.py destekler.

timeframes:
  trend: "1d"              # kademe 1-4 hesapları
  entry: "4h"              # kademe 5 (tetik) + MTF uyum
  source_intraday: "1h"    # 4H bunun resample'ı (seans hizalı, Bölüm 7.5)

signal:
  ema_fast: 50
  ema_slow: 200
  adx_period: 14
  adx_min: 20              # altında → HOLD_CASH
  rsi_period: 14
  rsi_entry_low: 40
  rsi_entry_high: 55
  macd: [12, 26, 9]
  atr_period: 14
  atr_stop_mult: 1.5
  atr_anomaly_mult: 2.0    # ATR > 20-gün ATR ort × bu → HOLD_CASH
  bb_period: 20
  bb_std: 2.0
  swing_lookback: 50       # destek/direnç için bar sayısı
  swing_fractal_n: 2       # swing high/low tanımı: her iki yanda n bar
  volume_confirm_mult: 1.5 # kırılım hacmi ≥ 20-bar ort × bu
  min_history_bars: 260    # bundan az veri varsa sembol o gün işlem görmez

risk:
  risk_per_trade_pct: 0.0075      # sermayenin %0.75'i
  daily_loss_limit_pct: 0.025
  weekly_loss_limit_pct: 0.05
  max_open_positions: 2
  max_position_notional_pct: 0.25 # tek pozisyon, sermayenin en fazla %25'i
  max_drawdown_breaker_pct: 0.10  # tepe equity'den %10 → tam durdurma, manuel restart
  min_rr: 1.8
  correlation_lookback_days: 90
  correlation_max: 0.85           # iki açık pozisyonun getirileri arası korelasyon üstü yasak
  news_blackout: true             # bilanço/KAP günü çevresinde yeni pozisyon yok (Bölüm 13.1)

costs:                     # backtest + paper broker'da uygulanır
  commission_bps: 10       # tek yön; kullanıcı Deniz Yatırım gerçek oranını girecek
  slippage_bps: 5

backtest:
  start: "2018-01-01"
  end: "auto"              # bugüne kadar
  initial_equity: 100000
  walk_forward:
    train_months: 24
    test_months: 6
    step_months: 6
  monte_carlo_runs: 500
  random_seed: 42          # deterministik sonuç — tutarlılık şartı

execution:
  bar_close_grace_sec: 60  # bar kapanışından sonra bekleme (veri otursun)
  order_timeout_sec: 30
  algolab_throttle_sec: 5.1   # AlgoLab bilinen limiti: ~5 sn/istek (Bölüm 11.3)

paper:
  initial_equity: 100000
  fill_model: "next_tick_with_slippage"

safety:
  heartbeat_interval_sec: 300
  heartbeat_stale_sec: 900       # watchdog: bu süre sinyal yoksa CRITICAL alarm
  reconciliation_interval_min: 15
  kill_switch_file: "runtime/KILL_SWITCH"   # bu dosya varsa: yeni işlem yok
  max_price_jump_pct: 0.08       # son fiyat, önceki kapanıştan bu kadar sapmışsa emir gönderme (bozuk veri şüphesi)

telegram:
  enabled: true
  # token ve chat_id secrets.env'de: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
```

`secrets.env` şablonu (Faz 1'de `secrets.env.example` olarak commitle, gerçeğini kullanıcı doldurur):

```
ALGOLAB_API_KEY=API-XXXXXXXX
ALGOLAB_USERNAME=            # TC kimlik no veya Deniz müşteri no
ALGOLAB_PASSWORD=            # internet şubesi şifresi
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
```

---

# BÖLÜM 7 — VERİ KATMANI VE İNDİKATÖR MOTORU

## 7.1 Tarihsel Veri (data/historical.py) — backtest kaynağı

- Kaynak: `yfinance`. Günlük: sınırsız geçmiş. Saatlik (`1h`): yfinance ~730 günle sınırlıdır — 4H analizi backtest'te son ~2 yıl için mümkündür; daha eski dönemlerde huni yalnızca günlük kademelerle koşar ve tetik kademesi günlük mum formasyonlarına düşer (`signal_engine` bu degrade modu destekler; backtest raporunda hangi dönemin hangi modda koştuğu belirtilir).
- Cache: `data/historical/{symbol}_{tf}.parquet`. İndirici artımlıdır: mevcut parquet'in son tarihinden itibaren çeker, birleştirir, tekrar yazar.
- Altın proxy'si: `XAUUSD` (yfinance: `GC=F` yerine `XAUUSD=X` yoksa `GC=F`) × `USDTRY=X` / 31.1035 → gram altın TL serisi. Fonksiyon: `build_gold_try_proxy()`. Hacim kolonu sentetik olduğu için altında hacim gate'i otomatik SKIP sayılır (gate PASS döner, reason "volume gate skipped: synthetic series").

## 7.2 Veri Kalitesi (data/quality.py)

Her DataFrame işlenmeden önce şu kontrollerden geçer; geçemeyen sembol o turda işlem görmez (`events`'e WARN):
1. NaN yok (varsa: baştaki warm-up NaN'ları hariç → satır at, ortadaki NaN → fail).
2. Index monoton artan, duplicate yok.
3. `high >= max(open, close)`, `low <= min(open, close)` her satırda.
4. Ardışık kapanışlar arası %20'den büyük sıçrama → WARN + o sembolde o gün işlem yok (temettü/split ayarlanmamış veri şüphesi; yfinance `auto_adjust=True` kullanılır ki bu riski azaltsın).
5. Son bar zamanı beklenenden eskiyse (stale data) → fail.

## 7.3 İndikatör Motoru (indicators/engine.py)

Kütüphane: `pandas-ta`. Her indikatör saf fonksiyon; hepsi tek registry'de:

```python
# indicators/engine.py  (iskelet — tamamı bu kalıpla yazılır)
import pandas as pd
import pandas_ta as ta

def add_ema(df: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    df[f"ema_{fast}"] = ta.ema(df["close"], length=fast)
    df[f"ema_{slow}"] = ta.ema(df["close"], length=slow)
    return df

def add_adx(df, period): ...        # kolon: adx
def add_rsi(df, period): ...        # kolon: rsi
def add_macd(df, fast, slow, sig):  # kolonlar: macd, macd_signal, macd_hist
    ...
def add_atr(df, period):            # kolonlar: atr, atr_ma20 (=atr'nin 20-bar SMA'sı)
    ...
def add_bbands(df, period, std):    # kolonlar: bb_low, bb_mid, bb_high, bb_width
    ...
def add_swings(df, n: int):
    """Fraktal swing: swing_high[i]=True ise high[i] her iki yanındaki n barın high'ından büyük.
    Son n bar için tanımsız (geleceğe bakamayız) → False. Kolonlar: swing_high, swing_low (bool)."""
    ...
def add_support_resistance(df, lookback: int):
    """Son `lookback` bardaki swing seviyelerinden en yakın destek (altta) ve direnç (üstte).
    Kolonlar: nearest_support, nearest_resistance (float, yoksa NaN)."""
    ...
def add_volume_confirm(df, mult: float):
    """Kolon: vol_confirm (bool) = volume >= 20-bar SMA(volume) * mult"""
    ...
def add_candle_patterns(df):
    """Elle implementasyon — pandas-ta'nın pattern modülüne güvenme (TA-Lib bağımlılığı var).
    bullish_engulfing: önceki bar kırmızı, bu bar yeşil, bu barın gövdesi öncekinin gövdesini kapsar.
    pin_bar_bull: alt fitil >= gövde*2, üst fitil <= gövde*0.5, kapanış barın üst yarısında.
    inside_bar_breakout_bull: önceki bar inside bar (high<prev_high, low>prev_low) ve
                              bu barın kapanışı inside barın high'ının üstünde.
    Kolonlar: pat_engulf, pat_pin, pat_inside_break (bool)"""
    ...

FEATURE_PIPELINE = [add_ema, add_adx, add_rsi, add_macd, add_atr,
                    add_bbands, add_swings, add_support_resistance,
                    add_volume_confirm, add_candle_patterns]

def build_features(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Pipeline'ı sırayla uygular. Girdi df'i mutate etmez (copy).
    Warm-up dönemi (ilk max(ema_slow, ...) bar) NaN kalır; huni bunları işlemez."""
```

## 7.4 Golden Testler (tests/test_indicators.py)

- `tests/fixtures/thyao_daily_2022.csv`: yfinance'ten indirilen, repoya sabitlenmiş ~300 barlık gerçek veri. Testler bu sabit dosyayla koşar — ağa bağımlı test yasak.
- Sınır testleri: RSI ∈ [0,100]; ATR > 0; EMA son değeri, elle hesaplanmış referansla 1e-6 toleransta eşleşir (fixture'ın son 5 barı için beklenen değerler test dosyasına hard-code edilir — bu değerleri pandas-ta ile bir kez üretip sabitle; amaç ileride kütüphane sürüm değişikliğinde sessiz davranış kaymasını yakalamak).
- Pattern testleri: elle kurgulanmış 5-6 barlık mini DataFrame'lerle her pattern'in true/false döndüğü senaryolar.

## 7.5 4H Resample (data/resample.py)

BIST seansı ~10:00–18:00 Istanbul. 1h barları 4H'a şöyle hizala: `df.resample("4h", origin="start_day", offset="10h")` mantığıyla gün içinde 10:00–14:00 ve 14:00–18:00 iki barı oluşur (Istanbul saatinde hesapla, sonra UTC'ye çevir). Eksik saat barı varsa o 4H barı NaN bırak → quality katmanı yakalar.

---

# BÖLÜM 8 — SİNYAL MOTORU: 10 BİLEŞEN, 5 KADEMELİ HUNİ (strategy/signal_engine.py)

## 8.1 Bileşen Tablosu

| Kademe | Bileşen | Rol | Parametre (config'den) |
|---|---|---|---|
| 1 | EMA50/EMA200 (1d) | Yön: close > ema200 ve ema50 > ema200 değilse long düşünme | ema_fast/slow |
| 1 | ADX (1d) | Rejim: adx < adx_min → HOLD_CASH | adx_min |
| 2 | RSI (1d) | Pullback girişi: rsi ∈ [40,55] | rsi_entry_low/high |
| 2 | MACD (1d) | Teyit: macd > macd_signal VEYA macd_hist yükseliyor (son 2 bar) | macd |
| 3 | ATR (1d) | Stop mesafesi + anomali filtresi: atr > atr_ma20×2 → HOLD_CASH | atr_* |
| 3 | Bollinger (1d) | Aşırı uzama filtresi: close > bb_high ise giriş yok (kovalamaca yasak) | bb_* |
| 4 | Destek/Direnç | Hedef mantığı: nearest_resistance hedef referansı; direnç çok yakınsa (R:R tutmaz) giriş yok | swing_lookback |
| 4 | Hacim | Tetik barında vol_confirm zorunlu | volume_confirm_mult |
| 5 | Mum formasyonu (4h) | Tetik: pat_engulf VEYA pat_pin VEYA pat_inside_break | — |
| 5 | MTF uyum | 4h kapanış > 4h ema50 (günlük trend ile 4h çelişmiyor) | — |

## 8.2 Gate Mimarisi — genişletilebilirliğin kalbi

```python
# strategy/signal_engine.py (çekirdek yapı — aynen bu kalıpla)
from dataclasses import dataclass
from typing import Callable
from core.models import Signal, SignalAction

@dataclass(frozen=True)
class GateResult:
    passed: bool
    name: str
    detail: str          # örn: "ADX=17.3 < min 20 → yatay piyasa"

Gate = Callable[..., GateResult]   # (daily_row, h4_row, cfg) -> GateResult

def gate_trend(d, h4, cfg) -> GateResult:
    ok = d["close"] > d["ema_200"] and d["ema_50"] > d["ema_200"]
    return GateResult(ok, "trend", f"close={d['close']:.2f} ema200={d['ema_200']:.2f} ema50={d['ema_50']:.2f}")

# ... her gate aynı imzayla: gate_regime, gate_rsi, gate_macd, gate_atr_anomaly,
#     gate_bb_overextension, gate_structure_rr, gate_volume, gate_trigger_4h, gate_mtf

ENTRY_GATES: list[Gate] = [gate_trend, gate_regime, gate_rsi, gate_macd,
                           gate_atr_anomaly, gate_bb_overextension,
                           gate_structure_rr, gate_volume, gate_trigger_4h, gate_mtf]

def evaluate_entry(symbol, daily_df, h4_df, cfg) -> Signal:
    d = daily_df.iloc[-1]            # SON KAPANMIŞ günlük bar
    h4 = h4_df.iloc[-1] if h4_df is not None else None
    results, features = [], snapshot_features(d, h4)
    for gate in ENTRY_GATES:
        r = gate(d, h4, cfg)
        results.append(f"[{'PASS' if r.passed else 'FAIL'}] {r.name}: {r.detail}")
        if not r.passed:
            return Signal(symbol, d.name, SignalAction.HOLD_CASH, results, features,
                          entry_ref_price=float(d["close"]))
    stop = float(d["close"] - cfg.signal.atr_stop_mult * d["atr"])
    target = compute_target(d, cfg)   # nearest_resistance; NaN ise close + 2×(close-stop)
    return Signal(symbol, d.name, SignalAction.ENTER_LONG, results, features,
                  entry_ref_price=float(d["close"]),
                  suggested_stop=stop, suggested_target=target)
```

**Çıkış mantığı (`evaluate_exit`)** — açık pozisyon için her günlük bar kapanışında:
- close < ema_50 (1d) VEYA macd_hist üç bardır düşüyor ve macd < signal → `EXIT_LONG` ("trend zayıflıyor, karı/küçük zararı al").
- Aksi halde `HOLD_POSITION`. (Stop ve hedef zaten broker/paper tarafında bekleyen emir olarak duruyor — çıkış sinyali onların üstüne üçüncü bir korumadır.)

**Degrade mod:** `h4_df is None` (eski backtest dönemi) → `gate_trigger_4h` günlük pattern kolonlarına bakar, `gate_mtf` SKIP-PASS döner. Her SKIP reason'da açıkça yazılır.

## 8.3 Testler (tests/test_signal_engine.py)

Sentetik DataFrame'lerle her gate için ayrı ayrı: geçmesi gereken durumda geçtiği, kalması gereken durumda kaldığı ve `detail` string'inin doğru değerleri içerdiği. Ayrıca huni bütünü: "9 gate PASS + 1 FAIL → HOLD_CASH ve reasons listesinde tam 10 satır var" testi.

---

# BÖLÜM 9 — RİSK MOTORU (risk/risk_engine.py)

## 9.1 Kurallar (hepsi config'den; kod hiçbirini hard-code etmez)

| Kural | Config alanı | Davranış |
|---|---|---|
| İşlem başına risk | risk_per_trade_pct | Boyutlama formülünün girdisi |
| Günlük zarar limiti | daily_loss_limit_pct | Aşıldıysa gün sonuna kadar tüm ENTER reddedilir |
| Haftalık zarar limiti | weekly_loss_limit_pct | Aşıldıysa hafta sonuna kadar reddet + Telegram CRITICAL |
| Maks. açık pozisyon | max_open_positions | Doluysa reddet |
| Pozisyon tavanı | max_position_notional_pct | qty bu tavana kırpılır |
| Drawdown breaker | max_drawdown_breaker_pct | equity < peak×(1-x) → `runtime/BREAKER_TRIPPED` dosyası yaz, tüm yeni işlemler durur; dosyayı ancak kullanıcı elle siler |
| Min R:R | min_rr | (target-entry)/(entry-stop) < min_rr → reddet |
| Korelasyon | correlation_max | Aday sembolün son 90 günlük getirileri, herhangi bir açık pozisyonla > 0.85 korele → reddet |
| Kill switch | kill_switch_file | Dosya varsa tüm ENTER reddedilir (çıkışlar serbest — pozisyon kapatmak her zaman izinli) |

## 9.2 Boyutlama — referans implementasyon

```python
# risk/risk_engine.py
import math
from core.models import Signal, TradeDecision, AccountState, RejectReason

def size_and_approve(sig: Signal, acct: AccountState, cfg, corr_fn) -> TradeDecision:
    rejects = []
    entry, stop, target = sig.entry_ref_price, sig.suggested_stop, sig.suggested_target

    # --- kapılar (sıra önemli: en ucuz kontroller önce) ---
    if kill_switch_active(cfg):            rejects.append(RejectReason.KILL_SWITCH)
    if breaker_tripped():                  rejects.append(RejectReason.DRAWDOWN_BREAKER)
    if acct.realized_pnl_today <= -cfg.risk.daily_loss_limit_pct * acct.equity:
        rejects.append(RejectReason.DAILY_LOSS_LIMIT)
    if acct.realized_pnl_week <= -cfg.risk.weekly_loss_limit_pct * acct.equity:
        rejects.append(RejectReason.WEEKLY_LOSS_LIMIT)
    if len(acct.positions) >= cfg.risk.max_open_positions:
        rejects.append(RejectReason.MAX_POSITIONS)
    rr = (target - entry) / (entry - stop) if entry > stop else 0.0
    if rr < cfg.risk.min_rr:               rejects.append(RejectReason.MIN_RR_FAILED)
    if corr_fn(sig.symbol, acct.positions) > cfg.risk.correlation_max:
        rejects.append(RejectReason.CORRELATION_LIMIT)
    if rejects:
        return TradeDecision(sig, approved=False, reject_reasons=rejects)

    # --- boyutlama ---
    risk_amount = acct.equity * cfg.risk.risk_per_trade_pct
    per_share_risk = entry - stop                     # > 0 garantili (yukarıda kontrol)
    qty = math.floor(risk_amount / per_share_risk)
    max_notional = acct.equity * cfg.risk.max_position_notional_pct
    qty = min(qty, math.floor(max_notional / entry))
    qty = min(qty, math.floor(acct.cash / (entry * (1 + cfg.costs.commission_bps / 1e4))))
    if qty < 1:
        return TradeDecision(sig, approved=False,
                             reject_reasons=[RejectReason.POSITION_TOO_SMALL])
    return TradeDecision(sig, approved=True, quantity=qty,
                         stop_price=stop, target_price=target,
                         risk_amount_try=qty * per_share_risk)
```

## 9.3 Testler (tests/test_risk_engine.py)

Her reddetme nedeni için ayrı test; boyutlama için sayısal örnek testi (equity=100.000, risk %0.75, entry=100, stop=94 → risk 750 TL / 6 TL = 125 lot; notional tavanı 25.000/100=250 → bağlayıcı değil → beklenen qty=125). Kırpma senaryoları: notional tavanının bağladığı, nakdin bağladığı, qty<1 durumu.

---

# BÖLÜM 10 — PAPER BROKER (execution/paper_broker.py)

Paper mod, AlgoLab demo ortamının API'den erişilebilirliğine BAĞIMLI DEĞİLDİR — kendi simülatörümüz var. Bu, Faz 5'in en kritik tasarım kararı: canlı fiyat verisi AlgoLab'dan (ya da o da yoksa yfinance gecikmeli veriden) gelir, emirler ise `PaperBroker` içinde simüle dolar.

Davranış spesifikasyonu:
- `submit_bracket_order`: piyasa emri anındaki `get_last_price` üzerine `slippage_bps` eklenerek dolar; komisyon düşülür; pozisyon ve bekleyen stop/target kaydı SQLite'a (`runtime/paper_state.sqlite`) yazılır — süreç yeniden başlasa da state kaybolmaz.
- Her yeni fiyat gözleminde bekleyen stop/target kontrol edilir: `last <= stop` → stop fill (slippage stop aleyhine uygulanır), `last >= target` → target fill. Aynı barda ikisi de tetiklenmişse **stop önceliklidir** (konservatif varsayım).
- `get_account_state` gerçek zamanlı equity hesaplar (nakit + pozisyon × son fiyat).
- BIST seans kontrolü `core/clock.py`'den: seans dışında emir kabul edilmez (`MARKET_CLOSED`).

Test (tests/test_paper_broker.py): deterministik fiyat dizisi beslenir; fill fiyatları, komisyon, stop-önceliği, restart-sonrası state kurtarma doğrulanır.

---

# BÖLÜM 11 — ALGOLAB ADAPTER (execution/algolab/)

> **Doğruluk notu:** Aşağıdaki akış, AlgoLab'ın topluluk tarafından iyi bilinen API davranışına dayanır. Faz 5'in İLK işi, bu bölümdeki her endpoint adını/alanını resmi dokümantasyonla (https://www.algolab.com.tr/api — kullanıcı hesabıyla erişilir; gerekirse kullanıcıdan doküman PDF'ini istemek meşrudur) karşılaştırıp uyuşmazlıkları düzeltmektir. Uyuşmazlık bulursan bu dosyanın 11. bölümüne düzeltme notu ekle.

## 11.1 Operasyonel gerçek: SMS'li login

AlgoLab login akışı SMS doğrulaması içerir → **bot tam başlatma insan etkileşimi gerektirir.** Mimari çözüm:
- `python -m execution.algolab.auth login` — interaktif CLI: kullanıcı adı/şifre `secrets.env`'den, SMS kodunu kullanıcı terminale girer; dönen session hash `runtime/algolab_session.json`'a yazılır (dosya izni 600).
- `main.py` bu session'ı okur; periyodik `SessionRefresh` çağrısıyla canlı tutar. Session geçersizleşirse (`401` benzeri): bot **pozisyon açmayı durdurur**, Telegram'a CRITICAL "yeniden login gerekli" bildirir, mevcut bracket emirler broker tarafında zaten korumada olduğu için pozisyonlar korumasız kalmaz — bu, bracket emirlerin neden bot hafızasında değil broker'da durması gerektiğinin tam kanıtıdır.

## 11.2 Auth referans implementasyonu (auth.py)

```python
# execution/algolab/auth.py — referans; Faz 5'te resmi dokümanla doğrula
import base64, hashlib, json, requests
from Crypto.Cipher import AES               # pycryptodome
from Crypto.Util.Padding import pad

BASE = "https://www.algolab.com.tr/api"

class AlgoLabAuth:
    def __init__(self, api_key: str, username: str, password: str):
        self.api_key = api_key                      # "API-XXXX" formatında
        self.api_code = api_key.split("API-")[-1]
        self.username, self.password = username, password
        self.token = None      # SMS aşaması ara token'ı
        self.hash = None       # oturum hash'i (Authorization header)

    def _encrypt(self, text: str) -> str:
        iv = b"\0" * 16
        key = base64.b64decode(self.api_code.encode())
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(pad(text.encode(), 16))).decode()

    def _checker(self, endpoint: str, payload: dict | None) -> str:
        body = json.dumps(payload).replace(" ", "") if payload else ""
        return hashlib.sha256((self.api_key + endpoint + body).encode()).hexdigest()

    def login_user(self) -> None:
        """Adım 1: kimlik gönder → SMS tetiklenir, ara token döner."""
        payload = {"Username": self._encrypt(self.username),
                   "Password": self._encrypt(self.password)}
        r = self._post("/api/LoginUser", payload, authorized=False)
        self.token = r["content"]["token"]

    def login_user_control(self, sms_code: str) -> None:
        """Adım 2: SMS kodu → kalıcı oturum hash'i."""
        payload = {"token": self._encrypt(self.token),
                   "Password": self._encrypt(sms_code)}
        r = self._post("/api/LoginUserControl", payload, authorized=False)
        self.hash = r["content"]["hash"]

    def session_refresh(self) -> bool:
        r = self._post("/api/SessionRefresh", {}, authorized=True)
        return bool(r.get("success"))

    def _post(self, endpoint: str, payload: dict, authorized: bool) -> dict:
        headers = {"APIKEY": self.api_key,
                   "Checker": self._checker(endpoint, payload),
                   "Content-Type": "application/json"}
        if authorized:
            headers["Authorization"] = self.hash
        resp = requests.post(BASE + endpoint.removeprefix("/api"), json=payload,
                             headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success", False):
            raise BrokerError(f"AlgoLab {endpoint}: {data.get('message')}")
        return data
```

## 11.3 Throttle'lı istemci (client.py)

AlgoLab'ın bilinen kısıtı: **~5 saniyede 1 istek.** Tüm çağrılar tek bir `RateLimitedClient` üzerinden geçer: `threading.Lock` + son istek zamanı; gerekirse `time.sleep`. `429`/limit hatasında üstel geri çekilme (5→10→20 sn, 3 deneme), sonra `BrokerError`. Bu kısıt mimariyi etkiler: canlı döngü sembol başına bar çekerken istekleri sıralar — 3-4 enstrüman × 2 timeframe ≈ 8 istek ≈ 40 sn; `bar_close_grace_sec` bunu tolere eder.

## 11.4 Adapter (adapter.py) — endpoint eşlemesi

| BrokerAdapter metodu | AlgoLab endpoint (doğrulanacak) | Not |
|---|---|---|
| get_bars | `GetCandleData` | period paramı dakika cinsinden (günlük=1440). Tarihsel derinlik sınırlı olabilir — canlıda sorun değil (son ~300 bar yeter), backtest zaten yfinance kullanıyor |
| get_last_price | `GetEquityInfo` | |
| get_account_state | `InstantPosition` / `CashFlow` | alan adlarını dokümandan doğrula |
| submit_bracket_order | `SendOrder` | AlgoLab zincir emri destekliyor; desteklemeyen durumda: piyasa emri fill olduktan sonra ayrı stop-satış + limit-satış emirleri gönder, `broker_order_ids`'e üçünü de yaz |
| get_positions / get_open_orders | `InstantPosition` / `TodaysTransaction` | |
| cancel_all_orders | `DeleteOrder` | |

WebSocket (canlı tick) MVP'de zorunlu değil — bar-kapanışı döngüsü REST ile yeterli. WebSocket'i Faz 6+ iyileştirmesi olarak bırak.

---

# BÖLÜM 12 — BACKTEST MOTORU (backtest/)

## 12.1 Neden hazır kütüphane değil, kendi motorumuz

MTF (günlük+4H) huni, bracket emir simülasyonu ve "sinyal kodu canlıyla bire bir aynı" şartı hazır kütüphanelerde (backtesting.py, vectorbt) eğip bükmeyi gerektirir. Event-driven, bar-bazlı, ~200 satırlık kendi motorumuz hem daha sadık hem test edilebilir.

## 12.2 Motor döngüsü (engine.py)

```
her sembol için features hazırla (build_features — canlıyla aynı fonksiyon)
t = warm-up sonundan son bara kadar:
    1. Açık pozisyonların stop/target'ını t barının high/low'una karşı kontrol et:
       low <= stop → stop fill (fiyat: stop - slippage); aynı barda ikisi de → STOP ÖNCELİKLİ
       high >= target → target fill (fiyat: target - slippage yok, limit emir varsayımı; komisyon var)
    2. Açık pozisyonlar için evaluate_exit(t) → EXIT_LONG ise t+1 açılışında çık
    3. Pozisyonsuz semboller için evaluate_entry(t) → ENTER_LONG ise risk motoru → onaylıysa
       t+1 barının AÇILIŞINDA gir (fiyat: open × (1 + slippage_bps/1e4)), komisyon düş
    4. Equity snapshot kaydet
çıktı: trades listesi, equity serisi, günlük karar logu
```

## 12.3 Mutlak kural: look-ahead yasağı

**Sinyal, t barının kapanış verisiyle hesaplanır; işlem en erken t+1 barının açılışında gerçekleşir.** `iloc[-1]`'in "son KAPANMIŞ bar" olması, indikatörlerin gelecek veri içermemesi (fraktal swing'in son n barda tanımsız olması gibi) bu kuralın parçasıdır. Test: `test_backtest_engine.py` içinde "sinyal barının kapanışıyla aynı barda fill yok" asserti + sentetik 'yarının haberini bilen' seri ile motorun bunu kullanamadığının kanıtı.

## 12.4 Metrikler (metrics.py)

`total_return, cagr, max_drawdown, sharpe (günlük, rf=0, √252), win_rate, profit_factor, avg_r_multiple, expectancy, trade_count, time_in_cash_pct, per_regime kırılım`.

Rejim sınıflandırması (sembol bazında, günlük): `bull` = close > ema200 ve ema200 20 bar öncesinden yüksek; `bear` = close < ema200 ve ema200 düşüyor; aksi `sideways`. Rapor: her rejimde trade sayısı, win rate, toplam R.

## 12.5 Walk-forward (walkforward.py)

Config'ten `train/test/step`. Her pencerede: train diliminde küçük grid taraması (Bölüm 12.7'deki sınırlı grid) → en iyi parametreyi **komşu-sağlamlık** kriteriyle seç (en yüksek skor değil; skoru komşu parametre değerlerinde de çökmeyen) → test diliminde o parametreyle koş. Çıktı: pencere pencere OOS sonuçları + hepsinin birleşik equity'si. **Kabul kriteri raporda net yazılır:** birleşik OOS profit factor > 1.1 ve OOS max DD, in-sample max DD'nin 1.5 katından kötü değil — değilse `BACKTEST_REVIEW.md` bunu kırmızı bayrak olarak işaretler.

## 12.6 Monte Carlo (montecarlo.py)

```python
import numpy as np
def monte_carlo_dd(trade_returns: np.ndarray, runs: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    dds = np.empty(runs)
    for i in range(runs):
        eq = (1 + rng.permutation(trade_returns)).cumprod()
        dds[i] = (eq / np.maximum.accumulate(eq) - 1.0).min()
    p5, p50, p95 = np.percentile(dds, [5, 50, 95])
    return {"dd_p5": p5, "dd_median": p50, "dd_p95": p95}
```

Yorum kuralı: `dd_p5` (en kötü %5 senaryo — permütasyonların %5'i bundan daha derin bir drawdown gösteriyor) config'teki `max_drawdown_breaker_pct`'e yakın/aşkınsa, breaker canlıda sık tetiklenecek demektir → rapora kırmızı bayrak.

## 12.7 Parametre taraması — overfitting'e karşı bilinçli dar grid

Yalnızca şu üçü taranır: `atr_stop_mult ∈ {1.25, 1.5, 2.0}`, `adx_min ∈ {15, 20, 25}`, `min_rr ∈ {1.5, 1.8, 2.2}` (27 kombinasyon). Daha geniş grid YASAK — her eklenen boyut, geçmişe ezber riskini üstel artırır. RSI bandı, EMA periyotları vb. sabit kalır.

## 12.8 CLI (cli.py)

```bash
python -m backtest.cli --symbols THYAO,GARAN,ASELS --config config/config.yaml \
    --walk-forward --monte-carlo --regime-split --sweep --out runtime/backtest_reports/
```
Çıktılar: `report.md` (tüm metrikler + kırmızı bayrak bölümü), `equity.png` (matplotlib), `trades.csv`, `sweep_results.csv`. `--seed` config'den; aynı komut iki kez koşulduğunda **bit-bit aynı** sonuç üretmeli (tutarlılık şartı — test edilir). Aynı-gün çoklu giriş VE çıkış sırası alfabetik-deterministiktir (5227438 + ablasyon kapanış turu).

---

# BÖLÜM 13 — OPERASYONEL GÜVENLİK KATMANI

## 13.1 Emir-öncesi kontroller (safety/pretrade.py)

Her onaylı TradeDecision, emre dönüşmeden şu zincirden geçer (biri bile FAIL → emir yok, journal'a `PRETRADE_CHECK_FAILED` + detay):
1. Piyasa açık mı (`clock.is_bist_session()` — açılış müzayedesi ~09:40-09:55 ve kapanış ~18:00-18:10 pencerelerinde İŞLEM YOK; saatleri `core/clock.py`'de sabitleyip kaynak yorumu düş, Faz 5'te güncel seans saatlerini doğrula).
2. Fiyat makul mü: `abs(last/prev_close - 1) <= max_price_jump_pct` (bozuk/stale veri koruması).
3. Session sağlıklı mı (AlgoLab modunda: son SessionRefresh başarılı mı).
4. `quantity × price` nakitten büyük değil mi (son kontrol; risk motoru zaten baktı ama fiyat değişmiş olabilir).
5. Kill switch / breaker dosyaları yok mu.
6. `news_blackout` (MVP implementasyonu pragmatik: config'e elle girilen `blackout_dates` listesi — kullanıcı bilanço tarihlerini girer; otomatik KAP entegrasyonu Faz 6+).

## 13.2 Mutabakat (safety/reconciliation.py)

Her `reconciliation_interval_min`'de: `broker.get_positions()` ↔ journal'daki açık pozisyonlar karşılaştırılır (sembol, miktar). Uyuşmazlıkta: yeni girişler durdurulur (`runtime/RECON_MISMATCH` dosyası), Telegram CRITICAL, `events`'e detay. Bot uyuşmazlığı kendisi "düzeltmeye" çalışmaz — insan kararı.

## 13.3 Heartbeat + Watchdog (safety/watchdog.py)

`main.py` her `heartbeat_interval_sec`'te `runtime/heartbeat` dosyasına UTC timestamp yazar. `watchdog.py` AYRI bir süreçtir (ayrı launchd servisi): dosya yaşı > `heartbeat_stale_sec` ise Telegram'a CRITICAL "bot sessiz — pozisyonlar broker bracket'larıyla korunuyor, kontrol et" gönderir. Watchdog'un tek bağımlılığı Telegram token'ıdır — bot çökse bile o ayakta kalır.

## 13.4 Telegram (notify/telegram_bot.py)

Bildirimler: her fill, her reddedilen giriş (özet), günlük kapanış özeti (equity, günün P&L'i, açık pozisyonlar), tüm CRITICAL'lar. Komutlar: `/status` (equity+pozisyonlar), `/pause` (kill switch dosyası oluştur), `/resume` (sil), `/kill` (pause + tüm açık pozisyonları kapat — çift onay ister: `/kill CONFIRM`), `/report` (son 7 gün özeti). Komut handler'ları yalnızca `TELEGRAM_CHAT_ID`'den gelen mesajları kabul eder.

## 13.5 Ana döngü (main.py)

```
başlangıç: config yükle+doğrula → journal aç → broker connect →
           reconciliation (açılışta zorunlu) → Telegram "bot başladı"
scheduler (basit while+sleep yeterli, cron değil):
    her günlük bar kapanışı + grace: tam sinyal turu (Bölüm 3.3 akışı)
    her 4h bar kapanışı + grace: yalnızca tetik-bekleyen semboller için giriş turu
    her 5 dk: heartbeat + bekleyen paper stop/target kontrolü
    her 15 dk: reconciliation
    her 60 dk: SessionRefresh (algolab modunda)
kapanış sinyali (SIGTERM): açık emir iptali YOK (bracket'lar broker'da kalmalı),
    journal flush, Telegram "bot durdu".
```

Hata felsefesi: tek sembolün hatası turu düşürmez (try/except sembol bazında, `events`'e ERROR); auth/DB gibi sistemik hata → güvenli duruş (yeni işlem yok) + CRITICAL bildirim; **asla sessiz çökme yok.**

---

# BÖLÜM 14 — FAZ PLANI VE "BİTTİ" TANIMLARI

> Fazlar gün değil, iş birimi. Otonom koştuğun için hızlı bitebilirler — "Bitti Tanımı"ndaki her madde ÇALIŞTIRILARAK doğrulanmadan faz kapanmaz.

**FAZ 1 — İskelet + Veri Katmanı**
Yapılacak: repo yapısı, venv, requirements, config sistemi (+doğrulama), `core/` tamamı, `data/` tamamı, fixtures, `.gitignore`, `secrets.env.example`.
Bitti: `pytest -q` yeşil; `python -m data.historical --symbols THYAO,GARAN,ASELS` cache'i dolduruyor; quality kontrolleri fixture'daki bozuk-veri senaryolarını yakalıyor; config'e geçersiz değer verilince başlatma açıkça reddediliyor.

**FAZ 2 — İndikatörler + Sinyal Motoru**
Yapılacak: `indicators/engine.py` (10 bileşen), `strategy/signal_engine.py` (huni + exit), golden testler, degrade mod.
Bitti: testler yeşil; `python -m strategy.signal_engine --symbol THYAO --date 2024-06-03` gibi bir debug komutu o günün tüm gate kararlarını insan-okur formatta basıyor; 2 yıllık veri üzerinde sinyal taraması NaN/exception olmadan koşuyor.

**FAZ 3 — Risk Motoru**
Yapılacak: `risk/risk_engine.py`, korelasyon hesabı, breaker/kill-switch dosya mekanikleri.
Bitti: Bölüm 9.3'teki sayısal testler dahil tüm testler yeşil; her RejectReason en az bir testte üretiliyor.

**FAZ 4 — Backtest Harness**
Yapılacak: `backtest/` tamamı, CLI, rapor üretimi, determinizm.
Bitti: CLI tek komutla tam rapor üretiyor; aynı komut iki koşuda bit-bit aynı çıktı veriyor; look-ahead testleri yeşil; sweep 27 kombinasyonu bitiriyor.
**→ DURMA NOKTASI 1: `BACKTEST_REVIEW.md` üret, dur (Bölüm 0.1 + Bölüm 15).**

**FAZ 5 — Yürütme + Güvenlik + Paper Deploy** *(kullanıcı onayından sonra)*
Yapılacak: `paper_broker.py`, `algolab/` (resmi dokümanla doğrulama dahil), `safety/` tamamı, Telegram, `main.py`, launchd plist'leri (bot + watchdog), `README.md` (kurulum+işletme kılavuzu: login akışı, komutlar, dosya bayrakları).
Bitti: paper modda bot Mac Mini'de bir tam seans boyunca kesintisiz koşuyor; Telegram komutları çalışıyor; watchdog, bot bilerek durdurulduğunda alarm veriyor; reconciliation uyuşmazlık senaryosu testte üretilip yakalanıyor.

**FAZ 6 — Paper Doğrulama Penceresi** *(takvim işi, kod işi değil)*
Minimum 2 hafta paper koşusu. Bu sürede kod değişikliği yalnızca bug-fix (davranış değiştiren her şey önce backtest'ten geçer — Bölüm 0.2). Pencere sonunda `PAPER_REVIEW.md`: paper sonuçları ↔ backtest beklentisi karşılaştırması.
**→ DURMA NOKTASI 2 kalıcı olarak yürürlükte: gerçek moda geçiş her zaman kullanıcının elle eylemi.**

---

# BÖLÜM 15 — BACKTEST_REVIEW.md ŞABLONU (Durma Noktası 1 çıktısı)

```markdown
# Backtest Değerlendirme Raporu
Tarih / commit: ...
## Seçilen parametre seti ve gerekçe (komşu-sağlamlık kanıtıyla)
## Özet metrikler (tüm dönem): return, CAGR, maxDD, Sharpe, win rate, PF, avg R, trade sayısı, nakitte kalma %
## Rejim kırılımı: bull/bear/sideways ayrı tablo
## Walk-forward: pencere pencere OOS tablosu + birleşik OOS metrikleri + kabul kriteri sonucu
## Monte Carlo: dd_p5 / median / dd_p95 + breaker eşiğiyle karşılaştırma
## KIRMIZI BAYRAKLAR (dürüstçe, varsa):
- [ ] Performans tek rejime/tek yıla mı yoğun?
- [ ] Seçilen parametrenin komşuları çöküyor mu (overfitting işareti)?
- [ ] OOS, in-sample'dan belirgin kötü mü?
- [ ] MC dd_p95, breaker eşiğine yakın/aşkın mı?
- [ ] Trade sayısı istatistiksel anlam için çok mu az (<30)?
- [ ] 4H degrade dönem sonuçları tam-veri dönemden anlamlı sapıyor mu?
## Benim (Claude Code) değerlendirmem: <dürüst özet — ama karar kullanıcının>
```

---

# BÖLÜM 16 — BİLİNEN BELİRSİZLİKLER VE ÇÖZÜM PROTOKOLÜ

| # | Belirsizlik | Ne zaman çözülür | Protokol |
|---|---|---|---|
| 1 | AlgoLab endpoint/alan adlarının birebir doğruluğu | Faz 5 başı | Resmi dokümanla karşılaştır; erişemiyorsan kullanıcıdan doküman iste; Bölüm 11'e düzeltme notu ekle |
| 2 | Altın enstrümanının AlgoLab sembol kodu + sözleşme mekaniği (teminat, vade) | Faz 5 | Sembol listesi endpoint'inden doğrula; netleşene dek altın yalnızca backtest proxy'sinde kalır, paper/real'e eklenmez |
| 3 | AlgoLab demo ortamının API'den erişilebilirliği | Faz 5 | Erişilemiyorsa sorun değil: PaperBroker zaten bağımsız (Bölüm 10) |
| 4 | Deniz Yatırım gerçek komisyon oranı | Faz 5 | Kullanıcıdan iste; gelene dek 10 bps konservatif varsayım |
| 5 | BIST güncel seans/müzayede saatleri | Faz 5 | Doğrula, `core/clock.py`'ye kaynak yorumuyla işle |
| 6 | Session/SMS yenileme sıklığı (günlük mü?) | Faz 5, ilk canlı gün | Gözle, README'ye işletme notu yaz |

Genel kural: spec'te cevabı olmayan **teknik** kararlarda konservatif seçimi yap, `STATUS.md`'ye yaz, ilerle. **Risk parametresi veya gerçek parayla ilgili** belirsizlikte: varsayma, dur, sor.

---

# BÖLÜM 17 — GENİŞLETME REHBERİ (gelecek özellikler için)

**Yeni indikatör eklemek:** 1) `indicators/engine.py`'ye `add_x()` saf fonksiyonu yaz, `FEATURE_PIPELINE`'a ekle. 2) Golden test ekle. 3) Kullanılacaksa yeni gate yaz, `ENTRY_GATES`'e sırasına göre ekle (ucuz/eleyici kontroller öne). 4) Parametrelerini config'e ekle. 5) Backtest'ten geçmeden paper'a inmez (Bölüm 0.2).

**Yeni enstrüman:** config `instruments`'a blok ekle (AlgoLab sembolü + yf sembolü). Kod değişikliği gerekmez — gerekiyorsa mimari ihlali var demektir, düzelt.

**Yeni broker (örn. MT5/forex):** `execution/mt5/` altında `BrokerAdapter`'ı implemente et; çekirdeğe dokunma. Config'e `broker: algolab|mt5` seçici ekle. Forex'in seans/lot/pip farklılıkları adapter içinde soğurulur.

**Yeni strateji varyantı:** `ENTRY_GATES` listesini config'ten seçilebilir yapmak (gate registry + isim listesi) — Faz 6+ için doğal ilk refactor; şimdilik YAGNI.

---

# BÖLÜM 18 — requirements.txt (başlangıç seti)

```
pandas==2.2.*
numpy==1.26.*
pandas-ta==0.3.14b0
yfinance==0.2.*
requests==2.32.*
pycryptodome==3.20.*
python-dotenv==1.0.*
PyYAML==6.0.*
python-telegram-bot==21.*
matplotlib==3.9.*
pyarrow==16.*
pytest==8.*
```

Sürüm çakışması çıkarsa çöz, sabitle, commit mesajında belirt. `pandas-ta`'nın numpy 2.x uyumsuzluğu bilinen bir konudur — numpy 1.26'da kal; yükseltme ancak testler yeşilken bilinçli yapılır.

---

*Bu dokümanın sonu. İlk oturum: Faz 1'den başla.*

# EXPANSION.md — Çok Piyasalı Genişleme Spec'i (v2: ABD Hisseleri + Forex)

> **Bu dosya nedir:** CLAUDE.md'nin çok-piyasa genişlemesi için mühendislik spec'i ve yürütme planıdır. CLAUDE.md'deki tüm kurallar (Bölüm 0 dahil) aynen geçerlidir; bu dosya onları GENİŞLETİR, gevşetmez. Çelişki durumunda CLAUDE.md Bölüm 0 + kullanıcı kararı kazanır. HARDENING.md Bölüm B, Faz 5/E5 uygulamasında bağlayıcı olmaya devam eder.
>
> **İlk oturum talimatı:** Önce `STATUS.md` oku. Bu dosyanın E-fazları (Bölüm 16) kullanıcı onay kapılarıyla ayrılmıştır: "E1 onaylandı", "E2 onaylandı" (vb.) mesajı gelmeden o faza BAŞLAMA. Spec'te cevabı olmayan noktalarda Bölüm 17'deki belirsizlik protokolünü uygula — kullanıcıya sormadan önce bu dokümanın cevabı içerip içermediğini kontrol et.
>
> **Sürüm notu:** v2, v1'in stratejik içeriğini (gerekçeler) korur ve CLAUDE.md seviyesinde mühendislik sözleşmeleri ekler. v1 repoya hiç girmedi; bu dosya tek geçerli sürümdür.

---

# BÖLÜM 0 — PAZARLIK KONUSU OLMAYAN KURALLAR (CLAUDE.md Bölüm 0'a ek)

## 0.1 Durma noktaları her piyasa için ayrı ayrı geçerlidir
- Hiçbir sleeve, KENDİ backtest kabul kriterlerini (CLAUDE.md Bölüm 12.5 — aynen) geçmeden ve kullanıcı onayı almadan paper'a alınamaz; HARDENING B7 paper kriterlerini geçmeden ve kullanıcı onayı almadan real'e alınamaz.
- Her sleeve'in `mode: paper` alanı yalnızca kullanıcı tarafından elle değiştirilebilir (Durma Noktası 2, sleeve başına).
- "BIST altyapısı hazır" hiçbir sleeve'e kısayol vermez. **Paper ≠ strateji doğrulaması:** Faz 6'da üç sleeve'in birlikte paper koşması altyapıyı (emir akışı, mutabakat, takvim, parite) test eder; strateji hükmü yalnızca o sleeve'in kendi walk-forward'ından çıkar.

## 0.2 BIST Regresyon Çapası (E2+'nın mutlak kuralı)
`tests/golden/bist_v7_trades.csv` — repoya sabitlenecek golden dosya E2'nin ilk işidir, ama kaynağı **`runtime/backtest_reports_v7_1/trades.csv` (`backtest-v7.1-golden` git tag'i, SHA256: bkz. `runtime/backtest_reports_v7_1/MANIFEST.json`)** olacaktır — **v7'nin kendisi DEĞİL**. E2 ve sonrasındaki HER commit'te şu test yeşil kalmak zorundadır: BIST profili + v7 snapshot'ı + v7 config'i ile koşulan backtest, golden dosyayla **bayt-bayt aynı** trades.csv üretir. Bu test kırmızıyken hiçbir E-işi commitlenmez. Golden dosya yalnızca kullanıcı onaylı bir "taban çizgisi güncelleme" turunda değişebilir (gerekçe commit mesajına yazılır).

**v7 → v7.1 notu (ablasyon kapanış turu, R1):** v7'nin dondurulmuş `trades.csv`'si, `backtest/engine.py`'de sonradan bulunup düzeltilen bir çapraz-süreç determinizm bug'ı (`pending_exits` set-iteration sırası, `PYTHONHASHSEED`'e bağımlıydı) nedeniyle, aynı-gün-çoklu-çıkış durumlarında ARBİTRER (rastgele hash tohumlu) bir sıraya sahipti. v7.1-golden, İÇERİK olarak v7 ile TAM AYNIDIR (aynı 121 trade, aynı PnL — bkz. ABLATION_PORTFOLIO.md) ama satır sırası artık deterministik (alfabetik) — bu yüzden E2+ regresyon kıyası bayt-bayt **v7.1-golden'a** yapılır (v7 tarihsel kayıt olarak kalır; 2 satırlık sıra farkının nedeni ABLATION_PORTFOLIO.md'de belgelidir).

## 0.3 Kesinlikle yapılmayacaklar (ek)
- Sleeve'ler arası otomatik sermaye transferi veya cross-margin kodu yazmak.
- Haber/olay verisini GİRİŞ sinyali olarak kullanmak (yalnızca veto — Bölüm 10).
- Bir piyasanın maliyet modeli (Bölüm 7) backtest'e entegre edilmeden o piyasada kabul koşusu yapmak.
- FX sleeve'ini, kullanıcı SPK/vergi durumunu teyit etmeden real'e taşımayı önermek bile.
- CLAUDE.md Bölüm 4 sözleşmelerinde alan silmek/yeniden adlandırmak (yalnızca EKLEME serbest).
- Çekirdek modüllerde `if market == "fx"` tarzı piyasa dallanması (Bölüm 3.2).

## 0.4 Sıralama kilidi
E1 (veri temeli) motora dokunmaz; BIST teşhis/yeniden-tasarım işleriyle paralel koşabilir. **E2 ve sonrası, v7 turu tamamlanıp BIST strateji yeniden-tasarım kararı verilmeden başlamaz** — hangi stratejinin hangi piyasada koşacağı o karardan çıkacak; gate profilleri (Bölüm 8) bu esnekliği taşımak için var.

---

# BÖLÜM 1 — HEDEF: SLEEVE MODELİ

Tek bot süreci, üç izole **sleeve**:

| Sleeve id | Enstrümanlar | Para birimi | Broker | Backtest verisi | Yön | Runtime |
|---|---|---|---|---|---|---|
| `bist` | 12 hisse (mevcut) | TRY | AlgoLab | mevcut hat (kaynak kararı v7 sonrası) | long_only | `runtime/` (mevcut yollar korunur) |
| `us` | 15-20 likit büyük hisse (E1 önerir) | USD | Bölüm 14 kararı | yfinance-US | long_only (başlangıç) | `runtime/us/` |
| `fx` | EURUSD, GBPUSD, USDJPY (+altın: Bölüm 17) | USD | Bölüm 14 kararı | OANDA v20 / yedek CSV | two_sided ZORUNLU | `runtime/fx/` |

Sleeve ilkeleri (gerekçeleriyle):
1. **Sabit sermaye tahsisi**, değişiklik yalnızca kullanıcı elle (`config/portfolio.yaml`). *Gerekçe: bir sleeve'in kaybı diğerinin risk bütçesini sessizce büyütemesin.*
2. **Cross-margin yok.** *Gerekçe: bulaşma riskini mimari olarak imkânsız kılmak.*
3. Her sleeve **kendi para biriminde** muhasebe tutar; birleşik raporlama TRY'ye çevrilir (günlük USDTRY, YALNIZCA raporlama). *Gerekçe: kur oynaklığı risk kararlarına gürültü sokmasın.*
4. Sleeve state izolasyonu: kendi journal, BREAKER_TRIPPED, paper_state dosyaları. Bir sleeve'in donması diğerini durdurmaz; global `runtime/KILL_SWITCH` hepsini durdurur (mevcut semantik korunur).

**Sıralama gerekçesi — ABD önce, FX sonra:** ABD = düşük delta (günlük bar, long-only trend, gerçek hacim, temiz kurumsal-işlem verisi). FX = yüksek delta: short taraf motor işi; merkezî hacim yok (gate-ablasyonun değer kattığını gösterdiği volume gate'i FX'te çalışmaz — telafisi tasarım işi); swap maliyeti backtest'e girmek zorunda; kaldıraç/marjin muhasebesi; SPK düzenleme gerçeği (Bölüm 17). Eski "forex için VPS gerekir" notu MT5'e özgüydü — OANDA/IBKR REST ile Mac Mini'de VPS'siz çalışır; MT5 yolu MVP'den çıkarıldı.

---

# BÖLÜM 2 — ÇALIŞMA PROTOKOLÜ

CLAUDE.md Bölüm 2'nin tamamı (oturum akışı, STATUS.md şablonu, limit protokolü, token tasarrufu, ortam) aynen geçerli. Ekler:
- Her E-fazı sonunda STATUS.md'ye "EXPANSION EX bitti/durdu" satırı + DUR, kullanıcı onayı.
- E2+ boyunca her commit öncesi Bölüm 0.2 çapası (`pytest tests/test_golden_bist.py -q`); faz sonlarında tam süit.
- Yeni bağımlılık → Bölüm 18 + `requirements.txt` + `requirements.lock` birlikte güncellenir.

---

# BÖLÜM 3 — MİMARİ DEĞİŞİKLİKLER

## 3.1 Dizin yapısı (yalnızca EKLENEN/DEĞİŞEN — mevcut yapı CLAUDE.md 3.2)

```
trading-bot/
├── EXPANSION.md
├── config/
│   ├── portfolio.yaml              # YENİ: sleeve tahsisleri + global limitler (Bölüm 11.1)
│   └── markets/
│       ├── bist.yaml               # YENİ: mevcut config'in piyasa bölümünün davranış-nötr göçü (Bölüm 11.4)
│       ├── us_equities.yaml        # YENİ (Bölüm 11.2)
│       └── fx.yaml                 # YENİ (Bölüm 11.3)
├── core/
│   ├── markets.py                  # YENİ: MarketSpec + registry (Bölüm 4.2)
│   └── calendars.py                # YENİ: takvim sarmalayıcı (Bölüm 5); clock.py delege ederek KORUNUR
├── data/
│   ├── adapters/                   # YENİ: DataAdapter ABC + yf_us.py + oanda.py (Bölüm 6)
│   └── events.py                   # YENİ: earnings + ekonomik takvim vetoları (Bölüm 10)
├── costs/                          # YENİ: CostModel ABC + bist.py + us_equities.py + fx.py (Bölüm 7)
├── strategy/
│   └── gate_registry.py            # YENİ: isim→gate registry + profil kurulumu (Bölüm 8)
├── execution/
│   └── ibkr/ | alpaca/ + oanda/    # E3 kararına göre (Bölüm 14)
├── tests/golden/bist_v7_trades.csv # YENİ: regresyon çapası (Bölüm 0.2)
└── runtime/{us,fx}/                # YENİ sleeve dizinleri
```

## 3.2 Veri akışı — çok-piyasa hali

CLAUDE.md 3.3 zinciri sleeve başına aynen korunur; scheduler piyasa-farkındalıklı olur (Bölüm 13). Sinyal ve risk kodu tüm sleeve'lerde AYNI fonksiyonlardır; piyasa farkları yalnızca üç yerde soğurulur: `MarketSpec` (metadata), `CostModel` (maliyet), gate profili (hangi gate, hangi eşik). Bu üçü dışında çekirdekte piyasa dallanması yasaktır — ihtiyaç doğuyorsa mimari ihlal vardır: dur, tasarımı düzelt, STATUS.md'ye yaz.

---

# BÖLÜM 4 — ÇEKİRDEK SÖZLEŞME GENİŞLETMELERİ (core/models.py + core/markets.py)

CLAUDE.md Bölüm 4 kuralı geçerli: alan EKLENİR, silinmez/yeniden adlandırılmaz. Tüm yeni alanlar varsayılanlıdır (geriye uyum).

## 4.1 models.py ekleri

```python
class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class SignalAction(str, Enum):          # mevcut 4 üyeye EK:
    ENTER_SHORT = "ENTER_SHORT"
    EXIT_SHORT = "EXIT_SHORT"

class RejectReason(str, Enum):          # mevcut üyelere EK:
    PDT_LIMIT = "PDT_LIMIT"                     # ABD pattern-day-trader koruması (Bölüm 9.4)
    MARGIN_INSUFFICIENT = "MARGIN_INSUFFICIENT" # FX marjin yetersiz
    CALENDAR_BLACKOUT = "CALENDAR_BLACKOUT"     # deterministik takvim vetosu (earnings/ekonomik).
                                                # NEWS_BLACKOUT ayrı kalır: elle liste / (Faz 7) LLM vetosu.
    SETTLEMENT_CASH_UNAVAILABLE = "SETTLEMENT_CASH_UNAVAILABLE"  # T+1/T+2 nakdi henüz kullanılamaz

@dataclass(frozen=True)
class Signal:                            # EK alan:
    direction: Direction = Direction.LONG

@dataclass
class Position:                          # EK alanlar:
    direction: Direction = Direction.LONG
    market: str = "bist"

@dataclass(frozen=True)
class TradeDecision:                     # EK alanlar:
    risk_amount_ccy: float = 0.0         # sleeve para biriminde risk
    currency: str = "TRY"
    # risk_amount_try geriye uyum için kalır: bist'te ikisi eşit doldurulur,
    # diğer sleeve'lerde 0 bırakılır; raporlar risk_amount_ccy kullanır.

@dataclass
class AccountState:                      # EK alanlar:
    currency: str = "TRY"
    margin_used: float = 0.0             # FX; hisselerde 0
    settled_cash: float = -1.0           # -1 = "cash ile aynı" (BIST mevcut davranış);
                                         # ABD nakit-hesap modunda T+1 muhasebesi doldurur
```

## 4.2 MarketSpec (core/markets.py)

```python
@dataclass(frozen=True)
class MarketSpec:
    market_id: str                  # "bist" | "us" | "fx"
    calendar_id: str                # "XIST" | "XNYS" | "FX_24_5"
    currency: str
    direction_mode: str             # "long_only" | "two_sided"
    settlement_days: int            # BIST=2, US=1, FX=0
    qty_step: float                 # hisse=1; FX=1 unit (broker min'i E3'te doğrulanır)
    price_decimals: int
    cost_model_id: str              # costs/ registry anahtarı
    gate_profile_id: str            # config/markets/<id>.yaml profili
    data_adapter_id: str
    eval_after_close_min: int = 10
    pip_size: Optional[float] = None        # FX; enstrüman bazında config override
    max_leverage: Optional[float] = None    # FX; muhafazakâr varsayılan 5.0 (SPK senaryosu üst sınır 10.0)

MARKET_REGISTRY: dict[str, MarketSpec] = {}  # config yükleyici doldurur (Bölüm 11)
```

Kural: çekirdek, piyasa özelliğine yalnızca `MarketSpec` üzerinden erişir. Alan eklemeye açık; mevcut alan anlamı değiştirilemez.

---

# BÖLÜM 5 — TAKVİM MODÜLÜ (core/calendars.py)

Kütüphane: `exchange_calendars` (XIST, XNYS). FX için kütüphanesiz özel takvim `FX_24_5`: işlem günü kapanışı 17:00 America/New_York; Cumartesi kapalı; haftanın ilk günlük barı Pazartesi 17:00 NY kapanışı.

```python
class MarketCalendar:
    def is_trading_day(self, d: date) -> bool: ...
    def close_dt_utc(self, d: date) -> datetime: ...        # o günün bar kapanış anı (UTC)
    def next_eval_dt_utc(self, after: datetime) -> datetime # scheduler girdisi
    def trading_dates(self, start: date, end: date) -> list[date]: ...
```

**DST kuralları (mutlak):** Türkiye kalıcı UTC+3; ABD DST uygular — TR↔US farkı yılda iki kez değişir. Sabit saat farkı hard-code YASAK; tüm kapanış anları takvim + `zoneinfo` üzerinden hesaplanır. (Örnek, koda yorum olarak: NYSE 16:00 ET kapanışı = yazın 23:00, kışın 00:00 Europe/Istanbul; FX 17:00 NY kapanışı = yazın 00:00, kışın 01:00 Europe/Istanbul, ertesi gün.)

**BIST geriye uyumu:** `core/clock.py` API'si korunur, içi `MarketCalendar("XIST")`'e delege eder. XIST tatil bilgisi, v7 hayalet-bar filtresine ikinci doğrulama katmanı olarak `data/quality.py`'ye eklenir ("tarih takvimde işlem günü değilse bar şüpheli") — bu ekleme E2'de, regresyon çapası altında yapılır; v7 verisi temizse sonuç değişmez, değişirse golden güncellemesi kullanıcı onayına gider.

---

# BÖLÜM 6 — VERİ ADAPTER KATMANI (data/adapters/)

## 6.1 Kanonik OHLCV şeması (tüm adapter'ların çıktı sözleşmesi)
- Index: tz-aware DatetimeIndex; her barın etiketi ait olduğu GERÇEK piyasa-yerel işlem gününü gösterir (v7 tarih-normalizasyon kuralının genelleşmesi).
- Kolonlar: `open, high, low, close, volume` (float64). FX'te volume tick-volume ise `AdapterMeta.volume_kind="tick"`; hiç yoksa NaN.
- `AdapterMeta`: kaynak, indirme parametreleri, düzeltme politikası, kütüphane sürümü — snapshot manifest'ine yazılır.

## 6.2 ABC

```python
class DataAdapter(ABC):
    adapter_id: str
    @abstractmethod
    def fetch_history(self, symbol: str, timeframe: str,
                      start: date, end: date) -> tuple[pd.DataFrame, "AdapterMeta"]: ...
    @abstractmethod
    def fetch_latest(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame: ...
```

- `data/historical.py` (BIST) DOKUNULMAZ; E2'de ince `BistYfAdapter` sarmalayıcısıyla registry'ye bağlanır (davranış-nötr, çapa altında).
- `yf_us.py`: yfinance, `auto_adjust=True`. ABD'de kurumsal-işlem takibi güvenilirdir; yine de HARDENING A2 denetimi US verisine E1'de koşulur.
- `oanda.py`: v20 REST practice, D1 mumları (ücretsiz demo hesap gerekir). Hesap yoksa E1 yedek yolu: Dukascopy/histdata CSV → aynı kanonik şemaya dönüştürülür.
- **Snapshot entegrasyonu:** HARDENING A1 araçları piyasa-parametrik olur: `data/snapshots/<market>/<tarih>/` + manifest; `--snapshot` tüm piyasalarda aynı semantik. Kabul koşuları HER piyasada snapshot'tan koşulur.

---

# BÖLÜM 7 — MALİYET MODELLERİ (costs/)

## 7.1 ABC — motorun tek maliyet temas noktası

```python
class CostModel(ABC):
    model_id: str
    @abstractmethod
    def entry_costs(self, price: float, qty: float) -> float: ...
    @abstractmethod
    def exit_costs(self, price: float, qty: float) -> float: ...
    @abstractmethod
    def slippage_price(self, ref_price: float, side: Side) -> float: ...
    def daily_carry(self, pos: "Position", d: date) -> float:
        return 0.0   # varsayılan 0 — YALNIZCA fx override eder
```

**Motor entegrasyonu (E2):** `backtest/engine.py` ve `PaperBroker`, açık her pozisyon için her işlem günü `daily_carry` tahakkuk eder. BIST/US 0 döndürdüğünden BIST davranışı bit-bit aynı kalır (çapa kanıtlar).

## 7.2 Implementasyonlar
- `costs/bist.py`: mevcut komisyon+slippage mantığının taşınması; sayısal davranış birebir aynı (çapa testi).
- `costs/us_equities.py`: `commission_bps` (varsayılan 0), satışta `sec_fee_bps` + `taf_per_share` (güncel oranlar E3'te doğrulanır — Bölüm 17), `slippage_bps`.
- `costs/fx.py`: enstrüman bazında `spread_pips` (giriş ve çıkışta yarım spread), `slippage_pips`, **swap**: `swap_long_annual_pct` / `swap_short_annual_pct` (enstrüman bazında, config); `daily_carry = pozisyon_notional × (yıllık_oran/365)`; `triple_swap_wednesday: true` bayrağıyla Çarşamba 3× tahakkuk. Tarihsel swap serisi pratik olarak edinilemeyeceğinden oranlar MUHAFAZAKÂR sabitlerdir (pozisyon aleyhine) ve her FX backtest raporuna "swap: sabit muhafazakâr tahmin" notu ZORUNLU düşülür.

---

# BÖLÜM 8 — GATE PROFİLLERİ VE REGISTRY (strategy/gate_registry.py)

CLAUDE.md Bölüm 17'de "gate listesini config'ten seçilebilir yapmak — şimdilik YAGNI" denmişti. Çok-piyasa ile YAGNI bitti; bu refactor E2'nin parçasıdır.

```python
# strategy/gate_registry.py
GATE_REGISTRY: dict[str, Gate] = {
    "trend": gate_trend, "regime": gate_regime, "rsi": gate_rsi, "macd": gate_macd,
    "atr_anomaly": gate_atr_anomaly, "bb_overextension": gate_bb_overextension,
    "structure_rr": gate_structure_rr, "volume": gate_volume,
    "trigger_4h": gate_trigger_4h, "mtf": gate_mtf,
}

def build_entry_gates(profile: list[str]) -> list[Gate]:
    """config/markets/<id>.yaml -> gate_profile.entry listesinden huniyi kurar.
    Bilinmeyen isim = başlatma hatası (sessiz atlama YASAK)."""
```

Kurallar:
- `bist` profili = bugünkü `ENTRY_GATES` sırasının birebir isim listesi → çapa altında davranış-nötr göç.
- `fx` profilinde `volume` varsayılan olarak listede YOK (Bölüm 1 gerekçesi). Tick-volume tabanlı bir `volume_tick` gate'i ancak ayrı onaylı bir revizyon turunda eklenebilir.
- Short sinyal tanımı (hangi gate'lerin nasıl aynalanacağı) bu spec'in İÇİNDE DEĞİLDİR — BIST yeniden-tasarım kararından sonra, FX aktivasyonundan önce, kullanıcıyla ayrı bir tasarım turu olarak yazılır. E2 yalnızca motor YETENEĞİNİ (Direction) kurar; `direction_mode: two_sided` bir profil, short gate seti tanımlanana kadar backtest'te bile aktive edilmez.
- Exit mantığı (`evaluate_exit`) profil-farkındalıklı olur: long çıkışı mevcut kural; short çıkışı ayna kural (close > ema_50 VEYA macd_hist üç bardır yükseliyor ve macd > signal).

---

# BÖLÜM 9 — YÖN FARKINDALIĞI VE RİSK MOTORU GENİŞLEMESİ

## 9.1 Short mekanikleri (motor kuralları — FX aktivasyonunun ön şartı)
- Stop/hedef: SHORT için `stop = close + atr_stop_mult × atr` (fiyatın ÜSTÜNDE), hedef altta; `compute_target` ayna: `min(nearest_support, entry − 2×(stop−entry))`.
- R:R: `rr = (entry − target) / (stop − entry)` (SHORT); her iki yönde `per_unit_risk = abs(entry − stop) > 0` doğrulanır.
- Fill/stop-önceliği (PaperBroker + backtest): SHORT'ta `last >= stop` → stop fill (slippage aleyhte: stop'un ÜSTÜNDE dolar), `last <= target` → target fill; aynı barda ikisi de tetiklenmişse **stop önceliklidir** (mevcut konservatif kural, yön-simetrik).
- Equity/MTM: SHORT pozisyon değeri `qty × (2×entry − last)` DEĞİL — muhasebe net PnL üzerinden: `unrealized = qty × (entry − last)` (SHORT), `qty × (last − entry)` (LONG); equity = cash + Σ unrealized + Σ pozisyon teminatları (FX marjin modelinde cash zaten bloke marjin dahil tutulur; hisse short'u MVP kapsamı DIŞI — `us` long_only).

## 9.2 Boyutlama — genel formül (mevcut Bölüm 9.2'nin süperseti)
```
risk_amount = sleeve_equity × risk_per_trade_pct
per_unit_risk = abs(entry − stop)            # quote para biriminde
if quote_ccy != sleeve_ccy:                  # örn. USDJPY (quote=JPY, sleeve=USD)
    per_unit_risk = per_unit_risk / quote_to_sleeve_rate   # USDJPY için ÷ USDJPY kuru
qty = floor(risk_amount / per_unit_risk / qty_step) × qty_step
# hisse: mevcut notional + nakit kırpmaları aynen
# FX ek kırpma: qty ≤ (free_margin × max_leverage) / entry   → yetmezse MARGIN_INSUFFICIENT
```
Sayısal test örnekleri Bölüm 15.3'te.

## 9.3 Takas (settlement) nakdi
`AccountState.settled_cash` ≥ 0 ise boyutlamadaki nakit kırpması `cash` yerine `settled_cash` kullanır; yetmiyorsa `SETTLEMENT_CASH_UNAVAILABLE`. BIST'te alan -1 kalır (mevcut davranış değişmez); `us` nakit-hesap modunda PaperBroker satış nakdini T+1 sonrası `settled_cash`'e ekler (E3'te broker gerçek kuralıyla doğrulanır).

## 9.4 PDT koruması (yalnızca `us`, `account_type: margin` iken)
- Tanım: aynı ABD seansında aynı sembolde aç+kapa = 1 day-trade. Journal `orders` tablosundan son 5 iş günü penceresinde sayılır.
- Konservatif kural: `sleeve_equity < 25_000 USD` VE rolling day-trade sayısı ≥ 3 ise yeni ENTER reddedilir (`PDT_LIMIT`) — çünkü yeni pozisyonun aynı gün stop'lanması 4.'yü oluşturabilir. `account_type: cash` ise PDT devre dışı, 9.3 devrede.

## 9.5 Sleeve + global risk katmanı
- HARDENING B3 kill-switch hiyerarşisi HER sleeve'de bağımsız (kendi para biriminde, kendi `runtime/<sleeve>/BREAKER_TRIPPED` dosyasıyla).
- Global: (a) `global_max_open_positions` (tüm sleeve'ler toplamı); (b) birleşik TRY equity üzerinde `global_dd_alert_pct` (varsayılan 0.15) — YALNIZCA CRITICAL alarm, otomatik FREEZE değil (*gerekçe: USDTRY oynaklığı gerçek kayıp olmadan birleşik DD oynatabilir*); (c) `runtime/KILL_SWITCH` = tüm sleeve'lerde yeni ENTER yasak (mevcut semantik, global).
- Korelasyon limiti (mevcut) sleeve-İÇİ kalır; sleeve'ler-ARASI korelasyon MVP'de modellenmez (kabul edilen karşılığı: sabit tahsis + bağımsız breaker'lar). 

---

# BÖLÜM 10 — TAKVİM VETOLARI (data/events.py) — VETO, ASLA GİRİŞ SİNYALİ DEĞİL

Önceki karar aynen: haber/olay = yalnızca veto. Bu bölüm DETERMİNİSTİK (Tier 0) vetoları kurar; LLM haber vetosu (Tier 1) Faz 7 kararına tabidir ve bu spec'in kapsamı dışındadır.

## 10.1 Arayüz
```python
class EventCalendar:
    def is_blackout(self, market_id: str, symbol: str, d: date) -> tuple[bool, str]:
        """True ise reason string'i insan-okur: 'earnings 2026-07-24 (T-2)' gibi.
        Risk motoru True'da CALENDAR_BLACKOUT reject üretir. ÇIKIŞLAR HER ZAMAN SERBEST."""
```

## 10.2 Veri şemaları (parquet, snapshot disiplinine tabi)
- `data/events/earnings_<SEMBOL>.parquet`: kolonlar `announce_date, session(bmo|amc|unknown), source`.
- `data/events/econ_calendar.parquet`: kolonlar `ts_utc, event, impact(high|med|low), currencies(list)`.

## 10.3 Kurallar (config'ten, Bölüm 11)
- `us`: `announce_date ± earnings_blackout_days` (varsayılan: önce 3, sonra 1) yeni giriş yok; `hold_through_earnings: false` → açık pozisyon açıklamadan önceki gün kapatılır (EXIT her zaman serbest olduğundan veto ile çelişmez).
- `fx`: `impact == high` VE enstrümanın base/quote para birimi etkileniyorsa `ts ± econ_blackout_hours` (varsayılan 12) yeni giriş yok.
- `bist`: mevcut NEWS_BLACKOUT mekaniği değişmez.

## 10.4 Tarihsel derinlik gerçeği ve fallback protokolü
Earnings/ekonomik takvimin 2005'e kadar giden ücretsiz tarihçesi bulunamayabilir (yfinance earnings geçmişi sığdır). Protokol: E1'de kaynak adayları değerlendirilir (broker API, Nasdaq, FMP/AlphaVantage ücretsiz katmanları, ForexFactory arşivi); **tam tarihçe bulunamazsa** veto canlı/paper'da aktif olur, backtest vetosuz koşar ve rapora ZORUNLU sınırlama notu düşülür: "takvim vetosu backtest'te modellenemedi; canlıda ek koruma olarak devrededir (sonuçları iyileştirmesi beklenir, kötüleştirmesi değil — yine de fark paper'da izlenecek)". Kısmi tarihçe varsa yalnızca kapsanan dönem vetolu koşulur ve raporda dönem sınırı belirtilir.

---

# BÖLÜM 11 — CONFIG ŞEMALARI

## 11.1 config/portfolio.yaml (tam hali)
```yaml
base_reporting_currency: "TRY"        # yalnızca raporlama
fx_rate_source: "yfinance:USDTRY=X"   # günlük kapanış; raporlamada kullanılır
sleeves:
  bist:
    enabled: true
    mode: paper                        # Durma Noktası 2'ye tabi (sleeve başına)
    allocation: 100000                 # TRY
    market_config: "config/markets/bist.yaml"
  us:
    enabled: false                     # E4 kabulüne kadar false kalır
    mode: paper
    allocation: 3000                   # USD — kullanıcı Faz 6 öncesi gerçekçi değer girer
    market_config: "config/markets/us_equities.yaml"
  fx:
    enabled: false
    mode: paper
    allocation: 2000                   # USD
    market_config: "config/markets/fx.yaml"
global:
  global_max_open_positions: 5
  global_dd_alert_pct: 0.15            # yalnızca CRITICAL alarm (Bölüm 9.5 gerekçesi)
  kill_switch_file: "runtime/KILL_SWITCH"
```

## 11.2 config/markets/us_equities.yaml (tam hali)
```yaml
market:
  market_id: us
  calendar_id: XNYS
  currency: USD
  direction_mode: long_only
  settlement_days: 1
  account_type: cash                  # cash | margin (Bölüm 9.3/9.4; E3 karar maddesi)
  qty_step: 1
  price_decimals: 2
  cost_model_id: us_equities
  data_adapter_id: yf_us
  eval_after_close_min: 15
instruments: []                        # E1 çıktısıyla doldurulur: {symbol, yf_symbol, sector}
signal:                                # başlangıç = bist değerleri; E4 kalibrasyonu ayrı onaylı turlarla
  <bist signal bloğunun kopyası>
gate_profile:
  entry: [trend, regime, rsi, macd, atr_anomaly, bb_overextension,
          structure_rr, volume, trigger_4h, mtf]
risk:
  <bist risk bloğunun kopyası; para birimi USD yorumuyla>
costs:
  commission_bps: 0
  sec_fee_bps: 0.28                    # SATIŞTA; güncel oranı E3'te doğrula (Bölüm 17)
  taf_per_share: 0.000166              # SATIŞTA; tavanıyla birlikte E3'te doğrula
  slippage_bps: 5
vetoes:
  earnings_blackout: {enabled: true, days_before: 3, days_after: 1, hold_through: false}
backtest:
  start: "2005-01-01"
  benchmark: "SPY"                     # al-tut kıyası zorunlu satır (+"sadece nakit")
```

## 11.3 config/markets/fx.yaml (tam hali)
```yaml
market:
  market_id: fx
  calendar_id: FX_24_5
  currency: USD
  direction_mode: two_sided            # short gate seti tanımlanana dek fiilen long_only koşar (Bölüm 8)
  settlement_days: 0
  qty_step: 1
  price_decimals: 5
  cost_model_id: fx
  data_adapter_id: oanda
  max_leverage: 5.0                    # muhafazakâr; SPK senaryosu üst sınır 10.0
  eval_after_close_min: 10
instruments:
  - {symbol: EUR_USD, pip_size: 0.0001, spread_pips: 0.9,
     swap_long_annual_pct: -2.0, swap_short_annual_pct: -0.5}   # muhafazakâr placeholder; E1'de güncel değerlerle değiştir, kaynak yaz
  - {symbol: GBP_USD, pip_size: 0.0001, spread_pips: 1.2,
     swap_long_annual_pct: -2.0, swap_short_annual_pct: -1.0}
  - {symbol: USD_JPY, pip_size: 0.01,  spread_pips: 1.0,
     swap_long_annual_pct: 0.0,  swap_short_annual_pct: -4.0}
signal: {<bist bloğu baz; kalibrasyon E4'te>}
gate_profile:
  entry: [trend, regime, rsi, macd, atr_anomaly, bb_overextension,
          structure_rr, trigger_4h, mtf]        # volume YOK (Bölüm 8)
risk:
  {<bist bloğu baz> + margin kontrolleri Bölüm 9.2}
costs: {triple_swap_wednesday: true, slippage_pips: 0.3}
vetoes:
  econ_blackout: {enabled: true, impact: high, hours_before: 12, hours_after: 12}
backtest:
  start: "2010-01-01"                  # OANDA/yedek veri derinliğine göre E1'de kesinleşir
  benchmark: "cash_only"               # FX'te al-tut anlamsız; kıyas: sıfır-getiri + swap notu
```

## 11.4 BIST config göçü (E2, davranış-nötr)
Mevcut `config/config.yaml` KALIR ve çalışmaya devam eder; `config/markets/bist.yaml` ondan üretilir ve yükleyici iki kaynağın eşdeğerliğini başlatmada doğrular (fark = başlatma hatası). Tam geçiş (config.yaml'ın piyasa bölümlerinin emekliliği) ancak çapa testi yeşilken, ayrı bir commit'te yapılır.

---

# BÖLÜM 12 — JOURNAL VE RUNTIME DÜZENİ

- Her sleeve kendi journal'ını tutar: `runtime/journal.sqlite` (bist — mevcut yol KORUNUR), `runtime/us/journal.sqlite`, `runtime/fx/journal.sqlite`. Şema CLAUDE.md Bölüm 5 + her tabloya `market TEXT` kolonu (ALTER ile eklenir; bist'te değeri 'bist' yazılır — geriye uyumlu).
- `equity_snapshots`'a `currency TEXT` kolonu eklenir.
- Günlük EOD raporu (HARDENING B6) sleeve başına üretilir + birleşik TRY özeti tek Telegram mesajında.
- Watchdog tüm sleeve heartbeat'lerini izler (tek watchdog süreci; sleeve başına dosya: `runtime/<sleeve>/heartbeat`, bist mevcut `runtime/heartbeat`).

---

# BÖLÜM 13 — SCHEDULER (main.py genişlemesi)

```
başlangıç: portfolio.yaml + market config'leri yükle+doğrula → MARKET_REGISTRY kur →
           her enabled sleeve için: journal aç → broker connect → reconciliation → "sleeve hazır"
döngü (tek süreç, basit while+sleep):
    her sleeve için next_eval_dt_utc (Bölüm 5) hesapla; zamanı gelen sleeve'in tam sinyal turunu koş
    her 5 dk: sleeve heartbeat'leri + bekleyen paper stop/target kontrolleri (tüm sleeve'ler)
    her 15 dk: sleeve başına reconciliation
    her 60 dk: broker session bakımı (AlgoLab SessionRefresh; diğerleri E3'e göre)
hata felsefesi: sembol hatası turu, sleeve hatası SÜRECİ düşürmez (sleeve FREEZE + CRITICAL);
    asla sessiz çökme yok (CLAUDE.md 13.5 aynen).
```

Değerlendirme anları takvimden türetilir (Bölüm 5) — örnek niyet: BIST kapanış+grace (TRT akşamüstü), US kapanış+grace (TRT gece — DST'ye göre 23:15/00:15), FX günlük kapanış+grace (TRT gece yarısı sonrası). Mac Mini 7/24 açık olduğundan gece işleri sorun değildir; launchd plist'i değişmez (tek süreç).

---

# BÖLÜM 14 — BROKER ADAPTER'LARI: İKİ YOL VE KARAR PROTOKOLÜ (E3)

> **Doğruluk notu (CLAUDE.md Bölüm 11 kalıbıyla):** Aşağıdaki bilgiler genel API davranışına dayanır; E3'ün İLK işi seçilen yolun resmî dokümantasyonuyla doğrulamaktır. Uyuşmazlık bulunursa bu bölüme düzeltme notu eklenir.

## Yol A — IBKR (tek broker, iki piyasa)
- `execution/ibkr/adapter.py`, kütüphane: `ib_async` (ib_insync'in bakımdaki devamı). IB Gateway, Mac Mini'de 7/24 ayrı süreç (launchd); adapter localhost'a bağlanır.
- Artı: US + FX tek adapter/tek hesap; kurumsal sınıf paper ortamı; bracket emir native. Eksi: Gateway işletme yükü (otomatik yeniden başlatma, haftalık restart penceleri), API öğrenme eğrisi.
- Bracket: native (`parent + takeProfit + stopLoss`); `submit_bracket_order` sözleşmesi doğrudan karşılanır.

## Yol B — Alpaca (US) + OANDA (FX) (iki basit REST adapter)
- Artı: iki API de basit REST, paper ortamları anahtar ile anında; Gateway süreci yok. Eksi: iki adapter + iki hesap işletmek; Alpaca bracket native, OANDA'da stop/target pozisyona bağlı emirlerle (adapter soğurur — çağıran bilmez, CLAUDE.md 4.3 kuralı).
- OANDA throttle ve emir birimleri (units) adapter içinde soğurulur.

## Karar protokolü (E3 spike, ~yarım gün, kod-atılabilir)
Her iki yol için POC: paper hesapta login → hesap durumu → 1 sembol bar çekimi → bracket emir → mutabakat okuması. Çıktı: `BROKER_SPIKE.md` — kurulum yükü, API kısıtları, veri erişimi, TR'den hesap açılabilirliği (kullanıcı teyidi gerekir) karşılaştırma tablosu + öneri. **Karar kullanıcının.** Karar sonrası diğer yolun kodu silinir (ölü kod bırakılmaz).

---

# BÖLÜM 15 — TEST PLANI

## 15.1 Regresyon çapası (Bölüm 0.2)
`tests/test_golden_bist.py`: v7 snapshot + v7 config → trades.csv, golden ile bayt-bayt karşılaştırma. E2+'da her commit'in ön şartı.

## 15.2 Takvim/DST testleri (tests/test_calendars.py)
- XNYS: DST geçiş haftalarında (Mart/Kasım) `close_dt_utc` değerlerinin doğru kaydığı — sabitlenmiş beklenen değerlerle (golden).
- XIST: bilinen resmî tatil örnekleri işlem günü DEĞİL; v6'daki hayalet-bar tarihi (2024-04-08) `is_trading_day == False`.
- FX_24_5: Cumartesi bar yok; Cuma ve Pazartesi kapanışları doğru; yıl geçişi.

## 15.3 Yön ve boyutlama testleri (tests/test_direction.py, test_risk_engine ekleri)
- **Ayna simetrisi:** sentetik fiyat serisi P ve aynası (2×P₀−P) üzerinde LONG ve SHORT koşuları; trade sayısı, R dizisi ve PnL büyüklükleri eşit (işaretler ayna).
- **Sayısal boyutlama (SHORT, FX):** sleeve_equity=10.000 USD, risk %0.75 → 75 USD; EURUSD SHORT entry=1.1000, stop=1.1080 → per_unit_risk=0.0080 → qty=9.375 units; max_leverage=5 → tavan 50.000/1.1 ≈ 45.454 units → bağlamaz → beklenen 9.375.
- **Quote-ccy dönüşümü:** USDJPY entry=150.00, stop=151.20 (SHORT), USDJPY kuru 150 → per_unit_risk=1.20 JPY=0.0080 USD → qty=9.375 units (aynı risk, farklı parite).
- **Marjin kırpması:** düşük equity + yüksek qty senaryosunda MARGIN_INSUFFICIENT üretimi.
- **Stop-önceliği (SHORT):** aynı barda stop ve target ikisi de menzilde → stop fill, slippage aleyhte.
- **Carry:** 10 gün taşınan FX pozisyonu → 10 tahakkuk (Çarşamba 3× dahil sayım testi).
- **PDT:** journal'a 3 day-trade yazılmış margin hesapta 4. giriş → PDT_LIMIT; cash hesapta → izinli ama settled_cash kuralı devrede.
- **Settlement:** T+1 satış nakdi ertesi işlem gününe kadar boyutlamada kullanılamıyor.

## 15.4 Adapter/veri testleri
- Kanonik şema doğrulayıcı: her adapter'ın çıktısı şema testinden geçer (fixture'lı, ağsız).
- Snapshot determinizmi her piyasa için (HARDENING A1 kanıtının tekrarı, kısa koşu).
- events.py: blackout pencere hesabı sınır testleri (tam sınır günü/saatinde davranış).

## 15.5 Kabul kriterleri (değişmez)
Her piyasa için CLAUDE.md Bölüm 12.5 aynen (walk-forward PF ve DD kriterleri) + benchmark satırı (US: SPY; FX: sıfır-getiri; BIST: XU100). Kriter uyarlaması ancak kullanıcı onaylı ayrı bir metodoloji turunda yapılabilir — sonuç görüldükten SONRA kriter değiştirmek yasaktır (v3 turunda konan ilke).

---

# BÖLÜM 16 — E-FAZ PLANI VE "BİTTİ" TANIMLARI

> CLAUDE.md Bölüm 14 kalıbı: her madde ÇALIŞTIRILARAK doğrulanmadan faz kapanmaz. Her faz sonunda DUR + kullanıcı onayı.

**E1 — Veri Temeli** *(v7 turu bittikten sonra; BIST tasarım işleriyle paralel; motora dokunmaz)*
Yapılacak: US evren önerisi (15-20 sembol; likidite+2005'ten beri tarihçe+sektör çeşitliliği; geçmiş getiriye göre seçim YOK; survivorship notu) ve FX seti; `data/adapters/` iskeleti + yf_us + oanda(veya yedek CSV); tam tarihçe indirme; `data/snapshots/us/` ve `data/snapshots/fx/` dondurma; A2 denetimleri; events.py veri kaynak değerlendirmesi + örnek çekim.
Bitti: DATA_AUDIT_US.md + DATA_AUDIT_FX.md üretildi; snapshot manifest'leri hash'li; evren öneri tablosu gerekçeli; `git diff` BIST hattında sıfır değişiklik gösteriyor; adapter şema testleri yeşil.

**E2 — Motor Genelleştirme** *(ön şart: v7 bitti + BIST yeniden-tasarım kararı verildi + "E2 onaylandı")*
Yapılacak: golden çapa kurulumu (İLK İŞ); MarketSpec+registry; calendars.py (+clock.py delegasyonu); gate_registry + bist profili göçü; models.py ekleri; CostModel katmanı + bist göçü; daily_carry motor entegrasyonu; yön farkındalığı (Bölüm 9.1); settled_cash/PDT/marjin kuralları; config yükleyici (portfolio + markets, eşdeğerlik doğrulaması 11.4); journal kolon ekleri.
Bitti: TÜM mevcut testler + Bölüm 15.1-15.3 yeşil; çapa testi yeşil (bayt-bayt); `python -m strategy.signal_engine --symbol THYAO --date <tarih>` çıktısı E2 öncesiyle birebir aynı.

**E3 — Broker Adapter'ları (paper)** *("E3 onaylandı" + Bölüm 14 spike kararı)*
Yapılacak: BROKER_SPIKE.md → kullanıcı kararı → seçilen adapter(ler); auth/anahtar yönetimi SECURITY_AUDIT.md Faz-5 tasarımına uygun; reconciliation (HARDENING B2) yeniden kullanımı; costs/us sabitlerinin resmî doğrulaması.
Bitti: paper hesapta uçtan uca döngü kanıtlı (bar çek → sinyal → bracket emir → fill → mutabakat → journal); kill-switch/breaker dosya mekanikleri sleeve dizinlerinde çalışıyor; sırlar hiçbir log/commit'te yok.

**E4 — Piyasa Backtestleri** *("E4 onaylandı")*
Yapılacak: US tam süiti (snapshot'tan; earnings vetosu 10.4 protokolüne göre); FX tam süiti YALNIZCA short gate seti tanımlanmış ve 9.1 testleri yeşilse — değilse FX bu fazda "veri hazır, strateji bekliyor" olarak raporlanır ve atlanır.
Bitti: BACKTEST_REVIEW_US.md (CLAUDE.md Bölüm 15 şablonu + benchmark satırı + maliyet/veto notları); kabul kriteri sonucu açık; DUR — geçse bile sleeve `enabled: true` YAPILMAZ, kullanıcı onayı beklenir.

**E5 — Faz 6 Çok-Piyasa Paper** *(Faz 5 tamam + "E5 onaylandı")*
Yapılacak: scheduler çok-sleeve modu; backtest'i geçen sleeve'ler sinyalli paper; geçmeyenler istenirse emirsiz gölge modda; HARDENING B5 parite kontrolü sleeve başına; B7 karneleri sleeve başına.
Bitti: her aktif sleeve için ayrı B7 karnesi; PAPER_REVIEW.md sleeve bölümleriyle; Durma Noktası 2 sleeve başına yürürlükte.

---

# BÖLÜM 17 — BİLİNEN BELİRSİZLİKLER VE ÇÖZÜM PROTOKOLÜ

| # | Belirsizlik | Ne zaman çözülür | Protokol |
|---|---|---|---|
| 1 | Broker seçimi (IBKR vs Alpaca+OANDA) | E3 spike | BROKER_SPIKE.md + kullanıcı kararı; TR'den hesap açılabilirliği kullanıcı teyidi |
| 2 | US hesap tipi (cash vs margin / PDT) | E3 | Varsayılan cash (konservatif); kullanıcı kararıyla margin |
| 3 | SEC/TAF güncel oranları | E3 | Resmî kaynaktan doğrula, config'e işle, kaynak yorumu yaz |
| 4 | Earnings tarihçesinin derinliği | E1 | Bölüm 10.4 fallback protokolü |
| 5 | Ekonomik takvim tarihsel kaynağı | E1 | Bölüm 10.4 fallback protokolü |
| 6 | FX swap güncel oranları | E1 + E3 | Broker'dan güncel değer; tarihçe yoksa muhafazakâr sabit + rapor notu |
| 7 | OANDA veri derinliği / backtest başlangıcı | E1 | Gerçek derinliğe göre fx.yaml `backtest.start` kesinleşir |
| 8 | Altın maruziyeti (XAUUSD vs BIST fonu vs hiç) | E4 öncesi | Kullanıcı kararı; netleşene dek altın hiçbir sleeve'e eklenmez |
| 9 | FX real yasal/vergi durumu (SPK) | FX real ÖNCESİ | Kullanıcı kendi kanallarından teyit eder; teyitsiz real önerilmez (Bölüm 0.3) |
| 10 | Short gate seti tasarımı | BIST yeniden-tasarım sonrası, E4-FX öncesi | Kullanıcıyla ayrı tasarım turu; bu spec yalnızca motor yeteneğini kurar |
| 11 | Sleeve tahsis tutarları | Faz 6 öncesi | Kullanıcı girer; paper'da bile gerçekçi tahsis (metrik anlamlılığı) |

Genel kural (CLAUDE.md Bölüm 16 aynen): teknik belirsizlikte konservatif seç, STATUS.md'ye yaz, ilerle; risk parametresi/gerçek para belirsizliğinde varsayma, dur, sor.

---

# BÖLÜM 18 — requirements.txt EKLERİ

```
exchange_calendars==4.*
# E3 kararına göre YALNIZCA seçilen yol eklenir:
# ib_async==1.*            (Yol A)
# alpaca-py==0.*           (Yol B - US)
# (OANDA v20: 'requests' ile ince istemci yazılır — ağır SDK bağımlılığı almayız)
```
Sürüm çakışması protokolü CLAUDE.md Bölüm 18 ile aynı. `requirements.lock` her ekleme sonrası yenilenir (HARDENING A4).

---

# BÖLÜM 19 — GENİŞLETME REHBERİ GÜNCELLEMESİ

- **Yeni piyasa eklemek (örn. kripto):** MarketSpec + config/markets/<id>.yaml + CostModel + DataAdapter + (gerekirse) BrokerAdapter + takvim. Çekirdeğe dokunulmuyorsa tasarım doğrudur; dokunmak gerekiyorsa dur, EXPANSION.md'ye tasarım bölümü ekle, onay al.
- **Yeni gate:** CLAUDE.md Bölüm 17 kuralları + gate_registry'ye kayıt + hangi profillerde aktif olacağı config'te açıkça.
- **Tier 1 LLM haber vetosu (Faz 7):** bu spec'e ayrı bölüm olarak, paper istikrarı sonrası, kullanıcı onayıyla yazılır.

---

*Bu dokümanın sonu. İlk oturum: STATUS.md'yi oku; onay kapısı gelmemiş hiçbir E-fazına başlama.*

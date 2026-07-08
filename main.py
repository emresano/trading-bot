# main.py
"""Gölge paper scheduler (Faz 5, F5-B1) — regime_core (D1) canlı/paper döngüsü.

GÖLGE MOD: AlgoLab İPTAL (broker 2025-12-31'de kapatıldı). Veri kaynağı yfinance
EOD; emir katmanı PaperBroker (dahili simülatör). "backtest=canlı aynı fonksiyon"
(CLAUDE.md 3.1): sinyal/boyutlama `strategy/regime_core.py` SAF fonksiyonlarından
`RegimeCoreRunner` üzerinden ÇAĞRILIR — kopya yok.

İKİ MOD (config paper.go_live_date ile):
  observe (go_live_date=null): sinyal/kompozit hesaplanır, journal'a signal_eval
    yazılır, heartbeat + EOD özet üretilir; paper hesabı BAŞLATILMAZ, İŞLEM AÇILMAZ.
    Faz 6 ölçümü BAŞLAMIŞ SAYILMAZ (madde 5). Bu, gözetimli ilk koşunun modu.
  active (go_live_date=YYYY-MM-DD): operatör kararı. İlk aktif günde rejim AÇIKSA
    mevcut rejim benimsenir → t+1 kapanışta INITIAL_ENTER (madde 3); KAPALIYSA
    nakitte beklenir + modellenmiş faiz tahakkuku başlar.

MUTABAKAT (GÖLGE): harici broker YOK → harici pozisyon çekimi ATLANIR ve açıkça
loglanır. PaperBroker↔LocalLedger iç mutabakatı (F5A-3) yine çalışır.

Durma Noktası 2: 'real'e geçiş kod/komut olarak YOK. Bu scheduler yalnızca paper.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import yaml

from core.bist_calendar import BistCalendar
from data.live_feed import LiveDataFeed
from data.live_store import LiveHistoryStore
from execution.paper_broker import PaperBroker
from execution.regime_core_runner import RegimeCoreRunner
from journal.decision_journal import DecisionJournal
from notify.eod_summary import build_eod_summary
from notify.telegram_bot import TelegramConfig, TelegramNotifier, notifier_status
from safety.heartbeat import write_heartbeat
from safety.kill_switch import KillSwitchManager, SwitchConfig
from safety.reconciliation import LocalLedger, startup_reconcile
from strategy.regime_core import (
    RegimeCoreBreaker, RegimeCoreParams, build_composite, compute_regime_signal,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CycleResult:
    date: str
    mode: str                       # observe | active | skipped
    trading_day: bool
    regime_on: bool = False
    action: str = "OBSERVE"
    equity: float = 0.0
    cash: float = 0.0
    day_pnl: float = 0.0
    modeled_interest_total: float = 0.0
    trips: list = field(default_factory=list)
    eod_summary: str = ""
    notes: list = field(default_factory=list)
    cash_rate_status: dict = field(default_factory=dict)


class PaperScheduler:
    """Gölge paper günlük döngüsü. Bileşenler config'ten kurulur; `feed` ve
    `notifier_sender` test için enjekte edilebilir (offline)."""

    def __init__(self, cfg: dict, runtime_dir: Path | str,
                 feed: Optional[LiveDataFeed] = None,
                 notifier_sender: Optional[Callable[[str], None]] = None,
                 known_secrets: tuple = (),
                 now_fn: Optional[Callable[[], datetime]] = None):
        self.cfg = cfg
        self.runtime = Path(runtime_dir)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.now_fn = now_fn or _utcnow
        self.grace_sec = int(cfg.get("paper", {}).get("bar_close_grace_sec", 3600))
        self.symbols = cfg["symbols"]
        reg = cfg["regime"]
        costs = cfg["costs"]
        paper = cfg.get("paper", {})
        self.params = RegimeCoreParams(
            symbols=self.symbols, ma_period=reg["ma_period"], band_pct=reg["band_pct"],
            confirm_days=reg["confirm_days"], commission_bps=costs["commission_bps"],
            slippage_bps=costs["slippage_bps"], initial_equity=cfg["initial_equity"])
        gl = paper.get("go_live_date")
        self.go_live_date = pd.Timestamp(gl, tz="UTC") if gl else None
        self.mode = "active" if self.go_live_date is not None else "observe"

        # takvim
        self.calendar = BistCalendar(logger=lambda m: self._log("WARN", "CALENDAR", m))
        # cash rate: snapshot (read-only) + CANLI uzantı besleme (K1). backtest ile
        # AYNI kaynak/formül; snapshot DEĞİŞMEZ, canlı yeni aylar ayrı depoya.
        self.cash_rate_feed = self._build_cash_rate_feed(cfg)
        self.cash_rate = self.cash_rate_feed.combined_series() if self.cash_rate_feed else None

        # depo + besleme (feed enjekte edilirse onun deposu otoriter — test/paylaşım)
        if feed is not None:
            self.feed = feed
            self.store = feed.store
        else:
            self.store = LiveHistoryStore(self.runtime / "live_history.sqlite")
            self.feed = LiveDataFeed(self.store, self.symbols,
                                     logger=lambda m: self._log("INFO", "FEED", m))

        # journal + maskeleme
        self.journal = DecisionJournal(
            self.runtime / "decision_journal.jsonl", known_secrets=known_secrets,
            ma_period=reg["ma_period"], band_pct=reg["band_pct"], confirm_days=reg["confirm_days"])

        # telegram (config-gated, token'sız log-only)
        tg = cfg.get("telegram", {})
        enabled_cfg = bool(tg.get("enabled", False))
        token_present = bool(os.environ.get("TELEGRAM_TOKEN"))
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        tconf = TelegramConfig(enabled=enabled_cfg and token_present,
                               chat_id=chat_id, token_present=token_present)
        self.notifier = TelegramNotifier(tconf, sender=notifier_sender, known_secrets=known_secrets,
                                         logger=lambda m: self._log("WARN", "TELEGRAM", m))
        # F5-B2a.1: konfig-niyet (telegram.enabled=true) ile çalışma-durumu (token/chat_id
        # okunabilirliği) arasındaki uyuşmazlık bir daha SESSİZ kalmasın — belirgin WARN +
        # kalıcı durum satırı (EOD + heartbeat_status.json, bkz. aşağı).
        self.telegram_status = notifier_status(enabled_cfg, token_present, chat_id)
        if enabled_cfg and self.telegram_status[0] != "ACTIVE":
            self._log("WARN", "TELEGRAM",
                      f"telegram.enabled=true ama çalışma-durumu LOG-ONLY: {self.telegram_status[1]}")

        # breaker + kill-switch
        safety = cfg.get("safety", {})
        freeze_dir = Path(safety.get("freeze_dir", self.runtime / "freeze"))
        self.breaker = RegimeCoreBreaker(
            alarm_pct=safety.get("alarm_drawdown_pct", 0.25),
            freeze_pct=safety.get("freeze_drawdown_pct", 0.40),
            freeze_file=freeze_dir / "BREAKER",
            alarm_hook=lambda a: self._alarm({"category": "BREAKER", "level": "WARN",
                                              "message": f"ALARM drawdown {a.get('drawdown'):.2%}"}))
        self.killswitch = KillSwitchManager(
            SwitchConfig.from_yaml_dict(safety), freeze_dir=freeze_dir,
            breaker=self.breaker, alarm_hook=self._alarm)

        # broker + defter + runner
        self.broker = PaperBroker(
            initial_equity=cfg["initial_equity"], commission_bps=costs["commission_bps"],
            slippage_bps=costs["slippage_bps"], state_path=self.runtime / "paper_state.sqlite",
            history_store=self.store)
        self.ledger = LocalLedger(self.runtime / "local_ledger.sqlite")
        self.runner = RegimeCoreRunner(
            self.broker, self.params, cash_rate=self.cash_rate, breaker=self.breaker,
            state_path=self.runtime / "regime_runner.sqlite",
            decision_hook=self.journal.record_decision, ledger=self.ledger)
        self._state_file = self.runtime / "scheduler_state.json"

    # ------------------------------------------------------------------ yardımcılar
    def _log(self, level: str, category: str, message: str) -> None:
        try:
            self.journal.record_event(level, category, message)
        except Exception:
            pass
        print(f"[{_utcnow().isoformat()}] {level} {category}: {message}")

    def _alarm(self, alarm: dict) -> None:
        self.journal.record_alarm(alarm)
        self.notifier.send(f"[{alarm.get('level')}] {alarm.get('category')}: {alarm.get('message')}")

    def _build_cash_rate_feed(self, cfg: dict):
        cy = cfg.get("cash_yield")
        if not (cy and cy.get("enabled")):
            return None
        p = Path(cy["aux_snapshot"])
        if not p.exists():
            self._log("WARN", "DATA", f"cash_yield aux yok: {p} → faiz tahakkuku YOK")
            return None
        from data.cash_rate_feed import CashRateFeed
        return CashRateFeed(p, self.runtime / "cash_rate_ext.sqlite",
                            staleness_days=int(cy.get("staleness_days", 35)))

    def _sched_state(self) -> dict:
        if self._state_file.exists():
            return json.loads(self._state_file.read_text())
        return {"last_equity": self.params.initial_equity, "modeled_interest_total": 0.0,
                "last_cycle_date": None}

    def _save_sched_state(self, st: dict) -> None:
        self._state_file.write_text(json.dumps(st, indent=2, default=str))

    def _write_heartbeat_status(self, as_of, res) -> None:
        """Heartbeat companion (K1): faiz değeri + kaynak tarihi + bayatlık. Watchdog'un
        okuduğu `heartbeat` dosyası SADE timestamp kalır (format değişmez); bu ayrı dosya."""
        state, reason = self.telegram_status
        status = {
            "ts": _utcnow().isoformat(), "as_of": str(as_of), "mode": res.mode,
            "equity": res.equity, "cash": res.cash, "regime_on": res.regime_on,
            "cash_rate": res.cash_rate_status or None,
            "telegram": {"state": state, "reason": reason},
        }
        (self.runtime / "heartbeat_status.json").write_text(json.dumps(status, indent=2, default=str))

    # ------------------------------------------------------------------ veri yenileme
    def refresh_data(self) -> dict:
        """yfinance EOD çek (retry çağıran döngüde). Döner: FeedReport.totals()."""
        rep = self.feed.eod_update()
        t = rep.totals()
        if rep.no_data_symbols:
            self._log("WARN", "DATA", f"bar yok: {rep.no_data_symbols}")
        if t["conflicts"]:
            self._log("WARN", "DATA", f"çapraz-kaynak çakışma: {t['conflicts']}")
        return t

    # ------------------------------------------------------------------ mutabakat (GÖLGE)
    def startup(self) -> None:
        """Başlangıç: iç mutabakat (PaperBroker↔LocalLedger). HARİCİ broker YOK
        (AlgoLab iptal) → harici pozisyon çekimi ATLANIR + loglanır (GÖLGE mod)."""
        self._log("INFO", "RECON",
                  "GÖLGE mod: harici broker yok (AlgoLab iptal) → harici pozisyon "
                  "çekimi atlandı; iç PaperBroker↔LocalLedger mutabakatı çalışıyor.")
        res = startup_reconcile(self.broker, self.ledger,
                                freeze_file=self.runtime / "RECON_MISMATCH", alarm_hook=self._alarm)
        self._log("INFO" if res.matched else "CRITICAL", "RECON", res.summary())
        self.notifier.send(f"Paper bot başladı ({self.mode} mod). {res.summary()}")

    # ------------------------------------------------------------------ bar finalliği
    def _is_bar_final(self, as_of: date) -> bool:
        """as_of gününün BIST barı KAPANMIŞ mı (oluşmakta olan bar yasağı, CLAUDE.md
        BrokerAdapter.get_bars). Geçmiş gün → final. Bugün → seans kapanışı+grace
        geçtiyse final. Gelecek → değil. Sinyal yalnız FİNAL bardan hesaplanmalı;
        aksi halde yfinance gün-içi güncellenen bar sinyali sahte oynatır."""
        from datetime import datetime as _dt, timedelta
        from core.clock import to_istanbul
        now_local = to_istanbul(self.now_fn())
        as_of_d = self.calendar._d(as_of)
        if as_of_d < now_local.date():
            return True
        if as_of_d > now_local.date():
            return False
        end = self.calendar.continuous_end_for(as_of_d)
        close_dt = _dt.combine(as_of_d, end).replace(tzinfo=now_local.tzinfo) + timedelta(seconds=self.grace_sec)
        return now_local >= close_dt

    def _data_complete(self, closes: dict[str, pd.Series], ts: pd.Timestamp) -> tuple[bool, list[str]]:
        """ts günü İÇİN TÜM sembollerin barı depoda var mı (VERİ TAMLIĞI). Canlıda
        yfinance bazı sembollerin gün barını diğerlerinden geç yayınlayabilir; eksik
        sembol varken basket ENTER yürütmek EKSİK basket (undersized) üretir — bu, F5-B1
        dry-run'ında gözlenen 'kısmi basket' kusurunun kök nedeniydi. Yürütme yalnız
        TAM veride yapılır (backtest paritesini de korur: backtest tam-veride koşar)."""
        missing = [s for s, ser in closes.items() if ts not in ser.index]
        return (len(missing) == 0, missing)

    def _last_executable_date(self, as_of: date, closes: dict[str, pd.Series]) -> pd.Timestamp:
        """as_of ve öncesindeki son YÜRÜTÜLEBİLİR gün: hem FİNAL (kapanış+grace) hem
        TÜM sembollerde bar var (veri tam)."""
        from datetime import timedelta
        d = self.calendar._d(as_of)
        for _ in range(15):
            ts = pd.Timestamp(d, tz="UTC")
            if (self.calendar.is_trading_day(d) and self._is_bar_final(d)
                    and self._data_complete(closes, ts)[0]):
                return ts
            d -= timedelta(days=1)
        return pd.Timestamp(as_of, tz="UTC")

    # ------------------------------------------------------------------ sinyal
    def evaluate_signal(self, closes: dict[str, pd.Series], as_of: pd.Timestamp) -> Optional[dict]:
        """as_of gününe kadar kompozit/rejim değerlendirmesi (observe modu için)."""
        if any(len(s) == 0 for s in closes.values()):
            return None
        composite, _ = build_composite(closes)
        composite = composite.loc[composite.index <= as_of]
        if composite.empty:
            return None
        regime_on = compute_regime_signal(composite, self.params.ma_period,
                                          self.params.band_pct, self.params.confirm_days)
        ma = composite.rolling(self.params.ma_period).mean()
        above_upper = composite > ma * (1 + self.params.band_pct)
        d = composite.index[-1]
        ma_v = ma.loc[d]
        return {
            "date": d, "composite": float(composite.loc[d]),
            "ma": None if pd.isna(ma_v) else float(ma_v),
            "upper_band": None if pd.isna(ma_v) else float(ma_v) * (1 + self.params.band_pct),
            "lower_band": None if pd.isna(ma_v) else float(ma_v) * (1 - self.params.band_pct),
            "confirm_count": int(above_upper.loc[:d].tail(self.params.confirm_days).sum()),
            "regime_on": bool(regime_on.loc[d]),
        }

    def _adopt_regime_on(self, closes: dict[str, pd.Series]) -> bool:
        """go_live gününde rejim AÇIK mı (INITIAL_ENTER kararı için)."""
        composite, _ = build_composite(closes)
        regime_on = compute_regime_signal(composite, self.params.ma_period,
                                          self.params.band_pct, self.params.confirm_days)
        sub = regime_on.loc[regime_on.index <= self.go_live_date]
        return bool(sub.iloc[-1]) if len(sub) else False

    # ------------------------------------------------------------------ günlük döngü
    def run_cycle(self, as_of: date) -> CycleResult:
        as_of_ts = pd.Timestamp(as_of, tz="UTC")
        res = CycleResult(date=str(as_of), mode=self.mode,
                          trading_day=self.calendar.is_trading_day(as_of))
        if not res.trading_day:
            res.mode = "skipped"
            self._log("INFO", "CALENDAR", f"{as_of} işlem günü değil → döngü atlandı")
            write_heartbeat(self.runtime / "heartbeat")
            return res

        closes = self.feed.closes()
        st = self._sched_state()
        # K1: faiz serisini canlı güncelle (bayatsa FRED; başarısızsa son değer + WARN).
        if self.cash_rate_feed is not None:
            res.cash_rate_status = self.cash_rate_feed.refresh(
                as_of, logger=lambda m: self._log("INFO", "CASH_RATE", m))
            self.cash_rate = self.cash_rate_feed.combined_series()
            self.runner.cash_rate = self.cash_rate      # runner refreshed seriyi kullansın
            if res.cash_rate_status.get("stale"):
                self._log("WARN", "CASH_RATE",
                          f"faiz serisi BAYAT ({res.cash_rate_status['staleness_days']}g) → "
                          f"son değer {res.cash_rate_status['rate_pct']}% ile sürülüyor")
        # K4: TARİHSEL veri kayması (temettü/split geriye-dönük düzeltme) tespiti.
        drift = []
        try:
            drift = self.feed.detect_drift(exclude_from=as_of_ts)
        except Exception as e:
            self._log("WARN", "DATA_DRIFT", f"drift tespiti atlandı ({type(e).__name__})")
        if drift:
            res.notes.append(f"VERİ KAYMASI: {len(drift)} tarihsel bar sapması → sinyal "
                             f"FİNALİZE EDİLMEZ (operatör 'resync' gerekir)")
            self._alarm({"category": "DATA_DRIFT", "level": "CRITICAL",
                         "message": f"{len(drift)} tarihsel bar kaydı sapması; ör: {drift[0]}"})
            self.journal.record_event("CRITICAL", "DATA_DRIFT",
                                      f"{len(drift)} sapan bar; ilk: {drift[0]}")

        # FİNAL bar = (1) seans kapanışı+grace geçti VE (2) TÜM sembollerde bar var
        #             VE (3) tarihsel veri kayması YOK (K4).
        time_final = self._is_bar_final(as_of)
        data_complete, missing = self._data_complete(closes, as_of_ts)
        final = time_final and data_complete and not drift
        if not time_final:
            res.notes.append("as_of barı henüz KAPANMADI (oluşmakta) → sinyal PROVISIONAL; "
                             "yürütme son yürütülebilir güne sınırlı")
            self._log("WARN", "SIGNAL", res.notes[-1])
        elif not data_complete:
            res.notes.append(f"as_of barı zaman-final ama VERİ EKSİK ({len(missing)} sembol: "
                             f"{missing[:5]}...) → yürütme ertelendi (kısmi basket yasağı)")
            self._log("WARN", "DATA", res.notes[-1])
        # yürütmede kullanılacak son yürütülebilir gün (final+veri-tam); değilse son tam gün
        exec_today = as_of_ts if final else self._last_executable_date(as_of, closes)

        if self.mode == "observe":
            snap = self.evaluate_signal(closes, as_of_ts)
            if snap is None:
                res.notes.append("kompozit hesaplanamadı (yetersiz geçmiş)")
                self._log("WARN", "SIGNAL", res.notes[-1])
            else:
                res.regime_on = snap["regime_on"]
                self.journal.record_signal_evaluation(
                    date=snap["date"], composite=snap["composite"], ma=snap["ma"],
                    upper_band=snap["upper_band"], lower_band=snap["lower_band"],
                    confirm_count=snap["confirm_count"], regime_on=snap["regime_on"],
                    in_position=False, mode="observe", provisional=not final)
                res.action = "OBSERVE_REGIME_ON" if snap["regime_on"] else "OBSERVE_REGIME_OFF"
            acct = self.broker.get_account_state()
            res.equity, res.cash = acct.equity, acct.cash
        else:  # active
            # ilk aktivasyon: initialize_flat(go_live, adopt)
            last_processed, *_ = self.runner._state()
            first_activation = last_processed is None
            if first_activation:
                adopt = self._adopt_regime_on(closes)
                self.runner.initialize_flat(self.go_live_date, adopt_regime_on=adopt)
                self._log("INFO", "GOLIVE",
                          f"go_live={self.go_live_date.date()} adopt_regime_on={adopt} "
                          f"(AÇIKSA t+1 kapanışta INITIAL_ENTER)")
            # oluşmakta olan bar üzerinde yürütme YOK — yalnız son FİNAL güne kadar işle.
            decisions = self.runner.process_up_to(closes, today=exec_today)
            # CATCH-UP + GECİKMİŞ SİNYAL (K3): bot kapalıyken (birden çok gün) oluşan
            # anahtarlamalar bugünün-öncesi günlerde yürütülür → GECİKMİŞ SİNYAL alarmı +
            # journal etiketi. İlk aktivasyon (go-live catch-up) BEKLENENDİR, işaretlenmez.
            if not first_activation:
                catchup = [d for d in decisions
                           if d.action in self._SWITCH_ACTIONS and pd.Timestamp(d.date) < exec_today]
                for d in catchup:
                    self._alarm({"category": "DELAYED_SIGNAL", "level": "WARN",
                                 "message": f"GECİKMİŞ SİNYAL: {d.action}@{pd.Timestamp(d.date).date()} "
                                            f"bot kapalıyken oluştu; catch-up ile bir sonraki kapanışta yürütüldü"})
                    self.journal.record_event("WARN", "DELAYED_SIGNAL",
                                              f"{d.action}@{pd.Timestamp(d.date).date()} gecikmeli yürütüldü "
                                              f"(kaçan gün, exec_today={exec_today.date()})")
                if catchup:
                    res.notes.append(f"catch-up: {len(catchup)} gecikmiş anahtarlama yürütüldü")
            acct = self.broker.get_account_state()
            res.equity, res.cash = acct.equity, acct.cash
            if decisions:
                last = decisions[-1]
                res.regime_on = last.signal_yesterday
                res.action = last.action
                res.modeled_interest_total = self.broker.accrued_interest
                res.day_pnl = res.equity - float(st["last_equity"])
                # kill-switch değerlendirmesi
                peak = max(last.peak_equity, res.equity)
                trips = self.killswitch.evaluate_cycle(
                    equity=res.equity, peak=peak, daily_pnl=res.day_pnl, date=as_of_ts)
                res.trips = [t.switch for t in trips]
                for t in trips:
                    self._alarm({"category": "KILL_SWITCH", "level": t.level,
                                 "message": f"{t.switch}: {t.reason}"})
            st["modeled_interest_total"] = self.broker.accrued_interest

        # heartbeat (+ K1 faiz durumu companion; watchdog heartbeat formatı DEĞİŞMEZ)
        write_heartbeat(self.runtime / "heartbeat")
        self._write_heartbeat_status(as_of, res)
        next_note = self._next_calendar_note(as_of)
        # F5-B2a.1 mikro-düzeltme: "Rejim" (regime_on — compute_regime_signal) ve
        # "Pozisyon" (in_position — broker'da sepet var mı) AYRI satırlar; observe modda
        # pozisyon HER ZAMAN NAKİT'tir (hesap başlatılmadı) ama rejim ON olabilir — eskiden
        # tek satır in_position'dan türetildiği için observe'da rejim ON iken bile "NAKİT
        # (rejim OFF)" basılıyor, üstteki [GÖZLEM] başlığıyla çelişiyordu.
        res.eod_summary = build_eod_summary(
            date=as_of, equity=res.equity, cash=res.cash, day_pnl=res.day_pnl,
            in_position=bool(self.broker.quantities()), regime_on=res.regime_on,
            observe_mode=(self.mode == "observe"), breaker_state="OK",
            frozen_switches=self.killswitch.frozen_switches(),
            modeled_interest_total=res.modeled_interest_total, next_calendar_note=next_note,
            cash_rate_status=res.cash_rate_status or None,
            telegram_status=self.telegram_status)
        if self.mode == "observe":
            res.eod_summary = "[GÖZLEM — paper hesabı başlatılmadı, işlem yok]\n" + res.eod_summary
        self.notifier.send(res.eod_summary)

        st["last_equity"] = res.equity
        st["last_cycle_date"] = str(as_of)
        self._save_sched_state(st)
        return res

    # ------------------------------------------------------------------ parite (B5)
    _SWITCH_ACTIONS = ("ENTER", "INITIAL_ENTER", "EXIT")

    def parity_check(self, as_of: date) -> dict:
        """Gölge parite (B5): TEMİZ bir yeniden-koşum (fresh RegimeCoreRunner, go-live'dan)
        canlı karar günlüğüyle karşılaştırılır. Aynı ÜRETİM kodu + aynı closes → aynı
        anahtarlamalar; fark = state bozulması / veri kayması / kod kayması → KIRMIZI
        ALARM. Yalnızca active modda anlamlı (observe'da anahtarlama yok)."""
        if self.mode != "active":
            return {"mode": self.mode, "applicable": False}
        import tempfile
        closes = self.feed.closes()
        tmp = Path(tempfile.mkdtemp(prefix="parity_", dir=str(self.runtime)))
        try:
            broker = PaperBroker(self.params.initial_equity, self.params.commission_bps,
                                 self.params.slippage_bps, state_path=tmp / "b.sqlite",
                                 history_store=self.store)
            runner = RegimeCoreRunner(broker, self.params, cash_rate=self.cash_rate,
                                      breaker=RegimeCoreBreaker(freeze_file=tmp / "BREAKER"),
                                      state_path=tmp / "r.sqlite")
            runner.initialize_flat(self.go_live_date, adopt_regime_on=self._adopt_regime_on(closes))
            decs = runner.process_up_to(closes, today=pd.Timestamp(as_of, tz="UTC"))
            replay = [(str(pd.Timestamp(d.date).date()), d.action) for d in decs
                      if d.action in self._SWITCH_ACTIONS]
            runner.close(); broker.close()
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        live = [(r["date"][:10], r["action"]) for r in self.journal.read_all()
                if r.get("type") == "decision" and r.get("action") in self._SWITCH_ACTIONS]
        matched = replay == live
        out = {"mode": "active", "applicable": True, "matched": matched,
               "replay_switches": replay, "live_switches": live}
        if not matched:
            self._alarm({"category": "PARITY", "level": "CRITICAL",
                         "message": f"PARİTE FARKI (KIRMIZI): replay={replay} canlı={live}"})
        else:
            self._log("INFO", "PARITY", f"parite OK — {len(replay)} anahtarlama özdeş")
        return out

    # ------------------------------------------------------------------ resync (K4, operatör)
    def resync(self, as_of: Optional[date] = None) -> dict:
        """OPERATÖR KOMUTU (K4): tam tarihçe yeniden çekilir (yfinance temettü/split
        yeniden-düzeltmesi), eski depo yedeklenir, farklar loglanır, canlı↔backtest kompozit
        paritesi OTOMATİK yeniden koşulur ve raporlanır. Otomatik DEĞİL — operatör başlatır."""
        as_of = as_of or self.calendar._d(self.now_fn().astimezone().date())
        self._log("INFO", "RESYNC", "resync başladı — tam tarihçe yeniden çekiliyor")
        start = self.cfg.get("backtest", {}).get("start", "2005-01-01")
        rep = self.feed.resync(self.runtime / "backups", start=start)
        # otomatik parite: canlı kompozit ↔ backtest snapshot kompozit (ortak günlerde)
        parity = self._composite_parity_vs_backtest()
        rep["composite_parity"] = parity
        lvl = "INFO" if parity.get("max_abs_diff", 1) < 1e-6 else "CRITICAL"
        self._log(lvl, "RESYNC",
                  f"resync bitti: {sum(rep['replaced'].values())} bar; kompozit parite "
                  f"max_abs_diff={parity.get('max_abs_diff')}")
        self.notifier.send(f"RESYNC tamam: {len(rep['diffs'])} sembolde tarihsel değişim; "
                           f"kompozit parite max_abs_diff={parity.get('max_abs_diff')}")
        return rep

    def _composite_parity_vs_backtest(self) -> dict:
        """Canlı depo kompoziti ↔ backtest snapshot kompoziti (ortak günlerde bit-bit)."""
        from data.cleaning import load_and_clean_universe
        from strategy.regime_core import build_composite
        bt_cfg = self.cfg.get("backtest", {})
        if not bt_cfg.get("snapshot") or not Path(bt_cfg["snapshot"]).exists():
            return {"skipped": "backtest snapshot yok"}
        live = build_composite(self.feed.closes())[0]
        snap_dir = Path(bt_cfg["snapshot"])
        start = bt_cfg["start"]

        def _load(s):
            return pd.read_parquet(snap_dir / f"{s}.parquet").loc[start:]

        try:
            cleaned, _ = load_and_clean_universe(self.symbols, _load)
            bt = build_composite({s: cleaned[s]["close"] for s in self.symbols})[0]
        except Exception as e:
            return {"error": type(e).__name__}
        common = live.index.intersection(bt.index)
        if len(common) == 0:
            return {"common_days": 0}
        diff = (live.loc[common] - bt.loc[common]).abs()
        return {"common_days": int(len(common)), "max_abs_diff": float(diff.max())}

    def _next_calendar_note(self, as_of: date) -> str:
        from datetime import timedelta
        d = pd.Timestamp(as_of).date() + timedelta(days=1)
        for _ in range(10):
            if self.calendar.is_trading_day(d):
                half = " (yarım gün)" if self.calendar.is_half_day(d) else ""
                return f"{d} işlem günü{half}"
            d += timedelta(days=1)
        return "sonraki işlem günü belirlenemedi"

    def run_once(self, as_of: Optional[date] = None) -> CycleResult:
        """Tam günlük akış: (opsiyonel veri yenileme çağıranın işi) → döngü."""
        as_of = as_of or self.calendar._d(datetime.now(timezone.utc).astimezone().date())
        return self.run_cycle(as_of)

    def close(self) -> None:
        for c in (self.store, self.broker, self.ledger, self.runner, self.killswitch):
            try:
                c.close()
            except Exception:
                pass


# ------------------------------------------------------------------ CLI
def load_config(cfg_path: str) -> dict:
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    # telegram bloğunu config.yaml'dan (varsa) ekle — regime_core.yaml içermez
    main_cfg_path = Path("config/config.yaml")
    if "telegram" not in cfg and main_cfg_path.exists():
        main = yaml.safe_load(main_cfg_path.read_text(encoding="utf-8"))
        cfg["telegram"] = main.get("telegram", {})
    return cfg


def _load_secrets() -> tuple:
    """secrets.env'i env'e yükle (varsa) ve maskeleme için değerleri topla.
    Değerler ASLA loglanmaz — yalnız maskeleme substring listesi."""
    env_path = Path("config/secrets.env")
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except Exception:
            pass
    keys = ("ALGOLAB_API_KEY", "ALGOLAB_USERNAME", "ALGOLAB_PASSWORD",
            "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "EVDS_API_KEY")
    return tuple(v for v in (os.environ.get(k) for k in keys) if v)


def _cmd_test_telegram(config_path: str, notifier: Optional[TelegramNotifier] = None) -> int:
    """F5-B2a.1: konfigürasyonu yükler, notifier durumunu raporlar (ACTIVE/LOG-ONLY
    + neden) ve ACTİFse maskeli bir test mesajı gönderir. Token/chat_id DEĞERİ hiçbir
    biçimde yazdırılmaz — yalnızca durum + maskeli gönderilen metin. `notifier` yalnız
    testte enjekte edilir (gerçek HTTP YOK); üretimde None → gerçek TelegramNotifier kurulur."""
    cfg = load_config(config_path)
    secrets = _load_secrets()
    tg = cfg.get("telegram", {})
    enabled_cfg = bool(tg.get("enabled", False))
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    state, reason = notifier_status(enabled_cfg, bool(token), chat_id)
    print(f"TELEGRAM durumu: {state} ({reason})")
    if state != "ACTIVE":
        print("test mesajı gönderilmedi (LOG-ONLY).")
        return 1
    if notifier is None:
        tconf = TelegramConfig(enabled=True, chat_id=chat_id, token_present=True)
        notifier = TelegramNotifier(tconf, known_secrets=secrets,
                                    logger=lambda m: print(f"WARN TELEGRAM: {m}"))
    ok = notifier.send(f"[test-telegram] BIST trading-bot bağlantı testi — {_utcnow().isoformat()}")
    masked = notifier.sent[-1] if notifier.sent else ""
    print(f"gönderim sonucu: {'BAŞARILI' if ok else 'BAŞARISIZ'}  mesaj(maskeli)={masked}")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="Gölge paper scheduler (F5-B1)")
    ap.add_argument("--config", default="config/regime_core.yaml")
    ap.add_argument("--bootstrap", action="store_true", help="snapshot'tan canlı depoyu bootstrap et")
    ap.add_argument("--refresh", action="store_true", help="yfinance EOD güncelle")
    ap.add_argument("--cycle", action="store_true", help="bir günlük döngü koş")
    ap.add_argument("--resync", action="store_true",
                    help="K4 operatör: tam tarihçe yeniden çek + yedekle + parite (veri kayması sonrası)")
    ap.add_argument("--test-telegram", action="store_true",
                    help="F5-B2a.1: notifier durumunu raporla (ACTIVE/LOG-ONLY+neden); "
                         "ACTİFse maskeli test mesajı gönder; exit code sonucu yansıtır")
    ap.add_argument("--as-of", default=None, help="döngü günü (YYYY-MM-DD; vars. bugün)")
    ap.add_argument("--runtime", default=None, help="runtime kökü (vars. config paper.runtime_dir)")
    args = ap.parse_args()

    if args.test_telegram:
        raise SystemExit(_cmd_test_telegram(args.config))

    cfg = load_config(args.config)
    secrets = _load_secrets()
    runtime_dir = args.runtime or cfg.get("paper", {}).get("runtime_dir", "runtime/paper")
    sched = PaperScheduler(cfg, runtime_dir, known_secrets=secrets)

    if args.bootstrap:
        snap = cfg["paper"]["snapshot_bootstrap"]
        rep = sched.feed.bootstrap_from_snapshot(snap, start=cfg["backtest"]["start"])
        print("bootstrap:", {s: rep[s].inserted for s in list(rep)[:3]}, "...")
    if args.refresh:
        print("refresh:", sched.refresh_data())
    if args.resync:
        rep = sched.resync()
        print("resync:", {"replaced_total": sum(rep["replaced"].values()),
                          "diffs": rep["diffs"], "composite_parity": rep["composite_parity"]})
    sched.startup()
    if args.cycle:
        as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).astimezone().date()
        res = sched.run_cycle(as_of)
        print("--- CYCLE ---")
        print(f"date={res.date} mode={res.mode} regime_on={res.regime_on} action={res.action}")
        print(f"equity={res.equity:,.2f} cash={res.cash:,.2f} trips={res.trips}")
        print(res.eod_summary)
    sched.close()


if __name__ == "__main__":
    main()

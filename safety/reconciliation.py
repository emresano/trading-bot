# safety/reconciliation.py
"""Başlangıç mutabakatı + durum kurtarma (HARDENING B2, Faz 5 F5A-3).

Broker'daki gerçek pozisyonlar ↔ yerel beklenen pozisyonlar karşılaştırılır. Herhangi
bir uyuşmazlık → **FREEZE** (yeni emir yok) + alarm. Bot uyuşmazlığı KENDİ BAŞINA
"düzeltmez" — insan kararı (B2: otomatik düzeltme YASAK).

"Emir gönderildi ama yanıt gelmeden çöküş" senaryosu: PaperBroker fill'i atomik
commit ettiğinden broker'da pozisyon oluşur; runner yerel defteri (LocalLedger)
güncellemeden çökerse → yeniden başlatmada broker≠yerel → FREEZE + alarm. Kurtarma
politikası: **broker gerçeği esastır** ama benimseme (adopt) yalnızca kullanıcı
komutuyla (freeze'i elle temizler + adopt_broker_state çağrılır).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

DEFAULT_LEDGER = Path("runtime/local_ledger.sqlite")
DEFAULT_RECON_FREEZE = Path("runtime/RECON_MISMATCH")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalLedger:
    """Botun 'beklediği' pozisyon durumu — broker'dan BAĞIMSIZ kalıcı defter.
    Runner her başarılı döngü SONUNDA buraya yazar; çöküş bu yazımdan önce olursa
    broker ile ayrışır (mutabakat bunu yakalar)."""

    def __init__(self, path: Path | str = DEFAULT_LEDGER):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.executescript(
            "CREATE TABLE IF NOT EXISTS local_positions (symbol TEXT PRIMARY KEY, "
            "quantity INTEGER NOT NULL, updated_at TEXT NOT NULL);")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def get_positions(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT symbol, quantity FROM local_positions WHERE quantity != 0").fetchall()
        return {r[0]: int(r[1]) for r in rows}

    def sync_from(self, positions: dict[str, int]) -> None:
        """Yerel defteri verilen pozisyon setine eşitle (döngü sonu / benimseme)."""
        now = _utcnow_iso()
        self._conn.execute("DELETE FROM local_positions")
        for sym, qty in positions.items():
            if qty != 0:
                self._conn.execute(
                    "INSERT INTO local_positions (symbol, quantity, updated_at) VALUES (?,?,?)",
                    (sym, int(qty), now))
        self._conn.commit()


@dataclass
class Mismatch:
    symbol: str
    broker_qty: int
    local_qty: int


@dataclass
class ReconResult:
    matched: bool
    mismatches: list[Mismatch] = field(default_factory=list)
    froze: bool = False
    checked_at: str = ""

    def summary(self) -> str:
        if self.matched:
            return "RECON OK — broker ↔ yerel eşleşti"
        parts = [f"{m.symbol}: broker={m.broker_qty} yerel={m.local_qty}" for m in self.mismatches]
        return "RECON MISMATCH — " + "; ".join(parts)


def diff_positions(broker: dict[str, int], local: dict[str, int]) -> list[Mismatch]:
    """Sembol+miktar bazında fark. Sıfır olmayan tüm ayrışmalar döner (deterministik sıra)."""
    mismatches: list[Mismatch] = []
    for sym in sorted(set(broker) | set(local)):
        b = int(broker.get(sym, 0))
        l = int(local.get(sym, 0))
        if b != l:
            mismatches.append(Mismatch(sym, b, l))
    return mismatches


def reconcile(broker_positions: dict[str, int], local_positions: dict[str, int],
              freeze_file: Path | str = DEFAULT_RECON_FREEZE,
              alarm_hook: Optional[Callable[[dict], None]] = None) -> ReconResult:
    """Mutabakat. Uyuşmazlıkta freeze_file yazılır + alarm_hook çağrılır. Otomatik
    düzeltme YOK — yalnızca durdurur ve bildirir."""
    checked = _utcnow_iso()
    mismatches = diff_positions(broker_positions, local_positions)
    if not mismatches:
        return ReconResult(matched=True, checked_at=checked)
    ff = Path(freeze_file)
    froze = False
    if not ff.exists():
        ff.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"date={checked} (RECON MISMATCH — yeni emir yok; reset yalnız kullanıcı)"]
        lines += [f"  {m.symbol}: broker={m.broker_qty} yerel={m.local_qty}" for m in mismatches]
        ff.write_text("\n".join(lines) + "\n")
        froze = True
    result = ReconResult(matched=False, mismatches=mismatches, froze=froze, checked_at=checked)
    if alarm_hook is not None:
        alarm_hook({"category": "RECON", "level": "CRITICAL", "message": result.summary(),
                    "mismatches": [(m.symbol, m.broker_qty, m.local_qty) for m in mismatches]})
    return result


def startup_reconcile(broker, ledger: LocalLedger,
                      freeze_file: Path | str = DEFAULT_RECON_FREEZE,
                      alarm_hook: Optional[Callable[[dict], None]] = None) -> ReconResult:
    """Başlangıçta broker.quantities() ↔ ledger.get_positions() (B2)."""
    return reconcile(broker.quantities(), ledger.get_positions(), freeze_file, alarm_hook)


def adopt_broker_state(broker, ledger: LocalLedger,
                       freeze_file: Path | str = DEFAULT_RECON_FREEZE) -> None:
    """KULLANICI KOMUTU (otomatik DEĞİL): broker gerçeğini yerel deftere benimse ve
    RECON freeze'ini temizle. B2: broker'daki gerçek durum esastır."""
    ledger.sync_from(broker.quantities())
    ff = Path(freeze_file)
    if ff.exists():
        ff.unlink()


def recon_frozen(freeze_file: Path | str = DEFAULT_RECON_FREEZE) -> bool:
    return Path(freeze_file).exists()

# execution/algolab/auth.py
"""AlgoLab login + SMS + session yönetimi (CLAUDE.md Bölüm 11.2, Faz 5 F5A-8).

**DOĞRULANMAMIŞ — REFERANS (oanda.py emsali):** endpoint adları/alanları AlgoLab'ın
topluluk-bilinen davranışına dayanır. F5-B'nin İLK işi bunları resmî dokümanla
karşılaştırmaktır (CLAUDE.md Bölüm 11 notu + Bölüm 16 #1). Bu modül HİÇBİR CANLI
ÇAĞRI YAPMAZ — `transport` enjekte edilebilir; F5-A testleri şifreleme/checker/başlık
kurulumunu ağsız fixture'la doğrular.

Kimlik bilgisi: değerler secrets.env'den okunur, KODA/LOGA düz metin yazılmaz
(journal.masking). Session hash `runtime/algolab_session.json`'a 600 izniyle yazılır.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Callable, Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from execution.broker_adapter import BrokerError

BASE = "https://www.algolab.com.tr/api"
DEFAULT_SESSION_FILE = Path("runtime/algolab_session.json")

# transport(endpoint, payload, headers) -> dict (parse edilmiş JSON). Canlı HTTP
# yalnızca F5-B'de default transport ile; F5-A'da her zaman enjekte edilir.
Transport = Callable[[str, dict, dict], dict]


class AlgoLabAuth:
    def __init__(self, api_key: str, username: str, password: str,
                 transport: Optional[Transport] = None,
                 session_file: Path | str = DEFAULT_SESSION_FILE):
        if not api_key.startswith("API-"):
            raise BrokerError("AlgoLab api_key 'API-' ile başlamalı")
        self.api_key = api_key
        self.api_code = api_key.split("API-")[-1]
        self.username = username
        self.password = password
        self._transport = transport
        self.session_file = Path(session_file)
        self.token: Optional[str] = None      # SMS aşaması ara token
        self.hash: Optional[str] = None        # oturum hash'i

    # ------------------------------------------------------------------ kripto (testable, saf)
    def _encrypt(self, text: str) -> str:
        iv = b"\0" * 16
        key = base64.b64decode(self.api_code.encode())
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(pad(text.encode(), 16))).decode()

    def _checker(self, endpoint: str, payload: Optional[dict]) -> str:
        body = json.dumps(payload).replace(" ", "") if payload else ""
        return hashlib.sha256((self.api_key + endpoint + body).encode()).hexdigest()

    def _headers(self, endpoint: str, payload: Optional[dict], authorized: bool) -> dict:
        headers = {"APIKEY": self.api_key, "Checker": self._checker(endpoint, payload),
                   "Content-Type": "application/json"}
        if authorized:
            if not self.hash:
                raise BrokerError("authorized çağrı için session hash yok (login gerekli)")
            headers["Authorization"] = self.hash
        return headers

    def _post(self, endpoint: str, payload: dict, authorized: bool) -> dict:
        if self._transport is None:
            raise BrokerError(
                "AlgoLabAuth: transport yok — F5-A'da canlı çağrı YASAK. Canlı HTTP F5-B'de "
                "resmî doküman doğrulamasından sonra bağlanır (CLAUDE.md 11).")
        headers = self._headers(endpoint, payload, authorized)
        data = self._transport(endpoint, payload, headers)
        if not data.get("success", False):
            raise BrokerError(f"AlgoLab {endpoint}: {data.get('message')}")
        return data

    # ------------------------------------------------------------------ akış
    def login_user(self) -> None:
        """Adım 1: kimlik gönder → SMS tetiklenir, ara token döner."""
        payload = {"Username": self._encrypt(self.username), "Password": self._encrypt(self.password)}
        r = self._post("/api/LoginUser", payload, authorized=False)
        self.token = r["content"]["token"]

    def login_user_control(self, sms_code: str) -> None:
        """Adım 2: SMS kodu → kalıcı oturum hash'i (600 izinli dosyaya yazılır)."""
        payload = {"token": self._encrypt(self.token), "Password": self._encrypt(sms_code)}
        r = self._post("/api/LoginUserControl", payload, authorized=False)
        self.hash = r["content"]["hash"]
        self._save_session()

    def session_refresh(self) -> bool:
        r = self._post("/api/SessionRefresh", {}, authorized=True)
        return bool(r.get("success"))

    # ------------------------------------------------------------------ session dosyası (600)
    def _save_session(self) -> None:
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.session_file.write_text(json.dumps({"hash": self.hash}))
        os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)  # 600

    def load_session(self) -> bool:
        if not self.session_file.exists():
            return False
        self.hash = json.loads(self.session_file.read_text()).get("hash")
        return bool(self.hash)

# journal/masking.py
"""Merkezî kimlik-bilgisi maskeleme (Faz 5, F5A-5).

Kural (CLAUDE.md 0.2 + HARDENING B4/B6): API anahtarı, oturum hash'i, TC no, şifre,
Telegram token — HİÇBİR log/journal/çıktıya düz metin yazılmaz. Bu yardımcı karar
günlüğü (F5A-5), Telegram (F5A-7) ve AlgoLab adapter (F5A-8) tarafından kullanılır.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

_API_KEY = re.compile(r"API-[A-Za-z0-9_\-]{4,}")
_LONG_HEX = re.compile(r"\b[0-9a-fA-F]{32,}\b")   # oturum hash'i benzeri
_TCNO = re.compile(r"\b\d{11}\b")                  # TC kimlik no
_BEARER = re.compile(r"(?i)(authorization|apikey|token|password|hash)\s*[=:]\s*\S+")

REDACTION = "***"


def mask_secret(value: Any, known_secrets: Iterable[str] = ()) -> str:
    """Bilinen sır dizelerini + genel desenleri maskele. `known_secrets`: secrets.env'den
    gelen gerçek değerler (varsa) — birebir eşleşmeler önce maskelenir."""
    s = str(value)
    for sec in known_secrets:
        if sec and len(str(sec)) >= 3:
            s = s.replace(str(sec), REDACTION)
    s = _BEARER.sub(lambda m: m.group(0).split("=")[0].split(":")[0].rstrip() + "=" + REDACTION
                    if ("=" in m.group(0) or ":" in m.group(0)) else REDACTION, s)
    s = _API_KEY.sub("API-" + REDACTION, s)
    s = _LONG_HEX.sub(REDACTION + "HASH" + REDACTION, s)
    s = _TCNO.sub(REDACTION + "TCNO" + REDACTION, s)
    return s


def sanitize(obj: Any, known_secrets: Iterable[str] = ()) -> Any:
    """Bir dict/list/str yapısını özyinelemeli maskele. Sayılar/bool dokunulmaz
    (miktar/fiyat gibi işlevsel veriler korunur), yalnızca string'ler maskelenir."""
    if isinstance(obj, str):
        return mask_secret(obj, known_secrets)
    if isinstance(obj, dict):
        return {k: sanitize(v, known_secrets) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v, known_secrets) for v in obj]
    return obj

"""Signed session cookie (stdlib only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from msgate.app.state import AppState

COOKIE_NAME = "msgate_session"
MAX_AGE = 86400 * 7


def session_key(state: AppState) -> bytes:
    return state.secret_box.derive_key("msgate-web-session-v1")


def encode_session(data: dict[str, Any], key: bytes) -> str:
    body = {**data, "exp": int(time.time()) + MAX_AGE}
    payload = json.dumps(body, separators=(",", ":")).encode()
    sig = hmac.new(key, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + sig).decode("ascii")


def decode_session(token: str, key: bytes) -> dict[str, Any] | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload, sep, sig = raw.rpartition(b".")
        if not sep:
            return None
        expected = hmac.new(key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(payload.decode("utf-8"))
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        return data
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

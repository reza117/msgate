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
    # Never store internal exp in the caller's dict; build a clean body.
    body = {k: v for k, v in data.items() if k != "exp"}
    body["exp"] = int(time.time()) + MAX_AGE
    payload = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(key, payload, hashlib.sha256).digest()
    # Base64 both parts so binary sig bytes (including 0x2e '.') cannot break the split.
    return (
        base64.urlsafe_b64encode(payload).decode("ascii")
        + "."
        + base64.urlsafe_b64encode(sig).decode("ascii")
    )


def decode_session(token: str, key: bytes) -> dict[str, Any] | None:
    try:
        payload_b64, sep, sig_b64 = token.partition(".")
        if not sep or not payload_b64 or not sig_b64:
            return None
        payload = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        sig = base64.urlsafe_b64decode(sig_b64.encode("ascii"))
        expected = hmac.new(key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(payload.decode("utf-8"))
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        data.pop("exp", None)
        return data
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

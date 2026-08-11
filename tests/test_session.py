"""Session cookie encode/decode tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from msgate.auth.session import decode_session, encode_session


def test_session_roundtrip() -> None:
    key = b"k" * 32
    token = encode_session({"admin_user": "admin", "must_change_password": False}, key)
    data = decode_session(token, key)
    assert data == {"admin_user": "admin", "must_change_password": False}


def test_session_survives_dot_bytes_in_hmac() -> None:
    """Old format broke when raw HMAC contained 0x2e ('.') — ~12% of tokens."""
    key = b"k" * 32
    # Force many encodes; at least one path must survive decode.
    ok = 0
    for i in range(200):
        token = encode_session({"admin_user": "admin", "n": i}, key)
        data = decode_session(token, key)
        assert data is not None
        assert data["admin_user"] == "admin"
        assert data["n"] == i
        ok += 1
    assert ok == 200


def test_legacy_raw_sig_format_rejected_safely() -> None:
    """Tokens from the old payload+raw_sig format must not crash; may fail verify."""
    key = b"k" * 32
    body = json.dumps({"admin_user": "admin", "exp": int(time.time()) + 3600}).encode()
    sig = hmac.new(key, body, hashlib.sha256).digest()
    # Inject a '.' inside the signature to mimic the old bug case.
    bad_sig = sig[:10] + b"." + sig[10:31]
    legacy = base64.urlsafe_b64encode(body + b"." + bad_sig).decode("ascii")
    assert decode_session(legacy, key) is None


def test_session_expired() -> None:
    key = b"k" * 32
    body = {"admin_user": "admin", "exp": int(time.time()) - 10}
    payload = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(key, payload, hashlib.sha256).digest()
    token = (
        base64.urlsafe_b64encode(payload).decode("ascii")
        + "."
        + base64.urlsafe_b64encode(sig).decode("ascii")
    )
    assert decode_session(token, key) is None

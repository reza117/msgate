"""Admin password hashing (stdlib scrypt)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_MIN_LEN = 8
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(plain: str) -> str:
    if len(plain) < _MIN_LEN:
        raise ValueError(f"Password must be at least {_MIN_LEN} characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        plain.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        algo, n, r, p, salt_hex, digest_hex = password_hash.split("$")
        if algo != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            plain.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

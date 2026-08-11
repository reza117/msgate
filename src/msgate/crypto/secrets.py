"""AES-256-GCM encryption for secrets at rest."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from msgate.logging_setup import get_logger
from msgate.paths import secret_key_path

log = get_logger("crypto")


class SecretBox:
    """Encrypt/decrypt strings with AES-256-GCM (key derived via SHA-256)."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("secret key must be 32 bytes")
        self._key = key
        self._aes = AESGCM(key)

    def derive_key(self, context: str) -> bytes:
        return hashlib.sha256(self._key + context.encode("utf-8")).digest()

    @classmethod
    def from_passphrase(cls, passphrase: str) -> SecretBox:
        digest = hashlib.sha256(passphrase.encode("utf-8")).digest()
        return cls(digest)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        nonce = secrets.token_bytes(12)
        ciphertext = self._aes.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        nonce, ciphertext = raw[:12], raw[12:]
        return self._aes.decrypt(nonce, ciphertext, None).decode("utf-8")


def resolve_secret_box(
    env_key: str | None = None,
    key_path: Path | None = None,
) -> SecretBox:
    """Load key from env, file, or generate a persistent dev key."""
    # Empty MSGATE_SECRET_KEY= in env files must not block file/auto key.
    if env_key and env_key.strip():
        return SecretBox.from_passphrase(env_key.strip())

    path = key_path or secret_key_path()
    if path.is_file():
        phrase = path.read_text(encoding="utf-8").strip()
        return SecretBox.from_passphrase(phrase)

    phrase = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(phrase + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    log.warning("Generated MSGATE secret key at %s (set MSGATE_SECRET_KEY in production)", path)
    return SecretBox.from_passphrase(phrase)

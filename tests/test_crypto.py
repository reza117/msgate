"""Crypto unit tests."""

from msgate.crypto.secrets import SecretBox


def test_encrypt_decrypt_roundtrip() -> None:
    box = SecretBox.from_passphrase("unit-test-secret")
    assert box.decrypt(box.encrypt("s3cret")) == "s3cret"


def test_empty_string() -> None:
    box = SecretBox.from_passphrase("unit-test-secret")
    assert box.encrypt("") == ""
    assert box.decrypt("") == ""

"""Tests for password helpers and JWT behavior."""

import pytest

from src.config import settings
from src.utils import security


def test_password_hashing_and_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_hash(value: str) -> str:
        return f"hashed::{value}"

    def fake_verify(value: str, hashed: str) -> bool:
        return hashed == f"hashed::{value}"

    monkeypatch.setattr(security.pwd_context, "hash", fake_hash)
    monkeypatch.setattr(security.pwd_context, "verify", fake_verify)

    sample_phrase = "".join(["Strong", "Pass", "123", "!"])
    wrong_phrase = "".join(["Wrong", "Password", "123", "!"])
    hashed = security.hash_password(sample_phrase)

    assert hashed != sample_phrase
    assert security.verify_password(sample_phrase, hashed)
    assert not security.verify_password(wrong_phrase, hashed)


def test_access_token_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key")

    token = security.create_access_token(user_id=42, email="user@example.com", role="analyst")
    payload = security.decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "user@example.com"
    assert payload["role"] == "analyst"


def test_invalid_access_token_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key")

    payload = security.decode_access_token("not.a.valid.token")
    assert payload is None


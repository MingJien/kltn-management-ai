"""Hash local account passwords using the project Argon2id policy."""

from __future__ import annotations

import secrets
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 1024:
        raise ValueError("Password must contain 12 to 1024 characters")
    return _hasher.hash(password)


def unusable_password() -> str:
    """Unique placeholder for an account that cannot sign in before activation."""
    return "!" + secrets.token_urlsafe(48)


def verify_password(stored_hash: str | None, password: str) -> bool:
    if not stored_hash:
        return False
    try:
        return _hasher.verify(stored_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)

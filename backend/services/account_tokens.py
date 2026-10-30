"""Short-lived, one-use links tied to the account credential version."""

from __future__ import annotations

import os
from uuid import UUID

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.db.models.entities import UserAccount


def _signer() -> URLSafeTimedSerializer:
    secret = os.getenv("AUTH_SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("AUTH_SESSION_SECRET must be a stable secret of at least 32 characters")
    return URLSafeTimedSerializer(secret, salt="kltn-account-link-v1")


def make_token(user: UserAccount, purpose: str) -> str:
    if purpose not in {"activate", "reset"} or not user.email:
        raise ValueError("Invalid account link purpose")
    return _signer().dumps({
        "id": str(user.id), "email": user.email, "version": user.row_version,
        "purpose": purpose,
    })


def token_account(token: str, purpose: str) -> tuple[UUID, str, int] | None:
    if len(token) > 2048:
        return None
    try:
        data = _signer().loads(token, max_age=1800 if purpose == "reset" else 86400)
        if data.get("purpose") != purpose or not isinstance(data.get("version"), int):
            return None
        email = data.get("email")
        if not isinstance(email, str) or not email or len(email) > 255:
            return None
        return UUID(data["id"]), email, data["version"]
    except (BadSignature, SignatureExpired, ValueError, TypeError, KeyError, AttributeError):
        return None

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Iterator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import APIKeyCookie, APIKeyHeader
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.db.models.entities import UserAccount

_session_cookie_auth = APIKeyCookie(name="kltn_session", auto_error=False)
_dev_header_auth = APIKeyHeader(name="X-Dev-User-Id", description="Chỉ DEV/TEST", auto_error=False)

def load_local_env() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_local_env()

_engine = None


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL must be configured")
    return value


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True)
    return _engine


def get_session() -> Iterator[Session]:
    with sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session


def current_user(
    request: Request,
    session: Session = Depends(get_session),
    dev_user_id: str | None = Header(default=None, alias="X-Dev-User-Id"),
    _session_cookie: str | None = Security(_session_cookie_auth),
    _dev_header: str | None = Security(_dev_header_auth),
) -> UserAccount:
    session_user_id = request.session.get("user_id") if "session" in request.scope else None
    if session_user_id:
        from backend.api.auth import _same_app_origin
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not _same_app_origin(request):
            raise HTTPException(403, "Request origin is not allowed")
        try:
            user_id = UUID(session_user_id)
        except (TypeError, ValueError):
            request.session.clear()
            raise HTTPException(401, "Invalid sign-in session")
    elif os.getenv("KLTN_ENV") in {"development", "test"} and os.getenv("KLTN_DEV_AUTH") == "true":
        if dev_user_id is None:
            raise HTTPException(401, "Missing development identity")
        try:
            user_id = UUID(dev_user_id)
        except (TypeError, ValueError):
            raise HTTPException(401, "Invalid development identity")
    else:
        raise HTTPException(401, "Sign in required")
    user = session.scalar(select(UserAccount).where(UserAccount.id == user_id, UserAccount.status == "ACTIVE"))
    if user is None:
        if session_user_id:
            request.session.clear()
        raise HTTPException(401, "Unknown or inactive identity")
    credential_version = request.session.get("credential_version") if session_user_id else None
    if credential_version is not None and credential_version != user.row_version:
        request.session.clear()
        raise HTTPException(401, "Sign-in session has expired")
    return user

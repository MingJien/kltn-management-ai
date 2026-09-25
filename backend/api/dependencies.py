from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Iterator
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.db.models.entities import UserAccount

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
    session: Session = Depends(get_session),
    dev_user_id: UUID | None = Header(default=None, alias="X-Dev-User-Id"),
) -> UserAccount:
    if os.getenv("KLTN_ENV") not in {"development", "test"} or os.getenv("KLTN_DEV_AUTH") != "true":
        raise HTTPException(503, "SSO is not configured; development identity is disabled")
    if dev_user_id is None:
        raise HTTPException(401, "Missing development identity")
    user = session.scalar(select(UserAccount).where(UserAccount.id == dev_user_id, UserAccount.status == "ACTIVE"))
    if user is None:
        raise HTTPException(401, "Unknown or inactive identity")
    return user

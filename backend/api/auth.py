from __future__ import annotations

import os
import threading
import time
from collections import deque
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.dependencies import get_session
from backend.db.models.entities import UserAccount
from backend.services.passwords import needs_rehash, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
_failed_logins: dict[str, deque[float]] = {}
_login_lock = threading.Lock()


class LocalLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


def _same_app_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True  # Command-line clients do not send Origin.
    configured = os.getenv("KLTN_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    allowed = {"http://localhost:5173", "http://127.0.0.1:5173", configured}
    return origin.rstrip("/") in allowed


def _throttle_key(request: Request, email: str) -> str:
    peer = request.client.host if request.client else "unknown"
    return f"{peer}:{email}"


def _login_throttled(key: str) -> bool:
    now = time.monotonic()
    with _login_lock:
        attempts = _failed_logins.setdefault(key, deque())
        while attempts and attempts[0] < now - 900:
            attempts.popleft()
        return len(attempts) >= 5


def _record_failure(key: str) -> None:
    with _login_lock:
        if len(_failed_logins) > 10_000:
            _failed_logins.clear()
        _failed_logins.setdefault(key, deque()).append(time.monotonic())


def _clear_failures(key: str) -> None:
    with _login_lock:
        _failed_logins.pop(key, None)


def oidc_is_configured() -> bool:
    required = (
        "OIDC_DISCOVERY_URL", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET",
        "OIDC_REDIRECT_URI", "AUTH_SESSION_SECRET",
    )
    return all(os.getenv(name, "").strip() for name in required) and len(os.getenv("AUTH_SESSION_SECRET", "")) >= 32


def development_auth_is_enabled() -> bool:
    return os.getenv("KLTN_ENV") in {"development", "test"} and os.getenv("KLTN_DEV_AUTH") == "true"


def authentication_mode() -> str:
    if oidc_is_configured():
        return "university_oidc"
    if len(os.getenv("AUTH_SESSION_SECRET", "")) >= 32 or os.getenv("KLTN_ENV") in {"development", "test"}:
        return "local_email"
    if development_auth_is_enabled():
        return "development"
    return "unavailable"


def _oidc_client():
    if not oidc_is_configured():
        raise HTTPException(503, "University OIDC is not configured")
    try:
        from authlib.integrations.starlette_client import OAuth
    except ImportError as exc:
        raise HTTPException(503, "Install the optional SSO dependencies to enable University OIDC") from exc

    oauth = OAuth()
    kwargs = {
        "client_id": os.environ["OIDC_CLIENT_ID"],
        "client_secret": os.environ["OIDC_CLIENT_SECRET"],
        "server_metadata_url": os.environ["OIDC_DISCOVERY_URL"],
        "token_endpoint_auth_method": os.getenv("OIDC_TOKEN_ENDPOINT_AUTH_METHOD", "client_secret_basic"),
        "client_kwargs": {"scope": os.getenv("OIDC_SCOPE", "openid")},
    }
    oauth.register("university", **kwargs)
    return oauth.university


@router.get("/config")
def auth_config() -> dict[str, str]:
    return {"mode": authentication_mode()}


@router.post("/login", status_code=204)
def local_login(payload: LocalLogin, request: Request, session: Session = Depends(get_session)) -> None:
    if "session" not in request.scope:
        raise HTTPException(503, "Session support is not configured")
    if os.getenv("KLTN_ENV") not in {"development", "test"} and len(os.getenv("AUTH_SESSION_SECRET", "")) < 32:
        raise HTTPException(503, "Sign-in configuration is incomplete")
    if not _same_app_origin(request):
        raise HTTPException(403, "Request origin is not allowed")
    email = payload.email.strip().lower()
    key = _throttle_key(request, email)
    if _login_throttled(key):
        raise HTTPException(429, "Too many sign-in attempts; try again later")
    user = session.scalar(select(UserAccount).where(func.lower(UserAccount.email) == email))
    if not user or not verify_password(user.password_hash, payload.password) or user.status != "ACTIVE" or user.email_verified_at is None:
        _record_failure(key)
        raise HTTPException(401, "Email or password is incorrect, or the account is unavailable")
    _clear_failures(key)
    request.session.clear()
    request.session["user_id"] = str(user.id)
    request.session["credential_version"] = user.row_version
    if needs_rehash(user.password_hash):
        from backend.services.passwords import hash_password
        user.password_hash = hash_password(payload.password)
        user.row_version += 1
        request.session["credential_version"] = user.row_version
        session.commit()


@router.get("/login")
async def login(request: Request):
    client = _oidc_client()
    request.session.clear()
    return await client.authorize_redirect(request, os.environ["OIDC_REDIRECT_URI"])


@router.get("/callback")
async def callback(request: Request, session: Session = Depends(get_session)):
    client = _oidc_client()
    try:
        token = await client.authorize_access_token(request)
    except Exception:
        request.session.clear()
        return JSONResponse({"detail": "University sign-in could not be verified"}, status_code=401)

    claims = token.get("userinfo")
    subject = claims.get("sub") if isinstance(claims, Mapping) else None
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        request.session.clear()
        return JSONResponse({"detail": "The identity provider returned no usable subject"}, status_code=401)

    user = session.scalar(select(UserAccount).where(
        UserAccount.external_subject == subject,
        UserAccount.status == "ACTIVE",
    ))
    if user is None:
        request.session.clear()
        return JSONResponse({"detail": "This University account has not been linked to an active KLTN account"}, status_code=403)

    request.session.clear()
    request.session["user_id"] = str(user.id)
    frontend_url = os.getenv("KLTN_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return RedirectResponse(f"{frontend_url}/?login=success", status_code=303)


@router.post("/logout", status_code=204)
def logout(request: Request) -> None:
    request.session.clear()

from __future__ import annotations

import os
import ipaddress
import secrets
import threading
import time
from collections import deque
from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.api.dependencies import get_session
from backend.db.models.entities import AuditEvent, LecturerProfile, StudentProfile, UserAccount
from backend.services.account_mail import frontend_origin
from backend.services.passwords import needs_rehash, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
_failed_logins: dict[str, deque[float]] = {}
_login_lock = threading.Lock()


def _access_audit(session, user, action):
    session.add(AuditEvent(id=uuid4(), actor_id=user.id, action=action,
        resource_type="user_account", resource_id=user.id,
        occurred_at=datetime.now(timezone.utc), correlation_id=uuid4()))
    session.commit()


class LocalLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class DemoLogin(BaseModel):
    key: str = Field(min_length=1, max_length=41)

    @field_validator("key")
    @classmethod
    def valid_key(cls, value: str) -> str:
        if value in _DEMO_ACCOUNTS:
            return value
        try:
            UUID(value)
        except ValueError:
            raise ValueError("Invalid demo account") from None
        return value


_DEMO_ACCOUNTS = {
    "sv1": ("synthetic-demo-student-1", "sv1@demo.test", "STUDENT", "Sinh viên demo 1"),
    "sv2": ("synthetic-demo-student-2", "sv2@demo.test", "STUDENT", "Sinh viên demo 2"),
    "sv3": ("synthetic-demo-student-3", "sv3@demo.test", "STUDENT", "Sinh viên demo 3"),
    "gv": ("synthetic-demo-lecturer-1", "gv@demo.test", "LECTURER", "Giảng viên demo"),
    "tbm": ("synthetic-demo-lecturer-2", "tbm@demo.test", "LECTURER", "Trưởng bộ môn demo"),
    "gv2": ("synthetic-demo-lecturer-3", "gv2@demo.test", "LECTURER", "Giảng viên demo 2"),
}


def _require_local_demo(request: Request) -> None:
    if os.getenv("KLTN_ENV") != "development" or os.getenv("KLTN_DEMO_MODE") != "true":
        raise HTTPException(404, "Demo mode is unavailable")
    try:
        if not request.client or not ipaddress.ip_address(request.client.host).is_loopback:
            raise HTTPException(404, "Demo mode is unavailable")
    except ValueError:
        raise HTTPException(404, "Demo mode is unavailable") from None
    if not _same_app_origin(request):
        raise HTTPException(403, "Request origin is not allowed")


def _demo_user(session: Session, key: str) -> UserAccount | None:
    conditions = [UserAccount.status == "ACTIVE", UserAccount.email_verified_at.is_not(None), UserAccount.email.is_not(None)]
    if key in _DEMO_ACCOUNTS:
        subject, email, role, _ = _DEMO_ACCOUNTS[key]
        conditions.extend([UserAccount.external_subject == subject, UserAccount.email == email, UserAccount.base_role == role])
    else:
        try:
            identifier = UUID(key)
        except ValueError:
            return None
        conditions.extend([UserAccount.id == identifier,
            or_(func.lower(UserAccount.email).like("%@demo.test"),
                select(StudentProfile.id).where(StudentProfile.user_id == UserAccount.id, StudentProfile.student_code.like("SYN-DEMO-%")).exists(),
                select(LecturerProfile.id).where(LecturerProfile.user_id == UserAccount.id, LecturerProfile.lecturer_code.like("SYN-DEMO-%")).exists()),
            or_(and_(UserAccount.base_role == "STUDENT", select(StudentProfile.id).where(StudentProfile.user_id == UserAccount.id).exists()),
                and_(UserAccount.base_role == "LECTURER", select(LecturerProfile.id).where(LecturerProfile.user_id == UserAccount.id).exists()))])
    return session.scalar(select(UserAccount).where(*conditions))


def allowed_frontend_origins() -> list[str]:
    configured = os.getenv("KLTN_FRONTEND_URL", "").strip().rstrip("/")
    if os.getenv("KLTN_ENV") == "production":
        return [configured] if configured else []
    return list(dict.fromkeys(origin for origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:1573",
        "http://127.0.0.1:1573",
        configured,
    ) if origin))


def _same_app_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        # Browser writes provide Origin. Allow origin-less local test/CLI requests only.
        return os.getenv("KLTN_ENV") in {"development", "test"}
    return origin in allowed_frontend_origins()


def require_csrf(request: Request) -> None:
    expected = request.session.get("csrf_token")
    provided = request.headers.get("x-csrf-token", "")
    if not isinstance(expected, str) or not secrets.compare_digest(expected, provided):
        raise HTTPException(403, "Request verification failed")


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
    return os.getenv("KLTN_ENV") == "test" and os.getenv("KLTN_DEV_AUTH") == "true"


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


@router.get("/demo-accounts")
def demo_accounts(request: Request, session: Session = Depends(get_session)) -> list[dict[str, str]]:
    _require_local_demo(request)
    accounts = [
        {"key": key, "email": email, "role": role, "label": label}
        for key, (_, email, role, label) in _DEMO_ACCOUNTS.items()
        if _demo_user(session, key) is not None
    ]
    known_emails = {item["email"].lower() for item in accounts}
    rows = session.execute(select(UserAccount, StudentProfile, LecturerProfile)
        .outerjoin(StudentProfile, StudentProfile.user_id == UserAccount.id)
        .outerjoin(LecturerProfile, LecturerProfile.user_id == UserAccount.id)
        .where(UserAccount.status == "ACTIVE", UserAccount.email_verified_at.is_not(None), UserAccount.email.is_not(None),
            UserAccount.base_role.in_(["STUDENT", "LECTURER"]),
            or_(func.lower(UserAccount.email).like("%@demo.test"), StudentProfile.student_code.like("SYN-DEMO-%"),
                LecturerProfile.lecturer_code.like("SYN-DEMO-%")))
        .order_by(UserAccount.base_role, UserAccount.email)).all()
    for user, student, lecturer in rows:
        profile = student if user.base_role == "STUDENT" else lecturer
        if not profile or user.email.lower() in known_emails:
            continue
        code = student.student_code if student else lecturer.lecturer_code
        accounts.append({"key": str(user.id), "email": user.email, "role": user.base_role,
            "label": f"{'SV' if student else 'GV'} · {profile.display_name} · {code}"})
    return accounts


@router.post("/demo-login", status_code=204)
def demo_login(payload: DemoLogin, request: Request, session: Session = Depends(get_session)) -> None:
    _require_local_demo(request)
    if "session" not in request.scope:
        raise HTTPException(503, "Session support is not configured")
    user = _demo_user(session, payload.key)
    if user is None:
        raise HTTPException(404, "Demo account is unavailable")
    _access_audit(session, user, "ACCOUNT_SIGNED_IN")
    request.session.clear()
    request.session["user_id"] = str(user.id)
    request.session["credential_version"] = user.row_version
    request.session["csrf_token"] = secrets.token_urlsafe(32)


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
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    if needs_rehash(user.password_hash):
        from backend.services.passwords import hash_password
        user.password_hash = hash_password(payload.password)
        user.row_version += 1
        request.session["credential_version"] = user.row_version
    _access_audit(session, user, "ACCOUNT_SIGNED_IN")


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

    _access_audit(session, user, "ACCOUNT_SIGNED_IN")
    request.session.clear()
    request.session["user_id"] = str(user.id)
    request.session["credential_version"] = user.row_version
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    frontend_url = frontend_origin()
    return RedirectResponse(f"{frontend_url}/?login=success", status_code=303)


@router.post("/logout", status_code=204)
def logout(request: Request, session: Session = Depends(get_session)) -> None:
    if not _same_app_origin(request):
        raise HTTPException(403, "Request origin is not allowed")
    if request.session.get("user_id"):
        require_csrf(request)
        try:
            user = session.get(UserAccount, UUID(request.session["user_id"]))
        except (ValueError, TypeError):
            user = None
        if user and user.row_version == request.session.get("credential_version"):
            _access_audit(session, user, "ACCOUNT_SIGNED_OUT")
    request.session.clear()

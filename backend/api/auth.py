from __future__ import annotations

import os
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.dependencies import get_session
from backend.db.models.entities import UserAccount

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


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

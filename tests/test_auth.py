from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.api.auth import allowed_frontend_origins, authentication_mode, oidc_is_configured
from backend.api import auth
from backend.api.dependencies import current_user


class FakeSession:
    def __init__(self, user):
        self.user = user

    def scalar(self, _statement):
        return self.user


def request_with_session(user_id: str | None = None) -> Request:
    scope = {"type": "http", "headers": [], "method": "GET", "path": "/", "query_string": b"", "session": {}}
    if user_id is not None:
        scope["session"] = {"user_id": user_id, "credential_version": 1, "csrf_token": "test-csrf-token"}
    return Request(scope)


def test_auth_mode_requires_complete_oidc_and_session_config(monkeypatch):
    for key in ("OIDC_DISCOVERY_URL", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET", "OIDC_REDIRECT_URI", "AUTH_SESSION_SECRET"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("KLTN_ENV", "production")
    monkeypatch.setenv("KLTN_DEV_AUTH", "true")
    assert not oidc_is_configured()
    assert authentication_mode() == "unavailable"

    monkeypatch.setenv("KLTN_ENV", "test")
    assert authentication_mode() == "local_email"

    monkeypatch.setenv("OIDC_DISCOVERY_URL", "https://identity.example/.well-known/openid-configuration")
    monkeypatch.setenv("OIDC_CLIENT_ID", "test-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://app.example/api/v1/auth/callback")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "test-only-secret-that-is-at-least-32-characters")
    assert authentication_mode() == "university_oidc"


def test_production_cors_uses_only_the_configured_frontend(monkeypatch):
    monkeypatch.setenv("KLTN_ENV", "production")
    monkeypatch.setenv("KLTN_FRONTEND_URL", "https://kltn.example/")
    assert allowed_frontend_origins() == ["https://kltn.example"]
    assert not auth._same_app_origin(request_with_session())


def test_oidc_session_maps_to_internal_account(monkeypatch):
    user_id = uuid4()
    user = SimpleNamespace(row_version=1)
    monkeypatch.setenv("KLTN_ENV", "production")
    monkeypatch.setenv("KLTN_DEV_AUTH", "false")
    result = current_user(request_with_session(str(user_id)), FakeSession(user), dev_user_id=None)
    assert result is user


def test_production_ignores_development_uuid_header(monkeypatch):
    monkeypatch.setenv("KLTN_ENV", "production")
    monkeypatch.setenv("KLTN_DEV_AUTH", "true")
    monkeypatch.setenv("OIDC_DISCOVERY_URL", "https://identity.example/.well-known/openid-configuration")
    monkeypatch.setenv("OIDC_CLIENT_ID", "test-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://app.example/api/v1/auth/callback")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "test-only-secret-that-is-at-least-32-characters")
    with pytest.raises(HTTPException) as error:
        current_user(request_with_session(), FakeSession(object()), dev_user_id=str(uuid4()))
    assert error.value.status_code == 401


def test_development_uuid_header_remains_test_only(monkeypatch):
    user = object()
    monkeypatch.setenv("KLTN_ENV", "test")
    monkeypatch.setenv("KLTN_DEV_AUTH", "true")
    assert current_user(request_with_session(), FakeSession(user), dev_user_id=str(uuid4())) is user


class FakeOIDCClient:
    async def authorize_access_token(self, _request):
        return {"userinfo": {"sub": "university-subject-42"}}


def test_oidc_callback_links_only_an_existing_account(monkeypatch):
    account = SimpleNamespace(id=uuid4(), row_version=1)
    monkeypatch.setattr(auth, "_oidc_client", FakeOIDCClient)
    monkeypatch.setenv("KLTN_FRONTEND_URL", "https://kltn.example")
    request = request_with_session()
    response = asyncio.run(auth.callback(request, FakeSession(account)))
    assert response.status_code == 303
    assert response.headers["location"] == "https://kltn.example/?login=success"
    assert request.session["user_id"] == str(account.id)
    assert request.session["credential_version"] == 1
    assert request.session["csrf_token"]


def test_oidc_callback_refuses_unlinked_account(monkeypatch):
    monkeypatch.setattr(auth, "_oidc_client", FakeOIDCClient)
    request = request_with_session()
    response = asyncio.run(auth.callback(request, FakeSession(None)))
    assert response.status_code == 403
    assert request.session == {}

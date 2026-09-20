"""Tests for the local email/password signup + forgot-password flows.

These exercise /api/v1/auth/{signup,verify-otp,forgot-password,reset-password}
without a live Postgres/SMTP by monkeypatching the ``local_auth`` service layer,
mirroring how test_api_e2e.py fakes get_db() for the upload routes.

The JWT/OTP helpers (otp.py) are exercised directly so we also cover the token
contract: signup/forgot-password issue an OTP JWT, and verify/reset decode it.
"""

import pytest
from fastapi.testclient import TestClient

import routes.auth  # noqa: F401 - imported so monkeypatch can patch its service funcs
from main import app


# Shared client for all tests (mirrors test_api_e2e.py).
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_dependency_overrides():
    """Isolate dependency_overrides between tests (TestClient state leaks)."""

    original = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original)


def _service():
    import routes.auth

    return routes.auth.local_auth  # the service module, patched via monkeypatch


def test_signup_requires_email_and_password():
    """Missing fields → 422 (pydantic validation before any service call)."""

    resp = client.post("/api/v1/auth/signup")
    assert resp.status_code == 422


def test_signup_returns_otp_sent(monkeypatch):
    """A valid signup returns 202 and hands back an OTP JWT + email."""

    from services.otp import decode_otp_token, issue_otp_token
    from services.local_auth import AuthError

    async def fake_signup(email, password, name=None):
        token = issue_otp_token(email.lower().strip(), "signup_verify")
        return {"status": "otp_sent", "email": email.lower().strip(), "token": token}

    monkeypatch.setattr(routes.auth, "local_signup", fake_signup)

    resp = client.post(
        "/api/v1/auth/signup", json={"email": "Alice@Example.com", "password": "supersecret"}
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "otp_sent"
    # Email is normalised to lowercase.
    assert body["email"] == "alice@example.com"

    # The token is a signed JWT carrying the email + signup_verify action.
    claims = decode_otp_token(body["token"])
    assert claims is not None
    assert claims["_email"] == "alice@example.com"
    assert claims["_action"] == "signup_verify"


def test_signup_rejects_short_password(monkeypatch):
    """A password under 8 chars is rejected by the service as a 400."""

    from services.local_auth import AuthError

    async def fake_signup(email, password, name=None):
        raise AuthError("Password must be at least 8 characters.", 400)

    monkeypatch.setattr(routes.auth, "local_signup", fake_signup)

    resp = client.post("/api/v1/auth/signup", json={"email": "a@b.co", "password": "short"})
    assert resp.status_code == 400


def test_signup_conflict_returns_409(monkeypatch):
    """A duplicate email surfaces as a 409 Conflict."""

    from services.local_auth import AuthError

    async def fake_signup(email, password, name=None):
        raise AuthError("An account with this email already exists.", 409)

    monkeypatch.setattr(routes.auth, "local_signup", fake_signup)

    resp = client.post(
        "/api/v1/auth/signup", json={"email": "dup@example.com", "password": "supersecret"}
    )
    assert resp.status_code == 409


def test_verify_otp_delegates_to_service(monkeypatch):
    """verify-otp forwards token+otp to the service and returns its result."""

    expected = {"token": "access", "user": {"email": "alice@example.com"}}

    async def fake_verify(token, otp):
        return expected

    monkeypatch.setattr(routes.auth, "verify_otp", fake_verify)

    resp = client.post(
        "/api/v1/auth/verify-otp", json={"token": "jwt", "otp": "123456"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"] == "access"
    assert body["user"]["email"] == "alice@example.com"


def test_verify_otp_requires_body():
    """Missing fields → 422."""

    resp = client.post("/api/v1/auth/verify-otp")
    assert resp.status_code == 422


def test_forgot_password_returns_otp_sent(monkeypatch):
    """forgot-password returns 202 with a generic response + OTP JWT."""

    from services.otp import decode_otp_token, issue_otp_token

    async def fake_forgot(email):
        token = issue_otp_token(email.lower().strip(), "password_reset")
        return {"status": "otp_sent", "email": email.lower().strip(), "token": token}

    monkeypatch.setattr(routes.auth, "forgot_password", fake_forgot)

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "Alice@Example.com"})
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "otp_sent"

    claims = decode_otp_token(body["token"])
    assert claims is not None
    assert claims["_email"] == "alice@example.com"
    assert claims["_action"] == "password_reset"


def test_forgot_password_generic_on_missing_email(monkeypatch):
    """A missing email is answered generically (never reveals account existence)."""

    from services.local_auth import AuthError

    async def fake_forgot(email):
        raise AuthError("If that account exists, a reset code was sent.", 400)

    monkeypatch.setattr(routes.auth, "forgot_password", fake_forgot)

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert resp.status_code == 400


def test_reset_password_delegates_to_service(monkeypatch):
    """reset-password forwards token+otp+new password to the service."""

    expected = {"token": "access", "user": {"email": "alice@example.com"}}

    async def fake_reset(token, otp, new_password):
        return expected

    monkeypatch.setattr(routes.auth, "reset_password", fake_reset)

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "jwt", "otp": "654321", "new_password": "brand-new-pass"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"] == "access"


def test_reset_password_requires_new_password():
    """Missing new_password → 422."""

    resp = client.post(
        "/api/v1/auth/reset-password", json={"token": "jwt", "otp": "123456"}
    )
    assert resp.status_code == 422

"""Auth routes — Keycloak OIDC + local email/password flows.

Two auth mechanisms coexist:

1. **Keycloak hosted login** (existing, Phase 0.x). The web UI redirects to
   Keycloak for sign-in; on return we redeem the authorization code server-side.

2. **Local email/password signup + forgot-password** (Phase 0.4/0.5). These use a
   self-contained bcrypt credential store and short-lived 6-digit OTP codes, so
   they work without the shared Keycloak realm. This backs the signup and
   forgot-password/reset pages ported from iacgenie.

All endpoints are prefixed ``/api/v1`` to match the web UI client (see
`webui/src/lib/api.ts`). Never leak secrets in responses.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from services.auth import get_user_from_token
from services.keycloak import auth_url, exchange_code_for_token, kc_config
from services.local_auth import AuthError as LocalAuthError
from services.local_auth import (
    forgot_password,
    reset_password,
    signup as local_signup,
    verify_otp,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Keycloak hosted-login callback (existing) ─────────────────────────────

def _redirect_uri() -> str:
    """The web UI callback URL Keycloak must redirect to after a flow."""

    return os.getenv("AUTH_CALLBACK_REDIRECT_URI", "/auth/callback")


class ExchangeRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


class ConfigResponse(BaseModel):
    kcUrl: str
    realm: str
    clientId: str


class AuthUrlResponse(BaseModel):
    """Return a Keycloak hosted-flow URL (register / forgot-password)."""

    url: str


@router.get("/config", response_model=ConfigResponse)
async def auth_config():
    """Public Keycloak connection info for the frontend (no secrets)."""

    cfg = kc_config()
    return ConfigResponse(kcUrl=cfg["kcUrl"], realm=cfg["realm"], clientId=cfg["clientId"])


@router.post("/auth-url", response_model=AuthUrlResponse)
async def auth_url_endpoint(action: str | None = "register"):
    """Return a Keycloak hosted-registration or forgot-password redirect URL.

    ``action`` selects the flow: ``register`` (signup) or ``forgotPassword``.
    These are Keycloak-hosted pages, so the web UI simply navigates to this URL.
    Defaults to registration (used by 0.4).
    """

    return AuthUrlResponse(url=auth_url(action))


@router.post("/exchange", response_model=dict)
async def exchange(request: ExchangeRequest):
    """Exchange a Keycloak authorization code for tokens (server-side).

    The web UI receives the ``code`` after Keycloak's hosted login/signup/forgot
    password flow redirects back here. Redeeming the code server-side keeps the
    confidential client secret out of the browser.

    Returns ``{"token": ..., "user": {...}}`` on success, or a 401 with
    ``{"error": "..."}`` if the exchange fails.
    """

    redirect_uri = request.redirect_uri or _redirect_uri()

    user_info = await exchange_code_for_token(request.code, redirect_uri)
    if not user_info:
        raise HTTPException(
            status_code=401, detail="Authentication failed. Please try signing in again."
        )

    return {"token": user_info.get("sub", ""), "user": user_info}


# ── Local email/password signup + forgot-password (Phase 0.4/0.5) ─────────


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class VerifyOtpRequest(BaseModel):
    token: str  # JWT issued alongside the OTP (carries email + action)
    otp: str  # 6-digit code delivered to the user's email


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str  # JWT issued alongside the OTP (carries email + action)
    otp: str  # 6-digit code delivered to the user's email
    new_password: str


@router.post("/signup", status_code=202)
async def signup(request: SignupRequest):
    """Create a local account; OTP verification is required to complete it.

    Returns 202 Accepted with a generic success message (never reveals whether
    the email exists). The account is created but unverified until verify-otp.
    """

    try:
        result = await local_signup(request.email, request.password, request.name)
    except LocalAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    # Generic response — do not reveal whether the email already exists.
    return {"status": "otp_sent", "email": result["email"], "token": result.get("token")}


@router.post("/verify-otp")
async def verify_otp_route(request: VerifyOtpRequest):
    """Complete signup OR validate a password-reset OTP.

    For ``action=signup_verify`` this returns the login response directly (the
    account is fully set up). For ``action=password_reset`` it only validates the
    code; a follow-up POST to /reset-password sets the new password.

    Raises 401/400 on invalid/expired/wrong codes.
    """

    result = await verify_otp(request.token, request.otp)
    return result


@router.post("/forgot-password", status_code=202)
async def forgot_password_route(request: ForgotPasswordRequest):
    """Issue a reset OTP for the given email.

    Returns 202 Accepted with a generic message (never reveals whether the email
    exists). The user then verifies via /reset-password.
    """

    try:
        result = await forgot_password(request.email)
    except LocalAuthError as e:
        # Generic — never reveal whether the email exists.
        raise HTTPException(
            status_code=e.status_code, detail=e.message
        ) from e

    return {"status": "otp_sent", "email": result["email"], "token": result.get("token")}


@router.post("/reset-password")
async def reset_password_route(request: ResetPasswordRequest):
    """Set a new password after verifying the OTP.

    Raises 401/400 on invalid/expired/wrong codes or weak new passwords.
    """

    try:
        result = await reset_password(
            request.token, request.otp, request.new_password
        )
    except LocalAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    return result


# ── Shared auth dependency (existing verify + n8n callback) ───────────────


async def require_auth(authorization: Optional[str] = Header(default="Bearer ")) -> dict:
    """Dependency: extract and validate Bearer token."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


@router.post("/verify", response_model=dict)
async def verify_token(user: dict = Depends(require_auth)):
    """Verify token and return user info."""

    return {"valid": True, "user": user}


@router.post("/n8n/callback", response_model=dict)
async def n8n_callback(x_api_key: Optional[str] = Header(...)):
    """Internal endpoint for n8n to push processing results."""

    API_SECRET = os.getenv("API_SECRET", "change-me-secret")
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return {"status": "ok", "message": "n8n callback accepted"}

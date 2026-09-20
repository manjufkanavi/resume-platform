"""Keycloak OIDC authentication service."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from jose import jwt

logger = logging.getLogger(__name__)

# ── Keycloak Configuration ─────────────────────────────────────────────

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "iacgenie")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "resume-platform")
KEYCLOAK_CLIENT_SECRET=os.getenv("KEYCLOAK_CLIENT_SECRET", "CHANGE_ME")
AUTH_WRAPPER_URL=os.getenv("AUTH_WRAPPER_URL", "http://iacgenie_auth_wrapper:9090")

# ── Token Validation ───────────────────────────────────────────────────

async def validate_token(token: str) -> dict[str, Any] | None:
    """Validate JWT token via auth-wrapper or Keycloak directly."""
    # Try auth-wrapper first (preferred)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{AUTH_WRAPPER_URL}/validate",
                json={"token": token},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Auth-wrapper validation failed: {e}")

    # Fallback: validate via Keycloak introspection
    return await _validate_via_keycloak(token)


async def _validate_via_keycloak(token: str) -> dict[str, Any] | None:
    """Validate token via Keycloak introspection endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect",
                data={
                    "token": token,
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "client_secret": KEYCLOAK_CLIENT_SECRET,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("active"):
                    return {
                        "sub": data.get("sub"),
                        "email": data.get("email"),
                        "name": data.get("preferred_username"),
                        "roles": data.get("roles", []),
                    }
    except Exception as e:
        logger.warning(f"Keycloak introspection failed: {e}")

    return None


async def get_user_from_token(token: str) -> dict[str, Any] | None:
    """Extract user info from token and return user dict.

    Tries the local login-JWT path first (used by the email/password signup and
    forgot-password flows), then falls back to Keycloak introspection for OIDC
    tokens. A token that matches neither returns ``None`` (unauthorized).
    """

    if _local_jwt_enabled():
        local = decode_login_token(token)
        if local:
            return local

    info = await validate_token(token)
    if not info:
        return None

    return {
        "keycloak_id": info.get("sub"),
        "email": info.get("email"),
        "name": info.get("name"),
    }


def _local_jwt_enabled() -> bool:
    """Whether the local email/password credential store is active.

    Enabled when a non-default AUTH_JWT_SECRET is configured, so the local JWT
    path stays off by default and never touches Keycloak's secret store.
    """

    from services import otp as _otp  # local import avoids a circular load cost

    return bool(_otp.JWT_SECRET and _otp.JWT_SECRET != "change-me-local-jwt-secret")


def decode_login_token(token: str) -> dict[str, Any] | None:
    """Decode a local login (access) token. Returns user claims or ``None``."""

    from services import otp as _otp  # local import avoids a circular load cost

    return _otp.decode_login_token(token)


def get_auth_wrapper_url() -> str:
    """Get the auth-wrapper URL for redirect-based auth."""
    return AUTH_WRAPPER_URL

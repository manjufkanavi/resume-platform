"""Local JWT + OTP helpers for the resume platform auth flow.

These back a self-contained email/password credential store (independent of
Keycloak) so signup and forgot-password work without the shared Keycloak realm.

* OTP codes are 6-digit numeric strings, short-lived (10 min by default).
* The "OTP token" handed to the frontend is a signed JWT carrying only enough
  info to look up and validate an OTP code (email + action). It is NOT a login
  token — the user must still enter the correct OTP before being logged in.

Configuration via env vars (see services/otp.py top for defaults).
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

try:  # PyJWT (pip install pyjwt)
    import jwt
except Exception:  # pragma: no cover - fallback to jose if present
    from jose import jwt

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "change-me-local-jwt-secret-32bytes-min")
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_EXPIRATION_MINUTES = int(os.getenv("OTP_EXPIRATION_MINUTES", "10"))
JWT_DEFAULT_LIFETIME_SECONDS = int(os.getenv("AUTH_JWT_TTL", "3600"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate_otp_code(length: int = OTP_LENGTH) -> str:
    """Return a cryptographically-random numeric OTP code."""

    digits = "".join(secrets.choice("0123456789") for _ in range(length))
    # Ensure it isn't all zeros.
    while set(digits) == {"0"}:
        digits = "".join(secrets.choice("0123456789") for _ in range(length))
    return digits


def issue_otp_token(email: str, action: str) -> str:
    """Issue a short-lived JWT that references an OTP code + action.

    ``action`` is one of "signup_verify" or "password_reset".
    """

    payload = {
        "sub": email.lower().strip(),
        "act": action,
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(minutes=OTP_EXPIRATION_MINUTES)).timestamp()),
        "jti": secrets.token_urlsafe(8),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_otp_token(token: str) -> dict | None:
    """Decode + validate an OTP token. Returns the claims or ``None``."""

    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False}
        )
    except Exception:  # invalid/expired/malformed token
        return None

    action = payload.get("act")
    email = payload.get("sub")
    if not action or not email:
        return None

    # Sanity-guard the allowed actions so a stray token can't be reused.
    if action not in ("signup_verify", "password_reset"):
        return None

    payload["_action"] = action
    payload["_email"] = email.lower().strip()
    return payload


def issue_login_token(user: dict) -> str:
    """Issue the long-lived access token handed back to a logged-in user."""

    payload = {
        "sub": str(user.get("email", "")),
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(seconds=JWT_DEFAULT_LIFETIME_SECONDS)).timestamp()),
        "jti": secrets.token_urlsafe(8),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_login_token(token: str) -> dict | None:
    """Decode a login (access) token. Returns the user claims or ``None``."""

    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False}
        )
    except Exception:
        return None

    email = payload.get("sub")
    if not email:
        return None

    return {
        "keycloak_id": f"local:{email}",  # namespace local users distinctly
        "email": email,
        "name": payload.get("name", ""),
    }


def _now_ts() -> int:  # pragma: no cover - unused helper, kept for symmetry
    return int(_now().timestamp())


def _seconds_until_expiry(minutes: int = OTP_EXPIRATION_MINUTES) -> float:  # pragma: no cover
    return minutes * 60

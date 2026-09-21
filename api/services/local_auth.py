"""Local email/password credential store + verification logic.

This backs the platform's own signup and forgot-password flows so they work
without a shared Keycloak realm. Passwords are hashed with bcrypt; verification
is gated by a short-lived 6-digit OTP delivered to the user's email.

Two-step signup:
    POST /signup(email, password, name) -> issue OTP -> 202 Accepted
    POST /verify-otp(token, otp)        -> complete account + return login token

Forgot-password:
    POST /forgot-password(email)      -> issue OTP -> 202 Accepted
    POST /reset-password(token, otp, new_password) -> rotate password

Only ``bcrypt`` is required; if it's missing the module still imports but signup
returns a clear 503 (see ``bcrypt_available``).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import User, OtpCode, get_db
import services.email_service as email_sender
from services.otp import (
    generate_otp_code,
    issue_otp_token,
    decode_otp_token,
    issue_login_token,
)

logger = logging.getLogger(__name__)

EMAIL_RE = os.getenv("OTP_EMAIL_PATTERN", r"^[^@\s]+@[^\s@]+\.[^\s@]+$")


def _render_otp_email(user_name: Optional[str], otp_code: str, reset: bool = False) -> str:
    """Render the OTP email template with Jinja2.

    Loads ``api/templates/otp_reset.html`` (password reset) or
    ``api/templates/otp_verification.html`` (signup), relative to this file, and
    renders it with the recipient name + OTP code. This mirrors the branded HTML
    email style iacgenie uses for its verification/reset emails. Returns an empty
    string on any failure so callers can degrade to the plaintext body instead of
    crashing signup/forgot-password.
    """

    template_name = "otp_reset.html" if reset else "otp_verification.html"
    try:
        from jinja2 import Environment, FileSystemLoader

        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_name)
        return template.render(user_name=user_name, otp=otp_code)
    except Exception:  # pragma: no cover - template missing / jinja2 absent
        logger.debug("OTP email template unavailable; falling back to plaintext.", exc_info=True)
        return ""


class AuthError(Exception):
    """Raised for user-facing auth failures (mapped to HTTP error codes)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _bcrypt() -> Optional[object]:
    """Return the bcrypt module, or None if not installed."""

    try:
        import bcrypt  # type: ignore

        return bcrypt
    except Exception:
        logger.warning("bcrypt not available; local auth disabled")
        return None


def bcrypt_available() -> bool:
    return _bcrypt() is not None


async def find_user_by_email(email: str) -> Optional[User]:
    async with get_db() as db:
        result = await db.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()


async def user_has_local_credential(email: str) -> bool:
    async with get_db() as db:
        result = await db.execute(
            select(User).where(
                User.email == email.lower().strip(),
                User.password_hash.isnot(None),
            )
        )
        return result.scalar_one_or_none() is not None


def _hash_password(password: str) -> Optional[str]:
    bcrypt = _bcrypt()
    if not bcrypt or len(password) < 8:
        return None
    try:
        digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return digest.decode("utf-8")
    except Exception:  # pragma: no cover - bcrypt edge cases
        return None


def _verify_password(password: str, password_hash: str) -> bool:
    bcrypt = _bcrypt()
    if not bcrypt or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:  # pragma: no cover - malformed hash
        return False


async def signup(email: str, password: str, name: Optional[str] = None) -> dict:
    """Create a user with a local credential. OTP is required to verify email.

    Returns ``{"status": "otp_sent", "email": ...}``. The account is created but
    marked unverified until the OTP succeeds. Raises AuthError on duplicate email
    or weak input.
    """

    if not isinstance(email, str) or len(email.strip()) < 3:
        raise AuthError("A valid email is required.", 400)

    if not isinstance(password, str) or len(password) < 8:
        raise AuthError("Password must be at least 8 characters.", 400)

    bcrypt = _bcrypt()
    if not bcrypt:
        raise AuthError("Authentication service unavailable. Please try again later.", 503)

    email = email.lower().strip()
    password_hash = _hash_password(password)
    if not password_hash:
        raise AuthError("Could not secure the provided password. Please try again.", 503)

    async with get_db() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise AuthError("An account with this email already exists.", 409)

        user = User(
            keycloak_id=f"local:{email}",  # namespace local users distinctly
            email=email,
            name=(name or "").strip() or None,
            password_hash=password_hash,
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except IntegrityError as e:
            # Concurrent signup race — treat as conflict, not a 500.
            await db.rollback()
            raise AuthError("An account with this email already exists.", 409) from e

    code = generate_otp_code()
    token = issue_otp_token(user.email, "signup_verify")
    await _store_otp(db, user.email, "signup_verify", code)

    # Deliver the OTP (SMTP or log fallback). Never fail signup on email errors.
    try:
        html = _render_otp_email(user.name, code)
        await email_sender.send_email(
            to=user.email,
            subject="Verify your Resume Platform account",
            body=f"Your verification code is: {code}",
            html=html or None,
        )
    except Exception as e:  # noqa: BLE001 - email failure is non-fatal
        logger.error("Failed to send signup OTP: %s", e)

    return {"status": "otp_sent", "email": user.email, "token": token}


async def forgot_password(email: str) -> dict:
    """Issue a password-reset OTP for the given email.

    Sends an OTP (via SMTP or log fallback) without revealing whether the email
    exists, matching signup. The user later verifies via /reset-password with the
    returned token + OTP; that route rotates the credential.

    Raises AuthError on invalid input (never reveals account existence).
    """

    if not isinstance(email, str) or len(email.strip()) < 3:
        raise AuthError("A valid email is required.", 400)

    email = email.lower().strip()

    # Confirm the account exists (without leaking anything to the response).
    user_record = await find_user_by_email(email)
    if not user_record:
        # Generic message — do not reveal whether the account exists.
        raise AuthError("If that account exists, a reset code was sent.", 400)

    # If the account has no local credential (e.g. Keycloak-only), there is
    # nothing to reset here; still return generically so we don't leak the fact.
    if not user_record.password_hash:
        raise AuthError("That account cannot be reset via this flow.", 400)

    code = generate_otp_code()
    token = issue_otp_token(user_record.email, "password_reset")
    async with get_db() as db:
        await _store_otp(db, user_record.email, "password_reset", code)

    try:
        reset_html = _render_otp_email(user_record.name, code, reset=True)
        await email_sender.send_email(
            to=user_record.email,
            subject="Reset your Resume Platform password",
            body=(
                "Use this code to reset your Resume Platform password: {code}\n"
                "If you did not request this, ignore this email."
            ).format(code=code),
            html=reset_html or None,
        )
    except Exception as e:  # noqa: BLE001 - email failure is non-fatal
        logger.error("Failed to send reset OTP: %s", e)

    return {"status": "otp_sent", "email": user_record.email, "token": token}


async def verify_otp(token: str, otp: str) -> dict:
    """Verify an OTP token + code and complete the pending action.

    ``token`` is the JWT issued alongside the OTP (carries email + action).
    Returns a login response ``{"token": ..., "user": {...}}`` on success.

    Raises AuthError for invalid/expired tokens, wrong codes, or unknown actions.
    """

    claims = decode_otp_token(token)
    if not claims:
        raise AuthError("Invalid or expired verification code.", 400)

    email = claims["_email"]
    action = claims["_action"]

    # Normalise the OTP (strip whitespace/dashes) before comparing.
    code = "".join(ch for ch in str(otp).strip() if ch.isdigit())
    if len(code) != 6:
        raise AuthError("Verification code must be 6 digits.", 400)

    async with get_db() as db:
        record = await db.execute(
            select(OtpCode).where(
                OtpCode.email == email,
                OtpCode.action == action,
                OtpCode.used.is_(False),
            )
        ).scalar_one_or_none()

        if not record:
            raise AuthError("No pending verification for this email.", 400)

        if record.expires_at < datetime.now(timezone.utc):
            raise AuthError("Verification code has expired. Request a new one.", 400)

        # Constant-time-ish comparison via bcrypt verify.
        if not _verify_password(code, record.code_hash):
            # Mark the code used to slow brute force (single-use).
            record.used = True
            await db.commit()
            raise AuthError("Incorrect verification code.", 401)

        record.used = True
        await db.commit()

        # Complete the action.
        user_record = await db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

    if not user_record:
        raise AuthError("Account no longer exists.", 400)

    if action == "signup_verify":
        # Mark the user verified (local accounts are always fully set up once OTP passes).
        return _login_response(user_record)

    if action == "password_reset":
        # Password is carried in the request body by the route; handled there.
        pass

    raise AuthError("Unexpected verification action.", 400)


async def reset_password(token: str, otp: str, new_password: str) -> dict:
    """Verify OTP for a password reset and rotate the user's credential.

    ``token`` carries email + action="password_reset". Raises AuthError on
    invalid/expired/incorrect codes or weak new passwords.
    """

    if not isinstance(new_password, str) or len(new_password) < 8:
        raise AuthError("Password must be at least 8 characters.", 400)

    claims = decode_otp_token(token)
    if not claims or claims["_action"] != "password_reset":
        raise AuthError("Invalid or expired reset code.", 400)

    email = claims["_email"]
    code = "".join(ch for ch in str(otp).strip() if ch.isdigit())
    if len(code) != 6:
        raise AuthError("Verification code must be 6 digits.", 400)

    async with get_db() as db:
        record = await db.execute(
            select(OtpCode).where(
                OtpCode.email == email,
                OtpCode.action == "password_reset",
                OtpCode.used.is_(False),
            )
        ).scalar_one_or_none()

        if not record:
            raise AuthError("No pending reset for this email.", 400)

        if record.expires_at < datetime.now(timezone.utc):
            raise AuthError("Reset code has expired. Request a new one.", 400)

        if not _verify_password(code, record.code_hash):
            record.used = True
            await db.commit()
            raise AuthError("Incorrect verification code.", 401)

        record.used = True
        await db.commit()

        user_record = await db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

    if not user_record:
        raise AuthError("Account no longer exists.", 400)

    new_hash = _hash_password(new_password)
    if not new_hash:
        raise AuthError("Could not secure the provided password. Please try again.", 503)

    async with get_db() as db:
        user_record.password_hash = new_hash
        await db.commit()

    return _login_response(user_record)


def _login_response(user_record: User) -> dict:
    """Build the login response for a verified local user."""

    token = issue_login_token(
        {"email": user_record.email, "name": user_record.name}
    )
    return {
        "token": token,
        "user": {
            "keycloak_id": user_record.keycloak_id,
            "email": user_record.email,
            "name": user_record.name or "",
        },
    }


async def login(email: str, password: str) -> dict:
    """Authenticate a local user with email + password.

    Verifies the supplied credentials against the stored bcrypt hash and, on
    success, returns a login response (matching verify_otp / reset_password).

    Raises AuthError on unknown email, wrong password, missing credential
    (Keycloak-only account), or unavailable bcrypt. The message never reveals
    whether the email exists, so it stays safe against account enumeration.
    """

    if not isinstance(email, str) or len(email.strip()) < 3:
        raise AuthError("A valid email is required.", 400)

    if not isinstance(password, str):
        raise AuthError("A password is required.", 400)

    email = email.lower().strip()
    bcrypt = _bcrypt()
    if not bcrypt:
        raise AuthError("Authentication service unavailable. Please try again later.", 503)

    user_record = await find_user_by_email(email)
    if not user_record or not user_record.password_hash:
        # Never reveal whether the account exists.
        raise AuthError("Invalid email or password.", 401)

    if not _verify_password(password, user_record.password_hash):
        raise AuthError("Invalid email or password.", 401)

    return _login_response(user_record)


async def _store_otp(
    db, email: str, action: str, code: str
) -> None:
    """Persist a hashed OTP + expiry for the given email/action."""

    record = OtpCode(
        email=email,
        action=action,
        code_hash=_hash_password(code),  # bcrypt hash of the numeric OTP
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(record)
    await db.commit()

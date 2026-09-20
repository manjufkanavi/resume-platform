"""Minimal email sender for OTP / password-reset codes.

Kept deliberately tiny so the auth flow has no external dependency by default.
Two send modes:

* SMTP (``SMTP_HOST`` set) — sends via a real mail server.
* Log/no-op (default, ``SMTP_HOST`` unset) — writes the code to stdout/stderr and
  prints a clearly-marked line so local/dev runs can read the code from logs.

The OTP payload is intentionally minimal (code + expiry hint), never the token
itself, so it can safely be delivered to logs or an email.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)


class EmailError(RuntimeError):
    """Raised when a message cannot be delivered."""


def send_email(
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> bool:
    """Send an email. Returns True on success.

    Falls back to logging (never raising) when no SMTP host is configured so the
    signup/forgot-password flow can still be exercised locally.
    """

    host = os.getenv("SMTP_HOST") or ""
    port = int(os.getenv("SMTP_PORT", "587"))

    if not host:
        # Dev/no-ops: emit the code to logs so it's inspectable. The marker makes
        # log parsers (and humans) able to find the code quickly.
        logger.info("OTP_CODE_MARKER %s subject=%r body=%r", to, subject, body)
        return True

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.getenv("SMTP_FROM", "noreply@iacgenie.com")
        msg["To"] = to

        if html:
            msg.add_alternative(html, subtype="html")
        else:
            msg.set_content(body)

        username = os.getenv("SMTP_USER") or None
        password = os.getenv("SMTP_PASSWORD") or None

        if username:
            server = smtplib.SMTP(host, port, timeout=15)
            if os.getenv("SMTP_TLS") not in ("0", "false"):
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
            server.quit()
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.send_message(msg)
            server.quit()

        logger.info("Sent OTP email to %s", to)
        return True
    except Exception as e:  # noqa: BLE001 - never fail the flow on email errors
        logger.error("Failed to send OTP email to %s: %s", to, e)
        raise EmailError(str(e)) from e

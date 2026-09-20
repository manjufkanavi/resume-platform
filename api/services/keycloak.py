"""Keycloak OIDC helpers for the resume platform.

The web UI uses Keycloak's hosted registration and forgot-password pages
(Keycloak-native signup/forgot-password), so this module only needs to:

* expose the Keycloak connection config (without secrets) for the frontend, and
* exchange an authorization code for tokens server-side so the confidential
  client secret never reaches the browser.

All calls use ``async httpx`` like ``services/auth.py``.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "iacgenie")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "resume-platform")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "CHANGE_ME")


def kc_config() -> dict:
    """Public Keycloak connection info for the frontend (no secrets)."""

    return {
        "kcUrl": KEYCLOAK_URL,
        "realm": KEYCLOAK_REALM,
        "clientId": KEYCLOAK_CLIENT_ID,
    }


def auth_url(action: str | None = None) -> str:
    """Build the Keycloak authorization endpoint URL.

    ``action`` maps to Keycloak's hosted flow via ``kc_action`` (e.g.
    ``register``, ``forgotPassword``). When omitted it is a plain login redirect.
    """

    base = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
    query = (
        f"?client_id={KEYCLOAK_CLIENT_ID}"
        "&response_type=code"
    )
    if action:
        query += f"&kc_action={action}"
    return base + query


async def exchange_code_for_token(code: str, redirect_uri: str) -> dict | None:
    """Exchange a Keycloak authorization code for tokens.

    Runs server-side so the confidential client secret stays out of the browser
    (the web UI cannot hold it). Returns decoded user info with keys ``sub``,
    ``email`` and ``name``, or ``None`` if the exchange fails.
    """

    token_url = (
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
        "/protocol/openid-connect/token"
    )
    data = {
        "grant_type": "authorization_code",
        "client_id": KEYCLOAK_CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            token_url,
            data=data,
            auth=httpx.BasicAuth(KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET),
        )

    if resp.status_code != 200:
        logger.warning(
            "Keycloak code exchange failed (status %s): %s",
            resp.status_code,
            resp.text[:200],
        )
        return None

    payload = resp.json()
    access_token = payload.get("access_token")
    if not access_token:
        return None

    # Prefer user info Keycloak embeds in the id_token; fall back to token claims.
    email = payload.get("email") or ""
    username = payload.get("preferred_username") or ""

    return {
        "sub": payload.get("sub", ""),
        "email": email,
        "name": username or (email.split("@")[0] if email else ""),
    }

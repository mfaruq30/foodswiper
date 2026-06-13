"""Apple Sign-in token handling for account deletion (Apple TN3194, D-013).

Apple REQUIRES that an app offering Sign in with Apple revoke the user's token
when their account is deleted. Deleting the Firebase user is not enough. So:

  sign-in  -> client sends the single-use Apple authorization code
           -> exchange it for a long-lived refresh token, store it (per uid)
  delete   -> revoke the stored refresh token at Apple, then drop it

The client secret is an ES256 JWT signed with the team's .p8 key. All of this
is GATED on four secrets (team id, key id, service id, private key); when any
is absent — the $0 demo, CI, local dev — `build_from_env` returns None, the
apple-link endpoint no-ops, and deletion simply skips the revoke (the data
purge still happens). The `pyjwt[crypto]` dependency lives in the firestore
extra and is imported lazily.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

_APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
_APPLE_REVOKE_URL = "https://appleid.apple.com/auth/revoke"
_APPLE_AUDIENCE = "https://appleid.apple.com"
# Apple caps the client-secret lifetime at ~6 months; we mint a short-lived one
# per operation, so a small window is plenty and limits blast radius.
_CLIENT_SECRET_TTL_S = 1800


@dataclass(slots=True)
class AppleCredentials:
    team_id: str
    key_id: str
    service_id: str  # the Services ID / client_id Sign in with Apple is tied to
    private_key_pem: str  # the .p8 key contents


def make_client_secret(creds: AppleCredentials, now: float | None = None) -> str:
    """The ES256 JWT Apple accepts as `client_secret`."""
    import jwt  # pyjwt[crypto]; lazy (firestore extra only)

    issued = int(now if now is not None else time.time())
    payload = {
        "iss": creds.team_id,
        "iat": issued,
        "exp": issued + _CLIENT_SECRET_TTL_S,
        "aud": _APPLE_AUDIENCE,
        "sub": creds.service_id,
    }
    return jwt.encode(
        payload, creds.private_key_pem, algorithm="ES256", headers={"kid": creds.key_id}
    )


class AppleAuthClient:
    """Exchanges and revokes Apple tokens. Constructed only when fully configured."""

    def __init__(self, creds: AppleCredentials) -> None:
        self._creds = creds

    def exchange_code_for_refresh_token(self, auth_code: str) -> str | None:
        """Trade the single-use authorization code for a refresh token.

        Returns None on any failure — sign-in must not break because the
        deletion-revoke seam couldn't be primed (deletion still purges data).
        """
        try:
            response = httpx.post(
                _APPLE_TOKEN_URL,
                data={
                    "client_id": self._creds.service_id,
                    "client_secret": make_client_secret(self._creds),
                    "grant_type": "authorization_code",
                    "code": auth_code,
                },
                timeout=httpx.Timeout(15.0),
            )
            response.raise_for_status()
            token = response.json().get("refresh_token")
            return str(token) if token else None
        # ValueError/TypeError also cover a malformed .p8 failing to sign the
        # client secret (cryptography raises these) — a misconfigured key must
        # degrade to None, not crash sign-in.
        except (httpx.HTTPError, ValueError, TypeError):
            return None

    def revoke(self, refresh_token: str) -> bool:
        """Revoke a stored refresh token at deletion (TN3194). Best-effort."""
        try:
            response = httpx.post(
                _APPLE_REVOKE_URL,
                data={
                    "client_id": self._creds.service_id,
                    "client_secret": make_client_secret(self._creds),
                    "token": refresh_token,
                    "token_type_hint": "refresh_token",
                },
                timeout=httpx.Timeout(15.0),
            )
            response.raise_for_status()
            return True
        # Best-effort (this runs mid-deletion): an Apple HTTP error OR a crypto
        # failure signing the client secret (malformed key -> ValueError/
        # TypeError) must return False, never propagate and 500 the delete.
        except (httpx.HTTPError, ValueError, TypeError):
            return False


def build_from_env() -> AppleAuthClient | None:
    """Construct the client iff all four secrets are present, else None.

    None is the supported demo/dev configuration (no Sign in with Apple).
    The private key can be inlined (APPLE_PRIVATE_KEY) or read from a path
    (APPLE_PRIVATE_KEY_PATH) — the .p8 is a file secret, never committed.
    """
    team_id = os.environ.get("APPLE_TEAM_ID")
    key_id = os.environ.get("APPLE_KEY_ID")
    service_id = os.environ.get("APPLE_SERVICE_ID")
    private_key = os.environ.get("APPLE_PRIVATE_KEY")
    key_path = os.environ.get("APPLE_PRIVATE_KEY_PATH")
    if key_path and not private_key:
        from pathlib import Path

        private_key = Path(key_path).read_text(encoding="utf-8")
    if not (team_id and key_id and service_id and private_key):
        return None
    return AppleAuthClient(
        AppleCredentials(
            team_id=team_id, key_id=key_id, service_id=service_id, private_key_pem=private_key
        )
    )

"""Authentication for the Munch API.

Every /v1 route requires a bearer token; the TokenVerifier port turns it into
a verified uid or raises. The Firebase implementation lives in adapters/ so
the untyped firebase_admin surface never touches this layer; tests and the
$0 demo inject simpler verifiers through the same seam.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from .ports import TokenVerifier


class AuthError(Exception):
    """Raised by TokenVerifier implementations on any invalid/expired token."""


class DevTokenVerifier:
    """Demo/dev verifier: the token IS the uid. NEVER for production.

    Exists so the free MVP-1 demo and local curl runs work with zero Firebase
    configuration (spec §10.8 degraded-mode guarantee). Selected only by an
    explicit MUNCH_AUTH=dev; the factory defaults to real verification.
    """

    def verify(self, token: str) -> str:
        if not token:
            raise AuthError("empty token")
        return token


def require_uid(request: Request) -> str:
    """FastAPI dependency: Authorization: Bearer <token> -> verified uid."""
    verifier: TokenVerifier = request.app.state.token_verifier
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return verifier.verify(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

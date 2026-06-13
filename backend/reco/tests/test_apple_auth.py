"""Apple client-secret JWT + the TN3194 link/revoke flow (D-013).

The JWT is verified against a freshly generated EC key (no real Apple creds);
exchange/revoke use a fake HTTP transport so nothing hits Apple's servers.
"""

from typing import cast

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey

from app.apple_auth import AppleAuthClient, AppleCredentials, build_from_env, make_client_secret


def _ec_private_key_pem() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _creds() -> AppleCredentials:
    return AppleCredentials(
        team_id="TEAM123456",
        key_id="KEY1234567",
        service_id="com.munch.app.service",
        private_key_pem=_ec_private_key_pem(),
    )


def test_client_secret_is_a_valid_es256_jwt() -> None:
    creds = _creds()
    secret = make_client_secret(creds, now=1_700_000_000)

    private_key = serialization.load_pem_private_key(creds.private_key_pem.encode(), password=None)
    public_key = cast(EllipticCurvePublicKey, private_key.public_key())
    # now is pinned in the past, so the token is "expired" vs wall-clock — we
    # verify the signature and the claim values, not freshness, here.
    claims = jwt.decode(
        secret,
        public_key,
        algorithms=["ES256"],
        audience="https://appleid.apple.com",
        options={"verify_exp": False},
    )

    assert claims["iss"] == "TEAM123456"
    assert claims["sub"] == "com.munch.app.service"
    assert claims["iat"] == 1_700_000_000
    # Apple caps client_secret at 6 months; we mint a short-lived 30-min one.
    assert claims["exp"] == 1_700_000_000 + 1800
    headers = jwt.get_unverified_header(secret)
    assert headers["kid"] == "KEY1234567"
    assert headers["alg"] == "ES256"


def test_build_from_env_is_none_without_all_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "APPLE_TEAM_ID",
        "APPLE_KEY_ID",
        "APPLE_SERVICE_ID",
        "APPLE_PRIVATE_KEY",
        "APPLE_PRIVATE_KEY_PATH",
    ):
        monkeypatch.delenv(var, raising=False)
    # The $0 demo / CI configuration: no Apple creds => no client (D-013).
    assert build_from_env() is None
    # Partial config is still None (all four are required).
    monkeypatch.setenv("APPLE_TEAM_ID", "T")
    assert build_from_env() is None


class _FakeResponse:
    def __init__(self, payload: dict[str, str], status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("bad", request=None, response=None)  # type: ignore[arg-type]

    def json(self) -> dict[str, str]:
        return self._payload


def test_exchange_and_revoke_use_the_apple_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_post(url: str, data: dict[str, str], timeout: object) -> _FakeResponse:
        calls.append((url, data))
        if url.endswith("/auth/token"):
            return _FakeResponse({"refresh_token": "rt-123"})
        return _FakeResponse({})

    monkeypatch.setattr("app.apple_auth.httpx.post", fake_post)
    client = AppleAuthClient(_creds())

    refresh = client.exchange_code_for_refresh_token("apple-code-abc")
    assert refresh == "rt-123"
    assert calls[0][0].endswith("/auth/token")
    assert calls[0][1]["grant_type"] == "authorization_code"
    assert calls[0][1]["code"] == "apple-code-abc"

    assert client.revoke("rt-123") is True
    assert calls[1][0].endswith("/auth/revoke")
    assert calls[1][1]["token"] == "rt-123"
    assert calls[1][1]["token_type_hint"] == "refresh_token"


def test_exchange_returns_none_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    def boom(url: str, data: dict[str, str], timeout: object) -> _FakeResponse:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.apple_auth.httpx.post", boom)
    # Sign-in must not break because the revoke seam couldn't be primed.
    assert AppleAuthClient(_creds()).exchange_code_for_refresh_token("x") is None


def test_exchange_and_revoke_degrade_on_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    # A non-2xx from Apple (raise_for_status path, distinct from a connection
    # error): exchange -> None, revoke -> False. revoke's False branch is the
    # best-effort guard that keeps account deletion from 500-ing.
    def reject(url: str, data: dict[str, str], timeout: object) -> _FakeResponse:
        return _FakeResponse({}, status=400)

    monkeypatch.setattr("app.apple_auth.httpx.post", reject)
    client = AppleAuthClient(_creds())
    assert client.exchange_code_for_refresh_token("x") is None
    assert client.revoke("rt") is False


def test_build_from_env_reads_private_key_from_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    # The production secret-loading mechanism: the .p8 lives on disk and is
    # referenced by APPLE_PRIVATE_KEY_PATH (it is never an inline env value in
    # plain text). Verify build_from_env actually reads the file.
    from pathlib import Path

    pem = _ec_private_key_pem()
    key_file = Path(str(tmp_path)) / "AuthKey.p8"
    key_file.write_text(pem, encoding="utf-8")

    monkeypatch.setenv("APPLE_TEAM_ID", "TEAM123456")
    monkeypatch.setenv("APPLE_KEY_ID", "KEY1234567")
    monkeypatch.setenv("APPLE_SERVICE_ID", "com.munch.app.service")
    monkeypatch.delenv("APPLE_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("APPLE_PRIVATE_KEY_PATH", str(key_file))

    client = build_from_env()
    assert client is not None
    assert client._creds.private_key_pem == pem


def test_inline_private_key_takes_precedence_over_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    # When both are set, the inline key wins (build_from_env only reads the path
    # `if key_path and not private_key`) — so a stale path can't shadow a
    # freshly-rotated inline secret.
    from pathlib import Path

    inline = _ec_private_key_pem()
    on_disk = _ec_private_key_pem()
    key_file = Path(str(tmp_path)) / "AuthKey.p8"
    key_file.write_text(on_disk, encoding="utf-8")

    monkeypatch.setenv("APPLE_TEAM_ID", "TEAM123456")
    monkeypatch.setenv("APPLE_KEY_ID", "KEY1234567")
    monkeypatch.setenv("APPLE_SERVICE_ID", "com.munch.app.service")
    monkeypatch.setenv("APPLE_PRIVATE_KEY", inline)
    monkeypatch.setenv("APPLE_PRIVATE_KEY_PATH", str(key_file))

    client = build_from_env()
    assert client is not None
    assert client._creds.private_key_pem == inline

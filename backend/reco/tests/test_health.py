"""Toolchain proof: exercises the only real endpoint shipped in Phase 0."""

from fastapi.testclient import TestClient

from app.main import SERVICE_VERSION, app


def test_health_reports_ok_and_version() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": SERVICE_VERSION}

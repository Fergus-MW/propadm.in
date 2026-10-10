"""Write-only credentials, the login domain lock, TOTP and the unconfigured provider path."""

import os
import stat

import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_runtime import create_app
from propadmin_runtime.config import Settings
from propadmin_runtime.credentials import domain_allowed, get_secret, totp

from services.browser.app.browser import router as browser_router


@pytest.fixture
def settings(tmp_path):
    return Settings(data_path=str(tmp_path / "state.json"))


def admin(app):
    client = TestClient(app)
    token = client.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_credentials_are_write_only(settings, tmp_path):
    app = create_app(store=Store(None), settings=settings, seed=False)
    client = admin(app)
    body = {
        "name": "Contractor portal",
        "username": "ops@example.test",
        "password": "hunter2-secret",
        "totp_seed": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ",
        "allowed_domains": ["Portal.com"],
    }
    created = client.post("/v1/credentials", json=body)
    assert created.status_code == 200
    record = created.json()
    assert record["allowed_domains"] == ["portal.com"] and record["has_totp"]
    listed = client.get("/v1/credentials")
    for response in (created, listed):
        assert "hunter2-secret" not in response.text and "GEZDGNBV" not in response.text
    assert "hunter2-secret" not in str(app.state.store.snapshot())

    secret_file = tmp_path / "credentials.secret.json"
    assert stat.S_IMODE(os.stat(secret_file).st_mode) == 0o600
    assert get_secret(settings, record["id"])["password"] == "hunter2-secret"

    rotated = client.post("/v1/credentials", json={**body, "id": record["id"], "password": "new"})
    assert rotated.json()["created_at"] == record["created_at"]
    assert get_secret(settings, record["id"])["password"] == "new"

    assert client.delete(f"/v1/credentials/{record['id']}").status_code == 200
    assert client.get("/v1/credentials").json() == {"items": []}
    assert "new" not in secret_file.read_text()


def test_domain_lock_rejects_lookalikes():
    domains = ["portal.com"]
    assert domain_allowed("https://portal.com/login", domains)
    assert domain_allowed("https://sub.portal.com/login", domains)
    assert not domain_allowed("https://evil-portal.com/login", domains)
    assert not domain_allowed("https://portal.com.evil.io/login", domains)
    assert not domain_allowed("https://evil.io/?next=https://portal.com", domains)
    assert not domain_allowed("http://portal.com/login", domains)


def test_totp_matches_rfc6238_vector():
    seed = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32("12345678901234567890")
    assert totp(seed, at=59, digits=8) == "94287082"
    assert totp(seed, at=1111111109, digits=8) == "07081804"


def test_browser_service_unconfigured_is_503(settings, monkeypatch):
    monkeypatch.delenv("BROWSERBASE_API_KEY", raising=False)
    monkeypatch.delenv("BROWSERBASE_PROJECT_ID", raising=False)
    app = create_app("browser", store=Store(None), settings=settings, seed=False)
    app.include_router(browser_router)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {settings.internal_token}"}
    url = "/internal/sessions/run:1/open"
    assert client.post(url, json={"url": "https://portal.com"}).status_code == 401
    response = client.post(url, json={"url": "https://portal.com"}, headers=headers)
    assert response.status_code == 503 and "BROWSERBASE_API_KEY" in response.json()["detail"]

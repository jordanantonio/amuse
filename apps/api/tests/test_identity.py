import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from shift_api import auth
from shift_api.config import Settings, settings
from shift_api.main import app


def test_demo_identity(client):
    response = client.get("/api/v1/me").json()
    assert response["demo"] is True
    assert response["organization_id"] == "northline"
    assert response["persona"]["role"] == "manager"
    assert "auth_subject" not in response


def test_hosted_identity_uses_membership_role(client, signing):
    response = client.get(
        "/api/v1/me", headers={"Authorization": "Bearer " + signing(role="admin")}
    )
    assert response.status_code == 200
    assert response.json()["persona"]["role"] == "manager"
    assert response.json()["demo"] is False
    assert client.get("/api/v1/personas").status_code == 404
    assert (
        client.post(
            "/api/v1/demo/reset", headers={"Authorization": "Bearer " + signing()}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"iss": "https://attacker.example/auth/v1"},
        {"aud": "wrong"},
        {"sub": ""},
        {"iat": 9999999999},
    ],
)
def test_invalid_claims(client, signing, claims):
    assert (
        client.get(
            "/api/v1/me", headers={"Authorization": "Bearer " + signing(**claims)}
        ).status_code
        == 401
    )


def test_missing_or_invalid_token(client, signing):
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    unrelated = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(
        dict(sub="demo:manager", iss=settings.issuer, aud="authenticated", iat=1, exp=9999999999),
        unrelated,
        algorithm="RS256",
    )
    assert (
        client.get("/api/v1/me", headers={"Authorization": "Bearer " + forged}).status_code == 401
    )


def test_missing_membership_and_demo_header(client, signing):
    assert (
        client.get(
            "/api/v1/me", headers={"Authorization": "Bearer " + signing(sub="unknown")}
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/me",
            headers={"X-Demo-Persona": "demo-admin", "Authorization": "Bearer " + signing()},
        ).status_code
        == 400
    )


def test_verifier_outage(client, signing, monkeypatch):
    def unavailable(_):
        raise jwt.PyJWKClientConnectionError("offline")

    monkeypatch.setattr(auth, "jwks_client", unavailable)
    assert (
        client.get("/api/v1/me", headers={"Authorization": "Bearer " + signing()}).status_code
        == 503
    )


def test_hosted_worker_privacy_and_role(client, signing):
    headers = {"Authorization": "Bearer " + signing(sub="demo:sofia")}
    response = client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json()["demo"] is False
    assert [w["id"] for w in response.json()["workers"]] == ["sofia"]
    assert "PRIVATE:" not in response.text
    assert client.post("/api/v1/projects/eastside/draft", headers=headers).status_code == 403


def test_safe_configuration_defaults():
    config = Settings(_env_file=None)
    # Environment may explicitly enable local demo in the test harness.
    config.demo_mode = False
    with pytest.raises(ValueError, match="PostgreSQL"):
        config.validate_hosted()
    config.database_url = "postgresql+psycopg://unused"
    with pytest.raises(ValueError, match="HTTPS"):
        config.validate_hosted()
    config.supabase_url = "https://fictional.supabase.co"
    config.validate_hosted()


def test_startup_rejects_missing_hosted_configuration(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "database_url", "sqlite://")
    with pytest.raises(ValueError, match="PostgreSQL"):
        with TestClient(app):
            pass


def test_demo_launcher_respects_hosted_dotenv(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    (tmp_path / ".env").write_text(
        "SHIFT_DEMO_MODE=false\nSHIFT_ENVIRONMENT=hosted\n"
        "SHIFT_DATABASE_URL=sqlite:///./must-not-exist.sqlite\n"
    )
    env = {key: value for key, value in os.environ.items() if not key.startswith("SHIFT_")}
    launcher = Path(__file__).resolve().parents[3] / "scripts/dev_api.py"
    result = subprocess.run(
        [sys.executable, str(launcher)], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "local-demo-only" in result.stderr
    assert not (tmp_path / "must-not-exist.sqlite").exists()

from shift_api.config import settings
from shift_api.session import safe_next


def sign_in(client, user_id):
    r = client.post("/api/v1/auth/demo", json={"user_id": user_id})
    assert r.status_code == 200, r.text
    return r.json()


def test_signed_out_requests_are_rejected(client):
    assert client.get("/api/v1/market/me").status_code == 401


def test_demo_sign_in_session_and_sign_out(client):
    assert sign_in(client, "u-maya")["next"] == "/home"
    me = client.get("/api/v1/market/me").json()
    assert me["user"]["full_name"] == "Maya Brooks"
    assert me["mode"] == "worker" and me["worker_profile"]["city"] == "Edmonton"
    client.post("/api/v1/auth/signout")
    assert client.get("/api/v1/market/me").status_code == 401


def test_tampered_session_cookie_is_rejected(client):
    client.cookies.set("shift_session", "not-a-real-token")
    assert client.get("/api/v1/market/me").status_code == 401


def test_new_worker_onboarding_steps(client):
    r = client.post("/api/v1/auth/demo", json={"full_name": "Jordan Kay"})
    assert r.json()["next"] == "/onboarding"
    r = client.put("/api/v1/market/onboarding", json={"role": "worker", "headline": "Welder"})
    assert r.status_code == 200 and r.json()["mode"] == "worker"
    assert not r.json()["onboarded"]
    r = client.put(
        "/api/v1/market/onboarding",
        json={"trades": ["Welding"], "city": "Leduc", "travel_radius_km": 80, "finish": True},
    )
    body = r.json()
    assert body["onboarded"] and body["worker_profile"]["trades"] == ["Welding"]
    # One role per account in V1.
    assert client.put("/api/v1/market/onboarding", json={"role": "business"}).status_code == 409


def test_onboarding_rejects_unknown_reference_data(client):
    client.post("/api/v1/auth/demo", json={"full_name": "Pat Doe"})
    client.put("/api/v1/market/onboarding", json={"role": "worker"})
    assert client.put("/api/v1/market/onboarding", json={"trades": ["Astronaut"]}).status_code == 422
    assert client.put("/api/v1/market/onboarding", json={"city": "Atlantis"}).status_code == 422


def test_business_onboarding_creates_owned_organization(client):
    client.post("/api/v1/auth/demo", json={"full_name": "Riley Fox"})
    r = client.put(
        "/api/v1/market/onboarding",
        json={"role": "business", "org_name": "Fox Builders", "city": "Calgary", "finish": True},
    )
    org = r.json()["organization"]
    assert org["name"] == "Fox Builders" and org["kind"] == "business" and org["handle"]


def test_google_start_falls_back_to_demo_when_not_configured(client):
    r = client.get("/api/v1/auth/google/start", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/signin/demo"
    assert client.get("/api/v1/auth/config").json() == {
        "google": False,
        "calendar": False,
        "demo": True,
    }


def test_google_start_redirects_to_consent_with_basic_scopes(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    r = client.get("/api/v1/auth/google/start?next=/work", follow_redirects=False)
    location = r.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "scope=openid+email+profile" in location and "calendar" not in location
    assert "shift_oauth_state" in r.headers["set-cookie"]


def test_oauth_callback_requires_matching_state_cookie(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    start = client.get("/api/v1/auth/google/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    client.cookies.clear()
    r = client.get(f"/api/v1/auth/google/callback?code=x&state={state}", follow_redirects=False)
    assert r.status_code == 400


def test_safe_next_blocks_open_redirects():
    assert safe_next("/work") == "/work"
    assert safe_next("//evil.example") == "/home"
    assert safe_next("https://evil.example") == "/home"
    assert safe_next("/\\evil") == "/home"


def test_demo_endpoints_disabled_outside_demo_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "session_secret", "test-secret")
    assert client.get("/api/v1/auth/demo-accounts").status_code == 404
    assert client.post("/api/v1/auth/demo", json={"user_id": "u-maya"}).status_code == 404

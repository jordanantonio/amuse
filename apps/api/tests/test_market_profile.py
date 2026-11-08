import base64
import pytest
from shift_api.config import settings

PDF = base64.b64encode(b"%PDF-1.4\n% demo ticket\n").decode()
PNG_BYTES_AS_PDF = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))


def as_user(client, uid):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo", json={"user_id": uid}).status_code == 200


def by_type(profile, type_id):
    return next(c for c in profile["credentials"] if c["credential_type_id"] == type_id)


def test_wallet_statuses_expiry_and_completeness(client):
    as_user(client, "u-maya")
    p = client.get("/api/v1/market/me/profile").json()
    whmis = by_type(p, "whmis")
    assert whmis["status"] == "verified" and whmis["expiring_soon"] and whmis["days_to_expiry"] == 6
    assert by_type(p, "aerial-platform")["status"] == "pending"
    assert 0 < p["completeness"]["percent"] <= 100 and p["completeness"]["next_step"]
    as_user(client, "u-isla")
    fall = by_type(client.get("/api/v1/market/me/profile").json(), "fall-protection")
    assert fall["status"] == "expired" and not fall["expiring_soon"]


def test_add_edit_delete_credential_and_reverify_on_edit(client):
    as_user(client, "u-maya")
    r = client.post(
        "/api/v1/market/credentials",
        json={"credential_type_id": "fall-protection", "issuer": "ACSA", "expires_on": "2029-01-31"},
    )
    assert r.status_code == 201 and r.json()["status"] == "self_reported"
    cid = r.json()["id"]
    verified = by_type(client.get("/api/v1/market/me/profile").json(), "csts-2020")
    edited = client.put(
        f"/api/v1/market/credentials/{verified['id']}",
        json={"credential_type_id": "csts-2020", "issuer": "ACSA", "number": "NEW-1"},
    ).json()
    assert edited["status"] == "self_reported"  # changed facts lose verification
    assert client.delete(f"/api/v1/market/credentials/{cid}").status_code == 200
    other = client.post(
        "/api/v1/market/credentials", json={"custom_name": "Hot work permit", "issuer": "Site"}
    ).json()
    assert other["name"] == "Hot work permit" and other["category"] == "Other"


def test_credential_validation(client):
    as_user(client, "u-maya")
    assert client.post("/api/v1/market/credentials", json={"issuer": "x"}).status_code == 422
    assert (
        client.post("/api/v1/market/credentials", json={"credential_type_id": "cor"}).status_code
        == 422
    )  # organization-only type
    bad_dates = {
        "credential_type_id": "whmis",
        "issued_on": "2026-05-01",
        "expires_on": "2026-01-01",
    }
    assert client.post("/api/v1/market/credentials", json=bad_dates).status_code == 422
    assert (
        client.post(
            "/api/v1/market/credentials", json={"credential_type_id": "cor", "scope": "org"}
        ).status_code
        == 403
    )


def test_document_upload_review_and_private_access(client):
    as_user(client, "u-maya")
    cid = by_type(client.get("/api/v1/market/me/profile").json(), "first-aid")["id"]
    body = {"filename": "first-aid.pdf", "content_type": "application/pdf", "data_base64": PDF}
    r = client.post(f"/api/v1/market/credentials/{cid}/document", json=body)
    assert r.status_code == 200 and r.json()["status"] == "pending" and r.json()["has_document"]
    mismatched = {**body, "data_base64": PNG_BYTES_AS_PDF}
    assert client.post(f"/api/v1/market/credentials/{cid}/document", json=mismatched).status_code == 422
    link = client.get(f"/api/v1/market/credentials/{cid}/document-link").json()["url"]
    file = client.get(link)
    assert file.status_code == 200 and file.content.startswith(b"%PDF")
    assert "no-store" in file.headers["cache-control"]
    # Another worker and an unrelated business can't get a link.
    as_user(client, "u-noah")
    assert client.get(f"/api/v1/market/credentials/{cid}/document-link").status_code == 404
    as_user(client, "u-marcus")
    assert client.get(f"/api/v1/market/credentials/{cid}/document-link").status_code == 404
    # Tampered links are refused.
    assert client.get(link + "x").status_code == 401


def test_documents_over_five_megabytes_are_refused(client):
    as_user(client, "u-maya")
    cid = by_type(client.get("/api/v1/market/me/profile").json(), "first-aid")["id"]
    big = base64.b64encode(b"%PDF" + b"0" * (5 * 1024 * 1024)).decode()
    body = {"filename": "big.pdf", "content_type": "application/pdf", "data_base64": big}
    assert client.post(f"/api/v1/market/credentials/{cid}/document", json=body).status_code in (
        413,
        422,
    )


def test_work_history_is_private_to_its_owner(client):
    as_user(client, "u-maya")
    r = client.post(
        "/api/v1/market/work-history",
        json={"role": "Lead hand", "company": "Acme", "start_date": "2024-01-01"},
    )
    entry = r.json()["id"]
    assert r.status_code == 201
    bad = {"role": "x", "company": "y", "start_date": "2024-05-01", "end_date": "2024-01-01"}
    assert client.post("/api/v1/market/work-history", json=bad).status_code == 422
    as_user(client, "u-noah")
    assert client.delete(f"/api/v1/market/work-history/{entry}").status_code == 404


def test_profile_update_and_rate_rules(client):
    as_user(client, "u-maya")
    r = client.put(
        "/api/v1/market/me/profile", json={"city": "Leduc", "rate_min_cents": 5000, "bio": "Hi"}
    )
    assert r.status_code == 200 and r.json()["profile"]["city"] == "Leduc"
    assert client.put("/api/v1/market/me/profile", json={"rate_max_cents": 100}).status_code == 422


def test_business_profile_and_org_wallet(client):
    as_user(client, "u-alex")
    assert client.get("/api/v1/market/me/profile").status_code == 403
    r = client.put("/api/v1/market/org/profile", json={"website": "https://northline.example"})
    assert r.status_code == 200 and r.json()["organization"]["website"]
    r = client.post(
        "/api/v1/market/credentials",
        json={"credential_type_id": "cgl-insurance", "scope": "org", "expires_on": "2027-06-30"},
    )
    assert r.status_code == 201
    names = [c["name"] for c in client.get("/api/v1/market/org/profile").json()["credentials"]]
    assert "Commercial general liability insurance" in names


def test_notifications_shape(client):
    as_user(client, "u-maya")
    body = client.get("/api/v1/market/notifications").json()
    assert set(body) == {"unread", "work_badge", "items"}

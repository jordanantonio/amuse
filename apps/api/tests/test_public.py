from datetime import date, timedelta

from sqlalchemy import select

from shift_api.config import settings
from shift_api.market_models import Posting


def test_public_contracts_require_no_identity_and_expose_only_public_fields(client, db):
    response = client.get("/api/v1/public/contracts")
    assert response.status_code == 200
    data = response.json()
    assert data["demo"] is True and data["contracts"]
    for item in data["contracts"]:
        assert set(item) == {
            "id",
            "title",
            "company",
            "trade",
            "city",
            "start_date",
            "end_date",
            "pay_rate_cents",
            "pay_unit",
            "posting_type",
        }
    for address in db.scalars(select(Posting.site_address)):
        if address:
            assert address not in response.text
    assert client.get("/api/v1/market/me").status_code == 401
    assert client.get("/api/v1/market/feed").status_code == 401


def test_public_contracts_omit_drafts_closed_filled_and_expired(client, db):
    postings = list(db.scalars(select(Posting).where(Posting.status == "open")))
    for posting, state in zip(postings[:3], ["draft", "closed", "filled"]):
        posting.status = state
    expired = postings[3]
    expired.start_date = date.today() - timedelta(days=10)
    expired.end_date = date.today() - timedelta(days=1)
    db.commit()
    ids = {item["id"] for item in client.get("/api/v1/public/contracts").json()["contracts"]}
    assert not ids.intersection(posting.id for posting in postings[:4])


def test_public_search_and_trade_filters(client, db):
    response = client.get("/api/v1/public/contracts", params={"trade": "Electrical"})
    items = response.json()["contracts"]
    assert items and all(item["trade"] == "Electrical" for item in items)
    assert (
        client.get("/api/v1/public/contracts", params={"q": "no-such-trade-93884"}).json()[
            "contracts"
        ]
        == []
    )
    assert client.get("/api/v1/public/contracts", params={"q": "%"}).json()["contracts"] == []
    assert client.get("/api/v1/public/contracts", params={"q": "x" * 101}).status_code == 422
    posting = db.scalar(
        select(Posting).where(Posting.status == "open", Posting.end_date >= date.today())
    )
    assert posting.id in {
        item["id"]
        for item in client.get("/api/v1/public/contracts", params={"q": posting.title}).json()[
            "contracts"
        ]
    }


def test_public_browse_stays_available_outside_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    response = client.get("/api/v1/public/contracts")
    assert response.status_code == 200
    assert response.json()["demo"] is False


def test_demo_signin_retains_safe_public_listing_destination(client):
    response = client.get(
        "/api/v1/auth/google/start?next=/postings/p-electrical", follow_redirects=False
    )
    assert response.headers["location"] == "/signin/demo?next=%2Fpostings%2Fp-electrical"
    response = client.post(
        "/api/v1/auth/demo?next=/postings/p-electrical", json={"user_id": "u-ilya"}
    )
    assert response.json()["next"] == "/postings/p-electrical"
    for unsafe in ("//evil.example", "/\\evil.example", "/\n/evil.example", "https://evil.example"):
        response = client.post(
            "/api/v1/auth/demo", params={"next": unsafe}, json={"user_id": "u-ilya"}
        )
        assert response.json()["next"] == "/home"

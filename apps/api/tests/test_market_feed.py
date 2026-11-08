import base64
from datetime import date, timedelta
import pytest
from shift_api.config import settings
from shift_api.engagements import book
from shift_api.feed_config import WEIGHTS
from shift_api.market_models import ContractApplication, Posting

MAYA_ELIGIBLE = {"p-rough-in", "p-service-elec", "p-temp-power", "p-sanitation", "p-line2", "p-panel"}


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))


def as_user(client, uid):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo", json={"user_id": uid}).status_code == 200


def feed(client, **params):
    r = client.get("/api/v1/market/feed", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_maya_sees_only_eligible_contracts_ranked(client):
    as_user(client, "u-maya")
    body = feed(client)
    ids = [c["id"] for c in body["items"]]
    assert set(ids) == MAYA_ELIGIBLE
    assert all(c["eligible"] and not c["reasons"] for c in body["items"])
    scores = [c["score"] for c in body["items"]]
    assert scores == sorted(scores, reverse=True)
    assert body["new_count"] == 3  # posted in the last 24 hours


def test_score_breakdown_is_explainable(client):
    as_user(client, "u-maya")
    rough = next(c for c in feed(client)["items"] if c["id"] == "p-rough-in")
    labels = [b["label"] for b in rough["score_breakdown"]]
    assert labels[0] == "Matches your trade (Electrical)"
    assert rough["score"] == sum(b["points"] for b in rough["score_breakdown"])
    points = {b["label"]: b["points"] for b in rough["score_breakdown"]}
    assert points["Matches your trade (Electrical)"] == WEIGHTS["trade_match"]
    assert points["You hold every nice-to-have ticket"] == WEIGHTS["nice_to_haves"]
    assert rough["match"] == {
        "required_total": 3,
        "required_held": 3,
        "items": rough["match"]["items"],
    }


def test_turning_off_the_filter_shows_greyed_reasons(client):
    as_user(client, "u-maya")
    items = {c["id"]: c for c in feed(client, qualified_only=False)["items"]}
    assert items["p-site-labour"]["reasons"] == ["Missing: Fall Protection"]
    assert items["p-high-bay"]["reasons"] == ["Needs verification: Aerial work platform"]
    assert "p-maint-elec" not in items  # already has an offer: lives in Work
    ordered = list(items.values())
    first_ineligible = next(i for i, c in enumerate(ordered) if not c["eligible"])
    assert all(c["eligible"] for c in ordered[:first_ineligible])


def test_search_filters(client):
    as_user(client, "u-maya")
    assert [c["id"] for c in feed(client, trade="General labour")["items"]] == ["p-sanitation"]
    near = feed(client, max_km=15)["items"]
    assert near and all(c["distance_km"] <= 15 for c in near)
    assert all(c["pay_rate_cents"] >= 4800 for c in feed(client, min_pay_cents=4800)["items"])
    assert [c["id"] for c in feed(client, q="panel")["items"]] == ["p-panel"]


def test_booked_dates_hide_overlapping_contracts(client, db):
    as_user(client, "u-maya")
    p = db.get(Posting, "p-service-elec")
    a = ContractApplication(posting_id=p.id, applicant_user_id="u-maya", status="accepted")
    db.add(a)
    db.flush()
    # An exclusive booking that overlaps the rough-in contract's dates.
    p.is_exclusive = True
    p.start_date, p.end_date = date.today() + timedelta(days=15), date.today() + timedelta(days=20)
    book(db, a, p)
    db.commit()
    ids = {c["id"] for c in feed(client)["items"]}
    assert "p-rough-in" not in ids
    greyed = {c["id"]: c for c in feed(client, qualified_only=False)["items"]}
    assert greyed["p-rough-in"]["reasons"][0].startswith("You’re booked")
    r = client.post("/api/v1/market/postings/p-rough-in/apply", json={})
    assert r.status_code == 409 and "booked" in r.json()["detail"]


def test_apply_rules(client):
    as_user(client, "u-maya")
    r = client.post("/api/v1/market/postings/p-rough-in/apply", json={"note": "Ready to start"})
    assert r.status_code == 201 and r.json()["status"] == "applied"
    assert client.post("/api/v1/market/postings/p-rough-in/apply", json={}).status_code == 409
    r = client.post("/api/v1/market/postings/p-site-labour/apply", json={})
    assert r.status_code == 409 and "Fall Protection" in r.json()["detail"]
    assert client.post("/api/v1/market/postings/a-shutdown/apply", json={}).status_code == 403
    assert "p-rough-in" not in {c["id"] for c in feed(client)["items"]}
    as_user(client, "u-alex")
    assert client.post("/api/v1/market/postings/p-panel/apply", json={}).status_code == 403
    notes = client.get("/api/v1/market/notifications").json()
    assert notes["items"][0]["type"] == "application.received"
    assert notes["work_badge"] >= 1


def test_business_reviews_applicants_and_offers(client):
    as_user(client, "u-alex")
    apps = client.get("/api/v1/market/postings/p-finish-carp/applicants").json()
    assert {a["applicant"]["name"] for a in apps} == {"Ella Thompson", "Lucas Martin", "Noah Williams"}
    ella = next(a for a in apps if a["applicant"]["name"] == "Ella Thompson")
    assert ella["posting"]["match"]["required_held"] == 2
    act = lambda aid, action: client.post(  # noqa: E731
        f"/api/v1/market/applications/{aid}/action", json={"action": action}
    )
    assert act(ella["id"], "shortlist").json()["status"] == "shortlisted"
    assert act(ella["id"], "offer").json()["status"] == "offered"
    assert act(ella["id"], "shortlist").status_code == 409  # already offered
    # Workers can't act as the business, and other businesses can't see applicants.
    as_user(client, "u-ella")
    assert act(ella["id"], "shortlist").status_code == 404
    detail = client.get("/api/v1/market/postings/p-finish-carp").json()
    assert detail["posting"]["site_address"] == "4210 Allard Way SW, Edmonton"
    assert detail["my_application"]["status"] == "offered"
    assert client.get("/api/v1/market/work").json()["offers"][0]["id"] == ella["id"]
    as_user(client, "u-marcus")
    assert client.get("/api/v1/market/postings/p-finish-carp/applicants").status_code == 404


def test_site_address_hidden_until_offer(client):
    as_user(client, "u-maya")
    assert client.get("/api/v1/market/postings/p-rough-in").json()["posting"]["site_address"] is None
    offered = client.get("/api/v1/market/postings/p-maint-elec").json()
    assert offered["posting"]["site_address"] == "6505 Sparrow Dr, Leduc"


def test_business_can_open_documents_only_of_applicants(client):
    as_user(client, "u-maya")
    profile = client.get("/api/v1/market/me/profile").json()
    cid = next(c["id"] for c in profile["credentials"] if c["credential_type_id"] == "csts-2020")
    pdf = base64.b64encode(b"%PDF-1.4 csts").decode()
    client.post(
        f"/api/v1/market/credentials/{cid}/document",
        json={"filename": "csts.pdf", "content_type": "application/pdf", "data_base64": pdf},
    )
    as_user(client, "u-marcus")  # Nisku: Maya has never applied there
    assert client.get(f"/api/v1/market/credentials/{cid}/document-link").status_code == 404
    as_user(client, "u-maya")
    client.post("/api/v1/market/postings/p-panel/apply", json={})
    as_user(client, "u-marcus")
    assert client.get(f"/api/v1/market/credentials/{cid}/document-link").status_code == 200


def posting_body(**over):
    start = date.today() + timedelta(days=10)
    body = {
        "title": "Drywall finisher",
        "trade": "General labour",
        "city": "Edmonton",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=30)).isoformat(),
        "pay_rate_cents": 3500,
        "requirements": [{"credential_type_id": "csts-2020"}],
    }
    return {**body, **over}


def test_create_edit_close_posting(client):
    as_user(client, "u-alex")
    r = client.post("/api/v1/market/postings", json=posting_body())
    assert r.status_code == 201 and r.json()["status"] == "open"
    pid = r.json()["id"]
    r = client.put(f"/api/v1/market/postings/{pid}", json=posting_body(pay_rate_cents=3700))
    assert r.json()["pay_rate_cents"] == 3700
    assert client.post(f"/api/v1/market/postings/{pid}/close").json()["status"] == "closed"
    bad = posting_body(end_date=(date.today() - timedelta(days=5)).isoformat())
    assert client.post("/api/v1/market/postings", json=bad).status_code == 422
    org_req = posting_body(requirements=[{"credential_type_id": "cor"}])
    assert client.post("/api/v1/market/postings", json=org_req).status_code == 422
    as_user(client, "u-maya")
    assert client.post("/api/v1/market/postings", json=posting_body()).status_code == 403
    as_user(client, "u-dana")  # agencies bid on crew work; they don't post
    assert client.post("/api/v1/market/postings", json=posting_body()).status_code == 403


def test_work_views_and_home(client):
    as_user(client, "u-maya")
    work = client.get("/api/v1/market/work").json()
    assert [a["posting"]["id"] for a in work["offers"]] == ["p-maint-elec"]
    assert [a["posting"]["id"] for a in work["applied"]] == ["p-pack-lead"]
    assert any(a["posting"]["id"] == "p-upgrade" for a in work["past"])
    home = client.get("/api/v1/market/home").json()
    assert len(home["offers"]) == 1 and home["expiring"][0]["name"] == "WHMIS"
    profile = client.get("/api/v1/market/me/profile").json()
    assert profile["completeness"]["next_step"]["label"] == (
        "Add your Fall Protection ticket to unlock 2 more contracts"
    )
    history = [h for h in profile["history"] if h["engagement_id"]]
    assert history and history[0]["description"] == "Completed on Shift."
    as_user(client, "u-alex")
    home = client.get("/api/v1/market/home").json()
    assert {a["name"] for a in home["new_applicants"]} == {
        "Ella Thompson",
        "Noah Williams",
        "Timberline Framing Crew",
    }
    org_work = client.get("/api/v1/market/org/work").json()
    assert any(e["applicant"]["name"] == "Ella Thompson" for e in org_work["active"])
    talent = client.get("/api/v1/market/talent", params={"trade": "Electrical"}).json()
    assert {t["name"] for t in talent} == {"Maya Brooks", "Sofia Rivera"}


def test_agency_feed_and_proposal(client):
    as_user(client, "u-omar")
    items = client.get("/api/v1/market/agency-feed").json()["items"]
    assert [i["id"] for i in items] == ["a-shutdown"]
    r = client.post(
        "/api/v1/market/postings/a-shutdown/apply",
        json={"note": "8 operators ready", "crew_size": 8, "proposed_rate_cents": 3400},
    )
    assert r.status_code == 201 and r.json()["crew_size"] == 8
    as_user(client, "u-dana")
    assert client.post("/api/v1/market/postings/a-shutdown/apply", json={}).status_code == 409


def test_dev_reset_restores_demo_and_is_disabled_outside_demo(client, monkeypatch):
    as_user(client, "u-maya")
    client.post("/api/v1/market/postings/p-rough-in/apply", json={})
    assert client.post("/api/v1/dev/reset").status_code == 200
    as_user(client, "u-maya")
    assert {c["id"] for c in feed(client)["items"]} == MAYA_ELIGIBLE
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "session_secret", "x")
    assert client.post("/api/v1/dev/reset").status_code == 404

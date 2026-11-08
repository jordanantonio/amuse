from datetime import date, timedelta
from shift_api.engagements import book
from shift_api.market_models import ContractApplication, Posting


def as_user(client, uid):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo", json={"user_id": uid}).status_code == 200


def test_ilya_profile_reads_like_a_person(client):
    as_user(client, "u-ilya")
    p = client.get("/api/v1/market/me/profile").json()
    assert p["profile"]["headline"].startswith("General labourer")
    assert p["profile"]["tools"][0] == "CSA steel-toe rubber boots"
    assert p["profile"]["languages"] == ["English", "Russian"]
    assert len(p["reviews"]) == 3 and p["reviews"][0]["rating"] == 5
    shift = next(h for h in p["history"] if h["engagement_id"])
    assert shift["rating"] == 5 and shift["photo_paths"] == ["/work/sanitation-line.svg"]
    assert any(h["photo_paths"] for h in p["history"] if not h["engagement_id"])
    assert p["availability"] == {"status": "open", "label": "Open to work now"}


def test_availability_pill_when_booked(client, db):
    as_user(client, "u-ilya")
    post = db.get(Posting, "p-shop-labour")
    post.start_date, post.end_date = date.today() - timedelta(days=2), date.today() + timedelta(days=20)
    post.is_exclusive = True
    a = ContractApplication(posting_id=post.id, applicant_user_id="u-ilya", status="accepted")
    db.add(a)
    db.flush()
    book(db, a, post)
    db.commit()
    pill = client.get("/api/v1/market/me/profile").json()["availability"]
    end = post.end_date
    assert pill == {"status": "booked", "label": f"Booked until {end:%b} {end.day}"}


def test_tools_and_languages_edit_inline(client):
    as_user(client, "u-ilya")
    r = client.put("/api/v1/market/me/profile", json={"tools": ["Ladder"], "languages": ["English"]})
    assert r.status_code == 200
    assert r.json()["profile"]["tools"] == ["Ladder"] and r.json()["profile"]["languages"] == ["English"]

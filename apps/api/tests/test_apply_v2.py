def as_user(client, uid):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo", json={"user_id": uid}).status_code == 200


def test_sanitation_posting_has_full_apply_content(client):
    as_user(client, "u-ilya")
    d = client.get("/api/v1/market/postings/p-sanitation").json()
    assert d["shift_hours"].startswith("10 PM")
    assert "CSA steel-toe rubber boots" in d["ppe_required"] and d["ppe_provided"]
    assert d["typical_day"] and d["org_about"]
    assert [q["id"] for q in d["questions"]] == ["overnight", "boots", "start"]
    assert d["calendar"] == {"status": "clear", "message": "No conflicts with your schedule"}


def test_apply_stores_screening_answers(client, db):
    from shift_api.market_models import ContractApplication

    as_user(client, "u-ilya")
    bad = client.post("/api/v1/market/postings/p-sanitation/apply", json={"answers": {"x": "1"}})
    assert bad.status_code == 422
    r = client.post(
        "/api/v1/market/postings/p-sanitation/apply",
        json={"answers": {"overnight": "Yes", "boots": "Yes", "start": "2026-11-20"}, "note": "Ready"},
    )
    assert r.status_code == 201
    a = db.get(ContractApplication, r.json()["id"])
    assert a.answers == {"overnight": "Yes", "boots": "Yes", "start": "2026-11-20"}


def test_calendar_check_reports_manual_unavailability(client):
    as_user(client, "u-ilya")
    d = client.get("/api/v1/market/postings/p-sanitation").json()
    start = d["posting"]["start_date"]
    client.post("/api/v1/market/availability", json={"start_date": start, "end_date": start, "note": "Trip"})
    check = client.get("/api/v1/market/postings/p-sanitation").json()["calendar"]
    assert check["status"] == "warning"

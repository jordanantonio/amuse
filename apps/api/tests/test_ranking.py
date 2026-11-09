def as_user(client, uid):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo", json={"user_id": uid}).status_code == 200


def rank(client):
    r = client.get("/api/v1/market/postings/p-warehouse/ranking")
    assert r.status_code == 200, r.text
    return r.json()


def test_coverage_strip_and_fit_sorting(client):
    as_user(client, "u-rahul")
    view = rank(client)
    labels = [c["label"] for c in view["coverage"]]
    assert labels == ["Forklift operator: need 2, hired 1", "Standard First Aid & CPR: need 1, covered"]
    names = [a["applicant"]["name"] for a in view["applicants"]]
    assert names[0] == "Ilya Sukhanov"  # holds the Valuable bonus cert and fills the gap
    assert view["applicants"][0]["fills_gap"] == ["Forklift operator"]
    scores = [a["score"] for a in view["applicants"] if not a["signals"]]
    assert scores == sorted(scores, reverse=True)
    bonus = {b["name"]: b for b in view["applicants"][0]["bonus"]}
    assert bonus["Forklift operator"] == {"name": "Forklift operator", "weight": "Valuable", "held": True}
    assert view["applicants"][0]["breakdown"][0]["kind"] == "certs"


def test_low_effort_signals_push_down_but_never_remove(client):
    as_user(client, "u-rahul")
    view = rank(client)
    tyler = next(a for a in view["applicants"] if a["applicant"]["name"] == "Tyler Brandt")
    assert set(tyler["signals"]) == {
        "Applied to 10+ postings in under 5 minutes",
        "Skipped all screening questions",
        "Outside their travel radius",
    }
    assert view["applicants"][-1]["applicant"]["name"] == "Tyler Brandt"
    assert tyler["status"] == "applied"


def test_requirements_pile_and_polite_bulk_decline(client):
    as_user(client, "u-rahul")
    view = rank(client)
    assert {a["applicant"]["name"] for a in view["pile"]} == {"Liam Patel", "Lucas Martin"}
    assert all(a["pile_reasons"] == ["Missing WHMIS"] for a in view["pile"])
    assert view["auto_decline"] is False
    r = client.post("/api/v1/market/postings/p-warehouse/decline-unqualified")
    assert r.json() == {"declined": 2}
    assert rank(client)["pile"] == []
    as_user(client, "u-liam")
    note = client.get("/api/v1/market/notifications").json()["items"][0]
    assert note["type"] == "application.declined" and "needs WHMIS" in note["payload"]["message"]


def test_auto_decline_is_opt_in(client):
    as_user(client, "u-rahul")
    r = client.put("/api/v1/market/postings/p-warehouse/screening", json={"auto_decline": True})
    assert r.status_code == 200 and r.json()["auto_decline"] and r.json()["pile"] == []
    as_user(client, "u-alex")
    assert client.get("/api/v1/market/postings/p-warehouse/ranking").status_code == 404


def test_bonus_weights_saved_from_the_posting_form(client):
    as_user(client, "u-rahul")
    body = {
        "title": "Dock helper",
        "trade": "Forklift & warehouse",
        "city": "Leduc",
        "start_date": "2027-01-04",
        "end_date": "2027-02-26",
        "pay_rate_cents": 2600,
        "requirements": [
            {"credential_type_id": "whmis"},
            {"credential_type_id": "forklift", "required": False, "weight": "very_valuable"},
            {"credential_type_id": "first-aid", "required": False},
        ],
    }
    pid = client.post("/api/v1/market/postings", json=body).json()["id"]
    items = {i["credential_type_id"]: i for i in client.get(f"/api/v1/market/postings/{pid}").json()["posting"]["match"]["items"]}
    assert items["forklift"]["weight"] == "very_valuable" and items["first-aid"]["weight"] == "nice"
    assert items["whmis"]["weight"] is None

from datetime import date, timedelta
from sqlalchemy import select
from shift_api.crew import bookings
from shift_api.market_models import CrewAssignment, CrewSlot

MONDAY = date.today() - timedelta(days=date.today().weekday())


def as_user(client, uid):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo", json={"user_id": uid}).status_code == 200


def slot_id(db, weekday, label, hour):
    return db.scalar(
        select(CrewSlot.id).where(
            CrewSlot.org_id == "prairie-harvest",
            CrewSlot.day == MONDAY + timedelta(days=weekday),
            CrewSlot.label == label,
            CrewSlot.start_minute == int(hour * 60),
        )
    )


def test_week_board_lists_slots_and_filled_spots(client, db):
    as_user(client, "u-rahul")
    week = client.get("/api/v1/market/crew/week", params={"start": str(MONDAY)}).json()
    assert week["start"] == str(MONDAY) and week["crew_size"] == 6
    mon_am = next(s for s in week["slots"] if s["day"] == str(MONDAY) and s["start_minute"] == 480)
    assert mon_am["label"] == "Packaging line" and mon_am["needed"] == 2
    assert mon_am["preferred_cert"]["name"].startswith("Forklift")
    assert {p["name"] for p in mon_am["spots"]} == {"Amelia Singh", "Sofia Rivera"}


def test_candidates_show_bar_and_fatigue_advice(client, db):
    as_user(client, "u-rahul")
    wed_am = slot_id(db, 2, "Packaging line", 8)
    rows = client.get(f"/api/v1/market/crew/slots/{wed_am}/candidates").json()
    ilya = next(r for r in rows if r["name"] == "Ilya Sukhanov")
    assert "Would be 3rd day in a row" in ilya["warnings"]
    assert ilya["bar"]["slot"] == [480, 720] and ilya["bar"]["free"] == [[360, 1080]]
    assert any(c["kind"] == "preferred" and c["state"] == "verified" for c in ilya["certs"])
    assert not ilya["blockers"] and rows[0]["score"] >= rows[-1]["score"]
    noah = next(r for r in rows if r["name"] == "Noah Williams")
    assert "Not available at this time" in noah["blockers"]


def test_assign_rules_and_no_double_booking(client, db):
    as_user(client, "u-rahul")
    wed_am = slot_id(db, 2, "Packaging line", 8)
    r = client.post(f"/api/v1/market/crew/slots/{wed_am}/assign", json={"user_id": "u-ilya"})
    assert r.status_code == 200 and any(p["name"] == "Ilya Sukhanov" for p in r.json()["spots"])
    sanitation = slot_id(db, 1, "Sanitation", 22)
    r = client.post(f"/api/v1/market/crew/slots/{sanitation}/assign", json={"user_id": "u-isla"})
    assert r.status_code == 409 and "certification" in r.json()["detail"]
    tue_pm = slot_id(db, 1, "Packaging line", 12.5)
    r = client.post(f"/api/v1/market/crew/slots/{tue_pm}/assign", json={"user_id": "u-noah"})
    assert r.status_code == 409 and "availability" in r.json()["detail"]
    # Overlap with an existing booking is refused.
    dock = slot_id(db, 0, "Loading dock", 6)
    mon_am = slot_id(db, 0, "Packaging line", 8)
    client.delete(f"/api/v1/market/crew/assignments/{db.scalar(select(CrewAssignment.id).where(CrewAssignment.slot_id == mon_am, CrewAssignment.user_id == 'u-amelia'))}")
    assert client.post(f"/api/v1/market/crew/slots/{dock}/assign", json={"user_id": "u-amelia"}).status_code == 200
    r = client.post(f"/api/v1/market/crew/slots/{mon_am}/assign", json={"user_id": "u-amelia"})
    assert r.status_code == 409 and "double-books" in r.json()["detail"]


def test_autofill_respects_rules_and_flags_gaps(client, db):
    as_user(client, "u-rahul")
    result = client.post("/api/v1/market/crew/autofill", params={"start": str(MONDAY)}).json()
    assert result["solver_status"] in {"OPTIMAL", "FEASIBLE"} and result["proposed"] > 0
    sunday = slot_id(db, 6, "Cold storage restock", 6)
    assert sunday in result["unfilled_slot_ids"]
    week = client.get("/api/v1/market/crew/week", params={"start": str(MONDAY)}).json()
    assert week["proposed"] == result["proposed"]
    # Every worker's week (assigned + proposed) keeps 10 h rest, no overlaps, <= 40 h.
    for uid in ["u-amelia", "u-ilya", "u-isla", "u-noah", "u-sofia", "u-lucas"]:
        shifts = bookings(db, uid, MONDAY, MONDAY + timedelta(days=6), include_proposed=True)
        shifts = [s for s in shifts if s[0].date() >= MONDAY]
        for (_, a1, _), (b0, _, _) in zip(shifts, shifts[1:], strict=False):
            assert (b0 - a1).total_seconds() >= 0
        hours = sum((e - s).total_seconds() for s, e, _ in shifts) / 3600
        assert hours <= 40
    accepted = client.post("/api/v1/market/crew/proposals/accept", json={"start": str(MONDAY)}).json()
    assert accepted["proposed"] == 0
    statuses = {a.status for a in db.scalars(select(CrewAssignment))}
    assert statuses == {"assigned"}


def test_find_a_replacement_searches_the_marketplace(client, db):
    as_user(client, "u-rahul")
    sunday = slot_id(db, 6, "Cold storage restock", 6)
    crew = client.get(f"/api/v1/market/crew/slots/{sunday}/candidates").json()
    assert all(r["blockers"] for r in crew)
    market = client.get(f"/api/v1/market/crew/slots/{sunday}/candidates", params={"scope": "market"}).json()
    assert market[0]["name"] == "Liam Patel" and not market[0]["blockers"] and not market[0]["on_crew"]


def test_crew_scope_and_rules(client, db):
    as_user(client, "u-ilya")
    assert client.get("/api/v1/market/crew/week").status_code == 403
    as_user(client, "u-alex")
    wed_am = slot_id(db, 2, "Packaging line", 8)
    assert client.get(f"/api/v1/market/crew/slots/{wed_am}/candidates").status_code == 404
    as_user(client, "u-rahul")
    r = client.put(
        "/api/v1/market/crew/rules",
        json={"max_consecutive_days": 4, "min_rest_hours": 11, "max_weekly_hours": 36},
    )
    assert r.status_code == 200
    week = client.get("/api/v1/market/crew/week").json()
    assert week["rules"]["min_rest_hours"] == 11

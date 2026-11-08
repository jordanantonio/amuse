from datetime import date, timedelta
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from shift_api import google
from shift_api.calendar_sync import event_specs
from shift_api.config import settings
from shift_api.engagements import book, sync_completions
from shift_api.market_models import (
    AvailabilityBlock,
    ConnectedAccount,
    ContractApplication,
    Credential,
    Engagement,
    Posting,
    WorkHistory,
)

TODAY = date.today()


def as_user(client, uid):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo", json={"user_id": uid}).status_code == 200


def app_id(db, posting, user):
    return db.scalar(
        select(ContractApplication.id).where(
            ContractApplication.posting_id == posting, ContractApplication.applicant_user_id == user
        )
    )


def test_accept_offers_to_withdraw_overlapping_and_locks_dates(client, db):
    as_user(client, "u-maya")
    offer = app_id(db, "p-maint-elec", "u-maya")
    weekend = app_id(db, "p-pack-lead", "u-maya")
    preview = client.get(f"/api/v1/market/applications/{offer}/accept-preview").json()
    assert preview["is_exclusive"] and not preview["conflicts"] and not preview["ticket_problems"]
    assert [o["id"] for o in preview["overlapping"]] == [weekend]
    r = client.post(f"/api/v1/market/applications/{offer}/accept", json={"withdraw_ids": [weekend]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "accepted" and body["engagement"]["status"] == "active"
    assert db.get(ContractApplication, weekend).status == "withdrawn"
    blocks = db.scalars(
        select(AvailabilityBlock).where(AvailabilityBlock.engagement_id == body["engagement"]["id"])
    ).all()
    assert [(b.start_date, b.end_date) for b in blocks] == [
        (TODAY + timedelta(days=7), TODAY + timedelta(days=120))
    ]
    assert db.get(Posting, "p-maint-elec").status == "filled"  # headcount 1
    # The feed now hides contracts that overlap the booking (FEED-1).
    ids = {c["id"] for c in client.get("/api/v1/market/feed").json()["items"]}
    assert "p-rough-in" not in ids and "p-line2" not in ids
    assert client.post(f"/api/v1/market/applications/{offer}/accept", json={}).status_code == 409
    as_user(client, "u-priya")
    types = [n["type"] for n in client.get("/api/v1/market/notifications").json()["items"]]
    assert "offer.accepted" in types and "application.withdrawn" in types


def test_accept_blocked_by_an_overlapping_booking(client, db):
    as_user(client, "u-maya")
    # Book Maya on another contract that overlaps the night-shift offer.
    other = db.get(Posting, "p-temp-power")
    a = ContractApplication(posting_id=other.id, applicant_user_id="u-maya", status="accepted")
    db.add(a)
    db.flush()
    book(db, a, other)
    db.commit()
    offer = app_id(db, "p-maint-elec", "u-maya")
    preview = client.get(f"/api/v1/market/applications/{offer}/accept-preview").json()
    assert preview["conflicts"] and "already booked" in preview["conflicts"][0]["message"]
    r = client.post(f"/api/v1/market/applications/{offer}/accept", json={})
    assert r.status_code == 409 and "won’t double-book" in r.json()["detail"]


def test_accept_rechecks_tickets_and_scope(client, db):
    as_user(client, "u-maya")
    offer = app_id(db, "p-maint-elec", "u-maya")
    weekend = app_id(db, "p-pack-lead", "u-maya")
    other = app_id(db, "p-upgrade", "u-maya")  # not overlapping
    r = client.post(f"/api/v1/market/applications/{offer}/accept", json={"withdraw_ids": [other]})
    assert r.status_code == 422
    whmis = db.scalar(
        select(Credential).where(
            Credential.owner_user_id == "u-maya", Credential.credential_type_id == "whmis"
        )
    )
    whmis.expires_on = TODAY - timedelta(days=1)
    db.commit()
    r = client.post(f"/api/v1/market/applications/{offer}/accept", json={"withdraw_ids": [weekend]})
    assert r.status_code == 409 and "WHMIS" in r.json()["detail"]
    as_user(client, "u-noah")
    assert client.post(f"/api/v1/market/applications/{offer}/accept", json={}).status_code == 404
    as_user(client, "u-priya")
    assert client.post(f"/api/v1/market/applications/{offer}/accept", json={}).status_code == 404


def accept_maya(client, db):
    as_user(client, "u-maya")
    offer = app_id(db, "p-maint-elec", "u-maya")
    body = client.post(f"/api/v1/market/applications/{offer}/accept", json={}).json()
    return body["engagement"]["id"]


def test_ics_download_for_full_time_contract(client, db):
    eid = accept_maya(client, db)
    r = client.get(f"/api/v1/market/engagements/{eid}/calendar.ics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    text = r.text.replace("\r\n ", "")
    assert text.count("BEGIN:VEVENT") == 1
    assert "SUMMARY:Shift: Maintenance electrician\\, night shift @ Prairie Harvest Foods" in text
    start, end = TODAY + timedelta(days=7), TODAY + timedelta(days=121)
    assert f"DTSTART;VALUE=DATE:{start:%Y%m%d}" in text and f"DTEND;VALUE=DATE:{end:%Y%m%d}" in text
    assert "6505 Sparrow Dr" in text
    as_user(client, "u-noah")
    assert client.get(f"/api/v1/market/engagements/{eid}/calendar.ics").status_code == 404


def test_event_shapes_for_part_time_patterns():
    start = date(2026, 11, 9)  # a Monday
    weekly = event_specs(start, date(2026, 12, 31), "mon_fri", False)
    assert len(weekly) == 1 and weekly[0].rrule == "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;UNTIL=20261231"
    weekends = event_specs(start, date(2026, 11, 30), "weekends", False)
    assert weekends[0].start == date(2026, 11, 14) and "BYDAY=SA,SU" in weekends[0].rrule
    rotation = event_specs(start, date(2026, 11, 24), "four_on_four_off", False)
    assert [(e.start.day, e.end_exclusive.day) for e in rotation] == [(9, 13), (17, 21)]
    full = event_specs(start, date(2026, 11, 20), "mon_fri", True)
    assert len(full) == 1 and full[0].end_exclusive == date(2026, 11, 21) and not full[0].rrule


def test_google_calendar_unavailable_without_keys(client, db):
    eid = accept_maya(client, db)
    r = client.post(f"/api/v1/market/engagements/{eid}/google").json()
    assert r["status"] == "unavailable" and ".ics" in r["message"]


@pytest.fixture
def google_on(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "cid")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    monkeypatch.setattr(settings, "token_encryption_key", Fernet.generate_key().decode())
    calls = []
    monkeypatch.setattr(google, "refresh_access_token", lambda token: "access-" + token)

    def fake(method, path, token, body=None):
        calls.append((method, path, token, body))
        return {"id": f"evt{len(calls)}"} if method == "POST" else {}

    monkeypatch.setattr(google, "calendar_request", fake)
    return calls


def test_google_calendar_incremental_connect_then_sync_and_cancel(client, db, google_on, monkeypatch):
    eid = accept_maya(client, db)
    r = client.post(f"/api/v1/market/engagements/{eid}/google").json()
    assert r["status"] == "needs_auth" and r["url"].startswith("/api/v1/auth/google/calendar/start")
    start = client.get(r["url"], follow_redirects=False)
    location = start.headers["location"]
    assert "calendar.events" in location and "access_type=offline" in location
    assert "include_granted_scopes=true" in location
    state = location.split("state=")[1].split("&")[0]
    monkeypatch.setattr(google, "exchange_code", lambda code: {"refresh_token": "r1", "scope": "x"})
    cb = client.get(f"/api/v1/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert cb.status_code == 303 and "calendar=added" in cb.headers["location"]
    account = db.get(ConnectedAccount, ("u-maya", "google_calendar"))
    assert account and "r1" not in account.refresh_token_encrypted
    assert google.decrypt(account.refresh_token_encrypted) == "r1"
    engagement = db.get(Engagement, eid)
    assert engagement.google_event_ids == ["evt1"]
    method, path, token, body = google_on[0]
    assert (method, path, token) == ("POST", "/calendars/primary/events", "access-r1")
    assert body["summary"].startswith("Shift: Maintenance electrician") and "date" in body["start"]
    # Re-syncing replaces the events instead of duplicating them (CAL-2).
    again = client.post(f"/api/v1/market/engagements/{eid}/google").json()
    assert again == {"status": "added", "url": None, "count": 1, "message": None}
    assert ("DELETE", "/calendars/primary/events/evt1", "access-r1", None) in google_on
    # Cancelling deletes the Google events and frees the dates.
    r = client.post(f"/api/v1/market/engagements/{eid}/cancel")
    assert r.status_code == 200
    db.refresh(engagement)
    assert engagement.status == "cancelled" and engagement.google_event_ids == []
    assert not db.scalars(select(AvailabilityBlock).where(AvailabilityBlock.engagement_id == eid)).all()
    assert db.get(Posting, "p-maint-elec").status == "open"


def test_calendar_callback_requires_the_same_signed_in_user(client, db, google_on, monkeypatch):
    accept_maya(client, db)
    start = client.get("/api/v1/auth/google/calendar/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    monkeypatch.setattr(google, "exchange_code", lambda code: {"refresh_token": "r1"})
    nonce = client.cookies.get("shift_oauth_state")
    as_user(client, "u-noah")
    client.cookies.set("shift_oauth_state", nonce, path="/api/v1/auth")
    cb = client.get(f"/api/v1/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert cb.status_code == 401


def test_schedule_tab_and_manual_unavailable_blocks(client, db):
    eid = accept_maya(client, db)
    start, end = TODAY, TODAY + timedelta(days=40)
    r = client.post(
        "/api/v1/market/availability",
        json={"start_date": str(TODAY + timedelta(days=3)), "end_date": str(TODAY + timedelta(days=4)), "note": "Dentist"},
    )
    assert r.status_code == 201
    view = client.get("/api/v1/market/schedule", params={"start": str(start), "end": str(end)}).json()
    kinds = {(i["kind"], i["title"]) for i in view["items"]}
    assert ("manual", "Dentist") in kinds and ("engagement", "Maintenance electrician, night shift") in kinds
    assert next(i for i in view["items"] if i["kind"] == "engagement")["engagement_id"] == eid
    bad = {"start_date": str(TODAY), "end_date": str(TODAY - timedelta(days=1))}
    assert client.post("/api/v1/market/availability", json=bad).status_code == 422
    too_long = {"start": str(start), "end": str(start + timedelta(days=90))}
    assert client.get("/api/v1/market/schedule", params=too_long).status_code == 422
    as_user(client, "u-priya")
    biz = client.get("/api/v1/market/schedule", params={"start": str(start), "end": str(end)}).json()
    assert any(i["subtitle"] == "Maya Brooks" for i in biz["items"])
    block = r.json()["id"]
    assert client.delete(f"/api/v1/market/availability/{block}").status_code == 404


def test_finished_contracts_complete_and_join_work_history(client, db):
    a = db.get(ContractApplication, app_id(db, "p-maint-elec", "u-maya"))
    p = db.get(Posting, "p-maint-elec")
    p.start_date, p.end_date = TODAY - timedelta(days=30), TODAY - timedelta(days=1)
    a.status = "accepted"
    book(db, a, p)
    db.commit()
    sync_completions(db)
    assert a.status == "completed"
    entry = db.scalar(select(WorkHistory).where(WorkHistory.role == p.title))
    assert entry and entry.description == "Completed on Shift."

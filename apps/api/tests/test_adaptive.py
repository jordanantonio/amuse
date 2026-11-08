from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from shift_api.models import *
from shift_api.seed import at, seed
from shift_api.solver import solve, utc, overlap
from shift_api.weather import refresh_forecast, weather_blockers
from shift_api.config import settings
from shift_api.database import Base, make_engine, get_db
from shift_api.main import app
from shift_api.locking import lock_schedule

MANAGER = {"X-Demo-Persona": "demo-manager"}
ADMIN = {"X-Demo-Persona": "demo-admin"}


def worker(wid):
    return {"X-Demo-Persona": "demo-" + wid}


def absence(client):
    r = client.post(
        "/api/v1/assignments/assignment-maya/disrupt",
        json={"starts_at": at(9, 8).isoformat(), "ends_at": at(13, 17).isoformat()},
    )
    assert r.status_code == 200


def proposal(client):
    response = client.post(
        "/api/v1/projects/eastside/proposals", json={"objectives": ["lowest_cost"]}
    )
    assert response.status_code == 200, response.text
    p = response.json()[0]
    assert "id" in p, p
    return p


def approve(client, p):
    r = client.post(
        f"/api/v1/proposals/{p['id']}/decision",
        json={"decision": "approve", "comment": "Reviewed qualifications and schedule."},
    )
    assert r.status_code == 200, r.text
    return r.json()


def accept_all(client, p):
    for c in p["confirmations"]:
        r = client.post(
            f"/api/v1/proposals/{p['id']}/confirmation",
            headers=worker(c["worker_id"]),
            json={"decision": "accept"},
        )
        assert r.status_code == 200, r.text


def test_approval_acceptance_publication_is_real_and_atomic(client, db):
    original = [(a.id, a.status) for a in db.scalars(select(Assignment))]
    absence(client)
    p = proposal(client)
    assert p["status"] == "pending_approval"
    assert original == [(a.id, a.status) for a in db.scalars(select(Assignment))]
    p = approve(client, p)
    assert p["status"] == "awaiting_confirmation"
    assert p["confirmations"]
    assert client.post(f"/api/v1/proposals/{p['id']}/publish").status_code == 409
    accept_all(client, p)
    assert db.scalar(select(SlotReservation.id))
    r = client.post(f"/api/v1/proposals/{p['id']}/publish")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"
    assert db.get(Assignment, "assignment-maya").status == "cancelled"
    assert db.get(Assignment, "assignment-noah").status == "confirmed"
    assert not db.scalar(select(SlotReservation.id))
    rows = list(db.scalars(select(Assignment).where(Assignment.status == "confirmed")))
    for i, a in enumerate(rows):
        assert not any(
            b.worker_id == a.worker_id and overlap(a.starts_at, a.ends_at, b.starts_at, b.ends_at)
            for b in rows[i + 1 :]
        )
    assert client.post(f"/api/v1/proposals/{p['id']}/publish").status_code == 409
    assert "schedule.published" in list(db.scalars(select(AuditEvent.action)))


def test_worker_may_only_see_and_accept_own_invitation(client):
    absence(client)
    p = approve(client, proposal(client))
    wid = p["confirmations"][0]["worker_id"]
    r = client.get(f"/api/v1/proposals/{p['id']}", headers=worker(wid))
    assert r.status_code == 200
    own = r.json()
    assert own["original_schedule"] == []
    assert all(s["worker_id"] == wid for s in own["proposed_schedule"])
    assert all(c["worker_id"] == wid for c in own["confirmations"])
    assert (
        client.post(
            f"/api/v1/proposals/{p['id']}/confirmation",
            headers=worker("liam"),
            json={"decision": "accept"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/proposals/{p['id']}/decision",
            headers=worker(wid),
            json={"decision": "approve"},
        ).status_code
        == 403
    )
    assert (
        client.post(f"/api/v1/proposals/{p['id']}/publish", headers=worker(wid)).status_code == 403
    )


def test_stale_approval_rejected(client, db):
    p = proposal(client)
    db.get(Worker, "sofia").hourly_rate_cents += 100
    db.commit()
    assert client.get(f"/api/v1/proposals/{p['id']}").json()["stale"]
    r = client.post(f"/api/v1/proposals/{p['id']}/decision", json={"decision": "approve"})
    assert r.status_code == 409
    assert not list(db.scalars(select(WorkerConfirmation)))


def test_revalidation_before_publish_prevents_changed_availability(client, db):
    absence(client)
    p = approve(client, proposal(client))
    accept_all(client, p)
    wid = p["confirmations"][0]["worker_id"]
    db.execute(delete(AvailabilityWindow).where(AvailabilityWindow.worker_id == wid))
    db.commit()
    assert client.post(f"/api/v1/proposals/{p['id']}/publish").status_code == 409
    assert db.get(Assignment, "assignment-maya").status == "confirmed"


def test_reject_revision_and_decline_keep_calendar_unchanged(client, db):
    absence(client)
    for decision, expected in [("reject", "rejected"), ("request_revision", "revision_requested")]:
        p = proposal(client)
        r = client.post(
            f"/api/v1/proposals/{p['id']}/decision",
            json={"decision": decision, "comment": "Need another option"},
        )
        assert r.json()["status"] == expected
    p = approve(client, proposal(client))
    wid = p["confirmations"][0]["worker_id"]
    assert (
        client.post(
            f"/api/v1/proposals/{p['id']}/confirmation",
            headers=worker(wid),
            json={"decision": "decline"},
        ).json()["status"]
        == "revision_requested"
    )
    assert db.get(Assignment, "assignment-maya").status == "confirmed"
    assert not list(db.scalars(select(SlotReservation)))
    assert len(list(db.scalars(select(ApprovalDecision)))) == 3


def test_expired_invitation_cannot_accept_and_is_shown_expired(client, db):
    p = approve(client, proposal(client))
    db.get(RecoveryProposal, p["id"]).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    wid = p["confirmations"][0]["worker_id"]
    assert client.get(f"/api/v1/proposals/{p['id']}").json()["status"] == "expired"
    assert (
        client.post(
            f"/api/v1/proposals/{p['id']}/confirmation",
            headers=worker(wid),
            json={"decision": "accept"},
        ).status_code
        == 409
    )


def test_competing_accepted_reservations_prevent_double_booking(client, db):
    absence(client)
    first = approve(client, proposal(client))
    second = approve(client, proposal(client))
    wid = first["confirmations"][0]["worker_id"]
    r = client.post(
        f"/api/v1/proposals/{first['id']}/confirmation",
        headers=worker(wid),
        json={"decision": "accept"},
    )
    assert r.status_code == 200
    r = client.post(
        f"/api/v1/proposals/{second['id']}/confirmation",
        headers=worker(wid),
        json={"decision": "accept"},
    )
    assert r.status_code == 409
    assert db.get(Assignment, "assignment-maya").status == "confirmed"


def test_weather_is_task_specific_source_labeled_and_updates_deduplicated(client, db):
    r = client.post("/api/v1/projects/eastside/weather", json={"adverse": True})
    assert r.json()["changed"]
    assert not client.post("/api/v1/projects/eastside/weather", json={"adverse": True}).json()[
        "changed"
    ]
    forecasts = client.get("/api/v1/projects/eastside/weather").json()
    assert all(f["simulated"] and "simulated" in f["source"] and f["fetched_at"] for f in forecasts)
    review = client.post("/api/v1/projects/eastside/review").json()
    assert any(r["task_id"] == "rough-in" and r["kind"] == "weather" for r in review["risks"])
    assert not any(r["task_id"] == "fabricate" and r["kind"] == "weather" for r in review["risks"])
    assert db.get(Assignment, "assignment-maya").status == "confirmed"
    p = proposal(client)
    rough = next(s for s in p["proposed_schedule"] if s["task_id"] == "rough-in")
    assert not weather_blockers(
        db,
        db.get(Project, "eastside"),
        db.get(Task, "rough-in"),
        datetime.fromisoformat(rough["starts_at"]),
        datetime.fromisoformat(rough["ends_at"]),
    )


def test_task_transition_contingency_and_daily_limits_enforced(db):
    policy = db.get(SchedulingPolicy, "eastside")
    policy.task_buffer_percent = 20
    policy.transition_minutes = 30
    policy.contingency_minutes = 60
    db.flush()
    d = solve(db, db.get(Project, "eastside"), db.get(Membership, "demo-manager"))
    assert d.solver_status in {"OPTIMAL", "FEASIBLE"}
    for p in d.proposals:
        t = db.get(Task, p["task_id"])
        assert (
            datetime.fromisoformat(p["ends_at"]) - datetime.fromisoformat(p["starts_at"])
        ).total_seconds() / 60 >= t.duration_hours * 60 * 1.2
        assert datetime.fromisoformat(p["ends_at"]) <= utc(
            db.get(Project, "eastside").deadline
        ) - timedelta(hours=1)
    policy.max_daily_hours = 3
    db.flush()
    assert (
        solve(db, db.get(Project, "eastside"), db.get(Membership, "demo-manager")).solver_status
        == "INFEASIBLE"
    )


def test_separate_solver_objectives_produce_measured_feasible_options(client):
    response = client.post("/api/v1/projects/eastside/proposals", json={})
    assert response.status_code == 200
    options = response.json()
    assert len(options) == 3
    assert {o["objective"] for o in options} == {
        "lowest_cost",
        "earliest_completion",
        "fewest_changes",
    }
    assert all(o["metrics"]["solver_status"] in {"OPTIMAL", "FEASIBLE"} for o in options)
    assert all(isinstance(o["metrics"]["labour_cost_cents"], int) for o in options)


def test_exact_absence_interval_preserves_confirmed_work(client, db):
    payload = {"starts_at": at(9, 9).isoformat(), "ends_at": at(9, 10).isoformat()}
    assert (
        client.post("/api/v1/assignments/assignment-maya/disrupt", json=payload).status_code == 200
    )
    a = db.scalar(select(WorkerAbsence))
    assert utc(a.starts_at) == at(9, 9)
    assert utc(a.ends_at) == at(9, 10)
    assert db.get(Assignment, "assignment-maya").status == "confirmed"


def test_worker_profile_availability_and_application_workflows(client, db):
    h = worker("sofia")
    assert (
        client.put(
            "/api/v1/me/availability",
            headers=h,
            json={
                "windows": [{"starts_at": at(9, 12).isoformat(), "ends_at": at(9, 17).isoformat()}]
            },
        ).status_code
        == 200
    )
    assert (
        len(
            list(
                db.scalars(
                    select(AvailabilityWindow).where(AvailabilityWindow.worker_id == "sofia")
                )
            )
        )
        == 1
    )
    payload = dict(
        title="Independent electrician",
        location="Edmonton, AB",
        hourly_rate_cents=7400,
        skills=["Electrical"],
        work_modes=["on_site"],
        certifications=[dict(name="Red Seal Electrical", expires_at=at(30, 17).isoformat())],
    )
    assert client.put("/api/v1/me/profile", headers=h, json=payload).status_code == 200
    assert db.get(Worker, "sofia").hourly_rate_cents == 7400
    assert client.post("/api/v1/jobs/job-electrical/apply", headers=h).status_code == 200
    assert client.post("/api/v1/jobs/job-electrical/apply", headers=h).status_code == 409
    applications = client.get("/api/v1/applications", headers=h).json()
    assert len(applications) == 1
    aid = applications[0]["id"]
    assert client.post(f"/api/v1/applications/{aid}/withdraw", headers=h).status_code == 200


def test_availability_edit_cannot_break_confirmed_assignment(client):
    r = client.put("/api/v1/me/availability", headers=worker("maya"), json={"windows": []})
    assert r.status_code == 409


def test_project_task_job_creation_and_cycle_rejection(client):
    payload = dict(
        name="New build",
        client="Client",
        location="Edmonton, AB",
        capacity=3,
        starts_at=at(9, 8).isoformat(),
        ends_at=at(13, 17).isoformat(),
        budget_cents=100000,
    )
    r = client.post("/api/v1/projects", json=payload)
    assert r.status_code == 200
    pid = r.json()["id"]
    task = dict(name="Task A", duration_hours=2, required_skills=["Electrical"])
    a = client.post(f"/api/v1/projects/{pid}/tasks", json=task)
    assert a.status_code == 200
    aid = a.json()["id"]
    b = client.post(
        f"/api/v1/projects/{pid}/tasks", json={**task, "name": "Task B", "predecessor_ids": [aid]}
    )
    bid = b.json()["id"]
    assert (
        client.put(
            f"/api/v1/projects/{pid}/tasks/{aid}", json={**task, "predecessor_ids": [bid]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/jobs",
            json=dict(
                project_id=pid,
                title="Electrician",
                location="Edmonton, AB",
                work_mode="on_site",
                skills=["Electrical"],
                rate_min_cents=6500,
                rate_max_cents=8000,
            ),
        ).status_code
        == 200
    )
    assert client.post("/api/v1/projects", headers=worker("sofia"), json=payload).status_code == 403


def test_forecast_or_policy_change_invalidates_proposal(client):
    p = proposal(client)
    assert (
        client.post("/api/v1/projects/eastside/weather", json={"adverse": True}).status_code == 200
    )
    assert (
        client.post(
            f"/api/v1/proposals/{p['id']}/decision", json={"decision": "approve"}
        ).status_code
        == 409
    )


def test_unknown_timezone_rejected_as_validation_error(client):
    assert (
        client.put(
            "/api/v1/projects/eastside/policy", json={"timezone": "Invalid/Zone"}
        ).status_code
        == 422
    )


def test_auth_verifies_signature_audience_and_subject_not_demo_header(client, db, monkeypatch):
    from shift_api import auth

    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class Client:
        def get_signing_key_from_jwt(self, token):
            return type("Key", (), {"key": key.public_key()})()

    monkeypatch.setattr(auth, "jwks_client", lambda issuer: Client())
    claims = dict(
        sub="supabase-user",
        iss="https://example.supabase.co/auth/v1",
        aud="authenticated",
        exp=datetime.now(timezone.utc) + timedelta(minutes=5),
        iat=datetime.now(timezone.utc),
    )
    db.get(Membership, "demo-sofia").auth_subject = "supabase-user"
    db.commit()
    token = jwt.encode(claims, key, algorithm="RS256")
    h = {"Authorization": "Bearer " + token, "X-Demo-Persona": "demo-admin"}
    assert client.get("/api/v1/dashboard", headers=h).json()["persona"]["id"] == "demo-sofia"
    assert client.post("/api/v1/projects/eastside/proposals", headers=h, json={}).status_code == 403
    assert client.get("/api/v1/dashboard", headers=MANAGER).status_code == 401
    invalid = jwt.encode({**claims, "aud": "wrong"}, key, algorithm="RS256")
    assert (
        client.get("/api/v1/dashboard", headers={"Authorization": "Bearer " + invalid}).status_code
        == 401
    )


def test_simultaneous_competing_acceptance_serialized(tmp_path):
    engine = make_engine("sqlite:///" + str(tmp_path / "concurrent.sqlite"))
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as s:
        seed(s)

    # Use a separate app dependency for every request, as production does.
    def sessions():
        with Session(engine, expire_on_commit=False) as s:
            yield s

    old = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = sessions
    try:
        with TestClient(app) as c:
            absence(c)
            a = approve(c, proposal(c))
            b = approve(c, proposal(c))
            wid = a["confirmations"][0]["worker_id"]

            def accept(pid):
                return c.post(
                    f"/api/v1/proposals/{pid}/confirmation",
                    headers=worker(wid),
                    json={"decision": "accept"},
                ).status_code

            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses = list(pool.map(accept, [a["id"], b["id"]]))
            assert sorted(statuses) == [200, 409]
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old)
        engine.dispose()


def test_manager_can_release_accepted_reservations_for_revision(client, db):
    absence(client)
    p = approve(client, proposal(client))
    wid = p["confirmations"][0]["worker_id"]
    assert (
        client.post(
            f"/api/v1/proposals/{p['id']}/confirmation",
            headers=worker(wid),
            json={"decision": "accept"},
        ).status_code
        == 200
    )
    assert db.scalar(select(SlotReservation.id))
    r = client.post(
        f"/api/v1/proposals/{p['id']}/decision",
        json={"decision": "request_revision", "comment": "Inputs changed; prepare another plan."},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "revision_requested"
    assert not db.scalar(select(SlotReservation.id))

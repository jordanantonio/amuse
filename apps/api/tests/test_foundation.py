from datetime import timedelta
from sqlalchemy import select, delete
from shift_api.models import *
from shift_api.seed import at, reset
from shift_api.solver import solve, overlap, utc
from shift_api.config import settings


def run(db):
    return solve(db, db.get(Project, "eastside"), db.get(Membership, "demo-manager"))


def remove_maya(db):
    db.get(Assignment, "assignment-maya").status = "disrupted"
    db.add(
        WorkerAbsence(
            worker_id="maya", starts_at=at(9, 8), ends_at=at(13, 17), recorded_by="demo-manager"
        )
    )
    db.flush()


def test_dashboard_is_seeded_data(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert len(data["workers"]) == 12
    assert len(data["projects"]) == 3
    assert data["staffing_gaps"] == 1
    assert data["demo"] is True
    assert data["assignments"][0]["starts_at"].endswith("Z")


def test_private_details_never_serialized(client):
    data = client.get("/api/v1/dashboard").json()
    assert "PRIVATE:" not in str(data)
    assert "health appointment" not in str(data)
    assert "private_label" not in str(data)
    sofia = next(w for w in data["workers"] if w["id"] == "sofia")
    assert sofia["busy"]
    assert set(sofia["busy"][0]) == {"starts_at", "ends_at"}


def test_worker_scope(client):
    data = client.get("/api/v1/dashboard", headers={"X-Demo-Persona": "demo-maya"}).json()
    assert [w["id"] for w in data["workers"]] == ["maya"]
    assert all(a["worker_id"] == "maya" for a in data["assignments"])
    assert [p["id"] for p in data["projects"]] == ["eastside"]


def test_worker_cannot_plan_or_disrupt(client):
    headers = {"X-Demo-Persona": "demo-sofia"}
    assert client.post("/api/v1/projects/eastside/draft", headers=headers).status_code == 403
    assert (
        client.post("/api/v1/assignments/assignment-maya/disrupt", headers=headers).status_code
        == 403
    )
    assert client.get("/api/v1/drafts", headers=headers).status_code == 403


def test_unknown_persona(client):
    assert client.get("/api/v1/dashboard", headers={"X-Demo-Persona": "bad"}).status_code == 401


def test_tenant_isolation(client, db):
    db.add(Organization(id="other", name="Other Co"))
    db.flush()
    db.add(
        Membership(
            id="other-manager",
            organization_id="other",
            auth_subject="other",
            name="Other Manager",
            role="manager",
        )
    )
    db.commit()
    headers = {"X-Demo-Persona": "other-manager"}
    assert client.get("/api/v1/dashboard", headers=headers).json()["workers"] == []
    assert client.post("/api/v1/projects/eastside/draft", headers=headers).status_code == 404
    assert (
        client.post("/api/v1/assignments/assignment-maya/disrupt", headers=headers).status_code
        == 404
    )


def test_manager_project_scope(client, db):
    db.add(
        Membership(
            id="unassigned-manager",
            organization_id="northline",
            auth_subject="unassigned",
            name="Other manager",
            role="manager",
        )
    )
    db.commit()
    h = {"X-Demo-Persona": "unassigned-manager"}
    assert client.get("/api/v1/dashboard", headers=h).json()["projects"] == []
    assert client.post("/api/v1/projects/eastside/draft", headers=h).status_code == 403


def test_production_mode_fail_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.get("/api/v1/dashboard").status_code == 503
    assert client.get("/api/v1/personas").status_code == 404


def test_real_cp_sat_draft_preserves_assignments(db):
    before = [
        (a.id, a.worker_id, a.starts_at, a.ends_at, a.status)
        for a in db.scalars(select(Assignment))
    ]
    d = run(db)
    assert d.solver_status in {"OPTIMAL", "FEASIBLE"}
    assert d.proposals
    assert all(p["state"] == "proposed" for p in d.proposals)
    assert before == [
        (a.id, a.worker_id, a.starts_at, a.ends_at, a.status)
        for a in db.scalars(select(Assignment))
    ]


def test_disruption_is_explicit_and_persistent(client, db):
    before = client.get("/api/v1/dashboard").json()["staffing_gaps"]
    response = client.post("/api/v1/assignments/assignment-maya/disrupt")
    assert response.status_code == 200
    assert response.json()["staffing_gaps"] == before + 1
    assert db.get(Assignment, "assignment-maya").status == "confirmed"
    assert db.scalar(select(WorkerAbsence.worker_id)) == "maya"
    assert client.post("/api/v1/assignments/assignment-maya/disrupt").status_code == 409
    assert db.scalar(select(AuditEvent.action)) == "worker.absence_recorded"


def test_recovery_finds_contractor_respects_private_busy(db):
    remove_maya(db)
    d = run(db)
    assert d.solver_status in {"OPTIMAL", "FEASIBLE"}
    replacement = next(p for p in d.proposals if p["task_id"] == "rough-in")
    assert replacement["worker_id"] == "sofia"
    assert utc(datetime.fromisoformat(replacement["starts_at"])) >= at(9, 12)
    assert db.get(Assignment, "assignment-noah").status == "confirmed"


def test_no_double_booking_cross_project(db):
    remove_maya(db)
    d = run(db)
    proposals = d.proposals
    fixed = list(db.scalars(select(Assignment).where(Assignment.status == "confirmed")))
    for p in proposals:
        start = datetime.fromisoformat(p["starts_at"])
        end = datetime.fromisoformat(p["ends_at"])
        assert not any(
            a.worker_id == p["worker_id"] and overlap(start, end, a.starts_at, a.ends_at)
            for a in fixed
        )
        assert not any(
            q is not p
            and q["worker_id"] == p["worker_id"]
            and overlap(
                start,
                end,
                datetime.fromisoformat(q["starts_at"]),
                datetime.fromisoformat(q["ends_at"]),
            )
            for q in proposals
        )


def test_certification_expiry_blocks_unqualified_workers(db):
    remove_maya(db)
    for cert in db.scalars(
        select(Certification).where(Certification.worker_id.in_(["sofia", "ethan", "jack"]))
    ):
        cert.expires_at = at(9, 7)
    db.flush()
    d = run(db)
    assert d.solver_status == "INFEASIBLE"
    assert any("Electrical rough-in" in b for b in d.blockers)


def test_skills_required(db):
    remove_maya(db)
    db.execute(delete(Skill).where(Skill.worker_id.in_(["sofia", "ethan", "jack"])))
    db.flush()
    assert run(db).solver_status == "INFEASIBLE"


def test_worker_availability_enforced(db):
    remove_maya(db)
    db.execute(
        delete(AvailabilityWindow).where(
            AvailabilityWindow.worker_id.in_(["sofia", "ethan", "jack"])
        )
    )
    db.flush()
    assert run(db).solver_status == "INFEASIBLE"


def test_existing_fixed_qualification_violation_reported(db):
    db.execute(delete(Skill).where(Skill.worker_id == "maya"))
    db.flush()
    d = run(db)
    assert d.solver_status == "INFEASIBLE"
    assert "preserved confirmed" in d.blockers[0]


def test_dependencies_enforced(db):
    remove_maya(db)
    d = run(db)
    assert d.proposals
    rough = next(p for p in d.proposals if p["task_id"] == "rough-in")
    inspection = next(p for p in d.proposals if p["task_id"] == "inspection")
    assert datetime.fromisoformat(inspection["starts_at"]) >= datetime.fromisoformat(
        rough["ends_at"]
    )


def test_dependency_cycle_rejected(db):
    db.add(TaskDependency(task_id="rough-in", predecessor_id="inspection"))
    db.flush()
    assert run(db).solver_status == "INVALID_INPUT"


def test_deadline_is_hard_constraint(db):
    db.get(Project, "eastside").deadline = at(9, 12)
    db.flush()
    assert run(db).solver_status == "INFEASIBLE"


def test_budget_is_hard_constraint(db):
    db.get(Project, "eastside").budget_cents = 1
    db.flush()
    d = run(db)
    assert d.solver_status == "INFEASIBLE"
    assert d.cost_cents is None


def test_site_capacity_enforced(db):
    db.get(Worksite, "fabrication-site").capacity = 1
    db.flush()
    assert run(db).solver_status == "INFEASIBLE"  # two fixed workers overlap on site


def test_timeout_not_reported_as_infeasible(db):
    assert run_with_limit(db, 0).solver_status == "UNKNOWN"


def run_with_limit(db, limit):
    return solve(db, db.get(Project, "eastside"), db.get(Membership, "demo-manager"), limit)


def test_partial_crews_are_filled_without_moving_fixed_members(db):
    db.get(Task, "rough-in").crew_size = 2
    db.flush()
    draft = run(db)
    assert draft.solver_status in {"OPTIMAL", "FEASIBLE"}
    assert any(p["task_id"] == "rough-in" and p["worker_id"] != "maya" for p in draft.proposals)


def test_fingerprint_changes_when_inputs_change(db):
    first = run(db).input_fingerprint
    db.get(Worker, "sofia").hourly_rate_cents += 1
    db.flush()
    assert run(db).input_fingerprint != first


def test_reset_repeatable_and_admin_only(client, db):
    assert client.post("/api/v1/demo/reset").status_code == 403
    h = {"X-Demo-Persona": "demo-admin"}
    client.post("/api/v1/assignments/assignment-maya/disrupt")
    client.post("/api/v1/projects/eastside/draft")
    assert client.post("/api/v1/demo/reset", headers=h).status_code == 200
    assert client.post("/api/v1/demo/reset", headers=h).status_code == 200
    assert db.get(Assignment, "assignment-maya").status == "confirmed"
    assert not list(db.scalars(select(ScheduleDraft)))


def test_reset_rejects_non_demo_data(client, db):
    db.add(Organization(id="real", name="Do not delete"))
    db.commit()
    assert (
        client.post("/api/v1/demo/reset", headers={"X-Demo-Persona": "demo-admin"}).status_code
        == 409
    )
    assert db.get(Organization, "real")


def test_busy_non_hour_aligned_blocks_intersected_slot(db):
    remove_maya(db)
    # Sofia cannot take a slot intersecting even 15 minutes of private busy time.
    commitment = db.scalar(select(PrivateCommitment).where(PrivateCommitment.worker_id == "sofia"))
    commitment.ends_at = at(9, 12) + timedelta(minutes=15)
    db.flush()
    d = run(db)
    p = next(p for p in d.proposals if p["task_id"] == "rough-in")
    if p["worker_id"] == "sofia":
        assert utc(datetime.fromisoformat(p["starts_at"])) >= at(9, 12) + timedelta(minutes=30)

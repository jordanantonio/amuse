from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from .auth import Database, Actor, managed_project
from .config import settings
from .models import Membership, ScheduleDraft, Assignment, Task, AuditEvent, WorkerAbsence
from .schemas import Dashboard, Persona, DraftView
from .views import dashboard
from .solver import solve
from .seed import reset

app = FastAPI(
    title="SHIFT Workforce API",
    version="0.1.0",
    description="Local fictional-data foundation. Demo personas are not authentication.",
)


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "demo": settings.demo_mode,
        "authentication": "local-demo-only",
        "solver": "OR-Tools CP-SAT",
    }


@app.get("/api/v1/personas", response_model=list[Persona])
def personas(db: Database):
    if not settings.demo_mode:
        raise HTTPException(404, "Demo personas disabled")
    # This endpoint is intentionally available only in the local demo.
    return list(db.scalars(select(Membership).where(Membership.organization_id == "northline")))


@app.get("/api/v1/dashboard", response_model=Dashboard)
def get_dashboard(db: Database, actor: Actor):
    return dashboard(db, actor)


@app.post("/api/v1/projects/{project_id}/draft", response_model=DraftView)
def generate_draft(project_id: str, db: Database, actor: Actor):
    project = managed_project(db, actor, project_id)
    try:
        draft = solve(db, project, actor)
        db.add(
            AuditEvent(
                organization_id=actor.organization_id,
                actor_id=actor.id,
                action="draft.generated",
                entity_id=draft.id,
            )
        )
        db.commit()
        db.refresh(draft)
        return draft
    except Exception:
        db.rollback()
        raise


@app.get("/api/v1/drafts", response_model=list[DraftView])
def get_drafts(db: Database, actor: Actor):
    if actor.role not in {"manager", "admin"}:
        raise HTTPException(403, "Drafts are manager-only")
    from .models import Project

    query = (
        select(ScheduleDraft).join(Project).where(Project.organization_id == actor.organization_id)
    )
    if actor.role == "manager":
        query = query.where(Project.manager_id == actor.id)
    return list(db.scalars(query.order_by(ScheduleDraft.created_at.desc())))


@app.post("/api/v1/assignments/{assignment_id}/disrupt", response_model=Dashboard)
def disrupt(assignment_id: str, db: Database, actor: Actor):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    task = db.get(Task, assignment.task_id)
    project = managed_project(db, actor, task.project_id)
    if assignment.status != "confirmed":
        raise HTTPException(409, "Only a confirmed assignment can be disrupted")
    # Explicit demo operation: unavailable for this project week, not a secret private calendar edit.
    assignment.status = "disrupted"
    db.add(
        WorkerAbsence(
            worker_id=assignment.worker_id,
            starts_at=project.starts_at,
            ends_at=project.deadline,
            recorded_by=actor.id,
        )
    )
    db.add(
        AuditEvent(
            organization_id=actor.organization_id,
            actor_id=actor.id,
            action="assignment.disrupted_and_absence_recorded",
            entity_id=assignment.id,
        )
    )
    db.commit()
    return dashboard(db, actor)


@app.post("/api/v1/demo/reset", response_model=Dashboard)
def demo_reset(db: Database, actor: Actor):
    if not settings.demo_mode:
        raise HTTPException(404, "Demo reset disabled")
    if actor.role != "admin":
        raise HTTPException(403, "Demo reset requires the demo administrator")
    # This route only resets the fixed fictional organization; don't run with real data.
    if actor.organization_id != "northline":
        raise HTTPException(403, "Not a demonstration organization")
    try:
        reset(db)
    except ValueError as error:
        db.rollback()
        raise HTTPException(409, str(error))
    return dashboard(db, db.get(Membership, "demo-admin"))

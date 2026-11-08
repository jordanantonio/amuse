from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import select
from .auth import Database, Actor, managed_project
from .config import settings
from .models import Membership, ScheduleDraft, Assignment, Task, AuditEvent, WorkerAbsence
from .schemas import Dashboard, Persona, DraftView
from .views import dashboard
from .solver import solve
from .seed import reset
from .inputs import AbsenceInput
from .locking import lock_schedule

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
        "authentication": "local-demo-only" if settings.demo_mode else "supabase-jwt",
        "supabase_url": settings.supabase_url if not settings.demo_mode else "",
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
def disrupt(assignment_id: str, db: Database, actor: Actor, payload: AbsenceInput | None = None):
    lock_schedule(db, actor.organization_id)
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    task = db.get(Task, assignment.task_id)
    project = managed_project(db, actor, task.project_id)
    if assignment.status != "confirmed":
        raise HTTPException(409, "Only a confirmed assignment can be disrupted")
    from .solver_time import utc

    start = payload.starts_at if payload else assignment.starts_at
    end = payload.ends_at if payload else assignment.ends_at
    if any(
        utc(a.starts_at) == utc(start) and utc(a.ends_at) == utc(end)
        for a in db.scalars(
            select(WorkerAbsence).where(WorkerAbsence.worker_id == assignment.worker_id)
        )
    ):
        raise HTTPException(409, "This absence is already recorded")
    # Record the requested absence; confirmed schedules change only at approved publication.
    db.add(
        WorkerAbsence(
            worker_id=assignment.worker_id,
            starts_at=payload.starts_at if payload else assignment.starts_at,
            ends_at=payload.ends_at if payload else assignment.ends_at,
            recorded_by=actor.id,
        )
    )
    db.add(
        AuditEvent(
            organization_id=actor.organization_id,
            actor_id=actor.id,
            action="worker.absence_recorded",
            entity_id=assignment.id,
        )
    )
    from .models import SchedulingEvent

    db.add(
        SchedulingEvent(
            project_id=project.id,
            kind="worker_absence",
            description="Worker unavailability recorded; confirmed work preserved pending recovery approval.",
        )
    )
    db.commit()
    return dashboard(db, actor)


@app.post("/api/v1/demo/reset", response_model=Dashboard)
def demo_reset(db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
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


from .adaptive_routes import router as adaptive_router
from .auth_routes import router as auth_router
from .market_routes import router as market_router
from .profile_routes import router as profile_router
from .posting_routes import dev as dev_router, router as posting_router

app.include_router(adaptive_router)
app.include_router(auth_router)
app.include_router(market_router)
app.include_router(profile_router)
app.include_router(posting_router)
app.include_router(dev_router)


@app.exception_handler(IntegrityError)
def constraint_conflict(request, error):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "This change conflicts with an existing record or schedule constraint. Refresh and try again."
        },
    )


@app.exception_handler(OperationalError)
def database_unavailable(request, error):
    return JSONResponse(
        status_code=503,
        content={"detail": "Scheduling storage is unavailable or busy. Please retry."},
    )

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from .auth import Actor, Database, managed_project
from .models import *
from .inputs import *
from .schemas import RecoveryView, BlockedPlan, ForecastView
from .locking import lock_schedule
from .solver import solve, utc, overlap
from . import recovery
from .weather import review, refresh_forecast
from .config import settings

router = APIRouter(prefix="/api/v1")


def own_worker(db, actor):
    worker = db.scalar(select(Worker).where(Worker.membership_id == actor.id))
    if actor.role != "worker" or not worker:
        raise HTTPException(403, "A worker profile is required")
    return worker


def committed_profile_valid(db, wid, skills, certs, windows=None):
    for a in db.scalars(
        select(Assignment).where(Assignment.worker_id == wid, Assignment.status == "confirmed")
    ):
        task = db.get(Task, a.task_id)
        if not set(task.required_skills) <= set(skills) or not all(
            any(c.name == name and utc(c.expires_at) >= utc(a.ends_at) for c in certs)
            for name in task.required_certifications
        ):
            raise HTTPException(
                409,
                "This would invalidate confirmed qualifications. Resolve the affected assignment first.",
            )
        if windows is not None and not any(
            utc(w.starts_at) <= utc(a.starts_at) and utc(w.ends_at) >= utc(a.ends_at)
            for w in windows
        ):
            raise HTTPException(
                409,
                "Availability must preserve confirmed work; report an absence to request recovery.",
            )


@router.put("/me/profile")
def update_profile(payload: ProfileInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    worker = own_worker(db, actor)
    committed_profile_valid(db, worker.id, payload.skills, payload.certifications)
    for a in db.scalars(
        select(Assignment).where(
            Assignment.worker_id == worker.id, Assignment.status == "confirmed"
        )
    ):
        task = db.get(Task, a.task_id)
        p = db.get(Project, task.project_id)
        site = db.get(Worksite, p.worksite_id)
        if task.work_mode not in payload.work_modes or (
            task.work_mode != "remote" and payload.location != site.location
        ):
            raise HTTPException(
                409, "Profile change conflicts with confirmed work mode or location"
            )
    for k in ("title", "location", "hourly_rate_cents", "work_modes"):
        setattr(worker, k, getattr(payload, k))
    db.execute(delete(Skill).where(Skill.worker_id == worker.id))
    db.execute(delete(Certification).where(Certification.worker_id == worker.id))
    db.add_all(
        Skill(worker_id=worker.id, name=s.strip())
        for s in dict.fromkeys(payload.skills)
        if s.strip()
    )
    db.add_all(Certification(worker_id=worker.id, **c.model_dump()) for c in payload.certifications)
    recovery.audit(db, actor, "worker.profile_updated", worker.id)
    db.commit()
    return {"id": worker.id}


@router.put("/me/availability")
def update_availability(payload: AvailabilityInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    worker = own_worker(db, actor)
    windows = sorted(payload.windows, key=lambda w: w.starts_at)
    if any(
        overlap(a.starts_at, a.ends_at, b.starts_at, b.ends_at)
        for a, b in zip(windows, windows[1:])
    ):
        raise HTTPException(422, "Published windows must not overlap")
    committed_profile_valid(
        db,
        worker.id,
        list(db.scalars(select(Skill.name).where(Skill.worker_id == worker.id))),
        list(db.scalars(select(Certification).where(Certification.worker_id == worker.id))),
        windows,
    )
    db.execute(delete(AvailabilityWindow).where(AvailabilityWindow.worker_id == worker.id))
    db.add_all(AvailabilityWindow(worker_id=worker.id, **w.model_dump()) for w in windows)
    recovery.audit(db, actor, "worker.availability_updated", worker.id)
    db.commit()
    return {"windows": len(windows)}


@router.post("/projects")
def create_project(payload: ProjectInput, db: Database, actor: Actor):
    if actor.role not in {"manager", "admin"}:
        raise HTTPException(403, "Manager required")
    if (payload.ends_at - payload.starts_at).days > 14:
        raise HTTPException(422, "Initial planning horizon is at most 14 days")
    lock_schedule(db, actor.organization_id)
    site = Worksite(
        organization_id=actor.organization_id,
        name=payload.name + " worksite",
        location=payload.location,
        capacity=payload.capacity,
    )
    db.add(site)
    db.flush()
    p = Project(
        organization_id=actor.organization_id,
        manager_id=actor.id,
        worksite_id=site.id,
        name=payload.name,
        client=payload.client,
        starts_at=payload.starts_at,
        deadline=payload.ends_at,
        budget_cents=payload.budget_cents,
        color="#8e7dcd",
    )
    db.add(p)
    db.flush()
    db.add(SchedulingPolicy(project_id=p.id))
    recovery.audit(db, actor, "project.created", p.id)
    db.commit()
    return {"id": p.id}


@router.put("/projects/{pid}")
def update_project(pid: str, payload: ProjectInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    p = managed_project(db, actor, pid)
    fixed = list(
        db.scalars(
            select(Assignment)
            .join(Task)
            .where(Task.project_id == pid, Assignment.status == "confirmed")
        )
    )
    if any(
        utc(a.starts_at) < utc(payload.starts_at) or utc(a.ends_at) > utc(payload.ends_at)
        for a in fixed
    ):
        raise HTTPException(409, "Date changes would exclude confirmed work")
    site = db.get(Worksite, p.worksite_id)
    if fixed and site.location != payload.location:
        raise HTTPException(409, "Resolve confirmed work before changing worksite location")
    p.name = payload.name
    p.client = payload.client
    p.starts_at = payload.starts_at
    p.deadline = payload.ends_at
    p.budget_cents = payload.budget_cents
    site.location = payload.location
    site.capacity = payload.capacity
    db.add(
        SchedulingEvent(
            project_id=pid,
            kind="project_updated",
            description="Project dates, capacity, or budget changed; review existing plans.",
        )
    )
    db.commit()
    return {"id": pid}


def write_task(db, actor, pid, payload, tid=None):
    managed_project(db, actor, pid)
    task = db.get(Task, tid) if tid else Task(project_id=pid)
    if tid and (not task or task.project_id != pid):
        raise HTTPException(404, "Task not found")
    if tid and db.scalar(
        select(Assignment.id).where(Assignment.task_id == tid, Assignment.status == "confirmed")
    ):
        raise HTTPException(
            409,
            "Confirmed task scope is frozen; recover its schedule before changing task requirements",
        )
    for pred in payload.predecessor_ids:
        t = db.get(Task, pred)
        if not t or t.project_id != pid or pred == tid:
            raise HTTPException(422, "Invalid task dependency")
    for k, v in payload.model_dump(exclude={"predecessor_ids"}).items():
        setattr(task, k, v)
    db.add(task)
    db.flush()
    db.execute(delete(TaskDependency).where(TaskDependency.task_id == task.id))
    db.add_all(
        TaskDependency(task_id=task.id, predecessor_id=pred)
        for pred in dict.fromkeys(payload.predecessor_ids)
    )
    db.flush()
    edges = list(
        db.scalars(
            select(TaskDependency)
            .join(Task, Task.id == TaskDependency.task_id)
            .where(Task.project_id == pid)
        )
    )
    graph = {t.id: [] for t in db.scalars(select(Task).where(Task.project_id == pid))}
    for edge in edges:
        graph[edge.task_id].append(edge.predecessor_id)

    def cycle(tid, path):
        return tid in path or any(cycle(p, path | {tid}) for p in graph[tid])

    if any(cycle(t, set()) for t in graph):
        raise HTTPException(422, "Task dependencies contain a cycle")
    recovery.audit(db, actor, "task.updated", task.id)
    db.commit()
    return {"id": task.id}


@router.post("/projects/{pid}/tasks")
def create_task(pid: str, payload: TaskInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    return write_task(db, actor, pid, payload)


@router.put("/projects/{pid}/tasks/{tid}")
def update_task(pid: str, tid: str, payload: TaskInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    return write_task(db, actor, pid, payload, tid)


@router.post("/jobs")
def create_job(payload: JobInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    managed_project(db, actor, payload.project_id)
    job = JobPosting(organization_id=actor.organization_id, **payload.model_dump())
    db.add(job)
    db.flush()
    recovery.audit(db, actor, "job.created", job.id)
    db.commit()
    return {"id": job.id}


@router.patch("/jobs/{jid}")
def job_state(jid: str, payload: JobStateInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    job = db.get(JobPosting, jid)
    if not job or job.organization_id != actor.organization_id:
        raise HTTPException(404, "Job not found")
    managed_project(db, actor, job.project_id)
    job.status = payload.status
    db.commit()
    return {"status": job.status}


@router.post("/jobs/{jid}/apply")
def apply(jid: str, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    worker = own_worker(db, actor)
    job = db.get(JobPosting, jid)
    if not job or job.organization_id != actor.organization_id or job.status != "open":
        raise HTTPException(404, "Open role not found")
    existing = db.scalar(
        select(Application).where(Application.job_id == jid, Application.worker_id == worker.id)
    )
    if existing:
        raise HTTPException(409, "You have already applied")
    application = Application(job_id=jid, worker_id=worker.id)
    db.add(application)
    db.flush()
    db.commit()
    return {"id": application.id}


@router.get("/applications")
def applications(db: Database, actor: Actor):
    query = (
        select(Application)
        .join(JobPosting)
        .where(JobPosting.organization_id == actor.organization_id)
    )
    if actor.role == "worker":
        query = query.where(Application.worker_id == own_worker(db, actor).id)
    elif actor.role == "manager":
        query = query.join(Project).where(Project.manager_id == actor.id)
    return [
        dict(
            id=a.id,
            job_id=a.job_id,
            job_title=db.get(JobPosting, a.job_id).title,
            worker_id=a.worker_id,
            worker_name=db.get(Worker, a.worker_id).name,
            project_id=db.get(JobPosting, a.job_id).project_id,
            status=a.status,
        )
        for a in db.scalars(query)
    ]


@router.get("/projects/{pid}/policy")
def get_policy(pid: str, db: Database, actor: Actor):
    managed_project(db, actor, pid)
    p = db.get(SchedulingPolicy, pid)
    return (
        {c.name: getattr(p, c.name) for c in SchedulingPolicy.__table__.columns}
        if p
        else dict(project_id=pid, **PolicyInput().model_dump())
    )


@router.put("/projects/{pid}/policy")
def policy(pid: str, payload: PolicyInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    managed_project(db, actor, pid)
    tids = set(db.scalars(select(Task.id).where(Task.project_id == pid)))
    if set(payload.task_weather_rules) - tids:
        raise HTTPException(422, "Weather policy contains tasks outside this project")
    p = db.get(SchedulingPolicy, pid) or SchedulingPolicy(project_id=pid)
    for k, v in payload.model_dump().items():
        setattr(p, k, v)
    db.add(p)
    recovery.audit(db, actor, "policy.updated", pid)
    db.commit()
    return {"project_id": pid}


@router.get("/projects/{pid}/weather", response_model=list[ForecastView])
def forecasts(pid: str, db: Database, actor: Actor):
    managed_project(db, actor, pid)
    return [
        dict(
            id=f.id,
            starts_at=utc(f.starts_at),
            ends_at=utc(f.ends_at),
            rain_probability=f.rain_probability,
            precipitation_mm=f.precipitation_mm,
            wind_kph=f.wind_kph,
            temperature_c=f.temperature_c,
            source=f.source,
            simulated=f.simulated,
            fetched_at=utc(f.fetched_at),
        )
        for f in db.scalars(
            select(WeatherForecast)
            .where(WeatherForecast.project_id == pid)
            .order_by(WeatherForecast.starts_at)
        )
    ]


@router.post("/projects/{pid}/weather")
def forecast_update(pid: str, payload: ForecastInput, db: Database, actor: Actor):
    if not settings.demo_mode:
        raise HTTPException(403, "Simulated forecast controls are demo-only")
    lock_schedule(db, actor.organization_id)
    project = managed_project(db, actor, pid)
    changed = refresh_forecast(db, project, payload.adverse)
    db.commit()
    return {"changed": changed, "simulated": True}


@router.post("/projects/{pid}/review")
def risk_review(pid: str, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    project = managed_project(db, actor, pid)
    output = review(db, project)
    db.commit()
    return output


@router.post("/projects/{pid}/proposals", response_model=list[RecoveryView | BlockedPlan])
def generate_proposals(pid: str, payload: ProposalInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    project = managed_project(db, actor, pid)
    plans = recovery.new_proposals(db, actor, project, list(dict.fromkeys(payload.objectives)))
    db.commit()
    return [p if isinstance(p, dict) else recovery.proposal_view(db, actor, p) for p in plans]


@router.get("/proposals", response_model=list[RecoveryView])
def proposals(db: Database, actor: Actor):
    query = (
        select(RecoveryProposal)
        .join(Project)
        .where(Project.organization_id == actor.organization_id)
    )
    if actor.role == "manager":
        query = query.where(Project.manager_id == actor.id)
    if actor.role == "worker":
        query = query.join(WorkerConfirmation).where(
            WorkerConfirmation.worker_id == own_worker(db, actor).id
        )
    return [
        recovery.proposal_view(db, actor, p)
        for p in db.scalars(query.order_by(RecoveryProposal.created_at.desc()))
    ]


@router.get("/proposals/{pid}", response_model=RecoveryView)
def proposal(pid: str, db: Database, actor: Actor):
    return recovery.proposal_view(db, actor, recovery.scoped_proposal(db, actor, pid))


@router.post("/proposals/{pid}/decision", response_model=RecoveryView)
def proposal_decision(pid: str, payload: DecisionInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    p = recovery.scoped_proposal(db, actor, pid, True)
    recovery.decide(db, actor, p, payload.decision, payload.comment)
    db.commit()
    return recovery.proposal_view(db, actor, p)


@router.post("/proposals/{pid}/confirmation", response_model=RecoveryView)
def proposal_confirmation(pid: str, payload: ConfirmationInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    p = recovery.scoped_proposal(db, actor, pid)
    recovery.confirm(db, actor, p, payload.decision)
    db.commit()
    return recovery.proposal_view(db, actor, p)


@router.post("/proposals/{pid}/publish", response_model=RecoveryView)
def proposal_publish(pid: str, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    p = recovery.scoped_proposal(db, actor, pid, True)
    recovery.publish(db, actor, p)
    db.commit()
    return recovery.proposal_view(db, actor, p)


@router.get("/history")
def history(db: Database, actor: Actor):
    if actor.role not in {"manager", "admin"}:
        raise HTTPException(403, "Manager required")
    # Project managers only receive events for projects they manage, plus their own actions.
    visible = set(
        db.scalars(
            select(Project.id).where(
                Project.organization_id == actor.organization_id, Project.manager_id == actor.id
            )
        )
    )
    visible.update(
        db.scalars(select(RecoveryProposal.id).where(RecoveryProposal.project_id.in_(visible)))
    )
    return [
        dict(
            id=e.id,
            action=e.action,
            actor=db.get(Membership, e.actor_id).name,
            entity_id=e.entity_id,
            created_at=utc(e.created_at),
        )
        for e in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == actor.organization_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(100)
        )
        if actor.role == "admin" or e.actor_id == actor.id or e.entity_id in visible
    ]


@router.post("/me/absence")
def report_absence(payload: AbsenceInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    worker = own_worker(db, actor)
    db.add(
        WorkerAbsence(
            worker_id=worker.id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            recorded_by=actor.id,
        )
    )
    affected = set()
    for a in db.scalars(
        select(Assignment).where(
            Assignment.worker_id == worker.id, Assignment.status == "confirmed"
        )
    ):
        if overlap(a.starts_at, a.ends_at, payload.starts_at, payload.ends_at):
            affected.add(db.get(Task, a.task_id).project_id)
    for pid in affected:
        db.add(
            SchedulingEvent(
                project_id=pid,
                kind="worker_absence",
                description="Worker reported unavailability; confirmed work requires review.",
            )
        )
    recovery.audit(db, actor, "worker.absence_reported", worker.id)
    db.commit()
    return {"affected_projects": len(affected)}


@router.post("/applications/{aid}/invite", response_model=RecoveryView)
def invite_applicant(aid: str, payload: InviteInput, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    application = db.get(Application, aid)
    job = db.get(JobPosting, application.job_id) if application else None
    if not job or job.organization_id != actor.organization_id:
        raise HTTPException(404, "Application not found")
    project = managed_project(db, actor, job.project_id)
    task = db.get(Task, payload.task_id)
    if not task or task.project_id != project.id:
        raise HTTPException(422, "Select a task in the advertised project")
    if db.scalar(
        select(Assignment.id).where(Assignment.task_id == task.id, Assignment.status == "confirmed")
    ):
        raise HTTPException(
            409, "Choose an unstaffed task; confirmed work must go through recovery"
        )
    plans = recovery.new_proposals(
        db, actor, project, ["lowest_cost"], candidate_workers={task.id: [application.worker_id]}
    )
    valid = [p for p in plans if isinstance(p, RecoveryProposal)]
    if not valid:
        raise HTTPException(
            409,
            {
                "message": "Applicant cannot be assigned under this project’s constraints.",
                "blockers": [b for p in plans for b in p.get("blockers", [])],
            },
        )
    application.status = "reviewing"
    db.commit()
    return recovery.proposal_view(db, actor, valid[0])


@router.post("/applications/{aid}/withdraw")
def withdraw_application(aid: str, db: Database, actor: Actor):
    lock_schedule(db, actor.organization_id)
    worker = own_worker(db, actor)
    application = db.get(Application, aid)
    if not application or application.worker_id != worker.id:
        raise HTTPException(404, "Application not found")
    application.status = "withdrawn"
    db.commit()
    return {"status": "withdrawn"}

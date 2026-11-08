from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import *
from .schemas import *
from .solver_time import overlap
from .config import settings


def dashboard(db: Session, actor: Membership) -> Dashboard:
    org = db.get(Organization, actor.organization_id)
    projects = list(
        db.scalars(select(Project).where(Project.organization_id == actor.organization_id))
    )
    if actor.role == "manager":
        projects = [p for p in projects if p.manager_id == actor.id]
    all_workers = list(
        db.scalars(select(Worker).where(Worker.organization_id == actor.organization_id))
    )
    own = next((w for w in all_workers if w.membership_id == actor.id), None)
    workers = (
        [own] if actor.role == "worker" and own else [] if actor.role == "worker" else all_workers
    )
    all_tasks = list(db.scalars(select(Task).where(Task.project_id.in_([p.id for p in projects]))))
    all_assignments = list(
        db.scalars(select(Assignment).where(Assignment.task_id.in_([t.id for t in all_tasks])))
    )
    # Worker sees only projects where assigned, plus role postings independently.
    if actor.role == "worker":
        all_assignments = [a for a in all_assignments if own and a.worker_id == own.id]
        project_ids = {
            t.project_id for t in all_tasks if t.id in {a.task_id for a in all_assignments}
        }
        projects = [p for p in projects if p.id in project_ids]
        all_tasks = [t for t in all_tasks if t.project_id in project_ids]
    wviews = []
    for w in workers:
        # Managers receive opaque cross-project busy intervals, not assignment details.
        commitments = list(
            db.scalars(select(PrivateCommitment).where(PrivateCommitment.worker_id == w.id))
        ) + list(db.scalars(select(WorkerAbsence).where(WorkerAbsence.worker_id == w.id)))
        other_assignments = list(
            db.scalars(
                select(Assignment)
                .join(Task)
                .where(
                    Assignment.worker_id == w.id,
                    Assignment.status == "confirmed",
                    Task.project_id.not_in([p.id for p in projects]),
                )
            )
        )
        data = {
            c.name: getattr(w, c.name)
            for c in Worker.__table__.columns
            if c.name not in {"membership_id", "organization_id"}
        }
        wviews.append(
            WorkerView(
                **data,
                skills=list(db.scalars(select(Skill.name).where(Skill.worker_id == w.id))),
                certifications=[
                    Certificate.model_validate(c)
                    for c in db.scalars(
                        select(Certification).where(Certification.worker_id == w.id)
                    )
                ],
                availability=[
                    Window(starts_at=a.starts_at, ends_at=a.ends_at)
                    for a in db.scalars(
                        select(AvailabilityWindow).where(AvailabilityWindow.worker_id == w.id)
                    )
                ],
                busy=[
                    Window(starts_at=a.starts_at, ends_at=a.ends_at)
                    for a in commitments + other_assignments
                ],
            )
        )
    pviews = []
    gaps = 0
    for p in projects:
        site = db.get(Worksite, p.worksite_id)
        task_views = []
        for t in [t for t in all_tasks if t.project_id == p.id]:
            count = len(
                {
                    a.worker_id
                    for a in all_assignments
                    if a.task_id == t.id and a.status == "confirmed"
                }
            )
            if actor.role != "worker":
                absences = list(db.scalars(select(WorkerAbsence)))
                unavailable = {
                    a.worker_id
                    for a in all_assignments
                    if a.task_id == t.id
                    and a.status == "confirmed"
                    and any(
                        b.worker_id == a.worker_id
                        and overlap(a.starts_at, a.ends_at, b.starts_at, b.ends_at)
                        for b in absences
                    )
                }
                gaps += max(0, t.crew_size - count) + len(unavailable)
            task_views.append(
                TaskView(
                    id=t.id,
                    project_id=p.id,
                    name=t.name,
                    duration_hours=t.duration_hours,
                    crew_size=t.crew_size,
                    required_skills=t.required_skills,
                    required_certifications=t.required_certifications,
                    work_mode=t.work_mode,
                    confirmed_count=count,
                    predecessor_ids=list(
                        db.scalars(
                            select(TaskDependency.predecessor_id).where(
                                TaskDependency.task_id == t.id
                            )
                        )
                    ),
                )
            )
        pviews.append(
            ProjectView(
                id=p.id,
                name=p.name,
                client=p.client,
                starts_at=p.starts_at,
                deadline=p.deadline,
                budget_cents=p.budget_cents,
                color=p.color,
                location=site.location,
                capacity=site.capacity,
                tasks=task_views,
            )
        )
    amap = {t.id: t for t in all_tasks}
    pmap = {p.id: p for p in projects}
    wmap = {w.id: w for w in all_workers}
    aviews = [
        AssignmentView(
            id=a.id,
            task_id=a.task_id,
            task_name=amap[a.task_id].name,
            project_id=amap[a.task_id].project_id,
            project_name=pmap[amap[a.task_id].project_id].name,
            worker_id=a.worker_id,
            worker_name=wmap[a.worker_id].name,
            starts_at=a.starts_at,
            ends_at=a.ends_at,
            status=a.status,
            color=pmap[amap[a.task_id].project_id].color,
        )
        for a in all_assignments
    ]
    jobs = list(
        db.scalars(
            select(JobPosting).where(
                JobPosting.organization_id == actor.organization_id, JobPosting.status == "open"
            )
        )
    )
    today = datetime.now(ZoneInfo("America/Edmonton")).date()
    current_week = (today - timedelta(days=today.weekday())).isoformat()
    return Dashboard(
        organization=org.name,
        persona=Persona.model_validate(actor),
        demo=settings.demo_mode,
        week_start="2026-11-09" if settings.demo_mode else current_week,
        timezone="America/Edmonton",
        workers=wviews,
        projects=pviews,
        assignments=aviews,
        jobs=[JobView.model_validate(j) for j in jobs],
        staffing_gaps=gaps,
    )

"""Human-approved recovery lifecycle. Caller holds tenant transaction lock."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from fastapi import HTTPException
from .models import *
from .solver import solve, scheduling_fingerprint, utc
from .weather import review
from .auth import managed_project

TERMINAL = {"published", "rejected", "expired", "revision_requested"}


def audit(db, actor, action, entity):
    db.add(
        AuditEvent(
            organization_id=actor.organization_id,
            actor_id=actor.id,
            action=action,
            entity_id=entity,
        )
    )


def assignment_record(db, a):
    t = db.get(Task, a.task_id)
    w = db.get(Worker, a.worker_id)
    return dict(
        id=a.id,
        task_id=a.task_id,
        task_name=t.name,
        worker_id=a.worker_id,
        worker_name=w.name,
        starts_at=utc(a.starts_at).isoformat(),
        ends_at=utc(a.ends_at).isoformat(),
        cost_cents=round(
            (utc(a.ends_at) - utc(a.starts_at)).total_seconds() / 3600 * w.hourly_rate_cents
        ),
    )


def new_proposals(db, actor, project, objectives, candidate_workers=None):
    risks = review(db, project)["risks"]
    movable = {r["task_id"] for r in risks if r["assignment_ids"]}
    deps = list(
        db.scalars(
            select(TaskDependency)
            .join(Task, Task.id == TaskDependency.task_id)
            .where(Task.project_id == project.id)
        )
    )
    changed = True
    while changed:
        before = len(movable)
        movable.update(d.task_id for d in deps if d.predecessor_id in movable)
        changed = len(movable) > before
    assignments = list(
        db.scalars(
            select(Assignment)
            .join(Task)
            .where(Task.project_id == project.id, Assignment.status == "confirmed")
        )
    )
    original = [assignment_record(db, a) for a in assignments]
    replaced = [a.id for a in assignments if a.task_id in movable]
    plans = []
    for objective in objectives:
        draft = solve(
            db,
            project,
            actor,
            objective=objective,
            movable_task_ids=movable,
            candidate_workers=candidate_workers,
        )
        if draft.solver_status not in {"OPTIMAL", "FEASIBLE"}:
            plans.append(
                dict(
                    solver_status=draft.solver_status, blockers=draft.blockers, objective=objective
                )
            )
            continue
        if not draft.proposals:
            plans.append(
                dict(
                    solver_status="NO_CHANGE",
                    blockers=["No uncovered or at-risk work requires a change."],
                    objective=objective,
                )
            )
            continue
        preserved = [r for r in original if r["id"] not in replaced]
        completion = max(
            (p["ends_at"] for p in preserved + draft.proposals),
            default=utc(project.starts_at).isoformat(),
        )
        oldcost = sum(p["cost_cents"] for p in original)
        original_end = max(
            (p["ends_at"] for p in original), default=utc(project.starts_at).isoformat()
        )
        policy = db.get(SchedulingPolicy, project.id)
        minutes_remaining = max(
            0,
            round(
                (utc(project.deadline) - datetime.fromisoformat(completion)).total_seconds() / 60
            ),
        )
        metrics = dict(
            labour_cost_cents=draft.cost_cents,
            cost_difference_cents=(draft.cost_cents or 0) - oldcost,
            completion_at=completion,
            completion_difference_minutes=round(
                (
                    datetime.fromisoformat(completion) - datetime.fromisoformat(original_end)
                ).total_seconds()
                / 60
            ),
            changed_assignments=len(replaced),
            new_assignments=len(draft.proposals),
            contingency_reserved_minutes=policy.contingency_minutes if policy else 0,
            contingency_consumed_minutes=0,
            remaining_deadline_minutes=minutes_remaining,
            task_buffer_minutes=sum(
                max(
                    0,
                    round(
                        (
                            datetime.fromisoformat(p["ends_at"])
                            - datetime.fromisoformat(p["starts_at"])
                        ).total_seconds()
                        / 60
                    )
                    - db.get(Task, p["task_id"]).duration_hours * 60,
                )
                for p in draft.proposals
            ),
            solver_status=draft.solver_status,
        )
        reason = (
            "; ".join(dict.fromkeys(r["reason"] for r in risks))
            or "Fill unstaffed project tasks while preserving confirmed commitments."
        )
        proposal = RecoveryProposal(
            project_id=project.id,
            draft_id=draft.id,
            created_by=actor.id,
            original_fingerprint=draft.input_fingerprint,
            original_schedule=original,
            proposed_schedule=draft.proposals,
            replaces_assignment_ids=replaced,
            objective=objective,
            reason=reason[:2000],
            status="pending_approval",
            metrics=metrics,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(proposal)
        db.flush()
        audit(db, actor, "proposal.generated", proposal.id)
        plans.append(proposal)
    return plans


def scoped_proposal(db, actor, pid, manager=False):
    p = db.get(RecoveryProposal, pid)
    project = db.get(Project, p.project_id) if p else None
    if not p or not project or project.organization_id != actor.organization_id:
        raise HTTPException(404, "Proposal not found")
    if manager:
        managed_project(db, actor, p.project_id)
    elif actor.role == "worker":
        worker = db.scalar(select(Worker).where(Worker.membership_id == actor.id))
        if not worker or not db.scalar(
            select(WorkerConfirmation.id).where(
                WorkerConfirmation.proposal_id == pid, WorkerConfirmation.worker_id == worker.id
            )
        ):
            raise HTTPException(404, "Proposal not found")
    elif actor.role == "manager":
        managed_project(db, actor, p.project_id)
    return p


def expire(db, p):
    if p.status not in TERMINAL and utc(p.expires_at) <= datetime.now(timezone.utc):
        p.status = "expired"
        db.execute(delete(SlotReservation).where(SlotReservation.proposal_id == p.id))
        db.flush()


def validate(db, p, actor):
    project = db.get(Project, p.project_id)
    if p.original_fingerprint != scheduling_fingerprint(db, project):
        raise HTTPException(
            409, "Proposal is stale: scheduling inputs changed. Generate a new plan."
        )
    moved = {r["task_id"] for r in p.original_schedule if r["id"] in p.replaces_assignment_ids}
    # The same CP-SAT constraints validate the exact stored placements, not a new optimized plan.
    checked = solve(
        db,
        project,
        actor,
        objective=p.objective,
        movable_task_ids=moved,
        forced=p.proposed_schedule,
        reservation_exclude=p.id,
        persist=False,
    )
    if checked.solver_status not in {"OPTIMAL", "FEASIBLE"}:
        raise HTTPException(
            409,
            {
                "message": "Proposal is no longer feasible; re-optimize.",
                "blockers": checked.blockers,
            },
        )
    return project


def decide(db, actor, p, decision, comment):
    expire(db, p)
    if p.status not in {"pending_approval", "awaiting_confirmation", "ready_to_publish"}:
        raise HTTPException(409, "Proposal no longer accepts scheduling decisions")
    if decision == "approve":
        if p.status != "pending_approval":
            raise HTTPException(409, "Proposal has already been approved")
        validate(db, p, actor)
        for wid in {slot["worker_id"] for slot in p.proposed_schedule}:
            db.add(WorkerConfirmation(proposal_id=p.id, worker_id=wid, status="pending"))
        p.status = "awaiting_confirmation"
    elif decision in {"reject", "request_revision"}:
        p.status = "rejected" if decision == "reject" else "revision_requested"
        db.execute(delete(SlotReservation).where(SlotReservation.proposal_id == p.id))
    else:
        raise HTTPException(422, "Unknown approval decision")
    db.add(
        ApprovalDecision(proposal_id=p.id, actor_id=actor.id, decision=decision, comment=comment)
    )
    audit(db, actor, "proposal." + decision, p.id)
    db.flush()


def confirm(db, actor, p, decision):
    worker = db.scalar(select(Worker).where(Worker.membership_id == actor.id))
    if actor.role != "worker" or not worker:
        raise HTTPException(403, "Only the affected worker may respond")
    response = db.scalar(
        select(WorkerConfirmation).where(
            WorkerConfirmation.proposal_id == p.id, WorkerConfirmation.worker_id == worker.id
        )
    )
    if not response:
        raise HTTPException(403, "No confirmation is assigned to you")
    expire(db, p)
    if p.status != "awaiting_confirmation" or response.status != "pending":
        raise HTTPException(409, "Confirmation is no longer pending")
    if decision not in {"accept", "decline"}:
        raise HTTPException(422, "Choose accept or decline")
    if decision == "accept":
        validate(db, p, actor)
        for slot in p.proposed_schedule:
            if slot["worker_id"] == worker.id:
                db.add(
                    SlotReservation(
                        proposal_id=p.id,
                        task_id=slot["task_id"],
                        worker_id=worker.id,
                        starts_at=datetime.fromisoformat(slot["starts_at"]),
                        ends_at=datetime.fromisoformat(slot["ends_at"]),
                    )
                )
        response.status = "accepted"
    else:
        response.status = "declined"
        p.status = "revision_requested"
        db.execute(delete(SlotReservation).where(SlotReservation.proposal_id == p.id))
        db.add(
            SchedulingEvent(
                project_id=p.project_id,
                kind="contractor_declined",
                description="A worker declined proposed work; generate revised alternatives.",
            )
        )
    response.responded_at = datetime.now(timezone.utc)
    db.flush()
    all_responses = list(
        db.scalars(select(WorkerConfirmation).where(WorkerConfirmation.proposal_id == p.id))
    )
    if all(r.status == "accepted" for r in all_responses):
        p.status = "ready_to_publish"
    audit(db, actor, "worker." + decision, p.id)


def publish(db, actor, p):
    expire(db, p)
    if p.status != "ready_to_publish":
        raise HTTPException(409, "All affected workers must accept before publishing")
    confirmations = list(
        db.scalars(select(WorkerConfirmation).where(WorkerConfirmation.proposal_id == p.id))
    )
    if not confirmations or any(c.status != "accepted" for c in confirmations):
        raise HTTPException(409, "Worker confirmations incomplete")
    validate(db, p, actor)
    for aid in p.replaces_assignment_ids:
        original = db.get(Assignment, aid)
        if not original or original.status != "confirmed":
            raise HTTPException(409, "Original assignment changed; regenerate")
        original.status = "cancelled"
    db.flush()
    for slot in p.proposed_schedule:
        db.add(
            Assignment(
                task_id=slot["task_id"],
                worker_id=slot["worker_id"],
                starts_at=datetime.fromisoformat(slot["starts_at"]),
                ends_at=datetime.fromisoformat(slot["ends_at"]),
                status="confirmed",
            )
        )
    db.execute(delete(SlotReservation).where(SlotReservation.proposal_id == p.id))
    p.status = "published"
    p.published_at = datetime.now(timezone.utc)
    audit(db, actor, "schedule.published", p.id)
    db.flush()


def proposal_view(db, actor, p):
    project = db.get(Project, p.project_id)
    confirmations = list(
        db.scalars(select(WorkerConfirmation).where(WorkerConfirmation.proposal_id == p.id))
    )
    worker = (
        db.scalar(select(Worker).where(Worker.membership_id == actor.id))
        if actor.role == "worker"
        else None
    )
    return dict(
        id=p.id,
        project_id=p.project_id,
        project_name=project.name,
        objective=p.objective,
        status="expired"
        if p.status not in TERMINAL and utc(p.expires_at) <= datetime.now(timezone.utc)
        else p.status,
        reason=p.reason,
        created_at=utc(p.created_at),
        expires_at=utc(p.expires_at),
        published_at=utc(p.published_at) if p.published_at else None,
        stale=p.status not in TERMINAL
        and p.original_fingerprint != scheduling_fingerprint(db, project),
        original_schedule=[] if worker else p.original_schedule,
        proposed_schedule=[
            s for s in p.proposed_schedule if not worker or s["worker_id"] == worker.id
        ],
        replaces_assignment_ids=[] if worker else p.replaces_assignment_ids,
        metrics={} if worker else p.metrics,
        confirmations=[
            dict(
                id=c.id,
                worker_id=c.worker_id,
                worker_name=db.get(Worker, c.worker_id).name,
                status=c.status,
            )
            for c in confirmations
            if not worker or c.worker_id == worker.id
        ],
        history=[]
        if worker
        else [
            dict(
                decision=h.decision,
                actor=db.get(Membership, h.actor_id).name,
                comment=h.comment,
                created_at=utc(h.created_at),
            )
            for h in db.scalars(
                select(ApprovalDecision)
                .where(ApprovalDecision.proposal_id == p.id)
                .order_by(ApprovalDecision.created_at)
            )
        ],
    )

"""Real CP-SAT model, hourly non-preemptive tasks; drafts never mutate assignments."""

import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import *
from .projections import hosted, busy_windows, external_commitments


def utc(value: datetime):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def overlap(a, b, c, d):
    return utc(a) < utc(d) and utc(c) < utc(b)


def solve(
    db: Session, project: Project, actor: Membership, limit_seconds: float = 5
) -> ScheduleDraft:
    workers = list(
        db.scalars(select(Worker).where(Worker.organization_id == project.organization_id))
    )
    tasks = list(db.scalars(select(Task).where(Task.project_id == project.id)))
    wids = [w.id for w in workers]
    all_projects = list(
        db.scalars(select(Project).where(Project.organization_id == project.organization_id))
    )
    all_tasks = list(
        db.scalars(select(Task).where(Task.project_id.in_([p.id for p in all_projects])))
    )
    all_assignments = list(
        db.scalars(
            select(Assignment).where(
                Assignment.worker_id.in_(wids), Assignment.status == "confirmed"
            )
        )
    )
    deps = list(
        db.scalars(select(TaskDependency).where(TaskDependency.task_id.in_([t.id for t in tasks])))
    )
    availability = list(
        db.scalars(select(AvailabilityWindow).where(AvailabilityWindow.worker_id.in_(wids)))
    )
    busy = list(
        db.scalars(select(PrivateCommitment).where(PrivateCommitment.worker_id.in_(wids)))
    ) + list(db.scalars(select(WorkerAbsence).where(WorkerAbsence.worker_id.in_(wids))))
    skills = list(db.scalars(select(Skill).where(Skill.worker_id.in_(wids))))
    certs = list(db.scalars(select(Certification).where(Certification.worker_id.in_(wids))))
    sites = list(
        db.scalars(select(Worksite).where(Worksite.organization_id == project.organization_id))
    )
    external = []
    if hosted(db):
        external = external_commitments(db, project.id)
        external_ids = {a.id for a in external}
        all_assignments = [a for a in all_assignments if a.task_id in {t.id for t in tasks}]
        busy = [a for a in busy_windows(db) if a.id not in external_ids]
    # Fingerprint all scheduling-relevant inputs. Private labels never leave service.
    records = (
        [project]
        + workers
        + tasks
        + all_projects
        + all_tasks
        + all_assignments
        + deps
        + availability
        + busy
        + skills
        + certs
        + sites
        + external
    )
    def snapshot(record):
        values = (
            {column.name: getattr(record, column.name) for column in record.__table__.columns}
            if hasattr(record, "__table__") else vars(record)
        )
        return {
            key: utc(value).isoformat() if isinstance(value, datetime) else value
            for key, value in values.items() if key != "private_label"
        }

    snap = [snapshot(record) for record in records]
    fingerprint = hashlib.sha256(json.dumps(snap, sort_keys=True, default=str).encode()).hexdigest()

    def result(status, blockers=None, proposals=None, cost=None):
        draft = ScheduleDraft(
            project_id=project.id,
            created_by=actor.id,
            input_fingerprint=fingerprint,
            solver_status=status,
            blockers=blockers or [],
            proposals=proposals or [],
            cost_cents=cost,
            status="draft",
        )
        db.add(draft)
        db.flush()
        return draft

    start = utc(project.starts_at)
    deadline = utc(project.deadline)
    if (
        any(v.minute or v.second or v.microsecond for v in (start, deadline))
        or deadline <= start
        or deadline - start > timedelta(days=14)
    ):
        return result(
            "INVALID_INPUT",
            [
                "Foundation requires hour-aligned project boundaries and a positive horizon of at most 14 days."
            ],
        )
    horizon = int((deadline - start).total_seconds() / 3600)
    tmap = {t.id: t for t in all_tasks}
    pmap = {p.id: p for p in all_projects}
    smap = {s.id: s for s in sites}
    site = smap[project.worksite_id]
    graph = {t.id: [] for t in tasks}
    for d in deps:
        if d.predecessor_id not in graph:
            return result("INVALID_INPUT", ["Dependencies must remain within this project."])
        graph[d.task_id].append(d.predecessor_id)
    visiting = set()
    visited = set()

    def cycle(tid):
        if tid in visiting:
            return True
        if tid in visited:
            return False
        visiting.add(tid)
        if any(cycle(p) for p in graph[tid]):
            return True
        visiting.remove(tid)
        visited.add(tid)
        return False

    if any(cycle(t.id) for t in tasks):
        return result("INVALID_INPUT", ["Task dependency graph contains a cycle."])
    model = cp_model.CpModel()
    worker_intervals = defaultdict(list)
    site_intervals = []
    site_demands = []
    starts = {}
    ends = {}
    choices = []
    cost_terms = []
    blockers = []
    fixed_cost = 0

    def hours(v):
        return (utc(v) - start).total_seconds() / 3600

    # Fixed commitments are rounded outward so non-aligned busy windows cannot leak.
    for a in all_assignments + busy:
        lo = math.floor(hours(a.starts_at))
        hi = math.ceil(hours(a.ends_at))
        if hi <= 0 or lo >= horizon:
            continue
        interval = model.new_fixed_size_interval_var(lo, hi - lo, "fixed_" + a.id)
        worker_intervals[a.worker_id].append(interval)
        if isinstance(a, Assignment):
            task = tmap[a.task_id]
            p = pmap[task.project_id]
            if p.worksite_id == site.id and task.work_mode != "remote":
                site_intervals.append(interval)
                site_demands.append(1)
    for a in external:
        lo, hi = math.floor(hours(a.starts_at)), math.ceil(hours(a.ends_at))
        if hi <= 0 or lo >= horizon:
            continue
        interval = model.new_fixed_size_interval_var(lo, hi - lo, "external_" + a.id)
        worker_intervals[a.worker_id].append(interval)
        if a.same_site and a.onsite:
            site_intervals.append(interval)
            site_demands.append(1)
    for t in tasks:
        fixed = [a for a in all_assignments if a.task_id == t.id]
        if fixed:
            if len(fixed) != t.crew_size or len({a.worker_id for a in fixed}) != len(fixed):
                return result(
                    "INVALID_INPUT",
                    [
                        f"{t.name}: partial or duplicate fixed crews require the crew-recovery milestone."
                    ],
                )
            if len({(utc(a.starts_at), utc(a.ends_at)) for a in fixed}) != 1:
                return result(
                    "INVALID_INPUT", [f"{t.name}: fixed crew must share a start and end."]
                )
            for committed in fixed:
                worker = next(w for w in workers if w.id == committed.worker_id)
                eligible_skills = set(t.required_skills) <= {
                    s.name for s in skills if s.worker_id == worker.id
                }
                eligible_certs = all(
                    any(
                        c.worker_id == worker.id
                        and c.name == name
                        and utc(c.expires_at) >= utc(committed.ends_at)
                        for c in certs
                    )
                    for name in t.required_certifications
                )
                available = any(
                    a.worker_id == worker.id
                    and utc(a.starts_at) <= utc(committed.starts_at)
                    and utc(a.ends_at) >= utc(committed.ends_at)
                    for a in availability
                )
                if (
                    not eligible_skills
                    or not eligible_certs
                    or not available
                    or t.work_mode not in worker.work_modes
                    or (t.work_mode != "remote" and worker.location != site.location)
                ):
                    return result(
                        "INFEASIBLE",
                        [
                            f"{t.name}: a preserved confirmed assignment conflicts with qualifications, published availability, work mode, or location. Explicitly resolve the commitment before replanning."
                        ],
                    )
            a = fixed[0]
            if (
                hours(a.starts_at) != int(hours(a.starts_at))
                or hours(a.ends_at) - hours(a.starts_at) != t.duration_hours
            ):
                return result(
                    "INVALID_INPUT",
                    [f"{t.name}: confirmed duration is not supported by the hourly model."],
                )
            starts[t.id] = model.new_int_var(
                int(hours(a.starts_at)), int(hours(a.starts_at)), "start_" + t.id
            )
            ends[t.id] = model.new_int_var(
                int(hours(a.ends_at)), int(hours(a.ends_at)), "end_" + t.id
            )
            model.add(starts[t.id] >= 0)
            model.add(ends[t.id] <= horizon)
            fixed_cost += sum(
                next(w.hourly_rate_cents for w in workers if w.id == a.worker_id) * t.duration_hours
                for a in fixed
            )
            continue
        starts[t.id] = model.new_int_var(0, horizon, "start_" + t.id)
        ends[t.id] = model.new_int_var(0, horizon, "end_" + t.id)
        model.add(ends[t.id] == starts[t.id] + t.duration_hours)
        task_choices = []
        worker_choices = defaultdict(list)
        for w in workers:
            if not set(t.required_skills) <= {s.name for s in skills if s.worker_id == w.id}:
                continue
            if t.work_mode not in w.work_modes:
                continue
            if t.work_mode != "remote" and w.location != site.location:
                continue
            for h in range(max(0, horizon - t.duration_hours + 1)):
                begins = start + timedelta(hours=h)
                ends_at = begins + timedelta(hours=t.duration_hours)
                if not all(
                    any(
                        c.worker_id == w.id and c.name == required and utc(c.expires_at) >= ends_at
                        for c in certs
                    )
                    for required in t.required_certifications
                ):
                    continue
                if not any(
                    a.worker_id == w.id and utc(a.starts_at) <= begins and utc(a.ends_at) >= ends_at
                    for a in availability
                ):
                    continue
                if any(
                    a.worker_id == w.id and overlap(begins, ends_at, a.starts_at, a.ends_at)
                    for a in all_assignments + busy
                ):
                    continue
                chosen = model.new_bool_var(f"{t.id}_{w.id}_{h}")
                interval = model.new_optional_fixed_size_interval_var(
                    h, t.duration_hours, chosen, f"slot_{t.id}_{w.id}_{h}"
                )
                worker_intervals[w.id].append(interval)
                if t.work_mode != "remote":
                    site_intervals.append(interval)
                    site_demands.append(1)
                model.add(starts[t.id] == h).only_enforce_if(chosen)
                cost = w.hourly_rate_cents * t.duration_hours
                cost_terms.append(cost * chosen)
                task_choices.append(chosen)
                worker_choices[w.id].append(chosen)
                choices.append((chosen, t, w, begins, ends_at, cost))
        if len(worker_choices) < t.crew_size:
            blockers.append(
                f"{t.name}: needs {t.crew_size} qualified available worker(s); only {len(worker_choices)} eligible within availability, certification expiry, location, commitments, and deadline."
            )
        if task_choices:
            model.add(sum(task_choices) == t.crew_size)
            for wc in worker_choices.values():
                model.add(sum(wc) <= 1)
    if blockers:
        return result("INFEASIBLE", blockers)
    for intervals in worker_intervals.values():
        model.add_no_overlap(intervals)
    if site_intervals:
        model.add_cumulative(site_intervals, site_demands, site.capacity)
    for d in deps:
        model.add(ends[d.predecessor_id] <= starts[d.task_id])
    if project.budget_cents is not None:
        model.add(sum(cost_terms) + fixed_cost <= project.budget_cents)
    model.minimize(sum(cost_terms) * (horizon * max(len(tasks), 1) + 1) + sum(starts.values()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limit_seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 26
    status = solver.solve(model)
    label = solver.status_name(status)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        proposals = [
            dict(
                task_id=t.id,
                task_name=t.name,
                worker_id=w.id,
                worker_name=w.name,
                starts_at=b.isoformat(),
                ends_at=e.isoformat(),
                cost_cents=c,
                state="proposed",
            )
            for x, t, w, b, e, c in choices
            if solver.boolean_value(x)
        ]
        return result(
            label, proposals=proposals, cost=fixed_cost + sum(p["cost_cents"] for p in proposals)
        )
    if status == cp_model.INFEASIBLE:
        return result(
            label,
            [
                "No joint schedule satisfies worker non-overlap, fixed commitments, task dependencies, site capacity, project deadline, and labour budget. Eligible individual slots exist; revise these constraints or add qualified availability."
            ],
        )
    return result(
        label,
        [
            "Solver did not establish feasibility within the time limit."
            if status == cp_model.UNKNOWN
            else "Invalid solver model; inspect task durations and resource constraints."
        ],
    )

"""CP-SAT recovery model. 30-minute slots, fixed commitments, no LLM feasibility."""

import hashlib, json, math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from ortools.sat.python import cp_model
from sqlalchemy import select
from .models import *
from .solver_time import utc, overlap

OBJECTIVES = {"lowest_cost", "earliest_completion", "fewest_changes"}


def scheduling_fingerprint(db, project):
    org = project.organization_id
    projects = list(db.scalars(select(Project).where(Project.organization_id == org)))
    pids = [p.id for p in projects]
    workers = list(db.scalars(select(Worker).where(Worker.organization_id == org)))
    wids = [w.id for w in workers]
    tasks = list(db.scalars(select(Task).where(Task.project_id.in_(pids))))
    tids = [t.id for t in tasks]
    records = (
        projects
        + workers
        + tasks
        + list(db.scalars(select(Worksite).where(Worksite.organization_id == org)))
    )
    for cls in [Skill, Certification, AvailabilityWindow, PrivateCommitment, WorkerAbsence]:
        records += list(db.scalars(select(cls).where(cls.worker_id.in_(wids))))
    records += list(
        db.scalars(
            select(Assignment).where(
                Assignment.worker_id.in_(wids), Assignment.status == "confirmed"
            )
        )
    )
    records += list(db.scalars(select(TaskDependency).where(TaskDependency.task_id.in_(tids))))
    for cls in [SchedulingPolicy, WeatherForecast]:
        records += list(db.scalars(select(cls).where(cls.project_id.in_(pids))))
    normalized = []
    for r in records:
        row = {"table": r.__tablename__}
        row.update(
            {
                c.name: utc(getattr(r, c.name)).isoformat()
                if isinstance(getattr(r, c.name), datetime)
                else getattr(r, c.name)
                for c in r.__table__.columns
                if c.name not in {"private_label", "fetched_at"}
            }
        )
        normalized.append(json.dumps(row, sort_keys=True, default=str))
    return hashlib.sha256(json.dumps(sorted(normalized)).encode()).hexdigest()


def solve(
    db,
    project,
    actor,
    limit_seconds=5,
    *,
    objective="lowest_cost",
    movable_task_ids=None,
    forced=None,
    reservation_exclude=None,
    candidate_workers=None,
    persist=True,
):
    from .weather import weather_blockers

    movable = set(movable_task_ids or [])
    workers = list(
        db.scalars(select(Worker).where(Worker.organization_id == project.organization_id))
    )
    wids = [w.id for w in workers]
    projects = list(
        db.scalars(select(Project).where(Project.organization_id == project.organization_id))
    )
    pmap = {p.id: p for p in projects}
    all_tasks = list(db.scalars(select(Task).where(Task.project_id.in_(pmap))))
    tmap = {t.id: t for t in all_tasks}
    tasks = [t for t in all_tasks if t.project_id == project.id]
    original = list(
        db.scalars(
            select(Assignment).where(
                Assignment.worker_id.in_(wids), Assignment.status == "confirmed"
            )
        )
    )
    fixed = [
        a
        for a in original
        if not (a.task_id in movable and tmap[a.task_id].project_id == project.id)
    ]
    busy = list(
        db.scalars(select(PrivateCommitment).where(PrivateCommitment.worker_id.in_(wids)))
    ) + list(db.scalars(select(WorkerAbsence).where(WorkerAbsence.worker_id.in_(wids))))
    reserved = list(db.scalars(select(SlotReservation).where(SlotReservation.worker_id.in_(wids))))
    reserved = [
        r
        for r in reserved
        if r.proposal_id != reservation_exclude
        and (p := db.get(RecoveryProposal, r.proposal_id))
        and p.status not in {"published", "rejected", "revision_requested", "expired"}
        and utc(p.expires_at) > datetime.now(timezone.utc)
    ]
    availability = list(
        db.scalars(select(AvailabilityWindow).where(AvailabilityWindow.worker_id.in_(wids)))
    )
    skills = list(db.scalars(select(Skill).where(Skill.worker_id.in_(wids))))
    certs = list(db.scalars(select(Certification).where(Certification.worker_id.in_(wids))))
    deps = list(
        db.scalars(select(TaskDependency).where(TaskDependency.task_id.in_([t.id for t in tasks])))
    )
    policy = db.get(SchedulingPolicy, project.id)
    zone = ZoneInfo(policy.timezone if policy else "America/Edmonton")
    transition = policy.transition_minutes if policy else 0
    rest = policy.minimum_rest_hours if policy else 0
    daily = policy.max_daily_hours if policy else 24
    buffer_percent = policy.task_buffer_percent if policy else 0
    contingency = policy.contingency_minutes if policy else 0
    start = utc(project.starts_at)
    deadline = utc(project.deadline) - timedelta(minutes=contingency)
    horizon = int((deadline - start).total_seconds() // 1800)

    def result(status, blockers=None, proposals=None, cost=None):
        draft = ScheduleDraft(
            project_id=project.id,
            created_by=actor.id,
            input_fingerprint=scheduling_fingerprint(db, project),
            status="draft",
            solver_status=status,
            blockers=blockers or [],
            proposals=proposals or [],
            cost_cents=cost,
        )
        if persist:
            db.add(draft)
            db.flush()
        return draft

    if objective not in OBJECTIVES:
        return result("INVALID_INPUT", ["Unknown scheduling objective"])
    if (
        horizon <= 0
        or utc(project.deadline) - start > timedelta(days=14)
        or any(
            v.minute not in (0, 30) or v.second or v.microsecond
            for v in (start, utc(project.deadline))
        )
    ):
        return result(
            "INVALID_INPUT",
            [
                "Use half-hour project boundaries and a horizon of at most 14 days; contingency must fit the horizon."
            ],
        )
    graph = {t.id: [] for t in tasks}
    for d in deps:
        if d.predecessor_id not in graph:
            return result("INVALID_INPUT", ["Dependencies must remain within this project."])
        graph[d.task_id].append(d.predecessor_id)

    def cyclic(tid, path):
        return tid in path or any(cyclic(p, path | {tid}) for p in graph[tid])

    if any(cyclic(t.id, set()) for t in tasks):
        return result("INVALID_INPUT", ["Task dependency graph contains a cycle."])
    if forced is not None and set(p["task_id"] for p in forced) != {
        t.id for t in tasks if len([a for a in fixed if a.task_id == t.id]) < t.crew_size
    }:
        return result("INVALID_INPUT", ["Proposal coverage changed; regenerate the plan."])

    def same_day(a, b):
        return utc(a).astimezone(zone).date() == utc(b).astimezone(zone).date()

    def conflict(a, b):
        if overlap(a.starts_at, a.ends_at, b.starts_at, b.ends_at):
            return True
        left, right = (a, b) if utc(a.starts_at) <= utc(b.starts_at) else (b, a)
        gap = (utc(right.starts_at) - utc(left.ends_at)).total_seconds() / 60
        return gap < (transition if same_day(left.starts_at, right.starts_at) else rest * 60)

    # Fixed actual assignments may not conflict with each other or new known absences.
    for i, a in enumerate(fixed):
        if any(
            b.worker_id == a.worker_id and overlap(a.starts_at, a.ends_at, b.starts_at, b.ends_at)
            for b in busy
        ):
            return result(
                "INFEASIBLE",
                [
                    f"{tmap[a.task_id].name}: preserved confirmed work overlaps recorded unavailability; include its affected project in recovery."
                ],
            )
        if any(b.worker_id == a.worker_id and conflict(a, b) for b in fixed[i + 1 :]):
            return result(
                "INFEASIBLE",
                [
                    "Preserved confirmed assignments conflict with worker overlap, transition, or rest constraints."
                ],
            )
    fixed_daily = defaultdict(float)
    for assignment in fixed + reserved:
        if overlap(assignment.starts_at, assignment.ends_at, start, deadline):
            fixed_daily[
                (assignment.worker_id, utc(assignment.starts_at).astimezone(zone).date())
            ] += (utc(assignment.ends_at) - utc(assignment.starts_at)).total_seconds() / 3600
    if any(hours > daily for hours in fixed_daily.values()):
        return result(
            "INFEASIBLE",
            [
                "Preserved work exceeds the configured maximum daily hours. Resolve the affected confirmed commitments."
            ],
        )
    model = cp_model.CpModel()
    intervals = defaultdict(list)
    site_intervals = []
    demands = []
    starts = {}
    ends = {}
    cost_terms = []
    change_terms = []
    choices = []
    daily_terms = defaultdict(list)
    fixed_cost = 0
    blockers = []
    site = db.get(Worksite, project.worksite_id)

    def tick(v):
        return int((utc(v) - start).total_seconds() // 1800)

    for a in fixed + reserved:
        lo = tick(a.starts_at)
        hi = math.ceil((utc(a.ends_at) - start).total_seconds() / 1800)
        if hi <= 0 or lo >= horizon:
            continue
        task = tmap[a.task_id]
        if pmap[task.project_id].worksite_id == site.id and task.work_mode != "remote":
            site_intervals.append(
                model.new_fixed_size_interval_var(lo, hi - lo, "fixedsite_" + a.id)
            )
            demands.append(1)
    candidates_by_worker = defaultdict(list)
    for task in tasks:
        committed = [a for a in fixed if a.task_id == task.id]
        needed = task.crew_size - len(committed)
        if needed < 0:
            return result("INVALID_INPUT", [f"{task.name}: too many confirmed crew assignments"])
        duration = math.ceil(task.duration_hours * 60 * (1 + buffer_percent / 100) / 30)
        if committed:
            spans = {(utc(a.starts_at), utc(a.ends_at)) for a in committed}
            if len(spans) != 1:
                return result(
                    "INVALID_INPUT", [f"{task.name}: fixed crew must share a start and end"]
                )
            span_start, span_end = next(iter(spans))
            duration = round((span_end - span_start).total_seconds() / 1800)
            if span_start < start or span_end > deadline:
                return result(
                    "INFEASIBLE",
                    [
                        f"{task.name}: fixed assignment falls outside the deadline or reserved contingency"
                    ],
                )
            starts[task.id] = model.new_int_var(tick(span_start), tick(span_start), "s_" + task.id)
            ends[task.id] = model.new_int_var(tick(span_end), tick(span_end), "e_" + task.id)
            for a in committed:
                w = next(w for w in workers if w.id == a.worker_id)
                if (
                    not set(task.required_skills) <= {s.name for s in skills if s.worker_id == w.id}
                    or not all(
                        any(
                            c.worker_id == w.id
                            and c.name == required
                            and utc(c.expires_at) >= utc(a.ends_at)
                            for c in certs
                        )
                        for required in task.required_certifications
                    )
                    or not any(
                        v.worker_id == w.id
                        and utc(v.starts_at) <= utc(a.starts_at)
                        and utc(v.ends_at) >= utc(a.ends_at)
                        for v in availability
                    )
                ):
                    return result(
                        "INFEASIBLE",
                        [
                            f"{task.name}: preserved confirmed assignment violates qualifications or availability"
                        ],
                    )
                if weather_blockers(db, project, task, a.starts_at, a.ends_at):
                    return result(
                        "INFEASIBLE",
                        [
                            f"{task.name}: fixed weather-sensitive work is at risk; explicitly include it in a recovery proposal"
                        ],
                    )
                fixed_cost += round(w.hourly_rate_cents * duration / 2)
        else:
            starts[task.id] = model.new_int_var(0, horizon, "s_" + task.id)
            ends[task.id] = model.new_int_var(0, horizon, "e_" + task.id)
            model.add(ends[task.id] == starts[task.id] + duration)
        if not needed:
            continue
        task_choices = []
        worker_choices = defaultdict(list)
        for w in workers:
            if (
                candidate_workers
                and task.id in candidate_workers
                and w.id not in candidate_workers[task.id]
            ):
                continue
            if (
                w.id in {a.worker_id for a in committed}
                or not set(task.required_skills) <= {s.name for s in skills if s.worker_id == w.id}
                or task.work_mode not in w.work_modes
                or (task.work_mode != "remote" and w.location != site.location)
            ):
                continue
            for h in range(max(0, horizon - duration + 1)):
                begins = start + timedelta(minutes=h * 30)
                finishes = begins + timedelta(minutes=duration * 30)
                if committed and (
                    begins != utc(committed[0].starts_at) or finishes != utc(committed[0].ends_at)
                ):
                    continue
                local = begins.astimezone(zone)
                endlocal = finishes.astimezone(zone)
                if local.date() != endlocal.date() or (
                    policy
                    and (
                        local.hour < policy.day_start_hour
                        or endlocal.hour + endlocal.minute / 60 > policy.day_end_hour
                    )
                ):
                    continue
                if not any(
                    a.worker_id == w.id
                    and utc(a.starts_at) <= begins
                    and utc(a.ends_at) >= finishes
                    for a in availability
                ):
                    continue
                if not all(
                    any(
                        c.worker_id == w.id and c.name == r and utc(c.expires_at) >= finishes
                        for c in certs
                    )
                    for r in task.required_certifications
                ):
                    continue
                if weather_blockers(db, project, task, begins, finishes):
                    continue
                candidate = Assignment(
                    worker_id=w.id, task_id=task.id, starts_at=begins, ends_at=finishes
                )
                if any(
                    a.worker_id == w.id
                    and (
                        conflict(candidate, a)
                        if isinstance(a, (Assignment, SlotReservation))
                        else overlap(begins, finishes, a.starts_at, a.ends_at)
                    )
                    for a in fixed + busy + reserved
                ):
                    continue
                if forced is not None and not any(
                    p["task_id"] == task.id
                    and p["worker_id"] == w.id
                    and utc(datetime.fromisoformat(p["starts_at"])) == begins
                    and utc(datetime.fromisoformat(p["ends_at"])) == finishes
                    for p in forced
                ):
                    continue
                x = model.new_bool_var(f"{task.id}_{w.id}_{h}")
                iv = model.new_optional_fixed_size_interval_var(
                    h, duration, x, f"i_{task.id}_{w.id}_{h}"
                )
                intervals[w.id].append(iv)
                if task.work_mode != "remote":
                    site_intervals.append(iv)
                    demands.append(1)
                model.add(starts[task.id] == h).only_enforce_if(x)
                cost = round(w.hourly_rate_cents * duration / 2)
                cost_terms.append(cost * x)
                old = [a for a in original if a.task_id == task.id]
                change = (
                    0
                    if any(
                        a.worker_id == w.id
                        and utc(a.starts_at) == begins
                        and utc(a.ends_at) == finishes
                        for a in old
                    )
                    else 1
                )
                change_terms.append(change * x)
                task_choices.append(x)
                worker_choices[w.id].append(x)
                daily_terms[(w.id, local.date())].append(duration * x)
                candidates_by_worker[w.id].append((candidate, x))
                choices.append((x, task, w, begins, finishes, cost))
        if len(worker_choices) < needed:
            blockers.append(
                f"{task.name}: needs {needed} additional qualified available worker(s); only {len(worker_choices)} eligible after weather, buffers, rest, commitments, and deadline checks."
            )
        if task_choices:
            model.add(sum(task_choices) == needed)
            for xs in worker_choices.values():
                model.add(sum(xs) <= 1)
    if blockers:
        return result("INFEASIBLE", blockers)
    for ivs in intervals.values():
        model.add_no_overlap(ivs)
    for wid, options in candidates_by_worker.items():
        for i, (a, x) in enumerate(options):
            for b, y in options[i + 1 :]:
                if a.task_id != b.task_id and conflict(a, b):
                    model.add_bool_or([x.Not(), y.Not()])
    for (wid, date), terms in daily_terms.items():
        worked = sum(
            round((utc(a.ends_at) - utc(a.starts_at)).total_seconds() / 1800)
            for a in fixed + reserved
            if a.worker_id == wid and utc(a.starts_at).astimezone(zone).date() == date
        )
        model.add(sum(terms) + worked <= daily * 2)
    if site_intervals:
        model.add_cumulative(site_intervals, demands, site.capacity)
    for d in deps:
        model.add(ends[d.predecessor_id] <= starts[d.task_id])
    total_cost = sum(cost_terms) + fixed_cost
    if project.budget_cents is not None:
        model.add(total_cost <= project.budget_cents)
    completion = model.new_int_var(0, horizon, "completion")
    if ends:
        model.add_max_equality(completion, list(ends.values()))
    # Lexicographic weights use upper bounds, not fabricated performance metrics.
    maxcost = (
        sum(max(1, w.hourly_rate_cents) for w in workers) * max(1, horizon) * max(1, len(tasks))
    )
    if objective == "earliest_completion":
        model.minimize(completion * (maxcost + 1) + total_cost)
    elif objective == "fewest_changes":
        model.minimize(
            sum(change_terms) * (maxcost + 1) * (horizon + 1)
            + completion * (maxcost + 1)
            + total_cost
        )
    else:
        model.minimize(total_cost * (horizon * max(1, len(tasks)) + 1) + sum(starts.values()))
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
    return result(
        label,
        [
            "No joint plan satisfies fixed commitments, task dependencies, site capacity, rest, daily hours, buffers, budget and deadline."
        ]
        if status == cp_model.INFEASIBLE
        else [
            "Solver timed out without proving feasibility."
            if status == cp_model.UNKNOWN
            else "Invalid scheduling inputs."
        ],
    )

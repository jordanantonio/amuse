"""Slot-first crew planner (CREW-1..3): availability, bookings, fatigue advice, candidates."""

from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from .catalog import distance_km
from .market_models import (
    AvailabilityBlock,
    ContractApplication,
    CredentialType,
    CrewAssignment,
    CrewMember,
    CrewRules,
    CrewSlot,
    Engagement,
    Posting,
    User,
    WorkerHours,
    WorkerProfile,
)
from .models import Organization
from .ranking import fit_score
from .wallet import held

Interval = tuple[datetime, datetime, str]  # start, end, label


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def slot_times(slot: CrewSlot) -> tuple[datetime, datetime]:
    base = datetime.combine(slot.day, datetime.min.time())
    return base + timedelta(minutes=slot.start_minute), base + timedelta(minutes=slot.end_minute)


def rules_for(db: Session, org_id: str) -> CrewRules:
    rules = db.get(CrewRules, org_id)
    if not rules:
        rules = CrewRules(org_id=org_id, max_consecutive_days=5, min_rest_hours=10, max_weekly_hours=40)
        db.add(rules)
        db.flush()
    return rules


def hours_by_weekday(db: Session, user_id: str) -> dict[int, list[tuple[int, int]]]:
    result: dict[int, list[tuple[int, int]]] = {}
    for h in db.scalars(select(WorkerHours).where(WorkerHours.user_id == user_id)):
        result.setdefault(h.weekday, []).append((h.start_minute, h.end_minute))
    return result


def free_windows(hours: dict[int, list[tuple[int, int]]], day: date) -> list[tuple[int, int]]:
    """Availability windows touching `day`, as minutes relative to that day's midnight."""
    wd = day.weekday()
    windows = list(hours.get(wd, []))
    # Windows from the day before that run past midnight.
    for s, e in hours.get((wd - 1) % 7, []):
        if e > 1440:
            windows.append((s - 1440, e - 1440))
    return windows


def covers(hours, slot: CrewSlot) -> bool:
    return any(s <= slot.start_minute and e >= slot.end_minute for s, e in free_windows(hours, slot.day))


def engagement_shift(day: date, pattern: str) -> tuple[datetime, datetime]:
    """Approximate hours for a marketplace contract day: days 8-4:30, nights 10 PM-6:30 AM."""
    base = datetime.combine(day, datetime.min.time())
    if pattern == "nights":
        return base + timedelta(hours=22), base + timedelta(hours=30, minutes=30)
    return base + timedelta(hours=8), base + timedelta(hours=16, minutes=30)


def bookings(
    db: Session,
    user_id: str,
    start: date,
    end: date,
    *,
    include_proposed: bool = False,
    exclude_slot: str | None = None,
) -> list[Interval]:
    """Every shift a worker already has between two dates, across all employers."""
    statuses = ["assigned", "proposed"] if include_proposed else ["assigned"]
    result: list[Interval] = []
    rows = db.execute(
        select(CrewSlot, Organization.name)
        .join(CrewAssignment, CrewAssignment.slot_id == CrewSlot.id)
        .join(Organization, CrewSlot.org_id == Organization.id)
        .where(
            CrewAssignment.user_id == user_id,
            CrewAssignment.status.in_(statuses),
            CrewSlot.day >= start - timedelta(days=1),
            CrewSlot.day <= end,
        )
    )
    for slot, org_name in rows:
        if slot.id == exclude_slot:
            continue
        s, e = slot_times(slot)
        result.append((s, e, f"{slot.label}, {org_name}"))
    blocks = db.execute(
        select(AvailabilityBlock, Engagement.schedule_pattern, Posting.title)
        .join(Engagement, AvailabilityBlock.engagement_id == Engagement.id)
        .join(ContractApplication, Engagement.application_id == ContractApplication.id)
        .join(Posting, ContractApplication.posting_id == Posting.id)
        .where(
            AvailabilityBlock.user_id == user_id,
            AvailabilityBlock.source == "engagement",
            Engagement.status == "active",
            AvailabilityBlock.start_date <= end,
            AvailabilityBlock.end_date >= start - timedelta(days=1),
        )
    )
    for block, pattern, title in blocks:
        d = max(block.start_date, start - timedelta(days=1))
        while d <= min(block.end_date, end):
            s, e = engagement_shift(d, pattern)
            result.append((s, e, title))
            d += timedelta(days=1)
    return sorted(result)


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def fatigue(rules: CrewRules, shifts: list[Interval], new: tuple[datetime, datetime]) -> list[str]:
    """CREW-3 advice for adding `new` to a worker's existing shifts. Never blocks."""
    start, end = new
    warnings = []
    days = {s.date() for s, _, _ in shifts}
    run = 1
    d = start.date() - timedelta(days=1)
    while d in days:
        run += 1
        d -= timedelta(days=1)
    if run >= 3:
        warnings.append(f"Would be {ordinal(run)} day in a row")
    elif start.date() - timedelta(days=1) in days:
        warnings.append("Worked yesterday")
    if run > rules.max_consecutive_days:
        warnings.append(f"Over the {rules.max_consecutive_days}-days-in-a-row limit")
    before = [(start - e).total_seconds() / 3600 for _, e, _ in shifts if e <= start]
    after = [(s - end).total_seconds() / 3600 for s, _, _ in shifts if s >= end]
    if before and min(before) < rules.min_rest_hours:
        warnings.append(f"Only {round(min(before))} h rest since last shift")
    elif after and min(after) < rules.min_rest_hours:
        warnings.append(f"Only {round(min(after))} h rest before next shift")
    ws = datetime.combine(week_start(start.date()), datetime.min.time())
    we = ws + timedelta(days=7)
    week_hours = sum(
        (min(e, we) - max(s, ws)).total_seconds() / 3600 for s, e, _ in shifts if e > ws and s < we
    ) + (end - start).total_seconds() / 3600
    if week_hours > rules.max_weekly_hours:
        warnings.append(f"Would pass {rules.max_weekly_hours} h this week")
    return warnings


def overlapping(shifts: list[Interval], new: tuple[datetime, datetime]) -> Interval | None:
    return next((x for x in shifts if x[0] < new[1] and x[1] > new[0]), None)


def clip_bar(intervals, day: date) -> list[list[int]]:
    base = datetime.combine(day, datetime.min.time())
    bars = []
    for s, e, *_ in intervals:
        a = max(0, int((s - base).total_seconds() // 60))
        b = min(1440, int((e - base).total_seconds() // 60))
        if b > a:
            bars.append([a, b])
    return bars


def candidate_rows(db: Session, org: Organization, slot: CrewSlot, scope: str) -> list[dict]:
    rules = rules_for(db, org.id)
    crew_ids = set(db.scalars(select(CrewMember.user_id).where(CrewMember.org_id == org.id)))
    assigned = set(
        db.scalars(select(CrewAssignment.user_id).where(CrewAssignment.slot_id == slot.id))
    )
    if scope == "crew":
        pool = crew_ids
    else:
        pool = set(
            db.scalars(select(WorkerProfile.user_id).where(WorkerProfile.is_public.is_(True)))
        )
    types = {t.id: t.name for t in db.scalars(select(CredentialType))}
    start, end = slot_times(slot)
    rows = []
    for uid in pool - assigned:
        user = db.get(User, uid)
        profile = db.get(WorkerProfile, uid)
        if not user or not profile:
            continue
        wallet = held(db, uid, slot.day)
        missing = [types.get(c, c) for c in slot.required_certs if c not in wallet]
        hours = hours_by_weekday(db, uid)
        available = covers(hours, slot)
        shifts = bookings(db, uid, slot.day - timedelta(days=7), slot.day + timedelta(days=7))
        clash = overlapping(shifts, (start, end))
        warnings = fatigue(rules, shifts, (start, end))
        bonus = (
            [(types.get(slot.preferred_cert, slot.preferred_cert), "valuable", slot.preferred_cert in wallet)]
            if slot.preferred_cert
            else []
        )
        dist = distance_km(org.lat, org.lng, profile.lat, profile.lng)
        fit = fit_score(
            required_total=len(slot.required_certs),
            required_held=len(slot.required_certs) - len(missing),
            required_verified=sum(1 for c in slot.required_certs if wallet.get(c) == "verified"),
            bonus=bonus,
            distance_km=dist,
            radius_km=profile.travel_radius_km,
            available=available and not clash,
            warnings=warnings,
        )
        blockers = []
        if missing:
            blockers.append("Missing " + ", ".join(missing))
        if not available:
            blockers.append("Not available at this time")
        if clash:
            blockers.append(f"Booked: {clash[2]}")
        certs = [
            {"id": c, "name": types.get(c, c), "state": wallet.get(c, "missing"), "kind": "required"}
            for c in slot.required_certs
        ]
        if slot.preferred_cert:
            certs.append(
                {
                    "id": slot.preferred_cert,
                    "name": types.get(slot.preferred_cert, slot.preferred_cert),
                    "state": wallet.get(slot.preferred_cert, "missing"),
                    "kind": "preferred",
                }
            )
        rows.append(
            {
                "user_id": uid,
                "name": user.full_name,
                "headline": profile.headline,
                "on_crew": uid in crew_ids,
                "certs": certs,
                "score": fit.score,
                "breakdown": fit.rows,
                "warnings": warnings,
                "blockers": blockers,
                "bar": {
                    "free": [[max(0, s), min(1440, e)] for s, e in free_windows(hours, slot.day) if e > 0 and s < 1440],
                    "booked": clip_bar(shifts, slot.day),
                    "slot": [slot.start_minute, min(1440, slot.end_minute)],
                },
            }
        )
    rows.sort(key=lambda r: (bool(r["blockers"]), -r["score"], r["name"]))
    return rows

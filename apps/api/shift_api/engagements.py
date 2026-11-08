"""Accepting offers, the schedule lock and completions (FLOW-3, FLOW-4).

Shift's availability_blocks table is the source of truth for who is booked when;
Google Calendar is only a mirror of it.
"""

from datetime import date, datetime, timezone
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .market_models import (
    AvailabilityBlock,
    ContractApplication,
    Engagement,
    Posting,
    User,
    WorkHistory,
)
from .models import Organization
from .schedule import Range, blocked_ranges, overlap


def book(db: Session, a: ContractApplication, p: Posting, status: str = "active") -> Engagement:
    """Create the engagement and block the dates."""
    e = Engagement(
        application_id=a.id,
        start_date=p.start_date,
        end_date=p.end_date,
        is_exclusive=p.is_exclusive,
        schedule_pattern=p.schedule_pattern,
        status=status,
    )
    db.add(e)
    db.flush()
    owner = {"user_id": a.applicant_user_id} if a.applicant_user_id else {"org_id": a.applicant_org_id}
    for start, end in blocked_ranges(p.start_date, p.end_date, p.schedule_pattern, p.is_exclusive):
        db.add(
            AvailabilityBlock(
                **owner,
                start_date=start,
                end_date=end,
                source="engagement",
                engagement_id=e.id,
                note=p.title,
            )
        )
    return e


def fmt(d: date) -> str:
    return d.strftime("%b ") + str(d.day)


def owner_filter(model, a: ContractApplication):
    if a.applicant_user_id:
        return model.user_id == a.applicant_user_id
    return model.org_id == a.applicant_org_id


def conflicts(db: Session, a: ContractApplication, p: Posting) -> list[dict]:
    """Existing bookings that overlap the days this contract would block."""
    mine = blocked_ranges(p.start_date, p.end_date, p.schedule_pattern, p.is_exclusive)
    rows = db.execute(
        select(AvailabilityBlock, Engagement, ContractApplication.posting_id)
        .join(Engagement, AvailabilityBlock.engagement_id == Engagement.id)
        .join(ContractApplication, Engagement.application_id == ContractApplication.id)
        .where(
            owner_filter(AvailabilityBlock, a),
            AvailabilityBlock.source == "engagement",
            Engagement.status == "active",
        )
    )
    found: dict[str, dict] = {}
    for block, e, posting_id in rows:
        hit = overlap(mine, [(block.start_date, block.end_date)])
        if hit and e.id not in found:
            other = db.get(Posting, posting_id)
            kind = "full-time" if e.is_exclusive else "part-time"
            found[e.id] = {
                "engagement_id": e.id,
                "title": other.title,
                "message": f"You’re already booked {fmt(hit[0])} – {fmt(hit[1])} on "
                f"“{other.title}” ({kind}). Shift won’t double-book you.",
            }
    return list(found.values())


def manual_overlaps(db: Session, a: ContractApplication, p: Posting) -> list[dict]:
    mine = blocked_ranges(p.start_date, p.end_date, p.schedule_pattern, p.is_exclusive)
    blocks = db.scalars(
        select(AvailabilityBlock).where(
            owner_filter(AvailabilityBlock, a), AvailabilityBlock.source == "manual"
        )
    )
    return [
        {"id": b.id, "start_date": b.start_date, "end_date": b.end_date, "note": b.note}
        for b in blocks
        if overlap(mine, [(b.start_date, b.end_date)])
    ]


def overlapping_open(db: Session, a: ContractApplication, p: Posting) -> list[ContractApplication]:
    """Other open applications whose dates overlap an exclusive contract (FLOW-3)."""
    if not p.is_exclusive:
        return []
    mine: list[Range] = [(p.start_date, p.end_date)]
    owner = (
        ContractApplication.applicant_user_id == a.applicant_user_id
        if a.applicant_user_id
        else ContractApplication.applicant_org_id == a.applicant_org_id
    )
    others = db.scalars(
        select(ContractApplication).where(
            owner,
            ContractApplication.id != a.id,
            ContractApplication.status.in_(["applied", "invited", "shortlisted", "offered"]),
        )
    )
    result = []
    for other in others:
        q = db.get(Posting, other.posting_id)
        theirs = blocked_ranges(q.start_date, q.end_date, q.schedule_pattern, q.is_exclusive)
        if overlap(mine, theirs):
            result.append(other)
    return result


def lock_applicant(db: Session, a: ContractApplication) -> None:
    """Serialize acceptances for one applicant so two offers can't both claim a day."""
    if db.get_bind().dialect.name != "postgresql":
        return
    if a.applicant_user_id:
        db.execute(select(User.id).where(User.id == a.applicant_user_id).with_for_update())
    else:
        db.execute(
            select(Organization.id).where(Organization.id == a.applicant_org_id).with_for_update()
        )


def hired_count(db: Session, posting_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ContractApplication)
            .where(
                ContractApplication.posting_id == posting_id,
                ContractApplication.status.in_(["accepted", "completed"]),
            )
        )
        or 0
    )


def sync_completions(db: Session, today: date | None = None) -> None:
    """End date passed -> COMPLETED, and the job joins the worker's history (FLOW, PROF-2)."""
    today = today or date.today()
    done = list(
        db.scalars(
            select(Engagement).where(Engagement.status == "active", Engagement.end_date < today)
        )
    )
    for e in done:
        e.status = "completed"
        a = db.get(ContractApplication, e.application_id)
        a.status = "completed"
        a.updated_at = datetime.now(timezone.utc)
        if a.applicant_user_id and not db.scalar(
            select(WorkHistory.id).where(WorkHistory.engagement_id == e.id)
        ):
            p = db.get(Posting, a.posting_id)
            org = db.get(Organization, p.org_id)
            db.add(
                WorkHistory(
                    user_id=a.applicant_user_id,
                    role=p.title,
                    company=org.name,
                    city=p.city,
                    start_date=e.start_date,
                    end_date=e.end_date,
                    description="Completed on Shift.",
                    engagement_id=e.id,
                )
            )
    if done:
        db.commit()


def ensure_acceptable(db: Session, a: ContractApplication, p: Posting) -> None:
    if a.status != "offered":
        raise HTTPException(409, "Only an open offer can be accepted")
    if p.status not in {"open", "filled"} or hired_count(db, p.id) >= p.headcount:
        raise HTTPException(409, "This contract has already been filled")
    found = conflicts(db, a, p)
    if found:
        raise HTTPException(409, found[0]["message"])

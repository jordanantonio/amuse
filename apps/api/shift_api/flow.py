"""Applications and offers (FLOW-1, FLOW-2), Work tab views and helpers.

Status flow: applied/invited -> shortlisted -> offered -> accepted -> completed, with
declined and withdrawn as exits. Acceptance itself lives in engagements.py (FLOW-3/4).
"""

from datetime import date, datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .catalog import distance_km
from .feed import (
    OPEN_APPLICATION,
    as_utc,
    booked_ranges,
    booking_conflict,
    card,
    evaluate,
    org_held,
    requirements_for,
)
from .market_common import audit, user_org
from .market_models import (
    ContractApplication,
    Engagement,
    OrgMember,
    Posting,
    User,
    WorkerProfile,
)
from .models import Organization
from .profile_routes import notify, org_user_ids
from .wallet import held, type_map

# action -> (who may do it, allowed from statuses, resulting status)
TRANSITIONS = {
    "shortlist": ("business", {"applied", "invited"}, "shortlisted"),
    "offer": ("business", {"applied", "shortlisted"}, "offered"),
    "decline": ("business", {"applied", "invited", "shortlisted"}, "declined"),
    "withdraw_offer": ("business", {"offered"}, "withdrawn"),
    "decline_offer": ("applicant", {"offered", "invited"}, "declined"),
    "withdraw": ("applicant", {"applied", "invited", "shortlisted", "offered"}, "withdrawn"),
}
NOTIFY = {
    "shortlist": "application.shortlisted",
    "offer": "offer.received",
    "decline": "application.declined",
    "withdraw_offer": "offer.withdrawn",
    "decline_offer": "offer.declined",
    "withdraw": "application.withdrawn",
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def applicant_name(db, a: ContractApplication) -> str:
    if a.applicant_user_id:
        return db.get(User, a.applicant_user_id).full_name
    return db.get(Organization, a.applicant_org_id).name


def applicant_user_ids(db, a: ContractApplication) -> list[str]:
    if a.applicant_user_id:
        return [a.applicant_user_id]
    return org_user_ids(db, a.applicant_org_id)


def is_applicant(db, user: User, a: ContractApplication) -> bool:
    if a.applicant_user_id:
        return a.applicant_user_id == user.id
    org = user_org(db, user)
    return bool(org and org.id == a.applicant_org_id)


def owns_posting(db, user: User, p: Posting) -> bool:
    return bool(
        db.scalar(
            select(OrgMember.user_id).where(OrgMember.org_id == p.org_id, OrgMember.user_id == user.id)
        )
    )


def applied_to_org(db, worker_id: str, org_id: str) -> bool:
    """True when a worker has an application on any of this organization's postings."""
    return bool(
        db.scalar(
            select(ContractApplication.id)
            .join(Posting, ContractApplication.posting_id == Posting.id)
            .where(ContractApplication.applicant_user_id == worker_id, Posting.org_id == org_id)
            .limit(1)
        )
    )


def badge_count(db, user: User) -> int:
    """Work tab badge: offers/invites waiting (workers, agencies) or new applicants (businesses)."""
    org = user_org(db, user)
    if user.default_mode == "business" and org:
        since = now() - timedelta(hours=48)
        return (
            db.scalar(
                select(func.count())
                .select_from(ContractApplication)
                .join(Posting, ContractApplication.posting_id == Posting.id)
                .where(
                    Posting.org_id == org.id,
                    ContractApplication.status == "applied",
                    ContractApplication.created_at >= since,
                )
            )
            or 0
        )
    owner = (
        ContractApplication.applicant_user_id == user.id
        if user.default_mode == "worker"
        else ContractApplication.applicant_org_id == (org.id if org else None)
    )
    return (
        db.scalar(
            select(func.count())
            .select_from(ContractApplication)
            .where(owner, ContractApplication.status.in_(["offered", "invited"]))
        )
        or 0
    )


def apply(db: Session, user: User, p: Posting, note: str, rate: int | None, crew: int | None):
    if p.status != "open":
        raise HTTPException(409, "This contract is no longer taking applications")
    types = type_map(db)
    reqs = requirements_for(db, [p.id])[p.id]
    if p.posting_type == "individual":
        if user.default_mode != "worker" or not db.get(WorkerProfile, user.id):
            raise HTTPException(403, "Only workers can apply to this contract")
        ev = evaluate(reqs, held(db, user.id), types)
        conflict = booking_conflict(booked_ranges(db, user.id), p)
        if conflict:
            ev.reasons.append(conflict)
        owner = {"applicant_user_id": user.id}
        existing = db.scalar(
            select(ContractApplication).where(
                ContractApplication.posting_id == p.id, ContractApplication.applicant_user_id == user.id
            )
        )
    else:
        org = user_org(db, user)
        if user.default_mode != "agency" or not org:
            raise HTTPException(403, "Only contracting companies can send a proposal for crew work")
        ev = evaluate(reqs, org_held(db, org.id), types)
        owner = {"applicant_org_id": org.id}
        existing = db.scalar(
            select(ContractApplication).where(
                ContractApplication.posting_id == p.id, ContractApplication.applicant_org_id == org.id
            )
        )
    if not ev.eligible:
        raise HTTPException(409, "You can’t apply yet. " + "; ".join(ev.reasons) + ".")
    if existing and existing.status not in {"withdrawn", "declined"}:
        raise HTTPException(409, "You’ve already applied to this contract")
    if existing and existing.status == "declined":
        raise HTTPException(409, "This business has already decided on your application")
    a = existing or ContractApplication(posting_id=p.id, **owner)
    a.status, a.note, a.initiated_by = "applied", note, "applicant"
    a.proposed_rate_cents, a.crew_size = rate, crew
    a.created_at = a.updated_at = now()
    db.add(a)
    db.flush()
    notify(
        db,
        org_user_ids(db, p.org_id),
        "application.received",
        posting=p.title,
        posting_id=p.id,
        applicant=applicant_name(db, a),
    )
    audit(db, user, "application.submitted", "contract_applications", a.id)
    db.commit()
    return a


def transition(db: Session, user: User, a: ContractApplication, action: str) -> ContractApplication:
    if action not in TRANSITIONS:
        raise HTTPException(422, "Unknown action")
    actor, allowed, result = TRANSITIONS[action]
    p = db.get(Posting, a.posting_id)
    permitted = owns_posting(db, user, p) if actor == "business" else is_applicant(db, user, a)
    if not permitted:
        raise HTTPException(404, "Application not found")
    if a.status not in allowed:
        raise HTTPException(409, f"This application is {a.status.replace('_', ' ')}; that step isn’t available")
    a.status = result
    a.updated_at = now()
    org = db.get(Organization, p.org_id)
    recipients = applicant_user_ids(db, a) if actor == "business" else org_user_ids(db, p.org_id)
    notify(
        db,
        recipients,
        NOTIFY[action],
        posting=p.title,
        posting_id=p.id,
        org=org.name,
        applicant=applicant_name(db, a),
    )
    audit(db, user, f"application.{action}", "contract_applications", a.id, status=result)
    db.commit()
    return a


# ---------- Views ----------


def application_view(db, a: ContractApplication, viewer: User, ev_cache=None) -> dict:
    p = db.get(Posting, a.posting_id)
    org = db.get(Organization, p.org_id)
    types = type_map(db)
    reqs = requirements_for(db, [p.id])[p.id]
    wallet = held(db, a.applicant_user_id) if a.applicant_user_id else org_held(db, a.applicant_org_id)
    ev = evaluate(reqs, wallet, types)
    revealed = a.status in {"offered", "accepted", "completed"} or owns_posting(db, viewer, p)
    engagement = db.scalar(select(Engagement).where(Engagement.application_id == a.id))
    return {
        "id": a.id,
        "status": a.status,
        "note": a.note,
        "proposed_rate_cents": a.proposed_rate_cents,
        "crew_size": a.crew_size,
        "initiated_by": a.initiated_by,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "applicant": applicant_summary(db, a, p),
        "posting": card(db, p, org, ev, site_address=p.site_address if revealed else None),
        "engagement": engagement_summary(engagement) if engagement else None,
    }


def engagement_summary(e: Engagement) -> dict:
    return {
        "id": e.id,
        "start_date": e.start_date,
        "end_date": e.end_date,
        "is_exclusive": e.is_exclusive,
        "schedule_pattern": e.schedule_pattern,
        "status": e.status,
        "calendar_synced": bool(e.google_event_ids),
    }


def applicant_summary(db, a: ContractApplication, p: Posting) -> dict:
    if a.applicant_user_id:
        u = db.get(User, a.applicant_user_id)
        prof = db.get(WorkerProfile, u.id)
        dist = distance_km(prof.lat, prof.lng, p.lat, p.lng) if prof else None
        return {
            "kind": "worker",
            "id": u.id,
            "name": u.full_name,
            "headline": prof.headline if prof else "",
            "city": prof.city if prof else "",
            "distance_km": round(dist) if dist is not None else None,
        }
    o = db.get(Organization, a.applicant_org_id)
    return {
        "kind": "agency",
        "id": o.id,
        "name": o.name,
        "headline": o.about or "",
        "city": o.city or "",
        "distance_km": None,
        "verified": o.verification_status == "verified",
    }


def worker_work(db, user: User) -> dict:
    org = user_org(db, user)
    owner = (
        ContractApplication.applicant_user_id == user.id
        if user.default_mode == "worker"
        else ContractApplication.applicant_org_id == (org.id if org else None)
    )
    apps = list(
        db.scalars(select(ContractApplication).where(owner).order_by(ContractApplication.updated_at.desc()))
    )
    views = [application_view(db, a, user) for a in apps]
    today = date.today()
    return {
        "applied": [v for v in views if v["status"] in {"applied", "shortlisted"}],
        "offers": [v for v in views if v["status"] in {"offered", "invited"}],
        "active": [
            v
            for v in views
            if v["status"] == "accepted" and v["engagement"] and v["engagement"]["status"] == "active"
            and v["engagement"]["end_date"] >= today
        ],
        "past": [
            v
            for v in views
            if v["status"] in {"declined", "withdrawn", "completed"}
            or (v["engagement"] and v["engagement"]["status"] != "active")
        ],
    }


def org_postings(db, org: Organization) -> list[dict]:
    postings = list(
        db.scalars(select(Posting).where(Posting.org_id == org.id).order_by(Posting.start_date))
    )
    counts: dict[str, dict[str, int]] = {}
    for pid, status, n in db.execute(
        select(ContractApplication.posting_id, ContractApplication.status, func.count())
        .join(Posting, ContractApplication.posting_id == Posting.id)
        .where(Posting.org_id == org.id)
        .group_by(ContractApplication.posting_id, ContractApplication.status)
    ):
        counts.setdefault(pid, {})[status] = n
    reqs = requirements_for(db, [p.id for p in postings])
    types = type_map(db)
    result = []
    for p in postings:
        c = counts.get(p.id, {})
        ev = evaluate(reqs[p.id], {}, types)
        result.append(
            card(
                db,
                p,
                org,
                ev,
                site_address=p.site_address,
                description=p.description,
                applicants=sum(n for s, n in c.items() if s in OPEN_APPLICATION),
                new_applicants=c.get("applied", 0),
                offers_out=c.get("offered", 0),
                hired=c.get("accepted", 0) + c.get("completed", 0),
            )
        )
    return result


def applicants_for(db, user: User, p: Posting) -> list[dict]:
    if not owns_posting(db, user, p):
        raise HTTPException(404, "Posting not found")
    apps = db.scalars(
        select(ContractApplication)
        .where(ContractApplication.posting_id == p.id)
        .order_by(ContractApplication.created_at.desc())
    )
    return [application_view(db, a, user) for a in apps]


def org_engagements(db, org: Organization) -> dict:
    rows = list(
        db.execute(
            select(Engagement, ContractApplication)
            .join(ContractApplication, Engagement.application_id == ContractApplication.id)
            .join(Posting, ContractApplication.posting_id == Posting.id)
            .where(Posting.org_id == org.id)
            .order_by(Engagement.start_date)
        )
    )
    today = date.today()
    active, past = [], []
    for e, a in rows:
        p = db.get(Posting, a.posting_id)
        item = {
            "engagement": engagement_summary(e),
            "application_id": a.id,
            "posting_id": p.id,
            "posting_title": p.title,
            "applicant": applicant_summary(db, a, p),
        }
        (active if e.status == "active" and e.end_date >= today else past).append(item)
    return {"active": active, "past": past}


def new_applicants(db, org: Organization, hours: int = 48) -> list[dict]:
    since = now() - timedelta(hours=hours)
    rows = db.scalars(
        select(ContractApplication)
        .join(Posting, ContractApplication.posting_id == Posting.id)
        .where(Posting.org_id == org.id, ContractApplication.status == "applied")
        .order_by(ContractApplication.created_at.desc())
    )
    return [
        {
            "application_id": a.id,
            "posting_id": a.posting_id,
            "posting_title": db.get(Posting, a.posting_id).title,
            "name": applicant_name(db, a),
            "created_at": a.created_at,
        }
        for a in rows
        if as_utc(a.created_at) >= since
    ]

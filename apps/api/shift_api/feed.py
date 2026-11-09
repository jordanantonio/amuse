"""For You feed: gate first, then score (FEED-1, FEED-2), plus posting eligibility (POST-2).

Every number shown to a worker comes from here so "Why am I seeing this?" can list the
exact points that ranked a contract.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from .catalog import distance_km
from .feed_config import NEW_POSTING_HOURS, NEW_SINCE_HOURS, STARTS_SOON_DAYS, WEIGHTS
from .market_models import (
    AvailabilityBlock,
    ContractApplication,
    Credential,
    CredentialType,
    Engagement,
    Posting,
    PostingRequirement,
    User,
    WorkerProfile,
)
from .models import Organization
from .schedule import Range, blocked_ranges, overlap
from .wallet import effective_status, held, type_map

OPEN_APPLICATION = {"applied", "invited", "shortlisted", "offered"}


@dataclass
class Evaluation:
    items: list[dict] = field(default_factory=list)  # one per required/nice credential
    required_total: int = 0
    required_held: int = 0
    nice_total: int = 0
    nice_held: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return not self.reasons


def requirements_for(db: Session, posting_ids) -> dict[str, list[PostingRequirement]]:
    result: dict[str, list[PostingRequirement]] = {pid: [] for pid in posting_ids}
    if not result:
        return result
    for r in db.scalars(
        select(PostingRequirement).where(PostingRequirement.posting_id.in_(list(result)))
    ):
        result[r.posting_id].append(r)
    return result


def org_held(db: Session, org_id: str, on: date | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for c in db.scalars(select(Credential).where(Credential.owner_org_id == org_id)):
        status = effective_status(c, on)
        if c.credential_type_id and status not in {"expired", "rejected"}:
            level = "verified" if status == "verified" else "unverified"
            if result.get(c.credential_type_id) != "verified":
                result[c.credential_type_id] = level
    return result


def evaluate(
    reqs: list[PostingRequirement], wallet: dict[str, str], types: dict[str, CredentialType]
) -> Evaluation:
    ev = Evaluation()
    for r in sorted(reqs, key=lambda r: (not r.required, types[r.credential_type_id].name)):
        name = types[r.credential_type_id].name
        level = wallet.get(r.credential_type_id)
        if level == "verified":
            state = "ok"
        elif level == "unverified":
            state = "pending"
        else:
            state = "missing"
        ev.items.append(
            {
                "credential_type_id": r.credential_type_id,
                "name": name,
                "required": r.required,
                "must_be_verified": r.must_be_verified,
                "state": state,
                "weight": r.weight,
            }
        )
        if r.required:
            ev.required_total += 1
            if state != "missing":
                ev.required_held += 1
            if state == "missing":
                ev.reasons.append(f"Missing: {name}")
            elif state == "pending" and r.must_be_verified:
                ev.reasons.append(f"Needs verification: {name}")
        else:
            ev.nice_total += 1
            ev.nice_held += state != "missing"
    return ev


def booked_ranges(db: Session, user_id: str) -> list[tuple[Range, str]]:
    """Dates a worker is booked by active engagements, with the contract title."""
    rows = db.execute(
        select(AvailabilityBlock, Posting.title)
        .join(Engagement, AvailabilityBlock.engagement_id == Engagement.id)
        .join(ContractApplication, Engagement.application_id == ContractApplication.id)
        .join(Posting, ContractApplication.posting_id == Posting.id)
        .where(
            AvailabilityBlock.user_id == user_id,
            AvailabilityBlock.source == "engagement",
            Engagement.status == "active",
        )
    )
    return [((b.start_date, b.end_date), title) for b, title in rows]


def posting_ranges(p: Posting) -> list[Range]:
    return blocked_ranges(p.start_date, p.end_date, p.schedule_pattern, p.is_exclusive)


def booking_conflict(booked: list[tuple[Range, str]], p: Posting) -> str | None:
    mine = posting_ranges(p)
    for rng, title in booked:
        hit = overlap(mine, [rng])
        if hit:
            return f"You’re booked {fmt(hit[0])} – {fmt(hit[1])} ({title})"
    return None


def fmt(d: date) -> str:
    return d.strftime("%b ") + str(d.day)


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def score(p: Posting, profile: WorkerProfile, ev: Evaluation, today: date, now: datetime):
    breakdown = []
    if p.trade in (profile.trades or []):
        breakdown.append({"label": f"Matches your trade ({p.trade})", "points": WEIGHTS["trade_match"]})
    dist = distance_km(profile.lat, profile.lng, p.lat, p.lng)
    radius = max(profile.travel_radius_km or 0, 1)
    if dist is not None and dist <= radius:
        points = round(WEIGHTS["within_radius"] * (1 - dist / radius))
        breakdown.append(
            {"label": f"{round(dist)} km away, inside your {radius} km radius", "points": points}
        )
    if 0 <= (p.start_date - today).days <= STARTS_SOON_DAYS:
        breakdown.append(
            {"label": f"Starts within {STARTS_SOON_DAYS} days", "points": WEIGHTS["starts_soon"]}
        )
    if now - as_utc(p.created_at) <= timedelta(hours=NEW_POSTING_HOURS):
        breakdown.append({"label": "Posted in the last 2 days", "points": WEIGHTS["new_posting"]})
    if ev.nice_total and ev.nice_held == ev.nice_total:
        breakdown.append({"label": "You hold every nice-to-have certification", "points": WEIGHTS["nice_to_haves"]})
    return sum(b["points"] for b in breakdown), breakdown, dist


def card(db, p: Posting, org: Organization, ev: Evaluation, **extra) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "trade": p.trade,
        "posting_type": p.posting_type,
        "org": {
            "id": org.id,
            "name": org.name,
            "kind": org.kind,
            "verified": org.verification_status == "verified",
            "industry": org.industry,
        },
        "city": p.city,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "schedule_pattern": p.schedule_pattern,
        "is_exclusive": p.is_exclusive,
        "pay_rate_cents": p.pay_rate_cents,
        "pay_unit": p.pay_unit,
        "headcount": p.headcount,
        "status": p.status,
        "created_at": p.created_at,
        "match": {
            "required_total": ev.required_total,
            "required_held": ev.required_held,
            "items": ev.items,
        },
        "eligible": ev.eligible,
        "reasons": ev.reasons,
        **extra,
    }


@dataclass
class FeedFilters:
    q: str = ""
    trade: str | None = None
    max_km: int | None = None
    starts_before: date | None = None
    min_pay_cents: int | None = None
    posting_type: str | None = None
    qualified_only: bool = True


def hourly(p: Posting) -> int | None:
    if p.pay_unit == "hour":
        return p.pay_rate_cents
    if p.pay_unit == "day":
        return p.pay_rate_cents // 8
    return None


def feed(db: Session, user: User, filters: FeedFilters, today: date | None = None) -> dict:
    today = today or date.today()
    now = datetime.now(timezone.utc)
    profile = db.get(WorkerProfile, user.id)
    types = type_map(db)
    wallet = held(db, user.id, today)
    booked = booked_ranges(db, user.id)
    applied = set(
        db.scalars(
            select(ContractApplication.posting_id).where(
                ContractApplication.applicant_user_id == user.id,
                ContractApplication.status.in_(OPEN_APPLICATION | {"accepted"}),
            )
        )
    )
    rows = list(
        db.execute(
            select(Posting, Organization)
            .join(Organization, Posting.org_id == Organization.id)
            .where(
                Posting.status == "open",
                Posting.posting_type == "individual",
                Posting.end_date >= today,
            )
        )
    )
    reqs = requirements_for(db, [p.id for p, _ in rows])
    cards = []
    for p, org in rows:
        if p.id in applied:
            continue
        if filters.trade and p.trade != filters.trade:
            continue
        if filters.q and filters.q.lower() not in f"{p.title} {p.trade} {org.name} {p.city}".lower():
            continue
        if filters.starts_before and p.start_date > filters.starts_before:
            continue
        rate = hourly(p)
        if filters.min_pay_cents and (rate is None or rate < filters.min_pay_cents):
            continue
        ev = evaluate(reqs[p.id], wallet, types)
        conflict = booking_conflict(booked, p)
        if conflict:
            ev.reasons.append(conflict)
        total, breakdown, dist = score(p, profile, ev, today, now)
        if filters.max_km is not None and (dist is None or dist > filters.max_km):
            continue
        if filters.qualified_only and not ev.eligible:
            continue
        cards.append(
            card(
                db,
                p,
                org,
                ev,
                distance_km=round(dist) if dist is not None else None,
                score=total,
                score_breakdown=breakdown,
                is_new=now - as_utc(p.created_at) <= timedelta(hours=NEW_SINCE_HOURS),
            )
        )
    cards.sort(key=lambda c: (not c["eligible"], -c["score"], -c["created_at"].timestamp()))
    new = [c for c in cards if c["is_new"] and c["eligible"]]
    return {"items": cards, "new_count": len(new)}


def unlock_counts(db: Session, user: User) -> dict[str, int]:
    """How many open contracts each single missing ticket would unlock (PROF-3)."""
    if user.default_mode != "worker":
        return {}
    today = date.today()
    wallet = held(db, user.id, today)
    postings = list(
        db.scalars(
            select(Posting).where(
                Posting.status == "open",
                Posting.posting_type == "individual",
                Posting.end_date >= today,
            )
        )
    )
    # Only suggest certifications for work in the worker's own trades.
    profile = db.get(WorkerProfile, user.id)
    trades = set(profile.trades or []) if profile else set()
    if trades:
        postings = [p for p in postings if p.trade in trades]
    reqs = requirements_for(db, [p.id for p in postings])
    counts: dict[str, int] = {}
    for p in postings:
        missing = [
            r.credential_type_id
            for r in reqs[p.id]
            if r.required and r.credential_type_id not in wallet
        ]
        if len(missing) == 1:
            counts[missing[0]] = counts.get(missing[0], 0) + 1
    return counts

"""Shift V1 postings, For You feed, applications, Work and Home views."""

from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from .auth import Database
from .catalog import TEMPLATES, coordinates, distance_km
from .config import settings
from .feed import FeedFilters, card, evaluate, feed, org_held, requirements_for
from .flow import (
    applicants_for,
    application_view,
    apply,
    new_applicants,
    org_engagements,
    org_postings,
    owns_posting,
    transition,
    worker_work,
)
from .engagements import sync_completions
from .market_common import audit, require_org, require_worker, user_org
from .market_models import (
    ContractApplication,
    Credential,
    CredentialType,
    Posting,
    PostingRequirement,
    User,
    WorkerProfile,
)
from .market_schemas import (
    ActionInput,
    ApplicationView,
    ApplyInput,
    FeedView,
    HomeView,
    OrgWorkView,
    PostingCard,
    PostingDetail,
    PostingInput,
    TalentCard,
    WorkView,
)
from .models import Organization
from .profile_routes import credential_view
from .session import CurrentUser
from .wallet import effective_status, expiring_soon, held, type_map, user_credentials

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/posting-templates")
def posting_templates():
    return TEMPLATES


@router.get("/feed", response_model=FeedView)
def for_you(
    db: Database,
    user: CurrentUser,
    q: str = Query("", max_length=100),
    trade: str | None = None,
    max_km: int | None = Query(None, ge=1, le=2000),
    starts_before: date | None = None,
    min_pay_cents: int | None = Query(None, ge=0),
    qualified_only: bool = True,
):
    require_worker(db, user)
    filters = FeedFilters(
        q=q.strip(),
        trade=trade or None,
        max_km=max_km,
        starts_before=starts_before,
        min_pay_cents=min_pay_cents,
        qualified_only=qualified_only,
    )
    return feed(db, user, filters)


@router.get("/agency-feed", response_model=FeedView)
def agency_feed(db: Database, user: CurrentUser, qualified_only: bool = True):
    """Crew contracts for contracting companies, checked against the company wallet."""
    org = require_org(db, user, "agency")
    rows = list(
        db.execute(
            select(Posting, Organization)
            .join(Organization, Posting.org_id == Organization.id)
            .where(
                Posting.status == "open",
                Posting.posting_type == "agency",
                Posting.end_date >= date.today(),
            )
            .order_by(Posting.start_date)
        )
    )
    applied = set(
        db.scalars(
            select(ContractApplication.posting_id).where(
                ContractApplication.applicant_org_id == org.id,
                ContractApplication.status.notin_(["withdrawn"]),
            )
        )
    )
    reqs = requirements_for(db, [p.id for p, _ in rows])
    types, wallet = type_map(db), org_held(db, org.id)
    items = []
    for p, owner in rows:
        if p.id in applied:
            continue
        ev = evaluate(reqs[p.id], wallet, types)
        if qualified_only and not ev.eligible:
            continue
        dist = distance_km(org.lat, org.lng, p.lat, p.lng)
        items.append(card(db, p, owner, ev, distance_km=round(dist) if dist is not None else None))
    return {"items": items, "new_count": 0}


def save_requirements(db, posting: Posting, payload: PostingInput, org: Organization) -> None:
    applies = "org" if payload.posting_type == "agency" else "worker"
    for r in payload.requirements:
        t = db.get(CredentialType, r.credential_type_id)
        if not t:
            raise HTTPException(422, "Unknown credential in requirements")
        if t.applies_to != applies:
            kind = "company" if applies == "org" else "worker"
            raise HTTPException(422, f"{t.name} isn’t a {kind} credential")
    for old in db.scalars(select(PostingRequirement).where(PostingRequirement.posting_id == posting.id)):
        db.delete(old)
    db.flush()
    for r in payload.requirements:
        db.add(PostingRequirement(posting_id=posting.id, **r.model_dump()))


def apply_posting(posting: Posting, payload: PostingInput) -> None:
    data = payload.model_dump(exclude={"requirements"})
    for key, value in data.items():
        setattr(posting, key, value)
    posting.lat, posting.lng = coordinates(payload.city)
    posting.site_address = (payload.site_address or "").strip() or None


def owner_card(db, p: Posting) -> dict:
    org = db.get(Organization, p.org_id)
    return next(c for c in org_postings(db, org) if c["id"] == p.id)


@router.post("/postings", response_model=PostingCard, status_code=201)
def create_posting(payload: PostingInput, db: Database, user: CurrentUser):
    org = require_org(db, user, "business")
    p = Posting(org_id=org.id)
    apply_posting(p, payload)
    db.add(p)
    db.flush()
    save_requirements(db, p, payload, org)
    audit(db, user, "posting.created", "postings", p.id, status=p.status)
    db.commit()
    return owner_card(db, p)


def owned_posting(db, user: User, posting_id: str) -> Posting:
    p = db.get(Posting, posting_id)
    if not p or not owns_posting(db, user, p):
        raise HTTPException(404, "Posting not found")
    return p


@router.put("/postings/{posting_id}", response_model=PostingCard)
def edit_posting(posting_id: str, payload: PostingInput, db: Database, user: CurrentUser):
    p = owned_posting(db, user, posting_id)
    if p.status in {"closed", "filled"}:
        raise HTTPException(409, "Closed postings can’t be edited")
    hired = db.scalar(
        select(func.count())
        .select_from(ContractApplication)
        .where(ContractApplication.posting_id == p.id, ContractApplication.status == "accepted")
    )
    if hired and (payload.start_date != p.start_date or payload.end_date != p.end_date):
        raise HTTPException(409, "Dates can’t change after someone has accepted this contract")
    apply_posting(p, payload)
    save_requirements(db, p, payload, db.get(Organization, p.org_id))
    audit(db, user, "posting.edited", "postings", p.id)
    db.commit()
    return owner_card(db, p)


@router.post("/postings/{posting_id}/close", response_model=PostingCard)
def close_posting(posting_id: str, db: Database, user: CurrentUser):
    p = owned_posting(db, user, posting_id)
    p.status = "closed"
    audit(db, user, "posting.closed", "postings", p.id)
    db.commit()
    return owner_card(db, p)


@router.get("/postings/{posting_id}", response_model=PostingDetail)
def posting_detail(posting_id: str, db: Database, user: CurrentUser):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "Posting not found")
    org = db.get(Organization, p.org_id)
    is_owner = owns_posting(db, user, p)
    if p.status == "draft" and not is_owner:
        raise HTTPException(404, "Posting not found")
    mine = None
    if user.default_mode == "worker":
        mine = db.scalar(
            select(ContractApplication).where(
                ContractApplication.posting_id == p.id, ContractApplication.applicant_user_id == user.id
            )
        )
    elif user.default_mode == "agency":
        o = user_org(db, user)
        mine = db.scalar(
            select(ContractApplication).where(
                ContractApplication.posting_id == p.id, ContractApplication.applicant_org_id == o.id
            )
        )
    if is_owner:
        posting = owner_card(db, p)
    elif user.default_mode == "worker" and p.posting_type == "individual":
        # Reuse the feed's scoring so the detail matches the card the worker tapped.
        items = feed(db, user, FeedFilters(qualified_only=False))["items"]
        posting = next((c for c in items if c["id"] == p.id), None)
        if posting is None:
            reqs = requirements_for(db, [p.id])[p.id]
            posting = card(db, p, org, evaluate(reqs, held(db, user.id), type_map(db)))
    else:
        reqs = requirements_for(db, [p.id])[p.id]
        o = user_org(db, user)
        wallet = org_held(db, o.id) if o and user.default_mode == "agency" else {}
        posting = card(db, p, org, evaluate(reqs, wallet, type_map(db)))
    if mine and mine.status in {"offered", "accepted", "completed"}:
        posting["site_address"] = p.site_address
    return PostingDetail(
        posting=posting,
        description=p.description,
        is_owner=is_owner,
        my_application=application_view(db, mine, user) if mine else None,
    )


@router.post("/postings/{posting_id}/apply", response_model=ApplicationView, status_code=201)
def apply_to_posting(posting_id: str, payload: ApplyInput, db: Database, user: CurrentUser):
    p = db.get(Posting, posting_id)
    if not p or p.status == "draft":
        raise HTTPException(404, "Posting not found")
    a = apply(db, user, p, payload.note.strip(), payload.proposed_rate_cents, payload.crew_size)
    return application_view(db, a, user)


@router.get("/postings/{posting_id}/applicants", response_model=list[ApplicationView])
def posting_applicants(posting_id: str, db: Database, user: CurrentUser):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "Posting not found")
    return applicants_for(db, user, p)


@router.post("/applications/{application_id}/action", response_model=ApplicationView)
def application_action(application_id: str, payload: ActionInput, db: Database, user: CurrentUser):
    a = db.get(ContractApplication, application_id)
    if not a:
        raise HTTPException(404, "Application not found")
    transition(db, user, a, payload.action)
    return application_view(db, a, user)


@router.get("/work", response_model=WorkView)
def my_work(db: Database, user: CurrentUser):
    if user.default_mode not in {"worker", "agency"}:
        raise HTTPException(403, "Use the business Work view")
    sync_completions(db)
    return worker_work(db, user)


@router.get("/org/work", response_model=OrgWorkView)
def org_work(db: Database, user: CurrentUser):
    org = require_org(db, user)
    sync_completions(db)
    return {"postings": org_postings(db, org), **org_engagements(db, org)}


@router.get("/home", response_model=HomeView)
def home(db: Database, user: CurrentUser):
    today = date.today()
    sync_completions(db)
    if user.default_mode == "worker":
        work = worker_work(db, user)
        upcoming = sorted(work["active"], key=lambda v: v["engagement"]["start_date"])
        nxt = upcoming[0] if upcoming else None
        types = type_map(db)
        return HomeView(
            next_shift=(
                {
                    "application_id": nxt["id"],
                    "posting_title": nxt["posting"]["title"],
                    "org_name": nxt["posting"]["org"]["name"],
                    "start_date": nxt["engagement"]["start_date"],
                    "end_date": nxt["engagement"]["end_date"],
                    "city": nxt["posting"]["city"],
                }
                if nxt
                else None
            ),
            offers=work["offers"],
            expiring=[credential_view(c, types) for c in user_credentials(db, user.id) if expiring_soon(c, today)],
        )
    org = require_org(db, user)
    if user.default_mode == "agency":
        work = worker_work(db, user)
        return HomeView(offers=work["offers"], active_contracts=len(work["active"]))
    postings = org_postings(db, org)
    eng = org_engagements(db, org)
    return HomeView(
        new_applicants=new_applicants(db, org),
        offers_awaiting=sum(p["offers_out"] or 0 for p in postings),
        open_postings=sum(1 for p in postings if p["status"] == "open"),
        active_contracts=len(eng["active"]),
    )


@router.get("/talent", response_model=list[TalentCard])
def talent(
    db: Database,
    user: CurrentUser,
    q: str = Query("", max_length=100),
    trade: str | None = None,
):
    org = require_org(db, user)
    rows = db.execute(
        select(WorkerProfile, User)
        .join(User, WorkerProfile.user_id == User.id)
        .where(WorkerProfile.is_public.is_(True))
    )
    results = []
    for prof, u in rows:
        if trade and trade not in prof.trades:
            continue
        text = f"{u.full_name} {prof.headline} {' '.join(prof.trades)} {prof.city}".lower()
        if q and q.lower() not in text:
            continue
        creds = list(db.scalars(select(Credential).where(Credential.owner_user_id == u.id)))
        live = [c for c in creds if effective_status(c) not in {"expired", "rejected"}]
        dist = distance_km(org.lat, org.lng, prof.lat, prof.lng)
        results.append(
            TalentCard(
                id=u.id,
                name=u.full_name,
                headline=prof.headline,
                trades=prof.trades,
                city=prof.city,
                distance_km=round(dist) if dist is not None else None,
                verified_tickets=sum(1 for c in live if c.status == "verified"),
                tickets=len(live),
            )
        )
    results.sort(key=lambda t: (t.distance_km if t.distance_km is not None else 9999, t.name))
    return results


dev = APIRouter(prefix="/api/v1/dev", tags=["dev"])


@dev.post("/reset")
def dev_reset(db: Database):
    """SEED-5: restore the fictional demo. Disabled outside demo mode."""
    if not settings.demo_mode:
        raise HTTPException(404, "Not found")
    from .seed import reset

    try:
        reset(db)
    except ValueError as error:
        db.rollback()
        raise HTTPException(409, str(error)) from None
    return {"reset": True, "at": datetime.now(timezone.utc)}


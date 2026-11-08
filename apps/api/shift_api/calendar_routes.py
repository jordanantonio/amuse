"""Accept offers, engagements, Google Calendar + .ics, and the Schedule tab (Phase 4)."""

from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from . import google
from .auth import Database
from .calendar_sync import event_specs, google_body, ics, title
from .engagements import (
    book,
    conflicts,
    ensure_acceptable,
    hired_count,
    lock_applicant,
    manual_overlaps,
    overlapping_open,
    sync_completions,
)
from .feed import evaluate, org_held, requirements_for
from .flow import applicant_name, application_view, is_applicant, owns_posting
from .market_common import audit, user_org
from .market_models import (
    AvailabilityBlock,
    ConnectedAccount,
    ContractApplication,
    Engagement,
    Posting,
    User,
)
from .market_schemas import (
    AcceptInput,
    AcceptPreview,
    ApplicationView,
    BlockInput,
    CalendarResult,
    ScheduleView,
)
from .models import Organization
from .profile_routes import notify, org_user_ids
from .session import CurrentUser, safe_next, verify
from .wallet import held, type_map

router = APIRouter(prefix="/api/v1/market", tags=["market"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def applicant_application(db, user: User, application_id: str) -> ContractApplication:
    a = db.get(ContractApplication, application_id)
    if not a or not is_applicant(db, user, a):
        raise HTTPException(404, "Application not found")
    return a


def requirement_reasons(db, a: ContractApplication, p: Posting) -> list[str]:
    """Re-check tickets at acceptance: something may have expired since applying."""
    wallet = held(db, a.applicant_user_id) if a.applicant_user_id else org_held(db, a.applicant_org_id)
    return evaluate(requirements_for(db, [p.id])[p.id], wallet, type_map(db)).reasons


@router.get("/applications/{application_id}/accept-preview", response_model=AcceptPreview)
def accept_preview(application_id: str, db: Database, user: CurrentUser):
    a = applicant_application(db, user, application_id)
    p = db.get(Posting, a.posting_id)
    return AcceptPreview(
        is_exclusive=p.is_exclusive,
        conflicts=conflicts(db, a, p),
        ticket_problems=requirement_reasons(db, a, p),
        overlapping=[application_view(db, o, user) for o in overlapping_open(db, a, p)],
        manual_overlaps=manual_overlaps(db, a, p),
    )


@router.post("/applications/{application_id}/accept", response_model=ApplicationView)
def accept(application_id: str, payload: AcceptInput, db: Database, user: CurrentUser):
    a = applicant_application(db, user, application_id)
    lock_applicant(db, a)
    db.refresh(a)
    p = db.get(Posting, a.posting_id)
    ensure_acceptable(db, a, p)
    problems = requirement_reasons(db, a, p)
    if problems:
        raise HTTPException(409, "Your certifications changed since you applied. " + "; ".join(problems) + ".")
    allowed = {o.id: o for o in overlapping_open(db, a, p)}
    if any(i not in allowed for i in payload.withdraw_ids):
        raise HTTPException(422, "Only overlapping applications can be withdrawn here")
    now = datetime.now(timezone.utc)
    for wid in payload.withdraw_ids:
        other = allowed[wid]
        other.status, other.updated_at = "withdrawn", now
        q = db.get(Posting, other.posting_id)
        notify(
            db,
            org_user_ids(db, q.org_id),
            "application.withdrawn",
            posting=q.title,
            posting_id=q.id,
            applicant=applicant_name(db, other),
        )
        audit(db, user, "application.withdraw", "contract_applications", other.id, reason="accepted_overlap")
    a.status, a.updated_at = "accepted", now
    e = book(db, a, p)
    db.flush()
    if hired_count(db, p.id) >= p.headcount:
        p.status = "filled"
    org = db.get(Organization, p.org_id)
    notify(
        db,
        org_user_ids(db, p.org_id),
        "offer.accepted",
        posting=p.title,
        posting_id=p.id,
        org=org.name,
        applicant=applicant_name(db, a),
    )
    audit(db, user, "offer.accepted", "contract_applications", a.id, engagement=e.id)
    db.commit()
    return application_view(db, a, user)


def engagement_for(db, user: User, engagement_id: str):
    e = db.get(Engagement, engagement_id)
    if not e:
        raise HTTPException(404, "Contract not found")
    a = db.get(ContractApplication, e.application_id)
    p = db.get(Posting, a.posting_id)
    if not (is_applicant(db, user, a) or owns_posting(db, user, p)):
        raise HTTPException(404, "Contract not found")
    return e, a, p


def describe(p: Posting, org: Organization) -> tuple[str, str, str]:
    summary = title(p.title, org.name)
    location = p.site_address or p.city
    detail = f"{p.trade} contract with {org.name}. Booked through Shift."
    return summary, location, detail


@router.get("/engagements/{engagement_id}/calendar.ics")
def download_ics(engagement_id: str, db: Database, user: CurrentUser):
    e, a, p = engagement_for(db, user, engagement_id)
    org = db.get(Organization, p.org_id)
    summary, location, detail = describe(p, org)
    body = ics(e.id, summary, location, detail, event_specs(e.start_date, e.end_date, e.schedule_pattern, e.is_exclusive))
    name = "".join(ch if ch.isalnum() else "-" for ch in p.title.lower()).strip("-")[:50] or "contract"
    return Response(
        body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="shift-{name}.ics"',
            "Cache-Control": "private, no-store",
        },
    )


def access_token(db, user: User) -> str | None:
    account = db.get(ConnectedAccount, (user.id, "google_calendar"))
    if not account:
        return None
    return google.refresh_access_token(google.decrypt(account.refresh_token_encrypted))


def delete_google_events(db, user: User, e: Engagement) -> None:
    token = access_token(db, user) if e.google_event_ids and google.calendar_enabled() else None
    if token:
        for event_id in e.google_event_ids:
            google.calendar_request("DELETE", f"/calendars/primary/events/{event_id}", token)
    e.google_event_ids = []


def push_to_google(db, user: User, e: Engagement, p: Posting) -> int:
    """Create (or replace) the Google events mirroring this engagement (CAL-1, CAL-2)."""
    token = access_token(db, user)
    if e.google_event_ids:
        for event_id in e.google_event_ids:
            google.calendar_request("DELETE", f"/calendars/primary/events/{event_id}", token)
    org = db.get(Organization, p.org_id)
    summary, location, detail = describe(p, org)
    ids = []
    for spec in event_specs(e.start_date, e.end_date, e.schedule_pattern, e.is_exclusive):
        created = google.calendar_request(
            "POST", "/calendars/primary/events", token, google_body(summary, location, detail, spec)
        )
        ids.append(created["id"])
    e.google_event_ids = ids
    return len(ids)


@router.post("/engagements/{engagement_id}/google", response_model=CalendarResult)
def add_to_google(engagement_id: str, db: Database, user: CurrentUser):
    e, a, p = engagement_for(db, user, engagement_id)
    if not is_applicant(db, user, a):
        raise HTTPException(403, "Only the person booked can add this to their calendar")
    if not google.calendar_enabled():
        return CalendarResult(
            status="unavailable",
            message="Google Calendar isn’t set up on this server. Download the .ics file instead.",
        )
    if not db.get(ConnectedAccount, (user.id, "google_calendar")):
        url = f"/api/v1/auth/google/calendar/start?engagement={e.id}&next=/work%3Ftab%3Dactive"
        return CalendarResult(status="needs_auth", url=url)
    count = push_to_google(db, user, e, p)
    audit(db, user, "calendar.synced", "engagements", e.id, events=count)
    db.commit()
    return CalendarResult(status="added", count=count)


@auth_router.get("/google/calendar/start")
def calendar_start(db: Database, user: CurrentUser, next: str | None = None, engagement: str | None = None):
    """Incremental consent for calendar.events only, at the moment it is useful (CONN-1)."""
    if not google.calendar_enabled():
        raise HTTPException(404, "Google Calendar isn’t set up on this server")
    from .auth_routes import oauth_redirect

    extra = {"uid": user.id, "hint": user.email}
    if engagement:
        extra["eng"] = engagement
    return oauth_redirect("calendar", google.CALENDAR_SCOPE, safe_next(next, "/schedule"), **extra)


def finish_calendar_connect(db, claims: dict, tokens: dict, shift_session: str | None):
    session = verify(shift_session, "session") if shift_session else None
    if not session or session.get("sub") != claims.get("uid"):
        raise HTTPException(401, "Sign in again, then connect Google Calendar")
    user = db.get(User, claims["uid"])
    refresh = tokens.get("refresh_token")
    if not refresh:
        raise HTTPException(502, "Google didn’t return calendar access. Try connecting again.")
    account = db.get(ConnectedAccount, (user.id, "google_calendar")) or ConnectedAccount(
        user_id=user.id, provider="google_calendar"
    )
    account.refresh_token_encrypted = google.encrypt(refresh)
    account.scopes = tokens.get("scope", google.CALENDAR_SCOPE)
    account.connected_at = datetime.now(timezone.utc)
    db.add(account)
    audit(db, user, "calendar.connected", "connected_accounts", user.id)
    db.commit()
    target = safe_next(claims.get("next"), "/schedule")
    if claims.get("eng"):
        e = db.get(Engagement, claims["eng"])
        a = db.get(ContractApplication, e.application_id) if e else None
        if e and a and is_applicant(db, user, a):
            push_to_google(db, user, e, db.get(Posting, a.posting_id))
            db.commit()
    sep = "&" if "?" in target else "?"
    response = RedirectResponse(f"{target}{sep}calendar=added", status_code=303)
    response.delete_cookie("shift_oauth_state", path="/api/v1/auth")
    return response


@router.post("/engagements/{engagement_id}/cancel", response_model=ApplicationView)
def cancel_engagement(engagement_id: str, db: Database, user: CurrentUser):
    e, a, p = engagement_for(db, user, engagement_id)
    if e.status != "active":
        raise HTTPException(409, "Only an active contract can be cancelled")
    if is_applicant(db, user, a):
        delete_google_events(db, user, e)
    e.status = "cancelled"
    for b in db.scalars(select(AvailabilityBlock).where(AvailabilityBlock.engagement_id == e.id)):
        db.delete(b)
    if p.status == "filled":
        p.status = "open"
    org = db.get(Organization, p.org_id)
    others = org_user_ids(db, p.org_id) if is_applicant(db, user, a) else (
        [a.applicant_user_id] if a.applicant_user_id else org_user_ids(db, a.applicant_org_id)
    )
    notify(db, others, "engagement.cancelled", posting=p.title, posting_id=p.id, org=org.name)
    audit(db, user, "engagement.cancelled", "engagements", e.id)
    db.commit()
    return application_view(db, a, user)


# ---------- Schedule tab ----------


@router.get("/schedule", response_model=ScheduleView)
def schedule(
    db: Database,
    user: CurrentUser,
    start: date,
    end: date,
):
    if end < start or (end - start).days > 62:
        raise HTTPException(422, "Choose a range of up to two months")
    sync_completions(db)
    items = []
    if user.default_mode == "business":
        org = user_org(db, user)
        rows = db.execute(
            select(Engagement, ContractApplication, Posting)
            .join(ContractApplication, Engagement.application_id == ContractApplication.id)
            .join(Posting, ContractApplication.posting_id == Posting.id)
            .where(
                Posting.org_id == org.id,
                Engagement.status != "cancelled",
                Engagement.start_date <= end,
                Engagement.end_date >= start,
            )
        )
        for e, a, p in rows:
            items.append(
                {
                    "id": e.id,
                    "kind": "engagement",
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "title": p.title,
                    "subtitle": applicant_name(db, a),
                    "posting_id": p.id,
                    "engagement_id": e.id,
                    "status": e.status,
                    "person_id": a.applicant_user_id,
                }
            )
    else:
        org = user_org(db, user)
        owner = (
            AvailabilityBlock.user_id == user.id
            if user.default_mode == "worker"
            else AvailabilityBlock.org_id == (org.id if org else None)
        )
        blocks = db.scalars(
            select(AvailabilityBlock).where(
                owner, AvailabilityBlock.start_date <= end, AvailabilityBlock.end_date >= start
            )
        )
        for b in blocks:
            if b.source == "engagement":
                e = db.get(Engagement, b.engagement_id)
                if e.status == "cancelled":
                    continue
                a = db.get(ContractApplication, e.application_id)
                p = db.get(Posting, a.posting_id)
                owner = db.get(Organization, p.org_id)
                items.append(
                    {
                        "id": b.id,
                        "kind": "engagement",
                        "start_date": b.start_date,
                        "end_date": b.end_date,
                        "title": p.title,
                        "subtitle": owner.name,
                        "posting_id": p.id,
                        "engagement_id": e.id,
                        "status": e.status,
                        "industry": owner.industry,
                    }
                )
            else:
                items.append(
                    {
                        "id": b.id,
                        "kind": "manual",
                        "start_date": b.start_date,
                        "end_date": b.end_date,
                        "title": b.note or "Unavailable",
                        "subtitle": "",
                    }
                )
    return ScheduleView(
        items=items,
        calendar_enabled=google.calendar_enabled(),
        calendar_connected=bool(db.get(ConnectedAccount, (user.id, "google_calendar"))),
    )


@router.post("/availability", status_code=201)
def add_block(payload: BlockInput, db: Database, user: CurrentUser):
    if user.default_mode != "worker":
        raise HTTPException(403, "Unavailable days are for worker accounts")
    if payload.end_date - payload.start_date > timedelta(days=366):
        raise HTTPException(422, "Block at most one year at a time")
    b = AvailabilityBlock(
        user_id=user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        source="manual",
        note=payload.note.strip(),
    )
    db.add(b)
    db.commit()
    return {"id": b.id}


@router.delete("/availability/{block_id}")
def delete_block(block_id: str, db: Database, user: CurrentUser):
    b = db.get(AvailabilityBlock, block_id)
    if not b or b.user_id != user.id or b.source != "manual":
        raise HTTPException(404, "Block not found")
    db.delete(b)
    db.commit()
    return {"deleted": True}


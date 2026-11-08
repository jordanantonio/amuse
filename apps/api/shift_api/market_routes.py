"""Shift V1: the signed-in account, onboarding and reference data."""

from fastapi import APIRouter, HTTPException
from .auth import Database
from .catalog import CITIES, INDUSTRIES, SCHEDULE_PATTERNS, TRADES, coordinates
from .market_common import unique_handle, user_org
from .market_models import OrgMember, User, WorkerProfile
from .market_schemas import City, MeView, Meta, OnboardingInput, OrgView, UserView, WorkerProfileView
from .models import Organization
from .session import CurrentUser

router = APIRouter(prefix="/api/v1/market", tags=["market"])


def me_view(db, user: User) -> MeView:
    profile = db.get(WorkerProfile, user.id)
    org = user_org(db, user)
    connected = False
    try:
        from .market_models import ConnectedAccount

        connected = bool(db.get(ConnectedAccount, (user.id, "google_calendar")))
    except ImportError:
        pass
    return MeView(
        user=UserView.model_validate(user),
        mode=user.default_mode,
        onboarded=user.onboarded,
        worker_profile=WorkerProfileView.model_validate(profile) if profile else None,
        organization=OrgView.model_validate(org) if org else None,
        planner_persona=user.membership_id,
        calendar_connected=connected,
    )


@router.get("/me", response_model=MeView)
def me(db: Database, user: CurrentUser):
    return me_view(db, user)


@router.get("/meta", response_model=Meta)
def meta():
    return Meta(
        trades=TRADES,
        industries=INDUSTRIES,
        cities=[City(name=n, lat=lat, lng=lng) for n, (lat, lng) in CITIES.items()],
        schedule_patterns=SCHEDULE_PATTERNS,
    )


@router.put("/onboarding", response_model=MeView)
def onboarding(payload: OnboardingInput, db: Database, user: CurrentUser):
    """Step-wise and idempotent: each step sends only the fields it collects."""
    if payload.role:
        if user.default_mode and user.default_mode != payload.role:
            raise HTTPException(409, "This account already has a role. Use a new account.")
        user.default_mode = payload.role
    if not user.default_mode:
        raise HTTPException(422, "Choose how you'll use Shift first")
    if payload.full_name:
        user.full_name = payload.full_name
    if user.default_mode == "worker":
        profile = db.get(WorkerProfile, user.id)
        if not profile:
            profile = WorkerProfile(
                user_id=user.id,
                handle=unique_handle(db, user.full_name, WorkerProfile, WorkerProfile.handle),
                trades=[],
            )
            db.add(profile)
        if payload.headline is not None:
            profile.headline = payload.headline
        if payload.trades is not None:
            profile.trades = payload.trades
        if payload.city is not None:
            profile.city = payload.city
            profile.lat, profile.lng = coordinates(payload.city)
        if payload.travel_radius_km is not None:
            profile.travel_radius_km = payload.travel_radius_km
    else:
        org = user_org(db, user)
        if not org:
            name = payload.org_name or f"{user.full_name}'s company"
            org = Organization(
                name=name,
                kind=user.default_mode,
                is_demo=user.email.endswith("@demo.shift.local"),
                handle=unique_handle(db, name, Organization, Organization.handle),
            )
            db.add(org)
            db.flush()
            db.add(OrgMember(org_id=org.id, user_id=user.id, role="owner"))
        if payload.org_name:
            org.name = payload.org_name
        if payload.industry is not None:
            org.industry = payload.industry
        if payload.city is not None:
            org.city = payload.city
            org.lat, org.lng = coordinates(payload.city)
    if payload.finish:
        user.onboarded = True
    db.commit()
    return me_view(db, user)

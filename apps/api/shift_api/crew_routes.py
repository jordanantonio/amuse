"""Crew planner API (CREW-1..3, CREW-5) for business accounts."""

from datetime import date, timedelta
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from .auth import Database
from .crew import (
    bookings,
    candidate_rows,
    covers,
    hours_by_weekday,
    overlapping,
    rules_for,
    slot_times,
    week_start,
)
from .crew_solver import autofill, week_slots
from .market_common import audit, require_org
from .market_models import CredentialType, CrewAssignment, CrewMember, CrewSlot, User
from .session import CurrentUser
from .wallet import held

router = APIRouter(prefix="/api/v1/market/crew", tags=["crew"])


class SpotView(BaseModel):
    assignment_id: str
    user_id: str
    name: str
    status: Literal["assigned", "proposed"]


class CertRef(BaseModel):
    id: str
    name: str


class SlotView(BaseModel):
    id: str
    day: date
    start_minute: int
    end_minute: int
    label: str
    needed: int
    preferred_cert: CertRef | None
    required_certs: list[CertRef]
    spots: list[SpotView]


class RulesView(BaseModel):
    max_consecutive_days: int = Field(ge=1, le=14)
    min_rest_hours: int = Field(ge=0, le=24)
    max_weekly_hours: int = Field(ge=1, le=84)


class WeekView(BaseModel):
    start: date
    slots: list[SlotView]
    rules: RulesView
    crew_size: int
    proposed: int


class CandidateCert(BaseModel):
    id: str
    name: str
    state: str
    kind: str


class BreakdownRow(BaseModel):
    kind: str
    label: str
    points: int
    strength: float


class Bar(BaseModel):
    free: list[list[int]]
    booked: list[list[int]]
    slot: list[int]


class CandidateView(BaseModel):
    user_id: str
    name: str
    headline: str
    on_crew: bool
    certs: list[CandidateCert]
    score: int
    breakdown: list[BreakdownRow]
    warnings: list[str]
    blockers: list[str]
    bar: Bar


class AssignInput(BaseModel):
    user_id: str


class AutofillResult(BaseModel):
    proposed: int
    unfilled_slot_ids: list[str]
    solver_status: str


class AcceptInput(BaseModel):
    start: date
    assignment_ids: list[str] = Field(default_factory=list, max_length=200)


def business(db, user):
    return require_org(db, user, "business")


def slot_view(db, slot: CrewSlot, types: dict[str, str]) -> SlotView:
    rows = db.execute(
        select(CrewAssignment, User.full_name)
        .join(User, CrewAssignment.user_id == User.id)
        .where(CrewAssignment.slot_id == slot.id)
        .order_by(CrewAssignment.status, CrewAssignment.created_at)
    )
    return SlotView(
        id=slot.id,
        day=slot.day,
        start_minute=slot.start_minute,
        end_minute=slot.end_minute,
        label=slot.label,
        needed=slot.needed,
        preferred_cert=CertRef(id=slot.preferred_cert, name=types.get(slot.preferred_cert, ""))
        if slot.preferred_cert
        else None,
        required_certs=[CertRef(id=c, name=types.get(c, c)) for c in slot.required_certs],
        spots=[
            SpotView(assignment_id=a.id, user_id=a.user_id, name=name, status=a.status)
            for a, name in rows
        ],
    )


def week_view(db, org_id: str, start: date) -> WeekView:
    types = {t.id: t.name for t in db.scalars(select(CredentialType))}
    slots = [slot_view(db, s, types) for s in week_slots(db, org_id, start)]
    rules = rules_for(db, org_id)
    crew = db.scalars(select(CrewMember.user_id).where(CrewMember.org_id == org_id)).all()
    return WeekView(
        start=start,
        slots=slots,
        rules=RulesView.model_validate(rules, from_attributes=True),
        crew_size=len(crew),
        proposed=sum(1 for s in slots for p in s.spots if p.status == "proposed"),
    )


def owned_slot(db, org_id: str, slot_id: str) -> CrewSlot:
    slot = db.get(CrewSlot, slot_id)
    if not slot or slot.org_id != org_id:
        raise HTTPException(404, "Shift not found")
    return slot


@router.get("/week", response_model=WeekView)
def get_week(db: Database, user: CurrentUser, start: date | None = None):
    org = business(db, user)
    view = week_view(db, org.id, week_start(start or date.today()))
    db.commit()
    return view


@router.get("/slots/{slot_id}/candidates", response_model=list[CandidateView])
def candidates(slot_id: str, db: Database, user: CurrentUser, scope: Literal["crew", "market"] = "crew"):
    org = business(db, user)
    slot = owned_slot(db, org.id, slot_id)
    return candidate_rows(db, org, slot, scope)


@router.post("/slots/{slot_id}/assign", response_model=SlotView)
def assign(slot_id: str, payload: AssignInput, db: Database, user: CurrentUser):
    org = business(db, user)
    slot = owned_slot(db, org.id, slot_id)
    worker = db.get(User, payload.user_id)
    if not worker or worker.default_mode != "worker":
        raise HTTPException(404, "Worker not found")
    existing = db.scalars(select(CrewAssignment).where(CrewAssignment.slot_id == slot.id)).all()
    mine = next((a for a in existing if a.user_id == worker.id), None)
    if mine and mine.status == "assigned":
        raise HTTPException(409, f"{worker.full_name} is already on this shift")
    if not mine and sum(1 for a in existing if a.status == "assigned") >= slot.needed:
        raise HTTPException(409, "This shift is already fully staffed")
    wallet = held(db, worker.id, slot.day)
    missing = [c for c in slot.required_certs if c not in wallet]
    if missing:
        raise HTTPException(409, f"{worker.full_name} is missing a required certification")
    if not covers(hours_by_weekday(db, worker.id), slot):
        raise HTTPException(409, f"{worker.full_name} hasn’t published availability for this shift")
    shifts = bookings(db, worker.id, slot.day - timedelta(days=1), slot.day + timedelta(days=1), exclude_slot=slot.id)
    clash = overlapping(shifts, slot_times(slot))
    if clash:
        raise HTTPException(409, f"{worker.full_name} is already booked: {clash[2]}. Shift never double-books.")
    if mine:
        mine.status = "assigned"
    else:
        db.add(CrewAssignment(slot_id=slot.id, user_id=worker.id, status="assigned"))
    audit(db, user, "crew.assigned", "crew_slots", slot.id, worker=worker.id)
    db.commit()
    types = {t.id: t.name for t in db.scalars(select(CredentialType))}
    return slot_view(db, slot, types)


@router.delete("/assignments/{assignment_id}", response_model=SlotView)
def unassign(assignment_id: str, db: Database, user: CurrentUser):
    org = business(db, user)
    a = db.get(CrewAssignment, assignment_id)
    if not a:
        raise HTTPException(404, "Assignment not found")
    slot = owned_slot(db, org.id, a.slot_id)
    db.delete(a)
    audit(db, user, "crew.unassigned", "crew_slots", slot.id, worker=a.user_id)
    db.commit()
    types = {t.id: t.name for t in db.scalars(select(CredentialType))}
    return slot_view(db, slot, types)


@router.post("/autofill", response_model=AutofillResult)
def run_autofill(db: Database, user: CurrentUser, start: date | None = None):
    org = business(db, user)
    result = autofill(db, org.id, week_start(start or date.today()))
    audit(db, user, "crew.autofill", "organizations", org.id, **result)
    db.commit()
    return result


@router.post("/proposals/accept", response_model=WeekView)
def accept_proposals(payload: AcceptInput, db: Database, user: CurrentUser):
    org = business(db, user)
    start = week_start(payload.start)
    ids = {s.id for s in week_slots(db, org.id, start)}
    query = select(CrewAssignment).where(
        CrewAssignment.slot_id.in_(ids), CrewAssignment.status == "proposed"
    )
    if payload.assignment_ids:
        query = query.where(CrewAssignment.id.in_(payload.assignment_ids))
    for a in db.scalars(query):
        slot = db.get(CrewSlot, a.slot_id)
        shifts = bookings(db, a.user_id, slot.day - timedelta(days=1), slot.day + timedelta(days=1), exclude_slot=slot.id)
        if overlapping(shifts, slot_times(slot)):
            raise HTTPException(409, "A proposal now overlaps another booking. Run Auto-fill again.")
        a.status = "assigned"
    audit(db, user, "crew.proposals_accepted", "organizations", org.id)
    db.commit()
    return week_view(db, org.id, start)


@router.post("/proposals/clear", response_model=WeekView)
def clear_week_proposals(db: Database, user: CurrentUser, start: date | None = None):
    from .crew_solver import clear_proposals

    org = business(db, user)
    week = week_start(start or date.today())
    clear_proposals(db, week_slots(db, org.id, week))
    db.commit()
    return week_view(db, org.id, week)


@router.put("/rules", response_model=RulesView)
def update_rules(payload: RulesView, db: Database, user: CurrentUser):
    org = business(db, user)
    rules = rules_for(db, org.id)
    for k, v in payload.model_dump().items():
        setattr(rules, k, v)
    audit(db, user, "crew.rules_updated", "crew_rules", org.id, **payload.model_dump())
    db.commit()
    return payload

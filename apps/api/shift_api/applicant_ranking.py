"""Applicant ranking for businesses (RANK-1..4).

Applicants who meet the requirements are sorted by an explainable fit score; low-effort
signals only push someone down and flag them, they never reject anyone. Applicants missing
a required certification or booked over the dates go to a collapsed pile the manager can
decline in one click with a polite message. Auto-decline is off unless the business opts in.
"""

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .catalog import distance_km
from .feed import OPEN_APPLICATION, as_utc, booked_ranges, booking_conflict, requirements_for
from .flow import application_view, owns_posting
from .market_common import audit
from .market_models import ContractApplication, Posting, User, WorkerProfile
from .models import Organization
from .profile_routes import notify
from .ranking import BONUS_LABEL, fit_score
from .wallet import held, type_map

BURST_COUNT = 10
BURST_WINDOW = timedelta(minutes=5)


def burst(db: Session, user_id: str) -> bool:
    """True when someone sent 10+ applications inside any 5-minute window."""
    times = sorted(
        as_utc(t)
        for t in db.scalars(
            select(ContractApplication.created_at).where(ContractApplication.applicant_user_id == user_id)
        )
    )
    return any(
        times[i + BURST_COUNT - 1] - times[i] < BURST_WINDOW for i in range(len(times) - BURST_COUNT + 1)
    )


def coverage(db: Session, p: Posting, types) -> tuple[list[dict], set[str]]:
    hired = list(
        db.scalars(
            select(ContractApplication.applicant_user_id).where(
                ContractApplication.posting_id == p.id,
                ContractApplication.status.in_(["accepted", "completed"]),
                ContractApplication.applicant_user_id.is_not(None),
            )
        )
    )
    wallets = {uid: held(db, uid) for uid in hired}
    rows, gaps = [], set()
    for need in p.coverage or []:
        cid, needed = need["credential_type_id"], int(need["needed"])
        have = sum(1 for w in wallets.values() if cid in w)
        name = types[cid].name.split(" (")[0] if cid in types else cid
        covered = have >= needed
        if not covered:
            gaps.add(cid)
        rows.append(
            {
                "credential_type_id": cid,
                "name": name,
                "needed": needed,
                "hired": have,
                "covered": covered,
                "label": f"{name}: need {needed}, {'covered' if covered else f'hired {have}'}",
            }
        )
    return rows, gaps


def ranking(db: Session, viewer: User, p: Posting) -> dict:
    if not owns_posting(db, viewer, p):
        raise HTTPException(404, "Posting not found")
    types = type_map(db)
    reqs = requirements_for(db, [p.id])[p.id]
    required = [r for r in reqs if r.required]
    bonus = [r for r in reqs if not r.required]
    cover_rows, gaps = coverage(db, p, types)
    apps = list(
        db.scalars(
            select(ContractApplication).where(
                ContractApplication.posting_id == p.id,
                ContractApplication.status.in_(OPEN_APPLICATION),
            )
        )
    )
    main, pile = [], []
    for a in apps:
        view = application_view(db, a, viewer)
        if a.applicant_user_id:
            uid = a.applicant_user_id
            wallet = held(db, uid)
            profile = db.get(WorkerProfile, uid)
            dist = distance_km(profile.lat, profile.lng, p.lat, p.lng) if profile else None
            radius = profile.travel_radius_km if profile else None
            conflict = booking_conflict(booked_ranges(db, uid), p)
        else:
            from .feed import org_held

            wallet = org_held(db, a.applicant_org_id)
            dist, radius, conflict = None, None, None
        missing = [types[r.credential_type_id].name.split(" (")[0] for r in required if r.credential_type_id not in wallet]
        fit = fit_score(
            required_total=len(required),
            required_held=len(required) - len(missing),
            required_verified=sum(1 for r in required if wallet.get(r.credential_type_id) == "verified"),
            bonus=[
                (types[r.credential_type_id].name.split(" (")[0], r.weight or "nice", r.credential_type_id in wallet)
                for r in bonus
            ],
            distance_km=dist,
            radius_km=radius,
            available=conflict is None,
            warnings=[],
        )
        signals = []
        if a.applicant_user_id and burst(db, a.applicant_user_id):
            signals.append("Applied to 10+ postings in under 5 minutes")
        if p.questions and not (a.answers or {}):
            signals.append("Skipped all screening questions")
        if dist is not None and radius is not None and dist > radius:
            signals.append("Outside their travel radius")
        entry = {
            **view,
            "score": fit.score,
            "breakdown": fit.rows,
            "bonus": [
                {
                    "name": types[r.credential_type_id].name.split(" (")[0],
                    "weight": BONUS_LABEL[r.weight or "nice"],
                    "held": r.credential_type_id in wallet,
                }
                for r in bonus
            ],
            "fills_gap": [
                types[c].name.split(" (")[0] for c in gaps if c in wallet and c in types
            ],
            "signals": signals,
            "answers": [
                {"prompt": q["prompt"], "answer": (a.answers or {}).get(q["id"], "")}
                for q in (p.questions or [])
            ],
            "pile_reasons": (["Missing " + ", ".join(missing)] if missing else [])
            + ([conflict.replace("You’re", "Already")] if conflict else []),
        }
        (pile if entry["pile_reasons"] else main).append(entry)
    # Low-effort signals push people down; they never remove anyone.
    main.sort(key=lambda e: (bool(e["signals"]), -e["score"], e["created_at"]))
    pile.sort(key=lambda e: -e["score"])
    return {"coverage": cover_rows, "applicants": main, "pile": pile, "auto_decline": p.auto_decline}


def polite_decline(db: Session, viewer: User, p: Posting, a: ContractApplication, reason: str) -> None:
    org = db.get(Organization, p.org_id)
    a.status = "declined"
    a.updated_at = datetime.now(timezone.utc)
    if a.applicant_user_id:
        notify(
            db,
            [a.applicant_user_id],
            "application.declined",
            posting=p.title,
            posting_id=p.id,
            org=org.name,
            message=(
                f"Thanks for applying to {p.title}. {reason} so {org.name} isn’t moving forward "
                "this time. Contracts that fit you are on Home."
            ),
        )
    audit(db, viewer, "application.auto_decline", "contract_applications", a.id, reason=reason)


def decline_pile(db: Session, viewer: User, p: Posting, missing_only: bool = False) -> int:
    view = ranking(db, viewer, p)
    count = 0
    for entry in view["pile"]:
        reasons = [r for r in entry["pile_reasons"] if r.startswith("Missing")] if missing_only else entry["pile_reasons"]
        if not reasons:
            continue
        a = db.get(ContractApplication, entry["id"])
        reason = (
            f"This contract needs {reasons[0].removeprefix('Missing ')}"
            if reasons[0].startswith("Missing")
            else "The dates overlap work you’re already booked for"
        )
        polite_decline(db, viewer, p, a, reason)
        count += 1
    db.commit()
    return count

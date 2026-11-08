"""Credential wallet rules: computed status, expiry warnings and profile completeness."""

from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from .feed_config import EXPIRING_SOON_DAYS
from .market_models import Credential, CredentialType, User, WorkerProfile, WorkHistory


def today() -> date:
    return date.today()


def effective_status(c: Credential, on: date | None = None) -> str:
    """Stored status, except an expiry date in the past always reads as 'expired' (CRED-2)."""
    on = on or today()
    if c.status == "rejected":
        return "rejected"
    if c.expires_on and c.expires_on < on:
        return "expired"
    return c.status


def days_to_expiry(c: Credential, on: date | None = None) -> int | None:
    return (c.expires_on - (on or today())).days if c.expires_on else None


def expiring_soon(c: Credential, on: date | None = None) -> bool:
    days = days_to_expiry(c, on)
    return effective_status(c, on) not in {"expired", "rejected"} and days is not None and (
        0 <= days <= EXPIRING_SOON_DAYS
    )


def credential_name(c: Credential, types: dict[str, CredentialType]) -> str:
    if c.credential_type_id and c.credential_type_id in types:
        return types[c.credential_type_id].name
    return c.custom_name or "Other credential"


def type_map(db: Session) -> dict[str, CredentialType]:
    return {t.id: t for t in db.scalars(select(CredentialType))}


def user_credentials(db: Session, user_id: str) -> list[Credential]:
    return list(
        db.scalars(
            select(Credential)
            .where(Credential.owner_user_id == user_id)
            .order_by(Credential.created_at)
        )
    )


def held(db: Session, user_id: str, on: date | None = None) -> dict[str, str]:
    """Catalog types a worker holds right now: type id -> 'verified' | 'unverified'."""
    result: dict[str, str] = {}
    for c in user_credentials(db, user_id):
        status = effective_status(c, on)
        if not c.credential_type_id or status in {"expired", "rejected"}:
            continue
        level = "verified" if status == "verified" else "unverified"
        if result.get(c.credential_type_id) != "verified":
            result[c.credential_type_id] = level
    return result


def completeness(db: Session, user: User, profile: WorkerProfile) -> dict:
    creds = user_credentials(db, user.id)
    history = db.scalar(select(WorkHistory.id).where(WorkHistory.user_id == user.id).limit(1))
    steps = [
        ("headline", "Add a headline", bool(profile.headline)),
        ("trades", "Choose your trades", bool(profile.trades)),
        ("city", "Set your home city", bool(profile.city)),
        ("rate", "Add your preferred rate", profile.rate_min_cents is not None),
        ("bio", "Write a short bio", bool(profile.bio)),
        ("credential", "Add a ticket to your wallet", bool(creds)),
        ("document", "Upload proof for a ticket", any(c.document_path for c in creds)),
        ("history", "Add a past job", bool(history)),
    ]
    done = sum(1 for *_, ok in steps if ok)
    next_step = next(({"key": k, "label": label} for k, label, ok in steps if not ok), None)
    unlock = best_unlock(db, user)
    if unlock:
        next_step = unlock
    return {
        "percent": round(100 * done / len(steps)),
        "steps": [{"key": k, "label": label, "done": ok} for k, label, ok in steps],
        "next_step": next_step,
    }


def best_unlock(db: Session, user: User) -> dict | None:
    """The single missing ticket that would open the most contracts (PROF-3)."""
    try:
        from .feed import unlock_counts
    except ImportError:
        return None
    counts = unlock_counts(db, user)
    if not counts:
        return None
    type_id, count = max(counts.items(), key=lambda kv: kv[1])
    name = type_map(db)[type_id].name
    noun = "contract" if count == 1 else "contracts"
    return {
        "key": "unlock",
        "label": f"Add your {name} ticket to unlock {count} more {noun}",
        "credential_type_id": type_id,
    }

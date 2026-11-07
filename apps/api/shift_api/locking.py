"""Serialize tenant scheduling mutations across processes and re-read under the lock."""

import hashlib
from sqlalchemy import text
from sqlalchemy.orm import Session


def lock_schedule(db: Session, organization_id: str):
    # End the dependency's read transaction before taking an exclusive write boundary.
    db.rollback()
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    elif db.bind.dialect.name == "postgresql":
        key = int.from_bytes(
            hashlib.sha256(organization_id.encode()).digest()[:8], "big", signed=True
        )
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    else:
        raise RuntimeError("Unsupported scheduling transaction backend")
    db.expire_all()

    from datetime import datetime, timezone
    from sqlalchemy import select, delete
    from .models import RecoveryProposal, Project, SlotReservation
    from .solver_time import utc

    for proposal in db.scalars(
        select(RecoveryProposal)
        .join(Project)
        .where(
            Project.organization_id == organization_id,
            RecoveryProposal.status.not_in(
                ["published", "rejected", "revision_requested", "expired"]
            ),
        )
    ):
        if utc(proposal.expires_at) <= datetime.now(timezone.utc):
            proposal.status = "expired"
            db.execute(delete(SlotReservation).where(SlotReservation.proposal_id == proposal.id))
    db.flush()

"""Engagements (accepted contracts) and the availability blocks they create (FLOW-4)."""

from sqlalchemy.orm import Session
from .market_models import AvailabilityBlock, ContractApplication, Engagement, Posting
from .schedule import blocked_ranges


def book(db: Session, a: ContractApplication, p: Posting, status: str = "active") -> Engagement:
    """Create the engagement and block the dates. Shift's blocks are the source of truth."""
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

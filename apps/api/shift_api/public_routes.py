"""Public, non-personalized contract discovery. Never serialize private posting fields."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import or_, select

from .auth import Database
from .config import settings
from .market_models import Posting
from .models import Organization

router = APIRouter(prefix="/api/v1/public", tags=["public"])


class PublicContract(BaseModel):
    id: str
    title: str
    company: str
    trade: str
    city: str
    start_date: date
    end_date: date
    pay_rate_cents: int
    pay_unit: Literal["hour", "day", "fixed"]
    posting_type: Literal["individual", "agency"]


class PublicContracts(BaseModel):
    demo: bool
    contracts: list[PublicContract]


@router.get("/contracts", response_model=PublicContracts)
def contracts(
    db: Database,
    q: str = Query("", max_length=100),
    trade: str = Query("", max_length=60),
):
    query = (
        select(Posting, Organization.name)
        .join(Organization, Posting.org_id == Organization.id)
        .where(Posting.status == "open", Posting.end_date >= date.today())
    )
    if trade.strip():
        query = query.where(Posting.trade == trade.strip())
    if q.strip():
        # Escape wildcard characters so a visitor's search is literal text.
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                Posting.title.ilike(f"%{term}%", escape="\\"),
                Posting.trade.ilike(f"%{term}%", escape="\\"),
                Posting.city.ilike(f"%{term}%", escape="\\"),
                Organization.name.ilike(f"%{term}%", escape="\\"),
            )
        )
    rows = db.execute(query.order_by(Posting.start_date, Posting.id).limit(40))
    return PublicContracts(
        demo=settings.demo_mode,
        contracts=[
            PublicContract(
                id=posting.id,
                title=posting.title,
                company=company,
                trade=posting.trade,
                city=posting.city,
                start_date=posting.start_date,
                end_date=posting.end_date,
                pay_rate_cents=posting.pay_rate_cents,
                pay_unit=posting.pay_unit,
                posting_type=posting.posting_type,
            )
            for posting, company in rows
        ],
    )

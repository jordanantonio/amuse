"""Shift V1 marketplace tables: people, profiles and organization membership.

Workers here are independent people, unlike the org-scoped `workers` table used by
the crew planner. `users.membership_id` bridges a V1 account to that planner.
"""

from datetime import date, datetime
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Index,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from .models import identifier, utcnow


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    full_name: Mapped[str] = mapped_column(String(160))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # 'worker' | 'business' | 'agency'; null until the first onboarding step.
    default_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    membership_id: Mapped[str | None] = mapped_column(
        ForeignKey("memberships.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerProfile(Base):
    __tablename__ = "worker_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    handle: Mapped[str] = mapped_column(String(60), unique=True)
    headline: Mapped[str] = mapped_column(String(160), default="")
    trades: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str] = mapped_column(String(100), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    travel_radius_km: Mapped[int] = mapped_column(Integer, default=50)
    rate_min_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_max_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bio: Mapped[str] = mapped_column(String(1000), default="")
    linkedin_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    """Marketplace decisions (offers, acceptances, verification). Append-only."""

    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    target_table: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CredentialType(Base):
    """Catalog entry (data, not code): e.g. Fall Protection, COR, Class 1."""

    __tablename__ = "credential_types"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(40))
    default_issuer: Mapped[str] = mapped_column(String(160), default="")
    # 'worker' | 'org'
    applies_to: Mapped[str] = mapped_column(String(10), default="worker")
    has_expiry: Mapped[bool] = mapped_column(Boolean, default=True)


class Credential(Base):
    """One wallet item. Exactly one of owner_user_id / owner_org_id is set."""

    __tablename__ = "credentials"
    __table_args__ = (
        CheckConstraint("(owner_user_id IS NULL) != (owner_org_id IS NULL)"),
        CheckConstraint("status IN ('self_reported','pending','verified','rejected')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    owner_org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    credential_type_id: Mapped[str | None] = mapped_column(
        ForeignKey("credential_types.id"), nullable=True
    )
    custom_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    issuer: Mapped[str] = mapped_column(String(160), default="")
    number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    document_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    document_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Stored status; "expired" is computed from expires_on when read.
    status: Mapped[str] = mapped_column(String(20), default="self_reported")
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkHistory(Base):
    __tablename__ = "work_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(160))
    company: Mapped[str] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(100), default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String(1000), default="")
    reference_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reference_contact: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # Set when the entry was created from a completed Shift contract.
    engagement_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Posting(Base):
    """A contract a business posts: hire a person (individual) or a crew (agency)."""

    __tablename__ = "postings"
    __table_args__ = (
        CheckConstraint("end_date >= start_date"),
        CheckConstraint("posting_type IN ('individual','agency')"),
        CheckConstraint("status IN ('draft','open','filled','closed')"),
        CheckConstraint("pay_unit IN ('hour','day','fixed')"),
        CheckConstraint("pay_rate_cents > 0 AND headcount > 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    trade: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(3000), default="")
    posting_type: Mapped[str] = mapped_column(String(20), default="individual")
    city: Mapped[str] = mapped_column(String(100))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Hidden from applicants until they receive an offer.
    site_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    schedule_pattern: Mapped[str] = mapped_column(String(30), default="mon_fri")
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=True)
    pay_rate_cents: Mapped[int] = mapped_column(Integer)
    pay_unit: Mapped[str] = mapped_column(String(10), default="hour")
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(10), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PostingRequirement(Base):
    __tablename__ = "posting_requirements"
    posting_id: Mapped[str] = mapped_column(ForeignKey("postings.id"), primary_key=True)
    credential_type_id: Mapped[str] = mapped_column(
        ForeignKey("credential_types.id"), primary_key=True
    )
    # required=False means nice-to-have: improves ranking, never gates eligibility.
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    must_be_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class ContractApplication(Base):
    __tablename__ = "contract_applications"
    __table_args__ = (
        CheckConstraint("(applicant_user_id IS NULL) != (applicant_org_id IS NULL)"),
        CheckConstraint(
            "status IN ('applied','invited','shortlisted','offered','accepted',"
            "'declined','withdrawn','completed')"
        ),
        UniqueConstraint("posting_id", "applicant_user_id"),
        UniqueConstraint("posting_id", "applicant_org_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    posting_id: Mapped[str] = mapped_column(ForeignKey("postings.id"), index=True)
    applicant_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    applicant_org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    # 'applicant' | 'business'
    initiated_by: Mapped[str] = mapped_column(String(20), default="applicant")
    status: Mapped[str] = mapped_column(String(20), default="applied")
    note: Mapped[str] = mapped_column(String(1000), default="")
    proposed_rate_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crew_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Engagement(Base):
    """An accepted contract. Its availability blocks are the source of truth (FLOW-4)."""

    __tablename__ = "engagements"
    __table_args__ = (CheckConstraint("status IN ('active','completed','cancelled')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("contract_applications.id"), unique=True
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_exclusive: Mapped[bool] = mapped_column(Boolean)
    schedule_pattern: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="active")
    google_event_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AvailabilityBlock(Base):
    """Dates someone is unavailable: booked by an engagement or added by hand."""

    __tablename__ = "availability_blocks"
    __table_args__ = (
        CheckConstraint("end_date >= start_date"),
        CheckConstraint("source IN ('engagement','manual')"),
        CheckConstraint("(user_id IS NULL) != (org_id IS NULL)"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20))
    engagement_id: Mapped[str | None] = mapped_column(
        ForeignKey("engagements.id"), nullable=True, index=True
    )
    note: Mapped[str] = mapped_column(String(200), default="")


class ConnectedAccount(Base):
    """An external account linked after sign-in, e.g. Google Calendar (CONN-1).

    The refresh token is Fernet-encrypted with SHIFT_TOKEN_ENCRYPTION_KEY.
    """

    __tablename__ = "connected_accounts"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), primary_key=True)
    scopes: Mapped[str] = mapped_column(String(500), default="")
    refresh_token_encrypted: Mapped[str] = mapped_column(String(2000))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrewMember(Base):
    """A worker on a business's regular crew roster (crew planner pool)."""

    __tablename__ = "crew_members"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)


class WorkerHours(Base):
    """Weekly availability: minutes from midnight on `weekday` (0 = Monday).

    `end_minute` may pass 1440 for windows that run past midnight (nights).
    """

    __tablename__ = "worker_hours"
    __table_args__ = (CheckConstraint("end_minute > start_minute AND weekday BETWEEN 0 AND 6"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    start_minute: Mapped[int] = mapped_column(Integer)
    end_minute: Mapped[int] = mapped_column(Integer)


class CrewSlot(Base):
    """A shift the business needs filled, e.g. Packaging line 8 AM–12 PM, needs 2."""

    __tablename__ = "crew_slots"
    __table_args__ = (
        CheckConstraint("end_minute > start_minute AND needed > 0"),
        Index("ix_crew_slots_org_day", "org_id", "day"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    day: Mapped[date] = mapped_column(Date)
    start_minute: Mapped[int] = mapped_column(Integer)
    end_minute: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(120))
    needed: Mapped[int] = mapped_column(Integer, default=1)
    preferred_cert: Mapped[str | None] = mapped_column(
        ForeignKey("credential_types.id"), nullable=True
    )
    required_certs: Mapped[list] = mapped_column(JSON, default=list)


class CrewAssignment(Base):
    __tablename__ = "crew_assignments"
    __table_args__ = (
        UniqueConstraint("slot_id", "user_id"),
        CheckConstraint("status IN ('assigned','proposed')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    slot_id: Mapped[str] = mapped_column(ForeignKey("crew_slots.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    # 'proposed' = Auto-fill ghost avatar until the manager accepts it.
    status: Mapped[str] = mapped_column(String(20), default="assigned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrewRules(Base):
    """Fatigue and fairness advice settings (CREW-3). Advice only; never blocks."""

    __tablename__ = "crew_rules"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    max_consecutive_days: Mapped[int] = mapped_column(Integer, default=5)
    min_rest_hours: Mapped[int] = mapped_column(Integer, default=10)
    max_weekly_hours: Mapped[int] = mapped_column(Integer, default=40)


class OrgMember(Base):
    __tablename__ = "org_members"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    # 'owner' | 'manager' | 'crew'
    role: Mapped[str] = mapped_column(String(20), default="owner")

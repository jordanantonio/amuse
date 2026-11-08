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
    ForeignKey,
    Integer,
    String,
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


class OrgMember(Base):
    __tablename__ = "org_members"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    # 'owner' | 'manager' | 'crew'
    role: Mapped[str] = mapped_column(String(20), default="owner")

"""Pydantic contracts for Shift V1 routes (mirrored in apps/web/src/lib/market-types.ts)."""

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .catalog import CITIES, INDUSTRIES, TRADES

Mode = Literal["worker", "business", "agency"]


def check_trades(value):
    if value is not None and any(t not in TRADES for t in value):
        raise ValueError("Choose trades from the list")
    return value


def check_city(value):
    if value is not None and value not in CITIES:
        raise ValueError("Choose a city from the list")
    return value


def check_industry(value):
    if value is not None and value not in INDUSTRIES:
        raise ValueError("Choose an industry from the list")
    return value


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    avatar_url: str | None
    is_admin: bool


class WorkerProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    handle: str
    headline: str
    trades: list[str]
    city: str
    travel_radius_km: int
    rate_min_cents: int | None
    rate_max_cents: int | None
    bio: str
    linkedin_url: str | None
    is_public: bool


class OrgView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    handle: str | None
    industry: str | None
    city: str | None
    website: str | None
    about: str | None
    verification_status: str


class MeView(BaseModel):
    user: UserView
    mode: Mode | None
    onboarded: bool
    worker_profile: WorkerProfileView | None
    organization: OrgView | None
    planner_persona: str | None
    calendar_connected: bool = False


class DemoAccount(BaseModel):
    id: str
    full_name: str
    email: str
    mode: Mode | None
    label: str


class DemoSignIn(BaseModel):
    user_id: str | None = None
    full_name: str | None = Field(None, min_length=1, max_length=160)
    email: str | None = Field(None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OnboardingInput(BaseModel):
    role: Mode | None = None
    full_name: str | None = Field(None, min_length=1, max_length=160)
    headline: str | None = Field(None, max_length=160)
    org_name: str | None = Field(None, min_length=1, max_length=160)
    trades: list[str] | None = Field(None, max_length=12)
    industry: str | None = None
    city: str | None = None
    travel_radius_km: int | None = Field(None, ge=5, le=1000)
    finish: bool = False

    _trades = field_validator("trades")(classmethod(lambda cls, v: check_trades(v)))
    _city = field_validator("city")(classmethod(lambda cls, v: check_city(v)))
    _industry = field_validator("industry")(classmethod(lambda cls, v: check_industry(v)))


class CredentialTypeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    category: str
    default_issuer: str
    applies_to: str
    has_expiry: bool


CredentialStatus = Literal["self_reported", "pending", "verified", "expired", "rejected"]


class CredentialView(BaseModel):
    id: str
    credential_type_id: str | None
    name: str
    category: str
    issuer: str
    number: str | None
    issued_on: date | None
    expires_on: date | None
    status: CredentialStatus
    expiring_soon: bool
    days_to_expiry: int | None
    has_document: bool
    document_name: str | None
    rejection_reason: str | None


class CredentialInput(BaseModel):
    credential_type_id: str | None = None
    custom_name: str | None = Field(None, max_length=160)
    issuer: str = Field("", max_length=160)
    number: str | None = Field(None, max_length=80)
    issued_on: date | None = None
    expires_on: date | None = None
    scope: Literal["me", "org"] = "me"

    @model_validator(mode="after")
    def coherent(self):
        if not self.credential_type_id and not (self.custom_name or "").strip():
            raise ValueError("Choose a credential type or name it under Other")
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError("The expiry date must be after the issue date")
        return self


class DocumentUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    content_type: Literal["application/pdf", "image/jpeg", "image/png", "image/webp"]
    # Base64 file body; the decoded size is limited server-side.
    data_base64: str = Field(min_length=4, max_length=7_200_000)


class WorkHistoryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    company: str
    city: str
    start_date: date
    end_date: date | None
    description: str
    reference_name: str | None
    reference_contact: str | None
    engagement_id: str | None


class WorkHistoryInput(BaseModel):
    role: str = Field(min_length=1, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    city: str = Field("", max_length=100)
    start_date: date
    end_date: date | None = None
    description: str = Field("", max_length=1000)
    reference_name: str | None = Field(None, max_length=160)
    reference_contact: str | None = Field(None, max_length=160)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("The end date must be after the start date")
        return self


class ProfileInput(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=160)
    headline: str | None = Field(None, max_length=160)
    trades: list[str] | None = Field(None, max_length=12)
    city: str | None = None
    travel_radius_km: int | None = Field(None, ge=5, le=1000)
    rate_min_cents: int | None = Field(None, ge=0, le=100_000)
    rate_max_cents: int | None = Field(None, ge=0, le=100_000)
    bio: str | None = Field(None, max_length=1000)
    linkedin_url: str | None = Field(None, max_length=300, pattern=r"^(https://[^\s]+)?$")
    is_public: bool | None = None

    _trades = field_validator("trades")(classmethod(lambda cls, v: check_trades(v)))
    _city = field_validator("city")(classmethod(lambda cls, v: check_city(v)))

    @model_validator(mode="after")
    def rate_order(self):
        if (
            self.rate_min_cents is not None
            and self.rate_max_cents is not None
            and self.rate_max_cents < self.rate_min_cents
        ):
            raise ValueError("The maximum rate must be at least the minimum")
        return self


class OrgInput(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)
    industry: str | None = None
    city: str | None = None
    website: str | None = Field(None, max_length=300, pattern=r"^(https?://[^\s]+)?$")
    about: str | None = Field(None, max_length=1000)

    _industry = field_validator("industry")(classmethod(lambda cls, v: check_industry(v)))
    _city = field_validator("city")(classmethod(lambda cls, v: check_city(v)))


class CompletenessStep(BaseModel):
    key: str
    label: str
    done: bool


class NextStep(BaseModel):
    key: str
    label: str
    credential_type_id: str | None = None


class Completeness(BaseModel):
    percent: int
    steps: list[CompletenessStep]
    next_step: NextStep | None


class ProfileView(BaseModel):
    user: UserView
    profile: WorkerProfileView
    credentials: list[CredentialView]
    history: list[WorkHistoryView]
    completeness: Completeness


class OrgProfileView(BaseModel):
    organization: OrgView
    credentials: list[CredentialView]


class NotificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    payload: dict
    read_at: datetime | None
    created_at: datetime


class NotificationsView(BaseModel):
    unread: int
    work_badge: int
    items: list[NotificationView]


class City(BaseModel):
    name: str
    lat: float
    lng: float


class Meta(BaseModel):
    trades: list[str]
    industries: list[str]
    cities: list[City]
    schedule_patterns: dict[str, str]

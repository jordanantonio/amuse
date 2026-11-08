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


def check_trade(value):
    if value not in TRADES:
        raise ValueError("Choose a trade from the list")
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


PostingType = Literal["individual", "agency"]
PayUnit = Literal["hour", "day", "fixed"]
Pattern = Literal["mon_fri", "nights", "four_on_four_off", "weekends"]


class RequirementInput(BaseModel):
    credential_type_id: str
    required: bool = True
    must_be_verified: bool = False


class PostingInput(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    trade: str
    description: str = Field("", max_length=3000)
    posting_type: PostingType = "individual"
    city: str
    site_address: str | None = Field(None, max_length=300)
    start_date: date
    end_date: date
    schedule_pattern: Pattern = "mon_fri"
    is_exclusive: bool = True
    pay_rate_cents: int = Field(gt=0, le=10_000_000)
    pay_unit: PayUnit = "hour"
    headcount: int = Field(1, ge=1, le=200)
    requirements: list[RequirementInput] = Field(default_factory=list, max_length=20)
    status: Literal["draft", "open"] = "open"

    _trade = field_validator("trade")(classmethod(lambda cls, v: check_trade(v)))
    _city = field_validator("city")(classmethod(lambda cls, v: check_city(v)))

    @model_validator(mode="after")
    def dates(self):
        if self.end_date < self.start_date:
            raise ValueError("The end date must be on or after the start date")
        ids = [r.credential_type_id for r in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("Each credential can be listed once")
        return self


class OrgRef(BaseModel):
    id: str
    name: str
    kind: str
    verified: bool


class MatchItem(BaseModel):
    credential_type_id: str
    name: str
    required: bool
    must_be_verified: bool
    state: Literal["ok", "pending", "missing"]


class Match(BaseModel):
    required_total: int
    required_held: int
    items: list[MatchItem]


class ScorePart(BaseModel):
    label: str
    points: int


class PostingCard(BaseModel):
    id: str
    title: str
    trade: str
    posting_type: PostingType
    org: OrgRef
    city: str
    start_date: date
    end_date: date
    schedule_pattern: str
    is_exclusive: bool
    pay_rate_cents: int
    pay_unit: PayUnit
    headcount: int
    status: str
    created_at: datetime
    match: Match
    eligible: bool
    reasons: list[str]
    distance_km: int | None = None
    score: int | None = None
    score_breakdown: list[ScorePart] = []
    is_new: bool = False
    site_address: str | None = None
    description: str | None = None
    applicants: int | None = None
    new_applicants: int | None = None
    offers_out: int | None = None
    hired: int | None = None


class FeedView(BaseModel):
    items: list[PostingCard]
    new_count: int


class ApplicantSummary(BaseModel):
    kind: Literal["worker", "agency"]
    id: str
    name: str
    headline: str
    city: str
    distance_km: int | None = None
    verified: bool | None = None


class EngagementSummary(BaseModel):
    id: str
    start_date: date
    end_date: date
    is_exclusive: bool
    schedule_pattern: str
    status: str
    calendar_synced: bool


class ApplicationView(BaseModel):
    id: str
    status: str
    note: str
    proposed_rate_cents: int | None
    crew_size: int | None
    initiated_by: str
    created_at: datetime
    updated_at: datetime
    applicant: ApplicantSummary
    posting: PostingCard
    engagement: EngagementSummary | None


class PostingDetail(BaseModel):
    posting: PostingCard
    description: str
    is_owner: bool
    my_application: ApplicationView | None


class ApplyInput(BaseModel):
    note: str = Field("", max_length=1000)
    proposed_rate_cents: int | None = Field(None, gt=0, le=10_000_000)
    crew_size: int | None = Field(None, ge=1, le=500)


class ActionInput(BaseModel):
    action: Literal["shortlist", "offer", "decline", "withdraw_offer", "decline_offer", "withdraw"]


class WorkView(BaseModel):
    applied: list[ApplicationView]
    offers: list[ApplicationView]
    active: list[ApplicationView]
    past: list[ApplicationView]


class OrgEngagementItem(BaseModel):
    engagement: EngagementSummary
    application_id: str
    posting_id: str
    posting_title: str
    applicant: ApplicantSummary


class OrgWorkView(BaseModel):
    postings: list[PostingCard]
    active: list[OrgEngagementItem]
    past: list[OrgEngagementItem]


class NewApplicant(BaseModel):
    application_id: str
    posting_id: str
    posting_title: str
    name: str
    created_at: datetime


class NextShift(BaseModel):
    application_id: str
    posting_title: str
    org_name: str
    start_date: date
    end_date: date
    city: str


class HomeView(BaseModel):
    next_shift: NextShift | None = None
    offers: list[ApplicationView] = []
    expiring: list[CredentialView] = []
    new_applicants: list[NewApplicant] = []
    offers_awaiting: int = 0
    open_postings: int = 0
    active_contracts: int = 0


class TalentCard(BaseModel):
    id: str
    name: str
    headline: str
    trades: list[str]
    city: str
    distance_km: int | None
    verified_tickets: int
    tickets: int


class AcceptInput(BaseModel):
    withdraw_ids: list[str] = Field(default_factory=list, max_length=50)


class ConflictItem(BaseModel):
    engagement_id: str
    title: str
    message: str


class ManualOverlap(BaseModel):
    id: str
    start_date: date
    end_date: date
    note: str


class AcceptPreview(BaseModel):
    is_exclusive: bool
    conflicts: list[ConflictItem]
    ticket_problems: list[str]
    overlapping: list[ApplicationView]
    manual_overlaps: list[ManualOverlap]


class CalendarResult(BaseModel):
    status: Literal["added", "needs_auth", "unavailable"]
    url: str | None = None
    count: int | None = None
    message: str | None = None


class ScheduleItem(BaseModel):
    id: str
    kind: Literal["engagement", "manual"]
    start_date: date
    end_date: date
    title: str
    subtitle: str
    posting_id: str | None = None
    engagement_id: str | None = None
    status: str | None = None


class ScheduleView(BaseModel):
    items: list[ScheduleItem]
    calendar_enabled: bool
    calendar_connected: bool


class BlockInput(BaseModel):
    start_date: date
    end_date: date
    note: str = Field("", max_length=200)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_date < self.start_date:
            raise ValueError("The end date must be on or after the start date")
        return self


class City(BaseModel):
    name: str
    lat: float
    lng: float


class Meta(BaseModel):
    trades: list[str]
    industries: list[str]
    cities: list[City]
    schedule_patterns: dict[str, str]

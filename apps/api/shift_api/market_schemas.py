"""Pydantic contracts for Shift V1 routes (mirrored in apps/web/src/lib/market-types.ts)."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .catalog import CITIES, INDUSTRIES, TRADES

Mode = Literal["worker", "business", "agency"]


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

    @field_validator("trades")
    @classmethod
    def known_trades(cls, value):
        if value is not None and any(t not in TRADES for t in value):
            raise ValueError("Choose trades from the list")
        return value

    @field_validator("city")
    @classmethod
    def known_city(cls, value):
        if value is not None and value not in CITIES:
            raise ValueError("Choose a city from the list")
        return value

    @field_validator("industry")
    @classmethod
    def known_industry(cls, value):
        if value is not None and value not in INDUSTRIES:
            raise ValueError("Choose an industry from the list")
        return value


class City(BaseModel):
    name: str
    lat: float
    lng: float


class Meta(BaseModel):
    trades: list[str]
    industries: list[str]
    cities: list[City]
    schedule_patterns: dict[str, str]

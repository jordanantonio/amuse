from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimeWindow(Input):
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def interval(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("End must be after start")
        return self


class AbsenceInput(TimeWindow):
    pass


class DecisionInput(Input):
    decision: Literal["approve", "reject", "request_revision"]
    comment: str = Field(default="", max_length=2000)


class ConfirmationInput(Input):
    decision: Literal["accept", "decline"]


class ProposalInput(Input):
    objectives: list[Literal["lowest_cost", "earliest_completion", "fewest_changes"]] = Field(
        default=["lowest_cost", "earliest_completion", "fewest_changes"], min_length=1, max_length=3
    )


class CertificateInput(Input):
    name: str = Field(min_length=1, max_length=100)
    expires_at: AwareDatetime


class ProfileInput(Input):
    title: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=100)
    hourly_rate_cents: int = Field(ge=0, le=100000)
    skills: list[str] = Field(max_length=40)
    certifications: list[CertificateInput] = Field(max_length=40)
    work_modes: list[Literal["on_site", "hybrid", "remote"]] = Field(min_length=1, max_length=3)


class AvailabilityInput(Input):
    windows: list[TimeWindow] = Field(max_length=200)


class TaskInput(Input):
    name: str = Field(min_length=1, max_length=160)
    duration_hours: int = Field(ge=1, le=16)
    crew_size: int = Field(default=1, ge=1, le=30)
    required_skills: list[str] = Field(default=[], max_length=30)
    required_certifications: list[str] = Field(default=[], max_length=30)
    work_mode: Literal["on_site", "hybrid", "remote"] = "on_site"
    predecessor_ids: list[str] = Field(default=[], max_length=30)


class ProjectInput(TimeWindow):
    name: str = Field(min_length=1, max_length=160)
    client: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1, le=100)
    budget_cents: int | None = Field(default=None, ge=0, le=100000000)

    @model_validator(mode="after")
    def planning_horizon(self):
        if self.ends_at - self.starts_at > timedelta(days=14):
            raise ValueError("Project planning horizon must not exceed 14 days")
        if any(
            v.minute not in (0, 30) or v.second or v.microsecond
            for v in (self.starts_at, self.ends_at)
        ):
            raise ValueError("Project boundaries must align to half-hour slots")
        return self


class JobInput(Input):
    project_id: str
    title: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=100)
    work_mode: Literal["on_site", "hybrid", "remote"] = "on_site"
    skills: list[str] = Field(default=[], max_length=30)
    rate_min_cents: int = Field(ge=0, le=100000)
    rate_max_cents: int = Field(ge=0, le=100000)

    @model_validator(mode="after")
    def rates(self):
        if self.rate_max_cents < self.rate_min_cents:
            raise ValueError("Maximum rate must not be below minimum")
        return self


class PolicyInput(Input):
    task_buffer_percent: int = Field(default=0, ge=0, le=50)
    transition_minutes: int = Field(default=0, ge=0, le=120, multiple_of=30)
    contingency_minutes: int = Field(default=0, ge=0, le=2880, multiple_of=30)
    freeze_hours: int = Field(default=48, ge=0, le=168)
    day_start_hour: int = Field(default=8, ge=0, le=23)
    day_end_hour: int = Field(default=17, ge=1, le=24)
    minimum_rest_hours: int = Field(default=11, ge=0, le=24)
    max_daily_hours: int = Field(default=9, ge=1, le=16)
    timezone: str = "America/Edmonton"
    task_weather_rules: dict[str, dict[str, int]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_policy(self):
        try:
            ZoneInfo(self.timezone)
        except Exception:
            raise ValueError("Unknown IANA time zone")
        if self.day_end_hour <= self.day_start_hour:
            raise ValueError("Workday must have positive duration")
        allowed = {
            "max_rain_probability",
            "max_precipitation_mm",
            "max_wind_kph",
            "min_temperature_c",
            "max_temperature_c",
        }
        if any(set(rules) - allowed for rules in self.task_weather_rules.values()):
            raise ValueError("Unknown weather threshold")
        if any(
            not -100 <= n <= 500 for rule in self.task_weather_rules.values() for n in rule.values()
        ):
            raise ValueError("Weather threshold out of range")
        return self


class ForecastInput(Input):
    adverse: bool = False


class JobStateInput(Input):
    status: Literal["open", "closed"]


class InviteInput(Input):
    task_id: str

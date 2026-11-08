from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator


class DTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="after")
    @classmethod
    def normalize_database_time(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Persona(DTO):
    id: str
    name: str
    role: Literal["worker", "manager", "admin"]


class Window(DTO):
    starts_at: datetime
    ends_at: datetime


class Certificate(DTO):
    name: str
    expires_at: datetime


class WorkerView(DTO):
    id: str
    name: str
    title: str
    location: str
    hourly_rate_cents: int
    employment_type: str
    work_modes: list[str]
    color: str
    skills: list[str]
    certifications: list[Certificate]
    availability: list[Window]
    busy: list[Window]


class TaskView(DTO):
    id: str
    project_id: str
    name: str
    duration_hours: int
    crew_size: int
    required_skills: list[str]
    required_certifications: list[str]
    work_mode: str
    confirmed_count: int
    predecessor_ids: list[str] = []


class ProjectView(DTO):
    id: str
    name: str
    client: str
    starts_at: datetime
    deadline: datetime
    budget_cents: int | None
    color: str
    location: str
    capacity: int
    tasks: list[TaskView]


class AssignmentView(DTO):
    id: str
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    worker_id: str
    worker_name: str
    starts_at: datetime
    ends_at: datetime
    status: Literal["confirmed", "completed", "cancelled", "disrupted"]
    color: str


class JobView(DTO):
    id: str
    title: str
    project_id: str
    location: str
    work_mode: str
    skills: list[str]
    rate_min_cents: int
    rate_max_cents: int
    status: str


class Dashboard(BaseModel):
    organization: str
    persona: Persona
    demo: bool
    week_start: str
    timezone: str
    workers: list[WorkerView]
    projects: list[ProjectView]
    assignments: list[AssignmentView]
    jobs: list[JobView]
    staffing_gaps: int


class Proposal(BaseModel):
    task_id: str
    task_name: str
    worker_id: str
    worker_name: str
    starts_at: datetime
    ends_at: datetime
    cost_cents: int
    state: Literal["proposed"] = "proposed"


class DraftView(DTO):
    id: str
    project_id: str
    created_at: datetime
    input_fingerprint: str
    status: str
    solver_status: str
    proposals: list[Proposal]
    blockers: list[str]
    cost_cents: int | None


class ConfirmationView(DTO):
    id: str
    worker_id: str
    worker_name: str
    status: str


class ApprovalView(DTO):
    decision: str
    actor: str
    comment: str
    created_at: datetime


class ScheduleSlot(DTO):
    id: str | None = None
    task_id: str
    task_name: str
    worker_id: str
    worker_name: str
    starts_at: datetime
    ends_at: datetime
    cost_cents: int
    state: str | None = None


class RecoveryView(DTO):
    id: str
    project_id: str
    project_name: str
    objective: Literal["lowest_cost", "earliest_completion", "fewest_changes"]
    status: str
    reason: str
    created_at: datetime
    expires_at: datetime
    published_at: datetime | None
    stale: bool
    original_schedule: list[ScheduleSlot]
    proposed_schedule: list[ScheduleSlot]
    replaces_assignment_ids: list[str]
    metrics: dict[str, int | str]
    confirmations: list[ConfirmationView]
    history: list[ApprovalView]


class BlockedPlan(DTO):
    solver_status: str
    blockers: list[str]
    objective: str


class ForecastView(Window):
    id: str
    rain_probability: int
    precipitation_mm: int
    wind_kph: int
    temperature_c: int
    source: str
    simulated: bool
    fetched_at: datetime

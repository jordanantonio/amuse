from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    Integer,
    JSON,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def identifier():
    return str(uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    name: Mapped[str] = mapped_column(String(160))


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint("role IN ('worker','manager','admin')"),
        UniqueConstraint("organization_id", "auth_subject"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    auth_subject: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(20))


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = (
        CheckConstraint("hourly_rate_cents >= 0"),
        CheckConstraint("employment_type IN ('employee','contractor')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    membership_id: Mapped[str] = mapped_column(ForeignKey("memberships.id"), unique=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(100))
    hourly_rate_cents: Mapped[int] = mapped_column(Integer)
    employment_type: Mapped[str] = mapped_column(String(20))
    work_modes: Mapped[list] = mapped_column(JSON, default=list)
    color: Mapped[str] = mapped_column(String(20), default="#9d95e7")


class Skill(Base):
    __tablename__ = "worker_skills"
    __table_args__ = (UniqueConstraint("worker_id", "name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))


class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = (UniqueConstraint("worker_id", "name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AvailabilityWindow(Base):
    __tablename__ = "availability_windows"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at"),
        Index("ix_availability_worker_time", "worker_id", "starts_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PrivateCommitment(Base):
    __tablename__ = "private_commitments"
    __table_args__ = (CheckConstraint("ends_at > starts_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    private_label: Mapped[str] = mapped_column(String(200))


class Worksite(Base):
    __tablename__ = "worksites"
    __table_args__ = (CheckConstraint("capacity > 0"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("deadline > starts_at"),
        CheckConstraint("budget_cents IS NULL OR budget_cents >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    manager_id: Mapped[str] = mapped_column(ForeignKey("memberships.id"))
    worksite_id: Mapped[str] = mapped_column(ForeignKey("worksites.id"))
    name: Mapped[str] = mapped_column(String(160))
    client: Mapped[str] = mapped_column(String(160))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    budget_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str] = mapped_column(String(20))


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("duration_hours > 0"),
        CheckConstraint("crew_size > 0"),
        CheckConstraint("work_mode IN ('on_site','hybrid','remote')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    duration_hours: Mapped[int] = mapped_column(Integer)
    crew_size: Mapped[int] = mapped_column(Integer, default=1)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    required_certifications: Mapped[list] = mapped_column(JSON, default=list)
    work_mode: Mapped[str] = mapped_column(String(20), default="on_site")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (CheckConstraint("task_id != predecessor_id"),)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), primary_key=True)
    predecessor_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), primary_key=True)


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at"),
        CheckConstraint("status IN ('confirmed','completed','cancelled','disrupted')"),
        Index("ix_assignment_worker_time", "worker_id", "starts_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="confirmed")


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        CheckConstraint("rate_max_cents >= rate_min_cents AND rate_min_cents >= 0"),
        CheckConstraint("status IN ('open','closed')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(100))
    work_mode: Mapped[str] = mapped_column(String(20))
    skills: Mapped[list] = mapped_column(JSON)
    rate_min_cents: Mapped[int] = mapped_column(Integer)
    rate_max_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="open")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "worker_id"),
        CheckConstraint("status IN ('applied','reviewing','withdrawn','rejected')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    job_id: Mapped[str] = mapped_column(ForeignKey("job_postings.id"))
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"))
    status: Mapped[str] = mapped_column(String(20), default="applied")


class ScheduleDraft(Base):
    __tablename__ = "schedule_drafts"
    __table_args__ = (CheckConstraint("status IN ('draft','approved','rejected')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("memberships.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    solver_status: Mapped[str] = mapped_column(String(30))
    proposals: Mapped[list] = mapped_column(JSON, default=list)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (CheckConstraint("status IN ('pending','accepted','declined','expired')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    draft_id: Mapped[str] = mapped_column(ForeignKey("schedule_drafts.id"))
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("memberships.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkerAbsence(Base):
    __tablename__ = "worker_absences"
    __table_args__ = (CheckConstraint("ends_at > starts_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[str] = mapped_column(ForeignKey("memberships.id"))

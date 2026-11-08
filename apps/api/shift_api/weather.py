"""Replaceable forecast provider and task-specific, deterministic risk rules."""

from datetime import timedelta
from zoneinfo import ZoneInfo
from typing import Protocol
from sqlalchemy import select, delete
from .models import (
    WeatherForecast,
    SchedulingPolicy,
    Project,
    Task,
    Assignment,
    SchedulingEvent,
    RiskReview,
)
from .solver_time import utc, overlap


class WeatherProvider(Protocol):
    def forecast(self, project: Project, adverse: bool) -> list[dict]: ...


class SimulatedWeatherProvider:
    def __init__(self, zone="America/Edmonton"):
        self.zone = ZoneInfo(zone)

    def forecast(self, project, adverse=False):
        start = (
            utc(project.starts_at)
            .astimezone(self.zone)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        return [
            dict(
                starts_at=utc(start + timedelta(days=i)),
                ends_at=utc(start + timedelta(days=i + 1)),
                rain_probability=95 if adverse and i < 2 else 15,
                precipitation_mm=22 if adverse and i < 2 else 0,
                wind_kph=24 if adverse and i < 2 else 12,
                temperature_c=7,
                source="SHIFT deterministic simulated weather v1",
                simulated=True,
            )
            for i in range(14)
        ]


def refresh_forecast(db, project, adverse=False, provider: WeatherProvider | None = None):
    policy = db.get(SchedulingPolicy, project.id)
    values = (
        provider or SimulatedWeatherProvider(policy.timezone if policy else "America/Edmonton")
    ).forecast(project, adverse)
    old = list(db.scalars(select(WeatherForecast).where(WeatherForecast.project_id == project.id)))

    def signature(rows):
        return sorted(
            (
                utc(r.starts_at).isoformat(),
                r.rain_probability,
                r.precipitation_mm,
                r.wind_kph,
                r.temperature_c,
            )
            for r in rows
        )

    incoming = [WeatherForecast(project_id=project.id, **v) for v in values]
    if signature(old) == signature(incoming):
        return False
    db.execute(delete(WeatherForecast).where(WeatherForecast.project_id == project.id))
    db.add_all(incoming)
    db.add(
        SchedulingEvent(
            project_id=project.id,
            kind="weather_changed",
            description="Simulated forecast materially changed; review weather-sensitive work.",
        )
    )
    db.flush()
    return True


def weather_blockers(db, project, task, start, end):
    policy = db.get(SchedulingPolicy, project.id)
    rule = (policy.task_weather_rules or {}).get(task.id) if policy else None
    if not rule:
        return []
    reasons = []
    for f in db.scalars(select(WeatherForecast).where(WeatherForecast.project_id == project.id)):
        if not overlap(start, end, f.starts_at, f.ends_at):
            continue
        checks = [
            ("max_rain_probability", f.rain_probability, "rain probability"),
            ("max_precipitation_mm", f.precipitation_mm, "precipitation"),
            ("max_wind_kph", f.wind_kph, "wind"),
            ("max_temperature_c", f.temperature_c, "temperature"),
        ]
        reasons.extend(
            f"{label} {value} exceeds task threshold {rule[key]}"
            for key, value, label in checks
            if key in rule and value > rule[key]
        )
        if "min_temperature_c" in rule and f.temperature_c < rule["min_temperature_c"]:
            reasons.append("Temperature below this task’s configured minimum")
    return reasons


def review(db, project):
    from .models import WorkerAbsence, Worker, Certification, SlotReservation

    policy = db.get(SchedulingPolicy, project.id)
    risks = []
    tasks = list(db.scalars(select(Task).where(Task.project_id == project.id)))
    for task in tasks:
        confirmed = list(
            db.scalars(
                select(Assignment).where(
                    Assignment.task_id == task.id, Assignment.status == "confirmed"
                )
            )
        )
        if len(confirmed) < task.crew_size:
            risks.append(
                dict(
                    task_id=task.id,
                    task_name=task.name,
                    kind="staffing_gap",
                    reason=f"{task.crew_size - len(confirmed)} worker(s) unassigned",
                    assignment_ids=[],
                )
            )
        for a in confirmed:
            reasons = weather_blockers(db, project, task, a.starts_at, a.ends_at)
            if reasons:
                risks.append(
                    dict(
                        task_id=task.id,
                        task_name=task.name,
                        kind="weather",
                        reason="; ".join(sorted(set(reasons))),
                        assignment_ids=[a.id],
                    )
                )
            absences = [
                b
                for b in db.scalars(
                    select(WorkerAbsence).where(WorkerAbsence.worker_id == a.worker_id)
                )
                if overlap(a.starts_at, a.ends_at, b.starts_at, b.ends_at)
            ]
            if absences:
                risks.append(
                    dict(
                        task_id=task.id,
                        task_name=task.name,
                        kind="absence",
                        reason="Confirmed assignment overlaps recorded worker unavailability",
                        assignment_ids=[a.id],
                    )
                )
    output = dict(
        project_id=project.id,
        risks=risks,
        horizon_days=14,
        forecast_source="Simulated; not a live forecast",
        contingency_minutes=policy.contingency_minutes if policy else 0,
        assumptions=[
            "Manual review; no background scheduler is configured.",
            "Thresholds are project/task examples, not universal safety standards.",
            "Frozen assignments remain protected unless their disruption is explicitly included in the reviewed proposal.",
        ],
    )
    db.add(RiskReview(project_id=project.id, report=output))
    db.flush()
    return output

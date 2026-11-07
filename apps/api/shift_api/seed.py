"""Fictional fixture, fixed week in America/Edmonton; never a production seed."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .models import *
from .database import Base

ZONE = ZoneInfo("America/Edmonton")


def at(day: int, hour: int):
    return datetime(2026, 11, day, hour, tzinfo=ZONE).astimezone(timezone.utc)


def seed(db: Session):
    if db.scalar(select(Organization.id).limit(1)):
        seed_adaptive(db)
        return
    db.add(Organization(id="northline", name="Northline Works"))
    db.flush()
    db.add_all(
        [
            Membership(
                id="demo-manager",
                organization_id="northline",
                auth_subject="demo:manager",
                name="Alex Morgan",
                role="manager",
            ),
            Membership(
                id="demo-admin",
                organization_id="northline",
                auth_subject="demo:admin",
                name="Taylor Chen",
                role="admin",
            ),
        ]
    )
    db.flush()
    people = [
        (
            "maya",
            "Maya Brooks",
            "Journeyperson electrician",
            6800,
            "employee",
            ["Electrical", "Blueprint reading"],
            ["Red Seal Electrical"],
            "#a79af0",
        ),
        (
            "noah",
            "Noah Williams",
            "Structural welder",
            6200,
            "employee",
            ["Welding", "Fabrication"],
            ["CWB Welding"],
            "#75b6a1",
        ),
        (
            "ella",
            "Ella Thompson",
            "Project engineer",
            7500,
            "employee",
            ["Engineering", "Blueprint reading"],
            ["P.Eng."],
            "#8cafe7",
        ),
        (
            "liam",
            "Liam Patel",
            "Equipment operator",
            5400,
            "employee",
            ["Equipment operation"],
            ["Heavy Equipment"],
            "#d9ac6d",
        ),
        (
            "sofia",
            "Sofia Rivera",
            "Electrical contractor",
            7200,
            "contractor",
            ["Electrical", "Blueprint reading"],
            ["Red Seal Electrical"],
            "#c68f9f",
        ),
        (
            "ethan",
            "Ethan Park",
            "Electrical contractor",
            7900,
            "contractor",
            ["Electrical"],
            ["Red Seal Electrical"],
            "#7abac4",
        ),
        (
            "ava",
            "Ava Wilson",
            "Fabrication specialist",
            6500,
            "contractor",
            ["Welding", "Fabrication"],
            ["CWB Welding"],
            "#c6b673",
        ),
        (
            "oliver",
            "Oliver James",
            "Mechanical engineer",
            7800,
            "contractor",
            ["Engineering"],
            ["P.Eng."],
            "#999fd7",
        ),
    ]
    for wid, name, title, rate, employment, skills, certs, color in people:
        mid = "demo-" + wid
        db.add(
            Membership(
                id=mid,
                organization_id="northline",
                auth_subject="demo:" + wid,
                name=name,
                role="worker",
            )
        )
        db.flush()
        db.add(
            Worker(
                id=wid,
                membership_id=mid,
                organization_id="northline",
                name=name,
                title=title,
                location="Edmonton, AB",
                hourly_rate_cents=rate,
                employment_type=employment,
                work_modes=["on_site", "hybrid", "remote"],
                color=color,
            )
        )
        db.flush()
        db.add_all([Skill(worker_id=wid, name=s) for s in skills])
        db.add_all([Certification(worker_id=wid, name=c, expires_at=at(30, 17)) for c in certs])
        db.add_all(
            [
                AvailabilityWindow(worker_id=wid, starts_at=at(d, 8), ends_at=at(d, 17))
                for d in range(9, 14)
            ]
        )
    db.add(
        PrivateCommitment(
            worker_id="sofia",
            starts_at=at(9, 8),
            ends_at=at(9, 12),
            private_label="PRIVATE: health appointment — never expose to managers",
        )
    )
    db.add(
        PrivateCommitment(
            worker_id="ethan",
            starts_at=at(10, 8),
            ends_at=at(10, 17),
            private_label="PRIVATE: another client contract",
        )
    )
    db.add_all(
        [
            Worksite(
                id="fabrication-site",
                organization_id="northline",
                name="Eastside fabrication facility",
                location="Edmonton, AB",
                capacity=4,
            ),
            Worksite(
                id="river-site",
                organization_id="northline",
                name="River District",
                location="Edmonton, AB",
                capacity=3,
            ),
            Worksite(
                id="studio-site",
                organization_id="northline",
                name="Northline Studio",
                location="Edmonton, AB",
                capacity=2,
            ),
        ]
    )
    db.flush()
    db.add_all(
        [
            Project(
                id="eastside",
                organization_id="northline",
                manager_id="demo-manager",
                worksite_id="fabrication-site",
                name="Eastside facility fit-out",
                client="Eastside Manufacturing",
                starts_at=at(9, 8),
                deadline=at(13, 17),
                budget_cents=200000,
                color="#a79af0",
            ),
            Project(
                id="river",
                organization_id="northline",
                manager_id="demo-manager",
                worksite_id="river-site",
                name="River District expansion",
                client="River District Construction",
                starts_at=at(9, 8),
                deadline=at(13, 17),
                budget_cents=300000,
                color="#75b6a1",
            ),
            Project(
                id="design",
                organization_id="northline",
                manager_id="demo-manager",
                worksite_id="studio-site",
                name="Northworks design review",
                client="Northworks",
                starts_at=at(9, 8),
                deadline=at(13, 17),
                budget_cents=120000,
                color="#8cafe7",
            ),
        ]
    )
    db.flush()
    tasks = [
        (
            "rough-in",
            "eastside",
            "Electrical rough-in",
            4,
            ["Electrical"],
            ["Red Seal Electrical"],
            "on_site",
        ),
        ("fabricate", "eastside", "Frame fabrication", 4, ["Welding"], ["CWB Welding"], "on_site"),
        ("inspection", "eastside", "Systems inspection", 3, ["Engineering"], ["P.Eng."], "hybrid"),
        (
            "site-prep",
            "river",
            "Site preparation",
            6,
            ["Equipment operation"],
            ["Heavy Equipment"],
            "on_site",
        ),
        ("river-weld", "river", "Structural welding", 4, ["Welding"], ["CWB Welding"], "on_site"),
        ("review", "design", "Design coordination", 3, ["Engineering"], ["P.Eng."], "remote"),
    ]
    for tid, pid, name, dur, skills, certs, mode in tasks:
        db.add(
            Task(
                id=tid,
                project_id=pid,
                name=name,
                duration_hours=dur,
                crew_size=1,
                required_skills=skills,
                required_certifications=certs,
                work_mode=mode,
            )
        )
    db.flush()
    db.add_all(
        [
            TaskDependency(task_id="inspection", predecessor_id="rough-in"),
            TaskDependency(task_id="inspection", predecessor_id="fabricate"),
        ]
    )
    for aid, tid, wid, day, start, end in [
        ("assignment-maya", "rough-in", "maya", 9, 8, 12),
        ("assignment-noah", "fabricate", "noah", 9, 8, 12),
        ("assignment-liam", "site-prep", "liam", 9, 8, 14),
        ("assignment-river", "river-weld", "noah", 10, 8, 12),
        ("assignment-review", "review", "ella", 9, 13, 16),
    ]:
        db.add(
            Assignment(
                id=aid,
                task_id=tid,
                worker_id=wid,
                starts_at=at(day, start),
                ends_at=at(day, end),
                status="confirmed",
            )
        )
    db.add_all(
        [
            JobPosting(
                id="job-electrical",
                organization_id="northline",
                project_id="eastside",
                title="Journeyperson electrician",
                location="Edmonton, AB",
                work_mode="on_site",
                skills=["Electrical"],
                rate_min_cents=6500,
                rate_max_cents=8500,
                status="open",
            ),
            JobPosting(
                id="job-welder",
                organization_id="northline",
                project_id="river",
                title="Structural welder · contract",
                location="Edmonton, AB",
                work_mode="on_site",
                skills=["Welding", "Fabrication"],
                rate_min_cents=5800,
                rate_max_cents=7200,
                status="open",
            ),
            JobPosting(
                id="job-engineer",
                organization_id="northline",
                project_id="design",
                title="Project engineer · hybrid",
                location="Edmonton, AB",
                work_mode="hybrid",
                skills=["Engineering"],
                rate_min_cents=7000,
                rate_max_cents=9000,
                status="open",
            ),
        ]
    )
    db.commit()
    seed_adaptive(db)


def seed_adaptive(db):
    # Upgrade only the known fictional workspace, never arbitrary production tenants.
    if not db.get(Organization, "northline"):
        return
    extras = [
        (
            "isla",
            "Isla Nguyen",
            "Concrete specialist",
            ["Concrete placement"],
            ["Concrete Safety"],
            5800,
        ),
        (
            "lucas",
            "Lucas Martin",
            "Site carpenter",
            ["Carpentry", "Blueprint reading"],
            ["Carpentry"],
            5700,
        ),
        (
            "amelia",
            "Amelia Singh",
            "Crane operator",
            ["Equipment operation"],
            ["Heavy Equipment"],
            6300,
        ),
        (
            "jack",
            "Jack Anderson",
            "Field electrician",
            ["Electrical"],
            ["Red Seal Electrical"],
            7600,
        ),
    ]
    for wid, name, title, skills, certs, rate in extras:
        if db.get(Worker, wid):
            continue
        mid = "demo-" + wid
        db.add(
            Membership(
                id=mid,
                organization_id="northline",
                auth_subject="demo:" + wid,
                name=name,
                role="worker",
            )
        )
        db.flush()
        db.add(
            Worker(
                id=wid,
                membership_id=mid,
                organization_id="northline",
                name=name,
                title=title,
                location="Edmonton, AB",
                hourly_rate_cents=rate,
                employment_type="contractor",
                work_modes=["on_site", "hybrid"],
                color="#759fa7",
            )
        )
        db.flush()
        db.add_all(Skill(worker_id=wid, name=skill) for skill in skills)
        db.add_all(Certification(worker_id=wid, name=cert, expires_at=at(30, 17)) for cert in certs)
        db.add_all(
            AvailabilityWindow(
                worker_id=wid, starts_at=at(d, 9 if wid == "jack" else 8), ends_at=at(d, 16)
            )
            for d in range(9, 14)
            if not (wid == "amelia" and d == 10)
        )
    from .weather import refresh_forecast

    for project in db.scalars(select(Project).where(Project.organization_id == "northline")):
        if not db.get(SchedulingPolicy, project.id):
            rules = (
                {"rough-in": {"max_rain_probability": 70, "max_wind_kph": 50}}
                if project.id == "eastside"
                else {"site-prep": {"max_precipitation_mm": 10, "max_wind_kph": 60}}
                if project.id == "river"
                else {}
            )
            db.add(
                SchedulingPolicy(
                    project_id=project.id,
                    task_buffer_percent=0,
                    transition_minutes=0,
                    contingency_minutes=0,
                    freeze_hours=48,
                    task_weather_rules=rules,
                )
            )
            db.flush()
        if not db.scalar(
            select(WeatherForecast.id).where(WeatherForecast.project_id == project.id).limit(1)
        ):
            refresh_forecast(db, project, False)
    db.commit()


def reset(db: Session):
    if db.scalar(select(Organization.id).where(Organization.id != "northline").limit(1)):
        raise ValueError("Reset refused: database contains non-demo organizations")
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(delete(table))
    db.expunge_all()
    seed(db)


if __name__ == "__main__":
    from .database import SessionLocal
    from .config import settings

    if not settings.demo_mode:
        raise SystemExit("Demo seed disabled")
    with SessionLocal() as db:
        seed(db)
    print("SHIFT fictional demo seeded: November 9–13, 2026, America/Edmonton.")

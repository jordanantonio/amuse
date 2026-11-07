"""Run a persisted rolling review. A cron/timer must be configured separately."""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from sqlalchemy import select
from shift_api.database import SessionLocal
from shift_api.models import Project
from shift_api.weather import review
from shift_api.locking import lock_schedule
from shift_api.solver_time import utc

if __name__ == "__main__":
    count = 0
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        projects = [
            (p.id, p.organization_id)
            for p in db.scalars(select(Project))
            if utc(p.deadline) >= now and utc(p.starts_at) <= now + timedelta(days=14)
        ]
        for pid, org in projects:
            lock_schedule(db, org)
            p = db.get(Project, pid)
            output = review(db, p)
            db.commit()
            count += 1
            print(f"{p.name}: {len(output['risks'])} modeled risk(s)")
    print(f"Reviewed {count} projects. No background scheduler was installed.")

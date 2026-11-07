"""PostgreSQL no-overlap constraints and API-exclusive RLS boundary.

SQLite scheduling mutations use BEGIN IMMEDIATE; PostgreSQL mutations additionally
use tenant advisory locks to validate cross-table accepted reservations atomically.
"""

from alembic import op

revision = "c39d0451b6d2"
down_revision = "12a81cadc818"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        "ALTER TABLE assignments ADD CONSTRAINT assignments_no_overlap EXCLUDE USING gist (worker_id WITH =, tstzrange(starts_at,ends_at,'[)') WITH &&) WHERE (status = 'confirmed')"
    )
    op.execute(
        "ALTER TABLE slot_reservations ADD CONSTRAINT reservations_no_overlap EXCLUDE USING gist (worker_id WITH =, tstzrange(starts_at,ends_at,'[)') WITH &&)"
    )
    # Supabase clients access data through the authenticated FastAPI boundary.
    # No direct browser writes or private-calendar reads are granted.
    tables = [
        "organizations",
        "memberships",
        "workers",
        "worker_skills",
        "certifications",
        "availability_windows",
        "private_commitments",
        "worksites",
        "projects",
        "tasks",
        "task_dependencies",
        "assignments",
        "job_postings",
        "applications",
        "schedule_drafts",
        "invitations",
        "audit_events",
        "worker_absences",
        "scheduling_policies",
        "weather_forecasts",
        "recovery_proposals",
        "worker_confirmations",
        "slot_reservations",
        "approval_decisions",
        "scheduling_events",
        "risk_reviews",
    ]
    for name in tables:
        op.execute(f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'REVOKE ALL ON TABLE "{name}" FROM PUBLIC')
        for role in ("anon", "authenticated"):
            op.execute(
                f'''DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') THEN EXECUTE 'REVOKE ALL ON TABLE "{name}" FROM {role}'; END IF; END $$'''
            )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE assignments DROP CONSTRAINT IF EXISTS assignments_no_overlap")
    op.execute("ALTER TABLE slot_reservations DROP CONSTRAINT IF EXISTS reservations_no_overlap")
    # RLS is intentionally retained on rollback; relaxing privacy needs explicit review.

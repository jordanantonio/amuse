"""Hosted identity policies and confirmed assignment exclusion."""

from pathlib import Path
from alembic import op

revision = "c8422af013ab"
down_revision = "89fc75569341"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(Path(__file__).with_suffix(".sql").read_text())


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE public.assignments DROP CONSTRAINT assignments_no_confirmed_overlap")
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
        for operation in ("read", "insert", "update"):
            op.execute(f"DROP POLICY IF EXISTS shift_{operation} ON public.{table}")
        op.execute(f"REVOKE ALL ON public.{table} FROM shift_app")
    for signature in (
        "shift_busy()",
        "shift_external_commitments(text)",
        "shift_project_visible(text)",
        "shift_project_managed(text)",
        "shift_worker_visible(text)",
        "shift_actor()",
    ):
        op.execute(f"DROP FUNCTION public.{signature}")
    # Shared group role/extension are deliberately retained; login roles may depend on them.


TABLES = (
    "organizations",
    "memberships",
    "workers",
    "worker_skills",
    "certifications",
    "availability_windows",
    "private_commitments",
    "worker_absences",
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
)

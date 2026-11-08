"""Opt-in integration suite: isolated database named shift_identity_test only."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from shift_api import database
from shift_api.config import settings
from shift_api.main import app
from shift_api.models import Membership, Organization
from shift_api.seed import seed
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

URL = os.getenv("SHIFT_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not URL, reason="SHIFT_TEST_POSTGRES_URL not configured")


@pytest.fixture(scope="module")
def postgres():
    assert make_url(URL).database == "shift_identity_test", (
        "Use a dedicated shift_identity_test database"
    )
    owner = create_engine(URL)
    with owner.begin() as conn:
        conn.execute(
            text("""DO $$ DECLARE browser_role text; BEGIN
          FOREACH browser_role IN ARRAY ARRAY['anon','authenticated'] LOOP
            IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname=browser_role) THEN
              EXECUTE format('CREATE ROLE %I NOLOGIN', browser_role);
            END IF;
          END LOOP;
        END $$""")
        )
        # Reproduce Supabase's permissive default function grants before migration.
        conn.execute(
            text(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon, authenticated"
            )
        )
    original = settings.database_url
    try:
        settings.database_url = URL
        command.upgrade(Config(str(Path(__file__).resolve().parents[3] / "alembic.ini")), "head")
        command.check(Config("alembic.ini"))
    finally:
        settings.database_url = original
    with Session(owner) as db:
        seed(db)
        if not db.get(Organization, "other"):
            db.add(Organization(id="other", name="Other fictional company"))
            db.flush()
            db.add_all(
                [
                    Membership(
                        id="other-admin",
                        organization_id="other",
                        auth_subject="other:admin",
                        name="Other Admin",
                        role="admin",
                    ),
                    Membership(
                        id="unassigned-manager",
                        organization_id="northline",
                        auth_subject="demo:unassigned",
                        name="Unassigned Manager",
                        role="manager",
                    ),
                ]
            )
            db.commit()
    with owner.begin() as conn:
        conn.execute(
            text("""DO $$ BEGIN
          IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='shift_test_runtime') THEN
            CREATE ROLE shift_test_runtime LOGIN NOSUPERUSER NOBYPASSRLS;
          END IF;
        END $$""")
        )
        conn.execute(text("GRANT shift_app TO shift_test_runtime"))
        if make_url(URL).password:
            from psycopg import sql

            conn.connection.driver_connection.execute(
                sql.SQL("ALTER ROLE shift_test_runtime PASSWORD {}").format(
                    sql.Literal(make_url(URL).password)
                )
            )
    with owner.begin() as conn:
        conn.execute(
            text("""INSERT INTO memberships(id,organization_id,auth_subject,name,role)
          VALUES ('river-manager','northline','demo:river-manager','River Manager','manager')
          ON CONFLICT (id) DO NOTHING""")
        )
        conn.execute(text("UPDATE projects SET manager_id='river-manager' WHERE id='river'"))
    runtime = create_engine(
        make_url(URL).set(username="shift_test_runtime"), pool_size=1, max_overflow=0
    )
    yield owner, runtime
    runtime.dispose()
    owner.dispose()


def scoped(runtime, subject):
    db = Session(runtime, expire_on_commit=False)
    db.info["auth_subject"] = subject
    return db


def test_rls_project_worker_and_tenant_scope(postgres):
    _, runtime = postgres
    with scoped(runtime, "demo:manager") as db:
        assert db.scalars(text("SELECT id FROM memberships")).all() == ["demo-manager"]
        assert db.scalars(text("SELECT id FROM organizations")).all() == ["northline"]
        projects = db.scalars(text("SELECT id FROM projects")).all()
        assert "eastside" in projects
        assert "river" not in projects
        assert db.scalar(text("SELECT count(*) FROM assignments WHERE id='assignment-river'")) == 0
        assert any(
            row.id == "assignment-river" for row in db.execute(text("SELECT * FROM shift_busy()"))
        )
        assert db.scalars(text("SELECT private_label FROM private_commitments")).all() == []
        assert db.execute(text("SELECT * FROM shift_busy()")).all()
        assert set(db.execute(text("SELECT * FROM shift_busy() LIMIT 1")).keys()) == {
            "id",
            "worker_id",
            "starts_at",
            "ends_at",
        }
    with scoped(runtime, "demo:sofia") as db:
        assert db.scalars(text("SELECT id FROM workers")).all() == ["sofia"]
        assert all(w == "sofia" for w in db.scalars(text("SELECT worker_id FROM assignments")))
        assert db.execute(text("SELECT * FROM shift_external_commitments('eastside')")).all() == []
    with scoped(runtime, "demo:unassigned") as db:
        assert db.scalars(text("SELECT id FROM projects")).all() == []
        assert db.scalars(text("SELECT id FROM schedule_drafts")).all() == []
    with scoped(runtime, "other:admin") as db:
        assert db.scalars(text("SELECT id FROM organizations")).all() == ["other"]
        assert db.scalars(text("SELECT id FROM workers")).all() == []
        assert db.execute(text("SELECT * FROM shift_busy()")).all() == []


def test_context_resets_across_commit_rollback_and_pool(postgres):
    _, runtime = postgres
    with scoped(runtime, "demo:manager") as db:
        assert db.scalar(text("SELECT count(*) FROM workers")) > 1
        db.commit()
        assert db.scalar(text("SELECT count(*) FROM workers")) > 1
        db.rollback()
    with Session(runtime) as db:
        assert db.scalar(text("SELECT count(*) FROM workers")) == 0
        assert db.scalar(text("SELECT count(*) FROM memberships")) == 0
    with scoped(runtime, "demo:sofia") as db:
        assert db.scalars(text("SELECT id FROM workers")).all() == ["sofia"]


def test_runtime_cannot_provision_users_or_read_private_labels(postgres):
    _, runtime = postgres
    with scoped(runtime, "demo:manager") as db:
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE memberships SET role='admin' WHERE id='demo-manager'"))
        db.rollback()
        assert db.scalars(text("SELECT private_label FROM private_commitments")).all() == []
    with scoped(runtime, "demo:unassigned") as db:
        assert (
            db.execute(
                text("UPDATE assignments SET status='disrupted' WHERE id='assignment-maya'")
            ).rowcount
            == 0
        )


def test_runtime_startup_role(postgres, monkeypatch):
    owner, runtime = postgres
    monkeypatch.setattr(database, "engine", runtime)
    database.check_runtime_role()
    monkeypatch.setattr(database, "engine", owner)
    with pytest.raises(RuntimeError):
        database.check_runtime_role()


def test_hosted_api_and_solver(postgres, signing, monkeypatch):
    owner, runtime = postgres
    monkeypatch.setattr(database, "engine", runtime)

    def get_db():
        with Session(runtime, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[database.get_db] = get_db
    try:
        with TestClient(app) as client:
            headers = {"Authorization": "Bearer " + signing()}
            response = client.get("/api/v1/dashboard", headers=headers)
            assert response.status_code == 200, response.text
            assert "PRIVATE:" not in response.text
            assert response.json()["demo"] is False
            draft = client.post("/api/v1/projects/eastside/draft", headers=headers)
            assert draft.status_code == 200, draft.text
            assert draft.json()["solver_status"] in ("OPTIMAL", "FEASIBLE"), draft.text
            worker = client.get(
                "/api/v1/dashboard",
                headers={"Authorization": "Bearer " + signing(sub="demo:sofia")},
            )
            assert worker.status_code == 200, worker.text
            assert [w["id"] for w in worker.json()["workers"]] == ["sofia"]
            denied = client.post(
                "/api/v1/projects/eastside/draft",
                headers={"Authorization": "Bearer " + signing(sub="demo:unassigned")},
            )
            assert denied.status_code in (403, 404)
            disrupted = client.post("/api/v1/assignments/assignment-maya/disrupt", headers=headers)
            assert disrupted.status_code == 200, disrupted.text
            assert (
                client.post(
                    "/api/v1/assignments/assignment-maya/disrupt", headers=headers
                ).status_code
                == 409
            )
            recovery = client.post("/api/v1/projects/eastside/draft", headers=headers)
            assert recovery.status_code == 200, recovery.text
            assert recovery.json()["solver_status"] in ("OPTIMAL", "FEASIBLE"), recovery.text
            assert any(p["worker_id"] == "sofia" for p in recovery.json()["proposals"])

    finally:
        app.dependency_overrides.clear()
        with owner.begin() as conn:
            conn.execute(
                text("UPDATE assignments SET status='confirmed' WHERE id='assignment-maya'")
            )
            conn.execute(
                text(
                    "DELETE FROM worker_absences WHERE worker_id='maya' AND recorded_by='demo-manager'"
                )
            )


def test_concurrent_overlap_and_adjacent_history(postgres):
    owner, _ = postgres
    # Test the constraint directly, independent of application checks or RLS.
    with owner.connect() as conn:
        worker = conn.scalar(text("SELECT id FROM workers LIMIT 1"))
        task = conn.scalar(text("SELECT id FROM tasks LIMIT 1"))
    sql = text("""INSERT INTO assignments(id,worker_id,task_id,starts_at,ends_at,status)
      VALUES (:id,:worker,:task,:start,:end,:status)""")

    barrier = Barrier(2)

    def insert(name):
        try:
            with owner.begin() as conn:
                barrier.wait(timeout=5)
                conn.execute(
                    sql,
                    dict(
                        id=name,
                        worker=worker,
                        task="rough-in" if name == "race-one" else "river-weld",
                        start="2026-12-01T16:00:00Z",
                        end="2026-12-01T18:00:00Z",
                        status="confirmed",
                    ),
                )
            return True
        except DBAPIError as error:
            assert error.orig.sqlstate in ("23P01", "40P01")
            return False

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(insert, ["race-one", "race-two"])) == [False, True]
        with owner.begin() as conn:
            conn.execute(
                sql,
                dict(
                    id="adjacent",
                    worker=worker,
                    task=task,
                    start="2026-12-01T18:00:00Z",
                    end="2026-12-01T19:00:00Z",
                    status="confirmed",
                ),
            )
            for status in ("cancelled", "disrupted"):
                conn.execute(
                    sql,
                    dict(
                        id="history-" + status,
                        worker=worker,
                        task=task,
                        start="2026-12-01T16:00:00Z",
                        end="2026-12-01T18:00:00Z",
                        status=status,
                    ),
                )
    finally:
        with owner.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM assignments WHERE id IN ('race-one','race-two','adjacent','history-cancelled','history-disrupted')"
                )
            )


def test_browser_roles_cannot_access_application_data_or_helpers(postgres):
    owner, _ = postgres
    with owner.connect() as conn:
        for role in ("anon", "authenticated"):
            assert not conn.scalar(
                text("SELECT has_table_privilege(:role, 'public.memberships', 'SELECT')"),
                {"role": role},
            )
            for function in (
                "public.shift_actor()",
                "public.shift_busy()",
                "public.shift_external_commitments(text)",
            ):
                assert not conn.scalar(
                    text("SELECT has_function_privilege(:role, :function, 'EXECUTE')"),
                    {"role": role, "function": function},
                )


def test_overlap_constraint_refuses_existing_invalid_data(postgres):
    owner, _ = postgres
    with pytest.raises(IntegrityError):
        with owner.begin() as conn:
            conn.execute(
                text("ALTER TABLE assignments DROP CONSTRAINT assignments_no_confirmed_overlap")
            )
            conn.execute(
                text("""INSERT INTO assignments(id,worker_id,task_id,starts_at,ends_at,status)
              SELECT 'invalid-existing-overlap',worker_id,task_id,starts_at,ends_at,status
              FROM assignments WHERE id='assignment-maya'""")
            )
            conn.execute(
                text("""ALTER TABLE assignments ADD CONSTRAINT assignments_no_confirmed_overlap
              EXCLUDE USING gist (worker_id WITH =, tstzrange(starts_at,ends_at,'[)') WITH &&)
              WHERE (status='confirmed')""")
            )
    # Transaction rollback preserves original assignments and reinstates the constraint.
    with owner.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM assignments WHERE id='invalid-existing-overlap'")
            )
            == 0
        )
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conname='assignments_no_confirmed_overlap'"
                )
            )
            == 1
        )

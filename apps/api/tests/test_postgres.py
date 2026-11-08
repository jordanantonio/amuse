"""Real PostgreSQL integration. Skipped locally without SHIFT_TEST_POSTGRES_URL.
CI provides a disposable PostgreSQL service and applies actual Alembic migrations.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, ProgrammingError
from fastapi.testclient import TestClient
from shift_api.database import make_engine, get_db
from shift_api.main import app
from shift_api.models import Assignment, SlotReservation
from shift_api.seed import reset, at

URL = os.environ.get("SHIFT_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not URL, reason="Disposable PostgreSQL integration URL not configured"
)


@pytest.fixture
def pg():
    engine = make_engine(URL)
    with Session(engine, expire_on_commit=False) as s:
        reset(s)
    old = app.dependency_overrides.copy()

    def sessions():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = sessions
    yield engine
    app.dependency_overrides.clear()
    app.dependency_overrides.update(old)
    engine.dispose()


def test_postgres_exclusion_rejects_overlapping_confirmed_assignments(pg):
    with Session(pg) as s:
        s.add(
            Assignment(
                task_id="rough-in",
                worker_id="maya",
                starts_at=at(9, 9),
                ends_at=at(9, 11),
                status="confirmed",
            )
        )
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()


def test_postgres_rls_denies_direct_client_access(pg):
    with pg.connect() as c:
        assert c.execute(
            text("SELECT relrowsecurity FROM pg_class WHERE relname='private_commitments'")
        ).scalar()
        c.execute(text("SET LOCAL ROLE authenticated"))
        with pytest.raises(ProgrammingError):
            c.execute(text("SELECT * FROM private_commitments"))
        c.rollback()


def test_postgres_concurrent_acceptance_and_publication(pg):
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/v1/assignments/assignment-maya/disrupt",
                json={"starts_at": at(9, 8).isoformat(), "ends_at": at(13, 17).isoformat()},
            ).status_code
            == 200
        )

        def make():
            p = c.post(
                "/api/v1/projects/eastside/proposals", json={"objectives": ["lowest_cost"]}
            ).json()[0]
            return c.post(
                f"/api/v1/proposals/{p['id']}/decision", json={"decision": "approve"}
            ).json()

        a, b = make(), make()
        wid = a["confirmations"][0]["worker_id"]

        def accept(p):
            return c.post(
                f"/api/v1/proposals/{p['id']}/confirmation",
                headers={"X-Demo-Persona": "demo-" + wid},
                json={"decision": "accept"},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(accept, [a, b]))
        assert sorted(r.status_code for r in responses) == [200, 409]
        winner = next(r.json() for r in responses if r.status_code == 200)
        # Worker responses intentionally redact other workers' confirmations.
        manager_view = c.get(f"/api/v1/proposals/{winner['id']}").json()
        for w in manager_view["confirmations"]:
            if w["status"] == "pending":
                assert (
                    c.post(
                        f"/api/v1/proposals/{winner['id']}/confirmation",
                        headers={"X-Demo-Persona": "demo-" + w["worker_id"]},
                        json={"decision": "accept"},
                    ).status_code
                    == 200
                )
        published = c.post(f"/api/v1/proposals/{winner['id']}/publish")
        assert published.status_code == 200, published.text
        assert published.json()["status"] == "published"
        with Session(pg) as s:
            assert not s.scalar(select(SlotReservation.id))

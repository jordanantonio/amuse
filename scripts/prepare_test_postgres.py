"""Create Supabase-like client roles only inside the explicitly named disposable CI DB."""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(os.environ["SHIFT_TEST_POSTGRES_URL"])
if url.host not in {"127.0.0.1", "localhost"} or url.database != "shift_test":
    raise SystemExit("Refusing to prepare a non-local/non-test database")
with create_engine(url).begin() as c:
    for role in ("anon", "authenticated"):
        c.execute(
            text(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') THEN CREATE ROLE {role} NOLOGIN; END IF; END $$"
            )
        )
print("Disposable PostgreSQL client roles prepared.")

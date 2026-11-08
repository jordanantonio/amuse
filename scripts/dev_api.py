"""Migrate, seed the local fictional fixture, and start FastAPI on loopback."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps/api"))
from alembic import command
from alembic.config import Config
import os
from shift_api.config import settings

# Default this explicit launcher to local demo, but respect settings supplied in
# either the shell or .env. A hosted .env must never be silently changed to demo.
if "demo_mode" not in settings.model_fields_set:
    settings.demo_mode = True
if "environment" not in settings.model_fields_set:
    settings.environment = "local"
from shift_api.database import SessionLocal
from shift_api.seed import seed
import uvicorn

if __name__ == "__main__":
    if not settings.demo_mode:
        raise SystemExit("This launcher is local-demo-only; use uvicorn for hosted mode.")
    settings.validate_hosted()
    from sqlalchemy.engine import make_url

    database = make_url(settings.database_url)
    if (
        database.get_backend_name() == "sqlite"
        and database.database
        and database.database != ":memory:"
    ):
        Path(database.database).parent.mkdir(parents=True, exist_ok=True)
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "apps/api/migrations"))
    command.upgrade(cfg, "head")
    with SessionLocal() as db:
        seed(db)
    uvicorn.run(
        "shift_api.main:app", host="127.0.0.1", port=int(os.environ.get("SHIFT_DEMO_PORT", "8000"))
    )

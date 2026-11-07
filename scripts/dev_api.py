"""Migrate, seed the local fictional fixture, and start FastAPI on loopback."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps/api"))
from alembic import command
from alembic.config import Config
from shift_api.config import settings
from shift_api.database import SessionLocal
from shift_api.seed import seed
import uvicorn

if __name__ == "__main__":
    if not settings.demo_mode:
        raise SystemExit("Production identity is not configured. This launcher is local-demo-only.")
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
    uvicorn.run("shift_api.main:app", host="127.0.0.1", port=8000)

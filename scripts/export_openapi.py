"""Export FastAPI's versioned contract; --check fails on stale generated output."""

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps/api"))
from shift_api.main import app

payload = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
target = root / "packages/contracts/openapi.json"
if "--check" in sys.argv:
    if not target.exists() or target.read_text() != payload:
        raise SystemExit("OpenAPI is stale: run python scripts/export_openapi.py")
else:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload)

# SHIFT

**Workforce, in sync.** A hybrid-first workforce operating system for construction,
manufacturing, and project-based employment. Built for natHacks 2026.

SHIFT connects availability and cross-project assignments, a project-based talent
marketplace, and Google OR-Tools CP-SAT scheduling. Its defining workflow is
recovering a project schedule when an important worker becomes unavailable.

This is the **runnable foundation**, not the finished MVP. It includes the project
docs, relational schema/migrations, fictional demo, role-scoped dashboard, team and
worker calendar, project/task views, searchable talent, explicit disruption action,
and a real CP-SAT draft generator. Drafts never become confirmed assignments.

## Run locally

Requirements: **Node.js 24 LTS + npm**, **Python 3.12+**, and **uv**. No Supabase
account or API key is required for the local SQLite demo. Commands run at repo root.

```sh
uv sync --locked
npm ci
```

Terminal 1 — migrations, fictional seed, and FastAPI:

```sh
uv run python scripts/dev_api.py
```

Terminal 2 — Next.js:

```sh
npm run dev
```

Open **http://127.0.0.1:3000**. FastAPI OpenAPI docs:
http://127.0.0.1:8000/docs. The API is proxied through Next.js at `/api/v1`.
Both launchers bind to loopback. Stop each with Ctrl+C.

The root `.env` is optional (see `.env.example`). To change the Next proxy, set
`API_INTERNAL_URL` in the web process environment or `apps/web/.env.local`.
The fictional fixture is the week **November 9–13, 2026, America/Edmonton**, so it
remains repeatable regardless of today's date. It persists in ignored `shift.sqlite`.
There is no production login yet: the clearly labeled persona selector is a local
role-policy demo. **Do not expose this foundation publicly.**

## Try the foundation

1. Explore Overview, Team calendar, Projects, and Talent marketplace. All use the API.
2. Open Schedule lab as Alex Morgan. Select Eastside facility fit-out.
3. Generate a draft: CP-SAT fills the unstaffed inspection while preserving fixed work.
4. On Maya Brooks's electrical rough-in, choose **Record absence**, read the
   project-week absence scope, and confirm. The assignment remains in history.
5. Generate again. The solver proposes qualified contractor coverage respecting
   private busy windows, dependencies, site capacity, deadlines, and budget.
6. The proposal is visibly a draft. Confirmed calendars remain unchanged. Approval,
   invitation, and contractor acceptance are intentionally the next milestone.
7. Switch to Sofia Rivera's worker persona to see her own profile/calendar and open
   roles. She cannot generate drafts or view other workers' private details.
8. Switch to Taylor Chen (admin), open Schedule lab, and reset the fictional demo.

## Verify

```sh
uv run pytest -q
uv run alembic upgrade head
uv run alembic check
uv run python scripts/export_openapi.py --check
npm run typecheck
npm run build
npm run test:e2e
```

Browser tests use Playwright; install a browser with `npx playwright install chromium`
or set `PLAYWRIGHT_CHROME_PATH` to an existing Chrome executable. They launch an
isolated API fixture in `.tmp/` and a Next server; keep ports 8000/3000 free.
See [docs/TESTING.md](docs/TESTING.md) for actual results and limitations.

To export an updated API contract:

```sh
uv run python scripts/export_openapi.py
```

For manual database administration (demo only):

```sh
uv run alembic upgrade head
PYTHONPATH=apps/api uv run python -m shift_api.seed
```

## Structure and collaboration

- `apps/web/`: Next.js App Router, TypeScript, Tailwind, Lucide, composable UI.
- `apps/api/shift_api/`: FastAPI, SQLAlchemy models, policy projections, CP-SAT.
- `apps/api/migrations/`: Alembic schema history (SQLite/PostgreSQL compatible).
- `packages/contracts/openapi.json`: exported API contract.
- `docs/`: [Product](docs/PRODUCT_SPEC.md), [Architecture](docs/ARCHITECTURE.md),
  [Implementation plan](docs/IMPLEMENTATION_PLAN.md).
- [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md): permanent collaborator rules.

Use `codex/<task>` and `claude/<task>` branches in separate worktrees. Coordinate
shared contracts before parallel changes. Never push or merge without authorization.
The original MIT license is retained.

## Next milestones

Supabase authentication/JWT and RLS; production PostgreSQL concurrency constraints;
profile, availability, project, and job editing; applications; versioned schedule
approval; invitations and atomic acceptance; full Gantt; complete recovery demo.
No LLM decides feasibility. No optimization performance claims are fabricated.

# SHIFT

**Workforce, in sync.** A hybrid-first workforce operating system for construction,
manufacturing and project work, built for natHacks 2026.

SHIFT connects professional profiles, published availability, cross-project
calendars, job postings/applications, and **SHIFT Adaptive**: weather-aware CP-SAT
recovery with manager approval, worker acceptance and atomic publication.

**SHIFT recommends. Authorized humans approve.** Proposed work never silently
replaces a confirmed schedule. No LLM determines feasibility or invents metrics.

## Run locally

Requirements: Node.js 24 LTS + npm, Python 3.12+, and uv. No cloud account is required
for the clearly labeled fictional SQLite demo.

```sh
uv sync --locked
npm ci
```

Terminal 1:

```sh
uv run python scripts/dev_api.py
```

Terminal 2:

```sh
npm run dev
```

Open **http://127.0.0.1:3000**. API documentation: http://127.0.0.1:8000/docs.
Both launchers bind to loopback. Stop with Ctrl+C. SQLite persists to ignored
`shift.sqlite`; startup applies Alembic migrations and idempotently upgrades the
fictional Northline fixture. It does not reset existing work.

The demo week is **November 9–13, 2026, America/Edmonton**, with 12 workers, three
projects, indoor/outdoor tasks, private busy windows and simulated weather. The
persona selector is a local demo harness, not production authentication.

## Try the complete recovery

1. As Alex Morgan, open **SHIFT Adaptive** and select Eastside facility fit-out.
2. Click **Simulate heavy rain**, then review the task-specific weather risks.
3. Record Maya Brooks's absence. Enter an explicit end of November 13 at 17:00.
   Confirmed assignments remain in place.
4. **Generate recovery options**: compare lowest cost, earliest completion and
   fewest changes. They may produce identical plans when constraints dictate one.
5. Review original/proposed Gantt timelines, actual labour costs, deadlines and
   buffers. **Approve & request acceptance**.
6. Switch to each named affected worker using the demo selector. In **My invitations**,
   open the proposal and **Accept assignments**. Declining requests revision.
7. Switch back to Alex. **Approval inbox → Revalidate & publish schedule**.
8. Inspect the manager and worker calendars: the accepted plan is now confirmed.
   Other assignments are retained; superseded assignments remain in audit history.
9. To repeat, switch to Taylor Chen (administrator) and use **Reset demo** in Adaptive.

See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for a three-minute walkthrough and
[docs/ADAPTIVE.md](docs/ADAPTIVE.md) for lifecycle/constraint details.

## Other working features

- Calendar day/week navigation, full-date matching, clipped multi-day busy windows,
  true free-time windows, proposal overlays, state legend and assignment drawer.
- Project/deadline/capacity editing; task requirements, crew sizes and dependency DAGs.
- Worker profile, qualifications, rates, availability editing and exact absence reports.
- Job creation/closing, role/profile search, applications/withdrawal and validated offers.
- Approval/revision/rejection comments and history; stale/expired proposal handling.
- Separately optimized feasible alternatives; configurable task/setup/contingency
  buffers, working hours, rest and daily-hour limits; task-specific weather thresholds.
- Manual 14-day review and a CLI suitable for separately configured cron execution.
- Operational overview, mobile worker workspace, shareable view/project/proposal URLs,
  and reliable refresh after writes plus 15-second polling/freshness indicators.

## Supabase authentication and PostgreSQL

The implementation supports Supabase password sign-in and server-side asymmetric
JWT verification (issuer/audience/expiry/signature), membership-based authorization,
PostgreSQL exclusion constraints and an API-exclusive RLS boundary. Hosted Supabase
credentials are not included. Local verification uses signed test JWTs; hosted
sign-in still requires a real project.

Configure backend variables in `.env`:

```dotenv
SHIFT_DEMO_MODE=false
SHIFT_DATABASE_URL=postgresql+psycopg://YOUR_SERVER_ONLY_CONNECTION
SHIFT_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
```

Configure public client values in `apps/web/.env.local`:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_OR_PUBLISHABLE_KEY
```

Apply migrations with `uv run alembic upgrade head`. Create an organization with
an operator-managed migration/provisioning process, then map an existing Supabase
Auth user's UUID to an organization and role:

```sh
uv run python scripts/provision_member.py --subject AUTH_USER_UUID \
  --organization ORGANIZATION_ID --name "Team member" --role worker
```

For authenticated mode, run the API without the demo seeding launcher:

```sh
PYTHONPATH=apps/api uv run uvicorn shift_api.main:app --host 127.0.0.1 --port 8000
```

Never expose a database password or service-role key to the browser. With demo
mode false, demo headers cannot select identities. Requests without verified JWTs
fail closed. Browser clients have no direct database grants; all app data passes
through the role-scoped FastAPI boundary. See [architecture](docs/ARCHITECTURE.md)
for deployment assumptions and verification limits.

## Tests

```sh
uv run pytest -q
uv run alembic upgrade head
uv run alembic check
uv run python scripts/export_openapi.py --check
npm run typecheck
npm run test:calendar
npm run build
npm run test:e2e
```

Playwright requires `npx playwright install chromium`, or set
`PLAYWRIGHT_CHROME_PATH` to an installed Chrome executable. It starts isolated
servers and `.tmp/e2e.sqlite`; ports 3000/8000 must be free. PostgreSQL integration
requires an explicitly disposable database; CI provides one. See
[TESTING.md](docs/TESTING.md) for actual results, skipped checks and limits.

Regenerate API contracts with `uv run python scripts/export_openapi.py`.
Run one persisted rolling review with `uv run python scripts/review_schedules.py`.
**No background scheduler is installed by these commands.**

## Repository and collaboration

- `apps/web`: Next.js, TypeScript, Tailwind, Lucide, Supabase client and owned UI primitives.
- `apps/api/shift_api`: FastAPI, SQLAlchemy, CP-SAT, policies and recovery transactions.
- `apps/api/migrations`: additive Alembic history and PostgreSQL guards.
- `packages/contracts/openapi.json`: versioned request/response contract.
- `AGENTS.md`, `CLAUDE.md`, and `docs/`: collaboration rules, architecture and milestones.

Use separate `codex/<task>` / `claude/<task>` branches and worktrees. Coordinate
shared contracts, test changes, and obtain authorization before pushing/merging.
The original MIT license is retained.

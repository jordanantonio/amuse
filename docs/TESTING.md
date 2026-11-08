# Foundation verification

Verified locally on 2026-11-06 using Python 3.12.14 and Node.js 24.22.2.
Dependency versions are recorded in uv.lock and package-lock.json. Both stacks
run locally without Supabase credentials. CI configuration is included but has not
run on GitHub because no changes have been pushed.

## Executed checks

| Check | Result | Scope |
| --- | --- | --- |
| `uv run pytest -q` | 27 passed | Seeded dashboard, role/tenant/project scope, privacy, CP-SAT and negative constraints |
| `npm run typecheck` | Passed | Strict TypeScript including component contracts |
| `npm run build` | Passed with Webpack | Next.js production compilation and prerender |
| `uv run alembic upgrade head` | Passed | Initial schema and explicit absence migration on SQLite |
| `uv run alembic check` | Passed | No model/migration schema drift |
| `uv run python scripts/export_openapi.py --check` | Passed | Exported contract matches live FastAPI schema |
| `npm run test:e2e` | 2 passed | Chrome browser, actual Next→FastAPI→SQLite→CP-SAT requests |

Backend cases include: unpublished/private calendar text never reaches managers;
workers see only their own assignments; workers cannot disrupt or generate drafts;
other tenants and unassigned managers cannot plan a project; production mode fails
closed without configured identity; solver drafts preserve confirmed assignments;
explicit absence raises a staffing gap; recovery selects qualified available
contractor coverage; cross-project double booking is disallowed; certifications,
skills, published windows, deadlines, dependencies, budget and site capacity are
hard constraints; timeout is UNKNOWN; partial fixed crews return unsupported input;
fingerprints change when rates change; only a demo admin can reset; non-demo data
prevents reset; fractional busy windows block intersecting hourly slots.

Browser cases cover: live manager overview and team calendar; explicit Maya absence
confirmation; persisted CP-SAT proposed recovery; drafts do not become confirmed
calendar entries; worker persona privacy; marketplace search; 390px layout without
document overflow. Screenshots are generated in ignored `test-results/`.

## Environment notes and reproducibility

This machine initially had no Node/npm in PATH. A checksum-verified Node 24 LTS
runtime was used from `/tmp/shift-node/`; no global runtime installation was made.
The repository itself uses standard `node`/`npm` commands and `.nvmrc`.
Python dependencies are isolated in `.venv`; lockfiles are committed-ready.

Turbopack's CSS processing tried to bind a subprocess port forbidden by this
execution environment. The supported `--webpack` option succeeds and is used by
both development and build scripts. This is a bundler selection, not a framework
or product-stack substitution.

For local browser checks on macOS with installed Chrome:

```sh
PLAYWRIGHT_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:e2e
```

Otherwise run `npx playwright install chromium` once, then `npm run test:e2e`.
The browser harness starts both servers and uses `.tmp/e2e.sqlite`, never the normal
`shift.sqlite`. Its dev launcher creates the database parent folder automatically.
Ports 3000 and 8000 must be free. Tests reset the fictional fixture before each case.
Python tests use an isolated in-memory database; no external service is needed.

The Python suite currently emits one upstream Starlette/httpx deprecation warning;
it does not fail tests. Migrate the test transport when the dependency transition
is settled; do not suppress the warning by hiding test output.

## Verification limits

No hosted deployment, Supabase project, Supabase Auth/JWT verification, production
RLS, PostgreSQL exclusion constraints, or PostgreSQL concurrent acceptance tests
have run. Authentication is explicitly not implemented. Approval, invitations,
acceptance, full CRUD and Gantt remain milestones, not tested claims. The solver
is an hourly demo model, not a complete labour-law/travel/overtime engine. No
optimization runtime, savings, or utilization benchmark is asserted.

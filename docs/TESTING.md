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
The current harness uses ports 3002 and 8002 and an isolated Next build directory. Tests reset the fictional fixture before each case.
Python tests use an isolated in-memory database; no external service is needed.

The Python suite currently emits one upstream Starlette/httpx deprecation warning;
it does not fail tests. Migrate the test transport when the dependency transition
is settled; do not suppress the warning by hiding test output.

## Historical foundation verification limits

No hosted deployment, Supabase project, Supabase Auth/JWT verification, production
RLS, PostgreSQL exclusion constraints, or PostgreSQL concurrent acceptance tests
have run. Authentication is explicitly not implemented. Approval, invitations,
acceptance, full CRUD and Gantt remain milestones, not tested claims. The solver
is an hourly demo model, not a complete labour-law/travel/overtime engine. No
optimization runtime, savings, or utilization benchmark is asserted.

## Identity and database safety verification — 2026-11-08

Executed on the implementation branch using the installed `.venv` and Node toolchain:

| Check | Actual result |
| --- | --- |
| Full API suite with `SHIFT_TEST_POSTGRES_URL` | **49 passed**, including 8 real PostgreSQL integration tests |
| SQLite Alembic upgrade and check on `.tmp/identity-schema.sqlite` | Passed; no model/schema drift |
| PostgreSQL Alembic upgrade and check (integration fixture) | Passed; no model/schema drift |
| `.venv/bin/python scripts/export_openapi.py --check` | Passed |
| `npm run typecheck` | Passed |
| `npm run build` | Passed with Webpack |
| `npm run test:e2e` with installed Chrome | **2 passed**, live demo API/SQLite/CP-SAT |
| `npm run test:auth` with installed Chrome | **3 passed**, hosted UI with mocked Supabase/API responses |
| Ruff undefined-name/import checks on new identity modules/tests | Passed |

The API suite was run as:

```sh
SHIFT_TEST_POSTGRES_URL=postgresql+psycopg://shift_test_owner@127.0.0.1:55432/shift_identity_test \
  .venv/bin/python -m pytest -q
```

PostgreSQL 17 was installed through Homebrew. A separate temporary cluster under
`.tmp/identity-postgres` was used on loopback port 55432; no persistent database
service was enabled. Test data is fictional. The test cluster is stopped after checks.

Coverage includes signed JWT validation and invalid signatures/claims, membership
roles independent of token metadata, missing membership, disabled demo identity,
startup credential/configuration guards, manager/worker/tenant boundaries, private
calendar projections, transaction context after commit/rollback and pooled reuse,
hosted CP-SAT recovery, concurrent cross-project exclusion, adjacent slots, historical
assignments, refusal of pre-existing overlap, and denied browser-role helper access.
The demo launcher also has a regression test proving a hosted `.env` cannot trigger seed.

Browser authentication checks cover invalid credentials, sign-in, restored sessions,
refresh of expired stored sessions, missing membership, sign-out and workspace
clearing on expiry. They verify UI/SDK behavior with mocked services; they do **not**
verify a real Supabase project's signing keys, email settings, networking or accounts.

The original demo still passes on isolated ports 8002/3002; hosted UI tests use 3001.
Separate Next build directories allow tests alongside the user's development servers.
Existing upstream Starlette/httpx and Alembic configuration deprecation warnings
remain visible. GitHub CI jobs were added but have not been run remotely here.

Remaining integration gates: configure a Supabase project, provision accounts and
runtime credentials, and verify real login/refresh/logout before hosting for users.
No hosted deployment was performed. Approval, invitations, acceptance and workforce
editors remain outside this milestone. These results supersede the historical M0
statements above that identity/RLS/PostgreSQL constraints were unimplemented.

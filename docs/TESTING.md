# SHIFT Adaptive verification

Local verification on 2026-11-07: Python 3.12.14, Node 24.22.2, macOS Chrome.
Dependency versions are locked in uv.lock/package-lock.json. Test data is fictional.

| Check | Actual result |
| --- | --- |
| `uv run pytest -q` | 46 passed, 3 PostgreSQL tests skipped without a disposable PostgreSQL URL |
| `npm run test:calendar` | 4 passed |
| `npm run typecheck` | Passed |
| `npm run build` | Passed (Next.js Webpack production build) |
| Alembic upgrade/check | Passed on SQLite; no model/schema drift |
| OpenAPI export `--check` | Passed |
| `npm run test:e2e` | 3 passed against real local Next/FastAPI/SQLite/CP-SAT requests |

API tests cover qualifications, worker overlap, dependencies, capacity, availability,
private-data boundaries, role/tenant/project scope, budgets, rest/daily hours,
task/setup/contingency buffers, weather specificity/deduplication, partial crews,
timeout distinction, exact absences, stale/expired proposals, rejection/revision,
approval, worker acceptance, reservations, atomic publication, profile/availability
editing, applications, project/task/job creation and cycle rejection.
Concurrent competing SQLite acceptances use separate database sessions/threads:
one reserves successfully and the other gets 409, with no double booking.
JWT tests use a real RSA signature and controlled JWKS key resolver, validating
subject/audience enforcement and rejecting a demo-header role override.

Calendar tests cover full-date comparison across months, subtraction of busy and
confirmed time, clipping multi-day blocks, half-open bounds, local-time conversion
and date navigation. Browser tests cover the complete rain + absence recovery through
manager approval, each worker's acceptance, publication and updated calendars;
mobile profile/availability/application actions; project/task editing and URLs surviving
reload. Desktop/mobile/comparison screenshots are in ignored test-results/.

## PostgreSQL and CI

The PostgreSQL integration suite is skipped locally because this machine has no
PostgreSQL server or Docker. The CI `postgres` job starts disposable PostgreSQL 17,
creates Supabase-like test roles, applies actual migrations, and checks:
- exclusion constraints rejecting overlapping confirmed work;
- RLS/direct-client read denial for private commitments;
- simultaneous competing acceptances and successful final publication.

The CI `api`, `web`, `browser`, and `postgres` jobs are included. Hosted CI status
must be checked after push; configuration alone is not proof the jobs passed.
The service credentials in the workflow belong only to the disposable CI database.
Never point destructive reset/integration tests at a production database.

For local PostgreSQL testing, provide a disposable local database named shift_test:

```sh
export SHIFT_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/shift_test
export SHIFT_TEST_POSTGRES_URL="$SHIFT_DATABASE_URL"
uv run python scripts/prepare_test_postgres.py
uv run alembic upgrade head
uv run pytest apps/api/tests/test_postgres.py -q
```

Browser tests launch isolated servers and `.tmp/e2e.sqlite`; normal shift.sqlite is
not reset by tests. Keep ports 3000/8000 free. Use `npx playwright install chromium`
or set PLAYWRIGHT_CHROME_PATH to an existing browser. Webpack is selected because
Turbopack's CSS subprocess port binding is restricted on this executor.

One upstream Starlette/httpx test-client deprecation warning remains. Native Node
TypeScript tests may emit a module-format detection warning; all assertions pass.
No warning is suppressed to make failing checks appear successful.

## Limits

No hosted Supabase credentials, external live weather feed, background scheduler,
or public deployment was supplied/verified. A local role harness is not authentication;
a configured hosted environment uses JWTs and ignores demo persona headers.
PostgreSQL CI and hosted Supabase verification are distinct: passing a disposable
PostgreSQL test does not verify a real Supabase project. No legal-compliance,
performance, resilience or savings benchmark is asserted.

## Verified hosted CI evidence

[GitHub Actions run 42412789167](https://github.com/jordanantonio/amuse/actions/runs/42412789167)
completed successfully for source commit `99b1299` on 2026-11-07. All four jobs
(`api`, `web`, `browser`, `postgres`) passed. This includes the three real PostgreSQL
integration cases, not just migration configuration. The initial PostgreSQL test
incorrectly expected a worker-scoped response to contain other workers' confirmations;
the corrected test obtains the authorized manager view before completing acceptance.
No privacy restriction was relaxed. Hosted Supabase credentials/sign-in remain a
separate, unverified deployment setup step.

## Public home verification — 2026-11-08

Implemented on `codex/public-home` using the user's Public home (open style) HTML
export as the visual reference. The export's bundled React/runtime is not shipped;
existing local illustrations were reused and electrical/welding/equipment SVGs added.

Executed results:

- `uv run pytest -q`: **113 passed, 3 PostgreSQL tests skipped** (no disposable
  PostgreSQL URL configured for this change).
- `uv run pytest -q apps/api/tests/test_public.py`: **5 passed**, including public
  allowlisted fields, hidden addresses, publication/expiry filters, bounded literal
  search, hosted-mode access and safe post-sign-in destinations. External URLs,
  protocol-relative paths, backslashes and control characters fall back to /home.
- `npm run typecheck` and `npm run build`: passed, including the new Inter font.
- `uv run alembic check` and OpenAPI export `--check`: passed; no schema changes.
- Full Playwright run: all **19 existing regression scenarios passed**, plus three
  new public-home scenarios. The fourth new scenario initially exceeded its
  five-second navigation assertion during the first cold compilation of a contract
  route; its assertion was changed to wait up to 15 seconds for that navigation.
- Focused `npm run test:e2e -- public-home.spec.ts` with installed Chrome:
  **all 4 public-home scenarios passed**, including the selected-contract sign-in
  return path. The existing regression scenarios were unchanged by that test-only fix.
- Live anonymous desktop (1280px) and mobile (390px) checks passed without browser
  runtime errors or document overflow. Screenshots are in ignored `.tmp/`.

Public browser scenarios cover search/trade filters, real carousel scrolling,
contract preview/escape dismissal, local saved IDs surviving reload, no root redirect
for existing sessions, empty/error/retry states, mobile layout, and authentication
before applying. Demo sign-in retains the selected contract for onboarded accounts;
incomplete accounts still go through onboarding. Public access does not expose site
addresses, private schedules, applicant records or credentials.

The browser harness now creates an isolated database/upload directory per run so
old branch migration histories cannot interfere. The preserved V2 local demo DB was
not reset. Development servers are left running on 127.0.0.1:3000 and :8000.
Existing upstream migration/Starlette warnings remain visible; live Google/Supabase
integration and PostgreSQL checks were not repeated for this change. No commits,
pushes or deployment were performed.

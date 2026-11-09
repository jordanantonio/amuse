<img width="1800" height="600" alt="SHIFT: Workforce, in sync" src="https://github.com/user-attachments/assets/379797a8-951e-453d-a6ec-6c5f569c37fe"/>

# SHIFT

**Workforce, in sync.** A hybrid-first workforce operating system for construction,
manufacturing and project work, built at natHacks 2026 (Construction & Manufacturing theme).

SHIFT connects professional profiles, published availability, cross-project
calendars, job postings/applications, and **SHIFT Adaptive**: weather-aware CP-SAT
recovery with manager approval, worker acceptance and atomic publication.

**SHIFT recommends. Authorized humans approve.** Proposed work never silently
replaces a confirmed schedule. No LLM determines feasibility or invents metrics.

# Features

🔐 Sign-In, Onboarding & Demo Personas

- Continue with Google: Google OAuth sign-in with server-side RS256 token verification is built in and switches on once `SHIFT_GOOGLE_CLIENT_ID` and `SHIFT_GOOGLE_CLIENT_SECRET` are set. Until then, the local demo opens a picker of fictional demo accounts instead. Hosted deployments can also use Supabase Auth (see below).
- Guided Role Onboarding: New users choose what they are here for—finding work, hiring a crew, or running a contracting company—and reach their home screen in under a minute.

🪪 Profile & Credential Wallet

- A person, not a record. Worker profiles are essentially a LinkedIn page for the trades with a photo, a headline, a clear availability badge (e.g. "Open to work from Jan 6"), an experience timeline with job photos, tools, trades, languages and past employer reviews.
- Structured Ticket & Certification Tracking: WHMIS, Fall Protection, Forklift, First Aid and trade licenses all tracked with issuer details, expiry dates and uploaded proof documents. All proof documents are served via private 5 minute signed URLs.
- Proactive Expiry Warnings: works out the current status of the credentials (self reported, pending review, verified or expired / expiring in the next 30 days) and warns the worker on their Home screen 30 days before a ticket expires so they never just quietly lose the job.

🏠 Home & Gated "For You" Feed (/)

- Daily At-a-Glance Summary: Starts with a summary card of new matching contracts since yesterday, then a Today Strip with the next booked shift, any pending offers requiring a reply and any certifications that need looking at.
- Qualified & Free Matching Engine: The For You feed will only surface contracts that the worker has every required ticket for and has open calendar blocks to take.
- "Why Am I Seeing This?" Transparency. Every job card will explain the match in plain English (distance in km, start date window, required and bonus cert matches, pay rate versus minimum preference, calendar fit) and will show which further certification would unlock more work.

🏢 Contracting Companies & Crew Proposals

- Crew Rosters & Pooled Credentials: Subs and agencies (e.g. Timberline Framing Crew) will show their full crew roster, each individual's verified trades and tickets and their company wide safety credentials.
- Side by side crew bidding: when a business puts out a crew contract the various contracting companies will submit their proposals in a structured format (crew size, rate, earliest start date and cover note) which the hiring manager can then compare side by side and book just as they would with an individual worker.

📅 Conflict-Free Booking & Calendar Sync

- Saying Yes Books it: an offer is checked for conflicts straight away and the booking is then stamped into the Schedule tab.
- Exclusive vs Part Time blocking: Exclusive (e.g. a 6 month full time role) will block the entire date range and allow one click withdraw from any overlapping applications. Part time roles will only block the specific shift days so the worker can still book work around them.
- Database level double booking prevention: published availability blocks are the single source of truth and are enforced in production via PostgreSQL btree_gist range exclusion constraints. Every booking offers a Google Calendar link and an .ics download; one-tap Google Calendar sync works once Google OAuth is configured.

⚡ Crew Planner (/crew)

- Visual Slot Scheduling & Fatigue Guardrails: The week is displayed as shift slots (e.g. "Packaging line, 8 AM-12 PM, needs 2, forklift preferred"). Clicking on a slot will then rank the available workers by fit, with side by side availability bars and a warning to the manager prior to assigning someone who has worked yesterday, is on their 3rd consecutive day, has no rest between shifts or would be over 40 hours.
- Auto-fill week (Google OR-Tools CP-SAT): fills as many open spots as possible, preferring workers who hold the slot's preferred cert. Hard rules: required certifications, published weekly hours, no overlap with any existing booking, slot headcount, minimum rest, maximum consecutive days and maximum weekly hours. Proposals appear as ghost assignments for the manager to accept.

🌧️ SHIFT Adaptive: Weather & Absence Recovery (/dev/legacy-planner)

- Weather-aware risk monitoring: checks the (simulated) forecast against task-specific safety and operational limits (e.g. outdoor electrical wiring or framing against heavy rain).
- Multi-objective recovery (CP-SAT): generates separately optimized plans for lowest cost, earliest completion and fewest schedule changes, under non-negotiable rules:
  - worker skills, published availability and existing commitments;
  - task dependency DAGs, site capacity, labour budgets and deadlines;
  - rest, daily-hour limits and task/setup/contingency buffers.
- Manager approval, worker acceptance and atomic publication: nothing reaches a confirmed calendar until every affected worker accepts and SHIFT revalidates the plan.

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

Open **http://127.0.0.1:3000** and click **Continue with Google** to pick a fictional
demo account (see `docs/V2.md`). The crew planner is at **/crew** (**/planner** redirects
there), and SHIFT Adaptive weather recovery is at **/dev/legacy-planner**. Reset the
marketplace demo at **/dev/reset**. API documentation: http://127.0.0.1:8000/docs.
Both launchers bind to loopback. Stop with Ctrl+C. SQLite persists to ignored
`shift.sqlite`; startup applies Alembic migrations and idempotently upgrades the
fictional Northline fixture. It does not reset existing work.

The demo week is **November 9–13, 2026, America/Edmonton**, with 12 workers, three
projects, indoor/outdoor tasks, private busy windows and simulated weather. The
persona selector is a local demo harness, not production authentication.

## Try the marketplace and crew planner

1. On **/**, click **Continue with Google** and choose **Ilya** (worker). Open _Why am I
   seeing this?_ on a job card, then **Apply** through the 4-step sheet.
2. Switch to **Rahul** (Prairie Harvest Foods). Under **Work → Applicants**, review
   fit-sorted applicants. Open **Work → Crew planner**, click **Auto-fill week**, then
   **Find a replacement** on the Sunday gap.
3. Switch to **Jordan** (Timberline Framing Crew) for the contracting-company view.
4. Reset everything at **/dev/reset**.

## Try the complete weather recovery

1. Open **/dev/legacy-planner**. As Alex Morgan, open **SHIFT Adaptive** and select
   Eastside facility fit-out.
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

## Team

Built at natHacks 2026 by [Name], [Name], [Name] and [Name].

# SHIFT architecture

## Current implementation
Next.js App Router/TypeScript/Tailwind/Lucide UI → same-origin `/api/v1` proxy →
FastAPI/Pydantic → SQLAlchemy/Alembic → SQLite local or PostgreSQL/Supabase.
Google OR-Tools CP-SAT is the only feasibility/optimization engine. No LLM is used.

The repository originally contained only README/LICENSE at f59048b. Foundation
commit 3239334 established the stack. Adaptive extends that implementation rather
than rebuilding its database or modifying Claude's separate worktree.

## Frontend
`adaptive-workspace.tsx` coordinates operational dashboard, projects, marketplace,
Adaptive and inbox views; `team-calendar.tsx`, `proposal-comparison.tsx`,
`data-editor.tsx`, `auth-gate.tsx` and owned UI primitives are separate components.
`calendar-time.ts` handles full local-date keys, timezone conversion, interval
clipping and subtraction. Query parameters persist view/project/proposal selection
and support sharing/reload/back navigation. Refresh follows writes plus a 15-second
poll; loaded-data age is visible. Calendar state explicitly distinguishes confirmed,
proposed and awaiting acceptance. The superseded read-only workspace was retired.

Public Supabase client configuration enables password sign-in/session refresh.
API calls attach the access token; no service-role or database credentials reach
browser code. The local persona harness remains available only in demo mode.
Next uses supported Webpack dev/build because the execution host restricts
Turbopack's CSS subprocess port binding.

## Database and API contracts
Core tables: organizations, memberships, workers, skills, dated certifications,
published availability, private commitments, worksites, projects, tasks,
dependencies, assignments, job postings, applications, legacy drafts/invitations,
worker absences and audit events.
Adaptive tables: scheduling policies, weather forecasts, recovery proposals,
worker confirmations, slot reservations, approval decisions, scheduling events,
and persisted risk reviews. Legacy draft/invitation tables remain compatible;
Adaptive confirmations/reservations are the new recovery invitation lifecycle.

Requests are explicit Pydantic schemas in inputs.py. Proposal/forecast/dashboard
responses have typed schemas; `packages/contracts/openapi.json` is generated from
FastAPI. Frontend contracts are in `lib/types.ts` and `lib/adaptive-types.ts`.
All API instants are timezone-aware, normalized to UTC; workspace presentation is
America/Edmonton. Intervals are half-open [start,end). Money is integer CAD cents.

## Authorization
Demo headers are a local role-policy harness, not login. In authenticated mode the
API ignores those headers, verifies Supabase asymmetric JWT signatures through
JWKS and checks issuer, audience, expiry, issued-at and subject. Roles and tenant
scope come from server database memberships, never user-editable JWT metadata.
No configured provider or missing/invalid tokens fails closed. Operator tooling
maps existing Supabase Auth users to memberships; account onboarding is not an
unrestricted self-assignment of company privileges.

Workers can update only their own profile/availability/applications/confirmations.
Managers can change only assigned projects; administrators have tenant scope.
Private calendar titles/reasons never enter dashboard or proposal responses.
Workers see only their own proposed slots, not another worker's original plan.

PostgreSQL migrations enable RLS and revoke direct anon/authenticated/PUBLIC table
access. This is an **API-exclusive database boundary**, not browser-side PostgREST
CRUD. The trusted API database role owns/bypasses those policies. Keep its connection
secret. RLS intentionally remains enabled on guard-migration downgrade.

## Atomic recovery
See ADAPTIVE.md for the detailed state machine. All scheduling mutations acquire
a tenant write boundary: SQLite BEGIN IMMEDIATE or PostgreSQL transaction advisory
lock. All writers must retain this convention. Approval/acceptance/publication
compare a canonical scheduling-input fingerprint and rerun CP-SAT with the exact
stored placements forced. Accepted slots are reserved under the same lock.
Publication checks all confirmations and atomically cancels only superseded work,
inserts confirmed assignments, releases reservations and records history.
PostgreSQL additionally uses btree_gist range exclusion constraints to reject
confirmed-worker overlap and reservation overlap within their respective tables.
Cross-table capacity/rest consistency is enforced by the locked validation service.

Supabase service-role clients or database owners can bypass RLS; do not expose
these credentials or use direct client-side scheduling writes. Read replicas cannot
be used for validation. Application API is the supported scheduling writer.

## Solver and weather
Half-hour, non-preemptive optional intervals, shared crew starts, dependencies,
capacity, fixed commitments, qualified availability, private busy windows, rest,
daily hours, task/setup/contingency buffers, weather and hard labour budgets.
Each objective is solved separately. Fixed work, including the freeze window,
remains protected unless a detected disruption and its dependency closure are
included in an explicitly approved project recovery. See ADAPTIVE.md for limitations.

A replaceable WeatherProvider returns source/timestamp-labeled forecasts. The
local provider is deterministic and simulated. Thresholds belong to tasks, not a
generic construction rule. Manual reviews persist risk evidence; a CLI supports
operator-configured cron. No unattended scheduler is installed by default.

## Verification boundary
Local SQLite, signed JWT policy tests, browser workflows and a production web build
are verified. A disposable PostgreSQL CI job covers migrations, RLS rejection,
overlap exclusions and concurrent acceptance/publication. Consult TESTING.md for
its actual execution status. No hosted Supabase account, live-weather provider,
or public deployment is assumed. Equipment, material delays, legal overtime rules,
preemptive/split tasks and resilience benchmarking remain outside this release.

## References
- [Next.js authentication](https://nextjs.org/docs/app/guides/authentication)
- [Supabase signing keys/JWKS](https://supabase.com/docs/guides/auth/signing-keys)
- [Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts)
- [PostgreSQL range exclusions](https://www.postgresql.org/docs/current/rangetypes.html)
- [OR-Tools scheduling](https://developers.google.com/optimization/scheduling/employee_scheduling)

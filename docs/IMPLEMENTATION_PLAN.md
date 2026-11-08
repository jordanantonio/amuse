# SHIFT implementation plan and collaboration board

## Working agreements
Main is the integration branch. Initial changes live on codex/shift-foundation.
No commits, pushes, or merges without authorization. Before concurrent work,
create separate worktrees from an agreed base, claim a task here, and confirm API
contracts. Codex and Claude Code should not edit the same checkout concurrently.
Task ownership below is a proposal for subsequent sessions, not launched agents.

## Milestones
1. **M0: foundation (current):** permanent docs, Next.js/FastAPI monorepo,
   migration-backed models, deterministic fixture, read dashboard/calendar/talent,
   role-scoped demo API, initial real CP-SAT draft and explicit disruption action,
   automated tests and startup guide.
2. **M1: identity and workforce:** Supabase Auth/JWT, memberships/RLS, profile,
   certifications, availability editor and privacy tests. PostgreSQL CI required.
3. **M2: projects and marketplace:** project/task/dependency editor, validation,
   job publication, contractor search, applications and company administration.
4. **M3: recovery transactions:** draft comparison, fingerprint/version checks,
   manager approval, invitation/accept/decline, atomic cross-project reservation,
   persistent audit trail, refreshed worker/manager calendars, repeatable reset.
5. **M4: judge-ready:** full recovery browser test, infeasibility cases, responsive
   calendar/Gantt, accessibility, timezone edges, deployment/auth review, demo script.

## Proposed independent tasks after M0
| ID / proposed owner | Branch | Owned files | Contract / acceptance |
| --- | --- | --- | --- |
| AUTH / Claude | claude/supabase-auth | auth module, supabase migrations, login UI | Verified JWT, tenant/role negative tests, no public demo bypass |
| SOLVER / Codex | codex/solver-hardening | solver.py, solver tests | Crew gaps, cert expiry, DST/travel policy, infeasible/unknown distinction |
| PROJECTS / Claude after AUTH | claude/project-editor | project routes and UI | Valid DAG, deadlines, scoped writes |
| RECOVERY / Codex after AUTH | codex/recovery-transactions | draft/invite service, locking migration | Atomic approval/acceptance with stale-input rejection |
| TALENT / Claude | claude/marketplace | job/application routes and talent UI | Search, apply, invite; qualified eligible candidates |
| CALENDAR / agreed owner | feature/calendar | calendar/Gantt components | Cross-project views, privacy, timezone, keyboard/mobile |

Shared ownership lock: models.py, schemas.py, packages/contracts/openapi.json,
frontend lib/types.ts, and root dependency manifests require coordination before
concurrent changes. Implement additive migrations; never modify an applied migration.

## Current limitations to carry forward
- Demo persona selection is not authentication; local-only, not safe to publish.
- Supabase project, auth, production RLS, and PostgreSQL concurrency constraints
  are not configured or verified in this foundation.
- Initial scheduling is hourly and non-preemptive; it is not a labour-law engine.
- Invitations/approval are modeled but mutations remain a follow-up, not a fake
  acceptance flow. Proposed drafts never update confirmed calendars.
- CRUD editors, applications, full Gantt, and a complete recovery reset walkthrough
  follow foundation review. No claims about optimization performance.

## Definition of ready / done per task
Ready: owner, branch, file boundaries, API contract, dependencies, acceptance cases.
Done: runnable implementation; schema/type changes documented; positive/negative
and privacy tests; appropriate web build/typecheck; recorded actual results;
known gaps; reviewable diff. Report any unrun tests explicitly.

## Foundation handoff (2026-11-06)

Foundation snapshot implemented on `codex/shift-foundation` (commit 3239334, pushed):
- All requested permanent product, architecture, implementation, and Claude docs.
- Next.js/TypeScript/Tailwind dashboard and FastAPI/SQLAlchemy monorepo.
- Alembic relational models, local fixture, OpenAPI export, lockfiles and CI checks.
- Manager, worker, administrator demo personas with server-side policy projections.
- Confirmed calendar, project/task coverage, talent and role search, schedule lab.
- Real CP-SAT draft generation; explicit absence/disruption with audit record;
  draft proposals remain separate from confirmed work. Demo-admin reset.
- 27 API/solver tests and 2 browser tests. See TESTING.md for evidence and limits.

Concrete next-task ownership seams:
- Calendar: `apps/web/src/components/team-calendar.tsx` and `src/lib/display.ts`.
- Overview project rows: `apps/web/src/components/project-card.tsx`.
- Session/UI coordination: `apps/web/src/components/workspace.tsx` (one owner).
- Policy/auth: `apps/api/shift_api/auth.py` and `views.py`.
- Solver: `apps/api/shift_api/solver.py` and solver test additions.
- Before parallel UI features, extract their view from workspace.tsx on one
  agreed branch; avoid simultaneous edits to that orchestration component.

M0 is ready for foundation review; M1–M4 remain open. Do not describe the product
as MVP complete until approval and contractor acceptance work end to end.

## Active Adaptive implementation — 2026-11-07
Owner: Codex, branch `codex/shift-adaptive`. Scope: all API/model/contract changes,
calendar, workspace and new Adaptive views in this checkout. Claude's existing
`claude/ui-polish` worktree is not modified. Do not concurrently edit these files.
Milestones: (1) versioned recovery/acceptance/publish transactions; (2) weather,
buffers and separately optimized alternatives; (3) editing, auth and operational
calendar/worker views; (4) integrated tests, docs, commit and feature-branch push.


## Adaptive handoff — 2026-11-07
Implemented on `codex/shift-adaptive`:
- Exact absences preserve confirmed work; targeted risk/dependency recovery.
- Three CP-SAT objectives, half-hour slots, partial crews, task/setup/contingency
  buffers, project work hours, rest/daily-hour policies and task-specific weather.
- Persistent proposal comparison, approval/revision/rejection, worker confirmations,
  accepted reservations, exact-plan revalidation and atomic publication.
- Tenant write serialization, PostgreSQL exclusion/RLS migrations, Supabase JWT
  verification and browser sign-in support (live credentials not supplied).
- Editable project/task/profile/availability/job flows; applications, withdrawal,
  validated offers; operational overview, date-aware calendar, actual free windows,
  overlays/legend/drawer, mobile worker workspace and shareable URLs.
- Deterministic simulated weather, rolling manual reviews and optional cron CLI.
- Expanded negative/concurrency tests and CI jobs. See TESTING.md for actual results.

Remaining deployment setup: provision Supabase/PostgreSQL credentials and initial
memberships; verify hosted sign-in; configure scheduler only if desired; deployment
review. Remaining product extensions: material/equipment models, jurisdictional
labour/overtime rules, split tasks, delegated crew/company roles, resilience analysis.
No production or performance benchmark is claimed without evidence.

Updated ownership seams: recovery.py/locking.py/adaptive_routes.py are the lifecycle;
solver.py/weather.py are constraint/risk services. UI uses adaptive-workspace.tsx,
team-calendar.tsx, proposal-comparison.tsx, data-editor.tsx, auth-gate.tsx. The old
read-only workspace.tsx is retired. Coordinate these contracts before parallel edits.

## Shift V1 marketplace — 2026-11-08
Branch `claude/shift-v1` (from `codex/shift-adaptive`). P0 phases 1–4 of
Shift_v1_Requirements.md shipped: Google/demo sign-in + onboarding; four-tab shell,
profiles and credential wallets; postings, For You feed and applications; accept with
conflict check, availability blocks, Google Calendar and .ics, Schedule tab. Status per
requirement and open P1/P2 items: docs/V1.md. The crew planner moved to /planner.

# SHIFT implementation plan and collaboration board

## Working agreements
Main is the integration branch. Initial changes live on codex/shift-foundation.
No commits, pushes, or merges without authorization. Before concurrent work,
create separate worktrees from an agreed base, claim a task here, and confirm API
contracts. Codex and Claude Code should not edit the same checkout concurrently.
Task ownership below is a proposal for subsequent sessions, not launched agents.

## Milestones
1. **M0: foundation (shipped):** permanent docs, Next.js/FastAPI monorepo,
   migration-backed models, deterministic fixture, read dashboard/calendar/talent,
   role-scoped demo API, initial real CP-SAT draft and explicit disruption action,
   automated tests and startup guide.
2. **M1: identity and workforce:** Identity/database safety implemented locally;
   live Supabase verification remains. Follow with profile,
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
| AUTH / Codex | codex/identity-database-safety | auth/config, RLS migrations, identity API, login UI, policy tests/CI | Implemented; live Supabase configuration/verification remains |
| SOLVER / Codex | codex/solver-hardening | solver.py, solver tests | Crew gaps, cert expiry, DST/travel policy, infeasible/unknown distinction |
| PROJECTS / Claude after AUTH | claude/project-editor | project routes and UI | Valid DAG, deadlines, scoped writes |
| RECOVERY / Codex after AUTH | codex/recovery-transactions | draft/invite service, locking migration | Atomic approval/acceptance with stale-input rejection |
| TALENT / Claude | claude/marketplace | job/application routes and talent UI | Search, apply, invite; qualified eligible candidates |
| CALENDAR / agreed owner | feature/calendar | calendar/Gantt components | Cross-project views, privacy, timezone, keyboard/mobile |

Shared ownership lock: models.py, schemas.py, packages/contracts/openapi.json,
frontend lib/types.ts, and root dependency manifests require coordination before
concurrent changes. Implement additive migrations; never modify an applied migration.

## Historical M0 limitations
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

Implemented on `codex/shift-foundation`, uncommitted and unpushed:
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
- Project cards: `apps/web/src/components/project-card.tsx`.
- Session/UI coordination: `apps/web/src/components/workspace.tsx` (one owner).
- Policy/auth: `apps/api/shift_api/auth.py` and `views.py`.
- Solver: `apps/api/shift_api/solver.py` and solver test additions.
- Before parallel UI features, extract their view from workspace.tsx on one
  agreed branch; avoid simultaneous edits to that orchestration component.

M0 is shipped; M1 identity/database implementation is recorded below. Workforce
editing and M2–M4 remain open. Do not describe the product
as MVP complete until approval and contractor acceptance work end to end.

## Identity and database safety — implementation complete

Owner: Codex, branch `codex/identity-database-safety`, sequential work only.
Owns auth/config/database, additive RLS migration, identity API/types, login UI,
policy tests/CI and documentation. Contract: GET /api/v1/me returns persona,
organization_id, organization, demo. Hosted requests use verified bearer JWTs;
local demo uses explicit demo mode. No approval/invitation mutations in this task.

Implementation delivered: email/password auth gate and session handling, verified
JWT identity, GET /me, restricted-role/RLS migrations, private-safe scheduling
projections, overlap exclusion, provisioning CLI, PostgreSQL CI and setup guide.
Local demo remains runnable with explicit local mode. Recovery approval and
acceptance are still the next lifecycle milestone. See TESTING.md for actual checks.

Verification (2026-11-08): 49 API tests passed with PostgreSQL enabled; 2 live-demo
browser tests and 3 mocked hosted-auth browser tests passed; web typecheck/build,
SQLite/PostgreSQL schema drift checks and OpenAPI checks passed. Real Supabase
integration and deployment were not performed. No commits or pushes were created.

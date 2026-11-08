# SHIFT — permanent product and development instructions

## Product vision
SHIFT is a hybrid-first workforce operating system for construction, manufacturing,
and project-based employment. One shared workforce graph connects three products:
worker availability and cross-project assignments; a contract job marketplace;
and constraint-based project scheduling. The defining demo is disruption recovery:
a worker becomes unavailable → staffing gap → qualified available contractors →
solver-generated revision → manager approval → contractor acceptance → calendar update.
Build a working application, not a static mockup. Target natHacks 2026.

## Non-negotiable invariants
- Google OR-Tools CP-SAT enforces schedules. An LLM must never decide feasibility.
- Never double-book a worker across projects. Enforce skills, valid certifications,
  published availability, existing commitments, task dependencies, site capacity,
  labour budget, and deadlines. Identify unsupported constraints explicitly.
- Preserve confirmed assignments. Changes require explicit manager approval;
  proposed or invited assignments are never represented as accepted or confirmed.
- Revalidate and atomically reserve slots at invitation acceptance; drafts may stale.
- Infeasibility must return actionable blockers. A solver timeout is UNKNOWN,
  never proof of infeasibility. Do not invent optimization or performance metrics.
- Managers may see published availability, relevant assignments, and opaque busy
  intervals. Never disclose private calendar titles, reasons, clients, or descriptions.
- Authorization belongs on the server and database, never just in the UI. Local
  demo identity is not authentication and must be disabled outside local demos.
- Use fictional demo data. Never commit secrets, credentials, or production data.

## Canonical documentation
Read docs/PRODUCT_SPEC.md, docs/ARCHITECTURE.md, and
 docs/IMPLEMENTATION_PLAN.md before planning or changing contracts. Keep them
consistent with implementation. README.md contains exact startup commands.
Python response models and generated packages/contracts/openapi.json define the
API; apps/web/src/lib/types.ts is the corresponding frontend contract.

## Repository and stack
- apps/web: Next.js App Router, TypeScript, Tailwind, composable shadcn-style UI.
- apps/api: Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic, OR-Tools.
- PostgreSQL/Supabase in production; explicit SQLite local fallback.
- packages/contracts: exported OpenAPI; docs: product, architecture, task ownership.
- No paid API or cloud account required for the foundation's local demo.

## Git and collaboration
Inspect status, branches, remotes, and relevant existing code before editing.
Never develop on main. Use codex/<task> and claude/<task> feature branches.
Do not push, merge, rebase shared history, or delete others' changes without the
user's authorization. Do not create commits unless requested.
Use separate worktrees for concurrent Codex/Claude work, not two agents sharing
one checkout. Claim file ownership and task contracts in the implementation plan
before concurrent work. Read its task board to avoid overlapping modifications.
Independent branches integrate through reviewed PRs; changes to models/contracts
must be coordinated before dependent frontend work.
Do not launch subagents unless the user explicitly delegates work or requests them.

## Implementation discipline
1. Inspect first; preserve unrelated work. State assumptions and scope.
2. Define contracts and lifecycle transitions before implementing UI mutations.
3. Keep runnable vertical slices; expose real loading, empty, and error states.
4. Validate at boundaries, enforce organization/role scope, use transactions.
5. Test scheduling invariants, negative authorization, privacy, and stale state.
6. Run API tests, web typecheck, and web production build for relevant changes.
7. Update docs, record actual commands/results and unresolved gaps. Never claim
   untested hardware, integrations, authentication, deployments, or benchmarks.
8. Prefer ordinary reversible decisions over clarification. Ask when blocked by
   credentials, unclear destructive scope, or consequential product decisions.

## UX
Professional, calm, modern SaaS: Linear's clarity with useful calendar/Gantt views.
Show manager and worker experiences distinctly. Status labels must distinguish
confirmed, invited, proposed, unavailable, and unstaffed. Use accessible contrast,
keyboard controls, responsive layout, clear costs/currency, timezone labels, and
an explicit fictional-demo indicator. No decorative buttons with no behavior.

## Initial scope
This branch is the documentation and runnable foundation, not the completed MVP.
See the implementation plan for shipped work and remaining acceptance criteria.

## SHIFT Adaptive implementation (2026-11-07)
The current product includes weather-aware recovery, manager decisions, worker
confirmations, reservations and publication. Read docs/ADAPTIVE.md before touching
this lifecycle. Never bypass the tenant transaction lock or exact-plan validation
at approval/acceptance/publication. PostgreSQL RLS is API-exclusive; do not grant
direct client access to private tables. Supabase JWT roles come from database
memberships, not client-editable token metadata. Keep demo and authenticated modes
explicitly separate. Retain immutable original assignments and decision history.
Calendar comparisons use full dates and half-open intervals; free time subtracts
all busy and confirmed windows, including multi-day blocks.

## Shift V1 marketplace (2026-11-08)
Product decision: the V1 contractor marketplace (credential wallet, For You feed,
offers, schedule lock + Google Calendar) is now the main product; SHIFT Adaptive
remains a business-side crew planner at /planner. Read docs/V1.md before changing it.
Availability blocks are the source of truth for bookings; Google Calendar only mirrors
them. Never show a site address before an offer, never serve credential documents
except through short-lived signed links, and keep ranking weights in feed_config.py.

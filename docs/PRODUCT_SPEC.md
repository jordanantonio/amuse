# SHIFT product specification

## Purpose and users
SHIFT connects workforce scheduling, project-based hiring, and solver-backed
planning for hybrid, onsite, and remote project work. Initial users are fictional
Alberta construction teams; these are demonstration fixtures, not customer claims.

| Role | Capabilities | Boundary |
| --- | --- | --- |
| Worker | Maintain profile, publish availability, browse roles, apply, review invitations, accept/decline, view own confirmed assignments | Cannot approve schedules or inspect another worker's private calendar |
| Project manager | Create/manage assigned projects, inspect team availability, view conflicts/gaps, generate/approve drafts, invite qualified contractors | Organization and managed-project scope; no private calendar details |
| Company administrator | Organization membership and roles, company projects and jobs, workforce oversight | Organization scope, not platform-wide access |

## MVP data
Worker: skills, certifications with expiry dates, location, hourly rate in integer
CAD cents, employment type, work-mode preferences. Availability is explicitly
published by the worker. Private commitments are separate records; only busy
intervals can leave the worker's access boundary. Projects contain tasks with
duration, required skills/certifications, dependency edges, worker count, earliest
start, deadline, work mode, site capacity, and optional labour budget.

## Core workflows
1. **Availability and assignment:** worker publishes time windows. Confirmed
   assignments across projects are combined in the worker calendar. Manager sees
   team-wide availability and appropriate assignment summaries. Any overlap is
   rejected server-side, including concurrent acceptance attempts.
2. **Project planning:** manager creates project and dependency graph, validates
   cycles and deadlines, requests CP-SAT draft. Draft has a versioned input
   snapshot, proposed worker/time assignments, cost, and actual solver status.
3. **Marketplace:** company posts a scoped contract role. Contractor profiles can
   be searched by qualifications, location, rate, and available windows. Workers
   apply; managers invite candidates. Invitations reserve nothing permanently.
4. **Disruption recovery:** manager explicitly marks a confirmed worker assignment
   as disrupted; it remains in audit history. A staffing gap appears. Candidate
   discovery respects qualifications and availability. Solver proposes a revision
   preserving other confirmed assignments. Manager approves the draft. Contractors
   receive invitations; only acceptance creates confirmed assignments. Calendars
   refresh from server data; gaps remain visible until staffed.
5. **Infeasible plan:** show validated input errors, tasks without eligible workers,
   and resource/deadline constraints. Do not relax safety/qualification constraints
   silently. Distinguish infeasible, invalid input, and solve timeout.

## Lifecycle
Task: unstaffed → proposed coverage → invited coverage → confirmed coverage.
Draft: draft → approved or rejected; stale inputs require regeneration.
Invitation: pending → accepted, declined, or expired. Acceptance revalidates all
constraints in a transaction. Approval is not contractor acceptance.
Assignment: confirmed → completed, cancelled, or disrupted, via authorized actions.
A disrupted assignment is historical evidence, not a live slot reservation.

## Demonstration scenario
Fictional Northline Works is fitting out an Edmonton fabrication facility. An
assigned electrician withdraws from a rough-in task. Manager records disruption,
sees the gap, generates a replacement draft, reviews contractor/rate and timing,
approves it, then switches to that fictional contractor to accept. Other confirmed
work is preserved. Reset restores the known dataset and is demo-only.

## UX and acceptance
Navigation: Overview, Team calendar, Projects, Talent marketplace, Schedule lab,
My schedule (worker). Dashboard shows actual counts and assignments from the API.
A calendar uses named days, local timezone, and assignment state. Planning has a
before/after view, explicit approval and invitation actions, blockers, and costs.
Do not publish fabricated utilization, savings, or optimization speed metrics.

MVP acceptance: workers cannot overlap across projects; unavailable or unqualified
workers cannot be assigned; private details never reach manager responses; stale
or unauthorized approvals fail; no draft becomes confirmed without acceptance;
infeasibility is explained; demo reset is repeatable; persisted data survives
restart; key flows pass API and browser checks. Responsive and keyboard-usable UI.

## Foundation versus full MVP
The foundation implements relational models, seed data, read dashboards, role-scoped
API projections, and an initial CP-SAT recovery draft. Follow-up tasks deliver
Supabase authentication/RLS, full project/profile/availability editing, marketplace
application flows, versioned approval and acceptance transactions, PostgreSQL
concurrency enforcement, and a complete repeatable recovery walkthrough.

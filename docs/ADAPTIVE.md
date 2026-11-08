# SHIFT Adaptive

## Lifecycle and transaction boundary

Generate → pending_approval → awaiting_confirmation → ready_to_publish → published.
Rejected, revision_requested and expired proposals are not publishable. A manager
can return an approved plan for revision, releasing accepted reservations. Every
approval decision is appended with actor, comment and time; no edit/delete API
exists for the audit trail.

Generation records the original confirmed schedule, candidate replacements,
objective, actual solver result, measured costs/completion/buffers, source input
fingerprint and 24-hour expiry. Confirmed work remains unchanged after generation,
approval and acceptance. Only an authorized publication cancels the specifically
superseded assignments and inserts the new confirmed assignments atomically.

All scheduling writers serialize by tenant: SQLite BEGIN IMMEDIATE; PostgreSQL
transaction advisory lock. Accepted workers acquire slot reservations under that
same lock. Approval, acceptance and publication compare scheduling input hashes
and validate the *exact stored placements* with CP-SAT. They do not silently swap
the approved plan for a newly optimized one. A conflicting reservation or stale
input produces 409. Expired reservations are ignored by solving and cleaned up
inside the next write transaction. PostgreSQL also excludes overlapping confirmed
assignments and overlapping reservations at the database layer.

## Solver semantics

30-minute, non-preemptive slots; at most a 14-day project horizon. Required crew
members share a task interval. Partially fixed crews can be filled without moving
their existing members. Published availability, qualifications through end time,
work modes/location, private commitments, absences, accepted reservations,
dependencies, site capacity, project working hours, daily hours, overnight rest,
setup/transition time, contingency and budget are hard constraints.

Setup/transition is conservatively required between shifts even at the same site.
It is not a geographic route/travel-time estimate. Tasks are not split overnight.
The model is not a complete jurisdiction-specific labour-law engine. Equipment,
materials, overtime pay rules and arbitrary split shifts remain outside this model.

Task percentage buffers round upward to the half hour and are included in planned
labour time/cost. Existing fixed shifts are not extended retroactively. Contingency
moves the latest permitted planned finish earlier than the project deadline. It
is protected; the solver does not silently consume it to force feasibility. Reported
consumption is therefore zero unless future policy explicitly allows it.

Confirmed assignments are fixed at all horizons, which also protects the configured
near-term freeze window. They become eligible for movement only when a detected
absence/weather disruption and its dependent tasks are explicitly included in a
recovery proposal. Publishing still requires the assigned project's manager/admin
and all affected new workers. Other projects' work is never cancelled by a recovery.

Three CP-SAT objectives are solved separately: lowest labour cost, earliest feasible
completion, and fewest changes to prior worker/time assignments with completion/cost
tie-breaks. Results may coincide. OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN are preserved;
a timeout is not called infeasible. Blockers are eligibility prechecks and declared
joint constraints, not a claim of a minimal unsatisfiable core.

## Weather and rolling review

`WeatherProvider` is replaceable. The default deterministic provider produces
14 local-date forecast windows per project, with source, fetched time and explicit
simulated labeling. Heavy rain affects the first two local days. Each task has its
own optional thresholds for rain probability, precipitation, wind, and temperature.
Indoor tasks without policies are not constrained by generic weather rules.
Forecast refresh compares material fields before adding a scheduling event.

Manual review persists risks from weather, absences and staffing gaps. Dependency
closure identifies affected tasks within that project. The CLI can be invoked by
cron, but no background scheduler is installed or claimed. Materials/equipment
risks require future resource models; no resilience score or predicted savings is
fabricated.

## Editing and privacy

Workers edit their own profile/availability, apply/withdraw, report exact absences,
and respond only to their own confirmations. Availability/profile edits cannot
silently invalidate confirmed work; they return a conflict and direct users to the
absence/recovery flow. Managers edit only their projects and see published windows
plus opaque busy intervals, never private calendar labels. Worker proposal responses
are reduced to their own slots/confirmations and omit other workers' original plan.

Project/task editors validate intervals, dependency scope and cycles. Confirmed task
requirements cannot be overwritten through a task edit. Applicant offers run the
same solver with that worker constrained to the selected task, then require the
same approval/acceptance/publishing lifecycle.

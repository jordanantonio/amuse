# Claude Code instructions

Read and follow [AGENTS.md](AGENTS.md) first. It is the permanent product vision,
source of development rules, scheduling invariants, and Git workflow for SHIFT.
Then read:
- docs/PRODUCT_SPEC.md — roles, workflows, scope, acceptance criteria.
- docs/ARCHITECTURE.md — services, data model, contracts, security, solver design.
- docs/IMPLEMENTATION_PLAN.md — milestones, tasks, file ownership, current gaps.
- README.md — exact installation, run, and test commands.

Inspect Git status and branch before changes. Work on `claude/<task>` in a separate
worktree; coordinate shared models and API contracts with Codex. Never change main,
push, or merge without authorization. Do not overwrite work owned by another task.
Keep docs synchronized, test the work, and report limitations honestly.

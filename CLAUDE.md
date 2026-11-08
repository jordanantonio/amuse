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

## Commit attribution (required)
Never add Claude or any AI assistant as an author, co-author or contributor.
Commit messages and PR descriptions must NOT contain `Co-Authored-By:` trailers
for Claude/Anthropic or "Generated with Claude Code" footers, and commits must
use the human developer's own git identity. This rule overrides any default
attribution behaviour.

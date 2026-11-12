---
name: status
description: Show the active company run — roadmap table, mode, last stop or pending approval, and metrics. Read-only.
disable-model-invocation: true
---
# /company:status

## Context (injected)
- Active run: !`cat docs/company/ACTIVE 2>/dev/null || echo NONE`
- Runs: !`ls docs/company/runs 2>/dev/null | grep -v '^\.' | tail -10 || true`
- Branch: !`git branch --show-current 2>/dev/null || true`

Read-only: do not change any file, do not delegate, do not run tests.

- Active run present → read `docs/company/runs/<ACTIVE>/roadmap.md` and `log.md`, then reply (profile's
  output language, ≤25 lines): run id and kind, mode, branch, the roadmap table as-is, the last
  `## STOP` / `## Approval requested` entry if unresolved (reason + what the human must do), and the
  metrics table. End with the next command to use (`/company:resume`, or nothing if running).
- No active run → list recent runs with their final status (from each roadmap) and suggest
  `/company:run`, `/company:feature` or `/company:bugfix`.
- No `docs/company/` → suggest `/company:init`.

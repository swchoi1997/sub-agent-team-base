---
name: resume
description: Resume the active company run after a stop, an approval, or a lost session — re-reads roadmap and log, checks the stop reason, and continues the feature loop.
disable-model-invocation: true
allowed-tools: Bash(printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH)
argument-hint: "[note about what was resolved]"
---
# /company:resume

Note from the human: $ARGUMENTS

## Context (injected)
- Subagent depth: !`printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH || echo "unset (default 3)"`
- Active run: !`cat docs/company/ACTIVE 2>/dev/null || echo NONE`
- Branch: !`git branch --show-current 2>/dev/null || true`
- Uncommitted changes: !`git status --porcelain 2>/dev/null | head -20`
- Diff stat: !`git diff --stat 2>/dev/null | tail -15`

Read and follow `${CLAUDE_PLUGIN_ROOT}/playbooks/common-rules.md` and
`${CLAUDE_PLUGIN_ROOT}/playbooks/orchestrator.md`. Talk to the human in the profile's output language.

1. Active run NONE → say there is nothing to resume (suggest `/company:status` or a new flow); stop.
2. Read `R/request.md` (kind), `R/roadmap.md`, `R/log.md` (mode, `## Plan approved`, last `## STOP`
   or `## Approval requested`). Make sure the current branch is `company/<R_ID>`; if not, ask before switching.
3. Mode: use the log's mode unless the current depth no longer allows it (then flat, and log it).
4. Where to continue:
   - No `## Plan approved` → go to the plan/spec review step of the run's kind.
   - Last stop is an approval → ask the approval question again (orchestrator §C), then continue.
   - Other stop → show the reason and ask the human whether it is resolved (use their note if given).
     Not resolved → stop again (no new log entry needed).
   - Feature in `진행` → continue its dev step (pass the diff stat to dev).
   - Feature in `개발완료` / `QA중` / `재작업N` → keep the changes and **restart QA** for it
     (rework counter stays as logged).
   - Feature in `멈춤` after QA failed twice → only continue if the human gives direction
     (e.g. revised criteria → planning revision, or one more rework explicitly approved).
5. Log `## Resumed` (time, decision). Show the goal sentence again (orchestrator §F) when features remain.
6. Continue the run's flow: feature loop (§D), then that kind's wrap-up (`/company:run` §5,
   `/company:feature` §4, or `/company:bugfix` §4).

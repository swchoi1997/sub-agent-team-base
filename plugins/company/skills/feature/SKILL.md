---
name: feature
description: Add one feature to an existing product through the company — impact analysis and a short spec, a quick human approval, then development, QA and a commit.
disable-model-invocation: true
allowed-tools: Bash(printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH)
argument-hint: "\"<feature request>\""
---
# /company:feature

Request: $ARGUMENTS

## Context (injected)
- Subagent depth: !`printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH || echo "unset (default 3)"`
- Profile: !`test -f docs/company/profile.md && echo present || echo MISSING`
- Active run: !`cat docs/company/ACTIVE 2>/dev/null || echo NONE`
- Existing runs: !`ls docs/company/runs 2>/dev/null | grep -v '^\.' | tail -5 || true`
- Branch: !`git branch --show-current 2>/dev/null || true`
- Uncommitted changes: !`git status --porcelain 2>/dev/null | head -15`

Read and follow `${CLAUDE_PLUGIN_ROOT}/playbooks/common-rules.md` and
`${CLAUDE_PLUGIN_ROOT}/playbooks/orchestrator.md`. Talk to the human in the profile's output language.

## 0. Preflight
Same as `/company:run` step 0 (profile, no active run, clean tree, mode, run id with slug,
branch `company/<R_ID>`, `request.md` with kind `feature`, `log.md`, `ACTIVE`, baseline).

## 1. Short spec
Planning step in **`feature` mode** (lead mode: `company:plan-lead`; flat: plan-lead playbook yourself).
No market research.

## 2. ★ Spec approval (human)
Show the 5-line spec (scope / acceptance criteria / risks / out of scope / features) and the roadmap
table. Approve → log `## Plan approved` and continue. Revise → planning revision → ask again.

## 3. Feature loop
Orchestrator §D for the 1–3 features, with the stop protocol for every stop.
For more than one feature, show the goal sentence (§F) once after approval.

## 4. Wrap-up
Update `docs/company/product.md`, clear `ACTIVE`, commit docs (`docs(<R_ID>): wrap up`), and report:
what changed, commits, metrics, branch. No marketing by default; if the human asks, run
`company:mkt-marketer` task `release-notes`. Never push.

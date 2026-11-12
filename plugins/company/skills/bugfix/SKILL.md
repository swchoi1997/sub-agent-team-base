---
name: bugfix
description: Fix a bug through the company — QA reproduces it with a failing test first, development finds the root cause and fixes it, QA verifies, then commit. No planning step.
disable-model-invocation: true
allowed-tools: Bash(printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH)
argument-hint: "\"<bug description>\""
---
# /company:bugfix

Bug: $ARGUMENTS

## Context (injected)
- Subagent depth: !`printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH || echo "unset (default 3)"`
- Profile: !`test -f docs/company/profile.md && echo present || echo MISSING`
- Active run: !`cat docs/company/ACTIVE 2>/dev/null || echo NONE`
- Existing runs: !`ls docs/company/runs 2>/dev/null | grep -v '^\.' | tail -5 || true`
- Branch: !`git branch --show-current 2>/dev/null || true`
- Uncommitted changes: !`git status --porcelain 2>/dev/null | head -15`

Read and follow `${CLAUDE_PLUGIN_ROOT}/playbooks/common-rules.md` and
`${CLAUDE_PLUGIN_ROOT}/playbooks/orchestrator.md` (sections A–C, E). Talk to the human in the
profile's output language.

## 0. Preflight
Same as `/company:run` step 0, with kind `bugfix`, slug prefixed `fix-`, and a one-row roadmap:
`| B1 | <bug> | - | 재현 테스트가 수정 전 실패하고 수정 후 통과, 기준선 대비 새 실패 0 | - | 대기 | - |`.
If the bug description is too vague to reproduce, ask the human for steps/expected/actual first.

## 1. Reproduce (QA)
Delegate to `company:qa-tester`: write a **failing test that reproduces the bug** (test files only),
run it, and confirm it fails for the reported reason. Evidence → `R/qa/B1.md` section 2.
Cannot reproduce → report to the human with what was tried (stop protocol).

## 2. Fix (development)
Lead mode: `company:dev-lead` with the bug, the reproduction test and `R/qa/B1.md`.
Flat mode: pick the owning role from the failing area and profile paths, delegate to that `company:dev-*`.
Instruction: follow systematic debugging — write the root cause to `R/log.md` (`## Root cause`)
before fixing; minimal fix; run the full test command.

## 3. Verify (QA)
QA step (qa-lead playbook by mode) with acceptance criteria from the B1 row: reproduction test passes,
negative/regression coverage, no new failures vs baseline, review + risk audit.
Fail → rework (max 2) → else stop protocol.

## 4. Commit
Orchestrator §D steps 6–9 (commit gate yourself, commit `fix(<R_ID>): <summary>`, update roadmap and
log, print the table). Clear `ACTIVE`. Report root cause, fix, test evidence, commit. Never push.

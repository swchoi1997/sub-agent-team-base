---
name: run
description: Run a full company project — the planning team writes the PRD and roadmap, the human reviews once, then each feature goes through development, QA and a commit until the roadmap is done. For services or large changes.
disable-model-invocation: true
allowed-tools: Bash(printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH)
argument-hint: "\"<service or change request>\""
---
# /company:run

Request: $ARGUMENTS

## Context (injected)
- Subagent depth: !`printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH || echo "unset (default 3)"`
- Profile: !`test -f docs/company/profile.md && echo present || echo MISSING`
- Active run: !`cat docs/company/ACTIVE 2>/dev/null || echo NONE`
- Existing runs: !`ls docs/company/runs 2>/dev/null | grep -v '^\.' | tail -5 || true`
- Branch: !`git branch --show-current 2>/dev/null || true`
- Uncommitted changes: !`git status --porcelain 2>/dev/null | head -15`

You are the head office. Read and follow, in this order:
1. `${CLAUDE_PLUGIN_ROOT}/playbooks/common-rules.md`
2. `${CLAUDE_PLUGIN_ROOT}/playbooks/orchestrator.md` — mode, delegation, approvals, feature loop, stop protocol
Talk to the human in the profile's output language (default Korean).

## 0. Preflight
- Request empty → ask for it and stop.
- Profile MISSING → tell the human to run `/company:init` and stop.
- Active run is not NONE → show its status (as `/company:status`) and suggest `/company:resume`; stop.
- Uncommitted changes → ask the human to commit or stash first (do not do it for them); stop.
- Mode from depth (orchestrator §A).
- Run id `R_ID` = next 3-digit number + short ASCII kebab slug of the request (e.g. `001-todo-service`).
  Run folder `R = docs/company/runs/<R_ID>`.
- `git switch -c company/<R_ID>`.
- Create `R/request.md` (kind `run`) and `R/log.md` (templates in `${CLAUDE_PLUGIN_ROOT}/templates/`),
  write `R_ID` to `docs/company/ACTIVE`.
- **Baseline**: if the profile has a verified test command, run it and write `R/baseline.md`
  (pre-existing failures). New project or unverified → write "기준선 없음 (사유)".

## 1. Planning
Run the planning step in **`run` mode** — lead mode: delegate to `company:plan-lead`; flat mode: run
`${CLAUDE_PLUGIN_ROOT}/playbooks/plan-lead.md` yourself. Handle any `Needs approval` per orchestrator §C.

## 2. ★ Plan review (human)
Show, concisely: PRD summary (≤10 lines), the roadmap table, the risk items to be approved during the
loop, the stack proposal (new project), and open questions from `Needs decision`. Ask: approve / revise.
- Revise → planning revision with the human's notes → back to 2.
- Approve → log `## Plan approved` (time, notes). For a new project, record the approved stack in
  `profile.md` (`확정 — F0에서 명령 채움`). Then show the goal sentence (orchestrator §F) and tell the human:
  "자리를 비우실 거면 이 문장으로 `/goal`을 설정하세요. 바로 이어서 진행합니다." and continue.

## 3. Marketing (background)
Start `company:mkt-marketer` **in the background** with tasks `positioning` then `launch-plan`
for run folder `R`. Do not wait for it.

## 4. Feature loop
Run orchestrator §D until no runnable feature remains. After each feature print the roadmap table and
continue without asking. Use the stop protocol (§E) for every stop.
If the run started as a new project, after F0 passes update `profile.md` commands and QA run profile
from what F0 produced (verify by running them) and include that in F0's commit.

## 5. Wrap-up (all features 완료)
1. `company:mkt-marketer` task `release-notes` (wait for it; also make sure the background marketing
   task finished).
2. ★ **Marketing review**: show a 5-line summary of positioning, launch plan and release notes with
   their paths; ask approve / revise. Revise → send notes to the marketer → ask again.
3. Update `docs/company/product.md` (new features, paths). Append a summary to `R/log.md`
   (metrics table totals). Clear `docs/company/ACTIVE` (delete the file).
4. Commit the docs: `docs(<R_ID>): wrap up run`. Never push.
5. Final report: features done, commits (`git log --oneline` of the run branch), metrics, branch name,
   and "push/PR은 직접 진행하세요".

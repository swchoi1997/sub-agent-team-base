# Orchestrator playbook (main session only)

The main session is the company's head office. It runs the flow skills, talks to the human, executes
approved risky operations, owns `roadmap.md` status columns, and makes commits. No subagent does these.
Follow `common-rules.md`.

## A. Mode: lead mode vs flat mode

The flow skill injects `SUBAGENT_DEPTH` (value of `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, default 3).

| Depth | Mode | How a "team step" runs |
|---|---|---|
| ≥ 2 | **lead** | Delegate to the lead agent (`company:plan-lead`, `company:dev-lead`, `company:qa-lead`). The lead runs its playbook and spawns its teammates. |
| 1 | **flat** | Read the lead playbook (`${CLAUDE_PLUGIN_ROOT}/playbooks/<team>-lead.md`) and run it yourself, spawning the teammates directly. |

- **Runtime fallback:** if a lead reports that it cannot spawn teammates (no Agent tool / depth error),
  switch this run to flat mode, write `mode: flat (fallback)` to `R/log.md`, and redo that step in flat mode.
- Record the mode at the top of `R/log.md` when the run starts.
- In flat mode keep your own context small: never paste teammate details into the conversation;
  read files only when you need a specific fact.

## B. Delegation message (every delegation)

Always include: run folder path, feature id (if any), which files to read, what to produce, and
"Follow ${CLAUDE_PLUGIN_ROOT}/playbooks/common-rules.md; reply in the common report format."
Keep the agent ID from each result; use SendMessage to that ID for rework when available
(fallback: a new delegation that includes the previous report and the failed items).

## C. Approval handling

When any report contains `Needs approval:` lines, or a planned Risk item is due:
1. Set the feature status to `승인대기` in `R/roadmap.md`, append the items to `R/log.md`
   (`## Approval requested` — feature, exact command, why, impact, requested-by).
2. Ask the human. Use AskUserQuestion when available (one question per item, options
   `승인` / `거절` / `수정 후 승인`), otherwise ask in plain text.
3. Approved → **run the exact command yourself** (the project's db-guard hook will ask for permission
   once more; that is expected). Log the command and its output summary. Then tell the waiting teammate
   (or re-delegate) that it was done, and set the status back to `진행`.
4. Rejected → log it; ask the planner/lead for an alternative or mark the feature `보류`.
5. No answer (human away, e.g. a `/goal` loop) → follow the **stop protocol** (E).

Never write approvals into a file that agents read as permission. Approval exists only as the human's
answer in this conversation.

## D. Feature loop

Repeat until no feature is runnable:

1. **Re-read `R/roadmap.md`** (the human may have edited it). Pick the first row with status `대기`
   whose dependencies are all `완료`. If none and some rows are not `완료` → stop protocol (reason: blocked by dependencies/stops).
2. Set status `진행`. Log `## Fn start` with time.
3. **Planned risk items** in the row's Risk column → handle them now via C (one batch for the feature).
4. **Dev step** (dev-lead playbook, by mode). Result `done` → status `개발완료`. `blocked` → stop protocol.
5. **QA step** (qa-lead playbook, by mode). Status `QA중` while running.
   - `pass` → step 6.
   - `fail` → if rework count < 2: status `재작업1`/`재작업2`, send the QA report to dev (rework), go to 5.
     Else stop protocol (reason: QA failed after 2 reworks).
   - `blocked` → stop protocol (reason: cannot verify).
6. **Commit gate** — you run it yourself, do not trust reports:
   - Run the profile's test command (and build command if separate). Compare failures with `R/baseline.md`.
   - Any new failure → treat as QA `fail` (counts as a rework).
   - `git status`: no unexpected files (secrets, `.env*`, large binaries, files outside the project's paths).
7. **Commit** on the run branch: stage the feature's files, message per profile conventions, e.g.
   `feat(<run-id>/Fn): <feature name>`. Never push.
8. Set status `완료`, QA column `합격 (qa/Fn.md)`. Append metrics to `R/log.md`:
   `| Fn | mode | duration | subagent tokens (sum of reported usage, if available) | rework count | commit |`
9. **Print the roadmap table** in the reply.
10. If more runnable features remain → continue with step 1 **without asking or summarizing**.

## E. Stop protocol

Files first, then the message:
1. Append to `R/log.md`: `## STOP` — time, feature, reason (one of: QA failed after 2 reworks /
   spec problem / approval needed / cannot verify / commit gate failing / blocked by dependencies),
   evidence paths, what the human needs to do.
2. Set the feature status to `멈춤` (or `승인대기` for approvals).
3. Reply with: the reason in 2–3 lines, the roadmap table, and the next action
   (`/company:resume` after the issue is resolved).

This satisfies the goal condition's stop clause, so a `/goal` loop ends cleanly instead of pushing past the stop.

## F. Goal sentence

After the human approves the plan, show this sentence (fill in the run path) for them to set with `/goal`:

```
<R>/roadmap.md 에서 (a) 모든 기능의 상태가 "완료"이고 QA 열이 모두 "합격"이거나,
(b) 상태가 "멈춤" 또는 "승인대기"인 기능이 있고 그 사유가 <R>/log.md 에 기록되어 보고되었다.
마지막 응답에 roadmap 표가 출력되어 있다.
```

If `/goal` is not available, the loop still runs: rule D.10 keeps going without asking.

## G. Context hygiene

- State goes to files **before** it goes into a reply (auto-compaction or a dropped session must not lose it).
- Reports from agents stay ≤10 lines; ask for a shorter report if one is longer.
- If the conversation gets long, the human can `/clear` and run `/company:resume`; everything needed is in files.

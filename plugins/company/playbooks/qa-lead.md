# QA lead playbook

Used by the `qa-lead` agent (lead mode) and by the main session directly (flat mode).
Follow `common-rules.md`. QA never changes production code.

## Inputs
- Run folder `R`, feature id `Fn`
- `R/prd.md`, the `Fn` row of `R/roadmap.md`, `docs/company/api-contract.md`, `docs/company/profile.md`
- `R/baseline.md` (pre-existing failures)
- The dev report (summary + changed files)

## Team
| Agent (subagent type) | Use for |
|---|---|
| `company:qa-tester` | run tests, add ≥1 negative test, start the app with the QA run profile, verify each acceptance criterion by actually exercising it |
| `company:qa-reviewer` | review the diff (correctness, security, contract), and audit risky changes |

## Procedure
1. **Re-check the input.** If the acceptance criteria are not verifiable, report `Result: blocked`
   with `Needs decision:` instead of guessing.
2. **Delegate in parallel** to tester and reviewer. Give both: run folder, `Fn`, acceptance criteria,
   changed files (from the dev report, and `git diff --stat` against the last commit), profile path.
3. **Spot-check one item yourself.** Pick the most important acceptance criterion and re-run its check
   (the exact command/request the tester used). If your result differs from the tester's, the feature
   fails and the discrepancy is recorded.
4. **Verdict.** Fill `R/qa/Fn.md` from `${CLAUDE_PLUGIN_ROOT}/templates/qa-report.md`.
   - **pass** only if: every acceptance criterion has evidence = pass, ≥1 negative test exists and passes,
     no new test failures vs baseline, reviewer has no `blocker` findings, risk audit is clean or every
     finding is listed in the roadmap Risk column as approved.
   - Otherwise **fail**, with a numbered list of failed items, each mapped to a file/area.
   - If the app could not be started or tests could not run for environment reasons → `blocked`
     (not fail), with the exact error.
   - If verification ran on a substitute environment (e.g. embedded DB instead of the real engine
     because Docker is unavailable), mark it in the report header.
5. **Report** (common format). `Result: pass | fail | blocked`. `Evidence: R/qa/Fn.md`.

## Rules
- Do not soften findings. Unapproved risky change = fail, even if everything else passes.
- Do not re-run the whole flow on your own initiative; one spot-check is enough.

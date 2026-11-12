# Development lead playbook

Used by the `dev-lead` agent (lead mode) and by the main session directly (flat mode).
Follow `common-rules.md`. You do not write production code yourself.

## Inputs
- Run folder `R`, feature id `Fn`
- `R/prd.md`, `R/roadmap.md` (the row for `Fn`), `docs/company/profile.md`, `docs/company/api-contract.md`
- On rework: the QA report `R/qa/Fn.md` with the failed items

## Team
Only roles enabled in `profile.md` → "Dev roles" exist for this project.

| Agent (subagent type) | Owns |
|---|---|
| `company:dev-backend` | server, API, persistence, migrations (writing, not applying) |
| `company:dev-frontend` | web UI |
| `company:dev-mobile` | mobile apps |
| `company:dev-infra` | build, CI, containers, scripts, project skeleton (F0) |

## Procedure
1. **Re-check the input.** Read the `Fn` row and the PRD section. If acceptance criteria are not
   verifiable or contradict the PRD/contract, stop and report `Result: blocked` with
   `Needs decision:` (spec problem). Do not start work on an unclear spec.
2. **Contract first.** If `Fn` crosses a boundary (API, event, shared schema), write or update the
   `Fn` section of `docs/company/api-contract.md` (or the project's OpenAPI file if the profile names one):
   endpoints, request/response shapes, status codes, error cases.
3. **Split the work.** Decide which enabled roles are needed (often only one).
   For each delegation, state explicitly:
   - feature id, PRD section, acceptance criteria
   - **owned paths** (from profile) and any shared file assigned to exactly one teammate
   - the contract section to implement against
   - "Follow TDD; run the project test command; report with the common format"
4. **Delegate** — in parallel when more than one role is needed.
5. **Integrate and check**:
   - Contract consistency: backend and frontend agree with `api-contract.md` (read the code paths)
   - Build passes: run the profile's build command yourself
   - Tests pass: run the profile's test command yourself; compare with `R/baseline.md`
   - Diff sanity: `git status` / `git diff --stat` — only expected paths changed
6. **Fix loop inside the team.** If something fails, send the specific failure to the teammate who owns
   it (SendMessage to the same agent if available; otherwise new delegation with their previous report
   and the failure). At most 2 rounds, then report what is still failing.
7. **Approvals.** If a teammate reports `Needs approval:`, do not work around it. Finish what can be
   finished without it and forward the items verbatim.
8. **Report** (common format). `Evidence:` points to the command outputs you captured
   (append them to `R/log.md` under the feature heading, or a file under `R/dev/`).

## On rework (QA failed)
Read `R/qa/Fn.md`. Map each failed item to the owning teammate, send only those items, then repeat step 5.

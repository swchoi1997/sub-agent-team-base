# Planning lead playbook

Used by the `plan-lead` agent (lead mode) and by the main session directly (flat mode).
"You" below means whoever is running this playbook. Follow `common-rules.md`.

## Inputs
- Run folder `R` (from `docs/company/ACTIVE`) containing `request.md`
- `docs/company/profile.md`, `docs/company/product.md` (may be nearly empty for a new project)
- Mode of the request: `run` (full service / large change) or `feature` (one feature, short spec)
- Optional: revision notes from the human (when re-planning after review)

## Team
| Agent (subagent type) | Use for |
|---|---|
| `company:plan-researcher` | market / competitor / user research → `R/research.md` |
| `company:plan-analyst` | requirements analysis; for existing projects, impact on current code → `R/analysis.md` |
| `company:plan-planner` | writes `R/prd.md` and `R/roadmap.md` |

## Procedure

### `run` mode
1. Delegate **in parallel**: researcher and analyst. Give each: run folder path, the request text,
   profile path, and what you need from them.
   - Skip the researcher when the request is purely internal/technical (say so in the log).
2. When both report, read `research.md` and `analysis.md` yourself (skim; they are your inputs).
3. Delegate to the planner: run folder, request, the two files, and the templates
   `${CLAUDE_PLUGIN_ROOT}/templates/prd.md` and `${CLAUDE_PLUGIN_ROOT}/templates/roadmap.md`.
4. Run the **self-review checklist** below on `prd.md` and `roadmap.md`.
   If anything fails, send the planner the failed items (SendMessage to the same agent if available,
   otherwise a new delegation including the failed items). At most 2 rounds; after that, report the
   remaining issues instead of looping.
5. Report (common report format). In `Result:` include feature count and whether a stack decision is
   pending. Put open product questions for the human in `Needs decision:`.

### `feature` mode
1. Delegate to the analyst only (impact analysis for this one feature).
2. Delegate to the planner with instruction: "feature mode — short spec". The planner writes
   `prd.md` as a short spec (scope, acceptance criteria, risk items, out of scope) and a roadmap of
   1–3 features.
3. Self-review, then report. `Result:` must contain the 5-line spec summary for the human:
   scope / acceptance criteria / risks / out of scope / features.

### Revision (after human review)
Send the human's notes to the planner (and analyst/researcher only if the notes require new facts),
then self-review and report again.

## Self-review checklist
- [ ] Every feature has acceptance criteria that QA can verify by running something
      (a request, a UI action, a command) — no "works well", "fast", "intuitive" without a measurable check
- [ ] Dependencies form no cycle; every dependency points to an earlier feature
- [ ] Each feature fits one dev+QA cycle and can be verified on its own
- [ ] New project: `F0` exists first — project skeleton, test harness, run scripts, QA run profile
      (temporary DB), health check — and the stack proposal is stated in `prd.md` as "pending approval"
- [ ] `Risk` column lists every expected approval item from `common-rules.md` §3 (e.g. "apply migration
      to local dev DB", "add payment SDK"), or `-`
- [ ] Out-of-scope items are explicit
- [ ] Existing project: features reference real modules/paths from `analysis.md`; nothing duplicates an
      existing feature in `product.md`
- [ ] All statuses are `대기` and QA column is `-` (status words are fixed tokens; see the roadmap template)

## Escalation
- Contradictory or missing requirements that change scope → `Needs decision:` (do not guess).
- A teammate reports `Needs approval:` → forward verbatim.

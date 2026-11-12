---
name: init
description: Set up the company structure in the current project — analyze the codebase (or detect a new project), write docs/company/profile.md, add the CLAUDE.md section, and install the db-guard hook. Run once per project; use --upgrade after a plugin update.
disable-model-invocation: true
allowed-tools: Bash(printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH)
argument-hint: "[--upgrade]"
---
# /company:init

Arguments: $ARGUMENTS

## Context (injected)
- Profile: !`test -f docs/company/profile.md && grep -o 'template_version: [0-9]*' docs/company/profile.md | head -1 || echo MISSING`
- Git: !`git rev-parse --is-inside-work-tree 2>/dev/null || echo NOT_A_GIT_REPO`; branch !`git branch --show-current 2>/dev/null || true`
- Tracked files (sample): !`git ls-files 2>/dev/null | grep -v '^docs/company/' | head -40`
- Subagent depth: !`printenv CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH || echo "unset (default 3)"`
- Plugin template version: 1

Follow `${CLAUDE_PLUGIN_ROOT}/playbooks/common-rules.md`. Talk to the human in Korean.

## 0. Guard
- Not a git repo → tell the human to `git init` first and stop.
- Profile exists and no `--upgrade` → say it is already initialized, show `/company:status`, stop.
- `--upgrade` → go to section U.

## 1. Environment and project type
- Check tools (run them; they are read-only): `docker info` (available?), `which jq python3 java node`.
- **New** if there is no application source (only README/LICENSE/docs/config). Otherwise **existing**.

## 2. Analyze (existing projects)
Inspect build and config files directly (package.json, build.gradle(.kts), pom.xml, settings.gradle,
pyproject.toml, requirements*.txt, go.mod, Cargo.toml, Gemfile, docker-compose*.yml, Dockerfile,
.github/workflows, application*.yml/properties, .env.example, existing CLAUDE.md / AGENTS.md / CONTRIBUTING).
For a large repo you may use one Explore subagent for the sweep. Determine:
- stack per area, and which **dev roles** apply (backend / frontend / mobile / infra) with owned paths
- build / test / lint / run commands and their working directories
- databases: every DB the app or tests connect to, and whether each is **temporary**
  (Testcontainers, H2/embedded, test-only container) or **permanent**
- a **QA run profile**: how to start the app against a temporary DB, with and without Docker.
  If none exists, write `미정 — F0/첫 기능에서 dev-infra가 추가` and note it.
- conventions: formatter/linter, commit message style, comment language, API contract source (OpenAPI?)

**Verify commands safely.** Before running a test command, check the test configuration's DB target.
If tests would connect to a permanent DB, do **not** run them; record `미검증 — 영구 DB 사용` and tell
the human. Otherwise run build and test once and record the result (pass/fail counts, date).
Never run migrations, seeds or DB writes during init.

## 3. Write files
1. `docs/company/profile.md` from `${CLAUDE_PLUGIN_ROOT}/templates/profile.md`, filled in.
   New project: stack `미정`, roles left as a proposal, commands `미정 (F0 후 채움)`.
   Record the environment facts above under 기본 → 모드 메모.
2. `docs/company/product.md` (existing: current features from routes/pages/modules; new: empty template).
3. `docs/company/api-contract.md` from the template (existing project with OpenAPI: link to it).
4. `docs/company/runs/.gitkeep`.
5. **CLAUDE.md**: insert `${CLAUDE_PLUGIN_ROOT}/templates/claude-md-section.md` between the
   `<!-- company:start -->` / `<!-- company:end -->` markers. If the markers exist, replace only that block.
   If CLAUDE.md does not exist, create it with just this block. Never change other content.
6. **db-guard hook**:
   - copy `${CLAUDE_PLUGIN_ROOT}/project-hooks/db-guard.sh` to `.claude/hooks/db-guard.sh` and `chmod +x` it
   - merge `${CLAUDE_PLUGIN_ROOT}/project-hooks/settings.snippet.json` into `.claude/settings.json`:
     keep every existing key; add the PreToolUse entry only if a hook with command containing
     `db-guard.sh` is not already there (use jq or python3 to merge; never overwrite the file blindly)
   - self-test: pipe `{"tool_name":"Bash","tool_input":{"command":"psql -c \"drop table x\""}}` into the
     hook and confirm the output contains `"permissionDecision":"ask"`; pipe a SELECT and confirm no output.

## 4. Confirm with the human
Show a short summary (≤15 lines): type, stack, enabled dev roles + paths, commands with results,
QA run profile, DB list (temporary vs permanent), anything `미정`/`미검증`, depth → expected mode
(≥2 lead mode, 1 flat mode), Docker availability. Ask what to correct (AskUserQuestion if available).
Apply corrections to `profile.md`.

Then ask whether to commit the setup now (recommended — `/company:run` needs a clean working tree).
If yes: `git add docs/company CLAUDE.md .claude/hooks/db-guard.sh .claude/settings.json` and commit
`chore: set up company profile` (follow the project's commit convention). Never push.

Suggest next steps: `/company:run "<서비스 요청>"`, `/company:feature "<기능>"`, `/company:bugfix "<버그>"`.
Recommend optional tools: Context7 MCP, Playwright MCP, the stack's LSP plugin.

## U. Upgrade (`--upgrade`)
Compare the profile's `template_version` with the plugin's (1). If equal, say so and stop.
Otherwise: add new fields from the current template without losing values, refresh the CLAUDE.md block
and `.claude/hooks/db-guard.sh`, re-run the hook self-test, show the diff, and ask before committing.

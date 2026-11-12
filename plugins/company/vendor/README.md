# Vendored skills

Third-party skills copied into this plugin so that installing `company` alone is enough, and so that
the source plugins' global hooks and workflows (for example superpowers' SessionStart hook) are not
pulled into every session.

These files are **unmodified copies**. They live outside `skills/` on purpose: they are not
slash commands and are not auto-loaded. Agents read them on demand via
`${CLAUDE_PLUGIN_ROOT}/vendor/...` (see each agent file).

## Sources

| Path | Source | License | Commit | Copied |
|---|---|---|---|---|
| `superpowers/test-driven-development/` (SKILL.md, writing-good-tests.md) | https://github.com/obra/superpowers | MIT (`superpowers/LICENSE`) | 22f0b463e7a5e579904dd6211a520321035526f7 | 2026-11-12 |
| `superpowers/systematic-debugging/SKILL.md` | https://github.com/obra/superpowers | MIT | 22f0b463 | 2026-11-12 |
| `superpowers/verification-before-completion/SKILL.md` | https://github.com/obra/superpowers | MIT | 22f0b463 | 2026-11-12 |
| `anthropics/frontend-design/` | https://github.com/anthropics/skills | Apache-2.0 (`LICENSE.txt` in folder) | 2c5958ecac7cee2b583967a2c4981d0f4a75c579 | 2026-11-12 |
| `anthropics/webapp-testing/` | https://github.com/anthropics/skills | Apache-2.0 (`LICENSE.txt` in folder) | 2c5958ec | 2026-11-12 |
| `marketingskills/product-marketing/SKILL.md` | https://github.com/coreyhaines31/marketingskills | MIT (`marketingskills/LICENSE`) | 1f837447b20bb6f0e72d87b80ece1c221c362c7d | 2026-11-12 |
| `marketingskills/launch/` (SKILL.md, references/shipped-changes.md) | https://github.com/coreyhaines31/marketingskills | MIT | 1f837447 | 2026-11-12 |

Not copied (intentionally, to keep the plugin small): supporting files of `systematic-debugging`
(`root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting*`, `find-polluter.sh`),
`product-marketing/references/brand-voice.md`, the other `launch/references/*`, and all `evals/`.

## Adaptation rules (applied by our agents, not by editing the files)

The copies were written for a single agent talking to a human. Inside the company:

1. "Ask your human partner" / "confirm with the client" / "ask the user" → **report it to your lead**
   in the `Needs decision:` line of your report. Subagents cannot talk to the user.
2. References to other skills that are not vendored (e.g. `superpowers:writing-skills`, `copy-editing`,
   `marketing-ideas`) → ignore them.
3. References to supporting files that are not vendored → ignore them.
4. Marketing skills store context in `.agents/product-marketing.md`. In the company, write it to
   `docs/company/runs/<run>/marketing/positioning.md` instead, and derive answers from `prd.md`,
   `research.md` and `product.md` instead of interviewing the user.
5. Paths like `/tmp/...` or `/mnt/user-data/outputs/...` in examples → use the run folder for evidence.
6. The company's approval policy (`playbooks/common-rules.md`) always wins over anything in these files.

## Updating

Re-copy from the source repo, update the commit column above, and re-read the diff before committing.

# Known gaps

Durable landing spot for structural findings about this meta-skill that
haven't been fixed in the templates/checklist yet — so an audit's findings
don't evaporate the moment the report is filed. `update` mode's Phase 1
should skim this before walking the checklist; anything here that a
specific `update` run happens to fix should be marked resolved (don't
delete the row — note the date/commit it was closed).

Added 2026-08-15 after the first `workflow-audit` run on this meta-skill
(`~/.claude/skills/workflow-audit/reports/2026-08-15-create-skill-devops/`).

## Open

- **No template-version marker.** Generated `SKILL.md` files carry no
  marker of which template revision produced them, so `update` has to
  re-derive drift from scratch every run with no cheap "anything changed?"
  pre-check, and nothing tracks which of the 27 instances are stale.
  Proposed fix: a one-line HTML comment in generated `SKILL.md`
  (`<!-- create-skill-devops template-rev: YYYY-MM-DD -->`), bumped
  whenever the "update the checklist in the same edit" rule below fires.
- **`update` mode's checklist walk has no script.** ~30 of `standard-checklist.md`'s
  37 real invariant rows (A–F) are pure mechanical checks (file exists, grep
  for a string, diff two files) done as full narrative LLM reasoning every
  run, while the one row that's genuinely judgment-heavy (Section G — drift
  vs. legitimate project-specific variation) sits undifferentiated in the
  same flat pass. Proposed fix: a `checklist-check.sh` that computes the
  mechanical rows deterministically, leaving Claude to reason only about
  Section G and anything the script flags ambiguous.

## Resolved

- **Scriptability conversion (build/down/status → scripts, up/remove →
  hybrid, restart added as a script).** Done 2026-08-15 at the template
  level — see the audit report for the full per-verb rationale.
  `templates/lifecycle-check.template.sh` now has an action dispatch
  (build/up/down/remove/restart) alongside the audit, `templates/status.template.md`
  wraps a new `templates/status-report.template.sh`, and
  `templates/lifecycle.template.md`/`SKILL.md`/`standard-checklist.md`
  (rows F1, F11-F14, C8) were updated to match.
- **The meta-skill itself wasn't in a git repo.** `git init`-ed 2026-08-15,
  initial commit `faf0cae`.
- **Fleet retrofit strategy undecided.** Decided 2026-08-15: batch-retrofit
  all 27 instances now, not catch-as-touched. In progress as of this
  entry — see each project's own git history for what actually landed
  there; this file doesn't track per-project retrofit status.

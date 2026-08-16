# Team roster grammar — canonical rules

Single source of truth for the shape of a substrate team. Skills and the
`team-of-agents` factory point here instead of restating this. Aligned with
`ember-substrate/vocabulary.md` (2026-08-12), which owns the org-level terms;
this file owns the team-level and agent-level conventions.

## Org structure (owned by ember-substrate/vocabulary.md — summary only)

**Substrate** (the whole company-wide AI organization) → **Division** (a broad
function area, e.g. Viability, Marketing) → **Team** (`team-<name>`: one
invocable unit with its own roster and a single deliverable) → **Foundation
team** (owned by no division, callable by any — e.g. `team-research`).

## Roles inside a team

- **Triage** — first in the pipeline; normalizes and profiles the input, gates
  on blocking ambiguity before any evaluation happens. Usually mechanical →
  low model tier.
- **Specialist** — one evaluator, one lens; run in parallel with the other
  specialists. Read-only plus a written findings file.
- **Validator** — independent, blind cross-check of specialists' claims
  against real evidence. For high-stakes output, run twice, blind to each
  other (the product-analyst double-blind pattern): nothing survives on one
  agent's opinion.
- **Judge / judge panel** — 2–3 independent votes, spawned **only when
  confidence is LOW or a call is genuinely ambiguous** (the em-judge pattern).
  One vote per invocation; no consensus-building between judges; the lead may
  override a majority with recorded reasoning.
- **Lead / synthesizer** — merges all findings into one reviewable
  deliverable, owns the team's run-log and decision log. Judgment-heavy →
  high model tier; the under-provisioned lead is the audit layer's most-cited
  failure.
- **Adversarial critic** (optional standing role) — reviews the finished work
  hunting for what a green result hides (build-reviewer,
  story-completeness-critic, spec-forge-staff-critic).

## Roster invariant (countable)

A workflow file's **roster** is the static multiset of quoted `agentType`
literals in that file, derived by
`grep -o "agentType: *'[^']*'" <file> | sort | uniq -c`. It is stable under
the runtime `runSet` trim (`director-of-engineering` narrowing which agents
actually run in `direct`/`fast` mode) and does not miscount a fan-out over an
array (a loop over an `EVALUATORS`-style array is one `agent(` call site but
several distinct `agentType` values). Any acceptance bar asserting "the
checker count is unchanged" means **this multiset is unchanged**, re-derived
at the time of the claim — never transcribed from an earlier count, and never
conflated with the separate, smaller quantity of `agent(` call sites in the
file (a loop body is one call site producing several roster entries).

Live baseline, `2026-08-16-catalog-digest-step-wiring`, re-derive at build
time rather than trust this table:

| file | roster multiset (distinct `agentType` count) | `agent(` call sites |
|---|---|---|
| `team-build/workflows/build.js` | 7 | 7 |
| `team-qa/workflows/qa.js` | 8 | 8 |
| `team-intake/workflows/intake.js` | 8 | 5 (4 evaluators share one loop-body call site) |
| `team-status/workflows/status-scan.js` | 2 distinct (`status-scanner`, `status-lead`) | 3 |

## Conventions every roster follows

- **Single writer.** Exactly one named role holds Edit/Write for each owned
  artifact (archivist, scribe, lead); everyone else proposes. The human gate
  sits between proposal and write.
- **Least-privilege tools.** Specialists default read-only; tool scope is
  declared in agent frontmatter and is itself an auditable surface.
- **Right-sized models.** Each agent declares a model **tier** matched to its
  work — mechanical → cheap/fast, synthesis/adversarial → strongest,
  implementation → mid. Recommend tiers, not model names, so the roster
  survives model churn. Absence of a `model:` line (inherit) is a choice —
  make it deliberately.
- **Agent files live in the registry** — `~/.claude/agents/` (personal) or
  `<project>/.claude/agents/` (project-scoped) — never inside the skill dir,
  with a `<team>-<role>` name prefix as the grouping convention.
- **Generated teams carry the marker** `<!-- team-of-agents-generated: v1 -->`
  right after SKILL.md frontmatter; hand-built teams that borrow the train
  discipline say so explicitly in their training-log header.
- **Agent-or-script is a standing question.** Before adding a roster seat,
  ask whether the step is a fixed, rule-based transform — if so it's a script
  the orchestrator runs, not an agent (the scriptability lens).

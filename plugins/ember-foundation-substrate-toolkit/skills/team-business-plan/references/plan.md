# plan

## Step 0 — Resolve target and output

1. Get the target as an already-evaluated item: a slug (or path) under the
   current project's `viability/` folder that contains a `verdict.md`. If the user names
   something with no viability folder, don't guess — list the folders that
   do have verdicts and ask which one (or point her to `team-viability
   evaluate` first).
2. Output directory: default to
   `<project-root>/viability/<target-slug>/business-plan/` — the plan
   lives beside the verdict it was built on.
3. If `<output-dir>/business-plan.md` already exists, show the user the prior
   plan's row (from `~/.claude/skills/team-business-plan/memory/run-log.md`) and ask whether this is a genuine
   re-plan (the verdict or evidence changed) or she wants the old plan
   as-is.

## Step 1 — Triage and the verdict gate

Invoke `bizplan-triage` with the target's viability folder and the output
directory. It writes `brief.md` with a **verdict-gate status**:

- **HALT** (no `verdict.md`) — stop here. Tell the user: run `team-viability`'s
  `evaluate` on this target first, then come back to `plan`. Do not let any
  specialist improvise a viability assessment.
- **HALT-PENDING-OVERRIDE** (verdict was DON'T BUILD) — stop and ask the user
  explicitly whether she really wants a business plan for a DON'T BUILD
  target. Proceed only on her explicit yes, and record her reason in the
  brief.
- **HALT-PENDING-GO-AHEAD** (verdict was NEEDS MORE EVIDENCE) — stop and
  ask the user explicitly: plan anyway (every named evidence gap carries
  forward as a standing risk in the plan), or gather the missing evidence
  first. Proceed only on her explicit choice.
- **PASS** (BUILD, or a split verdict with a BUILD component) — continue.
  For split verdicts the brief states exactly which component(s) the plan
  covers; confirm with the user if the brief flagged that as ambiguous.

**Recording a HALT-PENDING resolution.** When a halt requires the user's
explicit answer, the orchestrating session (never a subagent — `bizplan-triage`
does not re-run) captures her answer by appending a `## Gate resolution —
recorded by the orchestrator, <date>` section to the bottom of `brief.md`
itself, stating exactly what she chose (scope, go-ahead/override, and any
conditions she accepted). This section must exist in `brief.md` before Step 2
starts — the specialists read it from there, not from a separate memory or a
prompt fragment. Never proceed on an assumed yes, and never let the answer
live only in chat history where a specialist can't see it.

## Step 2 — Specialist fan-out (parallel)

One message, three agents, each given the brief path and output directory:

- `bizplan-offering` — reads the brief and the viability run's
  `supporting/product.md` + `verdict.md`, writes `supporting/offering.md`.
- `bizplan-financial` — reads the brief, the `team-research` dossier it
  points to, and the viability run's `supporting/market.md`, writes
  `supporting/financial.md`.
- `bizplan-gtm` — reads the brief, the dossier, and the viability run's
  `supporting/market.md` + `supporting/stakeholder.md`, writes
  `supporting/gtm.md`.

## Step 3 — Judge

Invoke `bizplan-judge` with all three `supporting/*.md` files and
`brief.md`. It writes `judgment.md`: an honest investor-skeptic attempt to
break the combined plan, or an explicit statement that no real objection
holds up.

## Step 4 — Lead synthesis

Invoke `bizplan-lead` with `brief.md`, all three `supporting/*.md` files,
`judgment.md`, the viability `verdict.md` path, and `~/.claude/skills/team-business-plan/memory/run-log.md`
(read first, for prior-plan context on this same target). It writes
`business-plan.md` and appends a row to `~/.claude/skills/team-business-plan/memory/run-log.md`.

## Report back to the user

- The plan's core bet, in one sentence
- Plan confidence, and why
- The judge's strongest surviving objection (or that the pass was clean)
- The top risk / open evidence gap
- Path to `business-plan.md`
- Whether this target had a prior plan in `~/.claude/skills/team-business-plan/memory/run-log.md`, and what
  changed if so

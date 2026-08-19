---
name: team-viability
argument-hint: "evaluate <target>"
description: >
  Viability Division's flagship team. Given a target (a product idea, or a
  path to a real product/repo/artifact), produces a verdict on whether it's
  worth building or continuing to invest in: BUILD / DON'T BUILD / NEEDS MORE
  EVIDENCE. `evaluate` runs the full pipeline (triage → parallel specialist
  fan-out covering product, market, and stakeholder lenses → adversarial
  judge → lead synthesis) and depends on `team-research`'s dossier for the
  external market/competitor/monetization half rather than duplicating it.
---

<!-- team-of-agents-generated: v1 -->

# Team Viability

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Ember's Viability Division flagship team. Shape: **pipeline** — triage →
parallel specialist fan-out → adversarial judge → lead synthesis into a
single verdict.

It exists because of a gap `team-research` found in a prior-art pass over
published business-viability evaluation systems: they either look outward
at the market or inward at
a text description of an idea — almost none genuinely ingest a real
product/codebase AND combine that with real external research into one
synthesized verdict. `viability-product` is built specifically to fill that
gap; `viability-market` deliberately does NOT re-do `team-research`'s job,
it consumes `team-research`'s dossier instead.

This is a **user skill** — usable from any project; run outputs land in the
current project. Vocabulary: a **team** is a skill-orchestrated pipeline of
subagents; **specialists** each work one lens in parallel; a **judge**
adversarially challenges their combined case; a **lead** synthesizes the
final artifact and owns the team's memory.

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-viability/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-viability/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

## Command routing

| Argument | Command |
|---|---|
| `evaluate <target>` | Full pipeline over `<target>` → a verdict at `<output-dir>/verdict.md` — `references/evaluate.md` |
| *(none)* | Ask what target to evaluate (an idea description, or a path to a real product/repo) and where to save the report |

## The team (user agents, installed at `~/.claude/agents/`)

| Agent | Role |
|-------|------|
| `viability-triage` | Normalizes the target into a brief. Checks whether a `team-research` dossier already exists for this target's topic; flags if `team-research` needs to run first. |
| `viability-product` | Specialist. **The differentiator.** Actually ingests the real product/code/artifact — genuine maturity, feasibility, technical completeness. Not a description-based guess. |
| `viability-market` | Specialist. Reads `team-research`'s dossier (market size, competitors, monetization) and synthesizes implications specific to this target — does not re-research from scratch. |
| `viability-stakeholder` | Specialist. High-level stakeholder/investor lens grounded in IDEO's Desirability-Feasibility-Viability framework — would this be compelling, and why. |
| `viability-judge` | Adversarially challenges the combined case from all three specialists — tries to argue against the verdict before it's allowed to stand. |
| `viability-lead` | Synthesizes into `verdict.md`: **BUILD / DON'T BUILD / NEEDS MORE EVIDENCE**, with rationale and confidence. Owns `~/.claude/skills/team-viability/memory/run-log.md`. |

> **How to invoke each role:** these are registered subagent types (user
> scope) — launch each with `subagent_type: "<name>"`. If a name isn't
> available as a subagent type, fall back to `general-purpose` and paste
> the role brief from `~/.claude/agents/<name>.md`.

## `evaluate`

1. Resolve the target and output directory (ask if not given). Default
   output: `<project-root>/viability/<target-slug>/` in the current project.
2. `viability-triage` → `brief.md`. If no `team-research` dossier exists yet
   for this target's topic, **stop and tell the user `team-research` needs to
   run first** — don't let `viability-market` research from scratch, that
   duplicates a whole other team's job.
3. **Parallel fan-out**: `viability-product`, `viability-market`,
   `viability-stakeholder` each write `supporting/{product,market,stakeholder}.md`.
4. `viability-judge` reads all three → `judgment.md` — challenges the
   combined case, doesn't just rubber-stamp it.
5. `viability-lead` reconciles everything → `verdict.md`, updates
   `~/.claude/skills/team-viability/memory/run-log.md`.
6. Report back in chat: the verdict, confidence, the strongest point for and
   against, and the path to `verdict.md`.

Full procedure in `references/evaluate.md`.

## Conventions

- **Never let `viability-market` re-research the market from scratch** — its
  whole point is to consume `team-research`'s existing dossier. If none
  exists, that's `team-research`'s job to produce first, not this team's.
- **`viability-product` must look at the real artifact**, not a description
  of it — that's the entire reason this team exists instead of just reusing
  a published idea-validator.
- **The judge is not a rubber stamp** — it must genuinely attempt to argue
  against the verdict the specialists lean toward; if it can't find a real
  counter-argument, it says so plainly rather than inventing a weak one.
- **Memory**: `~/.claude/skills/team-viability/memory/run-log.md` (one row per
  evaluated target, read first by the lead so a re-evaluation recognizes
  "evaluated before, verdict was X, what's changed") and
  `~/.claude/skills/team-viability/memory/decisions.md` (numbered, standing
  calls — create the first entry the first time a real standing decision
  comes up; don't pre-populate speculative ones). Always use this full,
  skill-anchored path — a bare `memory/run-log.md` reference previously
  resolved inconsistently (once to this file, once to a stray
  `viability/memory/run-log.md` that forked with a different schema and
  missing entries) and the two had to be manually reconciled.
- **`supporting/*.md` field shapes are a public contract.** `team-business-plan`'s
  specialists (`bizplan-offering`, `bizplan-financial`, `bizplan-gtm`) read
  `supporting/product.md`, `market.md`, and `stakeholder.md` directly and
  depend on their field names (Maturity assessment, Feasibility assessment,
  etc. — see each specialist agent's own Output format section). Keep those
  field names stable, or update `team-business-plan`'s specialists in the
  same change.

## Adding to the team

A new specialist lens gets its own file in `supporting/`, gets wired into
Step 3's parallel fan-out, and gets added to what `viability-judge` and
`viability-lead` read. Keep the judge and lead steps unchanged — they
operate on however many specialist files exist.

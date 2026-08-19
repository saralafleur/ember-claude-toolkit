---
name: team-business-plan
argument-hint: "plan <target>"
description: >
  Viability Division's business-planning team, downstream sibling of
  team-viability. Given a target that team-viability has already evaluated,
  produces a high-level business plan: offering & MVP, market & positioning,
  plan-level go-to-market, financial model, milestones, and risks. `plan`
  runs the full pipeline (triage → parallel specialist fan-out covering
  offering, financial, and gtm lenses → adversarial investor-skeptic judge →
  lead synthesis) and depends on team-viability's verdict and team-research's
  dossier rather than re-doing either team's work.
---

<!-- team-of-agents-generated: v1 -->

# Team Business Plan

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Ember's Viability Division business-planning team. Shape: **pipeline** —
triage → parallel specialist fan-out → adversarial judge → lead synthesis
into a single business plan.

It answers the question that follows `team-viability`'s: viability answers
*"should we build this?"*; this team answers *"it's a BUILD — what's the
plan?"*. It consumes the viability run's artifacts (`verdict.md`,
`supporting/*.md`, `judgment.md`) and the `team-research` dossier those were
built on — it never re-evaluates viability and never re-researches the
market.

This is a **user skill** — usable from any project; run outputs land in the
current project. Vocabulary: a **team** is a skill-orchestrated pipeline of
subagents; **specialists** each work one lens in parallel; a **judge**
adversarially challenges their combined case; a **lead** synthesizes the
final artifact and owns the team's memory.

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-business-plan/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-business-plan/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

## Command routing

| Argument | Command |
|---|---|
| `plan <target>` | Full pipeline over `<target>` → a plan at `<output-dir>/business-plan.md` — `references/plan.md` |
| *(none)* | Ask which evaluated target to plan (list the current project's `viability/*/verdict.md` candidates) |

## The team (user agents, installed at `~/.claude/agents/`)

| Agent | Role |
|-------|------|
| `bizplan-triage` | Ingests the completed viability run. Enforces the verdict gate: no verdict → halt; DON'T BUILD → the user's explicit override required; NEEDS MORE EVIDENCE → the user's explicit go-ahead required, gaps carried forward as risks. Normalizes into a planning brief. |
| `bizplan-offering` | Specialist. MVP scope, staged roadmap, differentiation — grounded in the viability run's real-artifact product assessment. |
| `bizplan-financial` | Specialist. Revenue model, pricing, cost structure, rough unit economics — from the `team-research` dossier's monetization findings; never re-researches them. |
| `bizplan-gtm` | Specialist. Segments, positioning, channel strategy at business-plan altitude only — execution detail is the Marketing Division's future `team-gtm`'s scope. |
| `bizplan-judge` | Adversarial investor-skeptic. Attacks the combined plan — pricing, channels, assumed-away product gaps, silently dropped evidence gaps — before it's allowed to stand. |
| `bizplan-lead` | Synthesizes into `business-plan.md`: one coherent plan with confidence and risks. Owns `~/.claude/skills/team-business-plan/memory/run-log.md`. |

> **How to invoke each role:** these are registered subagent types (user
> scope) — launch each with `subagent_type: "<name>"`. If a name isn't
> available as a subagent type, fall back to `general-purpose` and paste
> the role brief from `~/.claude/agents/<name>.md`.

## `plan`

1. Resolve the target's viability folder and output directory (ask if not
   given). Default output: `<project-root>/viability/<target-slug>/business-plan/`
   — the plan lives beside the verdict it was built on.
2. `bizplan-triage` → `brief.md`. **Verdict gate:** on HALT, stop and tell
   the user `team-viability` needs to run first. On HALT-PENDING-OVERRIDE
   (DON'T BUILD) or HALT-PENDING-GO-AHEAD (NEEDS MORE EVIDENCE), stop and
   ask the user explicitly — never proceed on an assumed yes.
3. **Parallel fan-out**: `bizplan-offering`, `bizplan-financial`,
   `bizplan-gtm` each write `supporting/{offering,financial,gtm}.md`.
4. `bizplan-judge` reads all three plus the brief → `judgment.md` — attacks
   the combined plan, doesn't just rubber-stamp it.
5. `bizplan-lead` reconciles everything → `business-plan.md`, updates
   `~/.claude/skills/team-business-plan/memory/run-log.md`.
6. Report back in chat: the plan's core bet, confidence, the judge's
   strongest surviving objection, the top risk, and the path to
   `business-plan.md`.

Full procedure in `references/plan.md`.

## Conventions

- **Never plan an unevaluated target** — no `verdict.md`, no plan. That's
  `team-viability`'s job to produce first, not this team's to improvise
  (D-001).
- **Specialists consume upstream artifacts, never redo upstream work** —
  no re-assessing the product, no re-researching the market or
  monetization. Narrow gap-closing lookups only, rare not routine (D-002).
- **`bizplan-gtm` stays at plan altitude** — detailed go-to-market
  execution belongs to the future `team-gtm` (Marketing Division), and the
  plan says so explicitly wherever it defers (D-003).
- **The judge is not a rubber stamp** — it must genuinely attempt to break
  the plan; if it can't find a real objection, it says so plainly rather
  than inventing a weak one.
- **Self-reported metrics are never load-bearing** — inherited from
  team-viability's D-004; applies to every projection, milestone, and
  positioning claim in the plan.
- **Memory**: `~/.claude/skills/team-business-plan/memory/run-log.md` (one row per planned target, read first
  by the lead so a re-plan recognizes "planned before, built on verdict X,
  what's changed") and `~/.claude/skills/team-business-plan/memory/decisions.md` (numbered, standing calls —
  append new ones as they're actually made; never delete a superseded
  decision, mark it superseded).

## Adding to the team

A new specialist lens gets its own file in `supporting/`, gets wired into
Step 3's parallel fan-out, and gets added to what `bizplan-judge` and
`bizplan-lead` read. Keep the judge and lead steps unchanged — they operate
on however many specialist files exist.

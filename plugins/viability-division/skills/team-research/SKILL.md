---
name: team-research
argument-hint: "research <topic-or-description>"
description: >
  Ember Substrate's foundation research team — not owned by any one division,
  callable by any of them. Given a topic (a product idea, a market, a
  competitor space), produces a sourced research dossier: market size,
  existing competitors/solutions, monetization patterns in that space, and
  any evidence that contradicts the working assumption. `research` runs the
  full pipeline (triage → parallel scout fan-out → comparator →
  independent validator → lead synthesis) and writes a resumable dossier
  other teams (team-viability, team-gtm) can build on.
---

<!-- team-of-agents-generated: v1 -->

# Team Research

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Ember Substrate's foundation team. Shape: **pipeline** — triage → parallel
specialist ("scout") fan-out → comparator → independent validator → lead
synthesis into a single dossier.

It exists because "just ask an agent to research this" tends to produce
confident-sounding claims with no real sourcing, and doesn't survive being
asked twice. This team grounds every claim in scored external evidence,
reconciles conflicts instead of smoothing them over, and independently
verifies the claims are actually sourced (not hallucinated) before they're
allowed into the dossier other teams will trust.

This is a **personal, cross-project skill** — usable from any division/team,
not tied to one codebase. Vocabulary: a **team** is a skill-orchestrated
pipeline of subagents; **specialists** each work one angle in parallel; a
**validator** independently cross-checks the reconciled findings; a **lead**
synthesizes the final artifact and owns the team's memory.

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-research/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-research/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

## Command routing

| Argument | Command |
|---|---|
| `research <topic>` | Full pipeline over `<topic>` → a dossier at `<output-dir>/dossier.md` — `references/research.md` |
| *(none)* | Ask what topic to research and where to save the dossier |

## The team (first-class agents, installed globally at `~/.claude/agents/`)

| Agent | Role |
|-------|------|
| `research-triage` | Normalizes the raw topic into a structured research brief → `brief.md`. Flags and strips any proprietary/internal specifics before anything goes external (see Conventions). |
| `research-scout` | Specialist. Fan-out, one instance per angle (market size, competitors, monetization models — see `references/research.md` for the default angle set). Scored external discovery: primary docs/original research > practitioner evidence > popularity. |
| `research-comparator` | Reconciles the scouts' findings — agreements, gaps, **contradictions** — and does not smooth conflicts over. Runs after all scouts finish. |
| `research-validator` | Independent, blind cross-check: is each claim actually sourced, not hallucinated? Runs after the comparator, sees the reconciled findings, not the raw scout files. |
| `research-lead` | Synthesizes into `dossier.md`. Reads `memory/decisions.md` for the token-budget ceiling and updates `STATUS.md` for the topic. |

> **How to invoke each role:** these are registered subagent types — launch
> each with `subagent_type: "<name>"`. Always give the agent the topic's
> output directory path. If a name isn't available as a subagent type, fall
> back to a `general-purpose` agent and paste the role brief from
> `~/.claude/agents/<name>.md`.

## `research`

1. Resolve the topic and output directory (ask if not given). Default output
   location: `<project-root>/research/<topic-slug>/` in the current project.
2. **Resume check** — if `<output-dir>/STATUS.md` already exists, read it
   first and ask the user whether to resume the existing topic run or start
   fresh. Never silently overwrite prior research.
3. `research-triage` → `brief.md` + `STATUS.md`.
4. **Parallel fan-out**: `research-scout`, one instance per angle in the
   brief, each writing `sources/<angle-slug>.md`.
5. `research-comparator` reads all scout files → `comparison.md`.
6. `research-validator` reads `comparison.md` (not the raw scout files) →
   `validation.md`.
7. `research-lead` reconciles, writes `dossier.md`, updates `STATUS.md`.
8. **Orchestrator** (whoever is running this pipeline, not a subagent —
   subagents can't see each other's token usage) tallies the actual token
   usage reported across all five agent invocations this run and appends the
   row to `memory/budget-ledger.md` — see `references/research.md`.
9. Report back in chat: the dossier's headline findings, confidence level,
   any unresolved contradictions, and the path to `dossier.md`.

Full procedure, including the token-budget checkpoint and the default angle
set, in `references/research.md`.

## Conventions

- **Never invent a claim without a source** — every scout finding must cite
  what was actually found (a named source, dated where possible), not a
  generic assumption.
- **Privacy boundary** (borrowed from `ai-coach-value`'s standing rule):
  `research-triage` strips proprietary/internal specifics (client names,
  unreleased product details) from anything that will be used in an external
  web query. Internal files can keep real specifics; external-facing queries
  cannot.
- **Token budget with mandatory checkpoint**: a pilot pass on a new topic
  defaults to a documented budget (see `memory/decisions.md` D-002) before
  any deeper research is allowed to run. This default is a draft — confirm
  or adjust it with the user the first time it's actually hit, then record the
  outcome as a decision.
- **Resumable by design**: `STATUS.md` + the `sources/` directory are the
  durable memory for a topic — a re-run picks up from what's already there
  instead of re-researching from scratch.
- **Memory**: `~/.claude/skills/team-research/memory/decisions.md` (numbered,
  standing calls — read first) and `memory/budget-ledger.md` (append-only,
  one row per run). Both updated by `research-lead` at the end of a run.

## Adding to the team

New scout angles (e.g. a regulatory/compliance angle) get added to the
default angle set in `references/research.md` and picked up automatically by
the fan-out step — no new agent needed unless the angle requires genuinely
different research judgment than `research-scout` already has. Keep the
comparator/validator/lead steps unchanged; they operate on however many scout
files exist, not a fixed count.

---
name: team-qa
description: 'Run a virtual QA team (change-intake, coverage cartographer, risk analyst, unit-test architect, e2e-test architect, QA strategist, QA lead) over a change that was just built — on any project. Use when: code has just been written/modified and you need to know what tests to add or update so it cannot silently regress; you want to understand the current testing strategy for an area before changing it; you have a git diff, a set of changed files, or a completed team-intake technical-plan and need a test plan; or you want to know "is what we just built actually guarded, or will it ship green-but-broken?". Produces a QA assessment (the coverage verdict) and a buildable test plan, and remembers recurring coverage gaps (when the project has a defect catalog configured) so the team stops shipping the same blind spot.'
argument-hint: 'How to find the change + where to write. e.g. a base git ref to diff, a folder of changed files, or a completed intake folder. Optional — will ask if omitted.'
---

# Team QA

Runs a small **virtual QA team** over a change that was *just built* and
produces two deliverables:

- **`qa-assessment.md`** — is the change adequately tested, where are the gaps, and
  have we shipped this *class* of gap before (the doc the **user** reads first).
- **`test-plan.md`** — exactly which tests to add/update to guard it (for the
  engineer who writes them).

It exists because delivery teams keep shipping changes that pass a **green test
suite and are still broken** — a consistency guard that didn't cover an entry, a
persisted field with no round-trip test, a renamed token with no no-leak
assertion. `team-intake` plans the work *before* it's built; **team-qa makes
sure what got built can't silently regress.**

This skill **plans tests — it does not write them.** It investigates read-only and
runs *existing* suites to establish a baseline; authoring the new tests is a
separate step. This is an **orchestration**: you (the main agent) run the phases
below and delegate each role to a subagent. You are the QA lead.

## The team (first-class agents, installed globally at `~/.gemini/config/agents/`)
| Agent | Role |
|-------|------|
| `qa-triage` | Ingest the change (diff/files/intake-plan) → change brief; gate on ambiguity |
| `qa-coverage-cartographer` | Map EXISTING coverage for the touched surfaces + run the green/red baseline |
| `qa-risk-analyst` | Blast radius, invariants at risk, defect-catalog mapping, "ships-green-but-broken" traps |
| `qa-unit-architect` | Design unit/parity/component tests + assertions |
| `qa-e2e-architect` | Design e2e/API tests, bucket + tag + single-spec run |
| `qa-strategist` | Coverage verdict + test-debt diagnosis + memory (the doc the user reads) |
| `qa-lead` | Synthesize coverage+risk+unit+e2e → the buildable test plan |

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.gemini/config/skills/team-qa/` + `~/.gemini/config/agents/`). If you
> installed this as a plugin instead, every `~/.gemini/config/skills/team-qa/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.gemini/config/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

> **How to invoke each role:** these are registered subagent types — launch each
> with `subagent_type: "<name>"` (e.g. `subagent_type: "qa-coverage-cartographer"`).
> Always give the agent: the `change-brief.md` path, the output dir, and (once
> known) the coverage verdict. (If a name isn't available as a subagent type, fall
> back to a `general-purpose` agent and paste the role brief from
> `~/.gemini/config/agents/<name>.md`.)

## Process

### Step 0 — Get the change scope and the output location
team-qa needs to know **what just changed** and **where to write the plans**. Scope
comes from one of three sources — accept whichever the user gives:
- **Git diff (default):** a base ref (branch/commit) to diff against. If the
  project has multiple independent repos (check `PROJECT-CONTEXT.md`), the
  diff runs against whichever repo(s) the change touches — the git repo may
  not be the project root. If they don't name a base, use the repo's default
  branch / last commit and state which. Also check `git status` for
  uncommitted work.
- **Explicit files/folder:** a list of changed paths or a folder of changed files.
- **team-intake hand-off:** a completed intake folder — read its `technical-plan.md`
  "Change set" as the intended change and confirm against the actual code.
- **If nothing was given, STOP and ask:** "What should I QA? Point me at a base git
  ref to diff, a set of changed files, or a finished intake folder — and I'll write
  the QA assessment + test plan next to it."

**Output location:** if pointed at an existing team-intake folder, write under
`<that-intake-dir>/qa/`. Otherwise create `<base>/qa/<YYYY-MM-DD>-<slug>/` (derive a
short kebab-case slug from the change). Create a `supporting/` subfolder inside it.
Use today's date. **Never write plans to a repo root.**

### Step 1 — Change-intake (gate)
Run `qa-triage` on the scope source → it writes `change-brief.md` and returns a
`READY` / `BLOCKED` verdict.
- If **BLOCKED** (e.g. no actual change found, can't determine the diff base, a
  changed file references something that doesn't exist), surface its blocking
  questions to the user with `AskUserQuestion` (or plain text) and wait. **Do not
  plan tests for a change nobody has pinned down.**
- **Log every clarifying/blocking question and its answer** (see "Decision logging")
  — record it `PENDING` before asking, flip to `DECIDED` when answered. Then update
  the brief and proceed.

### Step 2 — Evaluate (parallel fan-out)
Launch these **four agents in parallel** (one message, multiple tool calls). Give
each the `change-brief.md` path and the `supporting/` output path:
- `qa-coverage-cartographer` → `supporting/coverage.md`
- `qa-risk-analyst` → `supporting/risk.md`
- `qa-unit-architect` → `supporting/unit-tests.md`
- `qa-e2e-architect` → `supporting/e2e-tests.md`

### Step 3 — QA Strategist
Run `qa-strategist`. It reads the brief + four supporting files + **this
project's recurring-issue memory (if configured)** + the QA run-log, sets the
coverage verdict (ADEQUATE/GAPPED/BLIND), diagnoses the test-debt, writes
`qa-assessment.md`, and updates the QA run-log (and this project's
recurring-issue catalog if it has one and this run exposed/matched a
recurring gap). Capture its **coverage verdict** — the lead needs it.
- **Librarian Integration (Testing Risk Lookup & Research Trigger)**: The QA strategist queries the Librarian's Table of Contents (`TABLE-OF-CONTENTS.md` in the active library root) to check for past testing lessons, failure patterns, or coverage guidelines. If they encounter a high-risk surface with undocumented behavior or unknown error modes, they recommend triggering `team-research` to run edge-case and vulnerability analysis before build implementation.


### Step 4 — Test plan
Run `qa-lead` with the brief, the four supporting files, and the strategist's
verdict → it writes `test-plan.md`.

### Step 5 — Report back
Summarize for the user in chat:
- **Coverage verdict** (ADEQUATE / GAPPED / BLIND) and the surfaces touched.
- **"Seen this gap class before?"** (cite this project's defect-catalog id if matched).
- The strategist's headline recommendation (must-add-now tests vs the durable cure).
- The test plan in 2–3 bullets (tests to add by layer).
- Any **PENDING / PARKED decisions** still open (from `decisions.md`).
- Links to `qa-assessment.md`, `test-plan.md`, and `decisions.md`.
Then ask whether to proceed to writing the tests (out of scope for this skill).

## Decision logging
Whenever a clarifying or blocking question goes to the user — at the Step 1 gate or
anywhere a decision is genuinely the user's to make (e.g. "durable meta-test now, or
just point tests?") — record it so the team keeps a readable history. Two places:
1. **Per run:** `<output-dir>/decisions.md` (from `templates/decision-log.md`) — the
   full readable record: the question, "where we're coming from" (dated context),
   the options, and the decision. Mirror how it's presented in chat.
2. **Global:** the QA run-log already captures the run; if a decision maps to a
   recurring issue and this project has a catalog, note the reference in that
   entry.

Write the entry as `PENDING` *before* asking; flip to `DECIDED` (or `PARKED`) once
answered.

## Conventions
- **Scope source:** git-diff (default) / explicit-files / intake-handoff — provided
  by the user; if omitted, the skill asks.
- **Output per run:** `<base>/qa/<date>-<slug>/` (or `<intake-dir>/qa/`) containing
  `change-brief.md`, `qa-assessment.md`, `test-plan.md`, `decisions.md`, and
  `supporting/*.md`.
- **Templates:** `~/.gemini/config/skills/team-qa/templates/`.
- **Memory:** the QA run-log location comes from `PROJECT-CONTEXT.md` if the
  project names one; otherwise falls back to
  `~/.gemini/config/skills/team-qa/memory/qa-run-log.md` (a cross-project log — less
  useful than a project-specific one, but available). A project's own
  recurring-issue catalog, if it has one, is **shared with team-intake** — read
  it first every run, update it when a coverage gap recurs, never fork it into
  this skill's own memory.
- Investigation is read-only. This skill plans tests and runs *existing* suites to
  get a baseline; it does not author new tests or modify product code.

## The recurring trap this skill exists to catch
**Green suite ≠ no drift.** A change can pass every test and still be broken because
the surface it touched was never guarded — on any project with a recurring-issue
catalog configured, the team's most common recurring failure modes are documented
there and should be checked against every run:
- **Consistency across paths** — a registry/config-driven feature changed or added,
  but no case in the consistency guard covers it (cases are hand-enumerated, not
  derived from the registry).
- **Round-trip drop** — a persisted field added but silently dropped in one of
  several hand-maintained maps, with no write→read round-trip test.
- **Boundary leak** — a placeholder/token renamed or added on one side of a
  serialization boundary only, with no zero-unresolved assertion at the point it's
  produced and the point it's finally consumed.
If the change smells like any of these, `qa-strategist` must flag it loudly and the
test plan must add the missing guard (prefer the structural cure) — never declare it
safe just because the current suite is green. On a project with no catalog
configured, this team still enforces the general discipline (map real coverage,
name the invariants, distinguish must-add-now from durable cure) — just without a
documented history of prior instances to check against.

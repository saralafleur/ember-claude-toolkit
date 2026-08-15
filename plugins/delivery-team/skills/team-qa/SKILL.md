---
name: team-qa
description: 'Run a virtual QA team (change-intake, coverage cartographer, risk analyst, unit-test architect, e2e-test architect, QA strategist, QA lead) over a change that was just built — on any project. Use when: code has just been written/modified and you need to know what tests to add or update so it cannot silently regress; you want to understand the current testing strategy for an area before changing it; you have a git diff, a set of changed files, or a completed team-intake technical-plan and need a test plan; or you want to know "is what we just built actually guarded, or will it ship green-but-broken?". Produces a QA assessment (the coverage verdict) and a buildable test plan, and remembers recurring coverage gaps (when the project has a defect catalog configured) so the team stops shipping the same blind spot.'
argument-hint: '[<scope> | direct <scope>] — how to find the change + where to write, e.g. a base git ref to diff, a folder of changed files, or a completed intake folder. Optional — defaults to a git diff against the default branch if omitted. See "Run modes" for the direct token.'
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Workflow
  - Workflow(delivery-team:qa)
---

# Team QA

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

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

## The team (first-class agents, installed globally at `~/.claude/agents/`)
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
> install (`~/.claude/skills/team-qa/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-qa/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

> **How the team actually runs:** `qa-triage` through `qa-lead` (everything in
> Steps 1–4) run inside one `Workflow` call — `workflows/qa.js` — not as
> `Agent` calls you make directly; the script invokes each by its registered
> subagent type (`agentType: "<name>"`, e.g. `"qa-coverage-cartographer"`)
> and reuses these same agent files unchanged.

## Run modes

**This skill never stops to wait for a human answer, in any mode.** There is
no "auto-pilot" mode — the behavior auto-pilot used to opt into (decide on
the team's own best recommendation, log it, keep going) is now the only way
this skill runs, always. Standard mode (bare `<scope>`) runs the full
7-agent roster start to finish, straight through to a `team-build` hand-off,
with no interactive pause anywhere in "Process" below. One optional mode
changes the roster shape (not the no-stopping behavior, which applies
either way):

| Mode | Token | What changes |
|---|---|---|
| Direct | `direct` | Right after triage returns `READY`, the pipeline (Step 1's `Workflow` call) runs `director-of-engineering` with this skill's own roster (the table under "The team") instead of the fixed evaluation fan-out; it runs exactly the agents/order the director returns in place of the fixed roster. Still runs straight through with no pause. |

Every decision point in "Process" below resolves one of three ways, never a
stop-and-wait:
1. **A mechanical default exists** (e.g. no scope given at all → diff
   against the default branch) — apply it and state what was assumed.
2. **A genuine preference exists but any reasonable choice is safe to make**
   (e.g. "durable meta-test now, or just point tests?") — the team picks its
   own best recommendation and logs it to `decisions.md` as `DECIDED-AUTO`
   immediately (not `PENDING`-then-flip, since nothing is ever left waiting
   on an answer).
3. **The input is fundamentally unusable** (Step 1's `BLOCKED` case — no
   actual change found, an undeterminable diff base) — there is no safe
   default to guess at (fabricating a test plan for a change that doesn't
   exist is worse than doing nothing). The run **terminates with a report**
   instead of pausing: it logs the blocking question to `decisions.md` as
   `PENDING` (an open item for whenever a human looks, not something this
   run sits and waits on) and stops there — Steps 2–5 don't run. This is
   the one place "proceed all the way through" doesn't mean "produce a
   deliverable regardless" — it means "don't leave the run hanging," and a
   clean early stop with a clear reason isn't hanging.

`direct` mode only changes which agents run in Step 2's place — it produces
fewer `supporting/*.md` files (only for the agents actually run) but writes
every other artifact this skill normally writes, to the same paths.

## Process

### Step 0 — Get the change scope and the output location
team-qa needs to know **what just changed** and **where to write the plans**.

- Parse the skill argument for a leading `direct` token first (see "Run
  modes" above). Strip it if present; whatever remains is the scope.

Scope comes from one of three sources — accept whichever the user gives:
- **Git diff (default):** a base ref (branch/commit) to diff against. If the
  project has multiple independent repos (check `PROJECT-CONTEXT.md`), the
  diff runs against whichever repo(s) the change touches — the git repo may
  not be the project root. If they don't name a base, use the repo's default
  branch / last commit and state which.
- **Explicit files/folder:** a list of changed paths or a folder of changed files.
- **team-intake hand-off:** a completed intake folder — read its `technical-plan.md`
  "Change set" as the intended change and confirm against the actual code.
  If the folder holds a `run-plan.md` (the intake ran `direct`/`fast`), read
  its **"Agents skipped"** list too — those are the evaluation angles the
  intake deliberately deferred, and exactly where this QA pass should look
  hardest.

**If nothing was given at all** (no base ref, no files, no intake folder),
don't ask — default to **git diff against the repo's default branch** (the
same default the git-diff source already uses when a base is unnamed, just
extended to cover "no scope named at all") and check `git status` for
uncommitted work too. State the assumed scope plainly in the Step 5 summary
so it's visible, not silently guessed. If even that default isn't viable
(not inside a git repo, no repo discoverable) there's genuinely nothing to
evaluate — say so plainly and end the run there rather than fabricating a
scope.

**Output location:** if pointed at an existing team-intake folder, write under
`<that-intake-dir>/qa/`. Otherwise create `<base>/qa/<YYYY-MM-DD>-<slug>/` (derive a
short kebab-case slug from the change). Create a `supporting/` subfolder inside it.
Use today's date. **Never write plans to a repo root.**

### Step 1 — Run the QA pipeline

Triage runs first, by itself, since its `READY`/`BLOCKED` verdict decides
whether anything else runs at all:

```
Workflow({
  scriptPath: "~/.claude/skills/team-qa/workflows/qa.js",
  args: {
    changeBriefPath: "<output-dir>/change-brief.md",
    supportingDir: "<output-dir>/supporting",
    scope: "<the resolved scope from Step 0>",
    mode: "standard" | "direct"
  }
})
```

(Under a plugin install, `scriptPath` is
`${CLAUDE_PLUGIN_ROOT}/skills/team-qa/workflows/qa.js` instead — same "Path
note" translation as everywhere else in this file.)

This one call replaces what used to be four separate steps — change-intake,
the staged two-wave evaluation fan-out, the strategist, and the lead. The
mechanics described in the old Steps 1–4 are all still true, just executed
by the script now instead of by you:
- **`qa-triage`** writes `change-brief.md` and returns `READY`/`BLOCKED`.
  **If `BLOCKED`**, the script does not run anything else — it returns
  `{blocked: true, reason}` immediately. Do not plan tests for a change
  nobody has pinned down: log the blocking question to `decisions.md` as
  `PENDING` (see "Decision logging"), report plainly what was checked and
  why it's `BLOCKED`, and stop — do not proceed to `team-build`.
- **If `direct` was requested**, `director-of-engineering` runs right after
  triage, with this skill's own roster (the table under "The team"), and
  trims which of the remaining six agents actually run.
- **The evaluation fan-out runs in two waves**, not one flat fan-out — wave 2
  (`qa-unit-architect`, `qa-e2e-architect`) is fed wave 1's named
  "ships-green-but-broken" traps (with their stable ids) from `risk.md`, so
  the architects design tests against real traps instead of re-deriving risk
  analysis from scratch.
- **`qa-strategist`** sets the coverage verdict (ADEQUATE/GAPPED/BLIND),
  diagnoses test-debt, writes `qa-assessment.md`, and updates the QA run-log
  + recurring-issue catalog + (if `BLIND` and scope came from an intake
  hand-off) the source `technical-plan.md`'s Risks & rollback section — all
  via its own `Write`/`Bash` tools, unchanged.
- **`qa-lead`** synthesizes everything into `test-plan.md`.

The run goes silent in this session until the workflow completes — a
background job, not a live stream — so say so before starting it. It returns
an object; use it in Step 5 below.

**Writing back what the workflow decided:** the script never touches the
filesystem itself. `decisions.md` is your job, same as before — a
`BLOCKED` reason logged as `PENDING`, or a genuine preference point logged as
`DECIDED-AUTO` (see "Decision logging").

### Step 5 — Report back
Read the workflow's return value first (`coverageVerdict`, `matchedRecurringGap`,
`leadSummary`, `ranAgents`/`skippedAgents`), then summarize for the user in chat:
- **Coverage verdict** (ADEQUATE / GAPPED / BLIND) and the surfaces touched.
- **"Seen this gap class before?"** (cite this project's defect-catalog id if matched).
- The strategist's headline recommendation (must-add-now tests vs the durable cure).
- The test plan in 2–3 bullets (tests to add by layer).
- Any **PENDING / PARKED decisions** still open (from `decisions.md`).
- Every `DECIDED-AUTO` entry from this run — "Decided automatically: N items
  — see decisions.md" — so a choice the team made on its own is visible,
  not buried.
- Links to `qa-assessment.md`, `test-plan.md`, and `decisions.md`.

**Then move directly into `team-build` — no ask, in every mode.** Writing
the tests is still out of this skill's own scope, but deciding *whether* to
proceed there is no longer a preference to check — it's the standing next
step:
- **If scope source was a team-intake hand-off** (a `technical-plan.md`
  exists for this item), invoke `team-build` immediately on the same intake
  folder. State it plainly in the summary above — "Proceeding to
  `team-build` on `<folder>`." — rather than waiting for a go-ahead.
- **If scope source was git-diff or explicit-files,** there is no
  `technical-plan.md` for team-build's own required-input gate to find, so
  don't attempt the invocation — it would just fail that gate. Say so
  plainly instead: "team-build needs a completed intake folder; this run
  had none — point it at one manually, or run `team-intake` first if the
  change needs a plan."

## Decision logging
This skill never pauses to ask, so every decision point resolves to one of
two logged outcomes — record it so the team keeps a readable history. Two
places to log to:
1. **Per run:** `<output-dir>/decisions.md` (from `templates/decision-log.md`) — the
   full readable record: the question, "where we're coming from" (dated context),
   the options, and the decision. Mirror how it's presented in chat.
2. **Global:** the QA run-log already captures the run; if a decision maps to a
   recurring issue and this project has a catalog, note the reference in that
   entry.

- **A genuine preference where any reasonable choice is safe** (e.g.
  "durable meta-test now, or just point tests?"): the team picks its own
  best recommendation immediately and logs the entry as `DECIDED-AUTO` —
  never `PENDING`, since nothing is left waiting on an answer.
- **A blocking ambiguity with no safe default** (Step 1's `BLOCKED` case):
  log the entry as `PENDING` and end the run there (see Step 1) — `PENDING`
  here means "open, for whenever a human looks," not "this run is waiting."

**Propagate the flip, don't just log it.** The moment an entry moves off
`PENDING`/`PARKED`, grep the project for every other doc that cited its old
status — a technical-plan's Risks/rollback section, a sibling item's own
`decisions.md`, the defect catalog if configured, a cached
`status-report.md` — and correct them in the same sitting. If a citing doc
is out of this skill's write scope (product code, another team's memory) or
genuinely unreachable this session, **name it explicitly in the Step 5
report-back** instead of leaving it silently stale — that's what lets a
later `team-status` pass close the loop.

This same propagation discipline applies to a `BLIND` coverage verdict, not
just decision flips: `qa-strategist` writes that finding back into the
source `technical-plan.md`'s Risks & rollback section itself (see its role
file) — this closed a gap where a coverage finding that implied the plan
itself was incomplete used to dead-end in `qa-assessment.md` with nothing
routing it back to `team-intake`.

## Conventions
- **This skill has no interactive human gates.** Every decision point in
  "Process" resolves on its own — a mechanical default, an auto-decided
  `DECIDED-AUTO` preference, or (for a genuinely `BLOCKED` change) a
  terminated run with a `PENDING` entry — never a stop-and-wait. Make every
  auto-decision **visible in the Step 5 report**, even though nothing waited
  on it: state plainly what was assumed (Step 0's default scope), what was
  decided and why (each `DECIDED-AUTO` entry), and what's still open (any
  `PENDING`/`PARKED` entry, including a `BLOCKED`-triggered early stop).
  Legibility replaces confirmation — the user should be able to read one summary
  and know exactly what this run assumed, decided, and couldn't resolve,
  without having been asked any of it in the moment.
- **Scope source:** git-diff (default) / explicit-files / intake-handoff — provided
  by the user; if omitted entirely, defaults to a git diff against the
  repo's default branch (see Step 0).
- **Output per run:** `<base>/qa/<date>-<slug>/` (or `<intake-dir>/qa/`) containing
  `change-brief.md`, `qa-assessment.md`, `test-plan.md`, `decisions.md`, and
  `supporting/*.md`.
- **Templates:** `~/.claude/skills/team-qa/templates/`.
- **Memory:** the QA run-log location comes from `PROJECT-CONTEXT.md` if the
  project names one; otherwise falls back to
  `~/.claude/skills/team-qa/memory/qa-run-log.md` (a cross-project log — less
  useful than a project-specific one, but available). Rows are always
  appended via `~/.claude/skills/team-qa/scripts/add_qa_run_log_row.py`
  (never hand-typed — see `qa-strategist`'s role file) and read via `grep`
  scoped to a project, never a full `Read`. The shared fallback log is
  periodically rotated (older rows moved to `memory/archive/`) specifically
  to keep a full read viable if one is ever genuinely needed — see the live
  file's own header for its current rotation state and the threshold at
  which to re-rotate. A project's own recurring-issue catalog, if it has
  one, is **shared with team-intake** — read it first every run, update it
  when a coverage gap recurs, never fork it into this skill's own memory.
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

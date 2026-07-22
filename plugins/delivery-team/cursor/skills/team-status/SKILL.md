---
name: team-status
description: 'Run a virtual delivery-status team over a folder in a project''s delivery pipeline and answer "where are we, and what do we invoke next?" — on any project. Use when: you open a batch or an intake-base folder and need to know the true current state of every work item in it; a plan/report might be stale and you want it re-verified against the live code, not just re-read; you are picking up work someone else (or a past session) produced and need to reconstruct it; or you want a single, current status-report.md that says which of team-intake / team-qa / team-build / librarian to run next and why. Also trigger on short, bare prompts asking to reconstruct current state and the next step — e.g. "next", "next?", "what''s next", "where are we", "where are we at", "status check", "status" — even with no folder named (Step 0 resolves the folder from PROJECT-CONTEXT.md or asks). Produces one status-report.md per run and a thin run-log, and it NEVER changes product code, plans, or tests — it is read-only and advisory.'
---

# Team Status

This skill takes one argument: the path to the folder to assess (a whole
batch, or a single intake-base folder). It's optional — Step 0 below resolves
a default from `PROJECT-CONTEXT.md`, or asks, if it's omitted.

Runs a small **virtual delivery-status team** over a folder in the delivery
pipeline and answers the two questions no single artifact answers on its own:
**"where are we?"** and **"what do we invoke next?"**

It is the fourth member of the family, and it is the read-only *reconciler*
the other three don't provide:

- **`team-intake`** plans *what to change* → `technical-plan.md` +
  (project-specific) plan docs.
- **`team-qa`** plans *what must go red-then-green* → `qa-assessment.md` +
  `test-plan.md`.
- **`team-build`** builds it and proves it → a green diff + `build-report.md`.
- **`team-status`** reads across all of the above for a folder,
  **re-verifies the claims against the live code**, and says which team to
  run next → `status-report.md`.

It exists because of a lesson every delivery pipeline eventually teaches:
**there is no single "current plan" document, and the closest approximation
goes stale the moment anyone investigates further.** A `build-report.md` says
`DEFERRED` or `GREEN` as of when the build lead stopped writing; a sibling
item's plan never hears about a follow-on change that touched the same
surface. Reading those reports at face value is exactly how work gets
dropped, re-done, or declared finished when it isn't. This team's whole job
is to reconstruct the real state by **checking, not quoting** — and to leave
behind the one durable status artifact the pipeline was missing.

This skill is an **orchestration**: you (the main agent) run the phases below
and delegate each role to a subagent. You are the status lead. **This team is
strictly read-only** — it reads code, runs *existing* tests/greps to verify
claims, and writes only its own report + run-log. It never edits product
code, a plan, a test, or another team's memory.

## The team (subagents bundled with this plugin)
| Agent | Role |
|-------|------|
| `status-triage` | Resolve scope; enumerate every work item in the folder and inventory which artifacts each has; gate on an empty/unreadable target |
| `status-scanner` | Per item (fanned out): reconcile intent vs. last-reported state, **re-verify the claims against the live code**, classify the stage, flag drift |
| `status-lead` | Synthesize all items into `status-report.md` and name the single next action (which skill, on which folder, why) |

> **Path note:** wherever this file refers to `references/...` (templates and
> the run-log), it means the same-named folder bundled alongside this
> `SKILL.md`, and each agent named above is the matching file in this
> plugin's own `agents/` folder — same relative layout.

> **How to invoke each role:** these agents are bundled with this plugin.
> Delegate to a subagent by name — invoke it explicitly as `@<name>` with the
> task and inputs (e.g. delegate to the `status-scanner` subagent), or
> describe the task so the main agent routes it to the subagent whose
> `description` fits. Always give the agent: the target folder, the output
> path for the report, and (for scanners) the specific item folder it owns.

## Process

### Step 0 — Resolve the scope
`team-status` assesses a **folder**. Two shapes are common; detect which:
- **Batch** — a folder holding *several* sibling work items, each in its own
  intake-base. Assess every item.
- **Single item** — one intake-base folder holding one item's
  `intake/`/`qa/`/`build/` trail. Assess just it.

If the user gave a path, use it. **If no path was given, check for a default
before asking:** look for a `PROJECT-CONTEXT.md` at the project root. If it
names a "Default status scope" (or, failing that, a "Delivery pipeline
artifacts" folder), use that as the target — state the interpretation you're
taking ("no folder given — defaulting to `<path>` per `PROJECT-CONTEXT.md`")
and proceed without stopping.

**Only if no path was given AND no PROJECT-CONTEXT.md default exists, STOP
and ask:** "Which folder should I assess — a whole batch, or a single
intake-base folder? I'll reconstruct the true current state and write a
`status-report.md` there." If the shape is genuinely ambiguous, state the
interpretation you're taking and proceed; don't stall on it.

**Output location:** write `status-report.md` at the **root of the target
folder** (so a batch gets one roll-up report, a single item gets its own).
Never write it into a repo root or into another team's `intake/qa/build`
subfolder.

### Step 1 — Triage (gate)
Run `status-triage` on the target folder. It walks the tree, enumerates every
work item (each distinct `intake/<date>-<slug>/` it finds, at any depth), and
for each records the **artifact inventory** — which of these exist:
`technical-plan.md`, project-specific plan docs, `request-brief.md`,
`qa/test-plan.md`, `qa/qa-assessment.md`, `build/**/build-report.md`,
`decisions.md`. This is pure inventory — no judgment yet. It writes nothing
but returns the item list + a `READY` / `BLOCKED` verdict.
- **BLOCKED** only if the target doesn't exist, is empty, or contains nothing
  that looks like pipeline work. Surface that to the user directly (plain
  text) and stop — don't fan out scanners over nothing.
- **Log every clarifying/blocking question and its answer** (see "Decision
  logging").

### Step 1.5 — Change detection (fast-path skip)
Before launching any scanners, check whether a previous run's results can be
reused for unchanged items. This avoids re-verifying work that no one has
touched.

**How:**
1. Read the write timestamp of `<target>/status-report.md` (if it exists).
   Call this `LAST_RUN`. If no report exists, all items are NEW → skip this
   step and proceed to Step 2 (full scan of everything).
2. For each work item returned by triage, run:
   ```
   git -C <repo-root> log --since="<LAST_RUN>" -- <item-folder-path>
   ```
   If the project spans multiple repos, run it in each relevant repo.
3. **If `git log` returns no commits** for an item AND its scratch file
   `<target>/.status-scratch/<item-slug>.md` exists from the previous run →
   mark the item **SKIP** (carry forward the previous finding verbatim).
4. **If `git log` returns commits, OR the scratch file is missing** → mark
   the item **RESCAN** (run a full scanner for it).
5. Tell the user the split before launching: e.g. *"3 items unchanged since
   last run (skipping re-verify), 2 items changed (scanning now)."* If ALL
   items are SKIP, go directly to Step 3 with the cached scratch files and
   note in the report that no items changed since the last run.

**Force-rescan override:** if the user passes `--force` or says "force rescan"
/ "re-verify everything", skip this step and treat all items as RESCAN.

**Safety:** if `git` is unavailable in the target repo, treat all items as
RESCAN and note it (don't silently skip verification).

### Step 2 — Scan (parallel fan-out, one scanner per item)
Launch one `status-scanner` **per RESCAN item**, in parallel — dispatch all
of them at once rather than one after another. SKIP items do not get a
scanner — their existing scratch file is passed directly to Step 3. Give each
scanner: its item folder, the artifact inventory from triage, and the
shared-memory paths. Each scanner does the load-bearing work — **read-only,
but not passive:**
- **Reconcile intent vs. state:** read `technical-plan.md` (what was
  intended) against `build-report.md` (what was last reported done/verified)
  and the QA `qa-assessment.md` verdict.
- **Re-verify, don't quote.** For any load-bearing claim in a report —
  "GREEN", "DEFERRED", "N/N tests pass", "migration applied", "e2e not
  run" — check whether it is *still true now*: re-run the cited
  suite/filter, grep for the cited files/symbols, hit the cited endpoint. A
  report's claim is a hypothesis to test, not a fact to repeat. (This is the
  whole reason the skill exists.)
- **Open decisions:** scan `decisions.md` for any `PENDING` / `PARKED` item.
- **Cross-item drift:** flag when a sibling item's plan/decisions were never
  updated to reflect a follow-on that touches the same surface, or when two
  items edit the same file/section.
- **Classify the stage** (one of): `not-started` · `intake-only` (plans, no
  tests) · `qa-done` (test-plan exists, not built) · `build-in-progress` ·
  `build-green` · `build-green-with-caveats` · `stale — report contradicted
  by live code` · `blocked — open decision`.
- Write findings to `<target>/.status-scratch/<item-slug>.md` (scratch, not
  the final report).

### Step 3 — Synthesize + report
Run `status-lead` with the triage inventory + every scanner's scratch file.
It writes `<target>/status-report.md` (from `references/status-report.md`): a
stage-map of every item, the reconciled true state, open `PENDING`/`PARKED`
decisions, cross-item drift, a **parallelization opportunity** check (whether
two or more ready-to-build items are independent enough to run as concurrent
`team-build` worktree efforts, laid out as an Option A: concurrent / Option
B: sequential trade-off — never a unilateral pick), and — the point of the
whole skill — **the single recommended next action**: *which skill to invoke
(`team-intake` / `team-qa` / `team-build` / `librarian`), on which folder,
and why*, citing the concrete gap. It also appends one row to the status
run-log. Capture its headline recommendation and, if present, the
parallelization choice verbatim.

### Step 4 — Report back
Summarize for the user in chat:
- **The stage-map** — each work item and its verified stage (one line each).
- **Anything the reports got wrong** — every place a plan/report claim was
  contradicted by the live re-verification (this is the highest-value
  output).
- **Open decisions** still `PENDING` / `PARKED`.
- **The single next action** — the skill to run next, the target folder, and
  the one-line why.
- Links to `status-report.md` and any per-item scratch worth reading.
Then ask whether to proceed with the recommended next action (which means
invoking one of the *other* skills — out of scope for this one).

**If `status-lead` found a parallelization opportunity** (two or more
independent build-ready items), do not fold that into the same yes/no — put
it to the user as its own explicit choice, asked directly: Option A (run
`team-build` concurrently on the named items — state the items and the
time-saved trade-off) vs. Option B (run them sequentially in priority order —
state the lower-review-load trade-off). Let the user pick; then proceed
accordingly (each concurrent branch still goes through its own `build-triage`
for its own worktree, same as any single `team-build` run — just launched
together instead of one after another).

## Decision logging
This is a read-only audit skill, so it rarely needs a decision from the
user — but when it does (scope is genuinely ambiguous at Step 0; or a report
is old and the underlying code has since changed and you must choose "trust
the report" vs. "re-verify from scratch"), record it so the call is
remembered. Two places:
1. **Per run:** `<target>/status-decisions.md` (from
   `references/decision-log.md`) — the question, dated context, options, and
   the decision.
2. **Global:** the status-run-log row captures the run; note the decision
   there in one line.
Write it `PENDING` before asking; flip to `DECIDED` / `PARKED` once answered.

## Conventions
- **Read-only reconciler, single writer of its own artifacts.** Scanners and
  triage never write to any plan, test, product file, or another team's
  memory. Only `status-lead` writes, and only `status-report.md` + the
  run-log.
- **Shared memory is INPUT, never forked.** Read (do not copy, do not edit)
  each team's own `memory/` folder to know what's already been done and
  which project-specific defect surfaces are in play. **One source of
  truth — do not duplicate it here.**
- **Output per run:** `<target>/status-report.md` (+ transient
  `<target>/.status-scratch/*.md`, + `status-decisions.md` only if a decision
  was logged).
- **Templates:** this plugin's own `references/` (`status-report.md`,
  `decision-log.md`).
- **Memory:** the status run-log location comes from `PROJECT-CONTEXT.md` if
  the project names one; otherwise this plugin's own
  `references/status-run-log.md` (a cross-project fallback, append-only). It
  has no forked defect-catalog file — it reads the project's own if one is
  configured.
- **Repo layout is project-specific — check `PROJECT-CONTEXT.md` first**, or
  discover it. Verification commands run inside the project's actual repo(s).

## The recurring trap this skill exists to catch
**A report is a claim as of when it was written — not the current truth.**
So the standing rule for this team: **re-verify every load-bearing claim
against the live code before repeating it, run the deferred/uncertain thing
rather than accepting the caveat, and treat every report as perishable.**
Never declare a folder "done" because a report says so. If this project has
captured durable lessons (a knowledge library, a defect catalog), check
`PROJECT-CONTEXT.md` for where they live and read them for context on
patterns this team has been bitten by before.

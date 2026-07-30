# dispatch

Full decide → gate → dispatch → monitor → merge flow. You (the orchestrator)
run every step below directly except where an agent is named — only
`em-analyst`, `em-judge`, and `em-lead` are ever spawned as subagents; every
other action (provisioning follows automatically inside each delegate's own
`team-build` run, dispatching, monitoring, resuming, merging) is you, using
your own tools, same as `wrap-up`.

## Step 0 — Resolve the candidate set

If the user gave a folder, use it. Otherwise: check `PROJECT-CONTEXT.md` for
a "Default status scope" (same lookup `team-status` uses) and read that
folder's `status-report.md`.

**From the stage-map, take every item that is:**
- Intake ✅ and QA ✅,
- Build ❌ or ➡️ (not started, or started but not green/merged),
- **not** currently blocked on a PENDING/PARKED decision that would prevent
  a build from even starting.

If `status-report.md` doesn't exist or is stale beyond what you're willing to
trust, tell the user to run `team-status` first (or, if the project has no
`team-status` configured, ask the user directly which folders are the
candidates) — don't guess at the candidate set from a stale or missing
report.

If the stage-map has outstanding items but **none** are build-ready (no
Intake ✅ + QA ✅ + Build ❌/➡️ rows — everything's either still needing
intake, or is a doc/housekeeping fix), say so and point at `triage` instead:
`dispatch` only ever moves build-ready work, it doesn't create plans or fix
prose.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate, stays in every mode,
including auto-pilot.**
If the candidate set has **fewer than two items**, there's nothing to
decide — say so plainly ("only one build-ready item found; just run
`team-build` on it directly") and stop. Don't spin up the analyst for a
single item. There's nothing to recommend when there's no split to decide
between — this is a degenerate case, not a preference.

## Step 1 — Analyze independence

Run `em-analyst` on the candidate set (paths to each item's
`technical-plan.md`, `decisions.md`, and QA `test-plan.md`; note any existing
open efforts from this project's effort-worktree registry, if one exists, so
the analyst can check candidates against work already in flight, not just
against each other).

## Step 1.5 — Judge panel (conditional)

**Only if `em-analyst` reported confidence LOW**, run `em-judge` 2-3 times in
parallel (one message, multiple tool calls), each given the same candidate
set plus the analyst's findings and its stated ambiguity. If confidence was
HIGH, skip this step entirely — don't spend the calls on an uncontested
read.

## Step 2 — Synthesize the decision

Run `em-lead` with the analyst's findings (+ judge votes, if the panel ran).
It writes `<target>/dispatch-plan.md` — the final PARALLEL/SEQUENTIAL/
SINGLE-SESSION decision, the per-item dispatch spec (branch, worktree, the
exact self-contained dispatch prompt with the BLOCKED protocol baked in), and
the merge order.

**If this `dispatch` run is itself in auto-pilot,** tell `em-lead` so —
it bakes the same `auto`/`auto-pilot` token into each dispatch prompt's
`team-build` invocation (e.g. "run the `team-build` skill in `auto-pilot`
mode on `<path>`" instead of "run the `team-build` skill on `<path>`"), so
the delegate's own preference gates auto-decide too instead of a background
delegate silently stalling on a gate nobody can answer.

If the decision is **SINGLE-SESSION**: present that recommendation and stop
— there is nothing to dispatch. Suggest running `team-build` normally.

## Step 3 — Human gate

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
Present `dispatch-plan.md`'s decision in chat: the grouping/order, the
one-paragraph reasoning, any judge-panel disagreement, and anything flagged
for direct human attention instead of auto-dispatch. Letter the choice:

- **A) Proceed as recommended** — dispatch exactly as written.
- **B) Adjust the grouping/order** — ask what to change, update the plan
  in-memory (no need to re-run the agents for a manual override), then
  proceed with the adjusted plan.
- **C) Cancel** — stop here; nothing is dispatched.

Only continue past this point on A or B.

**Under auto-pilot,** skip the ask: auto-pick **A) Proceed as recommended**
(never B — an unattended adjustment isn't a recommendation the team actually
made) unless `dispatch-plan.md` itself flagged something for direct human
attention, in which case that flagged item is pulled out of the auto-dispatch
set and surfaced in the report-back instead of silently dispatched. Log the
choice to `<target>/dispatch-decisions.md` (from `templates/decision-log.md`,
create if it doesn't exist) as `DECIDED-AUTO`, state it plainly when
reporting back, and proceed to Step 4.

## Step 4 — Dispatch

For each item in a PARALLEL group, launch its delegate in the **same
message** as the other members of that group (multiple tool calls, one
message) — that's what makes them actually concurrent. For SEQUENTIAL items,
launch only the first; launch each subsequent one after its predecessor
reports DONE (Step 5) — not on a timer, not all at once.

Each delegate is `Agent(subagent_type: "general-purpose", run_in_background:
true, prompt: <the exact dispatch prompt from dispatch-plan.md>)`. Never use
`subagent_type: "fork"` — the delegate needs none of this session's
conversation history, only the item's own on-disk plan/decisions, which is
the entire reason the pipeline keeps those documents authoritative.

Immediately after dispatching, write/update
`<target>/.em-state/dispatch-state.json` (create the directory if it
doesn't exist) — one entry per dispatched item:

```json
{
  "<item-slug>": {
    "agent_id": "<from the Agent tool result>",
    "status": "IN_PROGRESS",
    "dispatched_at": "<from context, not computed>",
    "group": "parallel-1 | sequential | single",
    "branch": "<from dispatch-plan.md's spec>",
    "worktree": "<from dispatch-plan.md's spec>"
  }
}
```

This file is what makes `status`/`resume` (and a later session, if this one
ends before everything finishes) able to reconstruct what's in flight without
re-deriving it from scratch.

## Step 5 — Monitor and triage

As each dispatched delegate's background completion notification arrives,
read its final message and classify by the prefix `em-lead` had it use:

- **`DONE: ...`** — mark that item `READY-TO-MERGE` in `dispatch-state.json`,
  note the branch/worktree and verdict. If this was a SEQUENTIAL group's
  item and there's a next one queued, dispatch it now (back to Step 4).
- **`BLOCKED: ...`** — read the stated question. If it's answerable from a
  clear project convention or an obvious default (rare — most should already
  have been pre-cleared by intake/QA approval), you may answer it yourself
  and say so when reporting back. Otherwise:
  🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate, stays in every mode,
  including auto-pilot.** A delegate's own BLOCKED protocol already only
  fires when *it* determined the decision "cannot be safely deferred or
  defaulted" — that verdict came from inside a `team-build` run that was
  itself dispatched in auto-pilot (per the cascade in Step 2), so it already
  auto-decided everything it safely could before escalating. There's nothing
  left to auto-decide here.
  surface the exact question to the user immediately — don't batch it with
  unrelated items — get an answer, then `SendMessage` to that delegate's
  `agent_id` with the answer. This resumes the **same** delegate with full
  context; it is not a restart. Mark the item `BLOCKED` → back to
  `IN_PROGRESS` in `dispatch-state.json` once resumed.
- **`FAILED: ...`** — report what went wrong to the user.
  🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
  ask whether to retry (a fresh `Agent` call, same dispatch prompt — the
  worktree/branch and any partial progress are still on disk, so a fresh
  delegate isn't starting from zero even though it's a new agent ID) or hand
  the item back for manual investigation. Mark accordingly. **Under
  auto-pilot,** skip the ask once: auto-retry with a fresh delegate (same
  dispatch prompt, same auto-pilot cascade), log it `DECIDED-AUTO`, and state
  the retry in the report-back. **If that retry also reports `FAILED:`**,
  this stops being a preference — escalate to a hard stop and surface it to
  the user regardless of mode; don't auto-retry a second time.

Keep `dispatch-state.json` current after every transition — it's the only
durable record if this session ends mid-flight.

## Step 6 — Merge

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **stays a hard stop in every mode,
including auto-pilot.** Merging into the project's actual default branch is
exactly the kind of hard-to-reverse, shared-state action this environment's
own standing safety floor exists for — the same floor `team-build`'s "Run
modes" names as never moving regardless of mode (no force-push, no
`--no-verify`, no push/merge straight to the default branch without a human
looking first). Auto-pilot speeds up everything *before* this point; it does
not extend to putting unreviewed work on the branch everyone else builds on.

Once an item (or, for a same-surface SEQUENTIAL group, every item in it) is
`READY-TO-MERGE`, merge it using the same discipline as `wrap-up`'s Step 1-6
(audit outstanding → human gate → commit → push → merge into the detected
default branch → verify merged → clean up the branch/worktree) — either by
invoking the `wrap-up` skill scoped to that item's worktree/branch, or by
replicating its steps directly. Either way, **never skip that gate**, even
though the build itself ran unattended.

**Merge order**: independent items merge in whatever order they complete —
no dependency between them. Same-surface SEQUENTIAL items merge strictly in
`dispatch-plan.md`'s stated order, and each one rebases against the updated
default branch before merging the next, so the second doesn't silently drop
the first's change.

Mark each merged item `MERGED` in `dispatch-state.json`.

## Step 7 — Refresh status

Once all items in this dispatch are `MERGED` (or the run is ending with some
still open — note which), invoke `team-status` on the project's default
status scope if one is configured, same as `wrap-up`'s Step 7.5 — so the
next bare "next" reflects what actually shipped instead of paying a stale
rediscovery cost.

## Step 8 — Report back and record

One summary: the decision made (grouping + why), each item's outcome
(merged / still open / failed), any BLOCKED questions that came up and how
they were answered, and the merge commits. Then append one line to the run
log (location: `PROJECT-CONTEXT.md`'s "Dispatch run-log" entry if this
project names one, else this plugin's own bundled
`memory/dispatch-run-log.md` — create from `templates/run-log-header.md` if
it doesn't exist yet): date · target ·
items dispatched · decision (parallel/sequential/single + one-line why) ·
outcomes · merge commits.

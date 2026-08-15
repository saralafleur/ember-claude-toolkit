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
- Intake ✅ (QA ✅ is **not** required — as of 2026-08-14 `team-build`
  self-heals a missing test-plan by auto-running `team-qa` first, and
  `team-qa` auto-chains onward into the build, so pinning dispatch to a
  "QA done, build not started" stage would starve it of candidates other
  skills now flow straight past),
- Build ❌ or ➡️ (not started, or started but not green/merged),
- **not** currently blocked on a PENDING/PARKED decision that would prevent
  a build from even starting.

`scripts/list_build_ready.py <status-report.md>` computes exactly this
filter deterministically (stage columns + per-item open-decision counts via
`scan_decisions.py`) and fails loud on an unparseable table — use it, then
cross-check its candidate list against the report's own Notes column, which
carries sequencing rulings and plan-only carve-outs the emoji columns can't
express (e.g. an item whose Notes say "plan-only cycle — no build ever
authorized" is not a candidate no matter what its columns say).

**Alternate entry path (exercised 2026-08-14, legitimate):** candidates
don't have to come from a status-report. A `/worktree` status check that
surfaces dirty, genuinely-unfinished mid-build worktrees is a valid
candidate source (only available if the `worktree` skill is installed at
`~/.claude/skills/worktree/` — if it isn't, this alternate entry path
doesn't apply; use the stage-map path above instead) — investigate each
worktree's real state first (`~/.claude/skills/worktree/scripts/
worktree_status.py`, then the item's own build artifacts), and treat the
resulting items as resumed-build candidates subject to the same analysis,
gates, and state-file bookkeeping below.

If `status-report.md` doesn't exist or is stale beyond what you're willing to
trust, tell the user to run `team-status` first (or, if the project has no
`team-status` configured, ask the user directly which folders are the
candidates) — don't guess at the candidate set from a stale or missing
report.

If the stage-map has outstanding items but **none** are build-ready (no
Intake ✅ + Build ❌/➡️ rows — everything's either still needing
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

## Step 1-2 — Run the decide pipeline

Gather what `em-analyst` needs before starting: paths to each candidate's
`technical-plan.md`, `pm-plan.md` (its cost/scope framing and
durable-fix-vs-patch call are dispatch-relevant), `decisions.md`, QA
`test-plan.md`, and `qa-assessment.md` if one exists (its coverage verdict
matters: BLIND is not ADEQUATE); any existing open efforts from this
project's effort-worktree registry, if one exists; and
this plugin's own bundled `memory/standing-constraints.md` — the
durable shared-DB/registry/ceiling facts past runs already paid judge
panels to establish.

Then run the decide pipeline — analyst, the conditional judge panel, and
synthesis — as one call:

```
Workflow({
  scriptPath: "~/.claude/skills/engineering-manager/workflows/decide.js",
  args: {
    kind: "dispatch",
    targetDir: "<target>",
    runId: "<YYYY-MM-DD>-<run-slug>",
    candidates: [ {slug, path, note?}, ... ],
    standingConstraintsPath: "~/.claude/skills/engineering-manager/memory/standing-constraints.md",
    existingEffortsNote: "<open efforts from the effort-worktree registry, if any>"
  }
})
```

(Under a plugin install, `scriptPath` is
`${CLAUDE_PLUGIN_ROOT}/skills/engineering-manager/workflows/decide.js`
instead — same "Path note" translation as elsewhere in this repo.)

This one call replaces what used to be three separate steps — analyze
independence, the conditional judge panel, and synthesis. The mechanics are
all still true, just executed by the script now instead of by you:
- `em-analyst` proposes PARALLEL/SEQUENTIAL/SINGLE-SESSION with a confidence
  rating.
- **Any confidence rating other than an explicit HIGH is treated as LOW**
  (the panel convenes) — an out-of-vocabulary rating (a past run once
  returned "MEDIUM") must never silently skip the one safety net a
  wrong-HIGH would bypass. Only if confidence is LOW does the script convene
  a 3-way `em-judge` panel, in parallel.
- `em-lead` reconciles the analyst (+ judges, if run) into
  `<target>/.em-state/<run-id>/dispatch-plan.md`, updates the
  `<target>/.em-state/LATEST-dispatch` pointer — the per-item dispatch spec
  (provisional branch/worktree per `provision_worktrees.py`'s formula, the
  exact self-contained dispatch prompt with the protocol block from
  `templates/dispatch-protocols.md` baked in verbatim), and the merge order
  — all via its own `Write` tool, unchanged. **Dispatch prompts never carry
  a mode token, in any mode** — `team-build` parses no mode tokens anymore
  and runs fully autonomous regardless (its own "No gates, no modes"
  section). Auto-pilot here changes only *this* skill's own PREFERENCE gates
  (Steps 3 and 5 below), nothing downstream.

The run goes silent in this session until it completes; say so before
starting it. It returns an object (`decisionType`, `disagreementNoted`,
`flaggedForHuman`, `panelRan`); use it in Step 3 below.

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
choice to `<target>/dispatch-decisions.md` as `DECIDED-AUTO` via
`~/.claude/skills/team-decisions/scripts/add_decision.py` (canonical,
parseable block shape; it creates the file if needed — see
`templates/decision-log.md`'s header note), state it plainly when
reporting back, and proceed to Step 4.

## Step 4 — Dispatch

For each item in a PARALLEL group, launch its delegate in the **same
message** as the other members of that group (multiple tool calls, one
message) — that's what makes them actually concurrent. **Concurrency
budget:** a PARALLEL group larger than ~3 skill-running delegates
dispatches in waves of ~2-3, next wave on the previous wave's terminal
reports — this environment hard-caps ~20 concurrent subagents and each
`team-build`/`team-intake` delegate spawns ~5-7 of its own (past runs have
hit this ceiling when dispatching more than a few at once and needed a
manual retry pass; see `memory/standing-constraints.md`). For SEQUENTIAL items,
launch only the first; launch each subsequent one after its predecessor
reports DONE (Step 5) — not on a timer, not all at once.

Each delegate is `Agent(subagent_type: "general-purpose", run_in_background:
true, prompt: <the exact dispatch prompt from dispatch-plan.md>)`. Never use
`subagent_type: "fork"` — the delegate needs none of this session's
conversation history, only the item's own on-disk plan/decisions, which is
the entire reason the pipeline keeps those documents authoritative.

Immediately after dispatching, write/update
`<target>/.em-state/dispatch-state.json` via
`scripts/em_state.py update` (schema-enforced — never hand-write the JSON;
its docstring is the schema's single source) — one entry per dispatched
item:

```json
{
  "<item-slug>": {
    "agent_id": "<from the Agent tool result>",
    "status": "IN_PROGRESS",
    "dispatched_at": "<from context, not computed>",
    "group": "parallel-1 | sequential | single",
    "branch": "<provisional, from dispatch-plan.md's spec>",
    "worktree": "<provisional, from dispatch-plan.md's spec>",
    "note": "<optional free text>"
  }
}
```

Branch/worktree start as the plan's provisional predictions; **overwrite
them with the actuals from the delegate's `DONE:` report** (the protocol
requires it to state them) — `provision_worktrees.py` owns the real naming,
and a past run recorded two different conventions in one file by trusting
predictions.

This file is what makes `status`/`resume` (and a later session, if this one
ends before everything finishes) able to reconstruct what's in flight without
re-deriving it from scratch — and it has a **second consumer**: `team-status`
checks `.em-state/*.json` so a mid-dispatch status run doesn't recommend
`team-build` on an item that already has a live delegate. Keep it current.

## Step 5 — Monitor and triage

As each dispatched delegate's background completion notification arrives,
read its final message and classify by the prefix `em-lead` had it use.
The build-delegate contract is **`DONE:` / `FAILED:` only** — `team-build`
runs fully autonomous and treats an un-proceedable state as a terminal
outcome, not a question, so a build delegate has nothing to pause on
(2026-08-14 downstream redesign; the old BLOCKED/`PENDING`-breadcrumb
round-trip is contractually impossible now):

- **`DONE: ...`** — mark that item `READY-TO-MERGE` in `dispatch-state.json`
  (via `em_state.py`), recording the **actual** branch/worktree from the
  report (overwriting the plan's predictions) and the verdict. If this was a
  SEQUENTIAL group's item and there's a next one queued, dispatch it now
  (back to Step 4).
- **`FAILED: ...`** — the delegate is relaying `team-build`'s own terminal
  outcome (unbuildable plan, red test already green, non-converging fix
  loop, broken environment) or a genuine wrapper failure. Report the stated
  reason to the user.
- **A `BLOCKED: ...` from a build delegate should no longer happen.** If one
  arrives anyway (a stale prompt, a confused delegate):
  🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate, stays in every mode,
  including auto-pilot.** Surface the exact question to the user
  immediately — don't batch it with unrelated items — get an answer, then
  `SendMessage` to that delegate's `agent_id` with the answer (this resumes
  the **same** delegate with full context). Mark the item `BLOCKED` → back
  to `IN_PROGRESS` in `dispatch-state.json` once resumed. Note in the
  report-back that a build delegate blocked at all — that's a contract
  violation worth knowing about.
- **A vague, non-terminal ending** ("I'll wait for the background jobs…")
  violates the protocol (two delegates did this on 2026-08-14). Verify the
  item's real state **read-only** — if the `worktree` skill is installed at
  `~/.claude/skills/worktree/`, via
  `~/.claude/skills/worktree/scripts/worktree_status.py` (it cannot collide
  with anything); otherwise via plain read-only git (`git -C <worktree>
  status`, `git -C <worktree> log -1`) against that worktree — **never**
  by running ad hoc tests against a shared resource (a shared test DB, a
  shared stack) while the delegate may still be active; the orchestrator's
  own verification `pytest` against a shared DB has caused a wave of false
  failures before. Then `SendMessage` the delegate to finish and report a
  terminal prefix, explicitly telling it not to repeat the pattern.

On a genuine `FAILED:`, continue:
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
Ask whether to retry (a fresh `Agent` call, same dispatch prompt — the
worktree/branch and any partial progress are still on disk, so a fresh
delegate isn't starting from zero even though it's a new agent ID) or hand
the item back for manual investigation. Mark accordingly. **Under
auto-pilot,** skip the ask once: auto-retry with a fresh delegate (same
dispatch prompt), log it `DECIDED-AUTO`, and state
the retry in the report-back. **If that retry also reports `FAILED:`**,
this stops being a preference — escalate to a hard stop and surface it to
the user regardless of mode; don't auto-retry a second time.

Keep `dispatch-state.json` current after every transition — it's the only
durable record if this session ends mid-flight.

## Step 6 — Merge

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **stays a hard stop in every mode,
including auto-pilot.** Merging into the project's actual default branch is
exactly the kind of hard-to-reverse, shared-state action this environment's
own standing safety floor exists for — the same floor `team-build`'s
"No gates, no modes" section names as the one thing that never bends (no
force-push, no `--no-verify`, no push/merge straight to the default branch;
also canonical in `substrate-core/references/gates.md`, "The safety
floor"). Auto-pilot speeds up everything *before* this point; it does
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
status scope if one is configured, same as `wrap-up`'s Step 7.5 ("Refresh
team-status (when configured)") — so the
next bare "next" reflects what actually shipped instead of paying a stale
rediscovery cost.

## Step 8 — Report back and record

One summary: the decision made (grouping + why), each item's outcome
(merged / still open / failed), any BLOCKED questions that came up and how
they were answered, and the merge commits. Then append one row to the run
log **via `scripts/append_em_run_log_row.py` — never hand-typed** (location:
`PROJECT-CONTEXT.md`'s "Dispatch run-log" entry if this project names one,
else this plugin's own bundled `memory/dispatch-run-log.md`; the
script creates the file with the standard header if it doesn't exist yet).
Keep every cell terse — the plan in `.em-state/<run-id>/` and each item's
own decisions.md carry the narrative. **If this run learned a durable,
project-invariant constraint** (a shared DB, a shared registry, an
environment ceiling), append it to `memory/standing-constraints.md` too —
the run log is a ledger, not a memory anyone re-reads; standing-constraints
is what `em-analyst` actually loads next run.

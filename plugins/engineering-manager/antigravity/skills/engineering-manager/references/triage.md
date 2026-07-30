# triage

Sorts a folder's outstanding work into three tracks and moves the first two
along — you (the orchestrator) run every step directly except where an agent
is named, same discipline as `dispatch.md`.

> **Note:** the dispatch/monitor/resume mechanics described below — launching
> a delegate with `Agent(subagent_type: "general-purpose", run_in_background:
> true, ...)` and resuming a `BLOCKED:` delegate later via `SendMessage` to
> its `agent_id` with full context preserved — are Claude Code's `Agent` tool
> mechanics. This is **unverified for Antigravity**; adapt the steps below to
> whatever delegation/resume mechanism Antigravity actually supports.

## Step 0 — Resolve the target and read its state

Same folder-resolution as `dispatch`: use the given folder, or check
`PROJECT-CONTEXT.md`'s "Default status scope." Read that folder's
`status-report.md`.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate, stays in every mode,
including auto-pilot.**
If `status-report.md` doesn't exist, or its run date is old enough that you
wouldn't trust it, tell the user to run `team-status` first — `triage`
consumes that report's own re-verified findings, it doesn't re-derive them.
Don't triage from a stale or missing report. There's nothing to recommend
against a report that isn't trustworthy.

## Step 1 — Bucket every outstanding action item

Walk the Stage-map, the Merged-item follow-ups table, and the Recommended
next action / backlog section. For each concrete, nameable action item,
assign exactly one bucket:

**HOUSEKEEPING** — the report already states the correct replacement fact
(a merge that happened but the build-report still says "unmerged," a
catalog entry with stale phrasing, a superseded back-out command). Signal:
follow-up type `DOC CLEANUP` or `COSMETIC`, or a backlog line that names the
exact file and the exact correction with no remaining ambiguity. If the
"correction" would require a judgment call about wording, phrasing choice,
or scope — not just substituting a fact — it's not housekeeping; downgrade
it to NEEDS-INTAKE.

**NEEDS-INTAKE** — real outstanding work with no `technical-plan.md` yet.
Signal: follow-up type `FUTURE SCOPING` or `DEPENDS-ON-ITEM`, or an
`OPERATIONAL` item that turns out (read the report's own description) to be
a code/config/script fix rather than something requiring credentials or
production access. A live defect the rescan itself found (a test that
should be passing but isn't, code behaving differently than its own spec)
belongs here too — even if urgent, it still needs a plan before it needs a
build.

**NEEDS-HUMAN** — requires production/live-data access, repo-admin/GitHub
settings, credentials, or is explicitly named in the report as the user's
own decision to make (a DEC-id awaiting their sign-off, a live-risk fix
touching real customer/production data). Never dispatch these — list them
plainly in your report-back.

If a single item's note contains a mix (e.g. "fix the doc AND file a
follow-up") split it into its own HOUSEKEEPING line and its own
NEEDS-INTAKE line — don't force one bucket to cover both halves.

## Step 2 — Group HOUSEKEEPING by file

List every HOUSEKEEPING correction with its exact file path. Any two
corrections touching the **same file** go in the same delegate (sequential
edits inside one agent call, not two concurrent ones — concurrent Edit
calls against the same file from two different agents can clobber each
other, since each reads-then-writes independently). Corrections in
different files can each be their own delegate, dispatched together in one
parallel batch. This grouping is mechanical — no `em-analyst` call needed;
just read the file paths.

## Step 3 — Analyze the NEEDS-INTAKE set (only if 2+ items)

If there's exactly one NEEDS-INTAKE item, skip straight to Step 5 with it as
a SINGLE-SESSION-shaped group of one — no analyst needed for a single item,
same as `dispatch`.

Run `em-analyst` on the NEEDS-INTAKE set. Since none of these have a
`technical-plan.md` yet, hand it each item's raw description/request text
(and any request-log/catalog entry that names it) instead — the analyst's
job here is: do any of these target the same code area closely enough that
one intake should see the other's conclusion first (SEQUENTIAL), are any
small enough and similar enough that combining them into one intake request
saves real overhead without muddying the ask (BATCHED — name which items
combine into one request document), or is everything independent enough to
run concurrently (PARALLEL)? Same LOW-confidence → `em-judge` panel rule as
`dispatch`.

## Step 4 — Synthesize

Run `em-lead` with the analyst's findings (+ judge votes, if run) plus the
HOUSEKEEPING grouping from Step 2. It writes `<target>/triage-plan.md` (see
`templates/triage-plan.md`): the housekeeping delegate list, the intake
grouping decision (PARALLEL/SEQUENTIAL/BATCHED/SINGLE-SESSION) with per-item
or per-batch dispatch specs, and the NEEDS-HUMAN list for the human gate to
see (not to dispatch).

**If this `triage` run is itself in auto-pilot,** tell `em-lead` so — it
bakes the same `auto`/`auto-pilot` token into each intake delegate's
dispatch prompt (e.g. "invoke the `team-intake` skill in `auto-pilot` mode
targeting `<path>`" instead of "invoke the `team-intake` skill targeting
`<path>`"), so the delegate's own preference gates auto-decide too instead
of a background delegate stalling on a gate nobody can answer.

## Step 5 — Human gate

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
Present `triage-plan.md` in chat: the housekeeping count and file groups,
the intake grouping/decision and why, and the NEEDS-HUMAN list. Letter the
choice:

- **A) Proceed as recommended** — dispatch housekeeping and intake exactly
  as written.
- **B) Adjust** — ask what to change (e.g. skip a bucket, re-batch two
  intake items, drop an item entirely), update the plan in-memory, then
  proceed.
- **C) Cancel** — stop here; nothing is dispatched.

Only continue past this point on A or B. It's fine to approve one bucket and
decline the other (e.g. "do the housekeeping now, hold off on intake") — say
so explicitly if the user's answer only covers part of the plan.

**Under auto-pilot,** skip the ask: auto-pick **A) Proceed as recommended**
for both buckets (housekeeping and intake both dispatch as written) unless
`triage-plan.md` itself flagged something for direct human attention, which
stays pulled out and surfaced in the report-back instead. Log the choice to
`<target>/triage-decisions.md` (from `templates/decision-log.md`, create if
it doesn't exist) as `DECIDED-AUTO`, state it plainly when reporting back,
and proceed to Step 6. The NEEDS-HUMAN bucket is never dispatched in any
mode — auto-pilot doesn't touch it.

## Step 6 — Dispatch

**Housekeeping delegates:** for each file group from Step 2, launch a
backgrounded, full-tool-access delegate with a fully self-contained prompt —
the file path(s), the exact old text and the exact new text (or the fact to
substitute) per correction, and an instruction to read the file first,
verify the current text still matches before editing (state may have moved
since the report was written), and report a before/after snippet. No
`team-intake`/`team-build` skill invocation, no BLOCKED protocol — there's
no decision to block on, only a missing-match to report back if the file no
longer says what was expected.

**Intake delegates:** for each PARALLEL/SEQUENTIAL/BATCHED group, launch a
backgrounded, full-tool-access delegate per item (or per batch, for BATCHED
groups) with a fully self-contained prompt: the project's root and
`PROJECT-CONTEXT.md` location, the request description, an instruction to
write a `request.md` under a new
`<target>/<new-item-slug>/` folder and then invoke the `team-intake` skill
targeting it, and this **BLOCKED protocol**, verbatim (same shape as
`dispatch`'s, adapted — there's no worktree/branch to reference, just the
folder):

> If at any point you need a decision only a human can make and it cannot
> be safely deferred or defaulted, STOP. Do not guess. End your turn with a
> final message that starts exactly with `BLOCKED:` followed by one clear
> sentence stating what decision is needed. If intake completes, end with
> `DONE:` followed by the folder path and a one-line summary of the
> resulting technical plan. If intake cannot proceed at all, end with
> `FAILED:` followed by what went wrong.

Launch every member of a PARALLEL group in the same message (multiple tool
calls, one message). For SEQUENTIAL, launch only the first; launch the next
after its predecessor reports DONE. For BATCHED, there's one delegate per
batch, not one per original item — the batch's own `request.md` lists each
original item as a separate ask within one document (see
`references/dispatch.md`'s Step 4 for the same "one message, multiple tool
calls" discipline that applies here).

Write/update `<target>/.em-state/triage-state.json` immediately after
dispatching (create the directory if needed) — same shape as
`dispatch-state.json` (`references/dispatch.md` Step 4), plus a `"kind":
"housekeeping" | "intake"` field per entry so `status`/`resume` can tell
which protocol applies.

## Step 7 — Monitor and triage

Same classification as `dispatch.md` Step 5 (`DONE:`/`BLOCKED:`/`FAILED:`
prefixes, including its auto-pilot handling — `BLOCKED:` stays a QUALITY
gate in every mode, `FAILED:` gets one auto-retry under auto-pilot before
escalating to a hard stop), applied to both housekeeping and intake
delegates — housekeeping delegates just won't ever report `BLOCKED:` in
practice, since there's nothing to block on. Keep `triage-state.json`
current after every transition.

## Step 8 — Report back and record

One summary: how many housekeeping items closed (and what each corrected),
the intake grouping decision and each item's outcome (folder path +
one-line plan summary, or still BLOCKED/FAILED), and the NEEDS-HUMAN list
presented again as a reminder (nothing was dispatched for these). Note
explicitly that any completed intake item is now a `dispatch` candidate on
the next run, not automatically queued. Then append one row to the same run
log `dispatch` uses (location: `PROJECT-CONTEXT.md`'s "Dispatch run-log"
entry if named, else this plugin's own bundled
`~/.gemini/config/plugins/engineering-manager/skills/engineering-manager/memory/dispatch-run-log.md`
(if your actual install root differs, see this skill's `SKILL.md` Path
note)) — date ·
target · housekeeping count · intake decision + items · NEEDS-HUMAN count ·
outcomes.

**`triage` does not run `dispatch.md`'s Step 6/7** (merge, refresh
`team-status`) — intake delegates don't produce anything to merge, and
re-running `team-status` right after triage would just re-discover the same
report it started from, since nothing built or merged yet. Suggest the user
run `team-status` again once any dispatched intake work lands a plan, so the
next `dispatch` sees accurate build-ready candidates.

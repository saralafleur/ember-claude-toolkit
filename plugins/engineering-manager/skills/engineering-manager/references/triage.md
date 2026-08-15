# triage

Sorts a folder's outstanding work into three tracks and moves the first two
along — you (the orchestrator) run every step directly except where an agent
is named, same discipline as `dispatch.md`.

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

**Alternate entry path (exercised 2026-07-28→29, legitimate):** a fresh
request set the user types or hands over directly is a valid candidate
source with no status-report at all — the staleness gate above guards
*report-derived* facts, and a user-stated request set has none. In that
case there is usually no housekeeping bucket (nothing verified stale);
bucket the user's items as NEEDS-INTAKE/NEEDS-HUMAN as usual and proceed
from Step 3, saying plainly in the report-back that this run triaged a
direct request set, not a report.

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

**Deliberately no NEEDS-QA bucket — updated 2026-08-15.** The *pre-build*
QA gap no longer needs any routing at all: an item with a
`technical-plan.md` but no `test-plan.md` is already a `dispatch` candidate
(dispatch's filter is Intake✅ + Build❌/➡️ — `team-build` auto-runs
`team-qa` on a missing test-plan, see `dispatch.md` Step 0), so just note
that dispatch will pick it up. The case that *does* need a route is
**post-build QA debt**: an item whose stage is `build-green-with-qa-debt`
(a build shipped with QA deliberately deferred). None of the three buckets
fits it — it isn't housekeeping, it has a technical-plan so it isn't
NEEDS-INTAKE, and no human is required. Report it plainly as outstanding
and name **`team-qa` on that item's folder** as its next step (the deferred
QA run is the recorded debt coming due) — but don't invent a dispatch path
for it here; running team-qa is a one-skill action the user (or a plain
session) invokes directly.

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
other, since each reads-then-writes independently). This grouping is
mechanical — no `em-analyst` call needed; just read the file paths.

**Size the fan-out to the work (2026-08-15, ratifying real-run practice):**
- **Fewer than ~3-4 corrections:** don't dispatch at all — apply them
  directly in-session (verify each old-text match live first, same as a
  delegate would), and say so in the report-back. Many agent round-trips
  for a handful of mechanical edits is the shape to avoid.
- **Larger sets:** dispatch one delegate per *file group*, but prefer one
  delegate walking several small file groups sequentially over one delegate
  per file — the per-file clobber protection above is about concurrent
  writers to the same file, not about maximizing delegate count.

## Step 3-4 — Run the decide pipeline (only if 2+ NEEDS-INTAKE items)

If there's exactly one NEEDS-INTAKE item, skip straight to Step 5 with it as
a SINGLE-SESSION-shaped group of one — no analyst needed for a single item,
same as `dispatch`. **Do not call the workflow below for a single item.**

Otherwise, gather what `em-analyst` needs: since none of these have a
`technical-plan.md` yet, each item's raw description/request text (plus the
project's own request-log entry if `PROJECT-CONTEXT.md` names one, else
whatever lives in the item's own `intake/*/` folders — the *global*
request-log was retired 2026-08-14; the only surviving global registry is
team-intake's `decision-log.md` fallback), and
this plugin's own bundled `memory/standing-constraints.md`.

Then run the decide pipeline — analyst, the conditional judge panel, and
synthesis — as one call:

```
Workflow({
  scriptPath: "~/.claude/skills/engineering-manager/workflows/decide.js",
  args: {
    kind: "triage",
    targetDir: "<target>",
    runId: "<YYYY-MM-DD>-<run-slug>",
    candidates: [ {slug, path, note?}, ... ],  // each item's raw request text/path
    standingConstraintsPath: "~/.claude/skills/engineering-manager/memory/standing-constraints.md",
    housekeepingGrouping: <Step 2's file-grouped housekeeping list>
  }
})
```

(Under a plugin install, `scriptPath` is
`${CLAUDE_PLUGIN_ROOT}/skills/engineering-manager/workflows/decide.js`
instead — same "Path note" translation as elsewhere in this repo.)

This one call replaces what used to be two separate steps — analyzing the
NEEDS-INTAKE set and synthesis. The mechanics are all still true, just
executed by the script now instead of by you:
- `em-analyst`'s job here: do any of these target the same code area closely
  enough that one intake should see the other's conclusion first
  (SEQUENTIAL), are any small enough and similar enough that combining them
  into one intake request saves real overhead without muddying the ask
  (BATCHED — naming which items combine), or is everything independent
  enough to run concurrently (PARALLEL)?
- Same LOW-confidence → `em-judge` panel rule as `dispatch`, including its
  input validation: **any confidence rating other than an explicit HIGH is
  treated as LOW (the panel convenes)** — never let an out-of-vocabulary
  rating (e.g. "MEDIUM") silently skip the panel.
- `em-lead` writes `<target>/.em-state/<run-id>/triage-plan.md` and updates
  the `<target>/.em-state/LATEST-triage` pointer (see
  `templates/triage-plan.md` for section order): the housekeeping delegate
  list (passed in as `housekeepingGrouping`, not derived by the agent), the
  intake grouping decision with per-item or per-batch dispatch specs, and
  the NEEDS-HUMAN list for the human gate to see (not to dispatch) — all via
  its own `Write` tool, unchanged. **Dispatch prompts never carry a mode
  token, in any mode** — `team-intake` runs fully autonomous regardless and
  accepts legacy tokens only as no-ops. Auto-pilot here changes only *this*
  skill's own PREFERENCE gates (Step 5 below), nothing downstream.

The run goes silent in this session until it completes; say so before
starting it. It returns an object (`decisionType`, `disagreementNoted`,
`flaggedForHuman`, `panelRan`); use it in Step 5 below.

**If the decision is SINGLE-SESSION** (nothing benefits from splitting):
present that recommendation and stop — same rule as `dispatch.md` Step 2 —
suggesting the user run `team-intake` (or make the fix) normally. The one
exception, exercised 2026-07-27: for an item that is small, fully
diagnosed, and would gain nothing from a `team-intake` pass, you may
instead propose handling it **directly in this session** at the Step 5
gate — but only with the user's explicit in-chat approval of exactly that,
and the direct work then gets reported and logged like any dispatched
outcome. Never silently edit product code on a SINGLE-SESSION verdict
without that approval.

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
`<target>/triage-decisions.md` as `DECIDED-AUTO` via
`~/.claude/skills/team-decisions/scripts/add_decision.py` (canonical
parseable shape; creates the file if needed — see
`templates/decision-log.md`'s header note), state it plainly when reporting
back, and proceed to Step 6. The NEEDS-HUMAN bucket is never dispatched in
any mode — auto-pilot doesn't touch it.

## Step 6 — Dispatch

**Housekeeping delegates** (only when Step 2's threshold says to dispatch
at all — below ~3-4 corrections, do them directly in-session instead): for
each file group, launch
`Agent(subagent_type: "general-purpose", model: "haiku",
run_in_background: true)` with a
fully self-contained prompt — the file path(s), the exact old text and the
exact new text (or the fact to substitute) per correction, and an
instruction to read the file first, verify the current text still matches
before editing (state may have moved since the report was written), and
report a before/after snippet. The cheap/fast model tier is deliberate
(2026-08-15 audit): the judgment already happened upstream — `team-status`
verified the facts and Step 2 did the grouping — so the delegate's work is
a fully-specified mechanical substitution plus the verify-before-edit
re-check. No `team-intake`/`team-build` skill
invocation, no BLOCKED protocol — there's no decision to block on, only a
missing-match to report back if the file no longer says what was expected.

**Intake delegates:** for each PARALLEL/SEQUENTIAL/BATCHED group, launch
`Agent(subagent_type: "general-purpose", run_in_background: true)` per item
(or per batch, for BATCHED groups) with a fully self-contained prompt: the
project's root and `PROJECT-CONTEXT.md` location, the request description,
an instruction to write a `request.md` under a new
`<target>/<new-item-slug>/` folder and then invoke the `team-intake` skill
targeting it (bare path, no mode token), and the **intake-delegate protocol
block from `templates/dispatch-protocols.md`, pasted verbatim** — the
single source for the `BLOCKED:`/`DONE:`/`FAILED:` contract, including the
durable `request-blocked.md` record an early-blocking delegate must write
first and the no-vague-non-terminal-endings rule.

Launch every member of a PARALLEL group in the same message (multiple tool
calls, one message) — but respect the **concurrency budget**: groups larger
than ~3 skill-running delegates dispatch in waves of ~2-3, next wave on the
previous wave's terminal reports (each `team-intake` delegate spawns ~5-7
sub-agents of its own against this environment's hard ~20-concurrent
ceiling; the 2026-08-13 run fired 12 at once and needed a manual retry
pass — see `memory/standing-constraints.md`). For SEQUENTIAL, launch only
the first; launch the next
after its predecessor reports DONE. For BATCHED, there's one delegate per
batch, not one per original item — the batch's own `request.md` lists each
original item as a separate ask within one document (see
`references/dispatch.md`'s Step 4 for the same "one message, multiple tool
calls" discipline that applies here).

Write/update `<target>/.em-state/triage-state.json` immediately after
dispatching, via `scripts/em_state.py update` (schema-enforced — never
hand-write the JSON): the **same slug-keyed shape as
`dispatch-state.json`** (`references/dispatch.md` Step 4), plus a `"kind":
"housekeeping" | "intake"` field per entry so `status`/`resume` can tell
which protocol applies. (A pre-2026-08-15 triage-state.json may have an
older ad hoc top-level shape — `em_state.py show` flags such files loudly;
read them by hand, don't rewrite history.)

## Step 7 — Monitor and triage

Same classification as `dispatch.md` Step 5 (`DONE:`/`BLOCKED:`/`FAILED:`
prefixes, including its auto-pilot handling — `BLOCKED:` stays a QUALITY
gate in every mode, `FAILED:` gets one auto-retry under auto-pilot before
escalating to a hard stop, and a vague non-terminal ending gets the same
read-only verification + explicit resume treatment), applied to both
housekeeping and intake delegates. Housekeeping delegates won't ever report
`BLOCKED:` (nothing to block on), and an intake delegate reporting it
should be rare now that `team-intake` proceeds on recorded assumptions —
when it does happen, the delegate wrote its question to
`request-blocked.md` (or the intake `decisions.md`) first, per the
protocol, so the question survives this session. Keep `triage-state.json`
current after every transition (via `em_state.py`).

## Step 8 — Report back and record

One summary: how many housekeeping items closed (and what each corrected),
the intake grouping decision and each item's outcome (folder path +
one-line plan summary, or still BLOCKED/FAILED), and the NEEDS-HUMAN list
presented again as a reminder (nothing was dispatched for these). Note
explicitly that any completed intake item is now a `dispatch` candidate on
the next run, not automatically queued (true since 2026-08-15's filter
change: dispatch requires Intake ✅ + Build ❌/➡️ — no QA stage in
between). Then append one row to the same run
log `dispatch` uses, **via `scripts/append_em_run_log_row.py` — never
hand-typed** (location: `PROJECT-CONTEXT.md`'s "Dispatch run-log"
entry if named, else
this plugin's own bundled `memory/dispatch-run-log.md`; the
script creates the file with the standard header if needed). Keep cells
terse — the run's `.em-state/<run-id>/` plan carries the narrative — and
promote any durable project-invariant lesson to
`memory/standing-constraints.md`, which is what future runs actually load.

**`triage` does not run `dispatch.md`'s Step 6/7** (merge, refresh
`team-status`) — intake delegates don't produce anything to merge, and
re-running `team-status` right after triage would just re-discover the same
report it started from, since nothing built or merged yet. Suggest the user
run `team-status` again once any dispatched intake work lands a plan, so the
next `dispatch` sees accurate build-ready candidates.

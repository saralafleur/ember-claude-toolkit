---
name: team-status
description: 'Run a virtual delivery-status team over a folder in a project''s delivery pipeline and answer "where are we, and what do we invoke next?" — on any project. Use when: you open a batch or an intake-base folder and need to know the true current state of every work item in it; a plan/report might be stale and you want it re-verified against the live code, not just re-read; you are picking up work someone else (or a past session) produced and need to reconstruct it; or you want a single, current status-report.md that says which of team-intake / team-qa / team-build / librarian to run next and why. Also trigger on short, bare prompts asking to reconstruct current state and the next step — e.g. "next", "next?", "what''s next", "where are we", "where are we at", "status check", "status" — even with no folder named (Step 0 resolves the folder from PROJECT-CONTEXT.md or asks). Produces one status-report.md per run and a thin run-log, and it NEVER changes product code, plans, or tests — it is read-only and advisory.'
argument-hint: 'Path to the folder to assess (a whole batch, or a single intake-base folder). Optional — will ask if omitted.'
---

# Team Status

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

## The team (first-class agents, installed globally at `~/.claude/agents/`)
| Agent | Role |
|-------|------|
| `status-triage` | Resolve scope; enumerate every work item in the folder and inventory which artifacts each has; gate on an empty/unreadable target |
| `status-scanner` | Per item (fanned out): reconcile intent vs. last-reported state, **re-verify the claims against the live code**, classify the stage, flag drift |
| `status-lead` | Synthesize all items into `status-report.md` and name the single next action (which skill, on which folder, why) |

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-status/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-status/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

> **How to invoke each role:** these are registered subagent types — launch
> each with `subagent_type: "<name>"` (e.g. `subagent_type: "status-scanner"`).
> Always give the agent: the target folder, the output path for the report,
> and (for scanners) the specific item folder it owns. (If a name isn't
> available as a subagent type, fall back to a `general-purpose` agent and
> paste the role brief from `~/.claude/agents/<name>.md`.)

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

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
**Only if no path was given AND no PROJECT-CONTEXT.md default exists, STOP
and ask:** "Which folder should I assess — a whole batch, or a single
intake-base folder? I'll reconstruct the true current state and write a
`status-report.md` there." If the shape is genuinely ambiguous, state the
interpretation you're taking and proceed; don't stall on it.

**Output location:** write `status-report.md` at the **root of the target
folder** (so a batch gets one roll-up report, a single item gets its own).
Never write it into a repo root or into another team's `intake/qa/build`
subfolder.

### Step 0.5 — Cache-first fast path (skip triage/scan entirely when nothing changed)
Before running `status-triage`, check whether the last run's report is still
an exact match for reality. This is the whole point of caching: a bare
"next" that finds nothing changed should cost **zero agent calls** — not one
triage call plus however many scanners. Re-verification against live code
still happens, just only when something has actually moved.

**How:**
1. If `<target>/status-report.md` does not exist, there is no cache — skip
   straight to Step 1 (first run, nothing to trust yet, everything is
   effectively RESCAN).
2. If it exists, read its write timestamp (`LAST_RUN`) and run two cheap,
   local checks — no agents, just `git`/`find`:
   - **Committed changes:** `git -C <repo-root> log --since="<LAST_RUN>"
     --oneline -1 -- <target>` in each relevant repo (the target's own repo
     plus any product-code repos named in `PROJECT-CONTEXT.md`'s repo
     topology). Any hit at all means *something* under the target or the
     product code changed.
   - **Uncommitted / untracked changes.** A report can go stale before
     anything is ever committed — e.g. a build-lead drops a new
     `build-report.md` that hasn't been committed yet. Committed-only
     checking misses this, so also run:
     `find <target> -newer <target>/status-report.md -not -path
     '*/.status-scratch/*' -type f` and `git -C <repo-root> status
     --porcelain -- <target>`. Either returning anything counts as a hit.
     (Exclude `.status-scratch/` from the `find` — those files are the
     *output* of the last scan, not a change to detect; without the
     exclusion every run would falsely detect "change" from its own
     previous scratch writes.)
3. **If both checks are empty everywhere** — nothing changed anywhere in the
   target or the product repos since the cached report was written — skip
   triage and scanning entirely. Read the existing `status-report.md` and
   present its stage-map and recommended next action to the user as-is (see
   Step 4's "fully cached" variant). State the report's timestamp and that
   nothing has changed since. Stop here — do not launch any agent.
4. **If either check finds anything**, proceed to Step 1 (triage) as
   normal — something needs a closer look, but exactly *what* gets scoped
   precisely in Step 1.5, not assumed to be everything.

**Force-rescan override:** if the user passes `--force` or says "force
rescan" / "re-verify everything", skip this step entirely and go to Step 1
with every item pre-marked RESCAN.

### Step 1 — Triage (gate)
Run `status-triage` on the target folder. It walks the tree, enumerates every
work item (each distinct `intake/<date>-<slug>/` it finds, at any depth), and
for each records the **artifact inventory** — which of these exist:
`technical-plan.md`, project-specific plan docs, `request-brief.md`,
`qa/test-plan.md`, `qa/qa-assessment.md`, `build/**/build-report.md`,
`decisions.md`. This is pure inventory — no judgment yet. It writes nothing
but returns the item list + a `READY` / `BLOCKED` verdict.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- **BLOCKED** only if the target doesn't exist, is empty, or contains nothing
  that looks like pipeline work. Surface that to the user (plain text or
  `AskUserQuestion`) and stop — don't fan out scanners over nothing.
- **Log every clarifying/blocking question and its answer** (see "Decision
  logging").

### Step 1.5 — Per-item change detection, then ask before scanning
Reaching this step means Step 0.5 already found *something* changed
somewhere (or this is the first-ever run) — now scope precisely *which
items* need a scanner, and **ask before spending any scanner calls on
them.** This avoids the failure mode of "one file changed, so silently
re-verify all fifteen items" — rescanning is an explicit choice, not the
silent default.

**How:**
1. Use the same `LAST_RUN` timestamp from Step 0.5 (or, on a first-ever run
   with no prior report, treat every item as RESCAN-CANDIDATE and skip
   straight to the ask in step 5 — there's no cache to weigh against).
2. For each work item returned by triage, run both of Step 0.5's checks
   scoped to that item's own folder:
   - `git -C <repo-root> log --since="<LAST_RUN>" -- <item-folder-path>`
   - `find <item-folder-path> -newer <target>/status-report.md -not -path
     '*/.status-scratch/*' -type f` and `git -C <repo-root> status
     --porcelain -- <item-folder-path>`
   If the project spans multiple repos, run the git checks in each relevant
   repo — a build's product-code commits often land in a different repo
   than the item's own progress folder.
3. **If neither check finds anything** for an item AND its scratch file
   `<target>/.status-scratch/<item-slug>.md` exists from a previous run →
   mark the item **SKIP** (carry forward the previous finding verbatim).
4. **If either check finds something, OR the scratch file is missing** →
   mark the item **RESCAN-CANDIDATE** — provisionally; step 5 below can still
   downgrade it to SKIP if the touch turns out to be cosmetic.
5. **Fingerprint re-check — filter out cosmetic touches before asking.** A
   file's mtime moving doesn't mean a *claim* changed: someone may have just
   fixed a typo, added a pointer note, or corrected a stale "unmerged" line to
   say "merged" (the doc catching up to reality the scanner already knew).
   Re-verifying live code for a pure wording fix wastes a scanner call. So for
   every item marked RESCAN-CANDIDATE **whose scratch file already exists**
   (skip this for items with no prior scratch — nothing to compare against),
   cheaply re-extract the same fingerprint fields the scanner recorded last
   time (see Step 2's "Write a fingerprint") from the *current* file content —
   no agent, just `grep`/`git`:
   - **Verdict:** `grep -m1 -E '^\*\*Verdict:\*\*' <build-report.md>` → the
     GREEN / GREEN-WITH-CAVEATS / BLOCKED token.
   - **Decisions:** for each `## DEC-<n>` heading in `decisions.md`, grep the
     following `- **Status:**` line → collect as `DEC-n:STATUS` pairs.
   - **Test numbers:** `grep -oE '[0-9]+/[0-9]+' <build-report.md> | sort -u`.
   - **Merged:** if the fingerprint recorded a `merged_commit`, run
     `git -C <repo-root> merge-base --is-ancestor <merged_commit> <default-branch-HEAD>`
     — cheap, deterministic, no agent needed.

   Compare each freshly-extracted field to the value recorded in the scratch
   file's fingerprint:
   - **All fields match** (or the file simply doesn't conform to these
     markers at all — see safety note) is NOT enough on its own; only
     downgrade to **SKIP** when the fields *were extractable* on both sides
     **and matched exactly**. Note in the item's carried-forward finding that
     it was "touched at `<time>`, fingerprint re-checked and unchanged —
     treated as cosmetic" so this isn't silently invisible to the user.
   - **Any field differs** → stays **RESCAN-CANDIDATE**, a load-bearing claim
     actually moved.
   - **Safety fallback:** if a marker can't be found at all in the *current*
     file (irregular/non-template report, like a thin item with no
     `decisions.md`, or a build-report that doesn't follow the standard
     `**Verdict:**` line) — don't guess. Leave the item **RESCAN-CANDIDATE**.
     This check only ever *removes* scanner work when it's confident; it never
     invents confidence to save a call.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
6. **Ask before scanning.** Tell the user the split, and call out any items
   step 5 downgraded so that's visible, not silent: e.g. *"12 items unchanged
   since the last run (cache trusted), 2 items touched but confirmed
   cosmetic by fingerprint re-check (cache trusted): `uat-061826-topr-changes`
   (added a doc pointer, no claim changed), `committee-about-restructure`
   (build-report touched but verdict/decisions/test-numbers unchanged) — 1
   item shows a real change: `getmodsbyoffice-idor-scoping-gap` (verdict text
   in build-report.md changed)."* Then use `AskUserQuestion` with three
   options:
   - **Rescan only the flagged items (recommended)** — launch scanners for
     RESCAN-CANDIDATE items only; SKIP items carry forward their cached
     scratch verbatim.
   - **Trust cache, report as-is** — skip scanning even the flagged items;
     reuse the stale scratch/report content for everything, explicitly
     flagged as unverified-since-`LAST_RUN` in the output.
   - **Force full rescan of all items** — ignore SKIP/RESCAN-CANDIDATE
     entirely, scanner on every item regardless of what changed.

   **Skip this ask** (go straight to "rescan the flagged items") when: the
   user's invocation already said `--force` / "force rescan" / "re-verify
   everything"; or this is the first-ever run (nothing cached to offer as
   an alternative — there's no real choice to present).

**Safety:** if `git` is unavailable in the target repo, treat all items as
RESCAN-CANDIDATE and note it in the ask (don't silently skip verification).

### Step 2 — Scan (parallel fan-out, one scanner per item)
Launch one `status-scanner` **per item the Step 1.5 answer selected for
scanning** in parallel (one message, multiple tool calls) — this is the
RESCAN-CANDIDATE set if the user picked "rescan flagged," all items if they
picked "force full rescan," or none at all if they picked "trust cache"
(skip straight to Step 3 with every scratch file used as-is). Items not
selected for scanning use their existing scratch file, passed directly to
Step 3. Give each scanner: its item folder, the artifact inventory from
triage, and the shared-memory paths. Each scanner
does the load-bearing work — **read-only, but not passive:**
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
- **Write a fingerprint.** At the top of the scratch file, before the
  narrative, record the load-bearing facts as of this scan in a small
  frontmatter block — this is what next run's Step 1.5 fingerprint re-check
  compares against, so a future doc-only touch-up doesn't cost another
  scanner call:
  ```yaml
  ---
  fingerprint:
    verdict: GREEN | GREEN-WITH-CAVEATS | BLOCKED | n/a
    merged: true | false
    merged_commit: <hash> | null
    decisions: "DEC-1:DECIDED,DEC-2:PENDING" | "none"
    test_numbers: "319/319,731/731,14/14" | "none"
  verified_at: <run date>
  ---
  ```
  Fill each field from what you already verified — no extra work. Use `n/a`
  / `null` / `"none"` for anything the item's artifacts don't have (e.g. no
  `decisions.md`). Don't force a value onto a report that doesn't cleanly
  state one — an honest `n/a` is what makes the safety fallback in Step 1.5
  work correctly.
- Write findings to `<target>/.status-scratch/<item-slug>.md` (scratch, not
  the final report).

### Step 3 — Synthesize + report
Run `status-lead` with the triage inventory + every scanner's scratch file.
It writes `<target>/status-report.md` (from `templates/status-report.md`): a
stage-map of every item with explicit **Intake / QA / Build / Merged**
columns (never a single enum label — "merged" is always its own yes/no, not
folded into a phrase like "build-green"), a **merged-item follow-up**
breakdown for every item that IS merged (classified `NONE` / `COSMETIC` /
`DOC CLEANUP` / `OPERATIONAL` / `DEPENDS-ON-ITEM` / `FUTURE SCOPING` — see
the template), the reconciled true state, open `PENDING`/`PARKED` decisions,
cross-item drift, a **parallelization opportunity** check (whether two or
more ready-to-build items are independent enough to run as concurrent
`team-build` worktree efforts, laid out as an Option A: concurrent / Option
B: sequential trade-off — never a unilateral pick), and — the point of the
whole skill — **the single recommended next action**: *which skill to invoke
(`team-intake` / `team-qa` / `team-build` / `librarian`), on which folder,
and why*, citing the concrete gap. It also appends one row to the status
run-log. Capture its headline recommendation and, if present, the
parallelization choice verbatim.

### Step 4 — Report back
Present the reconciled state **in chat as plain-text tables** (ASCII-style
markdown tables render fine and are what Sara has asked for — not a rendered
UI/artifact page unless she explicitly asks for one):
- **A numbered stage-map table** — columns `#` · `Item` · `Intake` · `QA` ·
  `Build` · `Merged` · `Notes`, using ✅ / ❌ / ➡️ per the template's legend.
  This is the primary "where are we" answer — lead with it. Number the rows
  so the user can say "run #3" to pick one without retyping its slug.
  **Always print the legend directly under the table** — never assume the
  icons are self-explanatory: `✅ done · ❌ not done / not applicable ·
  ➡️ partially done (e.g. built but never committed/merged, deliberately
  waived, or found incomplete)`.
- **A merged-item follow-up table** — only for rows where Merged = ✅, columns
  `#` · `Item` · `Type` · `What's left`, using the fixed taxonomy (`NONE` /
  `COSMETIC` / `DOC CLEANUP` / `OPERATIONAL` / `DEPENDS-ON-ITEM` /
  `FUTURE SCOPING`). This is what stops "merged" from reading as "fully
  done" — say explicitly which merged items are actually finished (`NONE`)
  vs. which still carry a live data/ops task or just stale report text.
  Omit this table if nothing is merged yet.
- **Anything the reports got wrong** — every place a plan/report claim was
  contradicted by the live re-verification (this is the highest-value
  output).
- **Open decisions** still `PENDING` / `PARKED`.
- **The single next action** — the skill to run next, the target folder, and
  the one-line why.
- Links to `status-report.md` and any per-item scratch worth reading.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
Then ask whether to proceed with the recommended next action (which means
invoking one of the *other* skills — out of scope for this one), or invite
the user to pick a row number from either table directly. Letter the
choice — e.g. **A)** proceed with the recommended next action, **B)** pick a
different row/item, **C)** something else — per the lettering convention
above.

**Fully cached variant (Step 0.5 found nothing changed, no agents ran):**
Skip the bullets above — there is no fresh reconciliation to summarize.
Instead state plainly: the target has had no changes since `status-report.md`
was last written at `<LAST_RUN>`; present that report's stage-map and
recommended next action as-is (clearly labeled as cached, not re-verified
this run); and mention that a full rescan can be requested (`--force` /
"force rescan") if they want it re-verified anyway despite no detected
changes.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
**If `status-lead` found a parallelization opportunity** (two or more
independent build-ready items), do not fold that into the same yes/no —
put it to the user as its own explicit choice via `AskUserQuestion` with
three options:

- **Option A — fresh chats, one per item (recommended default).** For each
  item, generate a short, fully self-contained kickoff line:
  `Run team-build on <absolute path to the item's intake-base folder>`
  — nothing else. Print all N kickoff lines as separate copy-paste blocks in
  the chat reply. Do **not** spawn any subagent for this option — the whole
  point is that the current session does nothing further; the user opens N
  new chat sessions and pastes one line into each. This works *because* the
  pipeline is designed for it: everything a fresh session needs
  (`technical-plan.md`, `pm-plan.md`, `decisions.md`) already lives on disk,
  so a cold session with zero conversation history can execute the build
  correctly from the path alone. If a kickoff line would need anything
  beyond the folder path to work, that's a signal the item's own plan/
  decisions docs are incomplete — fix the docs, don't patch around it by
  stuffing context into the kickoff line.
- **Option B — concurrent in this session.** Launch the named items as
  parallel agent calls in one message. Use a plain subagent call (e.g.
  `general-purpose`, or omit `subagent_type`) that invokes the `team-build`
  skill itself from a clean start — **never `subagent_type: "fork"` for
  this.** A fork inherits this session's *entire* conversation history as
  its starting context, and a long-running status/build session can easily
  be tens or hundreds of thousands of tokens deep — the fork pays that
  inheritance cost before it does a single second of the item's own work,
  on top of a task that (per Option A's own premise) needed none of it. Each
  concurrent branch still goes through its own `build-triage` for its own
  worktree, same as any single `team-build` run — just launched together.
  State the time-saved trade-off, and that results still land back in this
  session (which keeps growing this conversation's size).
- **Option C — sequential in this session.** One at a time, priority order.
  State the lower-review-load trade-off.

Let the user pick; there is no unilateral default beyond presenting A first.
Whichever is chosen, proceed accordingly.

## Decision logging
This is a read-only audit skill, so it rarely needs a decision from the
user — but when it does (scope is genuinely ambiguous at Step 0; or a report
is old and the underlying code has since changed and you must choose "trust
the report" vs. "re-verify from scratch"), record it so the call is
remembered. Two places:
1. **Per run:** `<target>/status-decisions.md` (from
   `templates/decision-log.md`) — the question, dated context, options, and
   the decision.
2. **Global:** the status-run-log row captures the run; note the decision
   there in one line.
Write it `PENDING` before asking; flip to `DECIDED` / `PARKED` once answered.

## Conventions
- **Human gates must be visible, not just asked.** At every 🟧 HUMAN GATE
  REQUIRED point, present the question as its own standalone callout in the
  actual chat reply — **include the literal `🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧`
  banner line**, not just the blockquote underneath it:

  > 🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
  >
  > **Human decision needed:** <the question>

  Never fold a gate's question into a narrative summary paragraph where it
  reads as background rather than a stop-and-wait point. If more than one gate
  applies in the same report-back, each gets its own banner + callout — do not
  merge them into a single generic "want me to proceed?".
- **When a gate offers a choice in plain chat text (not via `AskUserQuestion`),
  letter the options** — `**A)**`, `**B)**`, `**C)**`, etc. — so Sara can
  answer with a single letter instead of re-describing the option. This
  applies to every human gate in this skill that presents more than one
  path forward: Step 0's ambiguous-scope ask, Step 1.5's rescan-scope ask
  (when not using `AskUserQuestion`), Step 4's proceed-with-recommendation
  callout, and the parallelization-opportunity gate's Option A/B/C (already
  lettered — keep it that way). A gate with only one path (e.g. a plain
  yes/no "proceed?") doesn't need lettering — this is for genuine multi-way
  choices.
- **Cache-first, not verify-first.** `status-report.md` plus the
  `.status-scratch/` files it was built from ARE the cache. The default
  answer to a bare "next" is to read that cache and, if nothing has changed
  (Step 0.5), hand it back with zero agent calls. Rescanning is something the
  user opts into (Step 1.5's ask) when something has actually changed — never
  a silent default just because the skill was invoked again. This trades a
  small risk of a stale-but-undetected change (e.g. code fixed without
  touching any file under the target folder) for not burning a scanner call
  every single time "next" is typed; the tradeoff is worth it because the
  moment something *is* detected, re-verification still happens for real
  (see "The recurring trap this skill exists to catch" below) — caching only
  skips the re-verify step when there is genuinely nothing new to check.
- **Mtime detects a touch; the fingerprint decides if it was a *claim*.** A
  file's mtime moving (Step 1.5, steps 1–4) is deliberately a coarse,
  cheap trigger — it catches every edit, including pure doc cleanup that
  brings stale report text in line with what a prior scan already found true
  (exactly the kind of edit `status-lead`'s **DOC CLEANUP** follow-up type
  exists to name). Re-verifying live code for that kind of edit is wasted
  work. Step 1.5's fingerprint re-check (step 5) is the second, finer filter:
  it only trusts a match when the relevant field was cleanly extractable on
  both sides, and defaults to RESCAN-CANDIDATE the moment a file doesn't
  conform to the expected markers — it removes scanner work only when
  confident, never invents confidence to save a call.
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
- **Templates:** `~/.claude/skills/team-status/templates/`.
- **Memory:** the status run-log location comes from `PROJECT-CONTEXT.md` if
  the project names one; otherwise
  `~/.claude/skills/team-status/memory/status-run-log.md` (a cross-project
  fallback, append-only). It has no forked defect-catalog file — it reads the
  project's own if one is configured.
- **Repo layout is project-specific — check `PROJECT-CONTEXT.md` first**, or
  discover it. Verification commands run inside the project's actual repo(s).
- **`fork` is for work that genuinely needs this session's conversation —
  not a default delegation tool.** A fork inherits the *entire* current
  conversation as its starting context. For any item whose full context
  already lives on disk (which is the whole point of this pipeline's
  `technical-plan.md`/`pm-plan.md`/`decisions.md` discipline), delegating
  via `fork` means paying to re-read a potentially enormous session before
  the delegated work even starts — see Step 4's parallelization options for
  the concrete alternative (fresh chats, or a plain non-fork subagent call).

## The recurring trap this skill exists to catch
**A report is a claim as of when it was written — not the current truth.**
So the standing rule for this team: **re-verify every load-bearing claim
against the live code before repeating it, run the deferred/uncertain thing
rather than accepting the caveat, and treat every report as perishable.**
Never declare a folder "done" because a report says so. If this project has
captured durable lessons (a knowledge library, a defect catalog), check
`PROJECT-CONTEXT.md` for where they live and read them for context on
patterns this team has been bitten by before.

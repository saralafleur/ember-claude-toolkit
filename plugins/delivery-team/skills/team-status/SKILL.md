---
name: team-status
description: 'Run a virtual delivery-status team over a folder in a project''s delivery pipeline and answer "where are we, and what do we invoke next?" — on any project. Use when: you open a batch or an intake-base folder and need to know the true current state of every work item in it; a plan/report might be stale and you want it re-verified against the live code, not just re-read; you are picking up work someone else (or a past session) produced and need to reconstruct it; or you want a single, current status-report.md that says which of team-intake / team-qa / team-build / librarian to run next and why. Also trigger on short, bare prompts asking to reconstruct current state and the next step — e.g. "next", "next?", "what''s next", "where are we", "where are we at", "status check", "status" — even with no folder named (Step 0 resolves the folder from PROJECT-CONTEXT.md or asks). Produces one status-report.md per run and a thin run-log, and it NEVER changes product code, plans, or tests — it is read-only and advisory (except its own local, docs-only commits — see Step 4.5).'
argument-hint: '[<path> | auto|auto-pilot <path> | direct <path>] — path to the folder to assess (a whole batch, or a single intake-base folder). Optional — will ask if omitted. See "Run modes" for the auto-pilot/direct tokens.'
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
  - Workflow
  - Workflow(delivery-team:status-scan)
  - Agent(status-triage)
---

# Team Status

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

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
strictly read-only** (except its own local, docs-only commits — see
Step 4.5) — it reads code, runs *existing* tests/greps to verify claims, and
writes only its own report + run-log. It never edits product code, a plan, a
test, or another team's memory.

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

> **How the team actually runs:** `status-scanner` (fanned out) and
> `status-lead` (Steps 2–3) run inside one `Workflow` call —
> `workflows/status-scan.js` — not as `Agent` calls you make directly; the
> script invokes each by its registered subagent type and reuses these same
> agent files unchanged. `status-triage` (Step 1's fallback path only) is
> still a plain `Agent` call you launch yourself, since it may need to run
> before the workflow's inputs even exist.

## Run modes

Standard mode (bare `<path>`) is the default described in "Process" below:
the fixed 3-agent roster, every 🟧 gate stops and waits. Two optional modes
change that, and compose in either order:

| Mode | Token(s) | What changes |
|---|---|---|
| Auto-pilot | `auto-pilot`, alias `auto` | Every gate in "Process" is tagged **PREFERENCE**, **QUALITY**, or **required-input**. PREFERENCE gates no longer stop — the team decides on its own best recommendation (usually the option this skill already states as "recommended"), logs the choice to `status-decisions.md` as `DECIDED-AUTO`, and keeps going. The QUALITY gates — Step 1's `BLOCKED` (target doesn't exist or has nothing to assess) and Step 4.5's proposed-corrections gate (edits to third-party pipeline docs are never auto-applied) — still stop, in every mode. This skill stays strictly read-only and advisory in every mode — "proceeds" at Step 4 means it states the recommendation as decided rather than asking, it never starts invoking `team-intake`/`team-qa`/`team-build` itself; that boundary doesn't move. |
| Direct | `direct` | Accepted for consistency with the rest of the suite, but has little to trim here: the roster is already 3 agents (triage, per-item scanner, lead) and Steps 0.5/1.5 already do a more sophisticated version of what `director-of-engineering` would decide elsewhere — which items actually need a live re-check, fingerprinted down to the field. `director-of-engineering` is not invoked; `direct` behaves the same as standard mode for agent selection. |

## Process

### Step 0 — Resolve the scope
`team-status` assesses a **folder**. Two shapes are common; detect which:
- **Batch** — a folder holding *several* sibling work items, each in its own
  intake-base. Assess every item.
- **Single item** — one intake-base folder holding one item's
  `intake/`/`qa/`/`build/` trail. Assess just it.

Parse the skill argument for a leading mode token first — `auto`/
`auto-pilot` and/or `direct`, before the path (see "Run modes" above). Strip
whatever mode tokens are present; whatever remains is the path (which may
still be empty — this skill is one of the ones that can run with none given).

If the user gave a path, use it. **If no path was given, check for a default
before asking:** look for a `PROJECT-CONTEXT.md` at the project root — on a
bare "next" with no path, "the project root" means **the current working
directory's repo root** (an unstated cwd assumption until 2026-08-15: if the
session isn't sitting in the project, there is no default to find — ask).
Don't `Read` a large `PROJECT-CONTEXT.md` whole (a `PROJECT-CONTEXT.md` can
exceed the 256KB Read cap in practice); **Grep for the section anchors
you need** ("Default status scope", "Delivery pipeline artifacts") and Read
just those line ranges. If it names a "Default status scope" (or, failing
that, a "Delivery pipeline artifacts" folder), use that as the target —
state the interpretation you're taking ("no folder given — defaulting to
`<path>` per `PROJECT-CONTEXT.md`") and proceed without stopping.

**Stale sibling-report warning (2026-08-15):** once the target is resolved,
check whether a *different* `status-report.md` (with or without its own
`.status-scratch/`) exists in a sibling or ancestor folder of the same
project (`find <project-root> -name status-report.md -not -path
"<target>/*"` — cheap). A superseded target's report + cache otherwise sit
around indefinitely presenting themselves as current (a stale twin has been
found sitting one directory above a live target before). If found, say so in the
report-back, and offer — via Step 4.5's normal corrections gate — to
**tombstone** the stale one: replace its content with a one-line pointer to
the live target's report and note its `.status-scratch/` is dead. Never
tombstone silently.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **required-input, unaffected by any mode.**
**Only if no path was given AND no PROJECT-CONTEXT.md default exists, STOP
and ask:** "Which folder should I assess — a whole batch, or a single
intake-base folder? I'll reconstruct the true current state and write a
`status-report.md` there." If the shape is genuinely ambiguous, state the
interpretation you're taking and proceed; don't stall on it. No mode removes
this gate — there's nothing to recommend a target for.

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

**How (script-first, 2026-08-15):** run the whole checklist below in one
deterministic call — no agents, no hand-run command list:

```bash
bash ~/.claude/skills/team-status/scripts/check_staleness.sh <target> \
  [-r <repo-root>]... [-s <shared-doc-path>]...
```

Pass one `-r` per product-code repo from `PROJECT-CONTEXT.md`'s repo
topology and one `-s` per shared decision-log / defect-catalog /
request-log / run-log / release-log path it names (**Grep the file for
those section anchors — never whole-read it**; the `## Repo topology`
section is written by the `worktree` skill, its heading is canonical, and
its fenced yaml `members:` block is the thing to parse first). The script
prints `NO-CACHE` (first run → Step 1, everything RESCAN), `UNCHANGED`
(→ point 3 below), or `HIT:` lines (→ point 4 below). It encodes every
check in points 1–2 below — which stay as the specification, and as the
manual fallback if the script can't run:
1. If `<target>/status-report.md` does not exist, there is no cache — skip
   straight to Step 1 (first run, nothing to trust yet, everything is
   effectively RESCAN).
2. If it exists, read its write timestamp (`LAST_RUN`) and run two cheap,
   local checks — no agents, just `git`/`find`:
   - **Committed changes:** `git -C <repo-root> log --since="<LAST_RUN>"
     --oneline -1 -- <target>` in each relevant repo (the target's own repo
     plus any product-code repos named in `PROJECT-CONTEXT.md`'s repo
     topology). Any hit at all means *something* under the target or the
     product code changed — **except this skill's own prior-run commit**
     (2026-08-15, self-poisoning fix): ignore a commit only when *every*
     path it touches is `status-report.md`, `status-decisions.md`, or
     `.status-scratch/*` (Step 4.5's own artifacts — otherwise every
     committed run defeats the next run's fast path). A commit that touches
     those files *plus anything else* still counts as a hit — never widen
     this to "any commit that merely includes them."
   - **Uncommitted / untracked changes.** A report can go stale before
     anything is ever committed — e.g. a build-lead drops a new
     `build-report.md` that hasn't been committed yet. Committed-only
     checking misses this, so also run:
     `find <target> -newer <target>/status-report.md -not -path
     '*/.status-scratch/*' -not -path '*/.em-state/*' -not -name
     'status-decisions.md' -type f` and
     `git -C <repo-root> status
     --porcelain -- <target>`. Either returning anything counts as a hit.
     (Exclude `.status-scratch/` from the `find` — those files are the
     *output* of the last scan, not a change to detect; without the
     exclusion every run would falsely detect "change" from its own
     previous scratch writes. Exclude `.em-state/` for the same reason —
     it's `engineering-manager`'s dispatch bookkeeping, updated on every
     state transition, not a change to the work items themselves. Exclude
     `status-decisions.md` likewise — every auto-pilot run writes it
     *after* the report, so without the exclusion the fully-cached fast
     path is unreachable after any committed run.)
   - **Shared cross-team docs.** `<target>` and the product-code repos
     aren't the only place a load-bearing claim can go stale — a decision,
     a defect-catalog entry, or a request-log row can flip in a shared doc
     that lives entirely outside `<target>` (a project's cross-request
     `decision-log.md`, its recurring-issue/defect catalog, its
     `request-log.md`). A `status-report.md`'s own recommended-next-action
     routinely cites these, so a change there is exactly as load-bearing as
     a change under `<target>` itself — treating it as out of scope is how
     a cached report ends up citing a decision as still PENDING after it
     was actually ruled. For every path `PROJECT-CONTEXT.md` names as a
     shared decision-log / defect-catalog / request-log / run-log /
     release-log location, run the same two checks against it (`git log
     --since="<LAST_RUN>" --oneline -1 -- <path>`, `git status --porcelain
     -- <path>`), scoped to whichever repo actually contains it. Any hit
     counts the same as a hit under `<target>`. A cached "not yet released"
     claim about an item is exactly this kind of load-bearing fact — don't
     let it go stale just because the change landed in `release-log.md`
     instead of `decision-log.md`.
   - **The global-fallback logs too — all of them** (generalized 2026-08-15
     from a team-intake-only point-fix; workflow-audit structural 4). When a
     project doesn't name its own shared-log paths, the family's records of
     what happened to this project's items live in the skills' global
     fallback ledgers under `~/.claude/skills/*/memory/` — which are not in
     any git repo, so the git checks can't see them. Run an mtime check
     (`-newer <target>/status-report.md`) against **each** of:
     team-intake `memory/decision-log*.md` · team-decisions
     `memory/decisions-log.md` (the Step 0.5 hook that skill's SKILL.md
     documents — implemented here as of 2026-08-15) · team-release
     `memory/release-log.md` (how a Ready-for-Deployment item's "released"
     flip becomes visible) · engineering-manager
     `memory/dispatch-run-log.md` · team-build `memory/build-run-log-INDEX.md`
     + `memory/build-run-log/*.md` · team-qa `memory/qa-run-log.md`.
     Any hit counts the same as a hit under `<target>`.
     (`check_staleness.sh` runs this whole list automatically.)
   - **Cheap live-state probes (2026-08-15, efficiency F1).** Git/mtime
     detection is structurally blind to live-state drift — a container
     down for days, a dead venv, a DB migration head contradicting the
     docs — which is exactly what has historically forced rational
     force-full rescans. If `PROJECT-CONTEXT.md` names live-state probes
     (a "Status probes" / health-check section: container status, migration
     head, a health endpoint), run them here — a handful of one-command
     checks, no agents. A probe failure counts as a hit (and is itself a
     finding to surface), making weekly 40-scanner sweeps rarer. If the
     project names none, skip — don't invent probes.
3. **If all checks are empty everywhere** — nothing changed anywhere in the
   target, the product repos, or the shared cross-team docs since the cached
   report was written — skip triage and scanning entirely. Read the
   existing `status-report.md` and present its stage-map and recommended
   next action to the user as-is (see Step 4's "fully cached" variant).
   State the report's timestamp and that nothing has changed since. Stop
   here — do not launch any agent.
4. **If any check finds anything**, proceed to Step 1 (triage) as
   normal — something needs a closer look, but exactly *what* gets scoped
   precisely in Step 1.5, not assumed to be everything.

**Force-rescan override:** if the user passes `--force` or says "force
rescan" / "re-verify everything", skip this step entirely and go to Step 1
with every item pre-marked RESCAN.

### Step 1 — Triage (script first, agent as fallback; gate)
The inventory is pure enumeration — no judgment yet — so run it as a script
first (2026-08-15, workflow-audit structural 9):

```bash
python3 ~/.claude/skills/team-status/scripts/inventory_items.py <target> --json
```

It enumerates every work item (each distinct `intake/<date>-<slug>/` at any
depth) and each item's **artifact inventory** — which of these exist:
`technical-plan.md`, project-specific plan docs, `request-brief.md`,
`qa/test-plan.md`, `qa/qa-assessment.md`, `build/**/build-report.md`,
`decisions.md` — plus a `READY` / `EMPTY` / `BLOCKED` verdict (exit 0/2/3).

**Launch the `status-triage` agent only as fallback:** when the script exits
2 (`EMPTY` — a non-empty folder where the fixed glob found nothing; layouts
vary, and searching a nonstandard layout is the judgment residue the agent
exists for), or when you have concrete reason to distrust the glob for this
project's layout. On the script's happy path, its JSON output *is* the
triage inventory — no agent call. (Known triage-agent error classes —
nested double-counts, artifact-absence mis-stagings — are exactly what the
deterministic glob doesn't suffer from, and the scan path self-heals the
rest.)

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate, stays in every mode,
including auto-pilot.**
- **BLOCKED** only if the target doesn't exist, is empty, or contains nothing
  that looks like pipeline work. Surface that to the user (plain text or
  `AskUserQuestion`) and stop — don't fan out scanners over nothing. There's
  nothing to recommend when the target itself is empty or unreadable.
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
   Re-verifying live code for a pure wording fix wastes a scanner call.
   **Run it as one script call** (2026-08-15, workflow-audit structural 2 —
   this used to be ~5 hand-run greps per item per run):

   ```bash
   python3 ~/.claude/skills/team-status/scripts/fingerprint_check.py <target> \
     --item <item-path> [--item ...] --repo <repo-root>
   ```

   for every item marked RESCAN-CANDIDATE **whose scratch file already
   exists** (skip this for items with no prior scratch — nothing to compare
   against). It emits `SKIP`/`RESCAN` per item with a reason that names
   exactly which field(s) changed, and is fail-safe by construction: any
   parse failure degrades to RESCAN, never a wrongly-trusted SKIP. **Note
   (one-time expectation):** every scratch file written before 2026-08-15
   predates the fingerprint-writer script and is old-grammar — the first
   post-fix run therefore correctly reports RESCAN for all of them and runs
   a full rescan once; that's the designed fallback, not a bug. What the
   script re-extracts (the spec, and the manual fallback if it can't run) —
   the same fingerprint fields the scanner recorded last time (see Step 2's
   "Write a fingerprint") from the *current* file content:
   - **Verdict:** `grep -m1 -E '^\*\*Verdict:\*\*' <build-report.md>` → the
     GREEN / GREEN-WITH-CAVEATS / BLOCKED token.
   - **Decisions:** for each decision-block heading in every `decisions.md`
     (item root, `qa/`, `build/**`), grep the following `- **Status:**`
     line → collect as `ID:STATUS` pairs. **Match the project's declared ID
     grammar, not `DEC-<n>` only** (widened 2026-08-15): live heading
     grammar includes `WATCH-n`, `PM-n`, `OD-n`, `DBA-n`, `PEND-n`,
     `OPEN-n`, `QA-DEC-n`, letter-suffixed instances — a DEC-only grep
     matches the DEC subset on both sides and can silently SKIP an item
     whose WATCH/PM/OD status flipped.
   - **Test numbers:** `grep -oE '[0-9]+/[0-9]+' <build-report.md> | sort -u`.
   - **Merged:** if the fingerprint recorded a `merged_commit`, run
     `git -C <repo-root> merge-base --is-ancestor <merged_commit> <default-branch-HEAD>`
     — cheap, deterministic, no agent needed.
   - **QA verdict:** `grep -A1 -m1 -E '^## Coverage verdict' <qa-assessment.md>
     | tail -1` if a `qa-assessment.md` exists for this item, else `n/a` —
     compare against the fingerprint's `qa_verdict`, same rule as every other
     field below (a change here is load-bearing on its own, even if
     `verdict`/`decisions`/`test_numbers` are unchanged — a re-run of
     `team-qa` doesn't touch any build-report field).

   Compare each freshly-extracted field to the value recorded in the scratch
   file's fingerprint:
   - **All fields match** (or the file simply doesn't conform to these
     markers at all — see safety note) is NOT enough on its own; only
     downgrade to **SKIP** when the fields *were extractable* on both sides
     **and matched exactly**. Record the annotation "touched at `<time>`,
     fingerprint re-checked and unchanged — treated as cosmetic" in the
     **downgrade list you pass into Step 2's `Workflow` call** as
     `cosmeticDowngradeAnnotations` (its documented input channel; the lead
     renders it in the report) so this isn't silently invisible to the user.
     Don't try to write it into the item's scratch file — the single-writer
     rule gives the orchestrator no write path into `.status-scratch/`.
   - **Any field differs** → stays **RESCAN-CANDIDATE**, a load-bearing claim
     actually moved. **Keep the which-field-changed diff** (the script's
     RESCAN reason line): pass it as that item's `fieldChangedDiff` in Step
     2's `itemsToScan` — the script hands it to both the rescanning scanner
     (so it knows where to look first) and `status-lead`.
   - **Safety fallback:** if a marker can't be found at all in the *current*
     file (irregular/non-template report, like a thin item with no
     `decisions.md`, or a build-report that doesn't follow the standard
     `**Verdict:**` line) — don't guess. Leave the item **RESCAN-CANDIDATE**.
     This check only ever *removes* scanner work when it's confident; it never
     invents confidence to save a call.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
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
     flagged as unverified-since-`LAST_RUN` in the output. **How that flag
     gets implemented** (it was promised but unwired until 2026-08-15):
     tell `status-lead` in its launch prompt which items were carried
     forward unverified despite a detected change, and instruct it to say
     "unverified since `<LAST_RUN>`" in those items' stage-map Notes and in
     the overall verdict line — and repeat the flag yourself in the Step 4
     report-back.
   - **Force full rescan of all items** — ignore SKIP/RESCAN-CANDIDATE
     entirely, scanner on every item regardless of what changed. **Caution
     on large batches:** a big force rescan launches that many concurrent
     scanners against the same shared dev/test stack, and concurrent test
     runs can produce transient contention that looks like a new failure.
     A "finding" that shows up only in a force-rescan and isn't corroborated
     by the item's own build-report should get a second look (e.g. does it
     reproduce in isolation?) before being reported as a live regression.

   **Under auto-pilot,** skip this ask too: auto-pick "rescan only the
   flagged items" (this skill's own stated recommendation), log it to
   `status-decisions.md` as `DECIDED-AUTO`, and state the split in the
   summary instead of waiting.

   **Skip this ask** (go straight to "rescan the flagged items") when: the
   user's invocation already said `--force` / "force rescan" / "re-verify
   everything"; or this is the first-ever run (nothing cached to offer as
   an alternative — there's no real choice to present).

7. **All-SKIP branch (2026-08-15 — previously undocumented).** If step 5
   downgraded *every* item to SKIP — Step 0.5 detected a touch somewhere,
   but no fingerprint field moved anywhere — do **not** fall through to a
   full opus synthesis that rewrites an identical report. Route to Step 4's
   **fully-cached variant** exactly as if Step 0.5 had found nothing: no
   scanners, no `status-lead`, present the cached report with a note listing
   the touched-but-cosmetic items ("N items touched since `LAST_RUN`, all
   fingerprint-confirmed cosmetic — cache trusted"). This is the same cost
   Step 0.5 exists to avoid; don't pay it for a typo fix.

**Safety:** if `git` is unavailable in the target repo, treat all items as
RESCAN-CANDIDATE and note it in the ask (don't silently skip verification).

**Safety (shared-doc hit):** if Step 0.5's shared cross-team doc check found
a hit this run, don't let the fingerprint re-check (step 5 above) downgrade
any item to SKIP on the strength of its own local fingerprint alone — that
fingerprint only re-extracts fields from the item's own artifacts, never
from the shared doc that actually changed. Mark every item whose
`decisions.md` or catalog references overlap the changed shared path as
RESCAN-CANDIDATE outright and skip fingerprinting for those; say so
plainly in the ask.

### Step 2 — Run the scan pipeline
Resolve, from Step 1.5's answer, exactly which items to scan and which to
carry forward:
- **`itemsToScan`** — the RESCAN-CANDIDATE set if the user picked "rescan
  flagged," all items if they picked "force full rescan," or none at all if
  they picked "trust cache." For each, include the which-field-changed line
  from Step 1.5 if this item was flagged by the fingerprint re-check.
- **`skippedItems`** — every item carried forward from cache, with its
  reason (unchanged, or fingerprint-confirmed cosmetic).
- **`capConcurrency`** — `true` when this project's items re-run tests
  against one shared, stateful dev/test stack (check `PROJECT-CONTEXT.md`)
  **and** the scan set is large (double digits); `false` when the project
  isolates each effort's own stack, or the scan set is small. **Before any
  double-digit launch with capping on, state your wave plan in chat** ("N
  items → waves of ~8: 8+8+8+…").

Then run the actual scan-and-synthesize pipeline as one call:

```
Workflow({
  scriptPath: "~/.claude/skills/team-status/workflows/status-scan.js",
  args: {
    targetDir: "<target>",
    reportPath: "<target>/status-report.md",
    itemsToScan: [ {slug, path, fieldChangedDiff?}, ... ],
    skippedItems: [ {slug, path, reason}, ... ],
    triageInventory: <Step 1's JSON or agent summary>,
    priorReportPath: "<target>/status-report.md (if one already existed)",
    lastRun: "<Step 0.5's LAST_RUN timestamp>",
    statusDecisionsPath: "<target>/status-decisions.md (if one exists)",
    cosmeticDowngradeAnnotations: [ "<Step 1.5 annotation>", ... ],
    unverifiedSinceLastRun: [ "<slug>", ... ],  // trust-cache branch only
    batchWideFindings: <prior report's batch-wide findings, force-rescan only>,
    capConcurrency: true | false,
    waveSize: 8
  }
})
```

(Under a plugin install, `scriptPath` is
`${CLAUDE_PLUGIN_ROOT}/skills/team-status/workflows/status-scan.js` instead
— same "Path note" translation as everywhere else in this file.)

This one call replaces what used to be two separate steps — the per-item
scanner fan-out and the status-lead synthesis. The mechanics described in
the old Steps 2–3 are all still true, just executed by the script now
instead of by you:
- **Each scanner** reconciles intent vs. state, re-verifies every
  load-bearing claim against the live code (never quotes a report's claim as
  fact), checks for open decisions and cross-item drift, classifies the
  stage, writes its narrative findings to
  `<target>/.status-scratch/<item-slug>.md`, and writes the fingerprint
  frontmatter via `write_fingerprint.py` — all via its own `Write`/`Bash`
  tools, unchanged. On a force-full rescan with a prior report, each scanner
  also gets that report's batch-wide findings, labeled "known — confirm or
  contradict in one command, don't re-derive."
- **When `capConcurrency` is set**, the script batches the launches itself
  (default 8 per wave, next wave once the prior one returns) instead of
  firing the whole set in one message — this is the contention-safety rule
  for a shared dev/test stack, now enforced structurally instead of by
  prompt discipline alone. The wave structure is visible in the script's own
  progress log.
- **`status-lead`** synthesizes everything into `status-report.md` — the
  two-table stage-map/Ready-for-Deployment split, the merged-item follow-up
  breakdown, the "changed since last run" element, open decisions, cross-item
  drift, the parallelization-opportunity check, the in-flight
  `engineering-manager` dispatch check (it reads
  `<target>/.em-state/dispatch-state.json`/`triage-state.json` itself), and
  the single recommended next action — then appends its own run-log row via
  `add_status_run_log_row.py`, unchanged.

The run goes silent in this session until the workflow completes — a
background job, not a live stream — so say so before starting it. It returns
an object (scanned/carried-forward/died counts, the recommended next action,
any parallelization opportunity); use it in Step 4 below.

**Writing back what the workflow decided:** the script never touches the
filesystem itself. Gate answers that resolve *after* synthesis (Step 4
proceed, parallelization, Step 4.5 corrections) are still your job to record
in `status-decisions.md` at Step 4.5, same as before.

### Step 4 — Report back
Present the reconciled state **in chat as plain-text tables** (ASCII-style
markdown tables render fine and are what the user has asked for — not a rendered
UI/artifact page unless she explicitly asks for one):
- **A numbered stage-map table, FIRST — items with outstanding work only** —
  columns `#` · `Item` · `Intake` · `QA` · `Build` · `Merged` · `Notes`, using
  ✅ / ❌ / ➡️ per the template's legend. This is the primary "where are we"
  answer — lead with it. Number the rows so the user can say "run #3" to pick
  one without retyping its slug. **Always print the legend directly under
  the table** — never assume the icons are self-explanatory: `✅ done · ❌
  not done / not applicable · ➡️ partially done (e.g. built but never
  committed/merged, deliberately waived, or found incomplete)`. **Any item
  that is all-four-✅ and whose Merged-item follow-up type is `NONE` does
  NOT appear in this table** — it belongs in the Ready for Deployment table
  below instead (this applies whether the split is freshly computed this run
  or read back from a cached `status-report.md`). If every item qualifies
  for Ready for Deployment, say so plainly instead of printing an empty
  table.
- **A "Ready for Deployment" table, SECOND** — columns `#` · `Item` ·
  `Notes` (Notes reads exactly "Ready for deployment." for every row — all
  four pipeline columns are implicitly ✅ by definition of being in this
  table, so they aren't repeated). Holds every item moved out of the
  stage-map above. Omit this table entirely if nothing currently qualifies.
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
- **Changed since last run** — which items flipped state vs. the prior
  report (from the lead's section of the same name), so a returning reader
  sees the delta, not just the absolute state.
- **Open decisions** still `PENDING` / `PARKED` / `WATCH` / `DEFERRED` —
  plus the line "**DEC entries flipped to `DECIDED-AUTO` since the last
  status run: N (unreviewed by a human)**" whenever N > 0; this report is
  the review surface for the pipeline's gateless producers.
- **The single next action** — the skill to run next, the target folder, and
  the one-line why.
- Links to `status-report.md` and any per-item scratch worth reading.
- **Under auto-pilot:** also list every `DECIDED-AUTO` entry from this run —
  "Decided automatically (auto-pilot): N items — see status-decisions.md."

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
Then ask whether to proceed with the recommended next action (which means
invoking one of the *other* skills — out of scope for this one), or invite
the user to pick a row number from either table directly. Letter the
choice — e.g. **A)** proceed with the recommended next action, **B)** pick a
different row/item, **C)** something else — per the lettering convention
above. **Under auto-pilot,** skip the ask: state the recommended next action
as decided rather than a question, log it as `DECIDED-AUTO`. This does not
change what the skill *does* — it's still read-only/advisory in every mode
and does not itself invoke `team-intake`/`team-qa`/`team-build`; "proceeds"
here means it stops phrasing the recommendation as a question.

**Fully cached variant (Step 0.5 found nothing changed — or Step 1.5's
all-SKIP branch fired — no agents ran):**
Skip the bullets above — there is no fresh reconciliation to summarize.
Instead state plainly: the target has had no changes since `status-report.md`
was last written at `<LAST_RUN>`; present that report's stage-map and
recommended next action as-is (clearly labeled as cached, not re-verified
this run); and mention that a full rescan can be requested (`--force` /
"force rescan") if they want it re-verified anyway despite no detected
changes. **Two rules made explicit 2026-08-15:** the proceed gate above
**still fires** on this variant (the cached recommendation is still put to
the user as a question — or stated as decided under auto-pilot); and a
fully-cached run appends **no run-log row** and skips Step 4.5 entirely
(nothing new was produced — that's by design, not an omission).

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
**If `status-lead` found a parallelization opportunity** (two or more
independent build-ready items), do not fold that into the same yes/no —
put it to the user as its own explicit choice via `AskUserQuestion`. **Use
the same two option letters the report itself uses** (re-lettered
2026-08-15 — the gate used to present a different "Option A" than the
report the user had just read, and auto-pilot auto-picked the one the
report never described):

- **Option A — run concurrently** (matches the report's Option A). Default
  execution — **fresh chats, one per item, recommended**: for each item,
  generate a short, fully self-contained kickoff line:
  `Run team-build on <absolute path to the item's intake-base folder>`
  — nothing else. Print all N kickoff lines as separate copy-paste blocks in
  the chat reply. Do **not** spawn any subagent for this form — the whole
  point is that the current session does nothing further; the user opens N
  new chat sessions and pastes one line into each. This works *because* the
  pipeline is designed for it: everything a fresh session needs
  (`technical-plan.md`, `pm-plan.md`, `decisions.md`) already lives on disk,
  so a cold session with zero conversation history can execute the build
  correctly from the path alone. If a kickoff line would need anything
  beyond the folder path to work, that's a signal the item's own plan/
  decisions docs are incomplete — fix the docs, don't patch around it by
  stuffing context into the kickoff line.
  Alternative execution (only if the user asks to stay in-session) —
  **concurrent in this session**: launch the named items as parallel agent
  calls in one message, each a plain subagent call (e.g. `general-purpose`,
  or omit `subagent_type`) that invokes the `team-build` skill itself from
  a clean start — **never `subagent_type: "fork"` for this.** A fork
  inherits this session's *entire* conversation history as its starting
  context, and a long-running status/build session can easily be tens or
  hundreds of thousands of tokens deep — the fork pays that inheritance
  cost before it does a single second of the item's own work, on top of a
  task that (per the fresh-chats premise) needed none of it. Each
  concurrent branch still goes through its own `build-triage` for its own
  worktree, same as any single `team-build` run — just launched together.
  State the time-saved trade-off, and that results still land back in this
  session (which keeps growing this conversation's size).
- **Option B — run sequentially** (matches the report's Option B). One at a
  time, priority order, in this session. State the lower-review-load
  trade-off.

Let the user pick; there is no unilateral default beyond presenting A first.
Whichever is chosen, proceed accordingly. **Under auto-pilot,** skip the ask:
auto-pick **Option A in its fresh-chats form** (already this skill's own
presented-first default — fresh, self-contained kickoff lines, no subagent
spawned), log it as `DECIDED-AUTO`, and print the kickoff lines directly
instead of waiting.

### Step 4.5 — Commit pipeline docs, and apply any proposed corrections (gate)
This step runs at the **orchestrator level** — the main agent, using its own
`git`/`Edit` access, same as Step 0.5's git checks already do. No subagent is
involved and `status-lead`'s own tool grant/write-scope doesn't change.

- **Skip entirely** if Step 0.5 took the fully-cached path (nothing new was
  written this run) or `<target>`'s repo isn't a git working tree. Say so
  plainly, don't fail.
- **If `status-report.md` contains a non-empty "Proposed corrections"
  section** (from `status-lead` — see its role file), gate on it before
  touching anything:

  🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate — stops in EVERY mode,
  including auto-pilot; corrections are never auto-applied.** (Retagged
  from PREFERENCE 2026-08-15: the old tag contradicted this gate's own
  "never auto-applied" body text, and the wrong reading auto-edits
  third-party pipeline docs.)
  Show each proposed correction (file · old text → new text · one-line why);
  ask lettered — **A)** apply all · **B)** apply some · **C)** apply none.
  On A/B, apply each approved edit with the file-edit tool against its real
  target file — this may be a *third-party* doc this team doesn't normally
  write to (`decision-log.md`, the defect catalog, a sibling item's own
  `decisions.md`), which is exactly why it's gated and never auto-applied.
  Never touch product code, a plan, or a test this way.
- **Record every correction's disposition** (2026-08-15, structural 3 —
  before this, a declined correction was indistinguishable from a
  never-noticed one, and the next 40-scanner pass re-derived it): log each
  drafted correction into `<target>/status-decisions.md` using the existing
  v2 status tokens — applied → `DONE` · declined → `WATCH` (known and
  deliberately carried — scanners/lead treat it as "previously seen, report
  once as such, don't re-draft") · deferred → `DEFERRED`. One short block
  per correction, `add_decision.py`-conformant. **Also record here, one
  line each, the Step 4 gate answers** that resolved after the run-log row
  was written (proceed choice, parallelization choice, this gate's own
  answer) — the observability half of the same audit finding.
- **Then make one local commit** covering `status-report.md`,
  `.status-scratch/*`, `status-decisions.md` (if written), any corrections
  just applied, and — **only when the project names its own in-repo
  status-run-log** — that log's new row. (Reworded 2026-08-15: the global
  fallback log lives outside any git repo, so in every observed run to date
  the run-log row was uncommittable — listing it unconditionally made the
  documented commit content impossible.) Stage by explicit path, never
  `git add -A` (a shared repo may have
  unrelated in-flight work sitting in the same working tree). **Never
  push** — pushing stays `wrap-up`'s job, not this skill's. Report the
  commit hash in the chat reply; this must be visible, not silent.
- If the commit can't land cleanly (a pre-commit hook rejects it, unrelated
  dirty state blocks a clean stage), report the failure plainly and stop —
  don't strip hooks, don't force it, don't fall back to `git add -A` to make
  it work.
- **Why this exists:** these are `status-report.md`/`.status-scratch/*`/the
  run-log — artifacts this team exclusively owns, that carry zero product-code
  risk. Leaving them uncommitted until a later `wrap-up` is exactly how a
  status report can go stale relative to its *own* on-disk state (a ruling
  gets made, the doc gets edited, and the edit itself sits unpropagated for
  hours) — see "The recurring trap this skill exists to catch" below.

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
   in its `Gate answers` cell in a few words (post-synthesis answers go in
   `status-decisions.md` instead — see Step 4.5).
Write it `PENDING` before asking; flip to `DECIDED` / `PARKED` once answered.

**Propagate the flip, don't just log it.** The moment a decision this run
touches moves off `PENDING`/`PARKED` (or `WATCH`/`DEFERRED`) anywhere in the project, name every
other doc that still cites the old status in the Step 4 report-back — a
cached report, a sibling's `decisions.md`, the defect catalog. This team
can't edit those on its own initiative (read-only outside Step 4.5), so the
correction itself is exactly what belongs in Step 4.5's "Proposed
corrections" gate — that's the tie-in between this rule and the
reciprocal-cross-reference check `status-lead` runs during synthesis.

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
  letter the options** — `**A)**`, `**B)**`, `**C)**`, etc. — so the user can
  answer with a single letter instead of re-describing the option. This
  applies to every human gate in this skill that presents more than one
  path forward: Step 0's ambiguous-scope ask, Step 1.5's rescan-scope ask
  (when not using `AskUserQuestion`), Step 4's proceed-with-recommendation
  callout, and the parallelization-opportunity gate's Option A/B (already
  lettered, matching the report's own letters — keep it that way). A gate
  with only one path (e.g. a plain
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
  One consequence to own openly: the `worktree` skill recomputes
  merged/dirty state live on every run, while this skill serves a cached
  fingerprint until change detection fires — so the two can give opposite
  answers on "is this merged?" in the same minute. On any such
  disagreement, `worktree`'s answer is the current one; treat the
  discrepancy as a signal this skill's cache needs a rescan, not as a
  conflict to adjudicate.
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
  run-log — it never touches a third-party doc itself. The one exception is
  Step 4.5, which runs at the orchestrator level (not `status-lead`), only
  ever on `status-lead`'s own explicitly-drafted "Proposed corrections," and
  only after an explicit human gate — never a silent or automatic edit to
  another team's file.
- **Shared memory is INPUT, never forked.** Read (do not copy, do not edit)
  each team's own `memory/` folder to know what's already been done and
  which project-specific defect surfaces are in play. **One source of
  truth — do not duplicate it here.**
- **Output per run:** `<target>/status-report.md` (+ transient
  `<target>/.status-scratch/*.md`, + `status-decisions.md` only if a decision
  was logged).
- **Templates:** `~/.claude/skills/team-status/templates/`.
- **Scripts:** `~/.claude/skills/team-status/scripts/` (added 2026-08-15) —
  `check_staleness.sh` (Step 0.5), `inventory_items.py` (Step 1),
  `fingerprint_check.py` (Step 1.5), `write_fingerprint.py` (scanners,
  Step 2), `add_status_run_log_row.py` (status-lead, Step 2),
  `check_backlinks.py` (status-lead's reciprocity sweep). Deterministic
  recipes run as scripts; agents handle the judgment residue.
- **Memory:** the status run-log location comes from `PROJECT-CONTEXT.md` if
  the project names one; otherwise
  `~/.claude/skills/team-status/memory/status-run-log.md` (a cross-project
  fallback, append-only — **rotated 2026-08-15**: rows go through
  `scripts/add_status_run_log_row.py` only, 7 columns, 400-char field cap;
  readers `grep` by project, never Read the file whole; prior history lives
  in `memory/archive/status-run-log-2026-07-20-to-2026-08-14.md`;
  re-rotate near ~150KB). It has no forked defect-catalog file — it reads
  the project's own if one is configured.
- **Session model:** this skill assumes the invoking session runs a strong
  model — `status-scanner` deliberately has no `model:` line and inherits
  whatever the session runs, and Steps 0.5/1.5 execute orchestrator-side.
  (Documented 2026-08-15; the inherit choice itself is settled — logged
  runs to date show no tier-attributable misses.)
- **Downstream consumers:** `engineering-manager` reads `status-report.md`
  to triage/dispatch work — its buckets are keyed off this skill's
  merged-item follow-up taxonomy (`NONE`/`COSMETIC`/`DOC CLEANUP`/
  `OPERATIONAL`/`DEPENDS-ON-ITEM`/`FUTURE SCOPING`) and stage vocabulary,
  so renaming either silently breaks it. It also dispatches builds and only
  refreshes status after merge — hence Step 2's in-flight dispatch check.
- **Repo layout is project-specific — check `PROJECT-CONTEXT.md` first**, or
  discover it. Verification commands run inside the project's actual repo(s).
  **Never `Read` a `PROJECT-CONTEXT.md` whole** — the file can exceed the
  256KB Read cap (one real install's file reached 541KB; a whole-read fails
  outright, and a whole-read failure has been observed to fan that
  unsatisfiable instruction out across many scanners at once).
  `Grep` for the section anchors you need (defect-class catalog / "Recurring
  issues", `## Repo topology`, shared-log paths, "Default status scope") and
  Read only those ranges. The `## Repo topology` heading is canonical and
  written by the `worktree` skill — parse its fenced yaml `members:` block
  first. Restructuring the oversized container is out of scope for this
  skill — treat it as a project-level decision.
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

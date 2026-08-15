# Status Report — <target folder name>

> Produced by `team-status` (read-only). Reconstructs the true current state of
> every work item in this folder by reconciling plans/reports AND re-verifying
> their claims against the live code. **This report is advisory — no plan, test,
> or product code was changed.** It is current as of the run date below and, like
> any status snapshot, goes stale the moment the code changes again.

- **Target:** `<absolute path>`
- **Scope:** batch of <N> items | single item
- **Run date:** <YYYY-MM-DD>
- **Overall verdict:** <one line — e.g. "3 items build-green; 1 stale (report contradicted); 1 open decision blocking">

---

## Stage-map

One row per work item **that still has something outstanding** — with the
pipeline stage spelled out as explicit columns — not a single enum label —
so "have we done intake," "are we ready to build," "are we in QA," and "is
this merged" are each a direct yes/no, not something the reader has to infer
from a phrase. This table is deliberately filtered: **items that are fully
done (see "Ready for Deployment" below) are removed from here once they
qualify**, so what remains in this table is always the true to-do list, not
diluted by finished work.

| # | Item (slug) | Intake | QA | Build | Merged | Notes |
|---|-------------|:------:|:--:|:-----:|:------:|-------|
| <n> | <slug> | ✅/❌/➡️ | ✅/❌/➡️ | ✅/❌/➡️ | ✅/❌/➡️ | <one line: what's actually true right now> |

_(At batch scale this may be split into several sub-tables grouped by
area/phase — that's the shape real 40-item reports have converged on. The
row schema above is the contract; the single-table layout is not.)_

> Legend: **✅** done · **❌** not done / not applicable to this item ·
> **➡️** partially done (e.g. built but never committed/merged, or a scanner
> found it incomplete). A `stale` or `contradicted-by-live-code` finding goes
> in Notes, not as a 4th symbol — say plainly what the report claimed vs. what
> the live check found.

_(If every item now qualifies for Ready for Deployment, say so plainly here
— "No items with outstanding work; everything is in Ready for Deployment
below" — don't leave an empty table with no explanation.)_

---

## Ready for Deployment

Items that have graduated out of the Stage-map above: all four columns
(Intake/QA/Build/Merged) are ✅ **and** the Merged-item follow-up type
(below) is `NONE` — genuinely nothing left, not even a doc/operational/
future-scoping residual — **or** whose only residual a human has explicitly
accepted via a `WATCH`/`RECORD` entry in `status-decisions.md` (cite it in
Notes). **The moment an item first meets this bar, move its
row here and remove it from the Stage-map** — don't leave it in both places.
This table is deliberately displayed **second**, after the Stage-map, so the
outstanding work is what a reader sees first.

| # | Item (slug) | Notes |
|---|-------------|-------|
| <n> | <slug> | Ready for deployment. |
| <n> | <slug> | Ready for deployment — residual accepted per status-decisions.md <id>. |
| <n> | <slug> | Released in <version> per release-log. |

_(Omit this whole section if no item currently qualifies — everything still
has some open thread, so the Stage-map above is the complete picture.)_

---

## Merged-item follow-ups

For every item with **Merged = ✅** above, name what — if anything — is
actually left, using this fixed taxonomy so "merged" never gets conflated
with "fully done":

| Type | Meaning |
|------|---------|
| **NONE** | Fully done. No action of any kind. |
| **COSMETIC** | Trivial, non-blocking text/comment cleanup. Zero risk if left alone. |
| **DOC CLEANUP** | The item's own report/decision-log text is stale vs. what's actually true (e.g. still says "unmerged" after it merged). No code or data changed — just correct the text. |
| **OPERATIONAL** | A live data/environment action is needed (e.g. a shared dev database holds the wrong value, an untracked migration needs cleanup) — or a non-code admin action (repo settings, secrets). Not something `team-build` fixes. |
| **DEPENDS-ON-ITEM** | Resolves automatically once another named item (cite its slug) is merged or decided — no independent action here. |
| **FUTURE SCOPING** | A follow-up was decided but never planned. Needs a future `team-intake` pass before it can be built. |

| # | Item (slug) | Type | What's left |
|---|-------------|------|-------------|
| <n> | <slug> | <NONE / COSMETIC / DOC CLEANUP / OPERATIONAL / DEPENDS-ON-ITEM / FUTURE SCOPING> | <one line, or "Nothing." for NONE> |

_(Omit this whole section if no item in the stage-map has Merged = ✅ yet.)_

---

## Changed since last run

> The delta against the prior `status-report.md` (`LAST_RUN: <timestamp>`),
> from the SKIP/RESCAN split. First run: "first run — no prior report."

- **Flipped:** <item> — <e.g. Merged ❌→✅ this run (evidence)>
- **Touched but cosmetic (cache trusted):** <item> — touched at `<time>`,
  fingerprint re-checked and unchanged — treated as cosmetic.
- **Rescan triggers:** <item> — <which fingerprint field changed, old → new>.
- **Carried forward unverified** _(trust-cache runs only)_: <item> —
  unverified since `<LAST_RUN>`.

---

## Report-vs-reality discrepancies

> The highest-value section. Each place a plan/report claim did NOT match what the
> live re-verification found. If empty, say so explicitly — "all reported claims
> re-verified true as of <date>."

- **<item slug> — <claim>:** report said `<quote>` → live check showed `<what you
  found>` (evidence: `<command run / grep / file state>`). Impact: <why it matters>.

**Previously accepted (not re-headlined):**
- <item slug> — <finding> — accepted per `status-decisions.md` <id>.

---

## Open decisions (PENDING / PARKED / WATCH / DEFERRED)

| DEC-id | Item | Status | Waiting on |
|--------|------|--------|------------|
| <id> | <slug> | PENDING / PARKED / WATCH / DEFERRED | <what/who> |

**DEC entries flipped to `DECIDED-AUTO` since the last status run: <N>
(unreviewed by a human)** — <ids, when few>.

_(None, if the item decision logs are all DECIDED.)_

---

## Cross-item drift

> Items touching the same surface, a plan/decisions not updated to reference a
> follow-on, or two items editing the same file/section. Flag; don't fix.

- <observation, with the two items and the shared surface>

_(None found, if clean.)_

---

## Parallelization opportunity

> `team-build` gives each effort its own isolated worktree + branch, so more than
> one can run at once. This section names whether any ready-to-build items are
> independent enough to do that — and presents it as a **choice**, not a pick, since
> it trades wall-clock time against how many diffs get reviewed at once.

**Candidate build-ready items:** <slug>, <slug>, ... _(items whose next step is a
real `team-build`, excluding anything documentation-only or blocked on a decision)_

- **Option A — run concurrently:** `<slug-a>` + `<slug-b>` — disjoint file
  footprints (per the drift check above), no shared decision dependency, no overlap
  with any open effort-registry row. Saves roughly <estimate> of wall-clock time;
  means reviewing <N> diffs at once.
- **Option B — run sequentially:** same items, one at a time in priority order —
  one diff to review at a time, lower cognitive load, no risk of the two reviews
  blurring together.

_(No parallelization opportunity this run, if fewer than two independent
build-ready items exist — state that plainly instead of forcing a choice.)_

---

## Recommended next action

**→ Invoke `<team-intake | team-qa | team-build | librarian>` on
`<exact folder path>`.**

**Why:** <the specific gap that makes this the next step, citing the item and, if
it closes a recurring issue, the RI-id.>

### Backlog (after the above), in order
1. <skill> on <folder> — <why>
2. …

---

## Proposed corrections

> Specific, unambiguous, low-risk fixes surfaced during synthesis — a missing
> one-line catalog backlink, a stale count or status already corrected
> elsewhere in this same batch of docs. Draft only: `status-lead` never
> applies these itself; they're gated and applied (or not) by the
> orchestrator at Step 4.5.

| # | File | Old text | New text | Why |
|---|------|----------|----------|-----|
| <n> | `<path>` | `<verbatim old text>` | `<verbatim new text>` | <one line> |

_(Omit this whole section if nothing this precise turned up this run — don't
manufacture a correction to fill it.)_

---

## What this run did NOT do

Read-only audit. No product code, plan, test, or team memory was modified. To act
on the recommendation, invoke the named skill separately.

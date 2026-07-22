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

| Item (slug) | Verified stage | What it needs next |
|-------------|----------------|--------------------|
| <slug> | <not-started / intake-only / qa-done / build-in-progress / build-green / build-green-with-caveats / stale / blocked> | <one line> |

> Stage legend: **not-started** (nothing yet) · **intake-only** (plans, no
> test-plan) · **qa-done** (test-plan exists, not built) · **build-in-progress** ·
> **build-green** (verified green now) · **build-green-with-caveats** (green but an
> explicit gap remains) · **stale** (a report claim was contradicted by live code)
> · **blocked** (open decision).

---

## Report-vs-reality discrepancies

> The highest-value section. Each place a plan/report claim did NOT match what the
> live re-verification found. If empty, say so explicitly — "all reported claims
> re-verified true as of <date>."

- **<item slug> — <claim>:** report said `<quote>` → live check showed `<what you
  found>` (evidence: `<command run / grep / file state>`). Impact: <why it matters>.

---

## Open decisions (PENDING / PARKED)

| DEC-id | Item | Status | Waiting on |
|--------|------|--------|------------|
| <DEC-n> | <slug> | PENDING / PARKED | <what/who> |

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

## What this run did NOT do

Read-only audit. No product code, plan, test, or team memory was modified. To act
on the recommendation, invoke the named skill separately.

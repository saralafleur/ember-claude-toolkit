---
name: time-ledger
description: Cross-project time, token, and cost ledger built from Claude Code session transcripts. Use when you want to know how many hours you've put into a project or a specific branch/effort, want a daily or weekly rollup of hours/cost across everything you work on, or ask to "update my hours report" / "regenerate the time dashboard".
---

# Time Ledger

Regenerates the cross-project hours/token/cost rollup from local Claude Code
session transcripts. Read-only against the transcripts; writes only to its own
output directory.

## What it does

1. Runs `scripts/rollup.py` — scans every `~/.claude/projects/*/*.jsonl`
   session transcript, computes active time per session (sum of gaps between
   messages, each capped at 20 minutes so idle time isn't counted), and
   aggregates hours/tokens/cost by project, calendar date (UTC), ISO week, and
   git branch. It also segments each session's event stream into contiguous
   "blocks" (same 20-minute-gap rule — a gap over the cap starts a new
   block) with real start/end timestamps and the source transcript's filename +
   event count, which is what powers the dashboard's calendar week view and
   its click-to-verify popup. Writes `rollups.json`.
2. Runs `scripts/render_markdown.py` — renders `daily-rollup.md` and
   `weekly-rollup.md` (with a per-project branch breakdown) from that JSON.
3. Rebuilds the HTML dashboard by embedding the fresh `rollups.json` into
   `dashboard.html`, then republish it as an Artifact (same file path — this
   keeps the existing share URL rather than minting a new one).

## Calendar week view

The dashboard has a "Week view" card that renders like a Teams/Outlook weekly
calendar: 7 day columns, an hour-of-day axis, and colored blocks positioned by
time (project color matches the rest of the dashboard's legend). It's built
from `DATA.blocks` in the embedded JSON — each entry is
`{project, start, end, seconds, branch, tokens, cost}` in local-ISO-with-offset
form, so the browser renders it in the viewer's own timezone. Prev/Next/Today
buttons page between weeks; the project filter dropdown also filters the
calendar. All JS for this lives inline in `dashboard.html` (`renderCalendar`
and its helpers) — there's no separate script to re-run for it, it regenerates
automatically whenever the dashboard is rebuilt from a fresh `rollups.json`.

Two display rules, applied client-side in JS (not in `rollup.py` — the
underlying hour/cost totals elsewhere on the dashboard stay based on real
active time, unrounded):

- **Half-hour snapping.** Any activity inside a 30-minute slot fills that
  whole slot, like a real calendar meeting — `snapToHalfHourBlocks()` unions
  the occupied slots per project per day and merges adjacent filled slots into
  one visual block. The tooltip still shows the real active duration
  separately from the displayed (slot-rounded) time range, so nothing is lost.
- **Side-by-side concurrency.** If two different projects have activity in
  overlapping slots (e.g. a main-loop session in one repo and a background
  effort in another), `layoutOverlaps()` places them in side-by-side columns
  within the day rather than stacking/hiding one — matching how Teams/Outlook
  shows overlapping meetings.
- **One color per project.** `PROJECT_COLOR` (built once, near `RANKED`) gives
  every project with tracked time its own color — the top 8 by all-time hours
  use the curated `--s1`..`--s8` palette, the rest get a golden-angle-spaced
  HSL hue so nothing collides. This is separate from the trend chart's
  `colorFor`, which still buckets the long tail into "Other projects" for
  legend legibility — that grouping is intentional there and untouched.
- **Click a block to verify it.** Clicking a calendar block opens a popup
  (`openEventModal()`) showing exactly what produced it: the displayed
  (half-hour-snapped) time range, then a table of the underlying raw
  transcript blocks that were merged into it — each with its real
  unrounded start/end, active minutes, turn count, tokens, cost, branch, and
  the transcript's session-file id (the `.jsonl` basename under
  `~/.claude/projects/<project>/`) so a claim can be traced back to its
  source. `snapToHalfHourBlocks()` carries this as a `sources` array on each
  merged block; `rollup.py` supplies `session` and `event_count` per raw block
  for it.

All output lives in `$TIME_LEDGER_OUTPUT_DIR` (default `~/time-ledger`),
configurable via that env var.

## To re-run

```bash
cd <this skill's scripts/ directory>
python3 rollup.py
python3 render_markdown.py
```

Then re-embed the data into the dashboard and republish it as an Artifact at
the same file path:

```bash
python3 -c "
import json, os
output_dir = os.path.expanduser(os.environ.get('TIME_LEDGER_OUTPUT_DIR', '~/time-ledger'))
d = json.load(open(os.path.join(output_dir, 'rollups.json')))
compact = json.dumps(d, separators=(',',':'))
html_path = os.path.join(output_dir, 'dashboard.html')
html = open(html_path).read()
import re
html = re.sub(r'const DATA = .*?;\n', f'const DATA = {compact};\n', html, count=1)
open(html_path, 'w').write(html)
"
```

(Note: after the first run, `__ROLLUPS_JSON__` in the template is replaced by
the actual data, so re-runs must regex-replace the `const DATA = ...;` line
instead of the original placeholder token.)

## Subscription billing

`scripts/rollup.py` has a `SUBSCRIPTION` constant, configurable via the
`TIME_LEDGER_SUBSCRIPTION_FEE`, `TIME_LEDGER_ANCHOR_DAY`, and
`TIME_LEDGER_CURRENCY` env vars (`fee`, `anchor_day` — the day of the month
the billing cycle renews — and `currency`). The shipped defaults are
placeholders (`$0.00`, cycle starting the 1st) — set your real subscription
fee and renewal day via those env vars before relying on the billing rollup.
It apportions that flat fee across projects by token share for the billing
cycle containing "now" and later — never retroactively for cycles before the
price was confirmed, since we don't know what (if anything) applied then. It
also reports the "API-equivalent" cost (what that usage would have cost on
pay-per-token pricing) and the savings gap. If the plan or price changes,
update the env vars before the next re-run — that takes effect starting from
the cycle current at run time, same rule as above.

There are two separate monthly-shaped views — don't conflate them:
- **Monthly rollup** (`monthly-rollup.md`, dashboard "Monthly" toggle): calendar
  months, UTC.
- **Billing rollup** (`billing-rollup.md`, dashboard "Current billing cycle"
  card): the subscription's actual renewal cycle, which rarely lines up with
  calendar month boundaries.

## Per-initiative SDLC journey artifacts

The cross-project dashboard above answers "how many hours have I spent." It
**cannot** answer "how long did this specific effort's intake/QA/build take,
and where did the time actually go" — because most of that time is background
subagent compute, not main-loop session time (see "Known limitations" below).
`log_agent_time.py` and `journey_report.py` close that gap, and are wired into
`team-intake`/`team-qa`/`team-build` (see each skill's own "Time logging"
section) rather than run standalone.

- **`log_agent_time.py`** — appends one record per completed `Agent()` call
  to a stage's `time-log.jsonl` (`--cycle-dir <stage output dir> --phase
  ... --role ... --label ... --duration-ms ... --tokens ... --tool-uses
  ...`, sourced directly from that call's own `<usage>` block — no transcript
  parsing needed). One log file per pipeline stage: `<intake-dir>/
  time-log.jsonl` (intake), `<intake-dir>/qa/time-log.jsonl` (qa),
  `<intake-dir>/build/<date>-<slug>/time-log.jsonl` (build).
- **`journey_report.py --initiative-root <intake-dir> --title ... --project
  ...`** — reads whichever of those log files exist, plus a hand-written
  `<intake-dir>/merge.json` once the effort is actually merged, and renders
  `<intake-dir>/sdlc-journey.html` (embedding `<intake-dir>/journey-data.json`,
  same "regex-replace `const DATA = ...;`" pattern as `dashboard.html`) — one
  artifact per initiative, covering its whole intake → QA → build → merge
  lifecycle, republished in place as each stage completes.

**Two clocks, always reported separately, never conflated:**
- **Running time** — sum of every agent's `duration_ms`. What it actually
  cost; can exceed wall-clock because of parallel fan-out.
- **Wall-clock** — real elapsed time, reported two ways: **active** (sum of
  contiguous blocks — a gap over `--gap-cap-minutes`, default 20, starts a
  new block, mirroring `rollup.py`'s own idle-gap-cap convention) and
  **calendar** (raw first-start to last-end, which includes any such gaps).
  A large gap is surfaced as an explicit annotation on the artifact
  ("⏸ 3h pause — session was idle or interrupted"), never silently folded
  into either number.

The **parallelism factor** (running ÷ active wall-clock, both overall and
per-phase) is the number that actually tells the story: a fan-out phase like
team-intake/team-qa's "Evaluate" step should show a factor well above 1×;
a strictly sequential single-agent step (triage, synthesis) shows ~1× — that
contrast is the point, not noise to average away.

## Known limitations (state these when reporting results)

- **Heuristic, not a stopwatch.** Hours are derived from message-timestamp
  gaps capped at 20 minutes — a reasonable activity-log estimate, not exact.
- **Main-loop time only.** Time spent by background/forked subagents while
  you did something else is not separately added to your hours. For any
  initiative run through team-intake/team-qa/team-build, that time is instead
  captured in its own SDLC journey artifact (see above) — the two are
  complementary, not overlapping: this dashboard is your own active
  presence across everything; a journey artifact is one initiative's total
  agent compute cost, background work included.
- **Cost is an estimate**, priced from local token usage against published
  API rates. If billing is via a Claude subscription rather than pay-per-token,
  treat it as "value consumed," not an invoice. Pricing table in
  `scripts/rollup.py` (`PRICING` dict) should be checked against
  `shared/models.md` in the `claude-api` skill periodically — it will drift.
- **Branch attribution is only as good as `gitBranch` in the transcript.**
  Projects where the working-tree root isn't the actual git repo (e.g. a
  project where the git repo root is a nested sub-directory rather than the
  working-tree root) show mostly "HEAD" or "unknown" — this gets exact once
  per-effort git worktrees are in place (each worktree has its own `cwd`,
  which the transcripts already log).

## A note on this being plugin-distributed content

This copy ships with placeholder configuration, not your real numbers: the
output directory and subscription fee/anchor day are all read from env vars
(`TIME_LEDGER_OUTPUT_DIR`, `TIME_LEDGER_SUBSCRIPTION_FEE`,
`TIME_LEDGER_ANCHOR_DAY`, `TIME_LEDGER_CURRENCY`) with generic defaults, so a
fresh install never inherits anyone else's real billing details or file
paths. Set your own via those env vars locally; don't hardcode real values
back into a copy of this repo meant for distribution.

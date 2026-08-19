# research

## Step 0 — Resolve topic and output

1. Get the topic as a concrete description — not just a one-word label. If
   the user gives something vague ("research X"), ask for enough framing that
   `research-triage` has something real to normalize (what is it, why does
   she want it researched, what decision will this feed).
2. Output directory: default to `<project-root>/research/<topic-slug>/` in
   the current project (slug = kebab-case of the topic). If the target division/team calling
   this wants a different location, use that instead.
3. If `<output-dir>/STATUS.md` already exists, read it and show the user a
   one-line summary of what's already done before asking whether to resume
   or start over. Starting over must be an explicit choice, never a default.

## Step 1 — Triage

Invoke `research-triage` with the topic and output directory. It writes:

- `brief.md` — the normalized research brief: what's being researched, what
  decision it feeds, what's already assumed/known vs. genuinely unknown, and
  the angle set to research (default set below unless the topic clearly
  needs different ones).
- `STATUS.md` — resumability marker, starts at `triage: done`.

**Default angle set** (triage can add/drop angles if the topic doesn't fit):

- `market-size` — how big is the addressable market/opportunity
- `competitors` — who else already does this or something adjacent
- `monetization` — how do comparable products/companies actually charge for this

## Step 2 — Scout fan-out (parallel)

One `research-scout` instance per angle in the brief, all in a single
message so they run concurrently. Each scout:

- Reads `brief.md` for context, is told its one assigned angle.
- Does scored external research (see the agent file for the scoring rule).
- Writes `sources/<angle-slug>.md`.

Update `STATUS.md` to `scouts: done (<N> angles)` once all return.

## Step 3 — Comparator

Invoke `research-comparator` with all `sources/*.md` files. It writes
`comparison.md`: agreements across angles/sources, gaps (nobody found
anything), and contradictions (sources disagree) — contradictions must be
stated plainly, not resolved by picking whichever sounds more confident.

Update `STATUS.md` to `comparator: done`.

## Step 4 — Validator

Invoke `research-validator` with `comparison.md` (not the raw `sources/`
files — it's checking whether the *reconciled* claims hold up, not
re-litigating the scouts' individual work). It writes `validation.md`: per
claim, `CONFIRMED` / `UNSOURCED` (couldn't verify the citation actually
supports the claim) / `CONTESTED` (found conflicting evidence the comparator
missed).

Update `STATUS.md` to `validator: done`.

## Step 5 — Lead synthesis

Invoke `research-lead` with `brief.md`, `comparison.md`, `validation.md`,
and `memory/decisions.md`. It writes `dossier.md` (see the agent file for
exact shape) and updates `STATUS.md` to `complete`.

## Step 6 — Orchestrator logs the budget row

This step is done by whoever is running the pipeline (you, the assistant
driving these Task/Agent invocations) — not a subagent, since no subagent
has visibility into another's token usage. Sum the token usage reported for
all five agent invocations this run (triage, each scout, comparator,
validator, lead) and append one row to `memory/budget-ledger.md`: date,
topic, total tokens, phase (`pilot` or `deep`), link to `dossier.md`.

## Token budget checkpoint

Per `memory/decisions.md` D-002: a topic's **pilot pass** (steps 1-5 above,
run once) defaults to a documented token ceiling. If the lead's tally comes
in over that ceiling, or the user wants to go deeper on a topic that already has
a completed pilot pass (more angles, deeper per-angle research, re-running a
contested claim), that is a **deep pass** — flag it explicitly to the user and
get an explicit go-ahead before spawning it, the same way `ai-coach-value`
gates full-corpus extraction behind a pilot review. Never silently escalate
from pilot to deep.

## Report back to the user

- The dossier's headline findings (market size takeaway, top 2-3
  competitors, the dominant monetization pattern found)
- Overall confidence (how many claims were `CONFIRMED` vs `UNSOURCED`/
  `CONTESTED`)
- Any unresolved contradiction the comparator/validator flagged
- Path to `dossier.md`
- Whether this was a pilot or deep pass, and current cumulative tokens
  against the D-002 ceiling

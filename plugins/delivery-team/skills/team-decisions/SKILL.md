---
name: team-decisions
description: 'Sweep a project''s delivery-team pipeline (every intake/qa/build/release/status decisions.md) for PENDING or PARKED decisions the team could not resolve on its own, and clear the backlog the way a director of engineering would: auto-resolve every decision the context can confidently settle — clear plain-language restatement, a re-derived recommendation, adopted immediately as DECIDED-AUTO — and escalate only the ones that are genuinely the user''s call (a subjective/creative/business preference the context can''t settle) to them directly via AskUserQuestion, recording their answer as a real DECIDED. Writes each resolution back into the source file in the project''s own decisions.md format, and commits the touched files at the end of the sweep. Use when the user asks "are there any open decisions", "let''s resolve open decisions", "walk me through open decisions", "what decisions are still open", or invokes "/team-decisions". Generic — works on any project using the delivery-team pipeline convention (team-intake/team-qa/team-build/team-release/team-status). Read-only until a decision is actually resolved; writes only decisions.md files (never product code, plans, or tests), one at a time, right after each is decided (or right after the user answers) — never in a batch at the end.'
argument-hint: '[<path>] — optional project/repo root to scope the sweep to. Defaults to the current project; asks if a solution spans multiple repos and the scope is ambiguous.'
---

# Team Decisions

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

The delivery-team pipeline (`team-intake`, `team-qa`, `team-build`,
`team-release`, `team-status`) leaves a paper trail every time it hits a
question it can't answer alone: a `decisions.md` entry, `**Status:**
PENDING`, with the question, the context, and — usually — a set of options
and a recommendation already drafted. The pipeline is built to keep moving
without the user whenever it safely can (that's what `DECIDED-AUTO` is for), but
a `PENDING` (or a deliberately shelved `PARKED`) entry is the case the rest
of the pipeline couldn't clear on its own — left sitting untouched until
someone goes looking for it file by file.

This skill is that "someone." It finds every open decision across a
project's pipeline and works the backlog the way a director of engineering
would: resolve everything the context can settle on its own authority —
one at a time, re-deriving a clean recommendation for each and adopting it
immediately as `DECIDED-AUTO`, never a wall of raw markdown to parse — and
escalate only what's genuinely the user's call, as a real question via
`AskUserQuestion`, instead of guessing at a preference nothing in the file
can settle. Most of the judgment that used to be theirs is now this skill's
own: Step 4's recommendation is usually the whole decision, not a pitch to
someone who'll catch a bad one. The one thing that never gets taken off their
plate is a decision that was never actually a technical judgment call to
begin with.

This is a **direct, single-agent skill** — no sub-agent delegation, same as
`wrap-up`. The task is a scan plus a sequential auto-resolution pass; each
decision's own file already carries the context needed to reason about it
well, so there's no fan-out work to delegate.

## When this triggers

- the user asks anything like **"are there any open decisions"**, "any open
  decisions?", "let's resolve the open decisions", "walk me through open
  decisions", "what decisions are still open", "decision review".
- the user explicitly invokes `/team-decisions`.

## Step 1 — Resolve scope

Default scope is the current project's repo (its git root). Check whether
the project's `PROJECT-CONTEXT.md` names a multi-repo solution — **don't
`Read` the whole file to check this.** A mature project's `PROJECT-CONTEXT.md`
can exceed the `Read` tool's size limit outright (confirmed on a real
project's file, 500KB+ — a full `Read` errors before you ever see the
repo-topology section). Instead extract just that section, one fixed
recipe: `grep -n '^## Repo topology'` (fall back to `grep -n -i 'repo
topology'` if that misses), then `Read` from that line with a small limit
and stop at the next `## ` heading. **If no such heading exists, don't
fall back to a full `Read` to "make sure"** — that's the exact hard-fail
the recipe avoids; treat the project as single-repo default scope and say
that assumption out loud in the scope line below. If the section exists,
treat it as authoritative — it's the topology `worktree` persists there
precisely so other skills don't re-discover or re-ask (see `worktree`'s
repo-membership convention). Determining what it *means* stays judgment,
not a repo-count (a real section here names four repos while declaring
"Single-repo solution"). Only ask which repos to include when the section
is genuinely absent-but-suspected-multi-repo or ambiguous — default to
**all of them** (this is meant to be a sweep, not a per-effort tool). If
an explicit path argument was given, use that as the root instead.

State the scope back in one line before scanning ("Sweeping `Acme` for
open decisions") so a wrong guess gets caught before anything else happens.

## Step 2 — Scan (read-only, scripted)

The scan is mechanical (find files, parse `## ` decision blocks, classify a
`Status`, tally, order oldest-first) — run it as a script instead of reading
every file by hand or fanning out an agent. Reading ~90 files one at a time
takes minutes; the script takes well under a second and is exact where a
free-form read is prone to skimming errors.

1. Run `python3 ~/.claude/skills/team-decisions/scripts/scan_decisions.py
   <root> [<root2> ...] --write-index` **once**, passing every scoped root
   from Step 1 as an argument to that same invocation — the script
   aggregates all roots into one combined tally and one combined queue;
   running it once per root would produce N separate tallies and break
   Step 3's single-table contract. Pass the actual root path(s), not `.`,
   if the working directory isn't already the root. The script already
   excludes `node_modules/`, `.git/`, `vendor/`,
   `__pycache__/` and walks every other directory (including a literal
   `build/` — that's a legitimate delivery-pipeline stage folder in this
   convention, not compiled output, and the filename filter already means a
   real build-output directory would never match `*decisions.md` anyway).
   Two v2 mechanics run automatically:
   - **Seal manifest (incremental scan):** a gitignored
     `.decisions-manifest.json` in the first root caches each file's parse
     summary keyed by content hash; unchanged files are skipped, so sweep
     cost tracks recent activity, not total history. Any edit bursts that
     file's seal (fail-safe); a `SCANNER_VERSION` bump in
     `decisions_lib.py` bursts every seal. The manifest is disposable —
     delete it (or pass `--full`) and everything re-parses. Run `--full`
     when something smells off, after a scanner change, or as an occasional
     reconciliation pass — not routinely.
   - **`--write-index`:** regenerates `OPEN-DECISIONS.md` in the first
     root — the one-file "is anything waiting on me?" answer (open items,
     WATCH/DEFERRED tripwires, the violations ratchet, a generated-at
     stamp). It is a rebuilt-from-scratch cache, NEVER hand-maintained;
     always pass this flag on a sweep so the index tracks the walkthrough's
     outcome (re-run the scanner with it after Step 5's writes too).
   A root may carry a `.decisions-scan-ignore` file (fnmatch globs, one per
   line) opting out files that match `*decisions.md` but are NOT pipeline
   decision logs — e.g. a project's own machine-generated
   `app/docs/import-decisions.md` product ledger, which can silently inflate
   the tally with a large number of unparseable blocks until excluded.
2. Read the script's stdout directly — it prints, in order:
   - the tally table (ready to paste into Step 3, already collapsed to the
     `PENDING`/`PARKED`/`DECIDED`/`DECIDED-AUTO`/`SUPERSEDED`/`Other` rows
     the Step 3 format wants, plus a `<details>` breakdown of what's inside
     `Other` for whenever the user asks),
   - the full walkthrough queue — every `PENDING`/`PARKED` block, oldest
     `Raised` first, each with its complete heading + body text already
     extracted. This is the primary source for Step 4; only re-open the
     source file directly if the printed body looks truncated or you need
     surrounding context the block itself doesn't carry.
   - the `DECIDED-AUTO` secondary list (file:ID only),
   - a **Format violations (normalization ratchet)** count + per-file list:
     blocks with no canonical status. Legacy debt for pre-cutoff files
     (see "Normalization lane" below), a lint failure for post-cutoff
     ones. Report the number in Step 3's one-liner so the ratchet stays
     visible run over run; a ratchet that ROSE since the last run means a
     recent write bypassed the format contract — say so.
   - a **Warnings** section, only when some file couldn't be read — treat
     a warned file as *unscanned*, not clean, and check it by hand,
   - a **Review-me** list: blocks that classify as something other than
     PENDING/PARKED but whose raw text still contains the literal substring
     `PENDING` or `PARKED` (usually a stale ID reference like `PENDING-CF-3`
     or prose mentioning another decision's status, but occasionally a
     genuine miss). v2 prints full entries only for files parsed FRESH
     this run; suspects inside unchanged (sealed) files were already
     skimmed the run that sealed them and appear as a count — don't
     re-skim them. Skim the fresh list before trusting the queue as complete —
     it's the script's own sanity net, not a second walkthrough queue. **If
     a listed block turns out to be a genuine miss** (a real open decision
     the classifier mis-scored), re-open that file directly, pull the full
     heading + body text yourself (the list only prints `file:id ->
     classified status`, not the block body), and fold it into both the
     Step 3 tally (move its count into `PENDING`/`PARKED` from whatever
   status the Review-me line says it was classified as — that can be
   `DECIDED`, `SUPERSEDED`, etc., not only `Other`) and
     the Step 4 queue by hand. **This net only catches misses whose block
     text contains the literal string `PENDING` or `PARKED` somewhere** —
     a project that marks open decisions with an entirely different word
     would land in `Other`, uncaught by either the classifier or this net.
     Low-probability for a delivery-team-pipeline project (this
     convention's own open-status vocabulary is `PENDING`/`PARKED`), but
     worth knowing before trusting a queue of 0 on an unfamiliar project.
3. The script's status vocabulary is deliberately small and literal
   (`DECIDED`, `DECIDED-AUTO`, `DECIDED-DEFAULT`, `PARKED`, `PENDING`,
   `WATCH`, `SUPERSEDED`, `RESOLVED`, `DEFERRED`, `DONE`, and — v2 —
   `RECORD`, the terminal home for blocks that live in a decisions.md by
   convention but were never decisions: scope boundaries, findings notes,
   narrative); anything else —
   including a block whose status doesn't cleanly parse at all — lands in
   `Other` under its own literal raw value, never forced into a known
   bucket and never dropped. `decisions.md` files are hand-written and
   often drift in format across a project (status as a `**Status:**` field,
   status embedded at the end of the `## ` heading line, bold or not,
   `**Decision:**` used instead of `**Status:**`, etc.) — expect `Other` to
   be the largest bucket. That's expected, not a parsing failure: it just
   means most individual entries didn't declare status in one of the two
   conventions the script actively recognizes, not that they're secretly
   open. The walkthrough queue and Review-me list are the two things that
   actually matter for completeness; the exact size of `Other` doesn't.
4. If the script's output looks wrong for a project (e.g. file count
   doesn't match a manual `find` sanity check, or the walkthrough queue
   looks implausibly empty for a project this size), don't silently trust
   it — spot-check a file or two by hand before reporting the table to
   the user.
5. **This is the default method, not a first pass to double-check.** An
   early run on this project (before this script existed) hit real misses
   from plain grep-based status matching and concluded, at the time, that a
   full-text parallel-agent sweep should be standard rather than a
   fallback — see this skill's own run-log for the entry that prompted this.
   This script was written specifically to close that gap: its status vocabulary
   and the Review-me net above both cover the formatting variations that
   caused the original misses. Only fall back to a full-text read (by hand,
   or a parallel-agent sweep for a large corpus) if item 4's spot-check
   turns up a real discrepancy — not as a routine second pass every run.

## The write contract, the lint gate, and the normalization lane (v2)

The 2026-08-14 architecture rework ("decision-log architecture v2") added
three standing mechanisms around the scan. They exist because prompts
alone don't keep hand-written status formats parseable — the corpus
accumulated a large number of blocks no scanner could classify. The posture is the same
as an AST-guard ecosystem: **never trust the writer, verify the artifact.**

- **Write contract:** every NEW `## ` block must carry a canonical status
  (`- **Status:** <TOKEN>` field line, or the token after the heading's
  last em-dash) from the shared vocabulary. Author new blocks with
  `scripts/add_decision.py` (it self-checks that what it wrote parses
  back conformant); resolve with `scripts/resolve_decision.py` as before.
  The single format definition lives in `scripts/decisions_lib.py` —
  every script in this family imports it, so writable/lintable/scannable
  can't drift apart. Any parsing/classification change there must bump
  `SCANNER_VERSION` (bursts every seal → one full re-verify).
- **Lint gate:** `scripts/lint_decisions.py <root>` fails (exit 1) on any
  nonconformant block in a file whose innermost cycle-slug date is on or
  after the cutoff (2026-08-14). Pre-cutoff files are grandfathered —
  legacy debt, not lint failures. Wire it into a project's CI —
  e.g., wiring the scan into a project's own CI `ci:` target
  (`decisions-lint` target); a PostToolUse hook runs the same linter at
  write time. Once a repo's ratchet hits zero, `--all` replaces the
  cutoff and the grandfather retires.
- **Normalization lane (ETL):** `scripts/normalize_decisions.py <root>`
  works the legacy ratchet down. Tier 1 (deterministic — exactly one
  unambiguous non-open token in a structural position) is applied by the
  script with `--apply`, as a pure `- **Status:** X` insertion under the
  heading, self-verified positionally after every write. **PENDING/PARKED
  are never Tier 1** — a script must never (re)open a decision. Tier 2
  (no token, or prose-only position) needs a model reading: propose a
  status with quoted evidence, batch the high-confidence ones, and mark
  genuine non-decisions `RECORD`. Tier 3 (multiple tokens, or anything
  that would mark a block OPEN) is walked with the user like Step 4, except
  the question is "confirm what this block's status actually is," never
  "make the decision." Normalization may only restate what the text
  already says — if inferring the status requires deciding anything, it
  waits for a human. Batch `--apply` commits by cycle folder so diffs
  stay reviewable.
- **Onboarding an unswept repo:** first run = scan (full, no manifest
  yet) → report the violations inventory + open queue → Tier 1 is safe to
  apply immediately → present Tier 2/3 volume and let the user choose: clean
  up now, in batches across future sweeps, or walk the open items first.
  Add a `.decisions-scan-ignore` for any machine-generated
  `*decisions.md` the first tally exposes.

## Step 3 — Summary before diving in

Before anything else, show the tally from Step 2 as one small table so the user
can see roughly where things stand at a glance — this is a "where are we"
snapshot, not a preview of the walkthrough, so show it even when the queue
turns out to be empty:

```
| Status         | Count |
|----------------|-------|
| PENDING        | 4     |
| PARKED         | 1     |
| DECIDED        | 158   |
| DECIDED-AUTO   | 21    |
| SUPERSEDED     | 1     |
| Other          | 12    |
| **Total**      | **197** |
```

- Only include rows with a nonzero count.
- Roll every non-standard value (`WATCH`, `DEFERRED`, whatever else turned
  up) into a single **Other** row — this is a glance, not an audit. Name the
  individual values in prose only if the user asks what's in it.
- **Total** is every decision block found, across every file, regardless of
  status — the honest denominator, not just what's open.

Under the table, one line: *"Found N open decisions (PENDING+PARKED) across
M files — resolving what the context can settle on its own, and asking you
directly about anything that's genuinely your call."* — plus, if any
`DECIDED-AUTO` already exist from a prior sweep or the wider pipeline,
*"(and P already auto-decided without human input, flag any of those if
you want them walked by hand instead)."*

If the queue (PENDING+PARKED) is empty, say so plainly right after the table
and skip straight to Step 6 — there's nothing to resolve, but the run
still gets logged either way (see Memory for why and for the row shape).
Don't invent resolution work over `DECIDED`/`SUPERSEDED` entries
just to have something to show; the table already gave the user the full
picture.

**Provisioning check (replaces the old up-front model gate, which fired
before the tally existed and couldn't see queue size):** Step 4 is this
skill's one genuinely judgment-heavy step — every entry needs its
recommendation re-derived, checked for supersession, and classified as
auto-resolvable or genuinely the user's call, and large sweeps (dozens of
decisions) do happen. If the open queue is large (roughly 10+), say so here and suggest
raising effort before starting the pass — for the auto-resolved entries
there's no one to catch a bad call downstream once it's written, so the
judgment quality has to be right going in. For a small queue, just
proceed; no interruption needed.

## Step 4 — Resolve the queue, one decision at a time

For each entry, in order, oldest `Raised` first. Work it the way a
director of engineering would: settle everything the context can settle
on your own authority, and put only what's genuinely the user's call in front
of them — never a wall of raw markdown, never a rubber-stamped guess at a
preference you can't actually derive. Don't batch entries into one pass —
each one gets its own recommendation (or its own question) worked on its
own merits, one at a time.

1. **Header.** Name the effort/file and give a one-line plain-language
   restatement of the actual question — not the raw heading, and not a
   markdown dump of the file.
2. **Context.** 2–4 sentences drawn from `Where we're coming from`,
   rewritten in plain language: what's being decided and why it actually
   matters. If the entry is `PARKED` rather than `PENDING`, say so and note
   why it was shelved, if the file records a reason.
3. **Classify — auto-resolvable, or genuinely the user's call?** This is the
   judgment gate the whole approach hinges on:
   - **Auto-resolvable (the default).** The file's own context — the
     stated tradeoffs, project conventions, `PROJECT-CONTEXT.md`, a related
     decision elsewhere in the same file or effort — is enough to derive a
     confident, defensible call. Most entries belong here, same as before.
   - **Genuinely the user's call.** The decision turns on something no amount
     of context resolves, because it was never a technical judgment call to
     begin with — a subjective/creative preference with no objectively
     better option (visual/creative direction, naming or voice, "which of
     these do you like"), a business/financial/legal call (budget, pricing,
     contractual terms, a risk tolerance they haven't stated anywhere), or a
     fact about their actual intent that the file doesn't carry (which
     client, whether they still want this feature, a priority call between
     two things they care about). The test: would two competent engineers,
     handed the exact same context, reasonably land on opposite answers
     because the "right" one depends on what the user wants rather than on
     what's technically correct? If yes, it's theirs.
   - **When genuinely unsure between the two:** default to auto-resolve —
     same bias as always, since asking too much defeats the point of a
     sweep. The one exception: default to *asking* instead when the call is
     high-cost or hard to reverse (real spend, an irreversible architecture
     choice, a client-facing commitment) — there, a wrong autonomous guess
     costs more than one extra question.
4. **Auto-resolvable → recommend, then resolve.** State a recommendation
   with one sentence of reasoning. If the file already marks an option
   `(Recommended)`, start from that — but actually re-read its stated
   tradeoff first; if it no longer looks like the right call (stale
   context, a later decision in the same file supersedes its premise,
   etc.), say so and recommend differently, with reasoning. Don't
   rubber-stamp a stale recommendation — this is the real judgment check
   for everything that stays in this skill's own hands, not a formality on
   the way to a foregone write. Then adopt the recommendation as the chosen
   option and go straight to Step 5 for this block — no confirmation, no
   pause. Log the header, chosen option, and one-line reasoning to the
   running summary as you go, so Step 6 can report every resolution
   without re-deriving it.
5. **Genuinely the user's call → hold it, don't write yet.** Add it to an asks
   queue instead of resolving it: the header, the plain-language question,
   and the options exactly as the file already states them, each with its
   stated tradeoff and which one — if any — the file already leans toward.
   Don't invent a recommendation of your own here; recommending one would
   just be guessing at the preference this branch exists precisely because
   you can't derive. Move on to the next entry — the queued question gets
   put to the user in Step 4.5, once the whole pass is walked.
6. **Can't resolve — data problem, not a place to defer.** If the block
   genuinely carries no usable options (a garbled or missing `Options
   presented` section, or there isn't even enough content to frame a real
   question), leave the block untouched, note it in the Step 6 summary as
   unresolved with the reason, and move on. This is for broken input, not a
   way to route a hard call to the user instead of working it — item 5 above is
   already where a genuinely-theirs call goes when the file has usable
   content to ask about.

**Scope boundary:** if the sweep surfaces something that *isn't* resolving
an existing queued block — a genuinely new decision that needs raising —
that's out of scope for Steps 4/4.5/5. Don't author a new `decisions.md`
entry here; name it in the Step 6 summary and route it to `team-intake`,
which owns the decision-log template and the context an entry needs.

## Step 4.5 — Put the user's-call items to them

Skip this step entirely if the asks queue from Step 4 item 5 is empty —
say so in Step 6 and go straight to wrap-up. This is the only step in the
sweep that pauses for the user; everything upstream and downstream of it stays
autonomous.

Otherwise, ask via `AskUserQuestion`, batching up to 4 questions per call
(its limit) and looping over the queue in batches until it's empty — a
large ask queue shouldn't turn into a string of separate interruptions when
one tool call can carry several at once. For each question:
- `header`: a short label for the effort/file (the tool's chip is short —
  keep this to a couple of words).
- `question`: the plain-language restatement captured in Step 4 item 1.
- `options`: the file's own `Options presented`, each as one option with
  its stated tradeoff as the description. If the file already marked one
  `(Recommended)`, keep it first with "(Recommended)" in its label — that's
  the file's own prior lean carried forward, not a fresh recommendation
  manufactured here (item 5 above deliberately doesn't add one).

As soon as a batch's answers come back, write each one back immediately per
Step 5 — before moving to the next batch, not after the whole queue is
answered — same "write right away, right after it's decided" discipline as
the auto-resolved path, just triggered by the user's answer instead of a
re-derived recommendation. Then fire the next batch if the queue isn't
empty yet.

A decision the user answers this way is a real, human-made call — record it as
`DECIDED`, not `DECIDED-AUTO` (see Step 5).

## Step 5 — Write the resolution back

Edit the source file's decision block in place, in the exact format this
project's own `decisions.md` files already use (see
`templates/resolution-block.md` for the concrete shape, including both the
`DECIDED-AUTO` and `DECIDED` variants) — never invent a different format.
The status token and `Decided by` name depend on which Step 4 path
resolved the block:

- **Auto-resolved (Step 4 item 4):** `- **Status:** PENDING` (or `PARKED`)
  → `- **Status:** DECIDED-AUTO`, with `**Decided by:** team-decisions
  (auto)`.
- **Answered by the user (Step 4.5):** `- **Status:** PENDING` (or `PARKED`) →
  `- **Status:** DECIDED` — the plain token, because this one genuinely was
  a human-made call — with `**Decided by:** the user (via team-decisions)`.
- Either way: `**Raised:** <date> · **Decided:** — · **Decided by:** —` →
  keep `Raised` as-is, fill `**Decided:** <today>` and the `Decided by`
  value above.
- Append, at the end of the block's existing content (before the next `## `
  heading or `---`):
  - `**Chosen:** <option letter> — <one-line summary of what was chosen>`
    — for a user-answered block, this is their actual answer (including their
    own wording if they used "Other"), not a paraphrase toward whichever
    option looks most defensible.
  - `**Note from decision-maker:** "<one-line reason this option won>"` —
    only if it adds something beyond the Recommendation reasoning (or,
    for a user-answered block, any annotation `AskUserQuestion` returned
    with their answer) already stated; omit the line entirely otherwise,
    don't pad it out.

**Preferred write path — the script, for the two shapes it recognizes:**

```
python3 ~/.claude/skills/team-decisions/scripts/resolve_decision.py \
  <file> <block-id> --chosen "B — <one-line summary>" --status DECIDED-AUTO \
  [--note "<one-line reason>"]
```

For a user-answered block, pass `--status DECIDED --decided-by "the user (via
team-decisions)"` instead — the script already supports both statuses; only
the flags you pass change.

(`--decided-by` defaults to `team-decisions (auto)` and `--status` defaults
to `DECIDED`, so an auto-resolved block still needs `--status
DECIDED-AUTO` passed explicitly — the default exists for the user-answered
path and any other future caller of this script, not as a shortcut for a
silent auto-resolution.)

All the judgment stays yours (the recommendation or the question, the
summary phrasing, capturing the note); the script only performs the
deterministic patch, and
it handles exactly the two conventions the scanner recognizes — the
canonical `- **Status:**` field and status embedded at the end of the `## `
heading line. On anything else (status folded into prose, a shape it can't
match exactly, a block that already carries a `Chosen` line) it **declines
loudly and writes nothing** — that's by design, not a bug: prose-embedded
status is exactly where mechanical substring patching risks corrupting an
ID reference, so those blocks stay freehand forever.

When the script declines (or the file uses `team-intake`'s `### Decision`
subheading shape — see the template's carve-out), fall back to a manual
`Edit`, targeting only that one block — never a blanket find/replace
across the file, since some files hold several entries and only one is
being resolved right now.

After the last resolution of the session (not per-decision), re-run the
scanner with `--write-index` so `OPEN-DECISIONS.md` reflects the sweep's
outcome — a stale index right after a walkthrough is the one staleness
mode the design can't self-announce past.

## Step 6 — Wrap the session

One tight summary:
- **Resolved automatically:** N decisions, each as `file:ID — one-line
  outcome`.
- **Resolved with your input:** K decisions, each as `file:ID — one-line
  outcome` — only entries that went through Step 4.5; omit this bucket
  entirely on a run where nothing needed asking.
- **Still open:** M decisions, each as `file:ID` (only ever because Step 4
  item 6 hit a genuine data problem — a missing/garbled options section —
  not because anything was skipped or left unasked; there's nothing left
  to skip past when the queue's already been walked and, where warranted,
  asked).
- **Files touched.**

Then — only if any files were actually touched; on a clean or all-unresolved
run there's nothing to commit, so skip this entirely — commit the touched
`decisions.md` files now, no ask: this skill's own local, docs-only commit,
staging exactly the files touched (plus the regenerated `OPEN-DECISIONS.md`,
which rides along whenever it changed) and naming which decisions were
resolved in the message, covering both buckets (auto and user-answered).
This is **not** a push or a merge; if those decisions should also land on
the default branch, name `/wrap-up` as the next step for that in the
summary, don't do it here.

Finally, append one line to this skill's own run-log (see Memory below).

## Best practices folded in (why each rule exists)

- **Auto-resolve what the context can settle; ask what's genuinely the user's
  call.** A sweep that always guesses risks silently overriding a
  preference only the user actually holds; a sweep that always asks defeats
  the whole point of an autonomous backlog-clearer. The classify gate in
  Step 4 item 3 is the load-bearing judgment call that keeps both failure
  modes in check — same posture as the `director-of-engineering` agent
  used elsewhere in this pipeline: solve what's genuinely yours to solve,
  escalate only what actually isn't.
- **One decision, one recommendation (or one question), one write.**
  Batching entries defeats the point of a sweep built for judgment
  quality — each decision gets read and weighed on its own, not skimmed as
  part of a list, and gets its own write immediately once it's resolved.
  The one batching that's allowed is delivery: Step 4.5 groups up to 4
  already-classified questions into a single `AskUserQuestion` call so a
  large ask queue doesn't turn into a string of separate interruptions —
  the judgment behind each question is still worked per-decision in
  Step 4; only the asking itself is batched.
- **Re-derive the recommendation, don't just echo the file's.** A
  `(Recommended)` tag was written when the decision was raised; by the time
  it's actually resolved, later decisions in the same file (or a sibling
  effort) may have already changed the premise. Rubber-stamping a stale
  recommendation is worse than not having one — and for the auto-resolved
  path, with no one left to catch a bad call downstream, this is the one
  place judgment has to be real, not a formality.
- **`PARKED` counts as open.** It was deliberately shelved, not resolved —
  leaving it out of the sweep would mean it never comes back up on its own.
- **Show the status-count table before anything else, every run.** A sweep
  can touch dozens of files and hundreds of historical blocks; without a
  quick tally there's no way to sanity-check "does 0 open sound right for a
  project this size?" or catch a scope mistake (wrong repo, a decisions.md
  format the parser choked on) before the resolution pass starts. The
  table costs nothing extra to produce — Step 2 already classifies every
  block — it just has to actually be shown instead of thrown away.
- **`DECIDED-AUTO` for the skill's own calls, plain `DECIDED` for the user's.**
  Every resolution this skill makes on its own authority is `DECIDED-AUTO`
  by construction, so the record stays honest and those entries stay
  flaggable for a later human review pass. A block the user actually answers
  through Step 4.5 gets the plain `DECIDED` token with `Decided by: the user
  (via team-decisions)` — it's a genuinely human-made call now, not a
  formality, and should read exactly like one everywhere else in this
  project's `decisions.md` convention does.
- **Write back in the project's own existing format.** These files are read
  by people and by other pipeline skills (`wrap-up`'s own audit step runs
  this skill's `scan_decisions.py` over them to find open items); a
  resolution in a different shape than the rest of the file breaks that.
- **No push/merge here.** Resolving a decision and landing it on the
  default branch are different concerns with different risk — this skill
  stays scoped to the former and defers to `/wrap-up` for the latter, even
  though the docs-only commit itself no longer waits on an ask.

## Memory

Append one line per run to
`~/.claude/skills/team-decisions/memory/decisions-log.md` (create it from
`templates/decisions-log-header.md` if it doesn't exist yet): date,
project/repo, decisions resolved (`file:ID` list), decisions left open,
whether the docs commit happened. **This line is appended on every
invocation, not just ones that reach a full sweep:**
- **Empty queue at Step 3** (scanned, nothing PENDING/PARKED):
  `Resolved`/`Still open` both blank — recording this is the point: it lets
  a future run tell "checked and it was clean" apart from "never checked."
- **Full sweep** (Step 4 ran): logged as before.

**Write the row itself with the script**, not freehand — the log has
already drifted from its own 5-column table shape twice when rows were
hand-typed:

```
python3 ~/.claude/skills/team-decisions/scripts/append_decision_log_row.py \
  --project "<project>" --resolved "file:ID, file:ID" \
  --open "file:ID" --committed yes|no|n/a
```

The script guarantees a valid table row (blank `--resolved`/`--open` for
an empty-queue run); it deliberately does **not** author prose. `--resolved`
carries both buckets from Step 6 (auto-resolved and user-answered) in one
list — the row itself doesn't distinguish them. When a run deserves
substantive notes under its row (process lessons, multi-wave detail,
per-decision rationale, or which items in this run went through Step 4.5),
write those freehand below the row, as the log already does.

**Once per project** (first run on a project, or whenever the pointer is
missing): if the project has a `PROJECT-CONTEXT.md`, check it for a
"shared decision-log" mention (grep — don't full-`Read`, same size trap as
Step 1) and, if absent, add a one-line pointer noting that cross-project
sweep history lives at
`~/.claude/skills/team-decisions/memory/decisions-log.md`. That's the hook
`team-status` Step 0.5's shared-doc mechanism reads, so "when was this
last swept" stops being invisible to the rest of the pipeline.

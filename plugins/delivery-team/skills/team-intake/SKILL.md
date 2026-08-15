---
name: team-intake
description: 'Run a virtual delivery team (triage, product owner, architect, engineer, QA, project manager, tech lead) over an incoming client request — on any project. Use when: a new feature/bug/change request comes in and needs to be understood, classified, and turned into a plan before any code is written; you have a file or folder describing what a client wants; you want intake/triage of a request; you need a technical plan AND a project-manager plan; or you want to know "have we seen this request before?" before acting. Produces a technical plan and a PM plan per request and remembers recurring issues (when the project has a defect catalog configured) so the team stops going in circles.'
argument-hint: '[<path> | direct <path> | fast <path>] — path to the intake base folder (holds the request; an `intake/` subfolder is created inside it for the plans). The run is fully autonomous — no human gates; every choice is made by the team, logged as DECIDED-AUTO, and reported at the end. `auto`/`auto-pilot` tokens are accepted for compatibility (they change nothing). See "Run modes" for direct/fast.'
---

# Team Intake

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Runs a small **virtual delivery team** over an incoming request and produces
two plans:

- **`technical-plan.md`** — what to do in the code (for the engineer who
  builds it).
- **`pm-plan.md`** — request type, history, *where it's coming from*, and how
  to stop it recurring (the plan the user reviews).

It exists because delivery teams keep re-solving the same problems. A
persistent **PM memory** — this project's own request log and, if configured,
its defect-class catalog — lets the team recognize repeats and break the
cycle instead of patching again.

This skill is an **orchestration**: you (the main agent) run the phases below
and delegate each role to a subagent. You are the delivery lead.

## The team (first-class agents, installed globally at `~/.claude/agents/`)
| Agent | Role |
|-------|------|
| `intake-triage` | Ingest the request → normalized brief; gate on ambiguity |
| `intake-project-manager` | Classify type, reconstruct history, own PM memory + PM plan |
| `intake-architect` | System/design impact, options, risks |
| `intake-engineer` | Exact code change set, feasibility, gotchas |
| `intake-product-owner` | Value, scope, acceptance criteria, sign-off needs |
| `intake-qa` | How we verify done + regression test to add |
| `intake-tech-lead` | Synthesize architect+engineer+QA → the technical plan |
| `intake-client-liaison` | Translate internal sign-off items into a plain-language client approval sheet (on demand) |

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-intake/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-intake/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

> **How to invoke each role:** these are registered subagent types — launch
> each with `subagent_type: "<name>"` (e.g. `subagent_type: "intake-architect"`).
> Always give the agent: the request-brief path, the output dir, and the
> PM's classification once known. (If for some reason a name isn't available
> as a subagent type, fall back to a `general-purpose` agent and paste the
> role brief from `~/.claude/agents/<name>.md`.)

## Run modes

**This skill runs fully autonomous in every mode — there are no human
gates.** (Removed 2026-08-14 on the user's direction, during the workflow-audit
apply pass.) Every choice the process used to stop for is instead made by
the team on its own best recommendation, logged to `decisions.md` as
`DECIDED-AUTO`, and listed plainly in the Step 6 report-back so nothing is
decided invisibly. A `BLOCKED` triage verdict no longer stops the run
either — see Step 2 for how it proceeds on recorded assumptions. The
`auto`/`auto-pilot` tokens are still accepted for compatibility but change
nothing.

Standard mode (bare `<path>`) runs the fixed 8-agent roster. Two optional
modes change the roster, and compose (`direct <path>`, `fast <path>`):

| Mode | Token(s) | What changes |
|---|---|---|
| Direct | `direct` | Right after Step 2's triage verdict, run `director-of-engineering` with this skill's own roster (the table above) instead of the fixed Step 3 fan-out; execute exactly the agents/order it returns in place of Steps 3–5. **`intake-project-manager` is never skippable** — it owns memory, `pm-plan.md`, and the `DECIDED-AUTO` self-consistency audit, which is the pipeline's only remaining internal check now that gates are gone. |
| Fast | `fast` | **Implies `direct`**, plus a speed bias: get something working with the direction still checked, QA deferred. Tell the director this run is **fast** — its roster default inverts to *skip unless load-bearing for direction* (product-owner/architect/tech-lead lean toward kept, `intake-qa` toward skipped; a defect-catalog match still forces the guardrail back on; the PM still always runs). At Step 6, the auto-decision becomes **"proceed straight to `team-build fast`"** — skipping the `team-qa` stage entirely — logged as `DECIDED-AUTO` with the deferred-QA trade-off named. |

Both modes still write every artifact this skill normally writes, to the same
paths — `direct` just produces fewer `supporting/*.md` files (only for the
agents actually run).

## Process

### Step 0 — Get the intake base folder (and the request inside it)
The provided folder is the **intake base folder**: it holds the request
materials *and* is where the plans get written (under an `intake/`
subfolder).

- Parse the skill argument for a leading mode token first — `direct` and/or
  `fast` (which implies direct), plus the legacy no-op tokens
  `auto`/`auto-pilot`, in any order, before the path (see "Run modes"
  above). Strip whatever mode tokens are present; whatever remains is the
  folder.
- If the user gave a folder path (as the skill argument or in the message),
  use it as the intake base folder. The request materials (ticket, email,
  doc, screenshots) live in this folder. (If they pointed at a single file
  instead, treat that file's parent folder as the base folder.)
- **If no folder was given**, resolve it from the conversation context (a
  folder or request file discussed this session). If nothing resolvable
  exists, the run cannot start — say so plainly and end; there is no
  request to intake. Do not invent a request or a location. (This is an
  error condition, not a gate — nothing to decide, nothing to run on.)

### Step 1 — Set up the intake folder
- Derive a short `slug` from the request (kebab-case, ~3 words).
- Scaffold with the script (creates the folder set and seeds `decisions.md`
  from the template so the FORMAT CONTRACT comment lands in every run):

  ```
  python3 ~/.claude/skills/team-intake/scripts/init_intake.py \
    <intake-base> <slug>
  ```

  It creates `<intake-base>/intake/<YYYY-MM-DD>-<slug>/` plus `supporting/`,
  using today's date. **Same-day collision rule:** if that folder already
  exists (a re-run or follow-up on the same slug today), the script appends
  `-2`, `-3`, … and prints the path it actually created — use the printed
  path. **Never write the plans to the root of `<intake-base>`** — they
  always go under the `intake/` subfolder. (If the script is unavailable,
  do the same by hand, including the collision suffix and the seeded
  `decisions.md`.)
- **Re-entry check (before running the team):** glob
  `<intake-base>/intake/*/` for an existing intake whose slug/brief covers
  the same ask. If one exists, this run is a *revision* — say so, link the
  prior folder in the new `request-brief.md` and `pm-plan.md`, and have the
  PM treat the prior plans as history rather than producing a disconnected
  second plan.

### Step 2 — Triage (gate)
Run `intake-triage` on the source → it writes `request-brief.md` and returns
a `READY` / `BLOCKED` verdict.

**PARKED re-trigger check — run by you, the orchestrator, while triage
works** (this is your step, not the triage agent's):

```
python3 ~/.claude/skills/team-decisions/scripts/scan_decisions.py --json \
  <intake-base> <project-root-if-different>
```

The scanner finds every `*decisions.md` under the given roots (use the
project root; add the intake base separately if it lives outside the repo)
and classifies statuses reliably — including format-drifted blocks a raw
grep would miss. From its PARKED list, flag any entry whose note names the
area this request touches — a PARKED decision often carries an explicit
re-trigger condition ("re-confirm when X gets scoped into a build cycle")
that only fires if someone actually checks. Don't auto-resolve a hit:
record it as a `WATCH` row in this run's `decisions.md`, name it in the
Step 6 report-back, and let the evaluators treat the parked question as
live context. This makes the re-trigger check systematic instead of
dependent on someone happening to remember.

**If `direct` was requested (including via `fast`):** once triage returns
its verdict (READY, or BLOCKED with assumptions adopted per above), run
`director-of-engineering` now with this skill's own roster (the
table under "The team") instead of the fixed Step 3 fan-out below — it writes
`run-plan.md`; execute exactly the agents/order it returns in place of
Steps 3–5. **If the run is `fast`, say so in the director's prompt** — its
keep/skip default inverts (see its "Fast mode" section).

**On a `BLOCKED` verdict, do not stop — proceed on recorded assumptions.**
(Gate removed 2026-08-14 on the user's direction.) For each blocking question
triage returned:
- Adopt the best-supported assumption (from the request materials, the
  project record, the decision-log, and triage's own non-blocking
  assumption list) and record the question + dated context + options +
  the adopted assumption in `decisions.md` as `DECIDED-AUTO`, with the
  rationale naming it an *assumption adopted in lieu of an answer*.
- Update the brief with the adopted assumptions, then run the rest of the
  team as normal.
- **Flag the run loudly:** the Step 6 report-back must open with a
  "Proceeded despite BLOCKED triage — N assumptions adopted" line listing
  each one, so a wrong guess is cheap to catch and reverse before anything
  gets built. The plans exist to be reviewed; nothing is implemented by
  this skill.
Non-blocking clarifying questions get the same treatment: log as
`DECIDED-AUTO` with the assumption, keep going (see "Decision logging"
below).

### Step 3 — Evaluate (parallel fan-out)
Launch these **four agents in parallel** (one message, multiple tool calls).
Give each the `request-brief.md` path and the `supporting/` output path:
- `intake-product-owner` → `supporting/product-owner.md`
- `intake-architect` → `supporting/architect.md`
- `intake-engineer` → `supporting/engineer.md`
- `intake-qa` → `supporting/qa.md`

Tell each to **start from the brief's Scout digest** (triage's shared
findings: stack, layout, test commands, candidate files, relevant
defect-catalog entries) instead of re-deriving those facts — their
*judgment* stays independent; the perspective-independent discovery is
paid once, by triage.

### Step 4 — Project Manager
Run `intake-project-manager`. It reads the brief + the four supporting files
+ **PM memory** (the decision-log, this project's own request-log *if
`PROJECT-CONTEXT.md` names one*, the defect catalog if configured, and the
project's existing `intake/*/` folders as the history record), classifies
the request, reconstructs history, writes `pm-plan.md`, and updates memory
(the defect catalog if it's a repeat or a likely-repeat and the project has
one; the project's own request-log if it has one — **the global request-log
was retired 2026-08-14 and no longer exists**). Capture its final
**request type** — the tech lead needs it. The PM runs in **every** mode,
including direct/fast — the director may not skip it.

### Step 5 — Technical plan
Run `intake-tech-lead` with the brief, the supporting files
(product-owner/architect/engineer/qa — whichever ran), and the PM's
classification → it writes `technical-plan.md`. If its summary returns any
`decisions.md` row content (a PENDING/WATCH scope boundary), **you** append
it via `add_decision.py` — the tech-lead deliberately cannot write that
file itself.

### Step 6 — Report back
Summarize for the user in the chat:
- **If triage was BLOCKED:** open with "Proceeded despite BLOCKED triage —
  N assumptions adopted", listing each adopted assumption first.
- Request **type** and **"seen before?"** (cite the defect-catalog id if
  matched and this project has one configured).
- The PM's headline recommendation (esp. the cycle-breaker if recurring).
- The technical approach in 2–3 bullets.
- Any **PENDING / PARKED decisions** still open (from `decisions.md`).
- Every `DECIDED-AUTO` entry from this run — "Decided automatically:
  N items — see decisions.md."
- Links to `pm-plan.md`, `technical-plan.md`, and `decisions.md`.

**Next stage (no ask, no wait):** the run always ends by *recording* the
next step, never by silently invoking another skill. Log "proceed to
`team-qa` next" to `decisions.md` as `DECIDED-AUTO` (unblocking the next
stage is this skill's whole purpose) and state it plainly in the summary —
the actual `team-qa` invocation is the user's (or a supervising
orchestrator's) to make; this skill does not launch it. **Under fast,**
the auto-decision is instead "proceed straight to `team-build fast`" — the
`team-qa` stage is deliberately skipped; log the `DECIDED-AUTO` entry
naming the trade-off (QA deferred, build will carry a `FAST — QA debt`
stamp so a later `team-status` pass recommends the follow-up `team-qa`
run).

### Step 7 — Client approval sheet (optional, on demand)
When sign-off items need to go to a non-technical client, run
`intake-client-liaison`. It reads `decisions.md`, `supporting/product-owner.md`,
and `technical-plan.md` and writes a plain-language `client-approval.md` (no
internal codes/jargon) plus a private `client-question-map.md` crosswalk so
the returned answers map back to the internal items/decisions. The client
only ever sees `client-approval.md`.

## Decision logging
Whenever the team encounters a question that would once have gone to the
user — a triage ambiguity, a genuine preference fork, a scope call — record
it so the team keeps a readable history of *what we chose and why* (and
never re-litigates a settled call). Two places:

1. **Per request:** `<intake-base>/intake/<date>-<slug>/decisions.md` (from
   `templates/decision-log.md`) — the full, readable record. For each
   question capture, in this order: **the question**, **"where we're coming
   from"** (the dated history/context — current ask vs. what was decided
   before and when, and what conflicts), **the options considered**, and
   **the decision** (chosen option + rationale + implications). **Author
   new blocks with the script, not by hand** — it emits the FORMAT-CONTRACT
   shape by construction and self-checks it parses back clean:

   ```
   python3 ~/.claude/skills/team-decisions/scripts/add_decision.py \
     <decisions.md> --id DEC-<n> --title "..." --status DECIDED-AUTO ...
   ```

2. **Global:** append a one-line row to the decision-log (location per
   `PROJECT-CONTEXT.md`, else this skill's global fallback memory) — via
   the validated appender, never a hand-typed row:

   ```
   python3 ~/.claude/skills/team-intake/scripts/append_intake_decision_row.py \
     --project "<project>" --slug "<slug>" --decision-id DEC-<n> \
     --item "<area>" --status DECIDED-AUTO \
     --decision "<one line, ≤300 chars>" --link "<path/decisions.md>"
   ```

Questions the team answers itself are logged directly as `DECIDED-AUTO`
with the adopted assumption/recommendation. `PARKED` remains available when
the materials themselves defer something to a named stakeholder. The PM
reads the decision-log during history reconstruction, so a question
answered once stays answered.

**Propagate the flip, don't just log it.** The moment an entry moves off
`PENDING`/`PARKED`, grep the project for every other doc that cited its old
status — a technical-plan's Risks/rollback section, a sibling item's own
`decisions.md`, the defect catalog if configured, a cached
`status-report.md` — and correct them in the same sitting. If a citing doc
is out of this skill's write scope (product code, another team's memory) or
genuinely unreachable this session, **name it explicitly in the Step 6
report-back** instead of leaving it silently stale — that's what lets a
later `team-status` pass close the loop.

## Conventions
- **Autonomous decisions must be visible, not silent.** There are no human
  gates in this skill (removed 2026-08-14). The compensating discipline:
  every choice the team makes on the user's behalf is (1) logged to
  `decisions.md` as `DECIDED-AUTO` with its rationale, (2) listed in the
  Step 6 report-back, and (3) — for assumptions adopted over a BLOCKED
  triage verdict — flagged at the *top* of the report-back, not buried.
  The `intake-project-manager`'s DECIDED-AUTO self-consistency audit (its
  job 2) is the standing internal check on these decisions and is why the
  PM can never be skipped.
- **Intake base folder:** provided by the user (skill argument or message);
  if omitted, the skill asks for it. The request lives here and the
  per-request output is written under an `intake/` subfolder inside it —
  never at its root.
- **Output per request:** `<intake-base>/intake/<date>-<slug>/` containing
  `request-brief.md`, `pm-plan.md`, `technical-plan.md`, `decisions.md`, and
  `supporting/*.md`.
- **Templates:** `~/.claude/skills/team-intake/templates/`.
- **PM memory:** location comes from `PROJECT-CONTEXT.md` if the project
  names one; otherwise `~/.claude/skills/team-intake/memory/` (a
  cross-project fallback — defect catalog read first every run if the
  project has one configured; `decision-log.md` append-only, scripted
  appends only, rows ≤300 chars). **The global `request-log.md` was
  retired and deleted 2026-08-14** — request history now lives in each
  project's own request-log (if `PROJECT-CONTEXT.md` names one) and in the
  project's `intake/*/` folders themselves.
- **Project profile (write-once, then reuse):** if the project has no
  `PROJECT-CONTEXT.md` — or has one with no profile section — after Step 5
  write/append a short profile (stack, layout, test commands, memory
  locations) to `PROJECT-CONTEXT.md` at the project root, log it as
  `DECIDED-AUTO`, and name it in the Step 6 report-back. Later intakes,
  and every other delivery-team skill, then trust the profile instead of
  re-discovering the project each run (the `worktree` skill's established
  pattern).
- Investigation is read-only. This skill plans; it does not modify product
  code.

## The recurring trap this skill exists to catch
If this project has a defect-class catalog configured (`PROJECT-CONTEXT.md`),
a request that matches a known recurring pattern must be flagged by the PM,
and the technical plan must apply that pattern's durable fix (typically:
route content/logic through its canonical source rather than hand-editing one
path) — never quietly re-take a shortcut the catalog already proved doesn't
work. On a project with no catalog configured, this team still enforces the
general discipline (classify accurately, check for scope/requirement drift,
recommend systemic fixes over patches) — just without a documented history
to check against.

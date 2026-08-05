---
name: team-build
description: 'Run a virtual engineering team (build-triage, build-planner, test-author, implementer, verifier, reviewer, build-lead) over an approved plan to actually BUILD it — on any project. Use when: a team-intake technical-plan and a team-qa test-plan exist and the work now needs to be implemented; you want code written test-first and proven red→green before it is declared done; you have an approved change to build and want it built without re-litigating the design; or a project has its own recurring-defect catalog and you want any durable structural cure actually applied instead of an inline shortcut. Produces a reviewable green diff in an isolated per-effort git worktree plus a build-report, and remembers when a build re-takes a shortcut so the team stops shipping the same regression — when the project has a defect catalog configured to remember it in.'
argument-hint: '[<path> | auto|auto-pilot [direct] <path> | direct [auto] <path> | fast <path>] — path to the completed intake folder (holding intake/.../technical-plan.md and, except under fast, qa/.../test-plan.md). A build/ subfolder is created inside it for the build artifacts. Optional — will ask if omitted. See "Run modes" for the auto-pilot/direct/fast tokens.'
---

# Team Build

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Runs a small **virtual engineering team** over an *already-approved* plan and
actually implements it. It is the third team in the trilogy — it closes the
loop:

- **`team-intake`** plans *what to change* → `technical-plan.md`.
- **`team-qa`** plans *what tests must go red-then-green* → `test-plan.md`.
- **`team-build`** writes those tests, implements to green, and **proves it** →
  a reviewable diff in an isolated worktree + **`build-report.md`** (the doc
  the user reads).

It exists because the build step is the one place a project's chronic
regressions are actually *introduced or prevented*: a durable cure gets
applied or someone takes the inline shortcut and ships green-but-broken. This
team is built to make any known cure **non-skippable when a project has one
configured** — the planner marks it mandatory, the implementer is forbidden
the shortcut, the verifier won't sign off without the guard, and the reviewer
adversarially hunts for exactly those traps. Everything project-specific (a
recurring-defect catalog, repo conventions) is optional and loaded from that
project's own `PROJECT-CONTEXT.md` if it has one — this team runs generically,
just without those extra guardrails, on a project that doesn't.

Unlike `team-intake` and `team-qa` — read-only planners that fan out four
agents in parallel — **`team-build` mutates product code**, and its core is a
**sequential red-first loop, not a fan-out**. This is an **orchestration**: you
(the main agent) run the phases below and delegate each role to a subagent.
You are the build lead.

> **This team is destructive by design — it edits a working tree in place.**
> That tree is an **isolated per-effort git worktree** (one checkout per repo
> the plan touches, on its own branch — see `build-triage`), never the single
> shared checkout, so two builds running around the same time can't blend into
> each other's uncommitted work. The first agent provisions that worktree set
> (+ a namespaced Docker stack, if the project has one) and records the
> starting commit(s) so the whole run stays a reviewable diff with a
> one-command back-out per repo. In standard mode it **stops at green +
> report**: it does NOT commit, push, or open a PR, and it does NOT tear the
> worktree/stack down — those are the user's call. **Under `auto-pilot`**,
> Step 8 commits + pushes on the effort's own isolated branch (see "Run
> modes"); teardown stays manual in every mode regardless, since an unmerged
> branch is still live work.

## The team (first-class agents, installed globally at `~/.claude/agents/`)
| Agent | Role |
|-------|------|
| `build-triage` | Confirm the two plans exist + are buildable; discover the project's repo layout; provision an isolated per-effort git worktree set + namespaced Docker stack (if the project has one); gate on a clean tree per repo; record the starting commit(s); write the build brief |
| `build-planner` | Turn technical-plan + test-plan into one ordered, dependency-correct task list; mark any project-specific **durable-cure** steps MANDATORY |
| `build-test-author` | Write the test-plan's tests and **prove each RED** before any product code changes |
| `build-implementer` | Apply the change set to GREEN, applying any MANDATORY durable cure — **no inline shortcuts** |
| `build-verifier` | Run all relevant suites, prove red→green per test, run the DoD checklist + any project-specific standing guards; gate |
| `build-reviewer` | Adversarial diff review against this project's known traps (if it has a defect catalog) plus ordinary correctness/simplification |
| `build-lead` | Sequence/reconcile the loop, write `build-report.md`, update build memory + this project's defect catalog if it has one |

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-build/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-build/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

> **How to invoke each role:** these are registered subagent types — launch
> each with `subagent_type: "<name>"` (e.g. `subagent_type: "build-implementer"`).
> Always give the agent: the `build-brief.md` path, the output dir, the paths
> to `technical-plan.md` and `test-plan.md`, and (once known) the ordered task
> list. (If a name isn't available as a subagent type, fall back to a
> `general-purpose` agent and paste the role brief from
> `~/.claude/agents/<name>.md`.)

## Run modes

Standard mode (bare `<path>`) is the default described in "Process" below:
the fixed 7-agent sequential roster, every 🟧 gate stops and waits. Two
optional modes change that, and compose in either order
(`auto direct <path>` / `direct auto <path>`):

| Mode | Token(s) | What changes |
|---|---|---|
| Auto-pilot | `auto-pilot`, alias `auto` | Every gate in "Process" is tagged **PREFERENCE**, **QUALITY**, or **SHIP**. PREFERENCE gates no longer stop — the team decides on its own best recommendation, logs the choice to `decisions.md` as `DECIDED-AUTO`, and keeps going. QUALITY gates (a `BLOCKED` verdict from a missing/incomplete plan, a red test that's already green, a fix loop that didn't converge) still stop, in every mode — there's no recommendation to make when the premise is broken. **SHIP gates proceed too under auto-pilot** (Step 8): commit + push land on this effort's own isolated branch, and open a PR if this project has that convention. What never changes, in any mode — this environment's own standing safety floor, not a skill preference: no force-push, no `--no-verify`, no push straight to the repo's default branch. |
| Direct | `direct` | Right after Step 1's `build-triage` returns `READY`, run `director-of-engineering` with this skill's own roster (the table under "The team"). **Build's red-first TDD core is structural, not discretionary** — `build-test-author` (Step 3), `build-implementer` (Step 4), and `build-verifier` (Step 5) always run; direct mode's real discretion here is over `build-planner` (Step 2 — foldable for a single obviously-ordered task) and `build-reviewer` (Step 6 — skippable only for a small, low-risk diff, unless a defect-catalog match forces it back on). `build-triage` and `build-lead` always run regardless. |
| Fast | `fast` | **Implies `auto` + `direct`**, plus a degraded-verification contract for building from a `technical-plan.md` alone — no `test-plan.md` required and no `team-qa` detour (Step 0's ask is skipped; the missing test-plan is logged `DECIDED-AUTO` as a named trade-off). The red-first core survives at **smoke level**: `build-test-author` derives **1–3 smoke assertions from the technical-plan's acceptance criteria** (not from a test-plan) and proves them red; the implementer makes them green; `build-verifier` runs a **fast DoD** — existing suites still green, smoke proof red→green, the thing actually runs. `build-reviewer` follows direct-mode discretion. The build-report and Step 8 summary carry a **`FAST — QA debt`** stamp listing what was deferred, so a later `team-status` pass recommends the follow-up `team-qa` run instead of the gap disappearing. QUALITY gates (BLOCKED triage, a smoke test that's already green, a non-converging fix loop) still stop; a **defect-catalog match still forces the full guardrail** for that concern, fast or not. Ship gate behaves as auto-pilot (commit + push on the effort's own branch). |

Both modes still write every artifact this skill normally writes, to the same
paths — `direct` just produces a thinner `run-plan.md`-guided pass (fewer of
the discretionary agents above), and `auto-pilot` still writes `decisions.md`,
just with `DECIDED-AUTO` entries instead of a stop.

## Process

### Step 0 — Get the approved plans and the output location
team-build needs **the technical-plan** (what to build) and **the test-plan**
(what to prove). Both normally live inside a completed intake folder:

- Parse the skill argument for a leading mode token first — `auto`/
  `auto-pilot`, `direct`, and/or `fast` (which implies both), in any order,
  before the path (see "Run modes" above). Strip whatever mode tokens are
  present; whatever remains is the path.
- If the user gave a path to a completed intake folder, use it. The plans are
  at `<intake-dir>/intake/.../technical-plan.md` and
  `<intake-dir>/qa/.../test-plan.md` (or directly inside it). Locate both —
  **under `fast`, only the technical-plan is required.**

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **required-input, unaffected by any mode.**
- **If nothing was given, STOP and ask:** "Point me at the completed intake
  folder — the one holding the `technical-plan.md` and the `test-plan.md`.
  I'll build it in an isolated worktree and write the build report next to
  them." No mode removes this gate — there's nothing to recommend a location
  for.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
- **If only the technical-plan exists (no test-plan), STOP and ask** whether
  to run `team-qa` first. Strict red-first TDD needs the test-plan; do not
  build blind. **Under auto-pilot,** skip the ask: default to "yes, run
  `team-qa` first" (this skill's own rule is never build blind — that's the
  best recommendation there is), log it to `decisions.md` as `DECIDED-AUTO`.
  **Under `fast`, the default flips:** proceed with the technical-plan alone —
  no `team-qa` detour — and log the missing test-plan to `decisions.md` as
  `DECIDED-AUTO` naming the trade-off (smoke-level verification only; QA
  deferred; the build-report will carry the `FAST — QA debt` stamp).
- Do not invent a plan or a location.

**Output location:** write under `<intake-dir>/build/<YYYY-MM-DD>-<slug>/`
(reuse the intake slug; create a `supporting/` subfolder). Use today's date.
**Never write build artifacts to a repo root.**

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
### Step 0.5 — Version bump check (only if the project has one)
Check whether this project has a version-bump convention — `PROJECT-CONTEXT.md`
names it if so. In standard mode, **always ask the user whether to bump before
this build starts** — every time, regardless of whether a bump already
happened earlier in the same session, and regardless of how obviously due a
bump seems. This is a standing rule for any project with a configured bump
mechanism, not a judgment call to skip — in standard mode.
- Ask with `AskUserQuestion` (or plain text): "Should we bump the version
  before building?" with options along the lines of *not yet* / *bump now
  (build/patch/minor/major)* / *no bump needed for this change*.
- Follow the mechanism `PROJECT-CONTEXT.md` names exactly (script, files it
  updates, commit convention).
- If the project has **no** version-bump convention configured, skip this step
  entirely — don't invent one.
- If the user says not yet / no bump needed, proceed straight to Step 1.
- **Under auto-pilot,** skip the ask: decide per the project's documented
  convention (bump at the level the convention names for this change's scope,
  or no bump if the convention says this class of change doesn't warrant one),
  follow the mechanism exactly as above, and log the decision to
  `decisions.md` as `DECIDED-AUTO` with the rationale, instead of waiting.

### Step 1 — Triage + safety gate (gate)
Run `build-triage`. It confirms both plans are present and buildable,
discovers the project's repo layout (checking `PROJECT-CONTEXT.md` first, else
discovering it), **provisions a per-effort worktree for every repo in that
layout** (new branch off its base branch for repos the plan touches,
base-branch HEAD for untouched ones), generates a namespaced Docker compose
stack if the project has one, **confirms each worktree is clean**, records the
**starting commit per repo**, registers the effort if this project has a
registry configured, writes `build-brief.md`, and returns a `READY` /
`BLOCKED` verdict.

**If `direct` was requested:** once triage returns `READY`, run
`director-of-engineering` now with this skill's own roster (the table under
"The team") — remember its discretion is limited to `build-planner` and
`build-reviewer` (see "Run modes" above); the red-first TDD core always runs.
It writes `run-plan.md`; follow exactly what it returns for those two agents.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **split by cause.**
- If **BLOCKED because a plan is missing/incomplete** — **QUALITY gate, stays
  in every mode, including auto-pilot.** Surface it to the user with
  `AskUserQuestion` (or plain text) and wait. There's no recommendation to
  make when the input itself isn't real.
- If **BLOCKED because a worktree is dirty** — **PREFERENCE gate.** In
  standard mode, surface it and wait: do not blend the build into
  uncommitted work; offer to stash/commit first or proceed on a named clean
  base. **Under auto-pilot,** auto-pick the skill's own already-offered safe
  option — `git stash -u` on the dirty worktree — log it to `decisions.md` as
  `DECIDED-AUTO`, and proceed. (Stashing is reversible and was already an
  offered path in standard mode; this isn't a new risk auto-pilot invents.)
- **Log every clarifying/blocking question and its answer** (see "Decision
  logging").

### Step 2 — Plan the build
Run `build-planner`. It reads `technical-plan.md` + `test-plan.md` + the brief
and writes `build-task-list.md`: one **ordered, dependency-correct** task list,
with each step independently checkable. It marks every **durable-cure** step
this project's defect catalog (if configured) calls for as **MANDATORY — not
optional**, citing the catalog id. Capture the ordered list — the next steps
follow it.

### Step 3 — Author the tests, red-first (gate)
Run `build-test-author`. It writes the tests named in `test-plan.md`, runs
them, and **proves each one RED** against the current (unbuilt) code in this
effort's worktree, recording the exact failing output. It changes test files
only — **no product code**.

**Under `fast` (no test-plan):** the test-author instead derives **1–3 smoke
assertions from the technical-plan's acceptance criteria** — the minimum
proof that the new behavior exists at all (one happy-path per acceptance
criterion, no edge-case matrix) — and proves those red the same way. This is
deliberately not a QA pass; it exists so the build can still prove it
changed something. The red-that-comes-up-green gate below applies to smoke
tests identically.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate, stays in every mode,
including auto-pilot.**
- If a test that should be red passes green already, that's a signal the plan
  is wrong or the behavior already exists — **surface it and pause**; do not
  paper over it. A test that can't be made red can't prove the fix, and
  auto-pilot has no "best recommendation" for a contradiction like this.

### Step 4 — Implement to green (sequential)
Run `build-implementer`. It works `build-task-list.md` **in order**, applying
the change set from `technical-plan.md` to make the red tests pass, inside
this effort's worktree. Hard rules it carries:
- Apply any structural cure the plan marked MANDATORY; do not substitute an
  inline patch.
- One implementer, sequential — no parallel edits to the same files.
- Keep changes scoped to the task list; if it discovers the plan is wrong
  mid-build, it stops and reports rather than improvising a different design.

### Step 5 — Verify (gate)
Run `build-verifier`. It brings up this effort's own isolated Docker stack (if
the project has one and the plan's scope needs it), runs the **full relevant
suites**, confirms **each new test went red→green**, and runs the Definition
of Done from the plans plus any standing guards this project's defect catalog
calls for. It records the green evidence.

**Under `fast`, the DoD is the fast DoD:** existing suites still green, every
smoke assertion proven red→green, and the built thing demonstrably runs
(app boots / endpoint answers / command exits clean — whatever the
technical-plan's surface implies). Defect-catalog standing guards still run —
fast never skips a guard the project already paid to learn. Everything else
in the plans' full DoD is recorded as **deferred**, not silently dropped —
the list feeds the `FAST — QA debt` stamp.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **QUALITY gate, stays in every mode,
including auto-pilot.**
- If anything is **red** or a **DoD item fails**, loop back to **Step 4**
  (implementer fixes), bounded — after ~3 fix attempts without convergence,
  stop and report to the user rather than thrashing. Never edit a test to make
  it pass. Auto-pilot gets the same bound, no silent 4th attempt — a build
  that can't converge is a QUALITY problem, not a preference to auto-decide.

### Step 6 — Adversarial review
Run `build-reviewer`. It reviews the **diff since the starting commit**, per
touched repo, against this project's known traps (if it has a defect catalog
configured) plus ordinary correctness/simplification. A real defect loops back
to **Step 4**.

### Step 7 — Synthesize + report
Run `build-lead`. It writes `build-report.md`, updates the build run-log, and
— if the build had to re-apply a known cure, took (or was tempted to take) a
shortcut, or exposed a new repeatable build trap, and this project has a
defect catalog configured — updates it. Capture its headline.

### Step 8 — Report back (stop at green)
Summarize for the user in chat:
- **What was built** and the **change verdict** (GREEN / GREEN-WITH-CAVEATS /
  BLOCKED).
- **Red→green evidence** — the new tests, observed red-before / green-after.
- **DoD checklist status** + whether any durable cure was applied or deferred.
- **Where the diff lives** (this effort's worktree paths — not any shared
  checkout) and the **one-command back-out per repo**
  (`git -C <worktree-path> reset --hard <starting-commit>`).
- Any **PENDING / PARKED decisions** still open (from `decisions.md`).
- Links to `build-report.md`, `build-task-list.md`, and `decisions.md`.
- **Under auto-pilot:** also list every `DECIDED-AUTO` entry from this run —
  "Decided automatically (auto-pilot): N items — see decisions.md."
- **Under `fast`:** lead with the **`FAST — QA debt`** stamp — it goes in
  both this summary and `build-report.md`'s header — listing exactly what
  was deferred (no test-plan, smoke-only coverage, the full-DoD items the
  verifier recorded as deferred) and the recommended follow-up: "run
  `team-qa` on this intake folder, then a follow-up build for the tests it
  plans." A later `team-status` pass reads this stamp to recommend that
  follow-up; never present a fast build as fully verified.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **SHIP gate.** In standard mode, **stop**
— do not commit, push, or open a PR. Ask whether the user wants to commit or
hand it back for changes. **Under auto-pilot,** proceed: commit on this
effort's own isolated branch (the one `build-triage` provisioned, never a
shared checkout), push it, and open a PR if this project has that convention
— then report what was pushed instead of asking. This is the one line that
does not bend to any mode, auto-pilot included, because it's this
environment's own standing safety floor rather than a per-skill preference:
**never force-push, never `--no-verify`, never push straight to the repo's
default branch.** Auto-pilot commits land on the effort's own branch, full
stop. **Whichever mode performs the commit,** append the resulting commit
SHA (per repo) to `build-report.md`'s "Shipped commit" field afterward —
`build-lead` can't fill this in at Step 7 since the commit hasn't happened
yet, but leaving it blank is how `team-release`'s `release-lead` ends up
re-deriving shipped commits from raw git history instead of reading them.

> **After the release ships:** when this build (and any others) are committed
> and a version is cut, run **`team-release`** to produce client-facing
> release notes bundling everything in the version, fact-checked against the
> actual shipped commits. That is the outward-facing end of the pipeline;
> team-build stays internal.

## Decision logging
Whenever a clarifying or blocking question goes to the user — at the Step 1
gate, a red-that-came-up-green at Step 3, a non-converging fix loop at Step 5,
or anywhere a decision is genuinely the user's to make — record it so the team
keeps a readable history. Two places:
1. **Per build:** `<output-dir>/decisions.md` (from `templates/decision-log.md`)
   — the full readable record: the question, "where we're coming from" (dated
   context), the options, and the decision. Mirror how it's presented in chat.
2. **Global:** the build run-log captures the run; if a decision maps to an
   entry in this project's defect catalog (if configured), note the reference
   there.

Write the entry as `PENDING` *before* asking; flip to `DECIDED` (or `PARKED`)
once answered.

**Propagate the flip, don't just log it.** The moment an entry moves off
`PENDING`/`PARKED`, grep the project for every other doc that cited its old
status — a technical-plan's Risks/rollback section, a sibling item's own
`decisions.md`, the defect catalog if configured, a cached
`status-report.md` — and correct them in the same sitting. If a citing doc
is out of this skill's write scope (product code, another team's memory) or
genuinely unreachable this session, **name it explicitly in the Step 8
report-back** instead of leaving it silently stale — that's what lets a
later `team-status` pass close the loop.

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
  answer with a single letter instead of re-describing the option. A gate
  with only one path (a plain yes/no "proceed?") doesn't need lettering —
  this is for genuine multi-way choices.
- **Version bump: always ask, every time, only if this project has a
  configured mechanism (Step 0.5).** Never decide unilaterally — ask the user,
  even if a bump already happened earlier in the same session. **Under
  auto-pilot**, this becomes a `DECIDED-AUTO` per the project's own
  convention instead of a stop — see "Run modes".
- **Inputs:** a completed intake folder holding `technical-plan.md` +
  `test-plan.md`; if omitted, the skill asks. Do not build without both.
- **Output per build:** `<intake-dir>/build/<date>-<slug>/` containing
  `build-brief.md`, `build-task-list.md`, `build-report.md`, `decisions.md`,
  and `supporting/*.md` (red/green evidence logs).
- **Templates:** `~/.claude/skills/team-build/templates/`.
- **Memory:** the build run-log location comes from `PROJECT-CONTEXT.md` if
  the project names one; otherwise falls back to
  `~/.claude/skills/team-build/memory/build-run-log.md` (a cross-project log —
  less useful than a project-specific one, but available). A project's own
  recurring-defect catalog, if it has one, is **its own** — read it, update it
  when a build re-takes a shortcut or re-applies a cure, never fork it into
  this skill's global memory.
- **This skill mutates a tree in place, sequentially, one implementer, no
  parallel edits to the same files within a build.** It gates on a clean tree
  per repo, records the starting commit(s), builds **strict red-first**, and
  in standard mode **stops at green + report** — no commit/push/PR (under
  `auto-pilot`, it does commit/push, per "Run modes" — never teardown though,
  in any mode, since that's always the user's call).
- **Every build runs in its own isolated git worktree set** (+ a namespaced
  Docker stack, if the project has one), provisioned by `build-triage`.
  Teardown is manual, run by whoever merges — never automatic, since an
  unmerged branch is still live work.
- **Repo layout is project-specific — discover it, don't assume one.** Check
  `PROJECT-CONTEXT.md` first; a project may be a single repo or contain
  several independent ones.

## The recurring trap this skill exists to catch
**The build is where a durable cure is applied or skipped.** On any project
with a recurring-defect catalog configured, every chronic regression shipped
because, at build time, someone hand-edited a point-fix instead of the
structural cure the catalog calls for — and the green suite hid it.
team-build must **apply the structural cure the plan specified (when one is
called for), prove every new test red→green, and never declare done on a
green suite that doesn't cover the new surface.** No inline shortcut, no
editing a test to make it pass, no "it's green so it's fine." On a project
with no catalog configured, this team still enforces the general discipline
(red-first, no test-weakening, adversarial review) — just without
project-specific guardrails to check against.

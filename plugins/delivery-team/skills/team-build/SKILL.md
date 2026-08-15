---
name: team-build
description: 'Run a virtual engineering team (build-triage, build-planner, test-author, implementer, verifier, reviewer, build-lead) over an approved plan to actually BUILD it — on any project. Use when: a team-intake technical-plan and a team-qa test-plan exist and the work now needs to be implemented; you want code written test-first and proven red→green before it is declared done; you have an approved change to build and want it built without re-litigating the design; or a project has its own recurring-defect catalog and you want any durable structural cure actually applied instead of an inline shortcut. Runs end-to-end with no stop-and-ask checkpoints — every decision that used to pause for a human is now auto-decided and logged, and a green build commits + pushes automatically on its own effort branch. Produces a reviewable (after the fact) diff in an isolated per-effort git worktree plus a build-report, and remembers when a build re-takes a shortcut so the team stops shipping the same regression — when the project has a defect catalog configured to remember it in.'
argument-hint: '<path> — path to the completed intake folder (holding intake/.../technical-plan.md and, if one exists yet, qa/.../test-plan.md). A build/ subfolder is created inside it for the build artifacts. Required — this skill no longer asks if it''s omitted; see "No gates, no modes" below.'
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Workflow
  - Workflow(delivery-team:build)
---

# Team Build

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Runs a small **virtual engineering team** over an *already-approved* plan and
actually implements it — **start to shipped, with no human checkpoints along
the way.** It is the third team in the trilogy — it closes the loop:

- **`team-intake`** plans *what to change* → `technical-plan.md`.
- **`team-qa`** plans *what tests must go red-then-green* → `test-plan.md`.
- **`team-build`** writes those tests, implements to green, proves it, and
  **ships it** — a diff on its own effort branch, pushed, plus
  **`build-report.md`** (the doc the user reads afterward).

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
agents in parallel — **`team-build` mutates product code and ships it**, and
its core is a **sequential red-first loop, not a fan-out**. This is an
**orchestration**: you (the main agent) run the phases below and delegate each
role to a subagent. You are the build lead.

## No gates, no modes

This skill used to stop and wait for a human decision at several points
(missing input, a version-bump preference, a dirty tree, a plan that turned
out unbuildable, a test that came up green when it should be red, a
non-converging fix loop, and a final ship-or-hold ask) and offered `auto`,
`direct`, and `fast` tokens to change that behavior per run. **All of that is
gone.** There is one way this skill runs now: **the full fixed 7-agent
roster, full rigor, every decision that used to be asked is auto-decided
using this skill's own already-documented best recommendation for it, and a
green build commits + pushes automatically.** Nothing pauses mid-run to ask
anything — see "What happens instead of asking," per step, below. If you want
a build reviewed before it ships, review the pushed branch/PR after the fact,
the same way you'd review anyone else's commit.

**The one thing that still doesn't bend, because it was never a per-skill
preference to begin with — this environment's own standing safety floor:**
**never force-push, never `--no-verify`, never push straight to the repo's
default branch.** Every ship lands on the effort's own isolated branch, full
stop.

> **This team is destructive by design — it edits a working tree in place.**
> That tree is an **isolated per-effort git worktree** (one checkout per repo
> the plan touches, on its own branch — see `build-triage`), never the single
> shared checkout, so two builds running around the same time can't blend into
> each other's uncommitted work. The first agent provisions that worktree set
> (+ a namespaced Docker stack, if the project has one) and records the
> starting commit(s) so the whole run stays a reviewable diff with a
> one-command back-out per repo.
>
> **Gate-then-ship ordering is still not optional under time or merge
> pressure — it just no longer requires a human to enforce it.** A real build
> once had its code merged to the shared checkout before
> `build-verifier`/`build-reviewer`/`build-lead` ever ran, then had those
> checks run retroactively, after the fact, against the now-shared tree
> (2026-08-14 workflow-audit). The fixed step order below (verify → review →
> lead → ship) still runs in full, every time, before anything is committed —
> removing the human gate does not mean skipping straight to a commit.

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

All seven always run, every time — there is no discretion left over which
agents to fold or skip.

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-build/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-build/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

> **How the team actually runs:** `build-triage` through `build-lead`
> (Steps 1–7) run inside one `Workflow` call — `workflows/build.js` — not as
> `Agent` calls you make directly; the script invokes each by its registered
> subagent type and reuses these same agent files unchanged. **Step 8's
> commit/push is not part of the workflow** — a script has no filesystem or
> git access of its own, and this was always your own action (same
> convention as `wrap-up`), not an agent's; you still run it directly, after
> the workflow returns.

## Process

### Step 0 — Get the approved plans and the output location
team-build needs **the technical-plan** (what to build) and **the test-plan**
(what to prove). Both normally live inside a completed intake folder:

- The path argument is required. If it's missing, this isn't a gate to stop
  and ask at — it's a missing required input, same as calling any tool
  without its argument. Report that plainly and stop; do not guess at a
  folder.
- The plans are at `<intake-dir>/intake/.../technical-plan.md` and
  `<intake-dir>/qa/.../test-plan.md` (or directly inside it). Locate both.

**What happens instead of asking, if only the technical-plan exists (no
test-plan):** run `team-qa` on this intake folder first, automatically —
strict red-first TDD needs the test-plan, and this skill's own rule was
always "never build blind," so that's what happens without a stop. Log it to
`decisions.md` as `DECIDED-AUTO`. (There is no smoke-only/skip-QA fast path
anymore — every build gets a real test-plan, generated first if it doesn't
exist yet.)

**Output location:** write under `<intake-dir>/build/<YYYY-MM-DD>-<slug>/`
(reuse the intake slug; create a `supporting/` subfolder). Use today's date.
**Never write build artifacts to a repo root.**

### Step 0.5 — Version bump (only if the project has one)
Check whether this project has a version-bump convention —
`PROJECT-CONTEXT.md` names it if so. If it doesn't, skip this step entirely —
don't invent one.

**What happens instead of asking:** decide per the project's documented
convention (bump at the level the convention names for this change's scope,
or no bump if the convention says this class of change doesn't warrant one),
follow the mechanism `PROJECT-CONTEXT.md` names exactly (script, files it
updates, commit convention), and log the decision to `decisions.md` as
`DECIDED-AUTO` with the rationale.

### Step 1 — Run the build pipeline

Run the entire triage-through-lead sequence as one call:

```
Workflow({
  scriptPath: "~/.claude/skills/team-build/workflows/build.js",
  args: {
    intakeDir: "<intake-dir>",
    technicalPlanPath: "<intake-dir>/intake/.../technical-plan.md",
    testPlanPath: "<intake-dir>/qa/.../test-plan.md",
    buildDir: "<intake-dir>/build/<date>-<slug>"
  }
})
```

(Under a plugin install, `scriptPath` is
`${CLAUDE_PLUGIN_ROOT}/skills/team-build/workflows/build.js` instead — same
"Path note" translation as everywhere else in this file.)

This one call replaces what used to be seven separate steps — triage, plan,
red, implement, verify, review, and lead synthesis. The mechanics described
in the old Steps 1–7 are all still true, just executed by the script now
instead of by you:
- **`build-triage`** confirms both plans, discovers the repo layout,
  provisions a per-effort worktree (+ Docker stack) per repo, gates on a
  clean tree, and records the starting commit(s) — all via its own
  `Write`/`Bash` tools, unchanged. **A dirty worktree is auto-stashed
  (`git stash -u`) by the agent itself and reported `READY`** — the script
  has no shell access to do this itself, so triage's own tools are what
  make this possible; a genuinely **missing/incomplete plan** is the one
  case that still comes back `BLOCKED`, and the script ends the run there —
  report it plainly and stop, same as before.
- **`build-planner`** writes `build-task-list.md`, marking every
  project-specific durable-cure step **MANDATORY**.
- **`build-test-author`** writes the tests and proves each one RED. **If a
  test that should be red is already green**, the script ends the run there
  too — that's a signal the plan is wrong, not something to loop past.
- **Implement → verify → review runs as one bounded loop** (up to 3 cycles):
  `build-implementer` applies the change set, `build-verifier` runs the full
  suites + Definition of Done, and — once verify is GREEN —
  `build-reviewer` does the adversarial diff review. A verify failure *or* a
  real defect the reviewer finds both re-enter the loop at
  `build-implementer`; running out of cycles without converging ends the run
  there, same "report plainly, don't force a 4th attempt" discipline as
  before.
- **`build-lead`** writes `build-report.md`, updates the build run-log, and
  updates this project's defect catalog if this build re-applied a cure or
  exposed a new trap.

The run goes silent in this session until it completes — a background job,
not a live stream — so say so before starting it. It returns an object
(`status`, `cycles`, `worktrees`, `reportPath`, `headline`); use it in Step
8 below. **A `status` of `BLOCKED` means the run ended early** (at triage,
red, verify, or review) — report the reason plainly and stop; do not
proceed to Step 8's ship.

### Step 8 — Ship, then report
**Commit on this effort's own isolated branch (the one `build-triage`
provisioned, never a shared checkout), push it, and open a PR if this
project has that convention — automatically, no ask.** The standing safety
floor still applies without exception: **never force-push, never
`--no-verify`, never push straight to the repo's default branch.**

Append the resulting commit SHA (per repo) to `build-report.md`'s "Shipped
commit" field — `build-lead` can't fill this in during the build pipeline
since the commit hasn't happened yet, but leaving it blank is how
`team-release`'s
`release-lead` ends up re-deriving shipped commits from raw git history
instead of reading them. **Confirm the field was actually updated before
ending the session** — it's easy to commit and move on without circling
back to it.

Then summarize for the user in chat:
- **What was built and shipped** and the **change verdict** (GREEN /
  GREEN-WITH-CAVEATS). (A `BLOCKED` verdict never reaches this step — it
  ended the run earlier, at whichever step found it, per "What happens
  instead of asking" above.)
- **Red→green evidence** — the new tests, observed red-before / green-after.
- **DoD checklist status** + whether any durable cure was applied or deferred.
- **Where the diff lives** (this effort's worktree/branch — not any shared
  checkout, not yet merged into the default branch) and the **one-command
  back-out per repo** (`git -C <worktree-path> reset --hard
  <starting-commit>`).
- **What was pushed** — branch name, commit SHA(s) per repo, PR link if one
  was opened.
- Every `DECIDED-AUTO` entry from this run — "Decided automatically: N items
  — see decisions.md."
- Links to `build-report.md`, `build-task-list.md`, and `decisions.md`.

Teardown of the worktree/Docker stack is still manual, still the user's own
call, run whenever they actually merge — an unmerged (or just-shipped)
branch is still live work.

> **After the release ships:** when this build (and any others) are merged
> and a version is cut, run **`team-release`** to produce client-facing
> release notes bundling everything in the version, fact-checked against the
> actual shipped commits. That is the outward-facing end of the pipeline;
> team-build stays internal.

## Decision logging
Every point that used to ask a human — Step 0's missing test-plan, Step 0.5's
version bump, Step 1's dirty-tree stash — is now auto-decided using this
skill's own already-documented best recommendation for it, and logged so the
team keeps a readable history instead of a silent decision. Two places:
1. **Per build:** `<output-dir>/decisions.md` (from `templates/decision-log.md`)
   — the full readable record: what was decided, "where we're coming from"
   (dated context), and the rationale for the choice made. Write each entry
   directly as `DECIDED-AUTO` — there is no `PENDING`-then-flip step anymore,
   since nothing waits for an answer.
2. **Global:** the build run-log captures the run; if a decision maps to an
   entry in this project's defect catalog (if configured), note the reference
   there.

A genuinely un-auto-decidable state (a missing/incomplete plan, a red test
already green, a non-converging fix loop) isn't logged as a decision at
all — it's the run's terminal outcome, reported plainly in the final chat
output per the relevant step above. There's no decision to log when there
was nothing safe to decide.

**Propagate the flip, don't just log it.** Whenever a decision changes a
project's prior stated status, grep the project for every other doc that
cited the old status — a technical-plan's Risks/rollback section, a sibling
item's own `decisions.md`, the defect catalog if configured, a cached
`status-report.md` — and correct them in the same sitting. If a citing doc
is out of this skill's write scope (product code, another team's memory) or
genuinely unreachable this session, **name it explicitly in the Step 8
report-back** instead of leaving it silently stale — that's what lets a
later `team-status` pass close the loop.

## Conventions
- **Inputs:** a completed intake folder holding `technical-plan.md`; a
  missing `test-plan.md` is generated automatically (Step 0), not asked
  about. The path itself is required — this skill does not guess a folder.
- **Output per build:** `<intake-dir>/build/<date>-<slug>/` containing
  `build-brief.md`, `build-task-list.md`, `build-report.md`, `decisions.md`,
  and `supporting/*.md` (red/green evidence logs).
- **Templates:** `~/.claude/skills/team-build/templates/`.
- **Memory:** the build run-log location comes from `PROJECT-CONTEXT.md` if
  the project names one; otherwise falls back to
  `~/.claude/skills/team-build/memory/build-run-log-INDEX.md` (a cross-project
  log, split by size into `build-run-log/*.md` part files — less useful than a
  project-specific one, but available). A project's own
  recurring-defect catalog, if it has one, is **its own** — read it, update it
  when a build re-takes a shortcut or re-applies a cure, never fork it into
  this skill's global memory.
- **This skill mutates a tree in place, sequentially, one implementer, no
  parallel edits to the same files within a build.** It gates on a clean tree
  per repo, records the starting commit(s), builds **strict red-first**, and
  **ships automatically on green** — commit + push on the effort's own
  branch, no ask, no interactive stop. Teardown is still always manual, the
  user's own call.
- **Every build runs in its own isolated git worktree set** (+ a namespaced
  Docker stack, if the project has one), provisioned by `build-triage`.
  Teardown is manual, run by whoever merges — never automatic, since an
  unmerged branch is still live work.
- **Repo layout is project-specific — discover it, don't assume one.** Check
  `PROJECT-CONTEXT.md` first; a project may be a single repo or contain
  several independent ones.
- **The standing safety floor never bends, in any case:** never force-push,
  never `--no-verify`, never push straight to the repo's default branch.
  Every ship in Step 8 lands on the effort's own isolated branch, full stop.

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

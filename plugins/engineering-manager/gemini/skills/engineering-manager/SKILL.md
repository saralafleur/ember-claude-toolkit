---
name: engineering-manager
argument-hint: "[auto|auto-pilot] [triage <folder>|dispatch <folder>|status|resume <item-slug> <answer>] — see \"Run modes\" for the auto-pilot/auto token."
description: >
  Evaluates a folder's outstanding work (typically team-status's stage-map)
  and gets it moving on whatever track it actually needs. `triage` sorts
  outstanding items into direct-fixable housekeeping, real work that needs
  team-intake first, and things only a human can do — then dispatches the
  first two. `dispatch` decides whether build-ready items (intake+QA already
  done) should build in parallel worktree efforts, sequentially, or as a
  single normal session, then actually dispatches and babysits the runs
  through to merge. Both commands run the same
  decide→gate→dispatch→monitor pattern — read-only analysis, a human
  approval gate, then real delegated work, never silent auto-action. An
  optional `auto`/`auto-pilot` mode token (see "Run modes") auto-decides
  every preference gate and cascades the same mode into every team-build/
  team-intake delegate it dispatches, while leaving quality gates and the
  merge-to-default-branch gate as hard stops in every mode. `status` checks
  on in-flight dispatches without re-deciding anything; `resume` answers a
  BLOCKED item and continues it. Generic — works on any project using the
  delivery-team pipeline conventions (team-intake/team-qa/team-build/
  team-status).
---

<!-- team-of-agents-generated: v1 -->

# Engineering Manager

Answers the question `team-status` raises but doesn't act on: given a
folder's outstanding work, what's the fastest safe way to actually close it
out — and who does it? Not every outstanding item is the same kind of work:
some are a stale sentence in a build-report, some are real work nobody's
scoped into a plan yet, some are already build-ready and just need
splitting across parallel or sequential efforts, and some only a human can
do (production data, repo-admin access, a genuine judgment call). This team
routes each kind to the right track and, once approved, carries it out —
not a fan-out report generator; its job doesn't stop at a recommendation.

Both commands share the same shape: a **pipeline** team (analyst → optional
judge panel → lead decide) followed by an **orchestration** phase the main
session runs directly (dispatch, monitor, merge/record).

## Command routing

Parse the argument for a leading mode token first — `auto`/`auto-pilot` —
before the command word (see "Run modes" below). Strip it if present;
whatever remains routes per the table.

| Argument | Command |
|---|---|
| `triage <folder>` (or no folder — see Step 0) | Sort a status-report's outstanding items into housekeeping / needs-intake / needs-human, then dispatch the first two — `references/triage.md` |
| `dispatch <folder>` (or no folder) | Full decide→gate→dispatch→monitor→merge flow for build-ready items — `references/dispatch.md` |
| `status` | Read-only check on any in-flight dispatch, from either command — `references/status-resume.md` |
| `resume <item-slug> <answer>` | Answer a BLOCKED item and continue it — `references/status-resume.md` |
| *(none)* | Resolve the target, then run whichever of `triage`/`dispatch` actually has candidates — see Step 0 in each reference |

## Run modes

Standard mode (bare `triage`/`dispatch`) is the default described in
`references/triage.md` / `references/dispatch.md`: every 🟧 gate stops and
waits.

| Mode | Token(s) | What changes |
|---|---|---|
| Auto-pilot | `auto-pilot`, alias `auto` | Every gate in the two references is tagged **PREFERENCE**, **QUALITY**, or the **merge gate**. PREFERENCE gates no longer stop — the team decides on its own best recommendation (always the option each gate already states as recommended, e.g. "A) Proceed as recommended"), logs the choice to `<target>/dispatch-decisions.md` or `<target>/triage-decisions.md` (from `templates/decision-log.md`) as `DECIDED-AUTO`, and keeps going. QUALITY gates (nothing to triage/dispatch against, a delegate reporting `BLOCKED:` on a decision it itself couldn't safely default) still stop, in every mode — there's no recommendation to make when the premise is broken or a downstream delegate already determined a human is required. A `FAILED:` delegate gets one auto-retry under auto-pilot (logged `DECIDED-AUTO`); if the retry also fails, that escalates to a hard stop — no unbounded auto-retry loop. **The merge gate (`dispatch` Step 6) is never auto-proceeded, in any mode** — merging into the project's actual default branch is exactly the kind of hard-to-reverse, shared-state action this environment's own standing safety floor exists for (same floor `team-build`'s "Run modes" names: no force-push, no `--no-verify`, no push/merge straight to the default branch without a human looking at it first), so it stays a stop even though the builds that produced the merge candidates ran fully unattended. |
| **Cascade** | — | Auto-pilot doesn't stop at this skill's own gates: every delegate this skill dispatches to run `team-build` (`dispatch`) or `team-intake` (`triage`'s intake phase) is launched with that same skill's own `auto`/`auto-pilot` token, so the delegate's downstream PREFERENCE gates are auto-decided too, all the way through the pipeline. Tell `em-lead` (Step 2 of `dispatch`, Step 4 of `triage`) that this run is in auto-pilot so it bakes the token into the dispatch prompt it authors — see each reference's Step for the exact instruction. |

There is no `direct` mode for this skill — its own roster (`em-analyst` →
optional `em-judge` panel → `em-lead`) is already the minimal shape; there's
nothing left to trim the way `director-of-engineering` trims a larger fixed
roster elsewhere in the suite.

## The team

- **em-analyst** — reads a candidate set — build-ready items for
  `dispatch`, or not-yet-planned request items for `triage`'s intake
  phase — and recommends PARALLEL / SEQUENTIAL / BATCHED-into-one-request /
  SINGLE-SESSION, with a confidence rating that decides whether a judge
  panel is needed. Read-only.
- **em-judge** — one independent vote in a 2-3-judge panel, convened **only**
  when the analyst's confidence is LOW. Read-only.
- **em-lead** — synthesizes the analyst (+ judges, if run) into a plan
  document — `dispatch-plan.md` for `dispatch`, `triage-plan.md` for
  `triage` — with the final grouping, the concrete per-item dispatch spec,
  and (for `dispatch`) the merge order. Writes only that report.

> **Path note (extension install):** if you installed this as a Gemini CLI
> extension, every `~/.gemini/skills/engineering-manager/...` path anywhere
> in this skill's files means "the same-named folder bundled alongside this
> extension" (extensions install to `.gemini/extensions/<name>/`, keeping
> the same `skills/` and `agents/` subfolder layout), not a literal
> home-directory path. `~/.gemini/agents/<name>.md` likewise means "the
> matching file in this extension's own `agents/` folder" — same relative
> layout, different root. This file was written assuming a standalone
> install (`~/.gemini/skills/engineering-manager/` + `~/.gemini/agents/`);
> adjust the root if you installed it as an extension instead.

> **How to invoke each role:** `em-analyst`, `em-judge`, and `em-lead` are
> Gemini CLI subagents. Delegate to one either by explicit mention —
> `@em-analyst <task>` — or by letting automatic delegation trigger it,
> since the main agent matches the task description to the subagent's
> `description` field. Always give the agent the candidate items' paths and
> (for `em-lead`) the analyst/judge findings it needs to synthesize. (If a
> subagent by that name isn't available, fall back to a plain instruction
> and paste the role brief from `~/.gemini/agents/<name>.md` directly into
> the request.) The `general-purpose` background delegates this skill
> dispatches for the actual `triage`/`dispatch` work (Step 4/6 of each
> reference) are a different, Claude-Code-specific mechanic — see the note
> at the top of `references/dispatch.md`, `references/triage.md`, and
> `references/status-resume.md`.

`triage`'s housekeeping bucket doesn't need this team — grouping direct text
corrections by which file they touch is mechanical enough for the
orchestrator to do directly (`references/triage.md`, Step 2). The team
exists for the judgment calls: is it safe to run these at the same time,
and does splitting even pay for itself.

Everything after the human approves a plan — provisioning, dispatching,
monitoring, resuming BLOCKED items, merging — is done by **you, the
orchestrator**, directly (same convention as `wrap-up`: no sub-agent
delegation for actions with real side effects). The three agents above only
ever read and recommend.

## `triage`

Read a folder's `status-report.md`, bucket every outstanding action item:

- **HOUSEKEEPING** — a stale-text/doc correction where the report already
  states the correct fact (its own follow-up type says `DOC CLEANUP` or
  `COSMETIC`). Dispatched directly as `general-purpose` delegates doing a
  targeted edit — no skill invocation, no plan needed.
- **NEEDS-INTAKE** — real outstanding work with no plan yet (`FUTURE
  SCOPING`, `DEPENDS-ON-ITEM`, or an `OPERATIONAL` item that's actually a
  code/config fix rather than an admin action, or a live defect the rescan
  itself found). Routed through `em-analyst`/`em-lead` the same as
  `dispatch`'s build candidates, then dispatched as `general-purpose`
  delegates running `team-intake`.
- **NEEDS-HUMAN** — requires credentials, production access, repo-admin
  rights, or a decision only the user can make. Surfaced plainly, never
  dispatched.

Full procedure in `references/triage.md`. Once an intake delegate produces a
`technical-plan.md`/`test-plan.md`, that item becomes a candidate for
`dispatch` on your next run — `triage` doesn't auto-chain into `dispatch`,
so the pipeline's own re-verify-before-acting discipline still holds between
phases.

## `dispatch`

Gather the build-ready candidate set → `em-analyst` → (`em-judge` panel only
if flagged ambiguous) → `em-lead` writes `dispatch-plan.md` → **human gate** →
dispatch each item as a backgrounded `general-purpose` delegate running
`team-build` → monitor completions, resuming any BLOCKED delegate once
answered → merge DONE items in the decided order → refresh `team-status` →
record the run. Full procedure, including the exact BLOCKED/DONE/FAILED
protocol and the merge discipline, in `references/dispatch.md`.

## `status` / `resume`

Lightweight commands for coming back to check on or unblock in-flight work
without re-running the decision phase. `references/status-resume.md`.

## Why delegates use `general-purpose`

The narrow role agents (`build-triage`, `build-implementer`,
`intake-triage`, `intake-tech-lead`, …) have no `Agent` tool — they can't
spawn further subagents. A delegate that's going to run a **skill** itself
(`team-build` for `dispatch`, `team-intake` for `triage`'s intake phase —
invoking each of that skill's own roles in turn) needs full tool access, so
both commands always use `subagent_type: "general-purpose"` with an
instruction to run the named skill — never one of the specialist role
agents directly, and never a `fork` (a fork inherits this entire session's
history, which the delegate doesn't need and shouldn't pay to load — see
`references/dispatch.md`'s and `references/triage.md`'s dispatch-prompt
specs). This is two levels of nesting — orchestrator → `general-purpose`
delegate → that delegate's own skill-internal agent calls — and it's as deep
as it goes: the specialist agents a delegate spawns are leaf workers with no
`Agent` tool of their own.

Housekeeping delegates are simpler still — they don't invoke a skill at all,
just a direct, fully-specified text correction (old string → new string, the
fact already verified by `team-status`), so there's no nesting to reason
about.

## Why a BLOCKED delegate isn't a dead end

A backgrounded delegate can't pause for live `AskUserQuestion` input the way
this session can. So it doesn't try to: it ends its turn with a `BLOCKED:`
report and stays addressable by its agent ID. Resuming it via `SendMessage`
continues it **with full context** — worktree state (for `dispatch`) or
whatever intake artifacts it already drafted (for `triage`), which step it
was on — not a restart. This only works within the session that spawned it;
`references/status-resume.md` covers the cross-session fallback (a fresh
delegate, informed by the now-answered `decisions.md` entry). Housekeeping
delegates don't use this protocol at all — a stale-text correction has no
decision to block on.

## Adding to the team

New judge lenses (e.g. a security-risk vote alongside the default
independence vote) go in a new `em-judge-<lens>` agent, invoked alongside
the existing `em-judge` calls in the panel step — `em-lead` already treats
judge votes as a list, not a fixed count. Changes to the merge discipline or
the BLOCKED protocol belong in `references/dispatch.md`; changes to the
housekeeping/intake bucketing rules belong in `references/triage.md` — not
scattered across the agent files, since the orchestrator (not the agents)
owns both.

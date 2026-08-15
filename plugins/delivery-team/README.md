# Delivery Team

Six virtual delivery teams for Claude Code, each a `SKILL.md` orchestration
that fans work out to a roster of specialist subagents. Five chain into one
pipeline; the sixth clears the backlog the other five leave behind:

```
team-intake  ->  team-qa  ->  team-build  ->  team-release
   (plan)         (test plan)    (implement)      (client notes)

team-status watches all four, on demand, and re-verifies claims against the
live code instead of trusting a report.

team-decisions sweeps every PENDING/PARKED decisions.md the other five
leave behind, resolves what it safely can, and asks about the rest.
```

| Skill | What it produces | Agents |
|---|---|---|
| `team-intake` | `technical-plan.md` + `pm-plan.md` | triage, product-owner, architect, engineer, qa, project-manager, tech-lead, client-liaison (8) |
| `team-qa` | `qa-assessment.md` + `test-plan.md` | triage, coverage-cartographer, risk-analyst, unit-architect, e2e-architect, strategist, lead (7) |
| `team-build` | a shipped diff (on its own effort branch, in an isolated worktree) + `build-report.md` | triage, planner, test-author, implementer, verifier, reviewer, lead (7) |
| `team-release` | client-facing `release-notes.md` | scribe, lead (2) |
| `team-status` | `status-report.md` + "what to run next" | triage, scanner, lead (3) |
| `team-decisions` | resolved `decisions.md` entries + a docs-only commit | direct, single-agent — no sub-team |

Plus one shared agent used by all five, `director-of-engineering` — invoked
only in `direct` mode (see "Run modes" below) to pick a leaner subset of
whichever skill called it.

All five work generically on any project. If a project has its own
`PROJECT-CONTEXT.md` (repo layout, a recurring-defect catalog, log
locations), the teams read it and use it; if it doesn't, they fall back to
generic behavior and their own bundled memory — nothing here requires
project-specific setup to run.

## Run modes

`team-build` no longer takes mode tokens at all — see "No gates, no modes"
below. Every other skill above accepts two optional leading tokens before its
normal argument, composable in either order (`auto direct <path>` /
`direct auto <path>`) — see each `SKILL.md`'s own "Run modes" section for the
skill-specific gate-by-gate detail:

- **`auto-pilot`** (alias **`auto`**) — removes the PREFERENCE gates (a
  judgment call with a defensible best answer): the team decides for itself,
  logs the choice to that run's `decisions.md` as `DECIDED-AUTO`, and keeps
  going instead of stopping. QUALITY gates (the premise is actually broken —
  a `BLOCKED` verdict, a test that's already green when it should be red, a
  fix loop that never converged) still stop, in every mode — there's no
  recommendation to make when something is contradictory. In `team-release`,
  auto-pilot also proceeds through the final SHIP gate (finalize the release
  notes) rather than stopping to ask — subject to one floor that holds in
  every mode regardless: no force-push, no `--no-verify`, no push straight to
  a repo's default branch.
- **`direct`** — runs a tailored, lighter-weight pass instead of the fixed
  roster: a new shared agent, `director-of-engineering`, looks at the actual
  request/change/plan and this skill's own roster, and decides which of that
  skill's agents are actually warranted for this specific piece of work (it
  never reaches outside the calling skill's own roster, and a defect-catalog
  match always forces the full roster back on). `team-release` and
  `team-status` already run a minimal roster, so `direct` is accepted for
  consistency but doesn't change their behavior.

**`team-build`** has no modes and no gates at all — every decision that used
to pause for a human is now auto-decided and logged, and a green build
commits and pushes automatically to its own effort branch (never straight to
the repo's default branch). Its `<path>` argument is required; it no longer
asks if you omit it. `team-decisions` is also a direct, single-agent skill —
no sub-team, no modes — it resolves what it safely can on its own and only
ever pauses to ask about a decision that's genuinely a human preference call.

## Install

### Option A — as a plugin (recommended)

From wherever this folder ends up (a git repo, a shared drive, a zip you
unpacked):

```bash
# one-time, from your own machine:
/plugin marketplace add <path-or-git-url-to-this-folder>
/plugin install delivery-team@<marketplace-name>
/reload-plugins
```

Or, for quick local testing without installing:

```bash
claude --plugin-dir /path/to/delivery-team-plugin
```

Skills load as `/delivery-team:team-intake`, `/delivery-team:team-qa`, etc.
(plugin skills are always namespaced to avoid colliding with anyone else's
skill of the same name). Agents appear under **Custom Agents** in `/context`.

### Option B — plain files (no plugin system involved)

Copy the two folders directly into your own `~/.claude/`:

```bash
cp -R skills/* ~/.claude/skills/
cp agents/*.md ~/.claude/agents/
```

(Or into a single project's `.claude/skills/` and `.claude/agents/` instead,
if you only want this available in one repo.) Skills load as their plain
names — `/team-intake`, `/team-qa`, etc. No restart needed; Claude Code picks
up new files on the next session.

**If you already have differently-named skills/agents with the same names**,
either method will collide — rename before copying.

## What's inside each skill folder

- `SKILL.md` — the orchestration logic and the agent roster.
- `templates/` — blank forms (technical-plan, test-plan, build-report, etc.)
  the agents fill in.
- `memory/` — a cross-project fallback log, used only when a project doesn't
  name its own log location in `PROJECT-CONTEXT.md`. **Shipped empty** (header
  + table header, no rows) — it'll fill up with your own history as you use
  it.

Each `SKILL.md` includes a short "path note" flagging the one thing that
changes between install methods: a few paths are written as
`~/.claude/skills/team-x/...`, which are exactly correct under Option B, and
mean "the same folder bundled alongside this file" under Option A.

## Notes

- `team-build` commits and pushes a green build automatically, to its own
  effort branch only — never to the repo's default branch, and never a
  force-push or `--no-verify`. `team-release` stops at a drafted,
  fact-checked `release-notes.md` (or, under auto-pilot, reports it as ready
  to send) — it never transmits anything itself. `team-decisions` commits its
  own resolved `decisions.md` files locally (docs only) at the end of a
  sweep. None of the six merge into a repo's default branch or send anything
  externally on your behalf — that's `/wrap-up`'s job, a deliberate, separate
  step every time.

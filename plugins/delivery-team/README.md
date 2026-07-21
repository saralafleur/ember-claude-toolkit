# Delivery Team

Five virtual delivery teams for Claude Code, each a `SKILL.md` orchestration
that fans work out to a roster of specialist subagents. They chain into one
pipeline:

```
team-intake  ->  team-qa  ->  team-build  ->  team-release
   (plan)         (test plan)    (implement)      (client notes)

team-status watches all four, on demand, and re-verifies claims against the
live code instead of trusting a report.
```

| Skill | What it produces | Agents |
|---|---|---|
| `team-intake` | `technical-plan.md` + `pm-plan.md` | triage, product-owner, architect, engineer, qa, project-manager, tech-lead, client-liaison (8) |
| `team-qa` | `qa-assessment.md` + `test-plan.md` | triage, coverage-cartographer, risk-analyst, unit-architect, e2e-architect, strategist, lead (7) |
| `team-build` | a green diff (in an isolated worktree) + `build-report.md` | triage, planner, test-author, implementer, verifier, reviewer, lead (7) |
| `team-release` | client-facing `release-notes.md` | scribe, lead (2) |
| `team-status` | `status-report.md` + "what to run next" | triage, scanner, lead (3) |

All five work generically on any project. If a project has its own
`PROJECT-CONTEXT.md` (repo layout, a recurring-defect catalog, log
locations), the teams read it and use it; if it doesn't, they fall back to
generic behavior and their own bundled memory — nothing here requires
project-specific setup to run.

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

- `team-build`'s `SKILL.md` mentions an optional integration with a
  time-cost-ledger dashboard — that's not part of this package; it's a no-op
  unless you have your own such skill installed and configured. Safe to
  ignore or delete that step if you don't.
- None of these teams commit, push, or send anything on your behalf.
  `team-build` stops at a green diff in an isolated worktree; `team-release`
  stops at a drafted, fact-checked `release-notes.md`. Every "send/merge/ship"
  action is left to you.

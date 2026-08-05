# Current standard — devops skill checklist

Used by `/create-skill-devops update`. Compare the project's
`<project>/.claude/skills/devops/` against these invariants (and against
the live templates in `templates/`). Mark each row **ok**, **drift**,
**missing**, or **n/a** (project does not use that feature).

Do **not** treat project-specific content as drift: solution names, ports,
deploy backends, smoke-test commands, environment-setup install steps, and
extra commands beyond the standard set are intentional. Only flag
structural / discipline gaps vs this meta-skill's current standard.

When a template has evolved, prefer the template's current wording for
shared sections (Human gates, status procedure shape, lifecycle remove
gates) over older generated prose — but keep project-filled `{{…}}` values.

---

## A. Layout & discoverability

| # | Invariant | How to check |
|---|---|---|
| A1 | Skill lives at `.claude/skills/devops/` with `SKILL.md` | Path exists |
| A2 | Frontmatter `name: devops` | YAML |
| A3 | `argument-hint` lists every command word and alias, pipe-separated in `[…]`, and includes `status` | Compare routing table ↔ hint |
| A4 | Frontmatter `description` names the project and summarizes every current command | Skim |
| A5 | Bare `/devops` (no arg) lists commands then runs `status` | Routing table has `*(none)*` → status |
| A6 | Unknown args list commands and suggest closest match | Mentioned in SKILL.md |

## B. Discipline & human gates

| # | Invariant | How to check |
|---|---|---|
| B1 | Every command follows audit → plan → install/execute → verify | SKILL.md discipline block + each `references/*.md` |
| B2 | Never mutates before showing audit + plan | Explicit in SKILL.md |
| B3 | Idempotent re-runs ("already set up" / "already up" / etc.) | Explicit in SKILL.md |
| B4 | Interactive steps handed as `!`-prefixed commands, never scripted around | SKILL.md / procedure docs |
| B5 | **Human gates** section present with orange banner `🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧`, callout shape, lettered multi-way options, wait-before-execute | Match `templates/SKILL.template.md` |
| B6 | Large downloads, `remove`, purge-data, and cloud-mutating deploys gate before execute | Each relevant procedure marks the gate |

## C. status command (required)

| # | Invariant | How to check |
|---|---|---|
| C1 | `status` in routing table + `argument-hint` + Commands section | SKILL.md |
| C2 | `references/status.md` exists | Path |
| C3 | Discovers `scripts/*-check.sh` automatically | status.md procedure |
| C4 | Lifecycle commands that share one audit are reported under one section, not repeated | status.md exception note |
| C5 | Never installs/fixes/changes anything | status.md |
| C6 | Report format: verdicts table first (`ready` / `partial` / `not set up`), detail after | Align with `templates/status.template.md` |
| C7 | Reports git worktree & branch status — one row per `git worktree list` entry (path, branch, sync vs `origin`, working-tree cleanliness, merged-into-default), always shown (not just "when relevant"), skipped only if the project isn't a git repo | status.md procedure + `templates/status.template.md` |

## D. Per-command structure

| # | Invariant | How to check |
|---|---|---|
| D1 | Every routed command (except shared lifecycle verbs) has `references/<command>.md` or is covered by a shared reference (e.g. `lifecycle.md`) | Diff routing table ↔ `references/` |
| D2 | Every command that needs an audit has `scripts/<name>-check.sh` (lifecycle set shares one) | Diff ↔ `scripts/` |
| D3 | Check scripts are invoked relative to the skill base dir, never absolute machine paths | Grep references + SKILL.md |
| D4 | "Adding new commands" section lists: routing row, SKILL section, reference doc, argument-hint, audit script | SKILL.md |

## E. Audit script shape

| # | Invariant | How to check |
|---|---|---|
| E1 | Scripts are `#!/usr/bin/env bash`, start with `shopt -s nullglob`, always `exit 0` | Read each `scripts/*-check.sh` |
| E2 | Output is `KEY | STATUS | DETAIL` rows via a `line` helper | Same |
| E3 | Status vocabulary matches the template (`ok` / `info` / `MISSING` / `WRONG` / `NEEDED` / `LOW` / `absent`) | Same + `templates/check.template.sh` |
| E4 | Read-only — no installs, no mutations | Skim for `docker compose up`, `rm`, package managers, etc. |

## F. Lifecycle set (only if `build`/`up`/`down`/`remove` exist)

| # | Invariant | How to check |
|---|---|---|
| F1 | Shared reference `references/lifecycle.md` covers the verbs that exist | Path + headings |
| F2 | Shared audit script (e.g. `compose-check.sh` / `native-check.sh`) is Phase 1 for all lifecycle verbs | lifecycle.md + scripts |
| F3 | Solutions table names real units; `all` defined | lifecycle.md |
| F4 | `up` verifies with a real traffic/log/health check, not just "container/PID exists" | lifecycle.md § up |
| F5 | `down` keeps the build artifact; uses stop/kill, not wipe | lifecycle.md § down |
| F6 | `remove` is destructive, shows plan table (artifact / re-acquire cost / data outside artifact), human gate before execute | Match `templates/lifecycle.template.md` |
| F7 | If any solution has bind-mounted / on-disk data outside the build artifact: ask every run (or `--purge-data`), separate gate from the remove confirm | lifecycle.md + compose/dev script |
| F8 | Docker backend: image presence uses `docker compose config --images` + `docker image inspect`, **not** `docker compose images` | Audit script |
| F9 | Docker `remove` scopes to the compose project only — no other projects, no remote registries | lifecycle.md |
| F10 | Native backend: wrap existing `scripts/dev.sh` (or equiv.) rather than duplicating start/stop; `remove` may be the only new verb | lifecycle.md |

## G. Template drift (shared prose)

For each of these templates, if the project's corresponding file is missing
shared sections that the **current** template requires, flag **drift** and
propose a surgical patch (do not wholesale replace project-specific fill-ins):

| Template | Project file |
|---|---|
| `templates/SKILL.template.md` → Human gates + discipline + status + adding-commands | `SKILL.md` |
| `templates/status.template.md` | `references/status.md` |
| `templates/lifecycle.template.md` (if lifecycle present) | `references/lifecycle.md` |
| `templates/check.template.sh` / `lifecycle-check.template.sh` | matching `scripts/*-check.sh` |

---

## Report format for `/create-skill-devops update`

```
## /create-skill-devops update — audit

| ID | Verdict | Finding |
|---|---|---|
| B5 | ok | Human gates section present |
| F8 | drift | compose-check still uses `docker compose images` |
| C2 | missing | no references/status.md |

## Plan
| Change | Why | Touches |
|---|---|---|
| … | … | … |
```

Then stop on a human gate before applying any file writes.

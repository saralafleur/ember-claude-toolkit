---
name: create-skill-devops
argument-hint: "[update | <command-name e.g. iphone-setup, docker-setup>]"
description: >
  Scaffold or update a project-scoped /devops skill in the current project —
  a command-based toolbox for setting up and verifying that project's build
  environments. Use when the user says "/create-skill-devops", "give this project
  a devops skill", "/create-skill-devops update", or wants to add
  environment-setup commands (e.g. iphone-setup, docker-setup, node-setup)
  to a project. Generic: interviews for what the project needs, then
  generates .claude/skills/devops/ from the templates, following the
  audit → plan → install → verify discipline. `update` audits an existing
  project devops skill against this meta-skill's current standard and
  proposes (then, after a gate, applies) structural fixes.
---

# create-skill-devops

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Creates or updates a **project** skill at
`<project>/.claude/skills/devops/` that gives the project a `/devops`
command toolbox for build-environment setup. This meta-skill encodes the
intent and discipline; the templates make it concrete.

## Meta-skill command routing

Parse the argument after `/create-skill-devops`:

| Argument | Action |
|---|---|
| `update` | Audit the project's existing `.claude/skills/devops/` against the current standard — follow **Update an existing devops skill** below |
| `<command-name>` (e.g. `iphone-setup`) | Scaffold / add-command mode — follow **Procedure** below |
| *(none)* | Same as scaffold / add-command mode (interview what the project needs) |

Unknown argument that isn't a plausible command name → list the table above
and suggest the closest match (`update` vs a kebab-case command name).

## The intent

Every project has environment prerequisites (SDKs, toolchains, runtimes,
services) that are easy to forget between machines and months. A project
devops skill makes them:

- **Discoverable** — `/devops` lists commands; the `argument-hint` shows the
  typeable options right in the slash-command autocomplete menu.
- **Reproducible** — the setup procedure lives in the repo, travels with git,
  and works on a fresh machine.
- **Safe** — nothing installs before an audit and a plan are shown; every
  step is idempotent; interactive steps (sudo, account logins) are handed to
  the user as `!`-prefixed commands, never scripted around.
- **Provable** — setup ends with a real verification (a build, a boot, a
  version check chain), not an assumption.
- **Observable** — a built-in `status` command reports the current state of
  everything the skill manages, any time, without changing anything.

## The discipline every generated command follows

1. **Audit first** — a read-only check script prints `KEY | STATUS | DETAIL`
   rows and always exits 0. Running it changes nothing, any time.
2. **Plan** — list only what the audit flagged, in dependency order, with
   download sizes, disk needs, and which steps are interactive. Get
   confirmation before large downloads.
3. **Install** — run non-interactive steps directly (long ones in the
   background). Interactive steps (sudo password, Apple ID, cloud logins) are
   given to the user as `! <command>` to run in-session. Idempotent: re-running
   on a healthy environment reports "already set up" and changes nothing.
4. **Verify** — re-run the audit, then prove the environment end-to-end with
   the most real check available (build the actual project if one exists).
   Report plainly what was proven and what wasn't.

## Human gates (same pattern as delivery-team)

**Every human decision** — in this meta-skill (interview / scaffold choices)
and in every generated project `/devops` skill — uses the delivery-team
visible gate. Do not bury a choice in a narrative paragraph.

Mark the stop point in the skill/procedure with the literal banner line
`🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧`, then present the question as its own
standalone callout in the **actual chat reply**:

> 🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
>
> **Human decision needed:** <the question>

Rules:

- Never fold a gate's question into a summary where it reads as background
  rather than a stop-and-wait point.
- If more than one gate applies in the same report-back, each gets its own
  banner + callout — do not merge them into a single generic "want me to
  proceed?".
- When a gate offers a genuine multi-way choice in plain chat text (not via
  `AskUserQuestion`), **letter the options** — `**A)**`, `**B)**`, `**C)**`,
  etc. — so the user can answer with a single letter. A plain yes/no "proceed?"
  does not need lettering.
- **Wait for the answer before continuing.** Audit + plan may run; execute /
  install / scaffold / delete must not.

**Where gates are required (non-exhaustive — any other decision uses the
same template):**

| Context | Gate before… |
|---|---|
| This meta-skill, interview | Asking any clarifying / blocking question |
| This meta-skill, scaffold | Writing or overwriting skill files when choices were ambiguous |
| Generated `/devops` setup commands | Large downloads / non-trivial installs |
| Generated `/devops remove` | Deleting build artifacts |
| Generated `/devops remove` + host data | Optionally purging bind-mounted / on-disk data (`--purge-data` skips the *ask*, not the confirm) |
| Generated deploy / other destructive or cloud-mutating commands | Executing the change |

This convention **must be copied into every generated** project
`.claude/skills/devops/SKILL.md` (see `templates/SKILL.template.md`) and
into procedure docs wherever a decision sits (see lifecycle / reference
templates).

## The optional lifecycle command set (build / up / down / remove)

Projects with multiple runnable units often want four standard actions per
unit rather than one bespoke command per service. This is backend-agnostic:
the unit can be a **Docker Compose service** (image + container) just as
easily as a **native background process** (a built binary/venv + a running
PID, managed by something like `scripts/dev.sh start|stop|status` with
PID-file bookkeeping instead of a container runtime) — same four verbs,
same audit/plan/execute/verify shape, different underlying commands. Offer
this set whenever the project has runnable units managed via Docker
Compose or a native lifecycle script — including a **single-service**
Compose stack (still give it `up` / `down` / `remove`; `build` optional
if `up --build` covers it). Especially offer the full set when there are
2+ independently named solutions (e.g. a `docker-compose.yml` with 2+
services, or 2+ native processes started/stopped via PID files):

- **`build <solution|all>`** — produce the build artifact (image, or a
  compiled binary / venv), start nothing.
- **`up <solution|all>`** — build if needed, start, then prove it's actually
  serving (curl/log/PID check), not just that a container or process
  technically exists.
- **`down <solution|all>`** — stop the running unit (container, or kill the
  PID), keep the build artifact. Cheaply reversible — `up` again should be
  fast.
- **`remove <solution|all>`** — wipe the solution's **local build
  artifacts** so nothing from that solution remains on the machine from a
  prior `build`/`up`. **Destructive.** Always show what will be deleted
  and its re-acquire cost (fast local rebuild vs. a real re-download) and
  get explicit confirmation via a human gate
  (`🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧`) before running — same rule as any
  hard-to-reverse action.
  - **Docker Compose backend (intent):** remove every local Docker item
    this solution created — running/stopped containers, the compose
    project network(s), and images built for the solution (typically
    `docker compose down --rmi local`). Scope is the compose project /
    solution only — never other projects' containers/images, and never
    remote registry contents (ECR/Docker Hub) unless a separate deploy
    command explicitly owns that. Named/anonymous volumes owned by the
    compose project are in scope when the plan says so (`-v`); bind-mounted
    host data is **not** (see data rule below).
  - **Native backend:** delete the build artifact (venv, downloaded
    binary, build output dir) that `build` created.
  - **If any solution persists real data outside the build artifact** (a
    Docker bind-mounted data volume, or — for a native process — a data
    directory / DB file on disk that a plain `down`+`remove` wouldn't
    touch), `remove` must **ask explicitly, every run**, whether to also
    delete that data, and wait for a yes/no before touching it — never
    delete it silently, and never assume removing the build artifact
    reset it (that data survives a plain `remove` and comes back
    untouched on the next `up`/`build`). Offer a `--purge-data`-style
    flag to skip the ask and go straight to "yes" for scripting/directness,
    but the flag is an opt-in shortcut to the same confirmed action, not a
    way to avoid the plan/confirm step.

A **"solution"** is whatever unit the project defines as independently
buildable/runnable — one row per Compose service, or one row per
native process the dev script manages — though units that are always
operated together (e.g. a tunnel pair bound by `depends_on`, or a bridge
process + app process always started/stopped as a pair) can be grouped
into one named solution.

These four commands share state, so they share ONE audit script
(`scripts/<name>-check.sh`, e.g. `compose-check.sh` for a Docker backend or
`native-check.sh` for a PID-file backend) rather than one each — it reports
build+running status per solution and is Phase 1 for all four. `status`'s
discovery still globs `scripts/*-check.sh`; when several routing-table
commands point at the same script, group them under one section in the
status report instead of repeating the same table four times.

Scaffold from `templates/lifecycle.template.md` (one reference doc covering
all four actions) and `templates/lifecycle-check.template.sh` (the shared
audit — has commented pattern blocks for both a Docker Compose backend and
a native PID-file backend; use whichever matches the project, or both if it
has solutions of both kinds). Still follows audit → plan → execute →
verify, just lighter than environment setup: audit = current build/run
state, plan = what will happen, execute = the actual compose command or
`dev.sh`-style invocation, verify = re-audit plus a real traffic/log check
for `up`.

Every project-scoped check script resolves `PROJECT_ROOT` with a
worktree-aware block (baked into `templates/lifecycle-check.template.sh` —
copy it verbatim into any hand-written check script too, not just the
generated one). A naive `PROJECT_ROOT="$(cd "$(dirname "$0")/../..." && pwd)"`
always resolves to wherever the skill file physically lives on disk — the
project's main checkout — even when `/devops` is invoked with `$PWD` inside
a different worktree of the *same* repo (e.g. an isolated team-build effort
worktree). That silently runs every command against the wrong checkout.
The fix: fall back to the naive resolution, but prefer `$PWD`'s own
worktree when `git -C "$PWD" rev-parse --git-common-dir` matches the skill
checkout's — same repo, different worktree — so commands and state stay
scoped to the worktree actually being worked in.

If the project already has its own lifecycle script (a `scripts/dev.sh` or
equivalent that starts/stops native processes), don't duplicate its logic —
the `/devops` commands should thinly wrap it (call `scripts/dev.sh build`,
`up`, `down`, etc.) and add only what it's missing, most often `remove`
(deleting build artifacts is rarely a verb an app's own dev script needs,
so this is usually genuinely new, implemented directly in the reference doc
as `rm -rf`/`rm -f` steps against the same paths `build` created).

## The standard `status` command

Every generated devops skill includes a `status` command, created at scaffold
time alongside the first real command. It is what makes the toolbox
observable, and it is generic by construction:

- **Discovers** every audit script in the skill's `scripts/` directory
  (`scripts/*-check.sh` → one entry per command), so commands added later are
  reported automatically with zero changes to `status`.
- **Runs** each audit (all read-only, all exit 0) and reports per command: a
  verdict — **ready** (all build-relevant rows `ok`), **partial**, or **not
  set up** — the non-`ok` rows, and the exact `/devops <command>` to fix it.
- **Reports git worktree & branch status** — always, not just "when
  relevant": one row per `git worktree list` entry (path, current branch,
  sync state vs `origin`, working-tree cleanliness, and whether the branch
  is merged into the project's default branch). Uses the same table shape
  as the `wrap-up` skill's own orientation table
  (`~/.claude/skills/wrap-up/templates/audit-report.md`) so the two read
  consistently side by side. Still shows one row even when the project only
  has its single main checkout — that's real state worth seeing, not
  something to skip. Skip this section silently if the project isn't a git
  repo at all.
- **Adds live extras** where cheap and read-only (running services, booted
  simulators/containers, in-flight background downloads).
- **Never installs, fixes, or changes anything.**
- Bare `/devops` routes to `status`, and `status` appears in the
  `argument-hint`.

Scaffold it from `templates/status.template.md`.

## Update an existing devops skill

Use when the user runs `/create-skill-devops update` (or asks to bring a
project's devops skill up to the current standard). This does **not**
scaffold a new skill and does **not** invent new project commands — it
detects structural / discipline drift against this meta-skill and proposes
surgical patches.

### Phase 1 — Audit (read-only)

1. Resolve the project root (cwd / git root). If
   `<project>/.claude/skills/devops/SKILL.md` is missing, report that there
   is nothing to update and offer to run scaffold mode instead. Stop.
2. Read this meta-skill's live templates under `templates/` and the
   checklist at `references/standard-checklist.md`.
3. Walk the checklist against the project's devops skill. For every row,
   record a verdict: **ok**, **drift**, **missing**, or **n/a**.
4. Also spot-check that shared prose still matches the *intent* of the
   current templates (especially Human gates, status discovery, lifecycle
   `remove` / purge-data gates, and Docker image-presence checks). Project-
   specific fill-ins (solution names, ports, deploy steps, install recipes)
   are **not** drift.
5. Print the audit in the checklist's report format (ID / Verdict /
   Finding table). If every applicable row is **ok** or **n/a**, report
   "already up to date" and stop.

### Phase 2 — Plan

From **drift** / **missing** rows only, list concrete file changes in
dependency order:

| Change | Why (checklist ID) | Touches |
|---|---|---|
| e.g. Add Human gates section | B5 | `.claude/skills/devops/SKILL.md` |

Rules for the plan:

- Prefer surgical edits over rewriting whole files.
- Never delete or rewrite a project-specific command (`deploy`,
  `iphone-setup`, etc.) just because it isn't in the generic templates.
- If the lifecycle set is present but incomplete (e.g. `up`/`down` without
  `remove`), propose adding the missing verbs from
  `templates/lifecycle.template.md` — that is in-scope for `update`.
- If `status` or its reference/audit discovery is missing, propose adding
  it from `templates/status.template.md`.
- Call out anything ambiguous (e.g. "is this bind mount project data that
  needs a purge-data gate?") as its own human gate, not a silent assumption.

### Phase 3 — Confirm, then apply

Stop before writing any files:

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧

> 🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
>
> **Human decision needed:** Apply the update plan above to
> `.claude/skills/devops/`?
>
> **A)** yes — apply all listed changes
> **B)** yes, but only these IDs: …
> **C)** no — leave the skill as-is

Only after the user answers, apply the approved edits. Idempotent: a second
`update` on a patched skill should audit clean.

### Phase 4 — Verify

Re-run Phase 1 against the same checklist. Report the new table. Every
previously approved drift/missing row should now be **ok** (or an explicit
deferred item the user chose to skip under **B)**). Remind them:
`/reload-skills` if the agent needs to pick up SKILL.md changes in-session.

**Maintaining the checklist:** whenever this meta-skill's templates or
discipline rules change, update `references/standard-checklist.md` in the
same edit so `update` keeps auditing against the real current standard.

---

## Procedure

### 1. Check for an existing skill

If `<project>/.claude/skills/devops/` already exists **and** the argument
is a new command name, switch to **add-command mode**: add the new command
to the existing skill (routing-table row, section in SKILL.md,
`references/<command>.md`, optional `scripts/<command>-check.sh`, and
update the `argument-hint`). Never overwrite existing commands.

If the argument is `update`, do **not** use this section — use **Update an
existing devops skill** above.

### 2. Interview (only what's not obvious)

Determine, from the argument, the project contents, and if needed 1-2 short
questions. **Any question that needs the user's choice is a human gate** — use
the `🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧` callout (see Human gates above),
letter multi-way options, and wait. Do not scaffold on an unanswered
ambiguity.

Topics to resolve (gate each one that isn't already obvious from the repo):

- What environment(s) does this project need? (e.g. iOS/Xcode, Docker,
  Node/pnpm, Python/uv, a database)
- What is the command name and its aliases? (kebab-case, e.g. `iphone-setup`
  with aliases `ios`, `iphone`)
- What does "verified working" mean for this project? (the smoke test)
- Does the project have runnable units — Docker Compose service(s) and/or
  native background processes managed by a dev script (PID files, `nohup`,
  etc.)? If so, offer the `build`/`up`/`down`/`remove` lifecycle set (see
  above), including for a single-service Compose stack. Name the actual
  solutions and confirm the grouping (e.g. does a bridge process + app
  process always started together count as one solution or two) before
  scaffolding. For Docker backends, confirm that `remove` means wiping
  local compose artifacts for that solution (containers, project
  networks, locally-built images) and does not touch remote registries.
  If a native dev script already exists, plan to wrap it rather than
  reimplement its start/stop logic.
- If offering the lifecycle set: does any solution persist real data outside
  its build artifact — a Docker bind-mounted data volume (check the compose
  file's `volumes:` for a host-path source, `./something:/container/path`,
  not a bare named volume), or, for a native process, a data directory/DB
  file on disk the build artifact doesn't include? If yes, record the
  path(s) per solution — `remove`'s template needs them to ask about
  deleting that data, every run.

### 3. Scaffold from templates

Copy and fill the templates in this skill's `templates/` directory:

| Template | Becomes | Fill in |
|---|---|---|
| `SKILL.template.md` | `.claude/skills/devops/SKILL.md` | project name, command rows, argument-hint |
| `reference.template.md` | `.claude/skills/devops/references/<command>.md` | audit keys, plan table, install steps, smoke test |
| `check.template.sh` | `.claude/skills/devops/scripts/<command>-check.sh` | one check block per prerequisite |
| `status.template.md` | `.claude/skills/devops/references/status.md` | usually verbatim — it is fully generic |
| `lifecycle.template.md` | `.claude/skills/devops/references/lifecycle.md` (one file covering all four `build`/`up`/`down`/`remove` actions) | naming the project's actual solutions/services and backend (Docker Compose, native PID-file processes, or mixed) |
| `lifecycle-check.template.sh` | `.claude/skills/devops/scripts/<name>-check.sh` (e.g. `compose-check.sh` or `native-check.sh`) | one built+running check block per solution, using whichever commented pattern (Docker or native) matches — only when the project has 2+ runnable units |

Rules that must survive templating:

- `argument-hint` lists every command word and alias, pipe-separated in
  square brackets — and is updated every time a command is added.
- Scripts are referenced relative to the skill's base directory (announced at
  invocation), never by absolute path — project skills must survive cloning.
- The check script starts with `shopt -s nullglob` (bash) and always exits 0.
- Research real download sizes / disk requirements for the plan table —
  don't invent numbers; mark unknown ones "verify at install time".
- The **Human gates** convention (orange banner + lettered multi-way
  options) is copied into the generated `SKILL.md` and into every
  procedure that needs a decision (`remove`, purge-data, large downloads,
  deploy confirms, etc.).

### 4. Test and hand off

- Run the generated check script; fix any script errors now.
- Show the user the audit output and the generated file tree.
- Remind them: `/reload-skills` to pick it up, and if the project isn't a git
  repo yet, the skill won't travel until it is.

## Reference implementation

If another project already has a devops skill generated from this pattern,
consult it as a working reference when a template leaves a question open.

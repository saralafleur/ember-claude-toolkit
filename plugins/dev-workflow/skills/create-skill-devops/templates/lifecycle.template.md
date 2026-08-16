# build / up / down / remove / restart — lifecycle commands for {{PROJECT}}'s solutions

This doc covers every lifecycle verb in one file — the default shape. A
project may instead split each verb into its own `references/<verb>.md`
(e.g. `build.md`/`up.md`/`down.md`/`remove.md`/`restart.md`) if that
already matches an existing convention there; both shapes are equally
valid and `update` mode must recognize either
(`references/standard-checklist.md` row F1). Don't invent a third shape
(e.g. per-solution-named files) — pick one of these two.

Goal: manage each of {{PROJECT}}'s runnable "solutions" — {{list, e.g. the
docker-compose services, or the native processes a dev script manages}} —
without hand-typing the underlying commands, and without ever deleting
something without a plan and a yes first.

Backend for this project: {{Docker Compose | native processes via
scripts/dev.sh (or equivalent) | mixed}}. If a native dev script already
exists, `scripts/{{lifecycle-check-name}}.sh`'s action functions thinly
wrap it rather than reimplementing its start/stop logic — `remove` is
usually the one genuinely new verb, since deleting build artifacts (a
venv, a downloaded binary) is rarely something an app's own dev script
needs. If that dev script exposes verbs beyond build/up/down/remove (e.g.
its own `restart`, `logs`), wrap those too rather than leaving them
unreachable through `/devops`.

## Solutions this covers

| Solution | Underlying unit(s) | Notes |
|---|---|---|
| `{{solution}}` | `{{service name(s), or the build artifact + PID file pair}}` | {{what it is, how it's built/started}} |
| `all` (default) | {{core services/processes}} | {{what "all" means here — usually the everyday stack, excluding optional profiles unless named}} |

## The shared script

Every verb below runs through one script,
`scripts/{{lifecycle-check-name}}.sh` — bare invocation is the read-only
audit (Phase 1 for all five actions); with an action argument it also
executes that action and re-runs the audit so you see the result. The
mechanical part of every verb (which command to run, the retry/health-check
loop, re-checking state afterward) lives in the script, not in this
doc — this doc states the discipline (what to say to the user before/after)
and the two things that stay genuinely agent-mediated: diagnosing an
`up`/`restart` that never comes healthy, and the `remove` human gate.

```bash
bash <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh
```

Prints, per solution: whether its build artifact exists — image built/pulled,
or binary/venv present (`ok`/`absent`) — and whether it's currently running
— container, or PID alive (`info`). Read-only, exits 0 always.

## build \<solution|all\>

**Plan:** state which build artifact(s) will be (re)built and from what —
this is non-destructive; a running instance from a stale artifact is
untouched until `up` runs again.

**Execute:**
```bash
bash <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh build <solution>
```

**Verify:** the script already re-ran the audit — relay its result. The
solution's build row should read `ok`. Building does not start anything;
`up` does that. A non-zero exit means the build itself failed (compiler /
Dockerfile error) — the script's own output is the error, relay it and
explain in plain language; there's no separate diagnosis step to run.

## up \<solution|all\>

**Plan:** state what will start, on what port(s)/address, and whether a
build is needed first (the script builds automatically if the audit showed
the build artifact `absent` — no separate `build` call needed first).

**Execute:**
```bash
bash <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh up <solution>
```

The script starts the solution, then polls the real health check (not just
"container/PID exists") until it's actually serving or a timeout is hit,
then re-runs the audit.

**Verify:** if the script exits 0, relay the re-run audit — running row is
set, and the script's own poll already proved it's serving. If it exits
non-zero, it already printed the tail of the relevant log to explain
why — **read that log and explain the failure in plain language; don't
guess or re-run blind.** This diagnosis is the one place in `up` that
genuinely needs judgment; everything before it is the script's job.

## down \<solution|all\>

**Plan:** state exactly which running unit(s) stop — container(s), or PID(s)
via the dev script. Cheaply reversible (`up` restarts from the same build
artifact) — show the plan, no confirmation gate needed beyond that.

**Execute:**
```bash
bash <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh down <solution>
```

**Verify:** the script already re-ran the audit — running row now reads
"not running"; build-artifact row is unchanged.

## restart \<solution|all\>

Equivalent to `down` immediately followed by `up` — zero judgment beyond
what those two already have. Offer this verb whenever `up`/`down` exist;
don't skip it just because a project's own dev script didn't have it
first (wrap it if the dev script has its own `restart`, otherwise the
script's `do_restart` composes `do_down`/`do_up` directly).

**Plan:** same as `down` followed by `up` — state what stops and what
restarts, no confirmation gate needed (same reversibility as `down`).

**Execute:**
```bash
bash <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh restart <solution>
```

**Verify:** identical to `up` — if it exits 0, relay the re-run audit and
the health-check proof; if non-zero, read and explain the log tail the
script already dumped. Do not re-implement this as a separate `down` call
followed by a separate `up` call by hand — the script's `restart` action
already does that and shares `up`'s health-wait/timeout logic.

## remove \<solution|all\>

**DESTRUCTIVE.** Wipes the solution's **local build artifacts** so a prior
`build`/`up` leaves nothing behind on this machine.

- **Docker Compose:** remove containers (running or stopped), the compose
  project network(s), and images built for this solution — do **not**
  delete other compose projects' resources, and do **not** delete remote
  registry images (ECR / Docker Hub) from this command.
- **Native:** delete the venv / downloaded binary / build output that
  `build` created.

Not cheaply reversible for anything pulled/downloaded rather than built
locally.

**If any solution persists real data outside its build artifact** — a
Docker bind-mounted data volume (e.g. a database data directory mounted via
`./data:/var/lib/...`, not managed by Docker's own volume store), or, for a
native solution, a data directory/DB file on disk that lives outside the
venv/binary — `remove` does **not** delete it by default. It also does not
silently leave it alone forever: **ask explicitly, every run**, whether to
also delete that data, and wait for a yes/no answer before touching it.
Optional flag: `--purge-data` — skips the ask and goes straight to "yes"
(still covered by the confirm below, not a bypass of it).

**Plan (always show before executing) — read-only, computed by the script:**

```bash
bash <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh remove <solution> --plan
```

This prints the deletion plan (build artifact removed, re-acquire cost,
data outside the artifact) sourced from the audit's own state — don't
retype this table from memory of prose; show exactly what the script
printed.

This is the one command in the set that isn't a no-op-safe re-run. If a
solution has data outside its build artifact, that question is a **separate
gate** from the general confirm: make sure the user answered *that* question
specifically (or passed `--purge-data`), not just "yes, run the command."

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧

> 🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
>
> **Human decision needed:** Proceed with `remove` for the solution(s)
> listed in the plan? (yes / no)

If host data is in scope and `--purge-data` was **not** passed, a second
gate first:

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧

> 🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
>
> **Human decision needed:** Also delete data outside the build artifact
> at `<path>`?
>
> **A)** Keep the data (default)
> **B)** Purge that data too

**Execute (only after confirmation):**
```bash
bash <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh remove <solution> --apply [--purge-data]
```

Pass `--purge-data` only if the data question was answered yes (or the
flag was passed up front).

**Verify:** the script already re-ran the audit — the solution's build row
reads `absent`, running row "not running". If data outside the artifact
was in scope, also report its actual current on-disk state — still present
(kept) or gone (purged) — matching what was confirmed, not just assumed.

## Notes

{{Constraints worth remembering: which solutions are grouped together and
why, profile flags needed, anything that makes one solution's remove step
pricier than another's.}}

{{If any solution has data outside its build artifact (a Docker bind mount,
or a native process's data dir/DB file): name it here explicitly (path,
what it holds) and call out that removing the container/image or the
venv/binary alone does NOT reset it — a plain `remove` (data question
answered no) followed by `up`/`build` restores the exact same data,
including anything stray that accumulated on disk. Don't assume a rebuild
reset the data; check the path directly if that assumption matters.}}

{{If the project's own dev script exposes verbs beyond build/up/down/remove
(e.g. `logs`, a custom `seed`), name them here and note whether `/devops`
wraps them too.}}

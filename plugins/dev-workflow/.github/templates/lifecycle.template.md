# build / up / down / remove — lifecycle commands for {{PROJECT}}'s solutions

Goal: manage each of {{PROJECT}}'s runnable "solutions" — {{list, e.g. the
docker-compose services, or the native processes a dev script manages}} —
without hand-typing the underlying commands, and without ever deleting
something without a plan and a yes first.

Backend for this project: {{Docker Compose | native processes via
scripts/dev.sh (or equivalent) | mixed}}. If a native dev script already
exists, these commands thinly wrap it rather than reimplementing its
start/stop logic — `remove` is usually the one genuinely new verb, since
deleting build artifacts (a venv, a downloaded binary) is rarely something
an app's own dev script needs.

## Solutions this covers

| Solution | Underlying unit(s) | Notes |
|---|---|---|
| `{{solution}}` | `{{service name(s), or the build artifact + PID file pair}}` | {{what it is, how it's built/started}} |
| `all` (default) | {{core services/processes}} | {{what "all" means here — usually the everyday stack, excluding optional profiles unless named}} |

## Shared audit (Phase 1 for all four actions below)

```bash
zsh <skill-base-dir>/scripts/{{lifecycle-check-name}}.sh
```

Prints, per solution: whether its build artifact exists — image built/pulled,
or binary/venv present (`ok`/`absent`) — and whether it's currently running
— container, or PID alive (`info`). Read-only, exits 0 always. If invoked in
status-only mode (bare `/devops`), stop after showing the table.

## build \<solution|all\>

**Plan:** state which build artifact(s) will be (re)built and from what —
this is non-destructive; a running instance from a stale artifact is
untouched until `up` runs again.

**Execute:**
```bash
cd {{project-root}}
{{build command per solution, e.g. docker compose build <service>, or scripts/dev.sh build}}
```

**Verify:** re-run the shared audit — the solution's build row reads `ok`.
Building does not start anything; `up` does that.

## up \<solution|all\>

**Plan:** state what will start, on what port(s)/address, and whether a
build is needed first (pass a build flag / run `build` first whenever the
audit showed the build artifact `absent`).

**Execute:**
```bash
cd {{project-root}}
{{up command per solution, e.g. docker compose up -d --build <service>, or scripts/dev.sh up}}
```

**Verify:** re-run the shared audit — the solution's running row is set.
Then prove it's actually serving — the real check, not just "container/PID
exists": {{curl/log/health-check command per solution}}.

## down \<solution|all\>

**Plan:** state exactly which running unit(s) stop — container(s), or PID(s)
via the dev script. Cheaply reversible (`up` restarts from the same build
artifact) — show the plan, no confirmation gate needed beyond that.

**Execute:**
```bash
cd {{project-root}}
{{stop command per solution, e.g. docker compose stop <service>, or scripts/dev.sh down}}
```

**Verify:** re-run the shared audit — running row now reads "not running";
build-artifact row is unchanged.

## remove \<solution|all\>

**DESTRUCTIVE.** Deletes the solution's build artifact(s) — image(s)/named-
volume caches, or the venv/downloaded binary for a native solution. Not
cheaply reversible for anything pulled/downloaded rather than built
locally.

**If any solution persists real data outside its build artifact** — a
Docker bind-mounted data volume (e.g. a database data directory mounted via
`./data:/var/lib/...`, not managed by Docker's own volume store — `down -v`
never reaches it on its own since `-v` only drops named/anonymous Docker
volumes, not bind mounts), or, for a native solution, a data directory/DB
file on disk that lives outside the venv/binary — `remove` does **not**
delete it by default. It also does not silently leave it alone forever:
**ask explicitly, every run**, whether to also delete that data, and wait
for a yes/no answer before touching it. Optional flag: `--purge-data` —
skips the ask and goes straight to "yes" (still covered by the confirm
below, not a bypass of it).

**Plan (always show before executing):**

| Solution | Build artifact removed | Re-acquire cost | Data outside the artifact |
|---|---|---|---|
| `{{solution}}` | {{image name, or venv path / binary path}} | {{fast local rebuild / real re-download}} | {{path, or "none"}} |

Get an explicit yes before running — this is the one command in the set
that isn't a no-op-safe re-run. If a solution has data outside its build
artifact, that question is separate from the general confirm: make sure
the user answered *that* question specifically (or passed `--purge-data`),
not just "yes, run the command."

**Execute (only after confirmation):**
```bash
cd {{project-root}}
{{remove command per solution, e.g. docker compose down <service> --rmi local -v, or rm -rf .venv && rm -f tools/x/binary}}
```

If (and only if) the data question was answered yes / `--purge-data` was
passed:
```bash
rm -rf {{data path outside the build artifact for this solution}}
```

**Verify:** re-run the shared audit — the solution's build row reads
`absent`, running row "not running". If data outside the artifact was in
scope, also report its actual current on-disk state — still present (kept)
or gone (purged) — matching what was confirmed, not just assumed.

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

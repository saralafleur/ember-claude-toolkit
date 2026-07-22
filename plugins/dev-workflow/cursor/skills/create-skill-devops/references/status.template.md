# status — devops skill status report

Goal: one read-only report answering "what state is everything the devops
skill manages in right now?" Never installs, fixes, or changes anything.

## Procedure

1. **Discover** — enumerate every audit script in this skill's `scripts/`
   directory (`scripts/*-check.sh`). Each one usually belongs to a single
   command (`<command>-check.sh` → `<command>`), picked up automatically
   with no changes to this doc needed. Exception: the lifecycle set
   (`build`/`up`/`down`/`remove`) shares ONE script (e.g.
   `compose-check.sh`) — report those four commands together under one
   section keyed by solution, not as four repeated tables.

2. **Run** — execute each audit script (they are all read-only and exit 0):

   ```bash
   zsh <skill-base-dir>/scripts/<command>-check.sh
   ```

3. **Report** — for each command show:
   - A one-line verdict: **ready** (all build-relevant rows `ok`),
     **partial** (some `ok`, some not), or **not set up** (core rows
     MISSING/WRONG).
   - The full audit table (or, if long, only the non-`ok` rows plus a count
     of healthy ones).
   - If unhealthy: the exact command to fix it (e.g. `/devops <command>`).

4. **Extras worth including when relevant** (cheap, read-only): running
   services, booted simulators/containers, background installs or downloads
   still in flight from this session.

## Report format

```
## /devops status

| Command | Verdict | Fix |
|---|---|---|
| <command> | ✅ ready | — |

<details per command: audit table or non-ok rows>
```

Keep it scannable — verdicts first, detail after.

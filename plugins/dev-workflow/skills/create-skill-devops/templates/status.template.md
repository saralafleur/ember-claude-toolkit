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
   bash <skill-base-dir>/scripts/<command>-check.sh
   ```

3. **Report** — for each command show:
   - A one-line verdict: **ready** (all build-relevant rows `ok`),
     **partial** (some `ok`, some not), or **not set up** (core rows
     MISSING/WRONG).
   - The full audit table (or, if long, only the non-`ok` rows plus a count
     of healthy ones).
   - If unhealthy: the exact command to fix it (e.g. `/devops <command>`).

4. **Git worktree & branch status** — if the project is a git repo, report
   one row per `git worktree list` entry: path, current branch, sync state
   vs `origin` (ahead N / behind N / in sync), working-tree cleanliness
   (clean / N modified, M untracked), and whether the branch is merged into
   the project's default branch. This is the same table shape the
   `wrap-up` skill uses for its own orientation table — keep them
   consistent. Skip this section silently if the project isn't a git repo.

   ```bash
   # Default branch (fall back to checking main/master/trunk if this fails)
   default_branch="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##')"

   git worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r wt; do
     branch="$(git -C "$wt" symbolic-ref --short -q HEAD || git -C "$wt" rev-parse --short HEAD)"
     upstream="$(git -C "$wt" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"
     if [ -n "$upstream" ]; then
       counts="$(git -C "$wt" rev-list --left-right --count "$upstream...HEAD" 2>/dev/null)"
     fi
     dirty_count="$(git -C "$wt" status --porcelain | wc -l | tr -d ' ')"
     merged="$(git -C "$wt" branch --merged "$default_branch" 2>/dev/null | grep -qx "  $branch\|\* $branch" && echo yes || echo no)"
     echo "$wt | $branch | $counts | $dirty_count | $merged"
   done
   ```

   Treat the row for the default branch itself as `n/a — already default`
   in the last column rather than running the merge check against itself.

5. **Extras worth including when relevant** (cheap, read-only): running
   services, booted simulators/containers, background installs or downloads
   still in flight from this session.

## Report format

```
## /devops status

| Command | Verdict | Fix |
|---|---|---|
| <command> | ✅ ready | — |

<details per command: audit table or non-ok rows>

### Git worktree & branch status

| Location | Branch | vs `origin` | Working tree | Merged into default? |
|---|---|---|---|---|
| `<path>` | `<branch>` | ahead N / behind N / in sync | clean / N modified, M untracked | yes (`<sha>`) / no / n/a — already default |
```

Keep it scannable — verdicts first, detail after.

# Active Efforts Registry (append-only)

> Tracks every effort that has an isolated git-worktree set + namespaced Docker
> stack provisioned by `build-triage` (the generic global agent, see
> `~/.claude/agents/build-triage.md` steps 5/7/8). `build-triage` reads this to
> pick the next free port block for a new effort; `status-lead` reads this to
> flag file-overlap risk between concurrently open efforts before it turns into
> a merge conflict. This file lives wherever this project's `PROJECT-CONTEXT.md`
> names as its effort registry — one copy per project, not shared globally.
>
> **Status is the only column ever edited in place** — flip to `merged` or
> `abandoned` (and note the date) once a worktree is torn down. Everything else
> is append-only, one row per effort, newest at the bottom.
>
> **Teardown is manual, not automated** — `git worktree remove` per repo +
> `docker compose -p <slug> down -v` (or `clean-docker-disk-usage`'s per-effort
> mode), run by whoever merges. A branch that hasn't merged yet is still live
> work; nothing in this team deletes it on its own.

| Slug | Repos touched | Branches | Worktree paths | Docker project | Port block | Status | Created |
|------|---------------|----------|-----------------|-----------------|------------|--------|---------|
<!-- Example row:
| 2026-07-12-example-effort | api, tests | api: `effort/2026-07-12-example-effort` (new, off `main`) · tests: `effort/2026-07-12-example-effort` (new, off `main`) · web: `main` (base HEAD, no new branch — untouched by this effort) | `efforts/2026-07-12-example-effort/{web,api,tests}` | 2026-07-12-example-effort | 7100–7155 | in-progress | 2026-07-12 |
-->

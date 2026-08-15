# status / resume

Two lightweight commands for coming back to in-flight dispatch or triage
work without re-running the decide/gate phase. Neither spawns `em-analyst`,
`em-judge`, or `em-lead` — they only read state files and act on them.

## `status`

1. Find `<target>/.em-state/dispatch-state.json` and/or
   `<target>/.em-state/triage-state.json`. If neither exists, say so —
   there's no in-flight work to report on — and suggest `dispatch` or
   `triage` if the user wants to start one. `scripts/em_state.py show`
   reads both files and loudly flags any entry (or whole file) whose shape
   predates the scripted schema — read those by hand. The current run's
   plan lives in the run directory named by
   `<target>/.em-state/LATEST-dispatch` / `LATEST-triage` (one-line pointer
   files), not at a fixed `<target>/*-plan.md` path.
2. For each entry, report its current status (`IN_PROGRESS` /
   `READY-TO-MERGE` / `BLOCKED` / `MERGED` / `FAILED` for `dispatch`
   entries; `IN_PROGRESS` / `DONE` / `BLOCKED` / `FAILED` for `triage`
   entries — there's no `READY-TO-MERGE`/`MERGED` state for intake or
   housekeeping work, nothing gets merged), its `"kind"`
   (`housekeeping`/`intake`, for `triage` entries) plus branch/worktree if
   it's a `dispatch` entry, and — for `BLOCKED` — the open question if you
   can still read it (from that item's `decisions.md` for `dispatch`
   entries; from the delegate's own last reported message for `triage`
   entries, since intake delegates don't write to a `decisions.md` that
   doesn't exist yet).
3. **Don't assume a stale `IN_PROGRESS` entry is still actually running** —
   if enough time has plausibly passed (e.g. this is a new session), a
   background delegate from a prior session is very unlikely to still be
   reachable. Say so plainly rather than implying it's live: "recorded as
   IN_PROGRESS as of `<dispatched_at>`, but that was from a previous session
   — its agent ID likely isn't resumable anymore; check the worktree
   directly for what actually happened" (for `dispatch` entries — if the
   `worktree` skill is also installed at `~/.claude/skills/worktree/`, use
   `~/.claude/skills/worktree/scripts/worktree_status.py <worktree>`, which
   reports branch, dirty state, last commit, and merged-into-default
   read-only in one call; otherwise hand-run the equivalent plain git
   directly against the worktree — `git status`, `git log -1`, `git
   merge-base --is-ancestor <branch> <default-branch>`), or "check whether
   `<new-item-slug>/technical-plan.md` exists yet" (for `triage` intake
   entries — its presence means the delegate finished even if its own
   report never made it back). **Also check for an out-of-band merge:**
   `git merge-base --is-ancestor <branch> <default-branch>` — a human or
   another session merging a dispatched effort branch directly via
   `wrap-up` won't have updated this state file (wrap-up doesn't know
   `.em-state` exists), so a `READY-TO-MERGE`/`IN_PROGRESS` entry whose
   branch is already an ancestor of the default branch is finished work
   wearing a stale label, not phantom in-flight work — say so, and update
   the entry to `MERGED` (via `em_state.py`) with a note.

## `resume <item-slug> <answer>`

1. Look up `<item-slug>` in `dispatch-state.json`, then
   `triage-state.json` if not found there. If it's not `BLOCKED`, say so and
   stop — nothing to resume.
2. **Same-session resume (preferred, if the agent ID is still live in this
   conversation)**: `SendMessage` to that `agent_id` with the given answer.
   This continues the exact delegate with full context — worktree state (for
   `dispatch`) or whatever intake artifacts it already drafted (for
   `triage`), partial progress, which step it paused on. Update the
   relevant state file back to `IN_PROGRESS`.
3. **Cross-session fallback (if the original agent ID isn't resumable — a
   new session, or the prior one ended):**
   - **For a `dispatch` entry**: a `BLOCKED` dispatch entry should be rare
     now — `team-build` runs fully autonomous and cannot pause, so there is
     no `PENDING`-breadcrumb round-trip anymore (the pre-2026-08-14
     contract). The durable recovery sources are the **worktree itself**
     (`worktree_status.py`, if the `worktree` skill is installed — otherwise
     plain `git status`/`git log -1` against the worktree — plus the item's
     `build/` artifacts show exactly how far the build got) and the build's
     **`DECIDED-AUTO` trail in its `decisions.md`** (every choice it made on
     the way). If the stale entry
     predates the contract change and the item's `decisions.md` *does* hold
     a `PENDING` question, update it to `DECIDED` with the given answer
     (never delete the record of what was asked and decided). Either way,
     dispatch a **fresh**
     `Agent(subagent_type: "general-purpose", run_in_background: true)`
     delegate with the same kind of self-contained prompt as the original
     dispatch: run `team-build` on the item's folder (bare path). Because
     the worktree, branch, and any recorded decisions are all already on
     disk, this fresh delegate picks up essentially where the stopped one
     left off rather than starting the build over — it is a new agent ID,
     not new work.
   - **For a `triage` intake entry**: check the durable records, in order —
     (1) the item's intake folder: `team-intake` creates
     `<item>/intake/<date>-<slug>/` at its Step 1 and records questions in
     that folder's `decisions.md` (as `DECIDED-AUTO` adopted assumptions,
     since it no longer stops) *before* they surface; (2) the
     `<item>/request-blocked.md` file the dispatch protocol requires an
     early-blocking delegate to write before ending with `BLOCKED:` — this
     exists precisely because a new session cannot see the old
     conversation's messages, so the delegate's last chat report is never
     the only copy of the question. Then dispatch a **fresh**
     `Agent(subagent_type: "general-purpose", run_in_background:
     true)` delegate whose prompt includes the original request plus the
     now-answered question and its answer, so it doesn't re-ask. If the
     delegate had already gotten as far as writing `request.md` before
     blocking, point the fresh delegate at that existing folder instead of
     starting over.
   - Either way, record the new `agent_id` in the relevant state file,
     replacing the stale one.
4. Report back which path was used (same-session resume vs. fresh delegate)
   and the new status.

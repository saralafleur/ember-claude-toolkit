# status / resume

> **Note:** the dispatch/monitor/resume mechanics described in this
> reference assume Claude Code's Agent tool (`subagent_type`,
> `run_in_background`, `SendMessage`-to-resume for a `BLOCKED` delegate).
> This is unverified for Gemini CLI — adapt to whatever delegation/resume
> mechanism Gemini CLI actually supports when using this.

Two lightweight commands for coming back to in-flight dispatch or triage
work without re-running the decide/gate phase. Neither spawns `em-analyst`,
`em-judge`, or `em-lead` — they only read state files and act on them.

## `status`

1. Find `<target>/.em-state/dispatch-state.json` and/or
   `<target>/.em-state/triage-state.json`. If neither exists, say so —
   there's no in-flight work to report on — and suggest `dispatch` or
   `triage` if the user wants to start one.
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
   directly (`git -C <worktree> log`, `git -C <worktree> status`) for what
   actually happened" (for `dispatch` entries), or "check whether
   `<new-item-slug>/technical-plan.md` exists yet" (for `triage` intake
   entries — its presence means the delegate finished even if its own
   report never made it back).

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
   - **For a `dispatch` entry**: the delegate already wrote the open
     question to that item's `decisions.md` as `PENDING` before it
     stopped — that's what makes this recoverable at all. Update that entry
     to `DECIDED` with the given answer (never delete the record of what was
     asked and decided), then dispatch a **fresh**
     `Agent(subagent_type: "general-purpose", run_in_background: true)`
     delegate with the same kind of self-contained prompt as the original
     dispatch: run `team-build` on the item's folder. Because the worktree,
     branch, and now-answered decision are all already on disk, this fresh
     delegate picks up essentially where the paused one left off rather than
     starting the build over — it is a new agent ID, not new work.
   - **For a `triage` intake entry**: there's no `decisions.md` to have
     recorded the question (the item folder may not even exist yet if it
     blocked before writing `request.md`). Use whatever the last visible
     message from that delegate said the question was — check this
     conversation's own history for its `BLOCKED:` report — and dispatch a
     **fresh** `Agent(subagent_type: "general-purpose", run_in_background:
     true)` delegate whose prompt includes the original request plus the
     now-answered question and its answer, so it doesn't re-ask. If the
     delegate had already gotten as far as writing `request.md` before
     blocking, point the fresh delegate at that existing folder instead of
     starting over.
   - Either way, record the new `agent_id` in the relevant state file,
     replacing the stale one.
4. Report back which path was used (same-session resume vs. fresh delegate)
   and the new status.

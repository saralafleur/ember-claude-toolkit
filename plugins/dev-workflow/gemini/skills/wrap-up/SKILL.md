---
name: wrap-up
description: 'Close out the current unit of work in a git repo: audit for anything outstanding (uncommitted/untracked changes anywhere in the repo, PENDING/PARKED decisions, open caveats from a build/QA report, unfinished items raised earlier in the conversation), surface that list and get an explicit human go-ahead, then commit → push → merge into the repo''s actual default branch → clean up the now-merged branch/worktree. Trigger on the phrases "let''s wrap this up", "wrap this up", "wrap it up", "time to wrap up", or an explicit "/wrap-up" — in any project. Never skips the human confirmation gate, even when nothing outstanding is found.'
---

# Wrap-up

Closes out a unit of work: **audit → human gate → commit → push → merge →
clean up.** It exists so that finishing a piece of work is never a silent
`git commit && push` — it's a deliberate checkpoint where anything left
undone gets said out loud before the branch disappears.

This is a **direct, single-agent skill** — no sub-agent delegation. The agent
runs every step itself, sequentially, running git and (optionally) `gh` via
`run_shell_command`.

If more than one repo/branch/worktree is in play, take an optional hint about
which one to wrap up; otherwise infer it from the current conversation.

## When this triggers

- The user says anything to the effect of **"let's wrap this up"**, "wrap
  this up", "wrap it up", "time to wrap up" — in any project, at any point
  in a conversation.
- The user explicitly invokes `/wrap-up`.

Either way, treat it as: *the current unit of work is what we've been doing
in this conversation — close it out.*

## Step 0 — Determine scope

Figure out, from the conversation and the repo itself, what "this work" is:

- **Which repo(s)** are in play. If a project's `PROJECT-CONTEXT.md` names
  multiple repos, wrap up every repo actually touched this session — not
  just the first one found.
- **Which branch / worktree** holds the work. If the session used an
  isolated git worktree (e.g. from `team-build`), that worktree's branch is
  almost always the thing being wrapped up. If work happened directly on a
  branch in the main checkout, that's the scope instead.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- If genuinely ambiguous (more than one plausible branch/worktree with
  recent activity), ask the user which one — don't guess.

State this scope back in one line before continuing ("Wrapping up
`build/foo` in `~/repo-worktrees/foo` against `main` in `~/repo`") so the
user can correct it before anything happens.

## Step 1 — Outstanding-work audit (read-only)

Sweep for anything left undone. This step is read-only — it changes nothing.
Check **all** of the following, not just the feature branch:

1. **`git status` in the feature branch/worktree** — uncommitted or
   untracked changes.
2. **`git status` in the main checkout too** — a very common miss: planning
   artifacts, docs, or side-edits often land as untracked files in the base
   repo while a feature worktree is off doing the actual build. Sweep both.
3. **Any `decisions.md` for this effort** — use `grep_search` for `PENDING`
   or `PARKED` status. A decision nobody actually made yet is exactly the
   kind of thing that must not get silently merged away.
4. **The most recent build-report / QA-assessment / PM-plan for this
   effort**, if one exists (e.g. from `team-build`/`team-qa`/`team-intake`)
   — look for a caveated verdict (`GREEN-WITH-CAVEATS`, `GAPPED`, etc.) and
   any explicitly-deferred manual step (a device acceptance checklist, a
   follow-up task, anything marked "still open").
5. **The conversation itself** — anything the user or you flagged earlier as
   still needing to happen ("we'll do X later", "that's still open", a
   fix that was deferred) that hasn't actually happened since.
6. **Unpushed commits / diverged remote** — `git log @{u}..HEAD` and
   `HEAD..@{u}` on every branch in scope, so a stale local-only commit or a
   remote that's moved ahead doesn't get silently overwritten later.

Compile a single, concrete list. Each item should be one line naming the
specific thing (not "some things might be missing" — either name it or
leave it off).

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
## Step 2 — Human gate (always runs)

Present the audit result and get an explicit go-ahead — **every time**,
even when the audit found nothing:

- If the list is **non-empty**: show it plainly ("Here's what's still
  outstanding based on this conversation: ...") and ask whether to proceed
  anyway or hold off. Ask the user to choose, with options along the lines of
  *proceed anyway* / *hold off, I'll handle these first*.
- If the list is **empty**: say so ("Nothing outstanding found") and still
  confirm before proceeding — this is the last chance to catch a scope
  mistake from Step 0.

If the user says hold off: **stop here.** Do not commit, push, or merge.
If the user says proceed: continue to Step 3. Either answer is fine — this
gate is a checkpoint, not a blocker that has to resolve to "nothing's wrong."

## Step 3 — Commit

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- Review `git status` (and `git diff` for already-staged content) before
  staging anything — never blanket `git add -A`. If anything looks like it
  could be a secret (`.env`, credentials, tokens) even under an innocuous
  filename, stop and confirm with the user before including it.
- Stage the relevant files across every location identified in Step 0.
- Write a commit message that says *why*, not just *what* — one or two
  sentences, following the repo's existing commit-message style. End it with
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` per standing
  convention.
- If a pre-commit hook fails, fix the underlying issue and re-commit — never
  `--no-verify`.
- If there's genuinely nothing to commit anywhere in scope, say so and skip
  to Step 4 (there may still be unpushed commits from earlier).

## Step 4 — Push

- Push the branch to its remote, setting upstream if it isn't tracked yet.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- **Never force-push.** If the push is rejected because the remote has
  diverged, stop and surface it to the user — do not rebase or
  force-push to resolve it unilaterally.

## Step 5 — Merge into the default branch

- **Detect the actual default branch — don't hardcode `main`.** Use
  `git symbolic-ref refs/remotes/origin/HEAD` (or `gh repo view --json
  defaultBranchRef` if `gh` is available) to find it; fall back to checking
  which of `main`/`master`/`trunk` actually exists if that fails.
- Confirm the feature branch is fully pushed and the default branch's
  checkout is clean before merging.
- Merge with `--no-ff` and a descriptive merge commit message summarizing
  what the branch did (pull this from the branch's own commit history / any
  build-report — don't just write "merge branch X").
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- **If there's a merge conflict, stop and surface it** — resolve
  collaboratively with the user, never silently pick a side.
- Push the default branch.

## Step 6 — Clean up

- **Verify the branch is actually merged** (`git branch --merged
  <default-branch>` should list it) before deleting anything — never delete
  an unmerged branch.
- Delete the local feature branch.
- Delete the remote feature branch (`git push origin --delete <branch>`).
- If a git worktree was used for this effort, remove it
  (`git worktree remove <path>`) and run `git worktree prune`.

## Step 7 — Close the loop on tracking artifacts (if applicable)

If this effort has an associated `team-intake`/`team-qa`/`team-build`
folder with an SDLC journey artifact (`<intake-dir>/artifact-url.txt` and
`sdlc-journey.html` exist): write `<intake-dir>/merge.json` —
`{"merged_at": "<ISO8601>", "commit": "<merge-commit-sha>", "branch":
"<branch>", "note": "<optional>"}` — then, if the `time-ledger` skill is
installed, re-run its `journey_report.py` for that initiative and republish
the artifact at its existing URL (skip this sub-step entirely if
`time-ledger` isn't installed). This closes the "Merge" stage those
pipelines otherwise leave permanently "not started."

## Step 7.5 — Refresh project-wide status tracking (if configured)

**This is the step that makes a fresh session's bare "next" actually cheap
afterward — skipping it is how a wrap-up quietly leaves the project's status
ledger stale.** Closing out the SDLC journey artifact in Step 7 is
*intake-specific*; it says nothing to the *project-wide* status document a
`team-status`-equipped project's "next" depends on. Those are two different
documents. This step closes the second one.

- Check whether this project has `team-status` configured — look for a
  "Default status scope" (or "Delivery pipeline artifacts" folder) named in
  `PROJECT-CONTEXT.md`. If the project has no such file, or no scope named,
  skip this step silently — there's no project-wide ledger to refresh.
- If it does: invoke the `team-status` skill on that default scope (no
  narrower folder argument — a single-item-scoped status-report.md lives at
  a different path than the batch one "next" actually reads, so scoping
  narrow here would not fix the staleness). Let it run its own normal
  cache-first process: it will detect the effort you just merged as new/
  changed, do the one incremental scan needed to record it (never a reason
  to skip this because "we already know it's done" — the discipline of
  independently re-verifying before trusting a report is the whole point of
  that skill, even for work from this same session), and write a fresh
  `status-report.md` that correctly shows the effort as merged plus any
  named follow-up items (like a disclosed non-blocking fast-follow) as the
  new recommended next action.
- If `team-status` isn't installed/available for some reason, don't block on
  it — note in the Step 8 report that this refresh was skipped and why.

## Step 8 — Report back

One tight summary: what got committed (if anything), the push, the merge
commit sha, what got cleaned up, whether project-wide status tracking was
refreshed (Step 7.5) or skipped and why, and confirmation everything landed
on the remote. Then append one line to this skill's own run-log (see Memory
below) — repo, branch, merge commit, date.

## Best practices folded in (why each rule exists)

- **Never force-push, never `--no-verify`.** A wrap-up is a finishing move,
  not a recovery tool — if something's blocking a clean push or a hook is
  failing, that's signal to fix, not bypass.
- **Detect the default branch instead of assuming `main`.** Repos disagree
  (`main` vs `master` vs `trunk`); hardcoding it is exactly the kind of
  small assumption that silently does the wrong thing on a different repo.
- **Sweep the whole repo in Step 1, not just the feature branch/worktree.**
  Untracked planning docs and side-edits in the base checkout are an easy
  miss when all the visible activity happened in an isolated worktree.
- **Verify merged-ness before deleting a branch.** A branch delete is only
  safe once git itself confirms the commits are reachable from the default
  branch — don't infer it from "the merge command didn't error."
- **The human gate always runs, even on an empty audit.** It's not there to
  catch problems only — it's the last checkpoint to confirm scope before an
  irreversible-feeling action (branch deletion) happens.
- **Log the wrap-up.** A one-line append-only record answers "when did I
  last close this out" without re-deriving it from git log across every
  project.
- **Refresh project-wide status tracking, not just the initiative's own
  journey artifact (Step 7.5).** Found in practice: a build merged cleanly,
  its own SDLC journey artifact was closed out correctly, but the project's
  batch `status-report.md` (what a fresh session's bare "next" reads) was
  never told the effort existed — so the very next "next" paid an
  unnecessary incremental-scan cost to discover something that had already
  shipped. The intake-specific and project-wide documents are not the same
  file and closing one does not close the other.

## Memory

Append one line per wrap-up to this skill's own `memory/wrap-up-log.md`
(create it with a header row if it doesn't exist yet): date, project, repo
path, branch merged, merge commit sha, one-line summary of what shipped, and
whether anything was deferred (from the Step 2 gate).

This plugin ships `memory/wrap-up-log.md` **empty** (header only) — a fresh
install should never inherit anyone else's project history. Real entries are
local instance data, not shippable skill content; keep them out of any copy
of this repo you intend to publish or share.

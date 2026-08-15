---
name: wrap-up
description: 'Close out the current unit of work in a git repo: audit for anything outstanding (uncommitted/untracked changes anywhere in the repo, PENDING/PARKED decisions, open caveats from a build/QA report, unfinished items raised earlier in the conversation), surface that list and get an explicit human go-ahead, then commit → push → merge into the repo''s actual default branch → clean up the now-merged branch/worktree, also sweeping for other orphaned (empty, unregistered) effort worktree directories and offering to delete them with confirmation. Trigger on the phrases "let''s wrap this up", "wrap this up", "wrap it up", "time to wrap up", or an explicit "/wrap-up" — in any project. Never skips the human confirmation gate, even when nothing outstanding is found.'
argument-hint: 'Optional: which repo/branch/worktree to wrap up, if more than one is in play. Omit to let the skill infer it from the current conversation.'
---

# Wrap-up

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Closes out a unit of work: **audit → human gate → commit → push → merge →
clean up.** It exists so that finishing a piece of work is never a silent
`git commit && push` — it's a deliberate checkpoint where anything left
undone gets said out loud before the branch disappears.

This is a **direct, single-agent skill** — no sub-agent delegation. The main
agent runs every step itself, sequentially, using git and (optionally) `gh`.

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
  just the first one found. **Also check the `worktree` skill's private
  topology fallback, if the `worktree` skill is also installed at
  `~/.claude/skills/worktree/`** (`~/.claude/skills/worktree/memory/
  repo-groups.md`) — projects that opted out of a `PROJECT-CONTEXT.md`
  topology block keep their multi-repo map there instead; skipping it
  silently treats a multi-repo project as single-repo and the second repo
  never gets committed, pushed, or merged. If `worktree` isn't installed,
  this fallback simply doesn't exist — rely on `PROJECT-CONTEXT.md` alone,
  and ask the user directly (per the ambiguity rule below) if repo scope
  still isn't clear.
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

**Multiple cleanup candidates = ONE wrap-up.** When the scope is N
already-merged worktrees/branches in the same repo (e.g. dispatched from a
`worktree` skill report listing several cleanup candidates), treat them as
a single batched run: one Step 1 audit over the shared root, one Step 2
gate listing all N candidates, one Step 6 sweep, one Step 7 log row.
Never run N separate full-ceremony wrap-ups for one repo's cleanup pile —
the gates are not weakened, they just fire once over the full candidate
list. Do NOT drop the audit on cleanup-only runs; batched audits have
caught an uncommitted `decisions.md` inside a "clean" worktree and a dirty,
5-commits-unpushed default branch.

### Flow variants (all real, all legitimate)

- **No remote:** the repo has no `origin` — Step 4's push and Step 6's
  remote-branch deletion are skipped; say so in the Step 7 report rather
  than silently omitting them.
- **Direct-on-default:** the work sits directly on the default branch (no
  feature branch/worktree) — Step 5's merge and Step 6's branch/worktree
  deletions are vacuous (Step 6's orphan sweep still runs); the run is
  audit → gate → commit → push, and the log row's Branch column records
  `<default> (direct, no feature branch/worktree)`.
- **Cleanup-only:** entry is effectively at Step 6 (already-merged
  worktrees/branches to remove, often dispatched cold from the `worktree`
  skill). Steps 3–5 have nothing to do, but Step 1's audit and Step 2's
  gate still run — see the batch clause above.

## Step 1 — Outstanding-work audit (read-only)

Sweep for anything left undone. This step is read-only — it changes nothing.
Check **all** of the following, not just the feature branch:

1. **Mechanical git sweep — if the `worktree` skill is also installed at
   `~/.claude/skills/worktree/`, run
   `python3 ~/.claude/skills/worktree/scripts/worktree_status.py --table
   <repo(s)>`** (read-only, handles worktree-interior cwd, no-remote repos,
   and missing paths). One call covers, for the feature worktree AND the
   main checkout: uncommitted/untracked changes, unpushed commits, a
   diverged remote, and merged-into-default — the very common miss being
   planning artifacts, docs, or side-edits landing as untracked files in
   the base repo while a feature worktree is off doing the actual build.
   Its `--table` output IS the audit report's orientation table (don't
   hand-build one), and its JSON's `default_branch` is what Step 5 uses.
   **If `worktree` isn't installed,** fall back to hand-running the
   equivalent plain git per repo/worktree in scope — `git status
   --porcelain`, `git rev-list --count @{u}..HEAD` (unpushed commits) and
   `..@{u}` (behind), `git worktree list`, and `git merge-base
   --is-ancestor <branch> <default>` for merged-into-default — and
   hand-build the orientation table from those instead.
2. **Any `decisions.md` for this effort** — if the `team-decisions` skill
   is also installed at `~/.claude/skills/team-decisions/`, run
   `python3 ~/.claude/skills/team-decisions/scripts/scan_decisions.py <root>`
   (read-only, sub-second, multi-root) and read its walkthrough queue plus
   its **Review-me** list, rather than grepping for `PENDING`/`PARKED`
   yourself — plain grep has twice missed real open items on real files in
   this corpus because status markers drift in format (`- **PENDING** —`,
   status embedded in headings, `**PENDING (the user)**`). A decision nobody
   actually made yet is exactly the kind of thing that must not get
   silently merged away. **If `team-decisions` isn't installed,** fall
   back to grepping every `decisions.md` under the target for those
   `PENDING`/`PARKED` markers by hand, and say so in the audit report so
   the reader knows the weaker check was used.
3. **The most recent build-report / QA-assessment / PM-plan for this
   effort**, if one exists (e.g. from `team-build`/`team-qa`/`team-intake`)
   — look for a caveated verdict (`GREEN-WITH-CAVEATS`, `GAPPED`, etc.) and
   any explicitly-deferred manual step (a device acceptance checklist, a
   follow-up task, anything marked "still open").
4. **The conversation itself** — anything the user or you flagged earlier as
   still needing to happen ("we'll do X later", "that's still open", a
   fix that was deferred) that hasn't actually happened since.
5. **Orphan-candidate preview (read-only)** — run
   `python3 ~/.claude/skills/wrap-up/scripts/orphan_sweep.py <repo>
   <efforts-root(s)>` so the audit report's "Orphaned effort directories"
   section can render now (Step 6 makes the actual delete decision behind
   its own gate; this just detects). Use the sweep-root rules from Step 6.

**Cold-start fallback (items 3–4):** on a cold dispatch (e.g. a
cleanup-only wrap dispatched from the `worktree` skill) there IS no
conversation to recall, and there may be no reports to read. Mark those
checks **"n/a (cold invocation)"** in the audit rather than omitting them —
the template's omit-empty-sections rule otherwise makes "checked, nothing
found" indistinguishable from "nothing existed to check".

Compile a single, concrete list. Each item should be one line naming the
specific thing (not "some things might be missing" — either name it or
leave it off).

**Render the audit using `templates/audit-report.md`** — don't collapse it
into a prose paragraph. The template's tables (worktree/branch status,
uncommitted changes *grouped by folder or logical concern*, open
decisions/caveats, orphaned directories) exist so the user can make one
decision per group instead of one blanket yes/no over an undifferentiated
wall of files. Omit a section entirely when it has no data; never pad with
"none found" rows (exception: checks marked "n/a (cold invocation)" — see
above — render as exactly that, so absence stays distinguishable).

**Provisioning advisory (conditional — same pattern team-decisions
ratified):** if the compiled audit shows multi-repo scope, 3+ change
groups, a large file count, or any suspected-secret candidate, say so
alongside the report and suggest raising effort / confirming the session
model before Step 3 — the two failure channels the human gate cannot catch
(an audit omission looks like a cleaner report; the Step 3 secret gate only
fires if the model notices) fail invisibly on a weak tier. On a small,
single-group audit, say nothing. This is advisory only — never an up-front
gate.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
## Step 2 — Human gate (always runs)

Present the rendered audit report and get an explicit go-ahead — **every
time**, even when the audit found nothing:

- If the report has **content**: show the tables, then ask how to proceed.
  When the "uncommitted changes" table has more than one group, don't just
  offer a blanket proceed/hold-off — offer per-group choices too (e.g. via
  `AskUserQuestion`: *commit everything as one checkpoint* / *split into
  commits by group* / *hold off entirely*), so a user who wants to land the
  docs group now and review a feature group later actually can.
- If the report is **empty** (nothing outstanding): say so ("Nothing
  outstanding found") and still confirm before proceeding — this is the
  last chance to catch a scope mistake from Step 0.

If the user says hold off: **stop here.** Do not commit, push, or merge.
State plainly what's left behind — uncommitted work still uncommitted,
branch unmerged, nothing touched — and how to re-enter (re-invoke
`/wrap-up` with the same scope; the audit re-runs from current state).
A held-off run still gets its Step 7 log row, marked deferred.
If the user says proceed (whole or per-group): continue to Step 3 with that
grouping in hand. Either answer is fine — this gate is a checkpoint, not a
blocker that has to resolve to "nothing's wrong."

**Proceeding past an open PENDING/PARKED decision is deliberately NOT
written into `decisions.md`** — team-decisions has no acknowledged/waived
state, and the decision block stays bit-identical to one never reviewed
(it will re-surface on the next sweep, by design). Record the conscious
waive in the Step 7 log row's Deferred column instead.

## Concurrency guard — MANDATORY before Steps 3, 5, and 6

wrap-up performs the most destructive git operations in the skill corpus —
commit-everything sweeps of a shared checkout, merges, branch deletion,
`git worktree remove`/`prune`, `rm -rf` — on a machine where **concurrent
Claude sessions sharing a repo cwd have caused real work loss**. Run this
pre-flight immediately before Step 3's staging, again immediately before
Step 5's merge, and again immediately before Step 6's deletions (the gap
since the last human gate is unbounded — a gate can dwell for hours, so a
check done once at Step 2 proves nothing by Step 6):

1. **Other live sessions on this repo:**
   `ps aux | grep -i '[c]laude'` and `lsof +D <repo> 2>/dev/null | grep -E
   'claude|git'` — look for another claude/git process working in this repo
   or its worktrees (not this session's own).
2. **In-flight git operation:** check for `<repo>/.git/index.lock` (and
   `MERGE_HEAD`) in every checkout in scope — a lock file means another git
   process is (or was) mid-operation.
3. **Freshness delta (Step 3 only):** re-run `git status --porcelain` and
   compare against what the Step 1 audit saw; check `find`-style mtimes on
   the files about to be staged. A file that changed *since the audit* may
   be another session's in-flight WIP — exactly what a checkpoint commit
   would silently capture.

**On any evidence of a live sibling session: warn and gate.** Name what was
found (process, lock file, or fresh mtime), and do not stage, merge, or
delete until the user explicitly confirms how to proceed (wait, narrow the
scope, or proceed anyway). A clean sweep takes a few seconds and needs no
commentary — just run it. Never treat the Step 6 mergedness check as a
substitute: it protects against deleting unmerged *history*, not against
racing a *live* session.

## Step 3 — Commit

**Run the concurrency guard first** (see above) — staging is the first
point where another session's WIP could be swept into a commit.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- Review `git status` (and `git diff` for already-staged content) before
  staging anything — never blanket `git add -A` unless the user chose the
  single-checkpoint option in Step 2. If anything looks like it could be a
  secret (`.env`, credentials, tokens) even under an innocuous filename, stop
  and confirm with the user before including it.
- If the user chose **split into commits by group** in Step 2: stage and
  commit one group from the audit table at a time (`git add <paths for that
  group>`), each with its own message scoped to that group — don't fall back
  to one combined commit just because it's less typing.
- Otherwise stage the relevant files across every location identified in
  Step 0 as one checkpoint.
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
  force-push to resolve it unilaterally. State the stopped state plainly:
  local commits exist and are safe, nothing was pushed, no merge has
  happened; re-entry is resolving the divergence with the user and then
  resuming at this step. A stopped run still gets its Step 7 log row,
  marked deferred with the reason.
- If the repo has no remote at all, skip this step (note it in Step 7) —
  see "Flow variants".

## Step 5 — Merge into the default branch

- **Determine the actual default branch — don't hardcode `main`.** Source
  of truth, in order: (1) the cached `default_branch:` in the project's
  `PROJECT-CONTEXT.md` repo-topology block (or worktree's private
  `repo-groups.md`, if that skill is installed) when present; (2) if the
  `worktree` skill is installed and Step 1 ran it, the `default_branch`
  field its `worktree_status.py` run already emitted — the executable
  detection chain (`worktree_status.py:detect_default_branch`) lives there,
  canonical, so don't re-derive it by hand; (3) if neither is available
  (worktree not installed, no cache yet), derive it yourself: `git
  symbolic-ref --short refs/remotes/origin/HEAD` (or, with no remote, `git
  branch --show-current` on whichever checkout has never had a feature
  branch). **If (1) and (2) disagree, flag the mismatch to the user and
  offer to refresh the cached value** — wrap-up is the
  skill most likely to observe a default-branch change, and nothing else
  refreshes that cache. (Note: the topology block's `confirmed:` date only
  refreshes on full rediscovery — an old date there is normal, not itself
  evidence of staleness.)
- **Run the concurrency guard again** (see above) — the default branch's
  cleanliness check below is point-in-time, and the gap since Step 2's
  human gate is unbounded.
- Confirm the feature branch is fully pushed and the default branch's
  checkout is clean before merging.
- Merge with `--no-ff` and a descriptive merge commit message summarizing
  what the branch did (pull this from the branch's own commit history / any
  build-report — don't just write "merge branch X").
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- **If there's a merge conflict, stop and surface it** — resolve
  collaboratively with the user, never silently pick a side. **If the user
  defers instead of resolving, run `git merge --abort` before stopping** —
  never leave the default-branch checkout mid-merge (`MERGE_HEAD`, conflict
  markers) for the next session to trip over. State what's left behind
  (branch committed and pushed but unmerged; default branch restored to
  pre-merge state) and that re-entry is re-invoking `/wrap-up` on the same
  scope. A deferred/aborted run still gets its Step 7 log row, marked
  deferred with the reason.
- Push the default branch.

## Step 6 — Clean up

- **Run the concurrency guard one more time** (see above) — the deletions
  below otherwise execute several steps after the last human yes, and
  `git worktree prune` can deregister a *sibling session's* worktree caught
  in a transiently bad state.
- **Verify the branch is actually merged** — `git merge-base --is-ancestor
  <branch> <default-branch>` must exit 0 — before deleting anything; never
  delete an unmerged branch. (This command is self-contained — it needs no
  other skill installed. It's also the same recipe `worktree_status.py`
  uses when the `worktree` skill is installed, for consistency; don't use
  `git branch --merged`, the recipe family the 2026-08-14 worktree audit
  retired because it silently drops detached-HEAD worktrees.)
- **Confirm the deletion set in one line before executing it** ("Deleting
  branch `<x>` locally + on origin, removing worktree `<path>` — ok?") —
  a lightweight re-confirmation adjacent to the destructive commands, since
  the Step 2 gate may be hours behind by now.
- Delete the local feature branch.
- Delete the remote feature branch (`git push origin --delete <branch>`) —
  skip if there's no remote.
- If a git worktree was used for this effort, remove it
  (`git worktree remove <path>`) and run `git worktree prune`.
- **Sweep for orphaned effort directories.** Determine the sweep roots:
  the folder named in `PROJECT-CONTEXT.md` if configured, otherwise a
  top-level `efforts/` folder if one exists, **plus the sibling-directory
  patterns real runs actually use** — `<repo>-efforts/` and
  `<repo>-worktrees/` next to the repo (Step 0's own example places
  worktrees in a sibling directory; when `PROJECT-CONTEXT.md` doesn't name
  it, husks otherwise accumulate there unseen forever). Then run
  `python3 ~/.claude/skills/wrap-up/scripts/orphan_sweep.py <repo>
  <roots...>` (read-only detection — it never deletes; Step 1 item 5 may
  already have this output) to find directories that are **empty** and
  **not** currently listed in `git worktree list` — leftover husks from
  worktrees that were removed without `git worktree remove`, or that were
  created and never used. This is a
  repo-wide sweep, independent of which effort is being wrapped up this run
  — do it every time Step 6 runs, not just when it happens to match today's
  work.
  - Only flag a directory as a candidate if it is **both** empty (or
    contains no `.git` file — a real worktree checkout always has one
    pointing back at the main repo) **and** absent from `git worktree
    list`. A non-empty directory, or one git still recognizes as a live
    worktree, is never a candidate — leave it alone even if it looks old.
  - **This sweep deliberately does NOT catch what the `worktree` skill
    calls a cleanup candidate** — a *live, registered* worktree that's
    merged into default but never removed. Those are the exact complement
    of this sweep's husks, and they reach this skill only via Step 0's
    scope argument (the user pointing wrap-up at that worktree/effort),
    never via this sweep. Don't assume the sweep covered them.
  - Before asking, check whether each candidate is verifiably merged (the
    project's active-efforts/status tracking doc, or branch/log history for
    that slug) — this decides which plain-language framing to use.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
  - Present each candidate in plain language first, not git jargon — lead
    with what it means, not the mechanism ("empty", "unregistered",
    "orphaned" are mechanism words; save them for if the user asks what that
    means):
    - Verifiably merged: *"`<name>` has already been merged (via `<sha>`) but
      wasn't deleted — want me to delete it now?"*
    - Not verifiably merged (never built, or mergedness can't be confirmed
      from this repo): *"`<name>` looks unused/abandoned — it's empty and
      isn't a live worktree anywhere — want me to delete it now?"*
  - Ask the user (via `AskUserQuestion`) whether to delete them, using that
    framing. Never delete without this confirmation, even though the
    removal criteria above are conservative.
  - If the user says yes, delete the confirmed directories (`rm -rf
    <path>`, since they're already verified empty) and run `git worktree
    prune` afterward for good measure. If the user says no or wants to
    review first, leave them untouched and note them in the Step 7 report.
  - If no candidates are found, skip this silently — don't call it out in
    Step 7 unless something was found or removed.

## Step 7 — Report back

One tight summary: what got committed (if anything), the push, the merge
commit sha, and what got cleaned up (including any orphaned effort
directories removed or left in place per Step 6), and confirmation
everything landed on the remote.

**Write the merge fact back to the effort's build-report** (if this wrap-up
merged a `team-build` effort that has a `build-report.md`): append two
lines to it —

```
Merged: <merge-sha> on <YYYY-MM-DD>
Worktree removed: <path> (wrap-up, <YYYY-MM-DD>)
```

— so team-status's fingerprint and release-lead's shipped-commit
verification pick the merge up for free (the build-report otherwise carries
only the pre-merge branch-tip SHA, which release-lead has caught stale
twice, and its back-out recipe points at a worktree this run just deleted).
Same appended-line pattern as release-lead's `Released:` write-back.

**Then append one row to this skill's run-log via the script — never
hand-typed:**

```
python3 ~/.claude/skills/wrap-up/scripts/append_wrap_up_log_row.py \
  --date <YYYY-MM-DD> --project <name> --repo <path> \
  --branch "<branch merged, or '<default> (direct, no feature branch/worktree)'>" \
  --merge-commit <sha(s) or "no merge (…)"> \
  --summary "<ONE TO TWO SENTENCES — the report and commit messages carry the narrative, not this cell>" \
  --deferred "<what was deferred at any gate, or 'none'>"
```

All seven fields, every run — **including deferred/aborted runs** (put the
STOP reason and the state left behind in `--deferred`), so the log's "when
did I last close this out" purpose includes the runs that most need
follow-up.

## Step 7.5 — Refresh team-status (when configured)

If the project configures a default status scope (a `team-status` target in
its `PROJECT-CONTEXT.md`), offer to run — or in an autonomous dispatch,
run — `team-status` on that scope now that the merge landed, so the next
bare "next" reflects what actually shipped instead of paying a stale
rediscovery cost. If the project has no `PROJECT-CONTEXT.md` or no
configured scope, skip and say so in one line. (engineering-manager's
dispatch flow cites this step by number — `dispatch.md` Step 7 runs the
same refresh after its own merges.)

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
  branch (`git merge-base --is-ancestor`) — don't infer it from "the merge
  command didn't error."
- **Check for concurrent sessions before every destructive step.** The
  mergedness check protects history; the concurrency guard protects *live*
  sibling sessions — a machine-level risk with documented real work loss
  behind it. The two are not interchangeable.
- **The human gate always runs, even on an empty audit.** It's not there to
  catch problems only — it's the last checkpoint to confirm scope before an
  irreversible-feeling action (branch deletion) happens.
- **When a gate offers a genuine multi-way choice in plain chat text (not via
  `AskUserQuestion`), letter the options** — `A)`, `B)`, `C)`, etc. — so the
  user can answer with a single letter instead of re-describing the option
  (e.g. Step 0's "which branch/worktree" ambiguity). A gate with only one
  path — a plain yes/no "proceed?", like Step 2's own audit gate — doesn't
  need lettering.
- **Log the wrap-up.** A one-row record answers "when did I last close this
  out" without re-deriving it from git log across every project. Recent
  runs live in the active file; **grep `memory/archive/` too** before
  concluding a project was never wrapped — a project-keyed grep against
  only the active file returns empty (no error) for anything last wrapped
  before the rotation window.
- **Sweep for orphaned effort directories, but only delete with explicit
  confirmation (Step 6).** Found in practice: a worktree can be torn down
  outside a proper `git worktree remove` (a manual `rm -rf` on its
  contents, an interrupted cleanup), leaving an empty directory git no
  longer knows about. These are safe to remove — but "safe" isn't the same
  as "no need to ask"; a human gate stays required because a directory
  looking empty and unregistered is exactly the kind of judgment call that
  deserves a second set of eyes before deletion.
- **Render the audit as grouped tables (`templates/audit-report.md`), not
  prose.** Found in practice: when uncommitted work has piled up directly on
  a default branch across several unrelated sessions (no single feature
  branch to scope it), a paragraph summary forces one blanket decision over
  everything. Grouping by folder/concern lets the user commit the docs group
  now and hold a feature group for review, instead of all-or-nothing.

## Memory

One row per wrap-up in `~/.claude/skills/wrap-up/memory/wrap-up-log.md`,
appended **only** via
`~/.claude/skills/wrap-up/scripts/append_wrap_up_log_row.py` (which creates
the file with its standard header if it doesn't exist — there is no header
template). Seven columns: date, project, repo path, branch merged, merge
commit sha(s), a one-to-two-sentence summary of what shipped, and what (if
anything) was deferred at a gate. Rows older than the active window are
rotated to `memory/archive/wrap-up-log-YYYY-MM.md` — see
`memory/README.md` for the rotation and grep conventions.

**This log is wrap-up's private, write-only ledger — no other skill reads
it.** The merge fact consumers actually need is propagated instead through
Step 7's build-report write-back (`Merged:` / `Worktree removed:`) and
Step 7.5's team-status refresh; don't point another skill at this file.

<!--
Template for wrap-up Step 1 (audit) / Step 2 (human gate) output.
Fill every section that has data; omit a section entirely if it's empty
(don't render "none found" rows — just leave the section out). Never
collapse this back into a prose paragraph — the tables are the point:
they're what makes a per-group decision possible instead of one blanket
proceed/hold-off.
-->

<!--
create-skill-devops (SKILL.md, its status command) mirrors this
orientation table's column headers — keep the two in sync.
-->

# Wrap-up audit — <repo or project name>

## Worktree & branch status

One row per repo/worktree in scope (Step 0). This is the orientation table —
it's what tells you whether there's even a branch to merge, or whether
this is direct-on-default work like a plain commit+push. **If the
`worktree` skill is installed, don't hand-build it**: paste the table
Step 1's
`python3 ~/.claude/skills/worktree/scripts/worktree_status.py --table`
run already emitted (same information, script-accurate). **If `worktree`
isn't installed,** build this table by hand from plain `git status
--porcelain` / `git rev-list --count` / `git worktree list` / `git
merge-base --is-ancestor` per repo — see Step 1 item 1's fallback.

| Location | Branch | vs `origin` | Working tree | Merged into default? |
|---|---|---|---|---|
| `<path>` | `<branch>` | ahead N / behind N / in sync | clean / N modified, M untracked | yes (`<sha>`) / no / n/a — already default |

## Uncommitted changes, grouped by folder

Group by top-level folder *or* by logical concern when one folder mixes
unrelated work (e.g. `client/src/` touched by two unrelated features) —
whichever grouping lets the user make one decision per row. Don't group so
coarsely that "everything" becomes one row; don't group so finely that
every file is its own row. `Looks like` is a one-line read of *what this
group is*, not a restatement of the file list.

| Group (folder / concern) | Files | +/- | Looks like | Suggested action |
|---|---|---|---|---|
| `<folder or concern>` | N modified, M new | +X/-Y | <one-line description> | commit / hold / needs review |

## Open decisions & caveats

Pull from `decisions.md` (PENDING/PARKED rows only — omit DECIDED),
the latest build-report/QA-assessment's caveats and open-decisions
sections, and anything flagged earlier in the conversation as deferred.

| Source | Item | Status |
|---|---|---|
| `<path/to/decisions.md>` | <question/decision> | PENDING / PARKED |
| `<path/to/build-report.md>` | <caveat or follow-up> | non-blocking / blocking |

## Orphaned effort directories

Only render if Step 1 item 5's read-only orphan preview
(`scripts/orphan_sweep.py`) found candidates (empty + unregistered with
`git worktree list`) — the detection runs at Step 1 so this section is
fillable when the report renders; Step 6 makes the actual delete decision
behind its own gate. Lead the `What this means` column with plain language,
not git jargon — "already merged but not deleted" or "looks unused/
abandoned," not "orphaned"/"unregistered." Keep the mechanism (empty? in
`git worktree list`?) as backup detail for if the user asks, not the headline.
Flag verifiability honestly — a directory whose name doesn't match anything
in *this* repo's history can't be confirmed merged from here; say so instead
of assuming.

| Directory | What this means | Empty? | In `git worktree list`? |
|---|---|---|---|
| `<path>` | already merged (`<sha>`) but not deleted / looks unused-abandoned, mergedness not confirmable from here | yes | no |

## Recommended next step

One line: what you'd do by default if the user just said "proceed" — e.g.
"commit all groups as one checkpoint" or "commit the docs group now, hold
the feature groups for review."

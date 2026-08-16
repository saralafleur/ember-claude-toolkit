# status — devops skill status report

Goal: one read-only report answering "what state is everything the devops
skill manages in right now?" Never installs, fixes, or changes anything.

## Procedure

Run the report script and relay its output verbatim — it already discovers
every `scripts/*-check.sh`, runs each, classifies a verdict, groups the
lifecycle set (`build`/`up`/`down`/`remove`/`restart`, which share one
check script) into one section automatically, and appends the git worktree
& branch status:

```bash
bash <skill-base-dir>/scripts/status-report.sh
```

The only judgment left on top of this script's output: if a row's `Fix`
column or `DETAIL` string doesn't answer a follow-up question the user asks
(e.g. "why is that happening"), explain further using the full audit table
in that section. Don't re-derive the table or the verdicts by hand — the
script already computed them.

## Report format

The script's own output already matches this shape — relay it as-is:

```
## /devops status — <project>

| Command | Verdict | Fix |
|---|---|---|
| <command> | ✅ ready | — |

### <command>

<full audit table for that command>

### Git worktree & branch status

| Location | Branch | vs `origin` | Working tree | Merged into default? |
|---|---|---|---|---|
| `<path>` | `<branch>` | behind N / ahead N | clean / N changed | yes / no / n/a — already default |
```

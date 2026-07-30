# Triage Plan — <target folder>

**Run date:** <date>
**Source report:** `<target>/status-report.md` (as of <status-report's run date>)

## Housekeeping

<count> items, grouped by file (any two touching the same file share one
delegate):

| Group | File(s) | Corrections |
|---|---|---|
| 1 | `<path>` | <old → new, one line each> |
| 2 | `<path>` | ... |

## Needs-intake

**Recommended grouping:** PARALLEL | SEQUENTIAL | BATCHED | SINGLE-SESSION
**Confidence:** HIGH | LOW

<Brief restatement of em-analyst's reasoning — for BATCHED, name exactly
which items combine into which request document and why.>

## Judge panel

<Omit this whole section if the panel didn't run.>

| Judge | Vote | Grouping/order | Confidence |
|---|---|---|---|
| 1 | PARALLEL/SEQUENTIAL/BATCHED/SINGLE-SESSION | ... | HIGH/LOW |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |

**Reconciliation:** <majority / conservative-tiebreak reasoning, and any
dissent named explicitly.>

## Per-item / per-batch dispatch spec

<Omit this whole section for SINGLE-SESSION with zero needs-intake items.>

### <item-slug-or-batch-name>

- **New folder:** `<target>/<new-item-slug>/`
- **Position:** <independent | step N of sequence>
- **Batched items** (omit if not a batch): <list of original stage-map
  items/notes this request folds together>
- **Dispatch prompt:**

```
<the exact, fully self-contained prompt this delegate will receive,
including the verbatim BLOCKED protocol from references/triage.md>
```

## Needs-human (not dispatched)

| Item | What it needs | Who |
|---|---|---|
| ... | ... | ... |

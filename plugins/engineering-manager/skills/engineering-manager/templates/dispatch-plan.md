# Dispatch Plan — <target folder>

**Run date:** <date>
**Candidate items:** <slug>, <slug>, <slug>, ...

## Analyst finding

**Recommended grouping:** PARALLEL | SEQUENTIAL | SINGLE-SESSION
**Confidence:** HIGH | LOW

<Brief restatement of em-analyst's reasoning and the pairwise overlaps that
drove it.>

## Judge panel

<Omit this whole section if the panel didn't run.>

| Judge | Vote | Grouping/order | Confidence |
|---|---|---|---|
| 1 | PARALLEL/SEQUENTIAL/SINGLE-SESSION | ... | HIGH/LOW |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |

**Reconciliation:** <majority / conservative-tiebreak reasoning, and any
dissent named explicitly.>

## Final decision

**PARALLEL: [[slug, slug], [slug]]** (or **SEQUENTIAL: slug → slug → slug**,
or **SINGLE-SESSION**)

<One paragraph a human needs to approve or override this.>

## Per-item dispatch spec

<Omit this whole section for SINGLE-SESSION.>

### <item-slug>

- **Branch:** <branch name>
- **Worktree:** <path>
- **Merge order position:** <n, or "independent — any order">
- **Dispatch prompt:**

```
<the exact, fully self-contained prompt this delegate will receive,
including the verbatim BLOCKED protocol from em-lead.md>
```

## Flagged for direct human attention

<Any item(s) the lead judged too risky/large to auto-dispatch even though
independent — or "none".>

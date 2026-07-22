# Audit row templates

The archivist appends these. Both logs are append-only; newest at the bottom.

## `audit-log.md` (library content changes)
One row per committed change to a knowledge entry or the TOC.

```
| <YYYY-MM-DD> | <CREATE|UPDATE-DESC|UPDATE-BODY|RECLASSIFY|DEPRECATE> | <entry-id> | <desc-before → desc-after, or "—"> | <reason> | approved |
```

Header (when the file is first scaffolded):
```
| Date | Action | Entry | Description change | Reason | Gate |
|------|--------|-------|--------------------|--------|------|
```

## `description-history.md` (per-entry description versions — oscillation detection)
Append the new description under the entry's section every time it changes.

```
### <entry-id>
- <YYYY-MM-DD> v1: "<description text>"
- <YYYY-MM-DD> v2: "<description text>"
```

> Before proposing a description change, the analyst diffs the candidate against
> this list. If it equals a prior version, flag **THRASHING** in the approval
> summary instead of silently re-flipping.

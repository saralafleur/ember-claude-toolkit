# team-intake — Project Manager memory (cross-project fallback)

This is the **fallback** location the `intake-project-manager` agent (and the
other teams' leads) write to when a project doesn't name its own memory
locations in `PROJECT-CONTEXT.md`. A project-specific location — living in
that project's own repo — is always preferred; these global files exist so
work against a project with no such convention still gets a record
somewhere, not lost, and so different projects' history doesn't get mixed
into one file.

If you're looking for a specific project's actual history (its defect
catalog, request log, decision log), check that project's `PROJECT-CONTEXT.md`
first — it names where that project keeps its own.

Three files, same shape as a project-specific instance would have:

- **`recurring-issues.md`** — a project may have its own catalog of problems
  that have come back more than once; there is no cross-project one here
  (a defect catalog is inherently project-specific — nothing to fall back to).
- **`request-log.md`** — an append-only ledger of every intake processed
  against a project with no configured location of its own.
- **`decision-log.md`** — an append-only ledger of every significant decision
  raised against a project with no configured location of its own.

## Rules
- Keep entries terse and high-signal.
- A "recurring issue," on a project that has its own catalog, earns an entry
  the second time it appears — or the first time, if the PM judges it
  structurally likely to repeat.
- The durable fix is the point. "Fix it again" is not a resolution; "make
  both paths read from one source + add a guard" is.

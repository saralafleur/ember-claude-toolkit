# Build Task List — <slug>

> Authored by `build-planner`, merging the technical-plan (what to change) and the
> test-plan (what to prove) into ONE ordered, dependency-correct sequence. The
> implementer follows this top to bottom, test-first. Detailed enough to build
> without re-reading the original investigation.

## Build order (dependency-correct, red-first)
> Tests that prove a change come BEFORE the change they guard. `[test]` = author a
> failing test; `[impl]` = product code; `MANDATORY [<catalog-id>]` = durable
> cure (cite this project's defect-catalog id, if it has one configured), gates
> done.

| # | Task | Type | Layer | File(s) | Done-check |
|---|------|------|-------|---------|------------|
| 1 |  | test/impl | (unit / integration / e2e / product / DB) | `path` | command or assertion |
| 2 |  |  |  |  |  |

## Mandatory durable-cure tasks
- **#<n> — <cure>** `MANDATORY [<catalog-id or —>]` — <what makes it
  structural, not a patch>
  <or: "none — this change introduces no known recurring-issue surface">

## Sequencing notes
- **Do not parallelize:** <which steps touch the same files / one sequential implementer>
- **Needs services up:** <which steps need this effort's own stack (see
  build-brief.md's port block) vs pure unit-level>
- **Stop-and-report triggers:** <plan-is-wrong conditions the implementer must escalate, not improvise>

# Build Report — <slug>

> Authored by `build-lead`, synthesizing the build brief, task list, red/green
> evidence, and review. The document the user reads. Written before Step 8
> ships this build automatically (commit + push on its own effort branch,
> PR if this project has that convention) — no ask, no stop.

## What was built
<one paragraph, plain language: the end state now sitting in the working tree>

## Change verdict
**Verdict:** GREEN | GREEN-WITH-CAVEATS | BLOCKED
**Durable cure:** applied | deferred | n/a — <catalog-id (if this project has
one configured) + one line>

## Red → green evidence
> Proof the change is actually guarded — every new test failed before the fix
> and passes after.

| Test | Layer | RED before | GREEN after |
|------|-------|-----------|-------------|
| `path::case` | (unit / integration / e2e) | ✅ (assertion that failed) | ✅ |

## Files changed
```
<git diff --stat since the starting commit, per touched repo>
```

## Standing guards + Definition of Done
- [ ] Each new test observed RED before, GREEN after
- [ ] Full relevant suites green (per layer, with counts)
- [ ] Every standing guard from this project's defect-class catalog that
      applies to this change, met (list them — see `PROJECT-CONTEXT.md` /
      `build-verifier`'s green-evidence for what applies)
- [ ] Build/typecheck clean
- [ ] Plan's own DoD items met

## Worktree & stack
- **Worktree paths:** <per-repo paths from build-brief.md — not any shared
  checkout>
- **Docker stack** (if provisioned): <compose file, project name, port block>

## Shipped commit
- **Per repo:** <filled in immediately after Step 8's automatic commit — the
  resulting SHA. This is what `team-release`'s `release-lead` reads to
  verify what actually shipped, instead of re-deriving it from raw git
  history. Confirm this field is actually filled in before ending the
  session.>

## Residual risk & back-out
- **Watch:** <what could still be wrong; any deferred cure and its
  consequence>
- **Back-out (per touched repo):** `git -C <worktree-path> reset --hard
  <starting-commit>`

## Auto-decisions this run
- <DEC-id + one-line rationale, or "none">

## Next step
Ships automatically next, in Step 8 — commit + push on this effort's own
branch, no ask. Does not tear down the worktree or Docker stack — that's a
separate, manual step at merge time.

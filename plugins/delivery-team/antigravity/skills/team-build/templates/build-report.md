# Build Report — <slug>

> Authored by `build-lead`, synthesizing the build brief, task list, red/green
> evidence, and review. The document the user reads. This build **stopped at
> green** — it did not commit, push, or open a PR.

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

## Residual risk & back-out
- **Watch:** <what could still be wrong; any deferred cure and its
  consequence>
- **Back-out (per touched repo):** `git -C <worktree-path> reset --hard
  <starting-commit>`

## Open decisions
- <decision-id + status, or "none">

## Next step
Stops at green. **The user commits / pushes / opens a PR — or hands it back
for changes.** This skill does not commit. Does not tear down the worktree or
Docker stack — that's a separate, manual step at merge time.

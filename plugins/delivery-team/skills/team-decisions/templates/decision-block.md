# Canonical decision-block shape (the write contract)

Every NEW `## ` block in a decisions.md must parse to a vocabulary status
via one of the two canonical sites. `scripts/add_decision.py` emits this
shape; `scripts/lint_decisions.py` enforces it for post-cutoff files;
`scripts/decisions_lib.py` is the single definition all of them share.

```markdown
## DEC-7 — Which cache backend do we use — **PENDING**

- **Status:** PENDING
- **Raised:** 2026-08-14 · **Decided:** — · **Decided by:** —
- **Where we're coming from:** one to four sentences of context — what is
  being decided and why it matters now.
- **The question:** the actual question, one line.
- **Options:**
  - A — redis: fast, but another service to run
  - B — sqlite: zero ops, slower under concurrency
- **Recommendation:** A — latency dominates this workload.
```

Rules:

- **Status vocabulary** (see `decisions_lib.STATUS_VOCAB`): `PENDING`,
  `PARKED` (open — awaiting a human ruling); `WATCH`, `DEFERRED` (live
  tripwires — condition-triggered, not awaiting a ruling); `DECIDED`,
  `DECIDED-AUTO`, `DECIDED-DEFAULT`, `SUPERSEDED`, `RESOLVED`, `DONE`,
  `RECORD` (terminal). Nothing else.
- **`RECORD`** is for blocks that live in a decisions.md by convention but
  are not decisions — scope boundaries, findings notes, build-outcome
  records, narrative. Use it instead of leaving the status off.
- The **`- **Status:** X`** field line is the canonical site. The heading
  suffix (`— **PENDING**` after the last em-dash) is also recognized;
  add_decision.py writes both so either parser path succeeds.
- The `**Raised:** <date> · **Decided:** — · **Decided by:** —`
  placeholder line is what `resolve_decision.py` fills at resolution time
  — include it on every open block.
- Block IDs must be unique within their file (duplicate IDs break by-ID
  tooling like resolve_decision.py's block lookup; the corpus already has
  legacy collisions — don't add more).
- Separate blocks with a bare `---` line or the next `## ` heading.

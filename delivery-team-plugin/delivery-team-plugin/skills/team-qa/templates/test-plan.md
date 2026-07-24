# Test Plan — <slug>

> Authored by `qa-lead`, synthesizing Coverage + Risk + Unit + E2E findings. The QA
> deliverable: exactly what tests to add/modify. Detailed enough to implement
> without re-investigating. (Plan only — a separate step writes the tests.)

## Objective
<one paragraph: what coverage we add, the end state — which invariants get guarded
that aren't today>

## Coverage gap being closed
- <UNGUARDED surface> — <this project's defect-catalog id, if any> — <what assertion will now pin it>

## Test change set
<group by whatever layers this project actually has>
**Frontend (unit/component)**
- `path` — <add/update> — assertion: <…>

**Backend (unit/integration)**
- `path` — <add/update; which suite> — assertion: <…>

**E2E**
- `path` — <add/update; bucket + tag> — assertion: <…>

**Fixtures / test data**
- <or "none — reuse existing">

## Implementation steps
1.
2.
3.
<each red-first: what makes it fail before the fix and pass after>

## Single-source-of-truth guardrail
<if applicable: tests assert rendered paths agree with the project's canonical
registry/config; no blessing a hand-edited path>

## Durable-cure decision
<adding the structural cure now (registry-complete meta-test / round-trip test /
no-leak assertion) or only point tests? the call + consequence of deferring>

## How to run
<this project's actual commands, from PROJECT-CONTEXT.md if configured, else
discovered — one line per layer>

## Definition of Done
- [ ] Each new test observed RED before the fix, GREEN after
- [ ] Full relevant suite green
- [ ] Registry / source-of-truth in sync (if applicable)
- [ ]

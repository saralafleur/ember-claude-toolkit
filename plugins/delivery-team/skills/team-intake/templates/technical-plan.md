# Technical Plan — <slug>

> Authored by `intake-tech-lead`, synthesizing Product Owner + Architect +
> Engineer + QA. The engineering deliverable: what to do in the code.
> Detailed enough to implement without re-investigating.
>
> **Consumer contract — section names are load-bearing.** `build-triage`,
> `build-planner`, `build-test-author`, and `qa-triage` locate "Change set",
> "Implementation steps", "Testing & verification", and "Definition of Done"
> by heading text. Do not rename or drop sections.

## Objective
<one paragraph: what changes, the end state>

## Recommended approach
<chosen design; note any override of architect/engineer and why>

## Change set
**Frontend**
- `path` — <what changes>

**Backend**
- `path` — <what changes>

**Database / migration**
- <or "none">

**Tests**
- `path` — <add/update>

## Implementation steps
1.
2.
3.

## Single-source-of-truth guardrail
<for content/config that must render identically across multiple paths or
variants: confirm it routes through one shared source; no hand-editing a
single path>

## Testing & verification
- Unit/parity (Vitest, Yarn):
- E2E (Playwright):
- Backend (xUnit):
- How to run:

## Risks & rollback
- Risk:
- Rollback:

## Definition of Done
<!-- This checklist IS the plan's acceptance criteria: in a `fast` build,
     build-test-author derives its smoke assertions directly from these
     items. Each must be a concrete, observable behavior. -->
- [ ]
- [ ]

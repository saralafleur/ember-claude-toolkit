# Technical Plan — <slug>

> Authored by `intake-tech-lead`, synthesizing Architect + Engineer + QA. The
> engineering deliverable: what to do in the code. Detailed enough to implement
> without re-investigating.

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
- [ ]
- [ ]

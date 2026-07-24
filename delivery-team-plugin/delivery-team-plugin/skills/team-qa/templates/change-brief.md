# Change Brief — <slug>

> Authored by `qa-triage`. The single normalized statement of *what we just
> changed*, before any coverage evaluation.

- **Date:**
- **Scope source:** git-diff (base ref: `<ref>`) | explicit-files | intake-handoff
- **Intake link (if handoff):**

## Change summary
<1–2 plain sentences: what was built/modified>

## Changed files (by layer)
<group by whatever layers this project actually has — e.g.>
**Frontend**
- `path` — <what changed>

**Backend**
- `path` — <what changed>

**Database / migration**
- <or "none">

**Tests changed in this set**
- <or "none — change shipped without test edits">

**Config / other**
- <or "none">

## Surfaces / features touched
<specific feature/module/endpoint — name it precisely, not "the app">

## Variant relevance
<if this project has variants that must stay consistent (tenants, roles, locales,
office/entity types, etc.) — is one involved? yes/no + detail>

## Test-invariants at risk
<check against this project's defect-catalog ids if configured, else name the
general invariant classes plainly>
- [ ] **Cross-path consistency** — <catalog id, if any> — <touched? detail>
- [ ] **Variant isolation** — <catalog id, if any> — <touched? detail>
- [ ] **Round-trip integrity** — <catalog id, if any> — <touched? detail>
- [ ] **No unresolved-boundary-token leak** — <catalog id, if any> — <touched? detail>

## Stated intent / acceptance
<any "this should…" the change author noted>

## Open questions
**Blocking (cannot plan tests):**
- [ ]

**Non-blocking (proceeding on assumption):**
- <question> → assumption:

## Verdict
**READY** | **BLOCKED**

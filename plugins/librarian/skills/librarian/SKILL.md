---
name: librarian
description: 'The team librarian — curates DURABLE knowledge into a shared, growing library so repeat work approaches one-shot. Use when: you want to capture what was learned in a conversation (how a system works, how we accomplished something with Playwright/the archive utility, architectural decisions and direction, how a solution solved a problem, style/UI conventions, best practices); you want to audit and improve the library''s descriptions so the right knowledge actually loads; you want to wire a repo''s CLAUDE.md to the library; or you want to set up / point a repo at the library. Organizes knowledge by domain/subdomain/topic with retrieval descriptions, keeps a single Table of Contents, audits its own descriptions AND itself for thrashing, and gates every write behind human approval.'
argument-hint: 'A mode: `capture` (default), `audit`, `wire-up [repo path]`, or `setup`. Optional.'
---

# The Librarian

A small **virtual library team** that turns the knowledge we generate while
working into a durable, well-indexed **library** — so the next time we do an
activity, the right knowledge loads and we get close to one-shot.

This skill is an **orchestration**: you (the main agent) run the phases and
delegate to subagents. You own the **human approval gate** — nothing is written
to the library or to the librarian's own files without Sara's approval.

## The team (first-class agents shipped alongside this skill)
| Agent | Role | Writes? |
|-------|------|---------|
| `librarian-curator` | Mine a conversation → durable-knowledge entries with retrieval descriptions; de-dupe vs the TOC | No (proposes) |
| `librarian-analyst` | Audit retrieval health **and the librarian itself**; detect description/self thrashing | No (proposes) |
| `librarian-archivist` | The **only** writer: commit entries, regenerate the TOC, log the audit trail, scaffold/wire-up | Yes (post-approval) |

> Launch each with `subagent_type: "<name>"`. If a name isn't available as a
> subagent type, fall back to a `general-purpose` agent and paste the role brief
> from that agent's file, which lives next to the other `librarian-*` agent
> files wherever this skill was installed from (alongside this skill, or in
> `~/.claude/agents/` for a loose, non-plugin install).

## Library layout (at `<library-root>`, shared by many repos)
```
TABLE-OF-CONTENTS.md     generated index: domain | subdomain/topic | description | path
_loader.md               how to read/contribute (from templates/library-loader.md)
knowledge/<domain>/<subdomain>/<topic>.md
audit/audit-log.md             append-only: content changes
audit/description-history.md   per-entry description versions (oscillation detection)
```
Librarian self-memory lives with **this skill's own directory**, not the library:
`memory/librarian-lessons.md` and `audit/self-audit-log.md`, both found next to
this `SKILL.md`.

## Step 0 — Resolve the library (every run)
Read `config/library-locations.json`, in the `config/` folder next to this
`SKILL.md`.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- If `libraries` is **empty → first-run setup**: STOP and ask Sara *"Where should
  the library live?"* (absolute path). Then have `librarian-archivist` scaffold it
  there and register it. Do not invent a location.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- If libraries exist but the **current repo has no binding**, ask Sara which
  registered library this repo should use (or declare a new one), and record the
  binding. Several repos may share one `libraryId` — that is how locations pool
  into one library.
- Resolve `<library-root>` before doing anything else.

## Modes

### `capture` (default) — harvest knowledge from this conversation
1. Run `librarian-curator` on the conversation, giving it `<library-root>`, the
   current `TABLE-OF-CONTENTS.md`, and a scratchpad output path. It returns a
   proposal (NEW/UPDATE entries + descriptions + de-dupe notes + dropped list).
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
2. **Human gate.** Present a high-level summary via `AskUserQuestion`: for each
   proposed entry — action (NEW / UPDATE \<id\>), domain/subdomain/topic, title,
   and the proposed **description**; plus what was dropped. Let Sara
   approve / edit / reject **per item**.
3. Run `librarian-archivist` with the **approved set only**. It commits entries,
   regenerates the TOC, and appends the audit rows (+ description-history on any
   description change).
4. Report back: what was filed, where, and the new/updated TOC rows.

### `audit` — improve the library AND the librarian
1. Run `librarian-analyst` (reads `librarian-lessons.md` first, then the audit
   logs). It returns **Scope A** (retrieval health: description↔task match, dead/
   overlapping entries, **thrashing**) and **Scope B** (the librarian itself:
   capture quality, taxonomy health, curator/description heuristics, **self-
   thrashing**), plus proposed `librarian-lessons.md` lines.
🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
2. **Human gate.** Present the proposals, **THRASHING / self-thrashing items
   first** (old → new, and the prior version it would revert to). Approve / edit /
   reject per item.
3. Run `librarian-archivist` with the approved set: apply description/taxonomy
   edits (regenerate TOC, log to `audit-log.md` + `description-history.md`) and
   approved self-improvements to `SKILL.md` / agents / templates / lessons
   (log to `self-audit-log.md`, marking reverts).
4. Report what changed and what was deferred.

### `wire-up [repo path]` — point a repo's CLAUDE.md at the library (idempotent)
Run `librarian-archivist` to insert the `templates/claude-md-block.md` block
(with `<library-root>` filled in) into the repo's `CLAUDE.md` — **only if** the
`<!-- LIBRARIAN:BEGIN -->` sentinel is absent. If present, leave it and report
"already wired." This is the "if we already know the library, don't re-add it"
guard; CLAUDE.md holds only the pointer, never a copy of the library.

### `setup` — manage library locations/bindings
Declare a new library root, or bind/rebind the current repo to an existing one.
Archivist updates `config/library-locations.json`.

## Proactive offer
At the end of a substantial work session (a system understood, a non-trivial
capability built, a real architectural decision made), proactively offer:
*"Want me to have the librarian capture what we learned here?"* — then run
`capture` if Sara says yes. Don't nag on small/transient work.

## Conventions
- **Read-only proposers, single writer.** Curator and analyst never write to the
  library; only the archivist does, and only the approved set — in full, no extra
  edits.
- **Descriptions are retrieval hooks**, not topic labels — they decide what loads.
- **The TOC is generated** from frontmatter, never hand-curated.
- **Everything is gated and logged.** Content changes → `audit/`; librarian self-
  changes → `audit/self-audit-log.md`; both detect thrashing.
- **Durable only.** If it won't help repeat an activity later, it isn't library
  knowledge. Never store secrets or what the repo already records.

## A note on this being plugin-distributed content
This copy is the shareable template: `config/library-locations.json` ships
**empty** (no libraries registered) so a fresh install always goes through
first-run setup rather than inheriting anyone else's library locations. Do not
commit real library paths/bindings back into a plugin source tree meant for
distribution — that belongs only in a local, non-shared copy of this skill.

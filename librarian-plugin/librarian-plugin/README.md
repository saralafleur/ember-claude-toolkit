# Librarian

A small virtual "library team" for Gemini CLI that turns the knowledge
generated during real work sessions into a durable, well-indexed knowledge
library — shared across as many repos as you want — so the next time you do
a similar activity, the right knowledge loads and you get close to one-shot.

```
librarian-curator    mines a conversation -> proposes NEW/UPDATE entries
librarian-analyst    audits retrieval health + the librarian itself
librarian-archivist  the ONLY writer -- commits approved entries, regenerates
                      the Table of Contents, logs every change
```

Every write — new knowledge, description edits, taxonomy changes, even
changes to the librarian's own files — passes a human approval gate first.
Nothing is filed silently.

## Modes

Run `/librarian` with an optional mode argument:

- **`capture`** (default) — harvest durable knowledge from the current conversation.
- **`audit`** — improve the library's retrieval quality *and* the librarian's own process (detects "thrashing" — a description or self-change flip-flopping back to a prior version).
- **`wire-up [repo path]`** — add a pointer block to a repo's `GEMINI.md` so any agent working there knows the library exists.
- **`setup`** — declare a new library location, or bind/rebind the current repo to one.

## Install

### Option A — as a plugin (recommended)

```bash
/plugin marketplace add <path-or-git-url-to-this-folder>
/plugin install librarian@<marketplace-name>
/reload-plugins
```

Or for local testing without installing:

```bash
gemini extensions link /path/to/librarian-plugin
```

Loads as `/librarian` (or `/librarian:librarian` if you have another plugin
skill named `librarian` — plugin skills are namespaced by plugin name to
avoid collisions, and the plugin here is also named `librarian`, so in the
common case there's no visible prefix). Agents appear under **Custom
Agents** in `/context`.

### Option B — plain files

```bash
cp -R skills/librarian ~/.gemini/config/skills/
cp agents/*.md ~/.gemini/config/agents/
```

(Or into a project's own `.gemini/config/skills/` + `.gemini/config/agents/` to scope it
to one repo.) Loads as `/librarian`. No restart needed.

## First run

`library-locations.json` ships **empty** — on first run the skill notices
there's no registered library and asks you where it should live (an
absolute path). It scaffolds the library there and binds your current repo
to it. Every repo after that either reuses a library you already declared or
gets asked to declare/bind one — nothing is assumed.

## What's inside

- `skills/librarian/SKILL.md` — the orchestration logic and mode definitions.
- `skills/librarian/templates/` — the knowledge-entry format, the
  Table-of-Contents format, the `GEMINI.md` wire-up block, and audit-row
  formats.
- `skills/librarian/config/library-locations.json` — where libraries live and
  which repos are bound to which. **Shipped empty**; fills in on first use.
- `skills/librarian/memory/librarian-lessons.md` — durable lessons about
  *how to be a better librarian* (description anti-patterns, taxonomy
  lessons). Ships with one generic, genuinely reusable lesson already in it;
  the rest fills in as you run `audit`.
- `skills/librarian/audit/self-audit-log.md` — append-only log of changes to
  the librarian's own machinery. **Shipped empty.**

Each `SKILL.md` includes a short "path note" flagging the one thing that
changes between install methods — a few paths are written as
`~/.gemini/config/skills/librarian/...`, which are exactly correct under Option B,
and mean "the same folder bundled alongside this file" under Option A.

## Notes

- This is a **read/propose/write-on-approval** system throughout: the
  curator and analyst never write to the library — only the archivist does,
  and only after you've approved the proposed set.
- The Table of Contents is always generated from entry frontmatter, never
  hand-edited.
- Nothing here reaches outside the library root and the skill's own files —
  it doesn't touch product code.

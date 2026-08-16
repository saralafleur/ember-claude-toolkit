# Catalog digest — canonical rules

Single source of truth for the run-local defect-catalog digest step. The four
orchestrating pipelines (`team-build`, `team-qa`, `team-intake`, `team-status`)
and their first-agent files point here instead of restating this. Written
2026-08-16, `2026-08-16-catalog-digest-step-wiring` (WATCH-2 Appendix A.5).

## What this is

Each pipeline's existing first agent (`build-triage`, `qa-triage`,
`intake-triage`, `status-scanner`) resolves the run's changed surfaces to a
run-local, pre-resolved shortlist of defect-catalog entries — produced once
per run by `scan_catalog.py --digest` — so that no run misses a documented
trap because every downstream checker independently guesses, under token
pressure, which catalog entries matter. The digest is **additive and
locator-only**: every checker keeps its own full catalog access and an
explicit right to read past the digest. Checker rosters are unchanged by this
mechanism — see `roster-grammar.md`'s roster invariant.

Only the **existing first agent** runs the CLI (it already holds Bash). The
workflow `.js` files cannot run it themselves — no `child_process`, `fs`,
`require`, or `import` exists in that layer — so their only job is threading
the resulting text into downstream prompts. No new `agent()` call site is
added anywhere by this mechanism.

## The resolver recipe (path → `family:id`)

Run from the project root holding `DEFECT-CATALOG.md`:

```
Resolve surfaces -> family:id  (run from the root holding DEFECT-CATALOG.md)
 1. S = this run's changed-path set:
      team-build   -> the technical plan's Change set / build-brief file list
      team-qa      -> the change scope already passed to qa-triage
      team-intake  -> the brief's "Surface / area touched" paths
      team-status  -> the files this item's own artifacts cite
 2. For each path p in S take basename(p) and p's immediate parent dir name.
 3. grep -nF "<token>" DEFECT-CATALOG.md      -> body line numbers
 4. Map each hit line into CATALOG-INDEX.md's (family, id, lines) ranges
    -> family:id.  The index's ranges are the ONLY structural mapping used;
    never re-derive entry boundaries from the body.
 5. Rank ids by hit count desc, then by id; CAP AT 12 tokens.
    Record every id dropped by the cap -- a dropped id is an unresolved
    surface, not an absent one.
 6. python3 <root>/tools/catalog/scan_catalog.py <root> --digest \
      --surfaces <f:id> --surfaces <f:id> ...        # one flag per token
 7. Capture BOTH streams:  ... 1>digest.out 2>digest.err
    digest.err's "WARN: surfaces not found: [...]" IS the unresolved list.
    Never report stdout alone.
```

**Why the index and not a fresh parse of the catalog body:** `cmd_digest`'s
own comment (`scan_catalog.py`) commits to the digest being "a projection of
this parse, never a third, independently re-derived path (Family-1
guardrail)." The resolver obeys the same rule it feeds — digest, index, and
full text are three projections of one parse; never hold two independent
narrowings and quietly prefer the cheaper one.

**Skipped, not blocking, when the project has no catalog configured** — see
STATE A below. A project with no `tools/catalog/scan_catalog.py`, or one
where `scan_catalog.py` exists but the given root has no `DEFECT-CATALOG.md`
(exits 1 with `ERROR` on stderr), both resolve to "proceed exactly as
today" — never `BLOCKED`.

## The three-state block contract

The exact string each consuming `.js` file's `catalogDigestBlock` builds, and
each `status-scanner`'s own conditional block:

```
STATE A -- no catalog configured:      block = ''   (pipeline behaves exactly as today)

STATE B -- configured, 0 rows resolved:
  "\n\nDefect-catalog digest for this run: CONFIGURED, 0 of <n> surface(s) resolved.
   Unresolved: <token list>.  Artifact: <path>.
   Treat this as UNKNOWN, not as 'no known trap applies'. <escalation clause>"

STATE C -- N rows:
  "\n\nDefect-catalog digest for this run (locator-only, <n> entr(y|ies)) -- artifact: <path>:
   | family | id | file | lines |
   <rows>
   Unresolved surfaces: <list or 'none'>.  <escalation clause>"
```

Never collapse STATE B into STATE A. `WARN: surfaces not found` goes to
stderr with exit 0 and empty stdout — a failed resolution is byte-identical
to a clean one on stdout alone. Reading stdout only, and treating an empty
digest as "nothing applies," mechanizes this project's catalog instance
1:26 (two independently-computed facts disagreeing, cleared by two readers
before a third caught it).

## The escalation clause (literal — every consumer carries this unmodified)

> **This digest is a starting shortlist, not the complete set of entries that apply.** It is locator-only by design (family, id, file, line range — no lesson text). Read the cited line ranges in the catalog body, and expand into a fuller catalog read — the generated index first, then any line range in the body — whenever this shortlist looks incomplete for this change. You do not need permission to go past the digest, and a digest with no rows is never by itself evidence that no known trap applies.

## Locator-only, permanently

The digest carries no lesson/status text — family, id, file, and line range
only. This is a standing invariant, not an implementation detail: folding a
lesson column in later would silently retire the reviewer's full-text
escalation right without touching a word of this file. Any future proposal
to enrich the digest's content is its own explicit ruling, not a quiet
addition — see this cycle's `decisions.md`, row TL-5.

## Single-copy discipline

This file is the **only** place the resolver recipe, the three-state
contract, and the escalation clause are authored. The four `.js` files and
the four first-agent files point at it by name; none paste a copy. Pasting
this wording into eight separate files is the shortcut this project's
catalog instance 1:26 already proved fails — on this exact surface, the same
week it was proved (`~/.claude`'s WATCH-2 fix drifting from its
`ember-claude-toolkit` twin the same day it shipped).

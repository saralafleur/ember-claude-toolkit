# Client Firewall — the shared translate-to-client rule set

> **Single source of truth** for what may NEVER appear in a client-facing
> document. Consumed by `release-scribe`, `release-lead`, and
> `intake-client-liaison` (each keeps only a pointer here — do not re-grow a
> private copy in any agent file; extracted 2026-08-15 from the three drifted
> per-agent lists, workflow-audit SC5). Applies to `release-notes.md`,
> `client-approval.md`, and any other document a client will read. Everything
> below belongs in the private crosswalk instead, where it is welcome.
>
> On top of this list, always load the project's own forbidden id patterns
> from `PROJECT-CONTEXT.md` (defect-catalog ids, decision ids, item-code
> shapes) — those are per-project and live there, not here.
> The mechanical half of this sweep is scripted:
> `~/.claude/skills/team-release/scripts/jargon_lint.py` (regex classes +
> `--id-pattern` for the project's own shapes). The semantic half — process
> talk, whitelist judgment calls — stays with the agent.

## NEVER in a client-facing document

**Identifiers and codes**
- Internal item codes / work-item slugs, defect-catalog ids, decision ids
  (e.g. `DEC-…`), ticket numbers, test names, internal doc/registry names.
- Commit hashes, branch names, repo names, version-control references.
- File paths, file names, extensions, function/class/component/service/
  controller names.

**Internal labels and process framing**
- Internal option labels ("Option A/B/C"), status labels ("PARKED",
  "PENDING", "GREEN", "BLOCKED"), agent/team-role names.
- Engineering framing: how it's built, which files change, architecture
  terms, framework/tooling names, internal test-layer names, test-coverage
  talk. The client cares about *what the deliverable is* and *what it means
  for them* — not the mechanism.
- Version-control or process talk ("we migrated", "red-first", "green
  suite", "merged to dev").
- **Internal QA/process gaps advertised as content** — e.g. a "Technical
  Details" section that discloses an internal testing gap (a past release's
  QA-debt disclosure, for instance). If a gap warrants client disclosure,
  that is a deliberate decision routed through `decisions.md`, never
  incidental content.

**History and tone**
- The team's own date-stamped history of its mistakes. Don't say "we
  reversed a decision we made on 6/4" — say what it says now vs. what
  they're asking for. (Deliberate, decided disclosures — a security gap the
  user chose to disclose — are the exception, and they go through a
  decision, in plain client language.)
- Don't lead the client to an answer; a team *recommendation* is fine if
  labeled as such.

## The test
If a client reads the document and has to ask "what does this mean for me?",
the firewall failed. Keep the fact, drop the code.

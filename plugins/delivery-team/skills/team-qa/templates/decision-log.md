# Decision Log — <slug>

> Every clarifying / blocking question the QA team raised on this change, the
> context behind it, the options offered, and the choice made. Readable on its own.
> Newest decisions at the bottom.
>
> Status values: **PENDING** (asked, awaiting answer) · **DECIDED** ·
> **DECIDED-AUTO** (decided by the team itself under `auto-pilot`, on its own
> best recommendation, without asking) · **PARKED** (deferred to stakeholder /
> later) · **SUPERSEDED** (a later decision overrode this one — link it).

---

## DEC-<n> — <short title>
- **Item / area:** <e.g. registry-complete meta-test vs point cases>
- **Status:** PENDING | DECIDED | DECIDED-AUTO | PARKED | SUPERSEDED
- **Raised:** <date> · **Decided:** <date or —> · **Decided by:** <name, or
  "auto-pilot" for a `DECIDED-AUTO` entry, or —>
- **Recurring-issue link:** <this project's catalog id, if it has one configured, or —>

### The question
<the question as posed, verbatim>

### Where we're coming from (history, as of when)
<the dated context: what's being asked now, what the current coverage is, what
conflicts. Concrete, with dates.>

### Options presented
- **A) <label>** — <description / trade-off>
- **B) <label>** — <description / trade-off>
- **C) <label>** — <description / trade-off>

### Decision
**Chosen:** <option + label, or "— (pending)">
**Note from decision-maker:** <verbatim note, if any>
**Rationale / implications:** <why; what it means for the test plan>

---
<!-- copy the DEC block above for each new question -->

<!-- ═══ FORMAT CONTRACT (decision-log architecture v2, 2026-08-14) ═══
     MACHINE-PARSEABLE STATUS IS MANDATORY on every `## ` block, exactly as the
     template above shows: a `- **Status:** <TOKEN>` field line (and/or the
     token after the heading's last em-dash). TOKEN must be one of:
       PENDING · PARKED · WATCH · DEFERRED · DECIDED · DECIDED-AUTO ·
       DECIDED-DEFAULT · SUPERSEDED · RESOLVED · DONE · RECORD
     Use RECORD for blocks that aren't decisions (scope boundaries, findings,
     build-outcome records, narrative) instead of omitting the status.
     Do NOT invent other status words, bold the status into prose, or fold it
     into a sentence — the shared linter (`team-decisions`'s
     lint_decisions.py, wired into the project's `make ci` and a write-time
     hook) FAILS THE GATE on any nonconformant block in a file dated on/after
     2026-08-14. Blocks may also be authored via:
       python3 ~/.claude/skills/team-decisions/scripts/add_decision.py \
         <file> --id DEC-n --title "..." --status PENDING ...
     which emits this exact shape and self-checks it parses back clean. -->

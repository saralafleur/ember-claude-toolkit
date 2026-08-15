# Decision Log — <slug>

> Every clarifying / blocking question the status team raised on this run (or
> disposition it recorded — gate answers, correction dispositions, accepted
> residuals), the context behind it, the options offered, and the choice made.
> Readable on its own. Newest decisions at the bottom.
>
> Status values — the full v2 contract set (see the FORMAT CONTRACT at the
> bottom of this file): **PENDING** (asked, awaiting answer) · **PARKED**
> (deferred to stakeholder / later) · **WATCH** (a live tripwire / an
> accepted-as-is finding being carried deliberately) · **DEFERRED** ·
> **DECIDED** · **DECIDED-AUTO** (decided by the team itself under
> `auto-pilot`, on its own best recommendation, without asking) ·
> **DECIDED-DEFAULT** · **SUPERSEDED** (a later decision overrode this one —
> link it) · **RESOLVED** · **DONE** (e.g. an applied correction) ·
> **RECORD** (not a decision — a finding/scope/outcome record).

---

## DEC-<n> — <short title>
- **Item / area:** <e.g. dirty working tree at start · apply durable cure now vs defer · plan-is-wrong stop>
- **Status:** PENDING | PARKED | WATCH | DEFERRED | DECIDED | DECIDED-AUTO | DECIDED-DEFAULT | SUPERSEDED | RESOLVED | DONE | RECORD
- **Raised:** <date> · **Decided:** <date or —> · **Decided by:** <name, or
  "auto-pilot" for a `DECIDED-AUTO` entry, or —>
- **Recurring-issue link:** <this project's catalog id, if it has one
  configured, or —>

### The question
<the question as posed, verbatim>

### Where we're coming from (history, as of when)
<the dated context: what's being built, what the plan says, what conflicts — e.g.
"tree was dirty with X", "technical-plan chose a point-fix where the project's
defect catalog wants a structural meta-test instead", "implementer hit a step
the plan got wrong". Concrete, with dates.>

### Options presented
- **A) <label>** — <description / trade-off>
- **B) <label>** — <description / trade-off>
- **C) <label>** — <description / trade-off>

### Decision
**Chosen:** <option + label, or "— (pending)">
**Note from decision-maker:** <verbatim note, if any>
**Rationale / implications:** <why; what it means for the build>

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

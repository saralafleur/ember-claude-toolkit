# Decision Log — <slug>

> Every point this build's own best-recommendation logic decided something
> that used to be asked of a human, the context behind it, and the rationale.
> Readable on its own. Newest decisions at the bottom.
>
> team-build no longer stops to ask, so every entry it writes is
> **DECIDED-AUTO** (decided by the team itself, on its own already-documented
> best recommendation, without asking) — **PENDING**/**PARKED** don't occur
> in this skill's own output anymore (a genuinely un-auto-decidable state
> ends the run instead of logging a pending question — see `SKILL.md`). The
> full status-token set below is the shared cross-skill format contract
> (`team-decisions`'s linter parses all of them); team-build just only ever
> emits `DECIDED-AUTO` in practice.

---

## DEC-<n> — <short title>
- **Item / area:** <e.g. dirty working tree at start · version bump · durable-cure MANDATORY tag>
- **Status:** DECIDED-AUTO
- **Raised:** <date> · **Decided:** <same date> · **Decided by:** team-build (auto)
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
**Chosen:** <option + label>
**Rationale / implications:** <why this option is the documented best
recommendation for this situation; what it means for the build>

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

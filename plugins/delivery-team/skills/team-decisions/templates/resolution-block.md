<!--
Reference for Step 4 of team-decisions: the exact shape a decision block
takes BEFORE and AFTER resolution, matching the format the delivery-team
pipeline's own decisions.md files already use. Copy the shape, not this
comment block.
-->

## Before — PENDING

```
## DEC-2 — Secrets injection without Docker
- **Item / area:** Prod secrets (Azure Graph credentials)
- **Status:** PENDING
- **Raised:** 2026-08-06 · **Decided:** — · **Decided by:** —
- **Recurring-issue link:** —

### The question
Prod currently pulls Azure Graph credentials from AWS SSM Parameter Store at
deploy time and injects them into the `docker compose up` process
environment (never baked into an image, never persisted to disk). Without
Docker, how does this injection happen?

### Where we're coming from
<context>

### Options presented
- **A) <option>** — <tradeoff>
- **B) <option> (Recommended)** — <tradeoff>
```

## After — DECIDED-AUTO

Only three things change: the `Status` line, the `Raised`/`Decided`/
`Decided by` line, and two new trailing lines appended after the existing
content (before the next `## ` heading or `---`). Everything else — the
question, the context, the options — stays exactly as written; don't
rewrite history, just record the outcome.

For a decision team-decisions resolves on its own authority (the default
path — see SKILL.md Step 4 item 4), it re-derives the recommendation
itself and adopts it, so the status token is `DECIDED-AUTO` and `Decided
by` names the skill, not the user:

```
## DEC-2 — Secrets injection without Docker
- **Item / area:** Prod secrets (Azure Graph credentials)
- **Status:** DECIDED-AUTO
- **Raised:** 2026-08-06 · **Decided:** 2026-08-08 · **Decided by:** team-decisions (auto)
- **Recurring-issue link:** —

### The question
Prod currently pulls Azure Graph credentials from AWS SSM Parameter Store at
deploy time and injects them into the `docker compose up` process
environment (never baked into an image, never persisted to disk). Without
Docker, how does this injection happen?

### Where we're coming from
<context>

### Options presented
- **A) <option>** — <tradeoff>
- **B) <option> (Recommended)** — <tradeoff>

**Chosen:** B — <one-line summary of what was chosen and why>
**Note from decision-maker:** "<one-line reason this option was picked over the others>"
```

Omit the `**Note from decision-maker:**` line entirely when the
Recommendation reasoning is already fully captured by `Chosen` — don't
pad it with a restatement.

## After — DECIDED (the user answered via AskUserQuestion, Step 4.5)

When the decision is genuinely the user's call — a preference the file's own
context couldn't settle — team-decisions asks them directly via
`AskUserQuestion` instead of guessing, and their answer gets the plain
`DECIDED` token (that's the one reserved for a genuinely human-made call)
with `Decided by` naming them:

```
## DEC-2 — Secrets injection without Docker
- **Item / area:** Prod secrets (Azure Graph credentials)
- **Status:** DECIDED
- **Raised:** 2026-08-06 · **Decided:** 2026-08-08 · **Decided by:** the user (via team-decisions)
- **Recurring-issue link:** —

### The question
Prod currently pulls Azure Graph credentials from AWS SSM Parameter Store at
deploy time and injects them into the `docker compose up` process
environment (never baked into an image, never persisted to disk). Without
Docker, how does this injection happen?

### Where we're coming from
<context>

### Options presented
- **A) <option>** — <tradeoff>
- **B) <option> (Recommended)** — <tradeoff>

**Chosen:** A — <one-line summary of what the user actually chose>
**Note from decision-maker:** "<the user's own reason, if AskUserQuestion returned an annotation>"
```

Same three changes as the auto-resolved case above — `Status`, the
`Raised`/`Decided`/`Decided by` line, and the trailing `Chosen`/`Note`
lines — just with the human-made token and the user's name in `Decided by`.
Note `Chosen` here landed on **A**, not the file's own `(Recommended)`
**B** — the user's actual answer always wins over whatever the file suggested;
that's the entire point of asking instead of auto-resolving.

## Non-canonical shapes: status recorded elsewhere

Real `decisions.md` files don't always use the canonical `- **Status:**`
field shown above. The scan script itself recognizes a second convention —
status embedded at the end of the `## ` heading line — and real files have
also turned up status folded into an inline sentence with no `Status:`
label at all. Same rule always applies: match whatever shape the file
already uses, don't force it into the canonical shape above.

**Status in the heading:**
```
## QA-3 — CF-DD4 promotion veto window — PARKED
```
becomes
```
## QA-3 — CF-DD4 promotion veto window — DECIDED-AUTO
```
(a user-answered block gets `DECIDED` in that slot instead, same
mechanics) with `Chosen`/`Note from decision-maker` still appended at the
end of the block's body, exactly as in the canonical case above.

**Status folded into prose** (e.g. `**Status: PENDING.**` mid-paragraph, or
a bare `**PENDING (the user)**` with no `Status:` label): edit only the status
word/phrase in place, leave the surrounding sentence otherwise untouched,
and still append `Chosen`/`Note from decision-maker` at the end of the
block.

**Block authored by `team-intake`'s template** (recognizable by its
`### Decision` subheading already containing a placeholder
`**Chosen:** — (pending)` line, plus a `**Rationale / implications:**`
field): do **not** append a second `Chosen` line at the end of the body —
that leaves two contradictory `Chosen` lines in one block. Instead fill
the existing `### Decision` section in place: replace the `— (pending)`
placeholder with the chosen option, fill `Note from decision-maker` with
the one-line reason this option was picked (or drop the line if the
Recommendation reasoning already covers it), and write one sentence into
`Rationale / implications` — that field is part of team-intake's contract
for these blocks, don't leave it dangling. The `Status`/`Decided`/`Decided
by` lines update the same as the canonical case — `DECIDED-AUTO` /
`team-decisions (auto)` for an auto-resolved block, or `DECIDED` / `the user
(via team-decisions)` for one they answered through Step 4.5.
(`resolve_decision.py` declines on this shape on purpose; it's a manual
`Edit`.)

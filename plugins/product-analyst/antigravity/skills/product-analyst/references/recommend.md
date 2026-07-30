# product / tech

## Step 0 — Resolve mode, target, and output location

The skill's first argument is the mode: `product` (Feature/End-User top 10)
or `tech` (Technical/Hardening top 10). The rest is the target: a local
repo/folder path, or (if no local path exists) a description of a live
app/solution to analyze.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- **If the mode is missing or isn't `product`/`tech`, STOP and ask:** "Do
  you want the top 10 **product** (feature/end-user) recommendations or
  the top 10 **tech** (technical/hardening) recommendations?"
- **If the target is missing, STOP and ask:** "What should I analyze? Point
  me at a local repo/folder, or describe the live solution, and I'll write
  the top-10 report next to it."

**Output location:**
- If the target resolves to a local directory: create
  `<target>/product-analysis/<YYYY-MM-DD>-<slug>/` (derive a short
  kebab-case slug from the target's name). Create a `supporting/` subfolder
  inside it. Never write into the target's repo root directly.
- If the target has no local writable path (a live URL / described app with
  no repo on this machine): ask where to save the report before
  proceeding.

## Step 1 — Triage (gate)

Run `product-analyst-triage` on the target → it writes `solution-brief.md`
and returns a `READY` / `BLOCKED` verdict.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
- If **BLOCKED** (target unreadable, ambiguous, or so thin there's nothing
  to analyze — e.g. an empty repo), surface the blocking question and wait.
  Don't propose features for a solution nobody has pinned down.

## Step 2 — Specialist fan-out (parallel)

Launch these **three agents in parallel** (one batch), regardless of mode
— a technical fix can be raised by the UX lens and vice versa, so
classification happens later, not by restricting who runs. Give each the
`solution-brief.md` path and the `supporting/` output path:
- `product-analyst-ux` → `supporting/ux.md`
- `product-analyst-technical` → `supporting/technical.md`
- `product-analyst-market` → `supporting/market.md`

Each specialist proposes its own candidate features — evidence-grounded,
not generic — from its own lens only. Overlap between lenses is fine and
expected; the lead reconciles duplicates later.

## Step 3 — Double-validation (parallel, independent)

Launch `product-analyst-validator` **twice, in the same batch**, both
invocations given identical inputs (the brief + all three supporting
files) and neither given any indication a second pass is running:
- Invocation A → `supporting/validation-1.md`
- Invocation B → `supporting/validation-2.md`

This is the cross-check the whole team exists for. If only one pass is run,
or the two invocations are run sequentially where the second could see the
first's output, the double-validation requirement is not satisfied — do not
skip or fake this step.

## Step 4 — Lead synthesis

Run `product-analyst-lead` with the **mode** (`product` or `tech`), the
brief, all three supporting files, both validation passes, and the run-log
at
`~/.gemini/config/plugins/product-analyst/skills/product-analyst/memory/run-log.md`
(see `SKILL.md`'s Path note if your actual install root differs). It:

1. Reads the run-log first — flags any candidate matching a prior run
   against this same target (in either mode) as "recommended before
   (date), still outstanding" rather than presenting it as new.
2. Reconciles the two independent validation verdicts per candidate:
   - Both `CONFIRMED` → keeps it, full confidence.
   - Split verdict, or either `REVISE` → keeps it only if the underlying
     gap is still real, with confidence downgraded and both verdicts
     quoted.
   - Either `REJECT` → drops it, and says why in the report's "considered
     and rejected" section — never silently discard.
3. Dedupes overlapping candidates across the three specialist lenses.
4. Classifies each surviving candidate as **Feature/End-User** (changes
   what the end user can do or see) or **Technical/Hardening**
   (reliability, performance, efficiency, security, data integrity,
   observability, engineering process) — by the nature of the fix, not by
   which lens raised it.
5. **Keeps only the candidates matching the requested mode** (`product` →
   Feature/End-User, `tech` → Technical/Hardening) — candidates classified
   into the other list are dropped from the final ranking but still noted
   in the run-log so a later opposite-mode run isn't blindsided.
6. Ranks the requested list by impact × effort × validation confidence
   into its top 10. If fewer than 10 candidates survive validation, report
   fewer — never pad the list with a rejected or low-confidence item just
   to reach 10.
7. Writes `recommendations.md`.
8. Appends a row to the run-log.

## Step 5 — Report back

Summarize for the user in chat:
- The requested top 10 (Feature/End-User or Technical/Hardening,
  whichever mode was run), one line each (name + why it matters +
  validation confidence).
- Any candidates that were downgraded or dropped due to a split
  validation verdict, and why.
- If this target has a prior run-log entry (in either mode): what's
  changed since (built / still outstanding).
- Link to `recommendations.md`.

## Output format reference

`recommendations.md` structure (written by `product-analyst-lead`):

1. **Solution summary** — one paragraph, plain language: what this is, its
   domain/nature, current state.
2. **Top 10 — Feature / End-User** (mode `product`) **or Top 10 —
   Technical / Hardening** (mode `tech`) — ranked, each with: name, the
   concrete gap/evidence it addresses, why it matters for a solution of
   this kind, rough impact/effort, and validation confidence
   (confirmed-by-both / confirmed-with-caveat).
3. **Considered and not recommended** — candidates either validation pass
   rejected, with the reason, so nothing is silently dropped. Include
   candidates classified into the *other* list here too (one line each),
   noting they belong to the other mode rather than that they were
   rejected.
4. **Prior-run cross-reference** — if the run-log has an entry for this
   target (either mode), what's still outstanding from last time vs.
   newly identified.

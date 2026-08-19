# evaluate

## Step 0 — Resolve target and output

1. Get the target as something concrete: either a plain-language idea
   description, or a path to a real product/repo/artifact. If the user gives
   just a name with no detail, ask for enough framing that `viability-triage`
   has something real to normalize.
2. Output directory: default to `<project-root>/viability/<target-slug>/`
   in the current project.
3. If `<output-dir>/verdict.md` already exists, show the user the prior verdict
   (from `~/.claude/skills/team-viability/memory/run-log.md`) and ask whether
   this is a genuine re-evaluation (something changed) or she wants the old
   verdict as-is.

## Step 1 — Triage

Invoke `viability-triage` with the target and output directory. It writes
`brief.md`: what the target is, what decision this evaluation feeds, and —
critically — whether a `team-research` dossier already exists for this
target's topic.

**Hard gate:** if no relevant `team-research` dossier exists, stop here.
Tell the user: run `team-research`'s `research` command on this target's topic
first (see `~/.claude/skills/team-research`), then come back to `evaluate`.
Do not let `viability-market` improvise its own external research — that
duplicates a whole other team's job and loses the sourcing rigor
`team-research` already built in.

## Step 2 — Specialist fan-out (parallel)

One message, three agents:

- `viability-product` — reads the brief, ingests the real target artifact
  (actual code/product, not a description of it), writes
  `supporting/product.md`.
- `viability-market` — reads the brief and the `team-research` dossier it
  points to, writes `supporting/market.md`.
- `viability-stakeholder` — reads the brief, applies the
  Desirability-Feasibility-Viability lens, writes `supporting/stakeholder.md`.

## Step 3 — Judge

Invoke `viability-judge` with all three `supporting/*.md` files. It writes
`judgment.md`: an honest attempt to argue against the verdict the
specialists lean toward, or an explicit statement that no real
counter-argument holds up.

## Step 4 — Lead synthesis

Invoke `viability-lead` with `brief.md`, all three `supporting/*.md` files,
`judgment.md`, and `~/.claude/skills/team-viability/memory/run-log.md` (read
first, for prior-evaluation context on this same target). It writes
`verdict.md` and appends a row to
`~/.claude/skills/team-viability/memory/run-log.md`.

## Report back to the user

- The verdict: **BUILD / DON'T BUILD / NEEDS MORE EVIDENCE**
- Confidence, and why
- The strongest point for, and the strongest point against (from the judge)
- Path to `verdict.md`
- Whether this target had a prior run in
  `~/.claude/skills/team-viability/memory/run-log.md`, and what changed if so

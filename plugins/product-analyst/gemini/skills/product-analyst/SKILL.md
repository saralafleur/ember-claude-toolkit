---
name: product-analyst
argument-hint: "<product|tech> <path-or-description-of-solution>"
description: >
  Runs a virtual product team over any web solution you point it at — a
  local repo/folder, or a described live app — and produces ONE ranked
  top-10 list of what to build next based on its actual current state:
  `product` gives the top 10 feature/end-user recommendations, `tech`
  gives the top 10 technical/hardening recommendations. Both commands run
  the same evaluation: a triage clerk profiles the solution, three
  specialists (UX, technical, market/domain) propose candidate next
  features from distinct lenses, an independent validator cross-checks
  every candidate against real web-development best practices for that
  solution's specific domain — TWICE, blind to each other — and a lead
  reconciles the two independent verdicts and ranks the top 10 for
  whichever list was asked for. No recommendation reaches the final list
  on one agent's opinion alone.
---

# Product Analyst

**Argument:** the mode (`product` or `tech`), then a local repo/folder path
or a description of a live app/solution to analyze. If either is not given,
ask for it (see Step 0).

Runs a virtual **product team** over a web solution and answers "what
should we build next, and how do we know these are good recommendations and
not just one agent's guess?" Shape: **pipeline** — triage → parallel
specialist fan-out → an independent double-validation pass → lead
synthesis into a single requested top-10 list.

It exists because a single agent asked "what features should this app have"
tends to pattern-match to generic SaaS checklist items regardless of what
the solution actually is or needs. This team grounds every candidate in
concrete evidence from the actual solution, then makes a second, independent
pass verify that evidence against real best practices for that solution's
specific nature *before* it's allowed onto the final list.

This is a **cross-project skill** — usable against any codebase, folder, or
described live app you point it at, not tied to one repo.

## Command routing

| Argument | Command |
|---|---|
| `product <target>` | Full pipeline over `<target>` → `recommendations.md` with the top 10 **Feature/End-User** recommendations only — `references/recommend.md` |
| `tech <target>` | Full pipeline over `<target>` → `recommendations.md` with the top 10 **Technical/Hardening** recommendations only — `references/recommend.md` |
| *(none, or missing `product`/`tech`)* | Ask which list is wanted (product or tech) and what to analyze (a local repo/folder path, or a description of a live app) |

## The team (first-class subagents, installed at `~/.gemini/agents/`)

| Agent | Role |
|-------|------|
| `product-analyst-triage` | Profiles the target → `solution-brief.md`: what it is, its domain/nature, tech stack, current feature inventory |
| `product-analyst-ux` | Specialist lens: user experience / usability gaps → candidate features |
| `product-analyst-technical` | Specialist lens: engineering/architecture completeness gaps → candidate features |
| `product-analyst-market` | Specialist lens: competitive/domain convention (what comparable best-in-class solutions have) → candidate features |
| `product-analyst-validator` | Cross-checks every candidate against real best practices for this solution's domain. **Invoked twice, independently** — this is the double-validation |
| `product-analyst-lead` | Reconciles both validation passes, dedupes, classifies survivors as feature/end-user vs. technical/hardening, keeps only the candidates matching the requested mode, ranks the top 10, updates the run-log |

> **Path note (extension install):** this file was written assuming a
> standalone install (`~/.gemini/skills/product-analyst/` +
> `~/.gemini/agents/`). If you installed this as a Gemini CLI extension
> instead, every `~/.gemini/skills/product-analyst/...` path below means
> "the same-named folder bundled alongside this `SKILL.md`" (extensions
> install to `.gemini/extensions/<name>/`, keeping the same `skills/` and
> `agents/` subfolder layout), and `~/.gemini/agents/<name>.md` means "the
> matching file in this extension's own `agents/` folder" — same relative
> layout, different root.

> **How to invoke each role:** these are Gemini CLI subagents. Delegate to
> one either by explicit mention — `@product-analyst-ux <task>` — or by
> letting automatic delegation trigger it, since the main agent matches the
> task description to the subagent's `description` field. Always give the
> agent the `solution-brief.md` path, the output dir, and (for the
> validator/lead) the supporting files it needs to read. (If a subagent by
> that name isn't available, fall back to a plain instruction and paste the
> role brief from `~/.gemini/agents/<name>.md` directly into the request.)

## `product` / `tech`

Both commands run the identical evaluation pipeline; only the final
synthesis step differs (which list gets built, and at what depth).

1. Resolve the mode (`product` or `tech`), the target, and the output
   location (ask if not given — see Step 0 in `references/recommend.md`).
2. `product-analyst-triage` profiles the solution → `solution-brief.md`.
3. **Parallel fan-out** (one turn, three agents): `product-analyst-ux`,
   `product-analyst-technical`, `product-analyst-market` each write their
   candidate features to `supporting/{ux,technical,market}.md`. All three
   run regardless of mode — a technical fix can be raised by the UX lens
   and vice versa; classification happens later, by nature of the fix.
4. **Double-validation** (one turn, two independent invocations of the
   *same* agent, each blind to the other): `product-analyst-validator` runs
   twice over the full candidate pool → `supporting/validation-1.md` and
   `supporting/validation-2.md`.
5. `product-analyst-lead` reconciles both validation passes — a candidate
   only reaches the final list if both agree it's sound, or the lead
   explicitly notes a downgraded confidence on a split verdict — classifies
   each survivor as feature/end-user or technical/hardening (by the nature
   of the fix, not the lens that raised it), keeps only the candidates in
   the requested list, ranks its top 10, writes `recommendations.md`, and
   updates the run-log.
6. Report back in chat: the requested top 10 (one line each), overall
   validation confidence, and a link to `recommendations.md`.

Full procedure in `references/recommend.md`.

## Conventions

- **Output per run:** `<target>/product-analysis/<YYYY-MM-DD>-<slug>/`
  containing `solution-brief.md`, `supporting/*.md`, and
  `recommendations.md`. If the target isn't a writable local path (e.g. a
  live-URL-only analysis with no local repo), ask where to save the report.
- **Never invent a candidate feature without evidence** — every candidate
  from `product-analyst-ux`/`-technical`/`-market` must cite something
  concrete about the actual solution (a file, a missing flow, an absent
  convention), not a generic checklist item.
- **The validator passes must be genuinely independent** — invoke both in
  the same turn so neither sees the other's output; never let the lead run
  only one pass and call it "validated."
- **Memory:** `~/.gemini/skills/product-analyst/memory/run-log.md` — one
  row per run, read first by the lead so a re-run against the same
  solution recognizes "recommended before, still outstanding" instead of
  re-presenting it as a fresh discovery. Updated last by the lead. This
  plugin ships `memory/run-log.md` **empty** (header only) — a fresh
  install with no run history yet.

## Adding to the team

New specialist lenses (e.g. a security or accessibility specialist) can be
added the same way: give it its own scope so it never duplicates another
specialist's candidates, wire it into Step 3's parallel fan-out in
`references/recommend.md`, and add its output file to what
`product-analyst-validator` and `product-analyst-lead` read. Keep the
double-validation step unchanged — it validates the *merged* candidate
pool regardless of how many specialists feed it.

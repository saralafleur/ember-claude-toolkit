---
name: team-release
description: 'Run a small virtual release team (release-scribe, release-lead) over everything that shipped in a version and produce a client-facing release-notes.md plus a self-contained release-notes.pdf — on any project. Use when: one or more team-build runs are done (verified green) and you want to tell the client what changed; you are cutting a version and need plain-language notes for a non-technical client; you want to bundle several work items into ONE client release doc; or you need release notes that are fact-checked against the actual shipped commits, not just what a report claimed. Produces client-facing release-notes.md + release-notes.pdf (images embedded, self-contained), a private crosswalk mapping every note back to its item/commit/decision, and remembers each release in a release-log. On projects with a configured screenshot/quicksheet skill, also illustrates shipped features with annotated images before rendering the PDF.'
argument-hint: '[<version/folders> | auto|auto-pilot <version/folders> | direct <version/folders>] — a version label (e.g. v0.7.3) and/or the folder(s) holding the shipped work. Optional — the skill will ask what is in the release if omitted. See "Run modes" for the auto-pilot/direct tokens.'
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
  - Workflow
  - Workflow(delivery-team:release-autopilot)
---

# Team Release

⚠️ **Experimental.** This skill is actively evolving — expect rough edges, and report issues if something breaks.

Runs a small **virtual release team** over everything that shipped in a
version and produces the document the **client** actually reads:

- **`release-notes.md`** — plain-language, client-facing: *what changed for
  you*, in the client's own words, with zero internal shorthand.
- **`release-crosswalk.md`** — a PRIVATE crosswalk mapping every client-facing
  line back to the internal item / commit / decision (audit trail; never
  sent).

It exists because the delivery teams (`team-intake`, `team-qa`, `team-build`)
speak in item codes, defect-catalog ids, file paths, and commit hashes — and
the client does not, and never should. team-release is the **outward-facing**
end of the pipeline: it closes the loop by telling the client, truthfully and
legibly, what a release gave them. A **release is a version, not a single
build** — it can bundle several work items that shipped together.

This is an **orchestration**: you (the main agent) run the phases below and
delegate each role to a subagent. You are the release lead's editor.

> **This skill does NOT commit, push, or send anything.** It produces a
> verified, jargon-clean client document in the repo and stops. Sending it to
> the client is the user's call.

## The team (first-class agents, installed globally at `~/.claude/agents/`)
| Agent | Role |
|-------|------|
| `release-scribe` | Draft the client-facing `release-notes.md` + private crosswalk from the shipped items' build-reports / plans / decisions. Strips ALL jargon. |
| `release-lead` | Runs last. Fact-checks every client claim against the ACTUAL shipped git commits (nothing over-claimed, nothing shipped omitted), sweeps for leaked jargon, sets the version framing, finalizes, owns the release-log. |

> **Path note (plugin install):** this file was written assuming a standalone
> install (`~/.claude/skills/team-release/` + `~/.claude/agents/`). If you
> installed this as a plugin instead, every `~/.claude/skills/team-release/...`
> path below means "the same-named folder bundled alongside this `SKILL.md`",
> and `~/.claude/agents/<name>.md` means "the matching file in this plugin's
> own `agents/` folder" — same relative layout, different root.

> **How the team actually runs:** under **auto-pilot**, `release-scribe` and
> `release-lead` (Steps 2–3, plus any redraft loop) run inside one `Workflow`
> call — `workflows/release.js` — not as `Agent` calls you make directly.
> Under **standard or direct mode**, they're plain `Agent` calls exactly as
> written in Steps 2–3 below — launch each with `subagent_type: "<name>"`
> (e.g. `subagent_type: "release-scribe"`), giving each the version label,
> the item list with artifact paths, and the output dir. (Standard mode
> keeps its own gates a workflow script has no way to express — see the
> callout at the top of Step 2.)

## Run modes

Standard mode (bare `<version/folders>`) is the default described in
"Process" below: both agents run, every 🟧 gate stops and waits. Two optional
modes change that, and compose in either order:

| Mode | Token(s) | What changes |
|---|---|---|
| Auto-pilot | `auto-pilot`, alias `auto` | Every gate in "Process" is tagged **PREFERENCE**, **QUALITY**, or **SHIP**. PREFERENCE gates no longer stop — the team decides on its own best recommendation, logs the choice to `decisions.md` as `DECIDED-AUTO`, and keeps going. The QUALITY rule (a client claim no commit supports) **binds in every mode** — it is a repair mandate, not a stop-and-wait gate: the lead repairs or cuts the claim (or sends it back to the scribe for redraft); a false claim never ships, and every repair/cut is reported explicitly at the SHIP gate (see Step 3). **The SHIP gate proceeds too** (Step 4): auto-pilot finalizes the notes and reports them ready rather than asking. This changes nothing about what the skill can actually *do* — it already never transmits anything itself (see the note above); "proceeds" just means it stops blocking on the question. |
| Direct | `direct` | Accepted for consistency with the rest of the suite, but this skill's own roster is already minimal — one drafter, one fact-checker, neither droppable (the scribe has nothing to check without a draft; the fact-check is the whole reason this skill exists). `director-of-engineering` is not invoked here; `direct` behaves the same as standard mode for agent selection. |

### Step 0 — Establish the release scope (what shipped in this version)
A release note is scoped to a **version**, which may bundle several work
items.

- Parse the skill argument for a leading mode token first — `auto`/
  `auto-pilot` and/or `direct`, in either order, before the version/folders
  (see "Run modes" above). Strip whatever mode tokens are present; whatever
  remains is the scope.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **required-input, unaffected by any mode.**
- Check `PROJECT-CONTEXT.md` for this project's version source of truth and
  where its delivery-pipeline artifacts (intake/build folders) live. If the
  user gave a version and/or folders, use them; otherwise ask: "What's in
  this release? Give me the version and the folder(s) or build(s) it covers."
  No mode removes this gate — there's nothing to recommend when nothing at
  all was given.
- Determine the version from the project's version source of truth (per
  `PROJECT-CONTEXT.md`) unless the user names one.
- Enumerate the **work items** in the release: each item's intake/build
  folder and its `build-report.md`. Confirm each item was actually built (a
  green build-report). **A `GREEN-WITH-CAVEATS` build-report qualifies** —
  the item may release — but the caveat travels with it: the lead records it
  in the crosswalk and surfaces it at the SHIP gate so client disclosure is
  the user's call (Steps 3–4). Step 0's deliverable is the **item list +
  artifact paths + green-build confirmation** — nothing more. You *may* pass
  along a commit range per repo, but label it explicitly as a **hint**: the
  release-lead re-derives the real range itself during fact-check (the one
  time a handed-down range was checkable, it was wrong). Step 0's
  scope/range resolution is judgment work — run it at the strong tier, or
  explicitly treat its output as untrusted input the lead must re-derive
  (the lead already behaves this way). If a
  recent `status-report.md` exists for this project (`team-status`'s output),
  check its "Ready for Deployment" table first — those items have already
  been independently re-verified as merged, so it's a faster starting point
  than re-deriving the item list from scratch. Being in that table means
  code-complete and merged, **not** already released — this skill still owns
  deciding what's actually in the release and still fact-checks every
  client-facing claim itself in Step 3. Fall back to enumerating each item's
  `build-report.md` directly if no `status-report.md` exists.

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.**
- Do not invent scope. If it's unclear which items belong to this version,
  ask. **Under auto-pilot,** auto-decide instead: default to every build not
  yet covered by a version whose **latest release-log row is marked `SENT`**
  (fall back to `CLEARED` if the project records clearance but not
  transmission) — compute from the log's Status column, never from "the last
  entry": the newest row may be a `HOLD` pass on a never-sent release. Hold
  the auto-decision in memory and write it to `decisions.md` as
  `DECIDED-AUTO` **at Step 1, once the release output folder exists** (the
  folder isn't created until then), and state it plainly in the Step 4
  report-back rather than asking.

### Step 1 — Set up the output location
Check `PROJECT-CONTEXT.md` for this project's convention on where release
docs live; if none is configured, write to `<project-root>/releases/<version>/`
(create it) and note that you used the generic default. If the user names a
different location, use it. **Never** scatter release notes inside a single
item's build folder — a release spans items.

**Under auto-pilot:** Steps 2 and 3 below (draft, fact-check/finalize,
including the lead→scribe→lead redraft loop) run as one `Workflow` call
instead — standard/direct mode keeps running them as written below, since
this skill's SHIP gate and scope-reopening gate have no pause-for-human
primitive to express inside a script.

```
Workflow({
  scriptPath: "~/.claude/skills/team-release/workflows/release.js",
  args: {
    version: "<version>",
    items: [ {slug, path, buildReportPath}, ... ],
    outputDir: "<output-dir-from-step-1>",
    scopeAssumptionNote: "<Step 0's DECIDED-AUTO scope pick, if any>",
    priorCrosswalkPath: "<prior release-crosswalk.md, re-entry passes only>",
    priorReleaseLogStatus: "<prior release-log Status token, re-entry passes only>"
  }
})
```

(Under a plugin install, `scriptPath` is
`${CLAUDE_PLUGIN_ROOT}/skills/team-release/workflows/release.js` instead —
same "Path note" translation as everywhere else in this file.)

The QUALITY rule (a claim no commit supports gets repaired/cut, never
shipped) still binds exactly as described in Step 3 — it's a repair mandate
inside the script now, not a stop-and-wait. The run goes silent in this
session until it completes; say so before starting it. It returns
`status: 'ready-to-send'` plus what the lead repaired/cut/added — identical
in substance to what auto-pilot already reported before this conversion,
since this skill never transmits anything itself in any mode. Use the
return value directly in Step 4's report-back; the SHIP gate itself (Step 4)
still runs in this session, not inside the workflow.

### Step 2 — Draft the client notes (standard/direct mode)
Run `release-scribe` with the version, the item list + artifact paths, and
the output dir. It **seeds both documents from
`~/.claude/skills/team-release/templates/`** (their structure is the
standard, not a suggestion), reads every item's build-report / pm-plan /
plan / decisions, and writes:
- `release-notes.md` (client-facing draft)
- `release-crosswalk.md` (private: each note → item/decision; the Commit(s)
  column stays `—` — it is lead-owned, filled during Step 3 verification)

### Step 3 — Fact-check + finalize (standard/direct mode, gate)
Run `release-lead`. It verifies every client-facing claim against the
**actual git commits** in the release range (over-claim → cut/return;
shipped-but-omitted → add), sweeps `release-notes.md` for any leaked internal
jargon (including this project's own defect-catalog/decision-id patterns, if
`PROJECT-CONTEXT.md` names any), confirms the version/date, finalizes the
notes, updates the crosswalk with its verification result per note, and
appends a row to the release-log — via
`~/.claude/skills/team-release/scripts/append_release_log_row.py`, one row
per lead pass, carrying a Status token (`HOLD — <reason>` / `CLEARED` /
`SENT <date>`) and a crosswalk link (see release-lead.md for the row
contract).
- If the lead finds a client claim **no commit supports**, that's the
  **QUALITY rule — binds in every mode, including auto-pilot.** The notes
  never ship a false claim; there's no "best recommendation" for a claim
  that isn't true. It operates as a **repair mandate, not a stop-and-wait
  gate**: the lead fixes the wording or cuts the line itself, or **sends it
  back** to the scribe for a targeted redraft when the fix is voice-level
  (the lead→scribe→lead loop — a targeted redraft-and-reverify pass is the
  established precedent here), then re-verifies. Every repair, cut, or send-back is reported
  explicitly at the SHIP gate so the user sees exactly what was caught.
- The lead **may reopen Step 0's scope decision** when its commit sweep
  finds a shipped, unclaimed client-visible item: route the scope change
  through the release folder's `decisions.md` (PENDING → ask the user;
  `DECIDED-AUTO` under auto-pilot), never a silent expansion.
- The lead also checks each bundled item's build-report for
  `GREEN-WITH-CAVEATS` / QA-debt markers and records any in the crosswalk
  for SHIP-gate disclosure (see release-lead.md, verification item 5).

### Step 3.5 — Illustrate the release (project-specific, optional)
Some projects maintain their own screenshot/quicksheet-generation skill for
turning a shipped feature into a client-shareable annotated image (e.g. a
project's `release-quicksheets` skill). This step exists so illustrated
release notes are a standing part of the pipeline for projects that have
one, without team-release hard-depending on any project-specific tooling.

- Check `PROJECT-CONTEXT.md` for a **"Release illustration skill"** entry
  (or equivalent — grep for "quicksheet"/"release illustration"/"screenshot
  skill" if the heading varies). If none is configured, **skip this step
  entirely and say so in the Step 4 report** — this is the common case for
  most projects and is not a gap to apologize for.
- If one is configured, invoke it once per client-facing feature section in
  the finalized `release-notes.md` (its own SKILL.md defines which sections
  warrant an image vs. which to skip — e.g. a wording-only fix usually
  doesn't need one; trust that skill's own judgment call, but if a feature
  clearly changes a visible UI surface and the illustration skill skipped
  it, ask before accepting the omission). For a feature already illustrated
  in an earlier, unsent release that this release is superseding/folding in
  (see "Re-entry passes" and the client firewall on combined releases),
  reuse that existing image rather than regenerating it if the underlying
  UI hasn't changed since — regenerating identical content wastes the
  (often substantial) live-screenshot work for no benefit.
- 🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **PREFERENCE gate.** Once images exist,
  confirm with the user before wiring `![alt](images/<slug>.png)` references
  into `release-notes.md` — the illustration skill's own convention is to
  ask before editing release notes unprompted, and that gate still applies
  here even though it's now a standing pipeline step. **Under auto-pilot,**
  skip the ask: wire the images in automatically and log the choice as
  `DECIDED-AUTO`, since this step only ever adds supporting visuals to
  already-approved text, never changes a claim.
- After wiring images in, do a final jargon/consistency check on the added
  `alt` text and any figure captions — the illustration skill strips UI
  chrome and internal ids from its own output, but doesn't know this
  project's specific jargon list.

### Step 3.6 — Render the client PDF
Always runs (no project-specific dependency) — a release isn't done until
there's a clean, shareable PDF alongside the markdown, since some clients
expect an attachment rather than a link.

```bash
python3 ~/.claude/skills/team-release/scripts/render_release_pdf.py \
  <output-dir>/release-notes.md \
  <output-dir>/release-notes.pdf
```

(Under a plugin install, the script path follows the same "Path note"
translation as everywhere else in this file.) The script embeds every local
image the notes reference (including any wired in at Step 3.5) as base64 so
the PDF is fully self-contained — no external file references, safe to
email or archive on its own. It renders via a fixed, professional default
style (a single `--accent <hex>` flag exists for light per-project color
tuning; don't hand-roll a second rendering path — extend this script's CSS
if a project genuinely needs more).

Re-render this step **any time `release-notes.md` changes after this
point** — a redraft, a Step 4.5-style correction, or a later re-entry pass
that repairs a line all leave a stale PDF behind if this step isn't re-run.
Treat the PDF as generated output, not a hand-maintained artifact: never
edit it directly.

### Step 4 — Report back
Summarize for the user in chat:
- The **version** and the **items** bundled into it.
- The client-facing headline (2–3 lines of what the client will see).
- Any claim the lead **cut, added, repaired, or sent back** during
  fact-check, and why (every QUALITY-rule catch is disclosed here — this is
  the visibility half of the repair mandate).
- Any **`GREEN-WITH-CAVEATS` / QA-debt caveat** on a bundled item — whether
  and how to disclose it to the client is the user's call at the SHIP gate.
- Any **"build-report claimed GREEN but commit unmerged/stale"** catch, and
  confirmation it was recorded in the project's defect catalog (if one is
  configured).
- Confirmation the notes are **jargon-clean** and **version-correct**.
- Whether this release was illustrated (Step 3.5) — which features got an
  image, which were skipped/reused and why, or that no illustration skill
  is configured for this project.
- Links to `release-notes.md` (the deliverable), `release-notes.pdf` (the
  same content, self-contained and shareable as an attachment), and
  `release-crosswalk.md` (internal).
- **Under auto-pilot:** also list every `DECIDED-AUTO` entry from this run —
  "Decided automatically (auto-pilot): N items — see decisions.md."

🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧 — **SHIP gate.**
Then ask whether the user wants to send the notes, edit them, or hold.
**Under auto-pilot,** skip the ask: report the notes as finalized and ready
to send instead of waiting — this skill still never transmits anything
itself in any mode, so "proceeding" here just means not blocking on the
question.

### Re-entry passes (re-running a version already drafted)
Most real releases take **more than one pass** — a SHIP-gate hold while a
decision is pending, a late scope change, a redraft after the user answers.
A re-entry pass is
this same process with a different input contract, not a from-scratch rerun:
- **Inputs:** the version's prior `release-crosswalk.md` and its prior
  release-log row(s) — the latest row's Status token (`HOLD — <reason>` /
  `CLEARED` / `SENT <date>`) is the state being resumed. Do not re-run the
  scribe over the whole release; run it only for targeted redrafts (the
  lead→scribe→lead loop in Step 3).
- **The lead applies its delta-verification rule** (see release-lead.md):
  prior ✓ marks + git-confirmed unchanged commit set → verify only the
  delta plus a full jargon re-sweep; a moved range or missing marks → full
  from-scratch verification, as on a first pass.
- **Every pass appends its own release-log row** (latest row per version
  wins); the pass that resolves a hold sets `CLEARED`/`SENT` and performs
  the released write-back to each item's `build-report.md`
  (release-lead.md, "What you produce").

## Decision logging
If a genuine choice goes to the user during a release (e.g. "bundle these two
versions into one note or keep them separate?", "include the internal item
the client never sees, or omit it?"), record it: mirror the per-request
`decisions.md` pattern used by the other teams, under the release's output
folder as `decisions.md`, and note it in the release-log row. Write PENDING
before asking, DECIDED after.

## Conventions
- **Human gates must be visible, not just asked.** At every 🟧 HUMAN GATE
  REQUIRED point, present the question as its own standalone callout in the
  actual chat reply — **include the literal `🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧`
  banner line**, not just the blockquote underneath it:

  > 🟧🟧🟧 HUMAN GATE REQUIRED 🟧🟧🟧
  >
  > **Human decision needed:** <the question>

  Never fold a gate's question into a narrative summary paragraph where it
  reads as background rather than a stop-and-wait point. If more than one gate
  applies in the same report-back, each gets its own banner + callout — do not
  merge them into a single generic "want me to proceed?".
- **When a gate offers a choice in plain chat text (not via `AskUserQuestion`),
  letter the options** — `**A)**`, `**B)**`, `**C)**`, etc. — so the user can
  answer with a single letter instead of re-describing the option. A gate
  with only one path (a plain yes/no "proceed?") doesn't need lettering —
  this is for genuine multi-way choices.
- **Input:** a version label and/or the folders/builds it covers — provided
  by the user; the skill asks if omitted. Do not write notes without a
  confirmed scope.
- **Output per release:** `<release-docs-root>/<version>/` (per
  `PROJECT-CONTEXT.md`, or the generic default) containing `release-notes.md`
  (client-facing), `release-notes.pdf` (same content, self-contained,
  Step 3.6), `release-crosswalk.md` (private), optionally `decisions.md`,
  and — only for projects with a configured illustration skill — an
  `images/` folder of feature screenshots referenced from the notes.
- **Templates:** `~/.claude/skills/team-release/templates/` — Step 2 seeds
  both documents from them; they are the structural standard.
- **Scripts:** `~/.claude/skills/team-release/scripts/` —
  `verify_commits.py` (per-SHA existence/ancestry/date/diffstat + a `range`
  sweep; the mechanical half of the lead's fact-check),
  `jargon_lint.py` (the regex half of the jargon sweep),
  `append_release_log_row.py` (the only way release-log rows are written),
  and `render_release_pdf.py` (Step 3.6 — markdown + embedded local images
  → a self-contained client PDF via headless Chrome; generic, no
  project-specific dependency, requires the `markdown` pip package and a
  local Chrome/Chromium install).
- **Memory:** the release-log location comes from `PROJECT-CONTEXT.md` if the
  project names one; otherwise
  `~/.claude/skills/team-release/memory/release-log.md` (a cross-project
  fallback, append-only). One row per release-lead pass, latest row per
  version wins; each row carries a Status token (`HOLD — <reason>` /
  `CLEARED` / `SENT <date>`) and a crosswalk link.
- **Client firewall:** the client only ever sees `release-notes.md`. The
  shared rule set lives at
  `~/.claude/skills/team-release/references/client-firewall.md` (one list,
  shared with `intake-client-liaison`); item codes, internal ids, file
  paths, commit hashes, and tooling words live in the crosswalk, never in
  the notes.
- This skill is READ + verify only for product code; it writes only the
  release docs and its own memory. It does not commit, push, or send.

## The recurring trap this skill exists to catch
**A release note that lies — by commission or omission — or that leaks
internal shorthand.** Build-reports are *claims* as of when they were
written; the scribe drafts from them, and the lead checks them against the
*commits*, which are facts. Never tell the client a change shipped when it's
uncommitted or was backed out; never omit a shipped client-visible change;
never let an item code or file path reach a client document. If the notes
haven't been reconciled against `git`, they aren't done.

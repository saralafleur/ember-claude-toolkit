---
name: team-release
description: 'Run a small virtual release team (release-scribe, release-lead) over everything that shipped in a version and produce a client-facing release-notes.md — on any project. Use when: one or more team-build runs are done (verified green) and you want to tell the client what changed; you are cutting a version and need plain-language notes for a non-technical client; you want to bundle several work items into ONE client release doc; or you need release notes that are fact-checked against the actual shipped commits, not just what a report claimed. Produces a client-facing release-notes.md plus a private crosswalk mapping every note back to its item/commit/decision, and remembers each release in a release-log.'
argument-hint: 'A version label (e.g. v0.7.3) and/or the folder(s) holding the shipped work. Optional — the skill will ask what is in the release if omitted.'
---

# Team Release

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

> **How to invoke each role:** launch each with `subagent_type: "<name>"`
> (e.g. `subagent_type: "release-scribe"`). Give each: the version label, the
> list of shipped items with their artifact paths, and the output dir. (If a
> name isn't a subagent type, fall back to `general-purpose` and paste the
> role brief from `~/.claude/agents/<name>.md`.)

## Process

### Step 0 — Establish the release scope (what shipped in this version)
A release note is scoped to a **version**, which may bundle several work
items.
- Check `PROJECT-CONTEXT.md` for this project's version source of truth and
  where its delivery-pipeline artifacts (intake/build folders) live. If the
  user gave a version and/or folders, use them; otherwise ask: "What's in
  this release? Give me the version and the folder(s) or build(s) it covers."
- Determine the version from the project's version source of truth (per
  `PROJECT-CONTEXT.md`) unless the user names one.
- Enumerate the **work items** in the release: each item's intake/build
  folder and its `build-report.md`. Confirm each item was actually built (a
  green build-report), and gather the commit range per repo touched.
- Do not invent scope. If it's unclear which items belong to this version,
  ask.

### Step 1 — Set up the output location
Check `PROJECT-CONTEXT.md` for this project's convention on where release
docs live; if none is configured, write to `<project-root>/releases/<version>/`
(create it) and note that you used the generic default. If the user names a
different location, use it. **Never** scatter release notes inside a single
item's build folder — a release spans items.

### Step 2 — Draft the client notes
Run `release-scribe` with the version, the item list + artifact paths, and
the output dir. It reads every item's build-report / plan / decisions and
writes:
- `release-notes.md` (client-facing draft)
- `release-crosswalk.md` (private: each note → item/commit/decision)

### Step 3 — Fact-check + finalize (gate)
Run `release-lead`. It verifies every client-facing claim against the
**actual git commits** in the release range (over-claim → cut/return;
shipped-but-omitted → add), sweeps `release-notes.md` for any leaked internal
jargon (including this project's own defect-catalog/decision-id patterns, if
`PROJECT-CONTEXT.md` names any), confirms the version/date, finalizes the
notes, updates the crosswalk with its verification result per note, and
appends a row to the release-log.
- If the lead finds a client claim **no commit supports**, that's a gate —
  the notes do not ship with a false claim. Fix the wording or drop the line.

### Step 4 — Report back
Summarize for the user in chat:
- The **version** and the **items** bundled into it.
- The client-facing headline (2–3 lines of what the client will see).
- Any claim the lead **cut or added** during fact-check, and why.
- Confirmation the notes are **jargon-clean** and **version-correct**.
- Links to `release-notes.md` (the deliverable) and `release-crosswalk.md`
  (internal).
Then ask whether the user wants to send the notes, edit them, or hold.

## Decision logging
If a genuine choice goes to the user during a release (e.g. "bundle these two
versions into one note or keep them separate?", "include the internal item
the client never sees, or omit it?"), record it: mirror the per-request
`decisions.md` pattern used by the other teams, under the release's output
folder as `decisions.md`, and note it in the release-log row. Write PENDING
before asking, DECIDED after.

## Conventions
- **Input:** a version label and/or the folders/builds it covers — provided
  by the user; the skill asks if omitted. Do not write notes without a
  confirmed scope.
- **Output per release:** `<release-docs-root>/<version>/` (per
  `PROJECT-CONTEXT.md`, or the generic default) containing `release-notes.md`
  (client-facing), `release-crosswalk.md` (private), and optionally
  `decisions.md`.
- **Templates:** `~/.claude/skills/team-release/templates/`.
- **Memory:** the release-log location comes from `PROJECT-CONTEXT.md` if the
  project names one; otherwise
  `~/.claude/skills/team-release/memory/release-log.md` (a cross-project
  fallback, append-only).
- **Client firewall:** the client only ever sees `release-notes.md`. Item
  codes, internal ids, file paths, commit hashes, and tooling words live in
  the crosswalk, never in the notes.
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

# Release Crosswalk — <version>  ·  INTERNAL — DO NOT SEND TO CLIENT

> Private map from every client-facing line in `release-notes.md` back to the internal
> source: the work item, the commit(s) that shipped it, and any decision id. This is
> how the team audits that the notes are true and complete — and the primary input a
> later release-lead re-entry pass resumes from. The client never sees this.
> (The release-log row links here; the verification NARRATIVE lives in this file,
> the log row stays one terse line.)

**Version:** <version> · **Cut:** <YYYY-MM-DD> · **Release folder:** <path>
**Repos / commit ranges:** `<repo>` `<base>..<head>` · `<repo>` `<...>` · … (lead-verified —
any range handed down at Step 0 is a hint until the lead re-derives it)

---

| # | Client note (short) | Internal item | Commit(s) | Decision | Lead verification |
|---|---------------------|---------------|-----------|----------|-------------------|
| 1 | <e.g. Social Media list now correctly numbered> | <item slug + artifact path> | — | <DEC-… or —> | <✓ backed / ✗ removed / + added> |
| 2 | <…> | <…> | — | <…> | <…> |

> **The Commit(s) column is lead-owned.** The scribe cites artifacts only
> (build-report path, decision ids) and writes `—`; the release-lead fills the
> commits during verification, from git (`verify_commits.py`) — never
> hand-copied from a build-report.

## Flags for the release-lead (scribe → lead channel)
> Anything the scribe could not assert from the artifacts alone: ambiguous merge
> status, a claim a build-report only implies, a judgment call the lead should
> re-decide. Mark CRITICAL where a client claim depends on it.
- <flag, or "none">

## Shipped-but-intentionally-silent (not in the client notes)
> Commits in the release range that are correctly NOT mentioned to the client, with why.
- `<hash>` — <e.g. version bump / internal test-hardening the client never sees>.

## Per-item verification narrative (lead)
> The lead's working evidence, per item: what was re-run, what the diffs showed,
> what was re-decided, send-backs to the scribe and their outcomes. This section —
> not the release-log row — is where the narrative belongs.
- **<item>:** <…>

## Lead reconciliation summary
- Claims cut (no supporting commit): <list or none>
- Client-visible changes added (were missing from the draft): <list or none>
- Send-backs to the scribe (lead→scribe→lead loop): <list or none>
- Jargon-leak sweep: <clean / fixed N> (mechanical half via `jargon_lint.py`)
- QA-debt / `GREEN-WITH-CAVEATS` on any bundled item: <none / item + caveat — surfaced at the SHIP gate>
- Version/date check vs this project's version source of truth: <ok / corrected>
- Status this pass: <HOLD — <reason> / CLEARED / SENT <YYYY-MM-DD>> (mirrors this pass's release-log row)

# Release Crosswalk — <version>  ·  INTERNAL — DO NOT SEND TO CLIENT

> Private map from every client-facing line in `release-notes.md` back to the internal
> source: the work item, the commit(s) that shipped it, and any decision id. This is
> how the team audits that the notes are true and complete. The client never sees this.

**Version:** <version> · **Cut:** <YYYY-MM-DD> · **Release folder:** <path>
**Repos / commit ranges:** `<repo>` `<base>..<head>` · `<repo>` `<...>` · … (one per repo this release touched)

---

| # | Client note (short) | Internal item | Commit(s) | Decision | Lead verification |
|---|---------------------|---------------|-----------|----------|-------------------|
| 1 | <e.g. Social Media list now correctly numbered> | <e.g. UAT 7626 items 6/7> | `<hash>` | <DEC-… or —> | <✓ backed / ✗ removed / + added> |
| 2 | <…> | <…> | `<hash>` | <…> | <…> |

## Shipped-but-intentionally-silent (not in the client notes)
> Commits in the release range that are correctly NOT mentioned to the client, with why.
- `<hash>` — <e.g. version bump / internal test-hardening the client never sees>.

## Lead reconciliation summary
- Claims cut (no supporting commit): <list or none>
- Client-visible changes added (were missing from the draft): <list or none>
- Jargon-leak sweep: <clean / fixed N>
- Version/date check vs this project's version source of truth: <ok / corrected>

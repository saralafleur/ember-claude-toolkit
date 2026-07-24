# Durable authority guardrails (standing)

Apply when a request involves webhooks, idempotent event processing, retry/DLQ
queues, or delayed destructive work (cleanup, purge, retention). Architect +
tech-lead + QA risk must mark each trap **PASS / FAIL / N/A**.

Do **not** over-correct stack choices that already converge (e.g. prefer a
durable queue over in-process timers). Focus on **where authority lives**.

| Trap | Pass looks like |
|------|-----------------|
| Dedupe authority | Durable unique ledger on event id (DB unique / equivalent); cache (Redis TTL) is optional accelerator only — never sole arbiter |
| Cancel authority | Pending schedule is a durable row/state; fire path re-checks before destroy; queue `remove()` is best-effort, not SSOT |
| Concurrent claim | Atomic set-if-not-exists (unique insert or `SET NX`); named concurrent-duplicate test — not check-then-write |
| Raw-body / verify boundary | Provider signature verified over raw bytes; regression: still verifies with a global JSON body parser also mounted |

## Decisions rule (triage / PM / orchestrator)

`decisions.md` must not be empty when the ask has silent product forks. Prefer
load-bearing product ambiguities over vendor shopping:

- What counts as reactivation / reverse of the destructive path?
- Does the reverse unlock / restore access?
- Soft vs hard delete (or equivalent irreversibility)?
- Retry-count semantics (N retries vs N total attempts)?
- Cache vs durable store as idempotency authority?

Vendor/SDK brand (mailer, object store) is non-blocking unless it changes design.
Pin a default with rationale when proceeding; still record the DEC entry.

## Definition of Done — delayed destruction

> Schedule is a durable row; cancel flips state; fire path deletes/destroys only if still pending.

Reject plans that treat “we’ll cancel the queue job” as sufficient without that sentence.

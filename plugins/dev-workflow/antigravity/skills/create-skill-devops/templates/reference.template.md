# {{command}} — {{environment name}} setup procedure

Goal: from any starting state, end with a machine that can {{build/run the
project}}, proven by {{the smoke test — a real build, service boot, etc.}}.

## Phase 1 — Audit (always first, read-only)

Run the audit script (at `scripts/{{command}}-check.sh` under this skill's
base directory) and show the user the table:

```bash
zsh <skill-base-dir>/scripts/{{command}}-check.sh
```

If every build-relevant row is `ok`, report "environment is already set up",
offer the Phase 4 smoke test as proof, and stop.

If invoked in status-only mode (bare `/devops`), stop after showing the table.

## Phase 2 — Plan

From the audit, list only the missing/wrong items, in dependency order, with
sizes. Template:

| Step | Size / time | Interactive? |
|---|---|---|
| {{Install X}} | {{~N GB download, ~N min}} | {{Yes — account/sudo / No}} |

Check disk space against the largest install. Confirm with the user before
starting any large download.

## Phase 3 — Install

Only run the steps the audit flagged. Every step is idempotent.

### 3.1 {{Step name}} (if `{{audit-key}}` MISSING)

{{Commands. Non-interactive → run directly, long ones in the background.
Interactive (sudo, account login) → give the user the `!`-prefixed command
and wait; never script around a login.}}

## Phase 4 — Verify (smoke test)

Re-run the audit script — all build-relevant rows must be `ok`. Then prove
the environment with the most real check available:

1. {{Cheapest structural proof — e.g. SDK/version listing.}}
2. {{Runtime proof — e.g. boot a simulator/container/service.}}
3. **Real build (best proof):** if the project's app/build target exists,
   build or run it. Don't scaffold throwaway projects into the project
   folders; use the scratchpad directory if a synthetic proof is needed.

Report the result plainly: what was proven, what wasn't.

## Notes

{{Constraints worth remembering: account tiers needed, version pinning,
platform quirks, history on this machine.}}

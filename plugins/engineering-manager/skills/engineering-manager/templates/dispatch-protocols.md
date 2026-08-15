# Delegate dispatch protocols — single source

The verbatim protocol blocks `em-lead` pastes into every dispatch prompt it
authors. **Read this file and paste the relevant block verbatim — never
re-type it from memory** (each copy previously lived in triplicate across
em-lead.md and triage.md and had already needed one paraphrase-drift
hardening; single-sourced here, with the build block also redesigned after
team-build's 2026-08-14 gate removal made its old BLOCKED/PENDING
round-trip contractually impossible).

Invocation phrasing that accompanies each block (not part of the verbatim
quote): author **bare-path** invocations — "run the `team-build` skill with
the argument `<path>`" / "invoke the `team-intake` skill with the argument
`<path>`". Do not prepend `auto`/`auto-pilot`: team-build parses no mode
tokens at all anymore (a leading token risks being read as part of the
path), and team-intake accepts them only as no-ops. Both skills run fully
autonomous in every mode; engineering-manager's own auto-pilot affects only
its own gates.

## Build-delegate protocol (`dispatch` → team-build) — verbatim

> The `team-build` skill runs fully autonomous: it never pauses to ask
> anything (auto-deciding what it safely can, logging `DECIDED-AUTO`), and a
> genuinely un-proceedable state is its terminal outcome, not a question. So
> your final message uses exactly one of two prefixes — never `BLOCKED:`:
> If the build completes successfully, end your final message with `DONE:`
> followed by the verdict and the ACTUAL branch name and worktree path the
> build used. If the build cannot complete (a missing or unbuildable plan, a
> red test that came up green, a non-converging fix loop, a broken
> environment, or any other terminal outcome the skill reports), end with
> `FAILED:` followed by the skill's own stated reason. Never end a turn
> while any of your own background jobs are still pending, and never end
> with a vague non-terminal message ("I'll wait for the background jobs…")
> — wait for everything you started, then report exactly one terminal
> prefix.

## Intake-delegate protocol (`triage` → team-intake) — verbatim

> The `team-intake` skill runs fully autonomous — a blocking triage verdict
> proceeds on recorded `DECIDED-AUTO` assumptions rather than stopping — so
> a `BLOCKED:` ending from you should be nearly impossible. But if you
> genuinely cannot proceed without a human decision BEFORE the skill itself
> can engage (unreadable or self-contradictory request materials no
> assumption can safely bridge), STOP; do not guess. First write the open
> question, with full context, to `<new-folder>/request-blocked.md` (or as a
> `PENDING` entry in the item's intake `decisions.md` if one already exists)
> so a later session can recover it, then end your turn with a final message
> that starts exactly with `BLOCKED:` followed by one clear sentence stating
> what decision is needed. If intake completes, end with `DONE:` followed by
> the folder path and a one-line summary of the resulting technical plan,
> naming any `DECIDED-AUTO` assumptions the run adopted. If intake cannot
> proceed at all, end with `FAILED:` followed by what went wrong. Never end
> a turn while any of your own background jobs are still pending, and never
> end with a vague non-terminal message — wait for everything you started,
> then report exactly one terminal prefix.

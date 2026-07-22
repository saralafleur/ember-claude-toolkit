---
name: devops
argument-hint: "[{{command}} | status]"
description: >
  {{PROJECT}}'s DevOps toolbox — commands for setting up and verifying this
  project's build environments. Use when the user types "/devops", or asks to
  set up, check, or repair a build environment for {{PROJECT}}. Current
  commands: `{{command}}` — {{one-line command summary}}; `status` —
  read-only report of the current state of everything the devops skill
  manages. Invoking with no command lists available commands and runs the
  status report.
---

# DevOps Skill — {{PROJECT}}

A command-based toolbox for build-environment setup. Each command follows the
same discipline:

1. **Audit first** — run the read-only check script and show current state.
2. **Plan** — list exactly what's missing, with download sizes and disk
   requirements, before installing anything.
3. **Install** — run non-interactive steps directly. For steps needing a
   login or `sudo`, give the user the exact command prefixed with `!` so
   they can run it in-session (e.g. `! sudo xcode-select -s ...`).
4. **Verify** — prove the environment works end-to-end, don't just assume
   installs succeeded.

Never install anything before showing the audit and plan. All installs must be
idempotent — re-running a command on a healthy environment should report
"already set up" and change nothing.

## Command routing

Parse the argument after `/devops`:

| Argument | Command |
|---|---|
| `{{command}}` | {{Command title}} — follow `references/{{command}}.md` |
| `status` | Report current state of everything this skill manages — follow `references/status.md` |
| *(none)* | List commands, then run the `status` command |

Unknown argument → list available commands, suggest the closest match.

## Commands

### {{command}}

{{What it sets up, 2-3 lines.}} Full procedure in
`references/{{command}}.md`; audit script at `scripts/{{command}}-check.sh`
(run it relative to this skill's base directory).

### status

Read-only report of the current state of everything the devops skill
manages. Runs every audit script in `scripts/` (so new commands are picked
up automatically) and gives a per-command verdict plus what to run to fix
anything unhealthy. Never installs or changes anything. Procedure in
`references/status.md`.

## Adding new commands

New commands get: a row in the routing table, a section here, a procedure doc
in `references/<command>.md`, an entry in the frontmatter `argument-hint`,
and a read-only audit script in `scripts/<command>-check.sh` — the audit
script is what makes the command show up in `status`. Keep the
audit/plan/install/verify structure.

#!/usr/bin/env python3
"""
Canonical engineering-manager run-log row author -- the WRITE half of the
script API for dispatch-run-log.md (either a project-specific log named in
PROJECT-CONTEXT.md, or the cross-project fallback at
~/.claude/skills/engineering-manager/memory/dispatch-run-log.md).

The orchestrator calls this at Step 8 of `dispatch`/`triage` instead of
hand-typing a markdown table row, so the row is correct by construction:
exactly 7 columns, every field's embedded `|` and newlines escaped, each
field capped at a fixed length, appended at the true end of the file, then
re-parsed as a self-check. Mirrors team-qa's add_qa_run_log_row.py.

Provenance: 2026-08-14 workflow-audit (scriptability finding 1 /
artifact-contract A1-A5): the hand-typed log's declared one-row grammar
broke mid-file and stayed broken -- table rows gave way to free-form `##`
sections; an orphaned Outcome paragraph attached itself below the wrong
entry; row size and per-entry verbosity grew sharply over time, projecting
a 256 KB Read-cap crossing if left unchecked. Same trajectory as the
team-build/team-qa/team-intake run-log incidents this script family exists
to prevent.

The orchestrator still composes the content -- decision, outcomes, lessons.
Durable, project-invariant lessons do NOT belong in a row: promote them to
memory/standing-constraints.md so future runs actually read them.

Usage:
    append_em_run_log_row.py <file> --date 2026-08-15 --command dispatch \
        --target "Acme/app/intake" \
        --housekeeping "none this run" \
        --decision "SEQUENTIAL 2 items (LOW -> panel unanimous): shared coach_dev_test DB" \
        --needs-human "3 named, none dispatched" \
        --outcomes "both DONE + MERGED; merge commits abc123, def456"

Creates the file (with the standard header + table) if it doesn't exist yet.
Warns (does not block) when the file exceeds ~50 KB -- see the header's
rotation rule.
"""
import argparse
import os
import sys

MAX_FIELD_LEN = 500  # bytes; mechanical backstop -- the primary lever is the
                     # "keep it terse, promote durable lessons" instruction
                     # in the references. Truncated fields get a marker.

ROTATE_WARN_BYTES = 50 * 1024

HEADER = """# Engineering-Manager Dispatch Run Log

> Appended only via `scripts/append_em_run_log_row.py` -- never hand-typed.
> One row per `dispatch` or `triage` run, exactly 7 columns. Substantive
> narrative belongs in that run's `.em-state/<run>/` plan and the item's own
> decisions.md, not here. Durable project-invariant lessons go to
> `memory/standing-constraints.md` (which em-analyst reads every run), not
> into a row. Rotation: when this file exceeds ~50 KB, move rows older than
> the current month to `archive/dispatch-run-log-<YYYY-MM>.md` (same
> header), keeping them greppable, never deleted.

| Date | Command | Target | Housekeeping | Decision + items | NEEDS-HUMAN | Outcomes |
|---|---|---|---|---|---|---|
"""

FIELDS = ["date", "command", "target", "housekeeping", "decision",
          "needs_human", "outcomes"]


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written): {msg}\n")
    sys.exit(1)


def escape_cell(value):
    """Make a value safe to sit inside one markdown table cell."""
    value = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    value = value.replace("|", "\\|")
    value = " ".join(value.split())  # collapse repeated whitespace
    if len(value) > MAX_FIELD_LEN:
        value = value[: MAX_FIELD_LEN - 1].rstrip() + "…"
    return value


def count_columns(line):
    """Count cells in a markdown table row, respecting escaped pipes."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    cells = []
    current = ""
    i = 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            current += "|"
            i += 2
            continue
        if body[i] == "|":
            cells.append(current)
            current = ""
            i += 1
            continue
        current += body[i]
        i += 1
    cells.append(current)
    return len(cells)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--command", required=True,
                    help='"dispatch" or "triage"')
    ap.add_argument("--target", required=True)
    ap.add_argument("--housekeeping", required=True,
                    help='housekeeping summary, or "—" for a dispatch run')
    ap.add_argument("--decision", required=True,
                    help="grouping decision + items + one-line why")
    ap.add_argument("--needs-human", required=True,
                    help='e.g. "4 named, none dispatched", or "—"')
    ap.add_argument("--outcomes", required=True,
                    help="per-item outcomes, merge commits if any")
    args = ap.parse_args()

    if args.command not in ("dispatch", "triage"):
        die(f'--command must be "dispatch" or "triage", got {args.command!r}')

    exists = os.path.exists(args.file)
    if not exists:
        content = HEADER
    else:
        content = open(args.file, encoding="utf-8").read()

    raw = {
        "date": args.date,
        "command": args.command,
        "target": args.target,
        "housekeeping": args.housekeeping,
        "decision": args.decision,
        "needs_human": args.needs_human,
        "outcomes": args.outcomes,
    }
    cells = [escape_cell(raw[f]) for f in FIELDS]
    row = "| " + " | ".join(cells) + " |"

    if count_columns(row) != 7:
        die(f"assembled row did not come out to 7 columns (got "
            f"{count_columns(row)}) -- this is a bug in this script, not "
            f"your input: {row!r}")

    if not content.endswith("\n"):
        content += "\n"
    content += row + "\n"

    with open(args.file, "w", encoding="utf-8") as f:
        f.write(content)

    # Self-check: re-read the file, confirm the last non-empty line is our
    # row and it parses back to exactly 7 columns.
    written = open(args.file, encoding="utf-8").read()
    last_line = [ln for ln in written.splitlines() if ln.strip()][-1]
    if last_line != row or count_columns(last_line) != 7:
        die(f"self-check FAILED after write -- inspect {args.file} "
            f"(expected last line {row!r}, found {last_line!r}); "
            "the file WAS modified")

    size = os.path.getsize(args.file)
    print(f"Added row to {args.file} :: {args.date} / {args.command} / "
          f"{args.target} (7 columns, self-check passed)")
    if size > ROTATE_WARN_BYTES:
        print(f"WARNING: {args.file} is {size} bytes (> ~50 KB) -- rotate "
              f"rows older than the current month to "
              f"archive/dispatch-run-log-<YYYY-MM>.md per the header rule.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Canonical status run-log row author -- the WRITE half of the script API for
status-run-log.md (either a project-specific one, or the cross-project
fallback at ~/.claude/skills/team-status/memory/status-run-log.md).

status-lead calls this instead of hand-typing a markdown table row, so the
row is correct by construction: exactly 7 columns, every field's embedded
`|` and newlines escaped, and each field capped at a fixed length so one
verbose run can't blow up the file's growth rate. (Audit finding, workflow-
audit 2026-08-14: 3 of 67 hand-typed rows had broken column counts from
unescaped `|`, one pair of rows was glued together with no newline, and
per-row size tripled month-over-month -- July avg ~1.5KB/row, August avg
~4.7KB/row, max 9,699 chars -- against a "one line" contract.)

Ported from team-qa/scripts/add_qa_run_log_row.py (same discipline as
team-decisions/add_decision.py): after writing, the file is re-parsed and
the run FAILS if the new row is not exactly 7 columns.

Usage:
    add_status_run_log_row.py <file> --date 2026-08-15 --project my-app \
        --target "/abs/path/to/intake" \
        --items "5 (2 rescanned, 3 cached)" \
        --verdict "All merged; 1 DOC CLEANUP residual" \
        --next-action "team-qa on intake/2026-08-10-foo -- coverage gap" \
        --gates "scan:flagged-only(auto) / proceed:A / parallel:none / corrections:2 applied"

Keep --verdict and --next-action to headline facts only (<=400 chars each,
enforced); the full story belongs in the run's status-report.md, which the
target path already locates.

Creates the file (with the standard header + table) if it doesn't exist yet.
"""
import argparse
import os
import sys

MAX_FIELD_LEN = 400  # chars; the hard length bound from the 2026-08-14
                     # workflow audit (quick win 8) -- headline facts only,
                     # link to status-report.md instead of inlining detail.
                     # Truncated fields get a marker.

HEADER = """# Status Run Log (project-specific)

> Appended only via `add_status_run_log_row.py` -- never hand-typed. See
> `~/.claude/skills/team-status/memory/status-run-log.md`'s own header for
> the rotation/grep-scoping conventions this file follows too.

| Date | Project | Target | Items scanned | Overall verdict | Recommended next action | Gate answers |
|------|---------|--------|----------------|------------------|--------------------------|--------------|
"""

FIELDS = ["date", "project", "target", "items", "verdict", "next_action", "gates"]
N_COLS = len(FIELDS)


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
    ap.add_argument("--project", required=True)
    ap.add_argument("--target", required=True, help="absolute target folder path")
    ap.add_argument("--items", required=True,
                    help='e.g. "38 (2 rescanned in 1 wave, 36 cached)" -- '
                         'include wave structure whenever the scan set '
                         'exceeded the ~8-10 fan-out cap')
    ap.add_argument("--verdict", required=True, help="headline only, <=400 chars")
    ap.add_argument("--next-action", dest="next_action", required=True,
                    help="headline only, <=400 chars; the report has the detail")
    ap.add_argument("--gates", required=True,
                    help='one word per gate answer, e.g. "scan:flagged-only(auto) '
                         '/ proceed:A / parallel:A / corrections:2 applied, 1 declined" '
                         '-- or "n/a (fully cached)"')
    args = ap.parse_args()

    exists = os.path.exists(args.file)
    if not exists:
        content = HEADER
    else:
        content = open(args.file, encoding="utf-8").read()

    raw = {f: getattr(args, f) for f in FIELDS}
    cells = [escape_cell(raw[f]) for f in FIELDS]
    row = "| " + " | ".join(cells) + " |"

    if count_columns(row) != N_COLS:
        die(f"assembled row did not come out to {N_COLS} columns (got "
            f"{count_columns(row)}) -- this is a bug in this script, not "
            f"your input: {row!r}")

    if not content.endswith("\n"):
        content += "\n"
    content += row + "\n"

    with open(args.file, "w", encoding="utf-8") as f:
        f.write(content)

    # Self-check: re-read the file, confirm the last non-empty line is our
    # row and it parses back to exactly N_COLS columns.
    written = open(args.file, encoding="utf-8").read()
    last_line = [ln for ln in written.splitlines() if ln.strip()][-1]
    if last_line != row or count_columns(last_line) != N_COLS:
        die(f"self-check FAILED after write -- inspect {args.file} "
            f"(expected last line {row!r}, found {last_line!r}); "
            "the file WAS modified")

    print(f"Added row to {args.file} :: {args.date} / {args.project} "
          f"({N_COLS} columns, self-check passed)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Canonical QA run-log row author -- the WRITE half of the script API for
qa-run-log.md (either a project-specific one, or the cross-project fallback
at ~/.claude/skills/team-qa/memory/qa-run-log.md).

qa-strategist calls this instead of hand-typing a markdown table row, so the
row is correct by construction: exactly 8 columns, every field's embedded
`|` and newlines escaped, and each field capped at a fixed length so one
verbose run can't blow up the file's growth rate. (Audit finding, workflow-
audit 2026-08-14: 6 of 86 hand-typed rows had broken column counts from
unescaped `|` in embedded code/regex fragments, and per-row size nearly
tripled over the log's first month with no length guard.)

After writing, the file is re-parsed and the run FAILS if the new row is not
exactly 8 columns -- the self-check that keeps this script honest against
its own format definition (same discipline as team-decisions/add_decision.py).

Usage:
    add_qa_run_log_row.py <file> --date 2026-08-14 --project my-app \
        --slug fix-auth-bug --surfaces "login, session refresh" \
        --verdict "GAPPED" --gaps "session refresh has no expiry test" \
        --recurring "No — first instance" \
        --link "/path/to/qa/2026-08-14-fix-auth-bug/"

Creates the file (with the standard header + table) if it doesn't exist yet.
"""
import argparse
import os
import sys

MAX_FIELD_LEN = 500  # bytes; a mechanical backstop, not the primary lever —
                      # the primary lever is the "keep it terse" instruction
                      # in qa-strategist.md. Truncated fields get a marker.

HEADER = """# QA Run Log (project-specific)

> Appended only via `add_qa_run_log_row.py` — never hand-typed. See
> `~/.claude/skills/team-qa/memory/qa-run-log.md`'s own header for the
> rotation/grep-scoping conventions this file follows too.

| Date | Project | Slug | Surfaces | Coverage verdict | Gaps found | Recurring? | Link |
|------|---------|------|----------|-------------------|-----------|-----------|------|
"""

FIELDS = ["date", "project", "slug", "surfaces", "verdict", "gaps", "recurring", "link"]


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
    # Split on unescaped pipes only.
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
    ap.add_argument("--slug", required=True)
    ap.add_argument("--surfaces", required=True)
    ap.add_argument("--verdict", required=True,
                     help='e.g. "ADEQUATE", "GAPPED", "BLIND", or a compound '
                          'form like "BLIND (pre-build) -> projected ADEQUATE once X lands"')
    ap.add_argument("--gaps", required=True)
    ap.add_argument("--recurring", required=True)
    ap.add_argument("--link", required=True)
    args = ap.parse_args()

    exists = os.path.exists(args.file)
    if not exists:
        content = HEADER
    else:
        content = open(args.file, encoding="utf-8").read()

    raw = {
        "date": args.date,
        "project": args.project,
        "slug": args.slug,
        "surfaces": args.surfaces,
        "verdict": args.verdict,
        "gaps": args.gaps,
        "recurring": args.recurring,
        "link": args.link,
    }
    cells = [escape_cell(raw[f]) for f in FIELDS]
    row = "| " + " | ".join(cells) + " |"

    if count_columns(row) != 8:
        die(f"assembled row did not come out to 8 columns (got "
            f"{count_columns(row)}) -- this is a bug in this script, not "
            f"your input: {row!r}")

    if not content.endswith("\n"):
        content += "\n"
    content += row + "\n"

    with open(args.file, "w", encoding="utf-8") as f:
        f.write(content)

    # Self-check: re-read the file, confirm the last non-empty line is our
    # row and it parses back to exactly 8 columns.
    written = open(args.file, encoding="utf-8").read()
    last_line = [ln for ln in written.splitlines() if ln.strip()][-1]
    if last_line != row or count_columns(last_line) != 8:
        die(f"self-check FAILED after write -- inspect {args.file} "
            f"(expected last line {row!r}, found {last_line!r}); "
            "the file WAS modified")

    print(f"Added row to {args.file} :: {args.date} / {args.project} / "
          f"{args.slug} (8 columns, self-check passed)")


if __name__ == "__main__":
    main()

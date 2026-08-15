#!/usr/bin/env python3
"""
Canonical wrap-up run-log row author -- the WRITE half of the script API for
~/.claude/skills/wrap-up/memory/wrap-up-log.md.

wrap-up Step 7 calls this instead of hand-typing a markdown table row, so the
row is correct by construction: exactly 7 columns, every field's embedded
`|` and newlines escaped, and each field capped at a fixed length so one
verbose run can't blow up the file's growth rate. (Audit finding, workflow-
audit 2026-08-14: 270 hand-typed rows had drifted into 4 syntaxes and 2
delimiters under a producer spec that contradicted itself on the field
count; 7 rows were invisible to any |-anchored grep, and the file breached
the 256 KB Read cap on 2026-08-09.)

After writing, the file is re-parsed and the run FAILS if the new row is not
exactly 7 columns -- the self-check that keeps this script honest against
its own format definition (same discipline as team-qa/add_qa_run_log_row.py,
which this is cloned from).

Usage:
    append_wrap_up_log_row.py [<file>] --date 2026-08-15 --project my-app \
        --repo /path/to/repo --branch "effort/2026-08-15-foo" \
        --merge-commit abc1234 \
        --summary "One-to-two-sentence summary of what shipped" \
        --deferred "none"

<file> defaults to ~/.claude/skills/wrap-up/memory/wrap-up-log.md.
Creates the file (with the standard header + table) if it doesn't exist yet
-- header creation lives HERE, not in a template (the old
templates/wrap-up-log-header.md reference was a dead path).

Deferred/aborted runs still get a row: put the STOP reason in --deferred
(e.g. "run aborted at Step 5 merge conflict; merge --abort run, branch left
unmerged") so the log's "when did I last close this out" purpose includes
the runs that most need follow-up.
"""
import argparse
import os
import sys

DEFAULT_FILE = os.path.expanduser("~/.claude/skills/wrap-up/memory/wrap-up-log.md")

MAX_FIELD_LEN = 500  # bytes; a mechanical backstop, not the primary lever —
                      # the primary lever is the one-to-two-sentence summary
                      # cap in SKILL.md Step 7. Truncated fields get a marker.

HEADER = """# Wrap-up Log (cross-project)

> One row per `/wrap-up` run, across every project. Exists so "when did I
> last close this out" never requires re-deriving it from `git log` across
> a dozen repos.
> Appended only via `../scripts/append_wrap_up_log_row.py` — never hand-typed.
> Rows are strictly chronological. Older rows are rotated to
> `archive/wrap-up-log-YYYY-MM.md`; a project-keyed grep that comes up empty
> here MUST also grep `archive/` before concluding a project was never
> wrapped (see `README.md` in this folder).

| Date | Project | Repo path | Branch merged | Merge commit | Summary | Deferred at gate? |
|------|---------|-----------|----------------|---------------|---------|--------------------|
"""

FIELDS = ["date", "project", "repo", "branch", "merge_commit", "summary", "deferred"]


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
    return value or "—"


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
    ap.add_argument("file", nargs="?", default=DEFAULT_FILE)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--project", required=True)
    ap.add_argument("--repo", required=True, help="repo path (main checkout)")
    ap.add_argument("--branch", required=True,
                     help='branch merged, e.g. "effort/…" or '
                          '"master (direct, no feature branch/worktree)"')
    ap.add_argument("--merge-commit", dest="merge_commit", required=True,
                     help='merge commit sha(s), or "no merge (…)" / "—"')
    ap.add_argument("--summary", required=True,
                     help="one to two sentences max — the report and commit "
                          "messages carry the narrative, not this cell")
    ap.add_argument("--deferred", required=True,
                     help='what was deferred at the gate, or "none"; for an '
                          'aborted/deferred run, the STOP reason and state left behind')
    args = ap.parse_args()

    import re
    if not re.match(r"^20\d\d-\d\d-\d\d$", args.date):
        die(f"--date must be YYYY-MM-DD, got {args.date!r}")

    exists = os.path.exists(args.file)
    if not exists:
        content = HEADER
    else:
        content = open(args.file, encoding="utf-8").read()

    raw = {f: getattr(args, f) for f in FIELDS}
    cells = [escape_cell(raw[f]) for f in FIELDS]
    row = "| " + " | ".join(cells) + " |"

    if count_columns(row) != 7:
        die(f"assembled row did not come out to 7 columns (got "
            f"{count_columns(row)}) -- this is a bug in this script, not "
            f"your input: {row!r}")

    if not content.endswith("\n"):
        content += "\n"
    content += row + "\n"

    os.makedirs(os.path.dirname(os.path.abspath(args.file)), exist_ok=True)
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

    print(f"Added row to {args.file} :: {args.date} / {args.project} / "
          f"{args.branch} (7 columns, self-check passed)")


if __name__ == "__main__":
    main()

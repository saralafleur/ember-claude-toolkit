#!/usr/bin/env python3
"""
Append one guaranteed-valid table row to the team-decisions run-log
(memory/decisions-log.md) for /team-decisions Step 6.

Exists because hand-typed rows have drifted from the log's own 5-column
table shape twice (bullet-style rows, missing leading/trailing pipes).
The script writes ONLY the skeletal row -- substantive prose notes under a
row (process lessons, multi-wave detail) stay freehand, by design.

Usage:
    append_decision_log_row.py --project "Acme" \
        --resolved "foo/decisions.md:DEC-1, foo/decisions.md:DEC-2" \
        --open "bar/decisions.md:QA-3" \
        --committed "Yes (abc1234)"
    # empty-queue run: omit --resolved/--open (both default to blank)

Exits non-zero without writing on any validation problem.
"""
import argparse
import datetime
import os
import re
import sys
from pathlib import Path

LOG_PATH = os.path.expanduser(
    "~/.claude/skills/team-decisions/memory/decisions-log.md")
TEMPLATE_PATH = str(
    Path(__file__).parent.parent / "templates" / "decisions-log-header.md")
EXPECTED_HEADER = "| Date | Project/repo | Resolved (file:ID) | Still open (file:ID) | Docs committed? |"
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written): {msg}\n")
    sys.exit(1)


def cell(text):
    """Make arbitrary text safe inside a markdown table cell."""
    text = " ".join(text.split())  # collapse newlines/runs of whitespace
    return text.replace("|", "\\|") or "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="project/repo name")
    ap.add_argument("--resolved", default="", help="file:ID list, comma-separated; blank for an empty-queue run")
    ap.add_argument("--open", dest="still_open", default="", help="file:ID list still open; blank if none")
    ap.add_argument("--committed", required=True, help='e.g. "Yes (abc1234)", "Yes, local only (abc1234)", "No", "n/a"')
    ap.add_argument("--date", default=None, help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--log", default=LOG_PATH, help="override the log path (testing only)")
    args = ap.parse_args()
    log_path = args.log

    date = args.date or datetime.date.today().isoformat()
    if not DATE_RE.match(date):
        die(f"--date {date!r} is not YYYY-MM-DD")
    if not args.project.strip():
        die("--project is empty")

    if not os.path.exists(log_path):
        try:
            header = open(TEMPLATE_PATH, encoding="utf-8").read()
        except OSError as e:
            die(f"log missing and template unreadable ({e})")
        parent = os.path.dirname(log_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(header if header.endswith("\n") else header + "\n")

    content = open(log_path, encoding="utf-8").read()
    if EXPECTED_HEADER not in content:
        die(f"log at {log_path} doesn't contain the expected 5-column header; "
            "schema may have changed -- update this script alongside it")

    row = "| {} | {} | {} | {} | {} |".format(
        date, cell(args.project), cell(args.resolved),
        cell(args.still_open), cell(args.committed))

    with open(log_path, "a", encoding="utf-8") as f:
        if not content.endswith("\n"):
            f.write("\n")
        f.write(row + "\n")
    print(f"Appended to {log_path}:\n{row}")


if __name__ == "__main__":
    main()

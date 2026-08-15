#!/usr/bin/env python3
"""
Append one guaranteed-valid table row to team-intake's global fallback
decision-log (memory/decision-log.md), or to a project-specific log via
--log.

Exists because hand-typed rows measurably drifted from the log's own
8-column shape (a sizable fraction of rows were found nonconformant in a
workflow audit). The script writes ONLY the skeletal row — substantive
detail belongs in the per-request decisions.md the Link column points to.

A status flip is recorded by appending a NEW row for the same decision id —
newest row wins; nothing is edited in place (append-only ledger).

Usage:
    append_intake_decision_row.py --project "Acme" \
        --slug run-tracking --decision-id DEC-3 --item "cache backend" \
        --status DECIDED-AUTO --decision "Chose sqlite — zero ops" \
        --link "intake/2026-08-14-run-tracking/decisions.md" \
        [--date YYYY-MM-DD] [--log /path/to/decision-log.md]

Exits non-zero without writing on any validation problem.
"""
import argparse
import datetime
import os
import re
import sys

LOG_PATH = os.path.expanduser(
    "~/.claude/skills/team-intake/memory/decision-log.md")
EXPECTED_HEADER = ("| Date | Project | Slug | Decision id | Item | Status "
                   "| One-line decision | Link |")
STATUS_VOCAB = {
    "PENDING", "PARKED", "WATCH", "DEFERRED", "DECIDED", "DECIDED-AUTO",
    "DECIDED-DEFAULT", "SUPERSEDED", "RESOLVED", "DONE", "RECORD",
}
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
MAX_DECISION_CHARS = 300


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written): {msg}\n")
    sys.exit(1)


def cell(value, name, required=True):
    v = " ".join(value.split())  # collapse newlines/runs of whitespace
    if required and not v:
        die(f"--{name} must not be empty")
    return v.replace("|", "\\|")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--decision-id", required=True)
    ap.add_argument("--item", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--decision", required=True)
    ap.add_argument("--link", default="")
    ap.add_argument("--date", default=None)
    ap.add_argument("--log", default=LOG_PATH)
    args = ap.parse_args()

    date = args.date or datetime.date.today().isoformat()
    if not DATE_RE.match(date):
        die(f"bad --date: {date!r}")
    status = args.status.strip().upper()
    if status not in STATUS_VOCAB:
        die(f"--status {args.status!r} not in shared vocabulary: "
            + " · ".join(sorted(STATUS_VOCAB)))
    decision = cell(args.decision, "decision")
    if len(decision) > MAX_DECISION_CHARS:
        die(f"--decision is {len(decision)} chars (max {MAX_DECISION_CHARS}) "
            "— the row is a pointer; put detail in the linked decisions.md")

    log = os.path.expanduser(args.log)
    if not os.path.isfile(log):
        die(f"log file does not exist: {log}")
    with open(log, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if EXPECTED_HEADER not in [ln.strip() for ln in lines]:
        die(f"log at {log} lacks the expected 8-column header — refusing to "
            f"append a row of the wrong schema. Expected: {EXPECTED_HEADER}")

    row = "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
        date, cell(args.project, "project"), cell(args.slug, "slug"),
        cell(args.decision_id, "decision-id"), cell(args.item, "item"),
        status, decision, cell(args.link, "link", required=False) or "—")

    if len(re.findall(r"(?<!\\)\|", row)) != 9:
        die("internal: row did not come out 8-column — bug, not written")

    with open(log, "a", encoding="utf-8") as f:
        if lines and lines[-1].strip():
            f.write("\n")
        f.write(row + "\n")
    print(f"appended to {log}:\n{row}")


if __name__ == "__main__":
    main()

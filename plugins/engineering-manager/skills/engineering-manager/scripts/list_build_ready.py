#!/usr/bin/env python3
"""
list_build_ready.py -- deterministic Step 0 candidate filter for
engineering-manager's `dispatch` command.

Parses the stage-map table(s) out of a team-status `status-report.md` and
emits the build-ready candidate set as JSON: every item whose row shows
Intake ✅ and Build ❌/➡️ (per the 2026-08-14 workflow-audit's SC2 decision,
QA ✅ is NOT required anymore -- team-build self-heals a missing test-plan by
auto-running team-qa first, so a completed intake is a dispatch candidate).
Optionally counts each candidate's open (PENDING/PARKED) decisions via
team-decisions' shared scan_decisions.py, since an item blocked on an open
decision is not dispatch-ready regardless of stage columns.

Provenance: 2026-08-14 workflow-audit (scriptability finding 3): the
emoji-column filter over team-status's templated stage-map is a
deterministic row scan re-derived by hand each run; the open-decision clause
is exactly what scan_decisions.py computes. The judgment stays agent-side:
the report-staleness call, and reading the Notes column for sequencing
rulings (which this script surfaces verbatim per row, never interprets).

Fails LOUD (non-zero exit, no partial output) when no stage-map table is
found or a row doesn't classify -- an unparseable report needs a human/agent
eye, not a silently shortened candidate list.

Usage:
    list_build_ready.py <status-report.md> [--target-root <dir>] [--all-rows]

    --target-root  the folder containing each item's own folder (defaults
                   to the report's parent dir); enables the open-decision
                   count via scan_decisions.py for slugs whose folder exists.
    --all-rows     emit every parsed stage-map row (with stage columns), not
                   just the build-ready filter -- useful for eyeballing the
                   parse against the report.
"""
import argparse
import json
import os
import re
import subprocess
import sys

DEFAULT_SCAN_DECISIONS = os.path.expanduser(
    "~/.claude/skills/team-decisions/scripts/scan_decisions.py")

# The canonical template header and the abbreviated variant seen in real
# reports' carried-forward sections.
HEADER_PATTERNS = [
    ["#", "item", "intake", "qa", "build", "merged"],
    ["#", "item", "i", "qa", "bld", "mrg"],
]

DONE = "✅"      # ✅
NOT_DONE = "❌"  # ❌
PARTIAL = "➡"   # ➡ (with or without variation selector)


def die(msg):
    sys.stderr.write(f"FAILED (no output emitted): {msg}\n")
    sys.exit(1)


def split_row(line):
    body = line.strip()
    if not (body.startswith("|") and body.endswith("|")):
        return None
    return [c.strip() for c in body[1:-1].split("|")]


def header_matches(cells):
    lowered = [re.sub(r"[^a-z#]", "", c.lower()) for c in cells]
    for pat in HEADER_PATTERNS:
        if len(lowered) >= len(pat) and all(
                cell.startswith(tok)
                for cell, tok in zip(lowered, pat)):
            return True
    return False


def classify_stage(cell):
    """Map a stage cell to done/not-done/partial/n-a/unknown."""
    if PARTIAL in cell:
        return "partial"
    if DONE in cell:
        return "done"
    if NOT_DONE in cell:
        return "not-done"
    if re.fullmatch(r"[—–\-\s]*", cell):
        return "n/a"   # container/not-applicable rows use an em-dash
    return "unknown"


def parse_report(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    rows = []
    in_table = False
    for i, line in enumerate(lines):
        cells = split_row(line)
        if cells is None:
            in_table = False
            continue
        if header_matches(cells):
            in_table = True
            continue
        if not in_table:
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue  # separator row
        if len(cells) < 6:
            die(f"line {i + 1}: stage-map row has {len(cells)} cells, "
                f"expected at least 6: {line!r}")
        num, item = cells[0], cells[1]
        slug_m = re.search(r"`([^`]+)`", item)
        slug = slug_m.group(1) if slug_m else item.strip()
        if not slug:
            die(f"line {i + 1}: could not extract a slug from {item!r}")
        rows.append({
            "row": num,
            "slug": slug,
            "intake": classify_stage(cells[2]),
            "qa": classify_stage(cells[3]),
            "build": classify_stage(cells[4]),
            "merged": classify_stage(cells[5]),
            "notes": cells[6] if len(cells) > 6 else "",
            "line": i + 1,
        })
    if not rows:
        die(f"no stage-map table found in {path} -- expected a table whose "
            "header starts with the template's columns "
            "(| # | Item (slug) | Intake | QA | Build | Merged |)")
    return rows


def open_decision_count(item_dir, scan_decisions_path):
    """Count PENDING/PARKED decisions under one item folder, or None if
    the count is unavailable (item folder missing, scan_decisions.py not
    found on this install -- team-decisions is a different plugin and may
    not be present -- or the scan itself failed/timed out)."""
    if not os.path.isdir(item_dir):
        return None
    if not os.path.isfile(scan_decisions_path):
        return None
    try:
        out = subprocess.run(
            [sys.executable, scan_decisions_path, "--json", "--no-manifest",
             item_dir],
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return None
    open_statuses = {"PENDING", "PARKED"}
    count = 0

    def walk(node):
        nonlocal count
        if isinstance(node, dict):
            status = node.get("status")
            if isinstance(status, str) and status.upper() in open_statuses:
                count += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--target-root",
                    help="folder holding each item's own subfolder "
                         "(default: the report's parent dir)")
    ap.add_argument("--all-rows", action="store_true")
    ap.add_argument("--scan-decisions-path", default=DEFAULT_SCAN_DECISIONS,
                    help="override the path to team-decisions' "
                         "scan_decisions.py (default: this machine's loose "
                         "install path; open_decisions is reported as "
                         "unavailable/null if the script isn't found there "
                         "-- team-decisions is a separate plugin and may "
                         "not be installed)")
    args = ap.parse_args()

    if not os.path.exists(args.report):
        die(f"{args.report} does not exist")
    target_root = args.target_root or os.path.dirname(
        os.path.abspath(args.report))

    rows = parse_report(args.report)

    if args.all_rows:
        print(json.dumps({"rows": rows}, indent=2, ensure_ascii=False))
        return

    candidates = []
    for r in rows:
        if "unknown" in (r["intake"], r["build"]):
            die(f"line {r['line']}: could not classify stage cells for "
                f"{r['slug']!r} -- refusing to emit a possibly-wrong "
                "candidate set")
        # SC2 filter: Intake done, Build not started or partial. (QA not
        # required -- team-build auto-runs team-qa on a missing test-plan.)
        if r["intake"] == "done" and r["build"] in ("not-done", "partial"):
            r = dict(r)
            r["open_decisions"] = open_decision_count(
                os.path.join(target_root, r["slug"]), args.scan_decisions_path)
            candidates.append(r)

    print(json.dumps({
        "report": os.path.abspath(args.report),
        "filter": "intake=done AND build in (not-done, partial); "
                  "open_decisions counted via scan_decisions.py "
                  "(null = item folder not found/scannable)",
        "candidates": candidates,
        "candidate_count": len(candidates),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

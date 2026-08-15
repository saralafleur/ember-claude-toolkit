#!/usr/bin/env python3
"""
Deterministic Step 1 inventory for team-status -- the script half of the
"script with agent fallback" split (workflow-audit 2026-08-14, structural 9).

Enumerates every work item under a target folder (each distinct
`intake/<date>-<slug>/` directory, at any depth) and records each item's
artifact inventory -- the same fixed checklist status-triage runs by hand.
The orchestrator runs this FIRST; it launches the status-triage agent only
as a fallback when this script exits 2 (zero items found in a non-empty
folder -- the "layouts vary, search don't assume" residue) or the output
looks wrong for a known-nonstandard layout.

Usage:
    inventory_items.py <target> [--json]

Exit codes:
    0  READY  -- one or more items found (inventory on stdout)
    2  EMPTY  -- target exists and is non-empty, but no `intake/<date>-<slug>/`
                 items were found -> fall back to the status-triage agent
    3  BLOCKED -- target missing, unreadable, or an empty directory
"""
import argparse
import glob
import json
import os
import re
import sys

DATE_SLUG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+")
STUB_BYTES = 200  # below this a file is flagged as a possible stub

SIMPLE_ARTIFACTS = [
    "request-brief.md",
    "technical-plan.md",
    "pm-plan.md",
    "qa/test-plan.md",
    "qa/qa-assessment.md",
    "decisions.md",
    "qa/decisions.md",
]


def check(path):
    """Return '-', 'yes', or 'stub?' for one artifact path."""
    if not os.path.isfile(path):
        return "-"
    try:
        return "stub?" if os.path.getsize(path) < STUB_BYTES else "yes"
    except OSError:
        return "-"


def inventory_item(item_path):
    inv = {}
    for rel in SIMPLE_ARTIFACTS:
        inv[rel] = check(os.path.join(item_path, rel))
    build_reports = sorted(
        glob.glob(os.path.join(glob.escape(item_path), "build", "**", "build-report.md"),
                  recursive=True))
    inv["build-report.md"] = [os.path.relpath(p, item_path) for p in build_reports] or "-"
    build_decisions = sorted(
        glob.glob(os.path.join(glob.escape(item_path), "build", "**", "decisions.md"),
                  recursive=True))
    inv["build/decisions.md"] = [os.path.relpath(p, item_path) for p in build_decisions] or "-"
    supporting = glob.glob(os.path.join(glob.escape(item_path), "supporting", "*.md"))
    inv["supporting/*.md count"] = len(supporting)
    return inv


def find_items(target):
    """Every dir whose parent is named `intake` and whose own name is
    <date>-<slug>, at any depth. Also handles target itself being one."""
    items = []
    base = os.path.basename(os.path.normpath(target))
    parent = os.path.basename(os.path.dirname(os.path.normpath(target)))
    if parent == "intake" and DATE_SLUG_RE.match(base):
        items.append(os.path.normpath(target))
    for root, dirs, _files in os.walk(target):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
        if os.path.basename(root) == "intake":
            for d in sorted(dirs):
                if DATE_SLUG_RE.match(d):
                    items.append(os.path.join(root, d))
    # de-dupe, keep order
    seen, out = set(), []
    for p in items:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.isdir(target) or not os.access(target, os.R_OK):
        print(json.dumps({"verdict": "BLOCKED",
                          "reason": "target missing or unreadable",
                          "target": target}))
        sys.exit(3)
    try:
        non_hidden = [e for e in os.listdir(target) if not e.startswith(".")]
    except OSError:
        non_hidden = []
    if not non_hidden:
        print(json.dumps({"verdict": "BLOCKED", "reason": "target is empty",
                          "target": target}))
        sys.exit(3)

    item_paths = find_items(target)
    if not item_paths:
        print(json.dumps({"verdict": "EMPTY",
                          "reason": "no intake/<date>-<slug>/ items found; "
                                    "fall back to the status-triage agent",
                          "target": target}))
        sys.exit(2)

    items = []
    for p in item_paths:
        items.append({"slug": os.path.basename(p), "path": p,
                      "artifacts": inventory_item(p)})
    result = {
        "verdict": "READY",
        "target": target,
        "shape": "single item" if len(items) == 1 and
                 os.path.normpath(items[0]["path"]) == os.path.normpath(target)
                 else f"batch ({len(items)} items)",
        "items": items,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"READY -- {result['shape']} under {target}")
        for it in items:
            a = it["artifacts"]
            br = a["build-report.md"]
            print(f"  {it['slug']}: plans:"
                  f"{'yes' if a['technical-plan.md'] == 'yes' else a['technical-plan.md']}"
                  f" test-plan:{a['qa/test-plan.md']}"
                  f" qa-assessment:{a['qa/qa-assessment.md']}"
                  f" build-report:{'-' if br == '-' else len(br)}"
                  f" decisions:{a['decisions.md']}")
    sys.exit(0)


if __name__ == "__main__":
    main()

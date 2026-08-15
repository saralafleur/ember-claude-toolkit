#!/usr/bin/env python3
"""
Format guard for decisions.md files -- the ENFORCEMENT half of the
decision-log write contract.

Every `## ` block in a post-cutoff decisions.md must carry a status the
shared parser (decisions_lib.py) classifies into the canonical vocabulary,
via one of the two canonical sites (a `- **Status:** X` field line, or the
status after the heading's last em-dash). Violations fail with
file:line:block-id, exit 1 -- wire this into `make ci` so freestyle writes
fail the gate no matter who or what produced them.

Scope rules (the legacy grandfather):
  - Roots mode (directories): only files whose innermost cycle-slug date
    (the last YYYY-MM-DD in the path) is >= --cutoff are linted. Older
    files are legacy debt, worked off by normalize_decisions.py, not lint
    failures. Undated files are skipped (listed with a note) unless --all.
  - Explicit-file mode (the PostToolUse hook passes one file): same date
    rule -- a pre-cutoff/undated file exits 0 with a "(legacy...)" note.
  - --all lints everything regardless of date (use once normalization
    reaches zero and the cutoff can be retired).
  - A root's .decisions-scan-ignore is honored in both modes, so a
    machine-generated *decisions.md (product data) is never linted.

Exit codes: 0 clean/skipped, 1 violations found, 2 usage error.

Usage:
    lint_decisions.py <root-or-file> [...] [--cutoff 2026-08-14] [--all]
"""
import argparse
import fnmatch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decisions_lib import (  # noqa: E402
    IGNORE_BASENAME, _load_ignore_patterns, find_decision_files, parse_file,
    path_cycle_date,
)

DEFAULT_CUTOFF = "2026-08-14"


def nearest_ignore_root(path):
    """For an explicit file: walk up to the nearest dir holding a
    .decisions-scan-ignore or .git -- that's the root its ignore patterns
    are relative to. None if neither is found."""
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if (os.path.exists(os.path.join(d, IGNORE_BASENAME))
                or os.path.isdir(os.path.join(d, ".git"))):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def is_ignored(path, root):
    if root is None:
        return False
    rel = os.path.relpath(os.path.abspath(path), root)
    return any(fnmatch.fnmatch(rel, p) for p in _load_ignore_patterns(root))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="roots (directories) and/or explicit decisions.md files")
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF,
                    help=f"cycle-date grandfather line (default {DEFAULT_CUTOFF}); older files are skipped")
    ap.add_argument("--all", action="store_true", help="lint every file regardless of cycle date")
    args = ap.parse_args()

    targets = []
    explicit = set()
    skipped = []
    for p in args.paths:
        if os.path.isdir(p):
            targets.extend(find_decision_files([p]))
        elif os.path.isfile(p):
            explicit.add(os.path.abspath(p))
            if not p.endswith("decisions.md"):
                continue  # hook may fire on any file; non-decision files aren't ours
            if is_ignored(p, nearest_ignore_root(p)):
                skipped.append((p, "ignored via " + IGNORE_BASENAME))
                continue
            targets.append(p)
        else:
            sys.stderr.write(f"lint_decisions: no such path: {p}\n")
            sys.exit(2)

    violations = []
    unreadable = []
    for f in sorted(set(targets)):
        d = path_cycle_date(f)
        if not args.all:
            if d is None:
                skipped.append((f, "no cycle date in path -- skipped (pass --all to lint)"))
                continue
            if d < args.cutoff:
                skipped.append((f, f"legacy (cycle date {d} < cutoff {args.cutoff}) -- normalization lane's job"))
                continue
        blocks, warnings = parse_file(f)
        unreadable.extend(warnings)
        for b in blocks:
            if not b["conformant"]:
                violations.append(b)

    if violations:
        print(f"DECISION-FORMAT LINT: {len(violations)} nonconformant block(s)\n")
        for b in violations:
            raw = f" (found: {b['status_raw'][:60]!r})" if b["status_raw"] else ""
            print(f"  {b['file']}:{b['heading_lineno']}: block {b['id']!r} has no canonical status{raw}")
        print("\nEvery `## ` block needs `- **Status:** <TOKEN>` (or the token after the "
              "heading's last em-dash), TOKEN from the shared vocabulary -- see "
              "decisions_lib.STATUS_VOCAB. Author new blocks with add_decision.py; "
              "use RECORD for non-decision blocks.")
    # Per-file skip notes only for files the caller named explicitly (the
    # hook's single-file case, where the note IS the answer); a directory
    # walk's skips collapse to one summary line so CI output stays readable.
    walk_skips = 0
    for f, why in skipped:
        if os.path.abspath(f) in explicit:
            print(f"(skipped {f}: {why})")
        else:
            walk_skips += 1
    if walk_skips:
        print(f"({walk_skips} pre-cutoff/undated legacy file(s) skipped -- the normalization lane's job, not lint's)")
    if unreadable:
        for w in unreadable:
            print(f"(warning: {w})")
        sys.exit(1)
    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()

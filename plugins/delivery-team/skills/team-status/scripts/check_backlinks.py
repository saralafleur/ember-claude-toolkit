#!/usr/bin/env python3
"""
Backlink sweep for status-lead's reciprocal-cross-reference check
(workflow-audit 2026-08-14, structural 9 / scriptability F6). Given the
catalog/decision IDs each item's docs cite (as surfaced by the scanners)
and the catalog/log files those IDs live in, emits every ONE-WAY pointer:
the cited entry exists but never mentions the citing item back.

Deterministic sweep only -- it does not judge whether a missing backlink
matters; status-lead does that (and drafts the one-line fix into Proposed
corrections when it does). A deterministic sweep doesn't get tired on pass
3 the way the hand-run grep demonstrably did (13 stale rows survived 3+
consecutive passes, 2026-08-01 audit).

Usage:
    check_backlinks.py --cite "RI-0014=2026-08-06-jobs-screen" \
        [--cite "DEC-7=simulator-mode-switch"] ... \
        <catalog-or-log-file> [<file> ...]

Each --cite is <ID>=<citing-item-slug>. Output per cite (tab-separated):
    OK\t<ID>\tentry in <file> mentions <slug>
    ONE-WAY\t<ID>\tentry in <file> has NO mention of <slug>
    MISSING\t<ID>\tno entry found in any given file
"""
import argparse
import os
import re
import sys


def find_entry_block(content, cid):
    """Return the text of the entry that DEFINES cid: the heading/table-row
    region from the first line containing cid as a whole token, through the
    next same-level heading (or 40 lines, for table/log rows)."""
    lines = content.splitlines()
    tok = re.compile(r"(?<![\w-])" + re.escape(cid) + r"(?![\w-])")
    for i, line in enumerate(lines):
        if tok.search(line):
            if line.lstrip().startswith("#"):
                level = len(line) - len(line.lstrip("#").lstrip())
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("#") and not lines[j].startswith("#" * (level + 1)):
                        return "\n".join(lines[i:j])
                return "\n".join(lines[i:])
            return "\n".join(lines[i:i + 40])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--cite", action="append", required=True,
                    help="<ID>=<citing-item-slug>, repeatable")
    args = ap.parse_args()

    cites = []
    for c in args.cite:
        if "=" not in c:
            sys.stderr.write(f"bad --cite {c!r} (want ID=slug)\n")
            sys.exit(3)
        cid, slug = c.split("=", 1)
        cites.append((cid.strip(), slug.strip()))

    contents = {}
    for f in args.files:
        if os.path.isfile(f):
            contents[f] = open(f, encoding="utf-8", errors="replace").read()

    one_way = 0
    for cid, slug in cites:
        found = False
        for f, content in contents.items():
            block = find_entry_block(content, cid)
            if block is None:
                continue
            found = True
            if slug in block or slug in content:
                where = "entry" if slug in block else "file (not entry block)"
                print(f"OK\t{cid}\t{where} in {f} mentions {slug}")
            else:
                print(f"ONE-WAY\t{cid}\tentry in {f} has NO mention of {slug}")
                one_way += 1
            break
        if not found:
            print(f"MISSING\t{cid}\tno entry found in any given file")
            one_way += 1
    sys.exit(1 if one_way else 0)


if __name__ == "__main__":
    main()

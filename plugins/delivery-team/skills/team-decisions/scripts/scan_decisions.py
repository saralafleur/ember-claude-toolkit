#!/usr/bin/env python3
"""
Fast mechanical scan of *decisions.md files for /team-decisions (Step 2/3).

v2: incremental via a seal manifest, plus index generation and a
violations ratchet. Parsing/format rules live in decisions_lib.py (shared
with lint/normalize/add), so scan/lint/write can never drift apart.

Finds every `*decisions.md` file under one or more roots, parses each `## `
decision block, classifies its Status, and prints:
  1. a tally table (status -> count) across every block/file
  2. the full text of every block classified PENDING or PARKED, oldest
     Raised date first, so the walkthrough can be built straight from stdout
  3. a short DECIDED-AUTO list (file:heading only)
  4. a "review me" list: any block containing the literal substrings
     PENDING or PARKED that did NOT classify as PENDING/PARKED -- printed in
     full only for files parsed fresh this run; blocks in cache-hit files
     were already skimmed the run that cached them, so they appear as a
     count, not a re-listing
  5. a format-violations ratchet: how many blocks are still nonconformant
     (no canonical status) -- the number normalize_decisions.py works down

Seal manifest (.decisions-manifest.json in the first root, gitignored):
a per-file cache keyed by content hash. Unchanged files reuse their cached
parse summary -- sweep cost tracks recent activity, not total history. Any
edit changes the hash and forces a fresh parse (fail-safe). A scanner
version bump bursts every entry, forcing one full re-verify under the new
parser. The manifest is disposable: delete it and the next run rebuilds it.

Usage:
    scan_decisions.py [root ...]          # incremental (default)
    scan_decisions.py --full [root ...]   # ignore cache, re-parse everything
    scan_decisions.py --no-manifest ...   # don't read OR write the manifest
    scan_decisions.py --write-index ...   # also regenerate OPEN-DECISIONS.md
                                          # in the first root
    scan_decisions.py --json [root ...]   # machine-readable dump (always a
                                          # full parse; cache not consulted)
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decisions_lib import (  # noqa: E402
    INDEX_BASENAME, MANIFEST_BASENAME, OPEN_STATUSES, SCANNER_VERSION,
    TRIPWIRE_STATUSES, file_hash, find_decision_files, load_manifest,
    parse_file, save_manifest, summarize_blocks_for_manifest,
)

DEDICATED_ROWS = ("PENDING", "PARKED", "DECIDED", "DECIDED-AUTO", "SUPERSEDED")


def write_index(index_path, open_items, tripwires, violations_total, files_count):
    """Regenerate OPEN-DECISIONS.md from scratch. Never hand-maintained --
    the generated-at stamp is its whole staleness story."""
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "# Open Decisions Index",
        "",
        f"> **Generated:** {now} by scan_decisions.py v{SCANNER_VERSION} — "
        "regenerated on every /team-decisions sweep and /wrap-up audit. "
        "DO NOT EDIT BY HAND: any manual change here is overwritten on the "
        "next scan; the source of truth is the per-cycle decisions.md files.",
        "",
        f"Scanned {files_count} decisions.md files. "
        f"Open: {len(open_items)} · Tripwires: {len(tripwires)} · "
        f"Format-violation backlog (normalization ratchet): {violations_total}",
        "",
        "## Awaiting a decision (PENDING / PARKED)",
        "",
    ]
    if open_items:
        lines += ["| File | ID | Status | Raised | Question |", "|---|---|---|---|---|"]
        for b in open_items:
            heading_short = b["heading"].replace("|", "\\|")[:100]
            lines.append(f"| {b['_relfile']} | {b['id']} | {b['status']} | "
                         f"{b['raised'] or '?'} | {heading_short} |")
    else:
        lines.append("(none)")
    lines += ["", "## Live tripwires (WATCH / DEFERRED — condition-triggered, not awaiting a ruling)", ""]
    if tripwires:
        lines += ["| File | ID | Status | Raised |", "|---|---|---|---|"]
        for b in tripwires:
            lines.append(f"| {b['_relfile']} | {b['id']} | {b['status']} | {b['raised'] or '?'} |")
    else:
        lines.append("(none)")
    lines.append("")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="*", default=["."])
    ap.add_argument("--json", action="store_true",
                    help="dump machine-readable JSON instead (always full-parses; cache not consulted)")
    ap.add_argument("--full", action="store_true",
                    help="ignore the seal cache and re-parse every file (reconciliation pass); still refreshes the manifest")
    ap.add_argument("--no-manifest", action="store_true",
                    help="neither read nor write the manifest")
    ap.add_argument("--manifest-path", default=None,
                    help=f"override manifest location (default: <first root>/{MANIFEST_BASENAME})")
    ap.add_argument("--write-index", action="store_true",
                    help=f"also regenerate {INDEX_BASENAME} in the first root")
    args = ap.parse_args()

    roots = args.roots or ["."]
    first_root = os.path.abspath(roots[0])
    manifest_path = args.manifest_path or os.path.join(first_root, MANIFEST_BASENAME)

    files = find_decision_files(roots)

    if args.json:
        all_blocks, all_warnings = [], []
        for f in files:
            blocks, warnings = parse_file(f)
            all_blocks.extend(blocks)
            all_warnings.extend(warnings)
        print(json.dumps({"files": files, "blocks": all_blocks,
                          "warnings": all_warnings}, indent=2))
        return

    use_manifest = not args.no_manifest
    manifest = load_manifest(manifest_path) if use_manifest else {"files": {}}
    old_entries = manifest.get("files", {})
    new_entries = {}

    all_warnings = []
    fresh_files, cached_files = [], []
    # Per-file summaries, whether fresh-parsed or cache-reused.
    summaries = {}  # abspath -> summary dict

    for f in files:
        ab = os.path.abspath(f)
        try:
            h = file_hash(ab)
        except OSError as e:
            all_warnings.append(f"{f}: UNREADABLE ({e})")
            continue
        cached = old_entries.get(ab)
        if cached and not args.full and cached.get("hash") == h:
            summaries[ab] = cached["summary"]
            new_entries[ab] = cached
            cached_files.append(ab)
            continue
        blocks, warnings = parse_file(ab)
        all_warnings.extend(warnings)
        if warnings:
            # An unreadable/partially-read file must never be sealed as clean.
            continue
        summary = summarize_blocks_for_manifest(blocks)
        summaries[ab] = summary
        new_entries[ab] = {"hash": h, "scanned": datetime.date.today().isoformat(),
                           "summary": summary}
        fresh_files.append(ab)

    if use_manifest:
        manifest["files"] = new_entries  # entries for deleted files drop out here
        try:
            save_manifest(manifest_path, manifest)
        except OSError as e:
            print(f"(warning: could not write manifest {manifest_path}: {e})", file=sys.stderr)

    # ---- aggregate ----
    tally, other_breakdown = {}, {}
    total_blocks = 0
    open_items, tripwires, auto_list, violations = [], [], [], []
    fresh_suspects, cached_suspect_count = [], 0

    for ab in sorted(summaries):
        s = summaries[ab]
        rel = os.path.relpath(ab, first_root)
        for status, count in s["status_counts"].items():
            total_blocks += count
            if status in DEDICATED_ROWS:
                tally[status] = tally.get(status, 0) + count
            else:
                tally["Other"] = tally.get("Other", 0) + count
                other_breakdown[status] = other_breakdown.get(status, 0) + count
        for b in s["open_blocks"]:
            open_items.append({**b, "file": ab, "_relfile": rel})
        for b in s["tripwire_blocks"]:
            tripwires.append({**b, "file": ab, "_relfile": rel})
        for bid in s["auto_ids"]:
            auto_list.append(f"{ab}:{bid}")
        for v in s["violations"]:
            violations.append({**v, "file": ab, "_relfile": rel})
        if ab in cached_files:
            cached_suspect_count += len(s["suspect_ids"])
        else:
            for sus in s["suspect_ids"]:
                fresh_suspects.append({**sus, "file": ab})

    # ---- report ----
    print(f"# Scan: {len(summaries)} decisions.md files, {total_blocks} decision blocks "
          f"({len(fresh_files)} parsed fresh, {len(cached_files)} unchanged since last verified"
          f"{', cache bypassed via --full' if args.full and use_manifest else ''})\n")
    print("| Status | Count |")
    print("|---|---|")
    for status in list(DEDICATED_ROWS) + ["Other"]:
        if tally.get(status):
            print(f"| {status} | {tally[status]} |")
    print(f"| **Total** | **{total_blocks}** |")

    print(f"\n<details><summary>Other breakdown ({tally.get('Other', 0)} blocks, "
          f"{len(other_breakdown)} distinct values) -- ask if you want this named in prose</summary>\n")
    for status, count in sorted(other_breakdown.items(), key=lambda kv: -kv[1]):
        print(f"- {status}: {count}")
    print("</details>")

    open_items.sort(key=lambda b: (b["raised"] or "0000-00-00"))
    print(f"\n## Walkthrough queue: {len(open_items)} PENDING/PARKED block(s), oldest Raised first\n")
    for b in open_items:
        raised_note = b["raised"] or "(unknown)"
        if b["raised"] and b["raised_inferred"]:
            raised_note += " (inferred from cycle-folder date, not an explicit field)"
        print(f"--- {b['file']} :: {b['id']} :: {b['status']} :: Raised {raised_note} ---")
        print(f"## {b['heading']}")
        print(b["body"].strip())
        print()

    if auto_list:
        print(f"\n## DECIDED-AUTO (secondary list, {len(auto_list)} blocks)\n")
        for entry in auto_list:
            print(f"- {entry}")

    if fresh_suspects or cached_suspect_count:
        print(f"\n## Review-me: classified as something else but text contains PENDING/PARKED"
              f" ({len(fresh_suspects)} in freshly-parsed files"
              f"{f'; {cached_suspect_count} more in unchanged files, already skimmed the run that sealed them' if cached_suspect_count else ''})\n")
        if fresh_suspects:
            print("(Usually a heading ID prefix like PENDING-CF-3, or prose referencing "
                  "another decision's status. Sanity-check these, don't trust either signal alone.)\n")
            for sus in fresh_suspects:
                print(f"- {sus['file']}:{sus['id']} -> classified {sus['status']}")

    print(f"\n## Format violations (normalization ratchet): {len(violations)} nonconformant block(s)")
    if violations:
        by_file = {}
        for v in violations:
            by_file[v["_relfile"]] = by_file.get(v["_relfile"], 0) + 1
        print("\nBlocks with no canonical status (legacy debt for pre-cutoff files; "
              "a LINT FAILURE for post-cutoff ones). Work down with normalize_decisions.py:\n")
        for rel, count in sorted(by_file.items(), key=lambda kv: -kv[1]):
            print(f"- {rel}: {count}")

    tripwires.sort(key=lambda b: (b["raised"] or "0000-00-00"))
    if args.write_index:
        index_path = os.path.join(first_root, INDEX_BASENAME)
        write_index(index_path, open_items, tripwires, len(violations), len(summaries))
        print(f"\n(index regenerated: {index_path})")

    if all_warnings:
        print(f"\n## Warnings ({len(all_warnings)})\n")
        for w in all_warnings:
            print(f"- {w}")


if __name__ == "__main__":
    main()

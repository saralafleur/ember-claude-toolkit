#!/usr/bin/env python3
"""
Normalization lane (ETL) for legacy decisions.md blocks -- works the
format-violation ratchet down toward zero, one safe tier at a time.

A "violation" is a block the shared parser can't classify (no canonical
status site). This script sorts every violation into tiers:

  Tier 1 (deterministic, script-appliable): the block's own text carries
      exactly ONE distinct vocabulary token, in a structural position
      (bold on its line, or leading a line), and that token is NOT
      PENDING/PARKED. Fix = INSERT `- **Status:** <TOKEN>` directly under
      the heading. Pure insertion: the original prose is never touched, so
      the fix can only restate what the text already says.
      PENDING/PARKED are NEVER Tier 1 -- a script must never (re)open a
      decision; deciding something is genuinely open is always a human
      call (Tier 3). Closing-shaped statuses are safe to restate; opening
      ones are not. (Worst case for a wrong Tier 1: one closed block
      labeled with the wrong *flavor* of closed -- it never invents an
      obligation.)

  Tier 2 (model-assisted): zero tokens (usually a non-decision block ->
      RECORD candidate), or a token in a weak/prose-only position. Needs a
      reading, not a ruling: propose a status with quoted evidence, then
      apply via add-a-Status-line by hand or re-run of this script's
      inventory. High-confidence proposals batch; low-confidence join
      Tier 3.

  Tier 3 (human-gated): multiple distinct tokens, or any candidate whose
      resolution would mark a block OPEN. Walked with the user like the
      /team-decisions queue, but the question is "confirm what this
      block's status actually is," never "make the decision."

Applying (--apply) writes ONLY Tier 1 fixes, then re-parses every touched
file and FAILS LOUDLY unless: block count unchanged, every patched block
now conformant with the predicted status, and no previously-conformant
block changed classification. Run --dry-run (the default) first and eyeball
the report; batch commits by cycle folder for reviewable diffs.

Usage:
    normalize_decisions.py [root ...]                 # dry-run report
    normalize_decisions.py --apply [root ...]         # apply Tier 1
    normalize_decisions.py --inventory out.json [...] # Tier 2/3 worklist
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decisions_lib import (  # noqa: E402
    OPEN_STATUSES, STATUS_TOKEN_RES, STRIKETHROUGH_RE, find_decision_files,
    parse_file,
)


def block_tokens(heading, body):
    """Distinct vocab tokens in the block's full text (strikethrough
    stripped, ID references excluded), with position strength per token:
    'structural' if any occurrence is on a bold line or leads a line,
    else 'prose'."""
    text = STRIKETHROUGH_RE.sub("", heading + "\n" + body)
    found = {}
    for line in text.splitlines():
        upper = line.upper()
        for token, pattern in STATUS_TOKEN_RES:
            m = pattern.search(upper)
            if not m:
                continue
            stripped = upper.lstrip("-*# ").lstrip()
            structural = ("**" in line) or stripped.startswith(token)
            if structural or token not in found:
                found[token] = "structural" if structural or found.get(token) == "structural" else "prose"
    return found


def classify(block):
    tokens = block_tokens(block["heading"], block["body"])
    if any(t in OPEN_STATUSES for t in tokens):
        return "tier3", tokens, "text mentions an OPEN status -- only a human may (re)open"
    if len(tokens) == 1:
        token, strength = next(iter(tokens.items()))
        if strength == "structural":
            return "tier1", tokens, f"single unambiguous token {token} in structural position"
        return "tier2", tokens, f"single token {token} but only in prose position -- needs a reading"
    if len(tokens) == 0:
        return "tier2", tokens, "no status token at all -- likely a non-decision block (RECORD candidate)"
    return "tier3", tokens, f"multiple distinct tokens {sorted(tokens)} -- ambiguous, human call"


def apply_tier1(path, fixes):
    """Insert `- **Status:** TOKEN` under each fix's heading line.
    fixes: list of (heading_lineno_1based, token). Returns new content."""
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
    # Bottom-up so earlier linenos stay valid.
    for lineno, token in sorted(fixes, reverse=True):
        insert_at = lineno  # 0-based index right after the 1-based heading line
        lines.insert(insert_at, f"- **Status:** {token}\n")
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="*", default=["."])
    ap.add_argument("--apply", action="store_true", help="write Tier 1 fixes (default is dry-run)")
    ap.add_argument("--inventory", default=None, help="write the Tier 2/3 worklist as JSON to this path")
    args = ap.parse_args()

    files = find_decision_files(args.roots or ["."])
    tier1, tier2, tier3 = [], [], []
    for f in files:
        blocks, warnings = parse_file(f)
        if warnings:
            print(f"(warning: {warnings} -- file skipped, not normalized)")
            continue
        for b in blocks:
            if b["conformant"]:
                continue
            tier, tokens, why = classify(b)
            item = {"file": f, "id": b["id"], "lineno": b["heading_lineno"],
                    "heading": b["heading"][:100], "tokens": sorted(tokens), "why": why}
            if tier == "tier1":
                item["fix_status"] = next(iter(tokens))
                tier1.append(item)
            elif tier == "tier2":
                tier2.append(item)
            else:
                tier3.append(item)

    total = len(tier1) + len(tier2) + len(tier3)
    print(f"# Normalization report: {total} nonconformant block(s) across {len(files)} scanned file(s)\n")
    print(f"- Tier 1 (deterministic, {'APPLYING' if args.apply else 'would apply with --apply'}): {len(tier1)}")
    print(f"- Tier 2 (model-assisted reading needed): {len(tier2)}")
    print(f"- Tier 3 (human-gated): {len(tier3)}\n")

    for label, items in (("Tier 1", tier1), ("Tier 2", tier2), ("Tier 3", tier3)):
        if not items:
            continue
        print(f"## {label}")
        for it in items:
            fix = f" -> - **Status:** {it['fix_status']}" if "fix_status" in it else ""
            print(f"- {it['file']}:{it['lineno']} {it['id']!r}: {it['why']}{fix}")
        print()

    if args.inventory:
        with open(args.inventory, "w", encoding="utf-8") as f:
            json.dump({"tier2": tier2, "tier3": tier3}, f, indent=1)
        print(f"(Tier 2/3 inventory written to {args.inventory})")

    if not args.apply or not tier1:
        return

    by_file = {}
    for it in tier1:
        by_file.setdefault(it["file"], []).append((it["lineno"], it["fix_status"]))

    failures = []
    for path, fixes in sorted(by_file.items()):
        before_blocks, _ = parse_file(path)
        # Expected status per heading lineno -- positional, NOT by block ID:
        # real files carry duplicate IDs (two `## TL-6 ...` headings exist in
        # this very corpus), which made a by-ID comparison raise false alarms.
        expected_by_lineno = {ln: tok for ln, tok in fixes}

        new_content = apply_tier1(path, fixes)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Insertion preserves block order and count, so before[i] and
        # after[i] are the same block -- compare the sequences index-wise.
        after_blocks, warnings = parse_file(path)
        problems = []
        if warnings:
            problems.append(f"unreadable after write: {warnings}")
        if len(after_blocks) != len(before_blocks):
            problems.append(f"block count changed {len(before_blocks)} -> {len(after_blocks)}")
        else:
            for bb, ab in zip(before_blocks, after_blocks):
                if bb["id"] != ab["id"]:
                    problems.append(f"block order/identity shifted: {bb['id']} -> {ab['id']}")
                    continue
                want = expected_by_lineno.get(bb["heading_lineno"])
                if want is not None:
                    if not ab["conformant"] or ab["status"] != want:
                        problems.append(f"{ab['id']}: expected {want}, got {ab['status']}")
                elif ab["status"] != bb["status"]:
                    problems.append(f"{ab['id']}: untouched block changed "
                                    f"{bb['status']} -> {ab['status']}")
        if problems:
            failures.append((path, problems))
            print(f"VERIFY FAILED {path}: {problems} -- REVERT THIS FILE (git checkout -- <file>)")
        else:
            print(f"applied+verified {path}: {len(fixes)} status line(s) inserted")

    if failures:
        sys.exit(1)
    print(f"\nTier 1 complete: {len(tier1)} block(s) normalized across {len(by_file)} file(s), all verified.")


if __name__ == "__main__":
    main()

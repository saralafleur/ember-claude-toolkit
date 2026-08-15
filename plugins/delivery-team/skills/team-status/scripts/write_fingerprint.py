#!/usr/bin/env python3
"""
Fingerprint frontmatter writer/validator for team-status scratch files --
makes the cache correct by construction (workflow-audit 2026-08-14,
structural 2: 39 of 69 sampled scratch files lacked the specced
`fingerprint:` block entirely, so the Step 1.5 cosmetic-touch filter was
silently inert and every doc touch bought a scanner call).

status-scanner calls this AFTER writing its narrative findings to the
scratch file; the script validates every enum and prepends (or replaces)
the exact frontmatter block SKILL.md specifies, then re-parses it to prove
it extracts clean. A scanner should never hand-type this block.

Usage:
    write_fingerprint.py <scratch-file> \
        --verdict GREEN --merged true --merged-commit abc1234 \
        --decisions "DEC-1:DECIDED,WATCH-2:WATCH" \
        --test-numbers "319/319,14/14" \
        --qa-verdict ADEQUATE --verified-at 2026-08-15
    write_fingerprint.py --stdout ...   (print the block, write nothing)

Decisions use the item's own declared ID grammar (DEC-n, WATCH-n, PM-n,
OD-n, QA-DEC-n, letter-suffixed instances, ...), not DEC-only -- pass
"none" when the item has no decisions.md.
"""
import argparse
import os
import re
import sys

VERDICTS = {"GREEN", "GREEN-WITH-CAVEATS", "BLOCKED", "n/a"}
QA_VERDICT_RE = re.compile(r"^(ADEQUATE|GAPPED|BLIND)( \(pre-build\))?$|^n/a$")
# Widened ID grammar (was DEC-only): letters+hyphens prefix, number, optional
# letter suffix -- covers DEC-1, WATCH-3, PM-9, OD-2, DBA-1, PEND-4, OPEN-6,
# QA-DEC-1, and letter-suffixed instances like 13a via the bare form.
ID_RE = r"(?:[A-Z][A-Z-]{0,14}-\d+[a-z]?|\d+[a-z]{1,2})"
STATUS_RE = (r"(?:PENDING|PARKED|WATCH|DEFERRED|DECIDED|DECIDED-AUTO|"
             r"DECIDED-DEFAULT|SUPERSEDED|RESOLVED|DONE|RECORD)")
DECISIONS_RE = re.compile(rf"^(none|{ID_RE}:{STATUS_RE}(,{ID_RE}:{STATUS_RE})*)$")
TESTNUM_RE = re.compile(r"^(none|\d+/\d+(,\d+/\d+)*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FM_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written): {msg}\n")
    sys.exit(1)


def build_block(a):
    return (
        "---\n"
        "fingerprint:\n"
        f"  verdict: {a.verdict}\n"
        f"  merged: {a.merged}\n"
        f"  merged_commit: {a.merged_commit}\n"
        f"  decisions: \"{a.decisions}\"\n"
        f"  test_numbers: \"{a.test_numbers}\"\n"
        f"  qa_verdict: {a.qa_verdict}\n"
        f"verified_at: {a.verified_at}\n"
        "---\n"
    )


def parse_block(text):
    """Re-extract the fields the Step 1.5 check will grep for; returns dict
    or None. Kept deliberately grep-simple -- same extraction the checker
    (fingerprint_check.py) uses."""
    m = FM_RE.match(text)
    if not m or "fingerprint:" not in m.group(0):
        return None
    out = {}
    for line in m.group(0).splitlines():
        lm = re.match(r"\s*(verdict|merged|merged_commit|decisions|test_numbers"
                      r"|qa_verdict|verified_at):\s*(.*)$", line)
        if lm:
            out[lm.group(1)] = lm.group(2).strip().strip('"')
    return out if len(out) == 7 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch_file", nargs="?")
    ap.add_argument("--verdict", required=True, choices=sorted(VERDICTS))
    ap.add_argument("--merged", required=True, choices=["true", "false"])
    ap.add_argument("--merged-commit", dest="merged_commit", default="null")
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--test-numbers", dest="test_numbers", required=True)
    ap.add_argument("--qa-verdict", dest="qa_verdict", required=True)
    ap.add_argument("--verified-at", dest="verified_at", required=True)
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args()

    if not QA_VERDICT_RE.match(a.qa_verdict):
        die(f"qa_verdict {a.qa_verdict!r} not in ADEQUATE|GAPPED|BLIND"
            f"[ (pre-build)]|n/a")
    if not DECISIONS_RE.match(a.decisions):
        die(f"decisions {a.decisions!r} must be 'none' or comma-joined "
            f"ID:STATUS pairs (v2 status vocab; any declared ID grammar)")
    if not TESTNUM_RE.match(a.test_numbers):
        die(f"test_numbers {a.test_numbers!r} must be 'none' or comma-joined N/M")
    if not DATE_RE.match(a.verified_at):
        die(f"verified_at {a.verified_at!r} must be YYYY-MM-DD")
    if a.merged_commit != "null" and not re.match(r"^[0-9a-f]{7,40}$", a.merged_commit):
        die(f"merged_commit {a.merged_commit!r} must be a hex hash or 'null'")
    if a.merged == "true" and a.merged_commit == "null":
        sys.stderr.write("warning: merged=true with merged_commit=null -- the "
                         "Step 1.5 cheap merged re-check needs the hash\n")

    block = build_block(a)
    if parse_block(block) is None:
        die("self-check FAILED: assembled block does not re-parse (script bug)")

    if a.stdout or not a.scratch_file:
        sys.stdout.write(block)
        return

    existing = ""
    if os.path.exists(a.scratch_file):
        existing = open(a.scratch_file, encoding="utf-8").read()
        existing = FM_RE.sub("", existing, count=1)  # replace any prior block
    with open(a.scratch_file, "w", encoding="utf-8") as f:
        f.write(block + existing)

    written = open(a.scratch_file, encoding="utf-8").read()
    if parse_block(written) is None:
        die(f"self-check FAILED after write -- inspect {a.scratch_file}; "
            "the file WAS modified")
    print(f"Fingerprint written to {a.scratch_file} (validated, re-parsed clean)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Step 1.5 fingerprint re-check for team-status, as a script (workflow-audit
2026-08-14, structural 2 / scriptability F2): re-extracts the fingerprint
fields from each RESCAN-CANDIDATE item's *current* artifacts and compares
them to the fingerprint recorded in the item's scratch file -- so a
touched-but-cosmetic doc edit doesn't cost a scanner call, without the
orchestrator hand-running ~5 greps per item per run.

Fail-safe BY CONSTRUCTION: any parse failure, missing marker, old-grammar
scratch file, or script error degrades to RESCAN -- never a wrongly-trusted
SKIP. (All scratch files written before 2026-08-15 are old-grammar; the
first post-fix run therefore correctly falls back to a full rescan, once,
then converges.)

Decision extraction imports team-decisions' decisions_lib (single source of
truth for the v2 status vocabulary and block grammar) and matches ANY
declared ID grammar (DEC-n, WATCH-n, PM-n, OD-n, DBA-n, PEND-n, OPEN-n,
QA-DEC-n, letter-suffixed instances) -- not DEC-only, which could silently
SKIP an item whose WATCH/PM/OD status flipped.

Usage:
    fingerprint_check.py <target> --item <item-path> [--item ...] \
        [--repo <repo-root>] [--default-branch main]

Output, one line per item (tab-separated):
    SKIP\t<slug>\tfingerprint match (fields ...)
    RESCAN\t<slug>\t<reason -- names exactly which field(s) changed>
The changed-field reason is load-bearing: the orchestrator passes it to the
rescanning scanner and to status-lead (quick win 6d).
"""
import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "team-decisions" / "scripts"))
try:
    import decisions_lib
except Exception:
    decisions_lib = None

ID_RE = re.compile(r"^(?:[A-Z][A-Z-]{0,14}-\d+[a-z]?|\d+[a-z]{1,2})$")
FM_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def parse_fingerprint(text):
    m = FM_RE.match(text)
    if not m or "fingerprint:" not in m.group(0):
        return None
    out = {}
    for line in m.group(0).splitlines():
        lm = re.match(r"\s*(verdict|merged|merged_commit|decisions|test_numbers"
                      r"|qa_verdict|verified_at):\s*(.*)$", line)
        if lm:
            out[lm.group(1)] = lm.group(2).strip().strip('"')
    required = {"verdict", "merged", "merged_commit", "decisions",
                "test_numbers", "qa_verdict"}
    return out if required <= set(out) else None


def newest(paths):
    return max(paths, key=os.path.getmtime) if paths else None


def extract_verdict(build_report):
    if not build_report:
        return "n/a"
    for line in open(build_report, encoding="utf-8", errors="replace"):
        m = re.match(r"\*\*Verdict:\*\*\s*(GREEN-WITH-CAVEATS|GREEN|BLOCKED)",
                     line.strip())
        if m:
            return m.group(1)
    return None  # marker absent -> not extractable -> RESCAN


def extract_test_numbers(build_report):
    if not build_report:
        return "none"
    text = open(build_report, encoding="utf-8", errors="replace").read()
    nums = sorted(set(re.findall(r"\d+/\d+", text)))
    return ",".join(nums) if nums else "none"


def extract_decisions(item):
    files = sorted(
        glob.glob(os.path.join(glob.escape(item), "decisions.md")) +
        glob.glob(os.path.join(glob.escape(item), "qa", "decisions.md")) +
        glob.glob(os.path.join(glob.escape(item), "build", "**", "decisions.md"),
                  recursive=True))
    if not files:
        return "none"
    pairs = []
    for f in files:
        if decisions_lib is not None:
            blocks, _warn = decisions_lib.parse_file(f)
            for b in blocks:
                if ID_RE.match(b["id"]) and b.get("conformant"):
                    pairs.append(f"{b['id']}:{b['status']}")
                elif ID_RE.match(b["id"]):
                    return None  # nonconformant block -> not extractable
        else:
            # minimal fallback: ## <ID> heading + following **Status:** line
            content = open(f, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"^## ([A-Za-z0-9._-]+)[^\n]*\n(.*?)(?=^## |\Z)",
                                 content, re.DOTALL | re.MULTILINE):
                bid = m.group(1)
                if not ID_RE.match(bid):
                    continue
                sm = re.search(r"\*\*Status:\*\*\s*([A-Z-]+)", m.group(2))
                if not sm:
                    return None
                pairs.append(f"{bid}:{sm.group(1)}")
    return ",".join(sorted(set(pairs))) if pairs else "none"


def extract_qa_verdict(item):
    qa = os.path.join(item, "qa", "qa-assessment.md")
    if not os.path.isfile(qa):
        return "n/a"
    lines = open(qa, encoding="utf-8", errors="replace").read().splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^## Coverage verdict", line):
            for nxt in lines[i + 1:]:
                if nxt.strip():
                    m = re.search(r"(ADEQUATE|GAPPED|BLIND)(\s*\(pre-build\))?",
                                  nxt)
                    return (m.group(1) + (" (pre-build)" if m.group(2) else "")
                            ) if m else None
    return None  # file exists but marker absent -> RESCAN


def check_merged(fp, repo, default_branch):
    commit = fp.get("merged_commit", "null")
    if commit == "null":
        return fp.get("merged")  # nothing cheap to re-verify; compare as-was
    if not repo:
        return None
    r = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor",
                        commit, default_branch], capture_output=True)
    if r.returncode == 0:
        return "true"
    if r.returncode == 1:
        return "false"
    return None  # git error -> not extractable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--item", action="append", required=True,
                    help="item folder path (repeatable)")
    ap.add_argument("--repo", help="repo root for the merged re-check")
    ap.add_argument("--default-branch", default=None,
                    help="default: origin/HEAD's target, else main")
    a = ap.parse_args()

    branch = a.default_branch
    if a.repo and not branch:
        r = subprocess.run(["git", "-C", a.repo, "symbolic-ref", "--short",
                            "refs/remotes/origin/HEAD"], capture_output=True,
                           text=True)
        branch = r.stdout.strip() if r.returncode == 0 else "main"
    branch = branch or "main"

    for item in a.item:
        slug = os.path.basename(os.path.normpath(item))
        try:
            scratch = os.path.join(a.target, ".status-scratch", f"{slug}.md")
            if not os.path.isfile(scratch):
                print(f"RESCAN\t{slug}\tno prior scratch file")
                continue
            fp = parse_fingerprint(open(scratch, encoding="utf-8",
                                        errors="replace").read())
            if fp is None:
                print(f"RESCAN\t{slug}\tscratch has no valid fingerprint block "
                      f"(old grammar -- expected once, pre-2026-08-15 files)")
                continue
            br = newest(glob.glob(os.path.join(glob.escape(item), "build", "**",
                                               "build-report.md"),
                                  recursive=True))
            current = {
                "verdict": extract_verdict(br),
                "test_numbers": extract_test_numbers(br),
                "decisions": extract_decisions(item),
                "qa_verdict": extract_qa_verdict(item),
                "merged": check_merged(fp, a.repo, branch),
            }
            missing = [k for k, v in current.items() if v is None]
            if missing:
                print(f"RESCAN\t{slug}\tfield(s) not cleanly extractable from "
                      f"current artifacts: {', '.join(missing)}")
                continue
            changed = [f"{k}: {fp.get(k)!r} -> {current[k]!r}"
                       for k in current if fp.get(k) != current[k]]
            if changed:
                print(f"RESCAN\t{slug}\tchanged -- {'; '.join(changed)}")
            else:
                print(f"SKIP\t{slug}\tfingerprint match "
                      f"(verdict/decisions/test_numbers/qa_verdict/merged all "
                      f"unchanged; verified_at {fp.get('verified_at', '?')})")
        except Exception as e:  # fail-safe: never let a bug produce a SKIP
            print(f"RESCAN\t{slug}\tfingerprint check errored ({e}) -- "
                  f"failing safe")


if __name__ == "__main__":
    main()

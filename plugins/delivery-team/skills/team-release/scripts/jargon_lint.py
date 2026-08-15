#!/usr/bin/env python3
"""
Regex half of the client-facing jargon sweep (workflow-audit 2026-08-14,
SC4b). The release-lead (and optionally the orchestrator, on the scribe's
draft between Steps 2-3) was hand-building the same patterns every pass --
hash-shaped tokens, id shapes, paths. This script runs those pattern
classes; the SEMANTIC half of the sweep -- process talk, tone, whitelist
judgment calls ("is 'green' here a traffic light or a test suite?") -- stays
agent-side, per the shared rule set at
~/.claude/skills/team-release/references/client-firewall.md.

Usage:
    jargon_lint.py <file> [<file> ...] \
        [--id-pattern 'RI-\\d+'] [--id-pattern 'DEC-\\d+'] \
        [--word 'worktree']

--id-pattern (repeatable): this project's own forbidden id shapes, from
PROJECT-CONTEXT.md (defect-catalog ids, decision ids, item-code shapes).
--word (repeatable): extra literal process words to flag.

Output: one line per hit -- "<file>:<line>: [<class>] <match>".
Exit: 0 clean · 1 hits found (a hit is a REVIEW flag, not an auto-fail:
the agent judges false positives, e.g. a legitimate client word).
"""
import argparse
import re
import sys

# A hex-ish word >=7 chars containing at least one digit (avoids "efface").
HASH_RE = re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")
# Something with a path separator and a known-source-ish extension, or a
# bare filename with a code extension.
PATH_RE = re.compile(
    r"[\w~.-]*/[\w/.-]+|\b[\w-]+\.(?:md|cs|ts|tsx|js|jsx|py|sh|yml|yaml|"
    r"json|css|html|env|sql|csproj|sln)\b")
# Ticket/id-shaped: 2-6 uppercase letters, dash, digits (e.g. RI-0011, DEC-1).
TICKET_RE = re.compile(r"\b[A-Z]{2,6}[-_]\d{1,6}\b")
# Range-shaped git refs (a1b2c3d..e4f5g6h) even if each side <7 chars.
RANGE_RE = re.compile(r"\b[0-9a-f]{6,40}\.\.[0-9a-f]{6,40}\b")

PROCESS_WORDS = [
    "commit", "commits", "branch", "merge", "merged", "repo", "repository",
    "backend", "frontend", "endpoint", "controller", "migration", "refactor",
    "worktree", "pipeline", "pull request", "red-first", "green suite",
    "test suite", "unit test", "e2e", "regression test", "codebase",
    "hotfix", "staging", "diffstat", "build-report", "crosswalk",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--id-pattern", action="append", default=[],
                    help="project-specific forbidden id regex (repeatable)")
    ap.add_argument("--word", action="append", default=[],
                    help="extra literal process word to flag (repeatable)")
    args = ap.parse_args()

    id_res = [(p, re.compile(p)) for p in args.id_pattern]
    words = PROCESS_WORDS + args.word
    word_re = re.compile(
        r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b",
        re.IGNORECASE)

    hits = 0
    for path in args.files:
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except OSError as e:
            sys.exit(f"cannot read {path}: {e}")
        for n, line in enumerate(lines, 1):
            for cls, rx in ([("commit-hash", HASH_RE),
                             ("commit-range", RANGE_RE),
                             ("path/filename", PATH_RE),
                             ("id/ticket-shaped", TICKET_RE),
                             ("process-word", word_re)]
                            + [(f"project-id:{p}", rx) for p, rx in id_res]):
                for m in rx.finditer(line):
                    print(f"{path}:{n}: [{cls}] {m.group(0)}")
                    hits += 1
    if hits:
        print(f"\n{hits} hit(s) — review each (agent judgment; some may be "
              f"legitimate client language)", file=sys.stderr)
        sys.exit(1)
    print("clean — no mechanical jargon hits (semantic sweep still required)")


if __name__ == "__main__":
    main()

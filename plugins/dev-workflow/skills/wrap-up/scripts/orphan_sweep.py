#!/usr/bin/env python3
"""
orphan_sweep.py — deterministic READ-ONLY candidate detection for wrap-up's
Step 6 orphaned-effort-directory sweep (and its Step 1 read-only preview).

Given a repo path and one or more efforts-root directories, lists which
immediate subdirectories are orphan candidates by wrap-up's own conservative
rules (SKILL.md Step 6):

  candidate  = directory is EMPTY and absent from
               `git worktree list --porcelain`.

A non-empty directory (`.git` entry or not — a real worktree checkout
always has one pointing back at the main repo), or one git still
recognizes as a live worktree, is NEVER a candidate — deletion downstream
assumes "already verified empty". The script reports skipped dirs as
`live-worktree` or `not-a-candidate` with the reason, so the caller can
still surface oddities (e.g. unregistered-but-has-.git) to the user.

This script only DETECTS. It never deletes anything; deletion stays behind
wrap-up's Step 6 human gate (its output feeds `rm -rf`, which is exactly
why the gate stays — workflow-audit 2026-08-14, Structural #4 caveat).

Usage:
    orphan_sweep.py <repo-path> <efforts-root> [<efforts-root> ...]

Output: one line per subdirectory: `<verdict>\t<path>\t<detail>`, where
verdict is `candidate`, `live-worktree`, or `not-a-candidate`. Exits 0
whether or not candidates are found; non-zero only on usage/IO errors.
"""
import os
import subprocess
import sys


def registered_worktrees(repo):
    try:
        r = subprocess.run(
            ["git", "-C", repo, "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if r.returncode != 0:
        return set()
    paths = set()
    for line in r.stdout.splitlines():
        if line.startswith("worktree "):
            p = line[len("worktree "):].strip()
            paths.add(os.path.realpath(p))
    return paths


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(__doc__)
        return 2
    repo = os.path.realpath(sys.argv[1])
    if not os.path.isdir(repo):
        sys.stderr.write(f"error: repo path not a directory: {repo}\n")
        return 2
    live = registered_worktrees(repo)

    found = 0
    for root in sys.argv[2:]:
        root = os.path.realpath(root)
        if not os.path.isdir(root):
            # a missing efforts-root is a normal state, not an error
            print(f"not-a-candidate\t{root}\tefforts-root does not exist")
            continue
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if not os.path.isdir(path) or os.path.islink(path):
                continue
            real = os.path.realpath(path)
            if real == repo:
                continue
            if real in live:
                print(f"live-worktree\t{path}\tregistered in `git worktree list` — leave alone")
                continue
            try:
                entries = os.listdir(path)
            except OSError as e:
                print(f"not-a-candidate\t{path}\tunreadable ({e}) — leave alone")
                continue
            if not entries:
                print(f"candidate\t{path}\tempty + unregistered")
                found += 1
            elif ".git" in entries:
                print(f"not-a-candidate\t{path}\thas .git but unregistered — "
                      f"unusual, surface to the user, do NOT auto-delete")
            else:
                print(f"not-a-candidate\t{path}\tnon-empty ({len(entries)} "
                      f"entries, no .git) — never a candidate, leave alone")
    if found == 0:
        print("no candidates found", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

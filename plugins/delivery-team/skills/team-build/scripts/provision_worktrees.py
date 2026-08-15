#!/usr/bin/env python3
"""provision_worktrees.py — mechanical per-effort git worktree provisioning.

Usage:
    provision_worktrees.py <spec.json>
    provision_worktrees.py - <<< '{"slug": "...", "efforts_dir": "...", "repos": [...]}'

Input JSON:
    {
      "slug": "2026-08-14-example",
      "efforts_dir": "/abs/path/to/efforts",
      "repos": [
        {"path": "/abs/path/to/repo1", "touched": true},
        {"path": "/abs/path/to/repo2", "touched": false}
      ]
    }

For each repo: creates (or reuses) a per-effort worktree at
<efforts_dir>/<slug>/<repo-name> — a new `effort/<slug>` branch off the
repo's detected default branch for touched repos, a detached checkout of
that same default branch's current HEAD for untouched ones — then runs the
safety gate (`git status --porcelain`) and records the starting commit for
back-out. Emits one JSON object to stdout; never prints partial results on
one line and JSON on another.

This mechanizes `build-triage`'s own steps 6-7 (branch/worktree naming,
clean-tree check, starting-commit + back-out command) — a fixed recipe
confirmed identical across 15+ real builds by the 2026-08-14 workflow-audit
(scriptability lens). What stays agent-side, deliberately not touched here:
deciding which repos a plan actually touches, first-run repo-layout
discovery, and whether to reuse a *different* phase's worktree set (that's
a judgment call about plan intent, not a mechanical check).

Read+mutate (creates worktrees/branches) — not read-only like the sibling
`worktree` skill's `worktree_status.py`. Idempotent: re-running with the
same slug reuses an existing worktree at that path rather than recreating.
"""

import json
import os
import subprocess
import sys


def git(args, cwd=None):
    try:
        r = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def detect_default_branch(repo_path):
    code, out, _ = git(["symbolic-ref", "refs/remotes/origin/HEAD"], repo_path)
    if code == 0 and out.startswith("refs/remotes/origin/"):
        return out[len("refs/remotes/origin/"):]
    for name in ("main", "master", "trunk"):
        code, _, _ = git(
            ["rev-parse", "--verify", "--quiet", "refs/heads/" + name], repo_path
        )
        if code == 0:
            return name
    code, out, _ = git(["branch", "--show-current"], repo_path)
    return out or None


def provision_one(repo_spec, efforts_dir, slug):
    repo_path = repo_spec["path"]
    touched = bool(repo_spec.get("touched", False))
    name = os.path.basename(os.path.normpath(repo_path))
    worktree_path = os.path.join(efforts_dir, slug, name)

    result = {
        "repo": repo_path,
        "name": name,
        "worktree_path": worktree_path,
        "touched": touched,
        "reused": False,
        "error": None,
    }

    if os.path.isdir(worktree_path):
        result["reused"] = True
    else:
        base_branch = detect_default_branch(repo_path)
        if not base_branch:
            result["error"] = "could not detect a default/base branch for this repo"
            return result
        result["base_branch"] = base_branch
        os.makedirs(os.path.dirname(worktree_path), exist_ok=True)
        if touched:
            branch = f"effort/{slug}"
            code, out, err = git(
                ["worktree", "add", worktree_path, "-b", branch, base_branch],
                repo_path,
            )
            result["branch"] = branch
            result["is_new_branch"] = True
        else:
            code, out, err = git(
                ["worktree", "add", "--detach", worktree_path, base_branch],
                repo_path,
            )
            result["branch"] = None
            result["is_new_branch"] = False
        if code != 0:
            result["error"] = f"git worktree add failed: {err or out}"
            return result

    code, out, _ = git(["status", "--porcelain"], worktree_path)
    result["dirty"] = bool(out)
    result["dirty_files"] = out.splitlines() if out else []

    code, out, _ = git(["rev-parse", "HEAD"], worktree_path)
    result["starting_commit"] = out if code == 0 else None
    result["back_out_command"] = (
        f"git -C {worktree_path} reset --hard {out}" if code == 0 else None
    )

    return result


def main():
    if len(sys.argv) != 2:
        print("usage: provision_worktrees.py <spec.json | ->", file=sys.stderr)
        sys.exit(2)

    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
    spec = json.loads(raw)

    slug = spec["slug"]
    efforts_dir = spec["efforts_dir"]
    repos = spec["repos"]

    results = [provision_one(r, efforts_dir, slug) for r in repos]
    blocked = any(r.get("error") or r.get("dirty") for r in results)

    print(json.dumps({"slug": slug, "blocked": blocked, "repos": results}, indent=2))
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()

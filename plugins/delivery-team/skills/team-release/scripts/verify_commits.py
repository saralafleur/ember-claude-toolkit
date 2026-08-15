#!/usr/bin/env python3
"""
Mechanical half of the release-lead's commit fact-check (workflow-audit
2026-08-14, SC4a). An opus agent was re-typing the same per-SHA incantations
every release pass -- fetch + existence + `merge-base --is-ancestor` +
`show --stat` across up to 4 repos. This script runs that fixed recipe;
ALL judgment stays agent-side: claim-vs-diffstat wording, stale-vs-fabricated
triage, and above all whether the INPUTS are right -- a script fed the wrong
range dutifully verifies the wrong thing (a handed-down commit range has
been wrong before, undetected until a lead's own verification caught it).

Read-only against the repo apart from `git fetch` (remote-tracking refs
only; skip with --no-fetch, at the cost of ancestry only being as fresh as
the local refs -- the default fetch exists because "merged" claims have gone
stale same-day in real runs).

Subcommands:

  verify   Per-SHA report: existence, date, subject, diffstat summary, and
           whether it is an ancestor of the release branch.
             verify_commits.py verify --repo <path> --branch origin/dev \
                 <sha> [<sha> ...]
           or a multi-repo manifest (one line per repo:
           "<repo-path><TAB><branch><TAB><sha>[,<sha>...]"):
             verify_commits.py verify --manifest manifest.tsv
           Output, one line per SHA (tab-separated):
             OK           <repo> <sha> <date> <files±lines> <subject>
             NOT-ANCESTOR <repo> <sha> <date> <files±lines> <subject>
             UNKNOWN      <repo> <sha>
           Exit: 0 all OK · 1 some NOT-ANCESTOR · 2 some UNKNOWN
           (UNKNOWN dominates; mirrors git's exit 1 vs 128 distinction).

  range    Completeness-sweep enumeration: every commit in <base>..<head>
           with sha/date/diffstat/subject, oldest first. Classifying each
           (client-visible / intentionally silent) stays agent-side.
             verify_commits.py range --repo <path> <base>..<head>
           Exit: 0 (even if empty -- an empty range prints a warning).

Validated against human-verified Meridian manifests before first trusted
use (2026-08-15). Its OK lines are also the source for the
crosswalk's lead-owned Commit(s) column.
"""
import argparse
import subprocess
import sys


def run_git(repo, *args, check=False):
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True, check=check)


def fetch(repo, do_fetch):
    if not do_fetch:
        sys.stderr.write(f"# WARNING: --no-fetch — ancestry in {repo} is "
                         f"only as fresh as the local remote-tracking refs\n")
        return
    r = run_git(repo, "fetch", "--quiet")
    if r.returncode != 0:
        sys.stderr.write(f"# WARNING: git fetch failed in {repo} "
                         f"({r.stderr.strip()}) — continuing with local "
                         f"refs; treat ancestry results as possibly stale\n")


def diffstat_summary(repo, sha):
    r = run_git(repo, "show", "--stat", "--format=", sha)
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return lines[-1].strip().replace("\t", " ") if lines else "(empty diff)"


def commit_meta(repo, sha):
    r = run_git(repo, "show", "-s", "--format=%H%x09%as%x09%s", sha + "^{commit}")
    if r.returncode != 0:
        return None
    full, date, subject = r.stdout.strip().split("\t", 2)
    return full, date, subject


def verify_one(repo, branch, sha):
    meta = commit_meta(repo, sha)
    if meta is None:
        print(f"UNKNOWN\t{repo}\t{sha}")
        return "unknown"
    full, date, subject = meta
    stat = diffstat_summary(repo, full)
    anc = run_git(repo, "merge-base", "--is-ancestor", full, branch)
    if anc.returncode == 0:
        print(f"OK\t{repo}\t{full[:9]}\t{date}\t{stat}\t{subject}")
        return "ok"
    if anc.returncode == 1:
        print(f"NOT-ANCESTOR\t{repo}\t{full[:9]}\t{date}\t{stat}\t{subject}")
        return "not-ancestor"
    print(f"UNKNOWN\t{repo}\t{sha}\t(merge-base error: {anc.stderr.strip()})")
    return "unknown"


def cmd_verify(args):
    jobs = []  # (repo, branch, [shas])
    if args.manifest:
        for raw in open(args.manifest, encoding="utf-8"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                sys.exit(f"bad manifest line (need repo<TAB>branch<TAB>"
                         f"sha[,sha...]): {line!r}")
            jobs.append((parts[0], parts[1],
                         [s for s in parts[2].replace(",", " ").split() if s]))
    else:
        if not (args.repo and args.branch and args.shas):
            sys.exit("need --repo, --branch and at least one SHA "
                     "(or --manifest)")
        jobs.append((args.repo, args.branch, args.shas))

    results = []
    for repo, branch, shas in jobs:
        if run_git(repo, "rev-parse", "--git-dir").returncode != 0:
            sys.exit(f"not a git repo: {repo}")
        fetch(repo, not args.no_fetch)
        for sha in shas:
            results.append(verify_one(repo, branch, sha))
    if "unknown" in results:
        sys.exit(2)
    if "not-ancestor" in results:
        sys.exit(1)


def cmd_range(args):
    repo = args.repo
    if run_git(repo, "rev-parse", "--git-dir").returncode != 0:
        sys.exit(f"not a git repo: {repo}")
    fetch(repo, not args.no_fetch)
    r = run_git(repo, "log", "--reverse", "--format=%h%x09%as%x09%s",
                args.range)
    if r.returncode != 0:
        sys.exit(f"git log {args.range} failed: {r.stderr.strip()}")
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if not lines:
        sys.stderr.write(f"# WARNING: range {args.range} is empty — is the "
                         f"handed-down range wrong? (it has been before)\n")
        return
    for ln in lines:
        sha, date, subject = ln.split("\t", 2)
        print(f"{sha}\t{date}\t{diffstat_summary(repo, sha)}\t{subject}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="per-SHA existence/ancestry/diffstat")
    v.add_argument("--repo")
    v.add_argument("--branch", help="release branch ref, e.g. origin/dev")
    v.add_argument("--manifest", help="TSV: repo<TAB>branch<TAB>sha[,sha...]")
    v.add_argument("--no-fetch", action="store_true")
    v.add_argument("shas", nargs="*")
    v.set_defaults(func=cmd_verify)

    g = sub.add_parser("range", help="enumerate base..head with diffstats")
    g.add_argument("--repo", required=True)
    g.add_argument("--no-fetch", action="store_true")
    g.add_argument("range", help="<base>..<head>")
    g.set_defaults(func=cmd_range)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

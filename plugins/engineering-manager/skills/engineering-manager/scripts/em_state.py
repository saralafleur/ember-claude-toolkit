#!/usr/bin/env python3
"""
em_state.py -- schema-enforced author/reader for engineering-manager's
`.em-state/dispatch-state.json` and `.em-state/triage-state.json`.

The orchestrator calls this at dispatch time and after every status
transition instead of hand-writing JSON, so the state file is valid by
construction: one canonical shape (a slug-keyed map of entries), a checked
status vocabulary, and no ad hoc fields silently invented per run.

Provenance: 2026-08-14 workflow-audit (scriptability finding 2 /
artifact-contract D1 / seams F5): the schema existed only as prose and the
live files had already drifted -- triage-state.json didn't match its own
declared "same shape as dispatch-state.json plus a kind field" contract
(top-level run_date/target/... keys, a null slug, 8 delegates recorded where
the run-log counted 12), making status-resume's documented slug lookup
silently unsatisfiable; dispatch-state.json carried an undocumented ad hoc
`note` field (now a documented optional field) and two different branch
naming conventions in one run. Historical pre-script state files are left
as-is -- this script documents and enforces the canonical schema going
forward.

Canonical schema (both files; `kind` used by triage entries):
    {
      "<item-slug>": {
        "agent_id": "...",
        "status": "IN_PROGRESS|READY-TO-MERGE|BLOCKED|MERGED|FAILED|DONE",
        "dispatched_at": "YYYY-MM-DD",
        "group": "parallel-1 | sequential | single | ...",
        "branch": "...",          # dispatch entries; "" until known
        "worktree": "...",        # dispatch entries; "" until known
        "kind": "housekeeping|intake",   # triage entries only
        "note": "..."             # optional free-text, documented
      }
    }

Branch/worktree are recorded as *actuals* from the delegate's DONE: report
whenever available (team-build's provision_worktrees.py owns the naming
formula: branch `effort/<slug>`, worktree `<efforts_dir>/<slug>/<repo>`);
plan-time values are provisional predictions.

Usage:
    em_state.py init   <file>
    em_state.py update <file> <slug> [--status S] [--agent-id ID]
                       [--dispatched-at D] [--group G] [--branch B]
                       [--worktree W] [--kind K] [--note N]
    em_state.py show   <file> [<file2> ...]

`update` upserts: it creates the entry if the slug is new, else patches only
the fields given. `show` prints a compact per-entry report (and flags any
entry whose shape predates this script). Exits non-zero, writing nothing,
on any validation problem.
"""
import argparse
import json
import os
import sys

STATUS_VOCAB = {"IN_PROGRESS", "READY-TO-MERGE", "BLOCKED", "MERGED",
                "FAILED", "DONE"}
KIND_VOCAB = {"housekeeping", "intake"}
KNOWN_FIELDS = {"agent_id", "status", "dispatched_at", "group", "branch",
                "worktree", "kind", "note"}
REQUIRED_ON_CREATE = {"agent_id", "status", "dispatched_at", "group"}


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written): {msg}\n")
    sys.exit(1)


def load(path, must_exist=True):
    if not os.path.exists(path):
        if must_exist:
            die(f"{path} does not exist (run `init` first)")
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        die(f"could not parse {path}: {e}")
    if not isinstance(data, dict):
        die(f"{path} top level is not an object")
    return data


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # Self-check: re-parse before moving into place.
    with open(tmp, encoding="utf-8") as f:
        json.load(f)
    os.replace(tmp, path)


def entry_problems(slug, entry):
    """Return a list of schema problems for one entry (empty = conformant)."""
    probs = []
    if not isinstance(entry, dict):
        return [f"entry {slug!r} is not an object"]
    unknown = set(entry) - KNOWN_FIELDS
    if unknown:
        probs.append(f"unknown field(s): {sorted(unknown)}")
    status = entry.get("status")
    if status not in STATUS_VOCAB:
        probs.append(f"status {status!r} not in {sorted(STATUS_VOCAB)}")
    kind = entry.get("kind")
    if kind is not None and kind not in KIND_VOCAB:
        probs.append(f"kind {kind!r} not in {sorted(KIND_VOCAB)}")
    return probs


def cmd_init(args):
    if os.path.exists(args.file) and os.path.getsize(args.file) > 0:
        die(f"{args.file} already exists and is non-empty; refusing to "
            "clobber it (edit via `update`)")
    os.makedirs(os.path.dirname(os.path.abspath(args.file)), exist_ok=True)
    save(args.file, {})
    print(f"Initialized empty state file at {args.file}")


def cmd_update(args):
    data = load(args.file, must_exist=False)
    entry = data.get(args.slug, {})
    is_new = args.slug not in data
    patch = {
        "agent_id": args.agent_id,
        "status": args.status,
        "dispatched_at": args.dispatched_at,
        "group": args.group,
        "branch": args.branch,
        "worktree": args.worktree,
        "kind": args.kind,
        "note": args.note,
    }
    patch = {k: v for k, v in patch.items() if v is not None}
    if not patch:
        die("no fields given to update")
    merged = dict(entry)
    merged.update(patch)
    if is_new:
        missing = REQUIRED_ON_CREATE - set(merged)
        if missing:
            die(f"new entry {args.slug!r} is missing required field(s): "
                f"{sorted(missing)}")
    probs = entry_problems(args.slug, merged)
    if probs:
        die(f"entry {args.slug!r} would violate the schema: " +
            "; ".join(probs))
    data[args.slug] = merged
    os.makedirs(os.path.dirname(os.path.abspath(args.file)), exist_ok=True)
    save(args.file, data)
    verb = "Created" if is_new else "Updated"
    print(f"{verb} {args.slug} in {args.file} :: status="
          f"{merged.get('status')} (schema-checked)")


def cmd_show(args):
    any_shown = False
    for path in args.files:
        if not os.path.exists(path):
            print(f"{path}: (missing)")
            continue
        data = load(path)
        any_shown = True
        print(f"{path}: {len(data)} entr{'y' if len(data) == 1 else 'ies'}")
        for slug, entry in data.items():
            if not isinstance(entry, dict):
                print(f"  - {slug}: NONCONFORMANT (pre-script shape) "
                      f":: {type(entry).__name__}")
                continue
            probs = entry_problems(slug, entry)
            line = (f"  - {slug}: {entry.get('status', '?')}"
                    f" · {entry.get('kind') or 'dispatch'}"
                    f" · dispatched {entry.get('dispatched_at', '?')}"
                    f" · agent {entry.get('agent_id', '?')}")
            if entry.get("branch"):
                line += f" · {entry['branch']}"
            print(line)
            if probs:
                print(f"    NONCONFORMANT (pre-script shape): "
                      f"{'; '.join(probs)}")
        # A file whose top level isn't slug-keyed entries at all
        # (e.g. the pre-script 2026-08-13 triage-state.json with
        # run_date/target/... keys) will show every key as nonconformant --
        # that is the intended loud signal to consult the file by hand.
    if not any_shown:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create an empty state file")
    p_init.add_argument("file")
    p_init.set_defaults(func=cmd_init)

    p_up = sub.add_parser("update", help="upsert one entry (schema-checked)")
    p_up.add_argument("file")
    p_up.add_argument("slug")
    p_up.add_argument("--status", choices=sorted(STATUS_VOCAB))
    p_up.add_argument("--agent-id")
    p_up.add_argument("--dispatched-at")
    p_up.add_argument("--group")
    p_up.add_argument("--branch")
    p_up.add_argument("--worktree")
    p_up.add_argument("--kind", choices=sorted(KIND_VOCAB))
    p_up.add_argument("--note")
    p_up.set_defaults(func=cmd_update)

    p_show = sub.add_parser("show", help="report entries + schema drift")
    p_show.add_argument("files", nargs="+")
    p_show.set_defaults(func=cmd_show)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

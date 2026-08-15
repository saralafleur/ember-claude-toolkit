#!/usr/bin/env python3
"""
Canonical decision-block author -- the WRITE half of the script API.

Authors ONE new decision block in the canonical shape every tool in this
family (scan/lint/normalize/resolve) recognizes, and appends it to a
decisions.md. Agents authoring pipeline decisions call this instead of
hand-writing markdown, so format is correct by construction; the judgment
(what the question is, the options, the recommendation) stays entirely
with the caller.

After writing, the file is re-parsed with the shared library and the run
FAILS if the new block did not come out conformant with the requested
status -- the self-check that keeps this script honest against its own
format definition.

Usage:
    add_decision.py <file> --id DEC-7 --title "Which cache backend?" \
        [--status PENDING] [--raised YYYY-MM-DD] \
        [--question "..."] [--context "..."] \
        [--option "A — redis: fast, another service to run"] \
        [--option "B — sqlite: zero ops, slower"] \
        [--recommend "A — latency matters here"] \
        [--body "extra freeform lines"] \
        [--decided-by the user]   # only used by terminal statuses

Creates the file (with a minimal header) if it doesn't exist yet.
Refuses a duplicate block ID. Status must be from the shared vocabulary.
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decisions_lib import (  # noqa: E402
    HEADING_ID_RE, OPEN_STATUSES, STATUS_VOCAB, TERMINAL_STATUSES, parse_file,
)


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written): {msg}\n")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--id", required=True, help="block ID (leading token of the heading), e.g. DEC-7")
    ap.add_argument("--title", required=True, help="short heading text after the ID")
    ap.add_argument("--status", default="PENDING", choices=STATUS_VOCAB)
    ap.add_argument("--raised", default=None, help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--question", default=None)
    ap.add_argument("--context", default=None, help="the 'Where we're coming from' line")
    ap.add_argument("--option", action="append", default=[],
                    help="repeatable; e.g. \"A — label: tradeoff\". Mark the recommended one in --recommend instead of inline.")
    ap.add_argument("--recommend", default=None, help="recommended option + one-line reasoning")
    ap.add_argument("--body", default=None, help="extra freeform markdown lines appended inside the block")
    ap.add_argument("--decided-by", default="the user", help="only used when --status is terminal")
    args = ap.parse_args()

    if not HEADING_ID_RE.match(args.id):
        die(f"--id {args.id!r} must start with a letter and use only [A-Za-z0-9._-]")
    today = datetime.date.today().isoformat()
    raised = args.raised or today

    exists = os.path.exists(args.file)
    if exists:
        blocks, warnings = parse_file(args.file)
        if warnings:
            die(f"can't parse existing file: {warnings}")
        if any(b["id"] == args.id for b in blocks):
            die(f"block ID {args.id!r} already exists in {args.file}")
        content = open(args.file, encoding="utf-8").read()
    else:
        cycle = os.path.basename(os.path.dirname(os.path.abspath(args.file))) or "this effort"
        content = f"# Decisions — {cycle}\n"
        blocks = []

    lines = [f"## {args.id} — {args.title} — **{args.status}**", ""]
    lines.append(f"- **Status:** {args.status}")
    if args.status in TERMINAL_STATUSES and args.status != "RECORD":
        lines.append(f"- **Raised:** {raised} · **Decided:** {today} · **Decided by:** {args.decided_by}")
    elif args.status == "RECORD":
        lines.append(f"- **Raised:** {raised}")
    else:  # PENDING, PARKED, WATCH, DEFERRED
        lines.append(f"- **Raised:** {raised} · **Decided:** — · **Decided by:** —")
    if args.context:
        lines.append(f"- **Where we're coming from:** {args.context}")
    if args.question:
        lines.append(f"- **The question:** {args.question}")
    if args.option:
        lines.append("- **Options:**")
        for opt in args.option:
            lines.append(f"  - {opt}")
    if args.recommend:
        lines.append(f"- **Recommendation:** {args.recommend}")
    if args.body:
        lines.append(args.body.rstrip())
    block_text = "\n".join(lines)

    if not content.endswith("\n"):
        content += "\n"
    # A bare --- terminates the previous block for the shared parser, so the
    # new block can never be swallowed by an unterminated predecessor.
    content += f"\n---\n\n{block_text}\n"

    with open(args.file, "w", encoding="utf-8") as f:
        f.write(content)

    # Self-check: the block we just wrote must parse back conformant.
    new_blocks, warnings = parse_file(args.file)
    mine = [b for b in new_blocks if b["id"] == args.id]
    if warnings or len(mine) != 1 or not mine[0]["conformant"] or mine[0]["status"] != args.status:
        die(f"self-check FAILED after write -- inspect {args.file} "
            f"(parsed: {[{k: b[k] for k in ('id', 'status', 'conformant')} for b in mine]}); "
            "the file WAS modified")
    print(f"Added {args.file} :: {args.id} — {args.status} (block count now {len(new_blocks)}, self-check passed)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""claim_port_block.py — atomically claim + register the next free Docker
port block.

Usage:
    claim_port_block.py <registry.md> <base> <increment> <row_template>

<row_template> is the exact markdown table row this project's effort
registry expects (see team-build's `build-triage.md` step 9), with the
literal token `{PORT}` in place of the port-block value, e.g.:

    "| 2026-08-14 | my-effort | repoA,repoB | effort/my-effort | /path/a,/path/b | my-effort-stack | {PORT} | in-progress |"

Reads the registry, finds every port block already claimed by an
**active** effort (any row whose Status column isn't
`done`/`torn-down`/`merged`/`closed`), computes the next unclaimed
`<base> + <increment>*N`, substitutes it into the template, and appends
the resulting row — all under a single exclusive file lock held for the
entire read-decide-write window, so two concurrent invocations can never
both compute and claim the same block.

This exists because a real build (`shared-stack-data-isolation-followups`
effort B, per the 2026-08-14 workflow-audit's scriptability finding) had an
LLM read-then-pick the port block freehand, mid-build, and pick a block a
concurrently-running effort had already claimed — a read-check-claim race
with no atomicity between the read and the claim, and no atomicity between
the decision and the registry write. A script that decides and releases
the lock *before* the caller writes back doesn't close that race — the
write has to happen inside the same lock hold, which is what this does.

Prints the claimed port block (an integer) to stdout on success. Exits
non-zero with a message on stderr if the registry can't be parsed or
doesn't exist yet.
"""

import fcntl
import os
import re
import sys


ACTIVE_STATUSES_EXCLUDED = {"done", "torn-down", "torn down", "merged", "closed"}


def claimed_blocks(registry_text):
    """Extract every port-block number from rows whose status isn't a
    terminal one. Best-effort table parse: split each `|`-delimited row,
    look for a Status-like cell and a Port-block-like cell by position
    relative to the header."""
    lines = [l for l in registry_text.splitlines() if l.strip().startswith("|")]
    if len(lines) < 2:
        return set()

    header_cells = [c.strip().lower() for c in lines[0].strip("|").split("|")]
    try:
        port_idx = next(i for i, c in enumerate(header_cells) if "port" in c)
    except StopIteration:
        return set()
    status_idx = next((i for i, c in enumerate(header_cells) if "status" in c), None)

    claimed = set()
    for line in lines[2:]:  # skip header + separator row
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) <= port_idx:
            continue
        if status_idx is not None and len(cells) > status_idx:
            status = cells[status_idx].strip().lower()
            if status in ACTIVE_STATUSES_EXCLUDED:
                continue
        m = re.search(r"\d+", cells[port_idx])
        if m:
            claimed.add(int(m.group()))
    return claimed


def main():
    if len(sys.argv) != 5:
        print(
            "usage: claim_port_block.py <registry.md> <base> <increment> <row_template_with_{PORT}>",
            file=sys.stderr,
        )
        sys.exit(2)

    registry_path, base, increment, row_template = (
        sys.argv[1],
        int(sys.argv[2]),
        int(sys.argv[3]),
        sys.argv[4],
    )

    if "{PORT}" not in row_template:
        print("row_template must contain the literal token {PORT}", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(registry_path):
        print(f"registry not found: {registry_path}", file=sys.stderr)
        sys.exit(1)

    with open(registry_path, "r+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            text = f.read()
            claimed = claimed_blocks(text)
            n = 0
            while base + increment * n in claimed:
                n += 1
            port = base + increment * n

            row = row_template.replace("{PORT}", str(port))
            if not text.endswith("\n"):
                text += "\n"
            text += row.rstrip("\n") + "\n"

            f.seek(0)
            f.write(text)
            f.truncate()

            print(port)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


if __name__ == "__main__":
    main()

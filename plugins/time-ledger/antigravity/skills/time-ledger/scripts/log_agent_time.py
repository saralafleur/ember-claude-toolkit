#!/usr/bin/env python3
"""Append one subagent-completion record to an initiative's time-log.jsonl.

Called by team-intake / team-qa / team-build orchestration immediately after
each Agent() call's completion notification is processed. This captures the
subagent compute-time data (duration_ms / tokens / tool_uses) that the
cross-project session-transcript rollup (rollup.py) cannot see, since
background subagents never write to the user's own main-loop transcript --
see time-ledger/SKILL.md's "Known limitations" ("Main-loop time only").

One JSONL file per pipeline stage, living inside that stage's own output
folder, e.g.:
  <intake-dir>/time-log.jsonl               (team-intake stage)
  <intake-dir>/qa/time-log.jsonl            (team-qa stage)
  <intake-dir>/build/<date>-<slug>/time-log.jsonl   (team-build stage)

journey_report.py reads all three (when present) and renders one
initiative-wide "SDLC journey" artifact.

Usage (typical, right after an Agent() call's usage block arrives):
  python3 log_agent_time.py \
    --cycle-dir "<stage output dir>" \
    --phase "Evaluate" \
    --role "intake-architect" \
    --label "Architect evaluation of authentication feature request" \
    --duration-ms 258477 --tokens 70868 --tool-uses 16

For an agent that was killed/interrupted before a usage block arrived, omit
--duration-ms/--tokens/--tool-uses and pass --status killed -- the record is
kept (with nulls) so the report can show it as an honest data gap rather
than silently dropping it.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycle-dir", required=True, help="This stage's output dir")
    p.add_argument("--phase", required=True, help="Skill-defined phase/step name, e.g. 'Evaluate'")
    p.add_argument("--role", required=True, help="Subagent type, e.g. 'intake-architect'")
    p.add_argument("--label", required=True, help="The short task description given to Agent()")
    p.add_argument("--duration-ms", type=int, default=None)
    p.add_argument("--tokens", type=int, default=None)
    p.add_argument("--tool-uses", type=int, default=None)
    p.add_argument(
        "--completed-at",
        default=None,
        help="ISO8601, local or UTC; defaults to now (UTC). Use to backfill reconstructed history.",
    )
    p.add_argument(
        "--started-at",
        default=None,
        help="ISO8601; overrides the duration_ms-derived start time if given explicitly.",
    )
    p.add_argument("--status", default="completed", choices=["completed", "killed", "error"])
    args = p.parse_args()

    completed_at = (
        datetime.fromisoformat(args.completed_at) if args.completed_at else datetime.now(timezone.utc)
    )
    if args.started_at:
        started_at = datetime.fromisoformat(args.started_at)
    elif args.duration_ms is not None:
        started_at = completed_at - timedelta(milliseconds=args.duration_ms)
    else:
        started_at = None

    record = {
        "phase": args.phase,
        "role": args.role,
        "label": args.label,
        "started_at": started_at.isoformat() if started_at else None,
        "completed_at": completed_at.isoformat() if args.status != "killed" or args.duration_ms else None,
        "duration_ms": args.duration_ms,
        "tokens": args.tokens,
        "tool_uses": args.tool_uses,
        "status": args.status,
    }

    os.makedirs(args.cycle_dir, exist_ok=True)
    log_path = os.path.join(args.cycle_dir, "time-log.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")

    dur = f"{args.duration_ms / 1000:.0f}s" if args.duration_ms is not None else "unknown"
    print(f"logged: [{args.phase}] {args.role} ({dur}, {args.status}) -> {log_path}")


if __name__ == "__main__":
    main()

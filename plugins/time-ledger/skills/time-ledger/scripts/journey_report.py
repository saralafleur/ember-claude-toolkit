#!/usr/bin/env python3
"""Roll up an initiative's per-stage time-log.jsonl files into one
"SDLC journey" data payload and render it into the sdlc-journey.html
artifact template (embedding the JSON, same pattern dashboard.html uses).

An "initiative" is one team-intake cycle folder
(<project>/intake/<date>-<slug>/) plus whatever team-qa/team-build/merge
work happened inside/under it:

  <root>/time-log.jsonl                       intake stage
  <root>/qa/time-log.jsonl                     qa stage
  <root>/build/<date>-<slug>/time-log.jsonl    build stage (latest, if several)
  <root>/merge.json                            merge stage marker (hand-written
                                                once the build's branch is
                                                actually merged -- see schema
                                                note below)

Two clocks are reported per phase/stage/initiative, never conflated:
  - RUNNING TIME  = sum of every subagent's duration_ms (total compute/work,
                    what it actually cost -- can exceed wall-clock because
                    of parallel fan-out).
  - WALL-CLOCK    = real elapsed time. Reported two ways: "active" (sum of
                    contiguous blocks, gap > --gap-cap-minutes starts a new
                    block -- mirrors rollup.py's own 20-minute idle-gap-cap
                    convention) and "calendar" (raw first-start to last-end,
                    which includes any such gaps).

merge.json schema (hand-written by whoever merges, or by a future skill
step -- optional, absent means stage="not-started"):
  {"merged_at": "2026-07-18T10:00:00", "commit": "abc1234",
   "branch": "effort/...", "note": "..."}

Usage:
  python3 journey_report.py --initiative-root <path> \
    --title "Laundry run alerts" --project laundryroom-alerts \
    [--stage-note qa="Verdict: GAPPED -- frozen-frame risk tracked as xfail"]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "sdlc-journey-template.html")

STAGE_DEFS = [
    ("intake", "Intake", ""),
    ("qa", "QA", "qa"),
    ("build", "Build", "build/*"),
]


def parse_ts(s):
    if not s:
        return None
    return datetime.fromisoformat(s)


def fmt_dur(seconds):
    if seconds is None:
        return None
    seconds = max(0, seconds)
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s" if s else f"{m}m"
    return f"{s}s"


def read_records(log_path):
    records = []
    if not os.path.exists(log_path):
        return records
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def active_blocks(records, gap_cap_minutes):
    """Gap-capped contiguous wall-clock blocks, mirroring rollup.py's
    20-minute idle-gap convention. Returns (active_seconds, gaps, span)."""

    spans = []
    for r in records:
        s, e = parse_ts(r.get("started_at")), parse_ts(r.get("completed_at"))
        if s and e:
            spans.append((s, e))
    if not spans:
        return 0.0, [], None

    spans.sort(key=lambda x: x[0])
    cap = timedelta(minutes=gap_cap_minutes)
    blocks = [list(spans[0])]
    gaps = []
    for s, e in spans[1:]:
        cur_start, cur_end = blocks[-1]
        if s - cur_end > cap:
            gaps.append({"after": cur_end.isoformat(), "before": s.isoformat(), "duration_s": (s - cur_end).total_seconds()})
            blocks.append([s, e])
        else:
            blocks[-1][1] = max(cur_end, e)

    active_s = sum((b[1] - b[0]).total_seconds() for b in blocks)
    overall_span_s = (spans[-1][1] - spans[0][0]).total_seconds() if len(spans) > 1 or True else None
    # recompute overall span from true min/max across all spans, not just sorted-by-start
    all_start = min(s for s, _ in spans)
    all_end = max(e for _, e in spans)
    overall_span_s = (all_end - all_start).total_seconds()
    return active_s, gaps, {"start": all_start.isoformat(), "end": all_end.isoformat(), "seconds": overall_span_s}


def build_phase_table(records, gap_cap_minutes):
    by_phase = defaultdict(list)
    for r in records:
        by_phase[r["phase"]].append(r)

    phases = []
    for phase, recs in by_phase.items():
        running_ms = sum(r.get("duration_ms") or 0 for r in recs)
        tokens = sum(r.get("tokens") or 0 for r in recs)
        tool_uses = sum(r.get("tool_uses") or 0 for r in recs)
        active_s, _, span = active_blocks(recs, gap_cap_minutes)
        unknown = sum(1 for r in recs if r.get("duration_ms") is None)
        agents = [
            {
                "role": r["role"],
                "label": r["label"],
                "duration_ms": r.get("duration_ms"),
                "tokens": r.get("tokens"),
                "tool_uses": r.get("tool_uses"),
                "status": r.get("status", "completed"),
            }
            for r in sorted(recs, key=lambda r: r.get("started_at") or "")
        ]
        phases.append(
            {
                "name": phase,
                "agent_count": len(recs),
                "running_ms": running_ms,
                "running_label": fmt_dur(running_ms / 1000),
                "wall_ms": (span["seconds"] * 1000) if span else None,
                "wall_label": fmt_dur(span["seconds"]) if span else None,
                "tokens": tokens,
                "tool_uses": tool_uses,
                "unknown_duration_count": unknown,
                "agents": agents,
            }
        )
    # preserve first-seen order by earliest started_at within each phase
    phases.sort(key=lambda p: min((a["duration_ms"] or 0) for a in p["agents"]) if False else 0)
    # order phases by the earliest started_at of their records instead
    order = {}
    for phase, recs in by_phase.items():
        starts = [r.get("started_at") for r in recs if r.get("started_at")]
        order[phase] = min(starts) if starts else "9999"
    phases.sort(key=lambda p: order.get(p["name"], "9999"))
    return phases


def stage_status(stage_key, stage_dir, records, override_note):
    if stage_key == "intake":
        done_marker = os.path.join(stage_dir, "technical-plan.md")
        status = "done" if os.path.exists(done_marker) else ("in-progress" if records else "not-started")
    elif stage_key == "qa":
        done_marker = os.path.join(stage_dir, "test-plan.md")
        status = "done" if os.path.exists(done_marker) else ("in-progress" if records else "not-started")
        assessment = os.path.join(stage_dir, "qa-assessment.md")
        if status == "done" and os.path.exists(assessment):
            text = open(assessment).read()
            m = re.search(
                r"\*\*Coverage verdict:\*\*\s*([A-Z]+)"
                r"|Verdict:\s*\*\*([A-Z]+)\*\*"
                r"|##\s*(?:Coverage\s+)?[Vv]erdict\s*\n+\*\*([A-Z]+)\*\*",
                text,
            )
            verdict = next((g for g in (m.groups() if m else []) if g), None) if m else None
            if verdict == "GAPPED":
                status = "warning"
            elif verdict == "BLIND":
                status = "blocked"
    elif stage_key == "build":
        done_marker = os.path.join(stage_dir, "build-report.md") if stage_dir else None
        status = "done" if done_marker and os.path.exists(done_marker) else ("in-progress" if records else "not-started")
    elif stage_key == "merge":
        status = "done" if records else "not-started"
    else:
        status = "not-started" if not records else "in-progress"
    return status


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--initiative-root", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--created", default=None, help="YYYY-MM-DD; derived from folder name if omitted")
    p.add_argument("--gap-cap-minutes", type=int, default=20)
    p.add_argument("--stage-note", action="append", default=[], help="stage=note text, repeatable")
    p.add_argument("--summary", default="", help="One-line initiative synopsis")
    args = p.parse_args()

    root = os.path.abspath(args.initiative_root)
    slug = os.path.basename(root.rstrip("/"))
    created = args.created or (slug.split("-", 3)[:3] and "-".join(slug.split("-")[:3]))
    notes = dict(kv.split("=", 1) for kv in args.stage_note)

    stages_out = []
    for key, label, subpath in STAGE_DEFS:
        if subpath.endswith("*"):
            candidates = sorted(glob.glob(os.path.join(root, subpath)))
            stage_dir = candidates[-1] if candidates else os.path.join(root, subpath.rstrip("*"))
        else:
            stage_dir = os.path.join(root, subpath) if subpath else root

        records = read_records(os.path.join(stage_dir, "time-log.jsonl"))
        phases = build_phase_table(records, args.gap_cap_minutes)
        active_s, gaps, span = active_blocks(records, args.gap_cap_minutes)
        running_ms = sum(r.get("duration_ms") or 0 for r in records)
        tokens = sum(r.get("tokens") or 0 for r in records)
        tool_uses = sum(r.get("tool_uses") or 0 for r in records)
        unknown = sum(1 for r in records if r.get("duration_ms") is None)

        status = stage_status(key, stage_dir if os.path.isdir(stage_dir) else stage_dir, records, notes.get(key))

        stages_out.append(
            {
                "key": key,
                "label": label,
                "status": status,
                "note": notes.get(key, ""),
                "phases": phases,
                "totals": {
                    "agents": len(records),
                    "running_ms": running_ms,
                    "running_label": fmt_dur(running_ms / 1000),
                    "active_wall_ms": active_s * 1000,
                    "active_wall_label": fmt_dur(active_s),
                    "calendar_span": span,
                    "calendar_span_label": fmt_dur(span["seconds"]) if span else None,
                    "tokens": tokens,
                    "tool_uses": tool_uses,
                    "unknown_duration_count": unknown,
                },
                "gaps": [{**g, "duration_label": fmt_dur(g["duration_s"])} for g in gaps],
            }
        )

    # merge stage: separate, marker-file based, no time-log
    merge_marker = os.path.join(root, "merge.json")
    merge_data = json.load(open(merge_marker)) if os.path.exists(merge_marker) else None
    stages_out.append(
        {
            "key": "merge",
            "label": "Merge",
            "status": "done" if merge_data else "not-started",
            "note": notes.get("merge", ""),
            "phases": [],
            "merge": merge_data,
            "totals": {"agents": 0, "running_ms": 0, "running_label": None, "active_wall_ms": 0, "active_wall_label": None, "calendar_span": None, "calendar_span_label": None, "tokens": 0, "tool_uses": 0, "unknown_duration_count": 0},
            "gaps": [],
        }
    )

    total_running_ms = sum(s["totals"]["running_ms"] for s in stages_out)
    total_active_s = sum((s["totals"]["active_wall_ms"] or 0) / 1000 for s in stages_out)
    total_tokens = sum(s["totals"]["tokens"] for s in stages_out)
    total_agents = sum(s["totals"]["agents"] for s in stages_out)
    all_gaps = [g for s in stages_out for g in s["gaps"]]

    current_stage = next((s["key"] for s in reversed(stages_out) if s["status"] in ("done", "in-progress", "warning", "blocked")), "intake")

    data = {
        "initiative": {
            "title": args.title,
            "project": args.project,
            "slug": slug,
            "created": created,
            "summary": args.summary,
            "current_stage": current_stage,
        },
        "stages": stages_out,
        "totals": {
            "running_ms": total_running_ms,
            "running_label": fmt_dur(total_running_ms / 1000),
            "active_wall_label": fmt_dur(total_active_s),
            "tokens": total_tokens,
            "agents": total_agents,
            "parallelism_factor": round((total_running_ms / 1000) / total_active_s, 2) if total_active_s else None,
            "gap_count": len(all_gaps),
        },
        "generated_note": "Timings from live-logged agent completions where available; the pilot intake+QA stages for this initiative were reconstructed retrospectively from file timestamps (minute precision) rather than logged live.",
    }

    data_path = os.path.join(root, "journey-data.json")
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)

    template = open(TEMPLATE_PATH).read()
    compact = json.dumps(data, separators=(",", ":"))
    html = re.sub(r"const DATA = .*?;\n", lambda m: f"const DATA = {compact};\n", template, count=1)
    html = re.sub(r"<title>.*?</title>", lambda m: f"<title>{args.title} — SDLC Journey</title>", html, count=1)
    out_path = os.path.join(root, "sdlc-journey.html")
    with open(out_path, "w") as f:
        f.write(html)

    print(f"wrote {data_path}")
    print(f"wrote {out_path}")
    print(f"totals: running={data['totals']['running_label']} active_wall={data['totals']['active_wall_label']} tokens={total_tokens:,} agents={total_agents} gaps={len(all_gaps)}")


if __name__ == "__main__":
    main()

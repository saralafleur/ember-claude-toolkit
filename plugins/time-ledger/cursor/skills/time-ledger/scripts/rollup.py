#!/usr/bin/env python3
"""
Cross-project time/token/cost ledger for Claude Code sessions.

Reads every top-level session transcript under ~/.claude/projects/*/*.jsonl,
computes active-time (timestamp-gap heuristic, capped idle gaps), and
aggregates hours + token cost by project / date / ISO week / git branch.

Writes rollups.json (raw aggregates) to the output directory. Does not
touch anything outside that directory.
"""
import json
import glob
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

PROJECTS_DIR = os.path.expanduser(os.environ.get("TIME_LEDGER_PROJECTS_DIR", "~/.claude/projects"))
OUTPUT_DIR = os.path.expanduser(os.environ.get("TIME_LEDGER_OUTPUT_DIR", "~/time-ledger"))
IDLE_CAP_SECONDS = 20 * 60  # gaps longer than this don't count as active time

# Flat-fee subscription — replaces per-token billing. Configure your real
# fee/cycle via TIME_LEDGER_SUBSCRIPTION_FEE / TIME_LEDGER_ANCHOR_DAY /
# TIME_LEDGER_CURRENCY env vars; the defaults below are placeholders, not a
# real price. Only apportioned for the cycle containing "effective_from" and
# later — we don't know what (if anything) was paid for earlier cycles, so
# history before that is never retroactively priced.
SUBSCRIPTION = {
    "fee": float(os.environ.get("TIME_LEDGER_SUBSCRIPTION_FEE", "0.00")),
    "anchor_day": int(os.environ.get("TIME_LEDGER_ANCHOR_DAY", "1")),
    "currency": os.environ.get("TIME_LEDGER_CURRENCY", "USD"),
}

# $ per 1M tokens: (input, output). Cache read = input * 0.1.
# Cache write: 5m TTL = input * 1.25, 1h TTL = input * 2.0.
PRICING = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
}


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def project_label(dirname, cwd_seen):
    if cwd_seen:
        home = os.path.expanduser("~")
        p = cwd_seen
        if p.startswith(home):
            p = "~" + p[len(home):]
        return p
    return dirname


def iso_week(dt):
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def month_key(dt):
    return f"{dt.year:04d}-{dt.month:02d}"


def billing_cycle_start(dt, anchor_day=1):
    """The start (00:00 UTC) of the billing cycle dt falls in."""
    if dt.day >= anchor_day:
        year, month = dt.year, dt.month
    else:
        month = dt.month - 1
        year = dt.year
        if month == 0:
            month = 12
            year -= 1
    return datetime(year, month, anchor_day, tzinfo=timezone.utc)


def billing_cycle_end(start):
    month = start.month + 1
    year = start.year
    if month == 13:
        month = 1
        year += 1
    next_start = start.replace(year=year, month=month)
    from datetime import timedelta
    return next_start - timedelta(days=1)


def cost_for_usage(model, usage):
    if not usage or model not in PRICING:
        return 0.0
    in_rate, out_rate = PRICING[model]
    input_tok = usage.get("input_tokens", 0) or 0
    output_tok = usage.get("output_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0
    cc = usage.get("cache_creation") or {}
    write_1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
    write_5m = cc.get("ephemeral_5m_input_tokens", 0) or 0
    if not write_1h and not write_5m:
        # fall back to the flat cache_creation_input_tokens field, assume 5m
        write_5m = usage.get("cache_creation_input_tokens", 0) or 0
    cost = (
        input_tok * in_rate
        + output_tok * out_rate
        + cache_read * in_rate * 0.1
        + write_5m * in_rate * 1.25
        + write_1h * in_rate * 2.0
    ) / 1_000_000
    return cost


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    project_dirs = sorted(glob.glob(os.path.join(PROJECTS_DIR, "*/")))

    # buckets: (project) -> (date) -> {seconds, cost, tokens}
    daily = defaultdict(lambda: defaultdict(lambda: {"seconds": 0.0, "cost": 0.0, "tokens": 0}))
    weekly = defaultdict(lambda: defaultdict(lambda: {"seconds": 0.0, "cost": 0.0, "tokens": 0}))
    monthly = defaultdict(lambda: defaultdict(lambda: {"seconds": 0.0, "cost": 0.0, "tokens": 0}))
    billing = defaultdict(lambda: defaultdict(lambda: {"seconds": 0.0, "cost": 0.0, "tokens": 0}))
    branch = defaultdict(lambda: defaultdict(lambda: {"seconds": 0.0, "cost": 0.0, "tokens": 0}))
    # contiguous work sessions ("meetings") for the calendar-week view — one
    # entry per run of events with no gap over IDLE_CAP_SECONDS between them.
    blocks = []

    skipped_files = []
    total_sessions = 0

    for pdir in project_dirs:
        dirname = os.path.basename(os.path.normpath(pdir))
        if dirname == "memory":
            continue
        jsonl_files = sorted(glob.glob(os.path.join(pdir, "*.jsonl")))
        if not jsonl_files:
            continue

        cwd_seen = None
        for jf in jsonl_files:
            total_sessions += 1
            events = []  # (dt, model_or_None, usage_or_None, branch)
            try:
                with open(jf, "r", errors="ignore") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            d = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        ts = parse_ts(d.get("timestamp"))
                        if ts is None:
                            continue
                        if d.get("cwd") and cwd_seen is None:
                            cwd_seen = d.get("cwd")
                        gb = d.get("gitBranch") or "unknown"
                        model = None
                        usage = None
                        if d.get("type") == "assistant":
                            msg = d.get("message", {}) or {}
                            model = msg.get("model")
                            usage = msg.get("usage")
                        events.append((ts, model, usage, gb))
            except OSError:
                skipped_files.append(jf)
                continue

            if not events:
                continue
            events.sort(key=lambda e: e[0])

            proj = project_label(dirname, cwd_seen)

            # active-time: sum capped gaps between consecutive events
            for i in range(1, len(events)):
                prev_ts = events[i - 1][0]
                cur_ts, _, _, gb = events[i]
                gap = (cur_ts - prev_ts).total_seconds()
                if gap <= 0:
                    continue
                active = min(gap, IDLE_CAP_SECONDS)
                date_key = cur_ts.date().isoformat()
                week_key = iso_week(cur_ts)
                mon_key = month_key(cur_ts)
                bill_key = billing_cycle_start(cur_ts, SUBSCRIPTION["anchor_day"]).date().isoformat()
                daily[proj][date_key]["seconds"] += active
                weekly[proj][week_key]["seconds"] += active
                monthly[proj][mon_key]["seconds"] += active
                billing[proj][bill_key]["seconds"] += active
                branch[proj][gb]["seconds"] += active

            # tokens/cost: every assistant turn with usage
            for ts, model, usage, gb in events:
                if not usage:
                    continue
                tok = (
                    (usage.get("input_tokens", 0) or 0)
                    + (usage.get("output_tokens", 0) or 0)
                    + (usage.get("cache_read_input_tokens", 0) or 0)
                    + (usage.get("cache_creation_input_tokens", 0) or 0)
                )
                c = cost_for_usage(model, usage)
                date_key = ts.date().isoformat()
                week_key = iso_week(ts)
                mon_key = month_key(ts)
                bill_key = billing_cycle_start(ts, SUBSCRIPTION["anchor_day"]).date().isoformat()
                daily[proj][date_key]["cost"] += c
                daily[proj][date_key]["tokens"] += tok
                weekly[proj][week_key]["cost"] += c
                weekly[proj][week_key]["tokens"] += tok
                monthly[proj][mon_key]["cost"] += c
                monthly[proj][mon_key]["tokens"] += tok
                billing[proj][bill_key]["cost"] += c
                billing[proj][bill_key]["tokens"] += tok
                branch[proj][gb]["cost"] += c
                branch[proj][gb]["tokens"] += tok

            # calendar blocks: split the same event stream into contiguous
            # runs (same rule as active-time — a gap over IDLE_CAP_SECONDS
            # ends the block), keeping real start/end wall-clock times so
            # they can be drawn like calendar meetings.
            session_id = os.path.splitext(os.path.basename(jf))[0]
            cur_start = events[0][0]
            cur_end = events[0][0]
            cur_branch_counts = defaultdict(int)
            cur_tokens = 0
            cur_cost = 0.0
            cur_event_count = 0

            def flush_block(start, end, branch_counts, tok, cost, event_count):
                if start is None:
                    return
                seconds = (end - start).total_seconds()
                if seconds <= 0 and tok <= 0:
                    return
                dominant_branch = max(branch_counts.items(), key=lambda kv: kv[1])[0] if branch_counts else "unknown"
                blocks.append({
                    "project": proj,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "seconds": seconds,
                    "branch": dominant_branch,
                    "tokens": tok,
                    "cost": cost,
                    "session": session_id,
                    "event_count": event_count,
                })

            for i, (ts, model, usage, gb) in enumerate(events):
                if i > 0:
                    gap = (ts - events[i - 1][0]).total_seconds()
                    if gap > IDLE_CAP_SECONDS:
                        flush_block(cur_start, cur_end, cur_branch_counts, cur_tokens, cur_cost, cur_event_count)
                        cur_start = ts
                        cur_branch_counts = defaultdict(int)
                        cur_tokens = 0
                        cur_cost = 0.0
                        cur_event_count = 0
                cur_end = ts
                cur_branch_counts[gb] += 1
                cur_event_count += 1
                if usage:
                    cur_tokens += (
                        (usage.get("input_tokens", 0) or 0)
                        + (usage.get("output_tokens", 0) or 0)
                        + (usage.get("cache_read_input_tokens", 0) or 0)
                        + (usage.get("cache_creation_input_tokens", 0) or 0)
                    )
                    cur_cost += cost_for_usage(model, usage)
            flush_block(cur_start, cur_end, cur_branch_counts, cur_tokens, cur_cost, cur_event_count)

    blocks.sort(key=lambda b: b["start"])

    def to_plain(d):
        return {k: dict(v) for k, v in d.items()}

    # ---- billing-cycle apportionment: flat fee split by token share, vs the
    # API-equivalent cost that same usage would have priced out to. Only for
    # the cycle containing "now" and later — we don't know what (if anything)
    # was paid for cycles before this subscription was confirmed.
    now = datetime.now(timezone.utc)
    effective_from = billing_cycle_start(now, SUBSCRIPTION["anchor_day"]).date().isoformat()
    billing_out = {}
    all_cycle_keys = sorted({k for proj in billing for k in billing[proj]})
    for cycle_key in all_cycle_keys:
        if cycle_key < effective_from:
            continue
        cycle_start = datetime.fromisoformat(cycle_key).replace(tzinfo=timezone.utc)
        total_tokens = sum(billing[proj][cycle_key]["tokens"] for proj in billing if cycle_key in billing[proj])
        total_api_cost = sum(billing[proj][cycle_key]["cost"] for proj in billing if cycle_key in billing[proj])
        projects_out = {}
        for proj in billing:
            if cycle_key not in billing[proj]:
                continue
            v = billing[proj][cycle_key]
            share = (v["tokens"] / total_tokens) if total_tokens > 0 else 0.0
            actual_cost = share * SUBSCRIPTION["fee"]
            projects_out[proj] = {
                "seconds": v["seconds"],
                "tokens": v["tokens"],
                "api_equivalent_cost": v["cost"],
                "actual_cost": actual_cost,
                "savings": v["cost"] - actual_cost,
            }
        billing_out[cycle_key] = {
            "cycle_start": cycle_key,
            "cycle_end": billing_cycle_end(cycle_start).date().isoformat(),
            "fee": SUBSCRIPTION["fee"],
            "total_tokens": total_tokens,
            "total_api_equivalent_cost": total_api_cost,
            "total_actual_cost": SUBSCRIPTION["fee"],
            "total_savings": total_api_cost - SUBSCRIPTION["fee"],
            "projects": projects_out,
        }

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "idle_cap_seconds": IDLE_CAP_SECONDS,
        "total_sessions_scanned": total_sessions,
        "skipped_files": skipped_files,
        "subscription": SUBSCRIPTION,
        "daily": to_plain(daily),
        "weekly": to_plain(weekly),
        "monthly": to_plain(monthly),
        "billing_cycles": billing_out,
        "branch": to_plain(branch),
        "blocks": blocks,
    }

    out_path = os.path.join(OUTPUT_DIR, "rollups.json")
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)

    print(f"Scanned {total_sessions} session files across {len(project_dirs)} project dirs.")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

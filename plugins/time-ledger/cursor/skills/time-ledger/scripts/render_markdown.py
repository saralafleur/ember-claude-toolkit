#!/usr/bin/env python3
"""Render daily-rollup.md and weekly-rollup.md from rollups.json."""
import json
import os

OUTPUT_DIR = os.path.expanduser(os.environ.get("TIME_LEDGER_OUTPUT_DIR", "~/time-ledger"))


def hrs(seconds):
    return seconds / 3600.0


def fmt_money(x):
    return f"${x:,.2f}"


def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def render_daily(data):
    daily = data["daily"]
    dates = sorted({d for proj in daily.values() for d in proj.keys()}, reverse=True)
    lines = [
        "# Daily Time & Cost Rollup",
        "",
        f"> Generated {data['generated_at']}. Hours are a heuristic — sum of gaps between",
        f"> session messages, each capped at {data['idle_cap_seconds']//60} min so idle time",
        "> isn't counted as work. Cost is an estimate from local token usage, not a bill.",
        "> Dates are bucketed in UTC. Scope: main-loop conversation only — background/",
        "> forked subagent time is not separately double-counted.",
        "",
    ]
    for date in dates:
        rows = [(p, v[date]) for p, v in daily.items() if date in v and v[date]["seconds"] > 0]
        if not rows:
            continue
        rows.sort(key=lambda r: -r[1]["seconds"])
        day_total_h = sum(r[1]["seconds"] for r in rows) / 3600
        day_total_cost = sum(r[1]["cost"] for r in rows)
        lines.append(f"## {date} — {day_total_h:.2f}h, {fmt_money(day_total_cost)}")
        lines.append("")
        lines.append("| Project | Hours | Tokens | Est. cost |")
        lines.append("|---|---:|---:|---:|")
        for p, v in rows:
            lines.append(f"| {p} | {hrs(v['seconds']):.2f} | {fmt_tokens(v['tokens'])} | {fmt_money(v['cost'])} |")
        lines.append("")
    return "\n".join(lines)


def render_weekly(data):
    weekly = data["weekly"]
    branch = data["branch"]
    weeks = sorted({w for proj in weekly.values() for w in proj.keys()}, reverse=True)
    lines = [
        "# Weekly Time & Cost Rollup",
        "",
        f"> Generated {data['generated_at']}. Same heuristic as the daily rollup, grouped",
        "> by ISO week. Branch breakdown is per-project, all-time (not scoped to the week)",
        "> — the git branch active during each session interval.",
        "",
    ]
    for week in weeks:
        rows = [(p, v[week]) for p, v in weekly.items() if week in v and v[week]["seconds"] > 0]
        if not rows:
            continue
        rows.sort(key=lambda r: -r[1]["seconds"])
        week_total_h = sum(r[1]["seconds"] for r in rows) / 3600
        week_total_cost = sum(r[1]["cost"] for r in rows)
        lines.append(f"## {week} — {week_total_h:.2f}h, {fmt_money(week_total_cost)}")
        lines.append("")
        lines.append("| Project | Hours | Tokens | Est. cost |")
        lines.append("|---|---:|---:|---:|")
        for p, v in rows:
            lines.append(f"| {p} | {hrs(v['seconds']):.2f} | {fmt_tokens(v['tokens'])} | {fmt_money(v['cost'])} |")
        lines.append("")

        # branch breakdown for the projects active this week
        for p, _ in rows:
            branches = branch.get(p, {})
            real_branches = {b: bv for b, bv in branches.items() if bv["seconds"] > 0}
            if len(real_branches) <= 1:
                continue
            lines.append(f"**{p} — branch breakdown (all-time):**")
            lines.append("")
            lines.append("| Branch | Hours | Tokens | Est. cost |")
            lines.append("|---|---:|---:|---:|")
            for b, bv in sorted(real_branches.items(), key=lambda x: -x[1]["seconds"]):
                lines.append(f"| {b} | {hrs(bv['seconds']):.2f} | {fmt_tokens(bv['tokens'])} | {fmt_money(bv['cost'])} |")
            lines.append("")
    return "\n".join(lines)


def render_monthly(data):
    monthly = data["monthly"]
    branch = data["branch"]
    months = sorted({m for proj in monthly.values() for m in proj.keys()}, reverse=True)
    lines = [
        "# Monthly Time & Cost Rollup",
        "",
        f"> Generated {data['generated_at']}. Same heuristic as the daily rollup, grouped",
        "> by calendar month (UTC). Branch breakdown is per-project, all-time (not scoped",
        "> to the month) — the git branch active during each session interval.",
        "",
    ]
    for month in months:
        rows = [(p, v[month]) for p, v in monthly.items() if month in v and v[month]["seconds"] > 0]
        if not rows:
            continue
        rows.sort(key=lambda r: -r[1]["seconds"])
        month_total_h = sum(r[1]["seconds"] for r in rows) / 3600
        month_total_cost = sum(r[1]["cost"] for r in rows)
        lines.append(f"## {month} — {month_total_h:.2f}h, {fmt_money(month_total_cost)}")
        lines.append("")
        lines.append("| Project | Hours | Tokens | Est. cost |")
        lines.append("|---|---:|---:|---:|")
        for p, v in rows:
            lines.append(f"| {p} | {hrs(v['seconds']):.2f} | {fmt_tokens(v['tokens'])} | {fmt_money(v['cost'])} |")
        lines.append("")

        for p, _ in rows:
            branches = branch.get(p, {})
            real_branches = {b: bv for b, bv in branches.items() if bv["seconds"] > 0}
            if len(real_branches) <= 1:
                continue
            lines.append(f"**{p} — branch breakdown (all-time):**")
            lines.append("")
            lines.append("| Branch | Hours | Tokens | Est. cost |")
            lines.append("|---|---:|---:|---:|")
            for b, bv in sorted(real_branches.items(), key=lambda x: -x[1]["seconds"]):
                lines.append(f"| {b} | {hrs(bv['seconds']):.2f} | {fmt_tokens(bv['tokens'])} | {fmt_money(bv['cost'])} |")
            lines.append("")
    return "\n".join(lines)


def render_billing(data):
    sub = data.get("subscription", {})
    cycles = data.get("billing_cycles", {})
    lines = [
        "# Billing — Actual Cost vs. API-Equivalent",
        "",
        f"> Generated {data['generated_at']}. Subscription: flat "
        f"{fmt_money(sub.get('fee', 0))}/cycle, renews on day {sub.get('anchor_day')} of "
        "each month. Only cycles from the point this price was confirmed onward are shown —",
        "> earlier history isn't retroactively priced against a fee we don't know applied then.",
        "",
        "> **How the split works:** the flat fee is apportioned across projects by their share",
        "> of tokens used that cycle (so the apportioned figures always sum to exactly the fee).",
        "> \"API-equivalent\" is what that same usage would have cost on pay-per-token pricing —",
        "> savings is the gap between the two.",
        "",
    ]
    for ck in sorted(cycles.keys(), reverse=True):
        c = cycles[ck]
        lines.append(f"## {c['cycle_start']} – {c['cycle_end']}")
        lines.append("")
        lines.append(
            f"Flat fee: **{fmt_money(c['fee'])}** · API-equivalent: **{fmt_money(c['total_api_equivalent_cost'])}** · "
            f"**Savings: {fmt_money(c['total_savings'])}**"
        )
        lines.append("")
        lines.append("| Project | Tokens | API-equivalent | Actual (apportioned) | Savings |")
        lines.append("|---|---:|---:|---:|---:|")
        rows = sorted(c["projects"].items(), key=lambda x: -x[1]["tokens"])
        for p, v in rows:
            lines.append(
                f"| {p} | {fmt_tokens(v['tokens'])} | {fmt_money(v['api_equivalent_cost'])} | "
                f"{fmt_money(v['actual_cost'])} | {fmt_money(v['savings'])} |"
            )
        lines.append("")
    if not cycles:
        lines.append("_No billing cycles tracked yet since the subscription price was confirmed._")
        lines.append("")
    return "\n".join(lines)


def main():
    with open(os.path.join(OUTPUT_DIR, "rollups.json")) as fh:
        data = json.load(fh)

    with open(os.path.join(OUTPUT_DIR, "daily-rollup.md"), "w") as fh:
        fh.write(render_daily(data))
    with open(os.path.join(OUTPUT_DIR, "weekly-rollup.md"), "w") as fh:
        fh.write(render_weekly(data))
    with open(os.path.join(OUTPUT_DIR, "monthly-rollup.md"), "w") as fh:
        fh.write(render_monthly(data))
    with open(os.path.join(OUTPUT_DIR, "billing-rollup.md"), "w") as fh:
        fh.write(render_billing(data))

    print("Wrote daily-rollup.md, weekly-rollup.md, monthly-rollup.md, and billing-rollup.md")


if __name__ == "__main__":
    main()

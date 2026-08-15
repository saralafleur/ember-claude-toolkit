#!/usr/bin/env python3
"""
Deterministic scaffold for one team-intake run (SKILL.md Step 1).

Creates <intake-base>/intake/<YYYY-MM-DD>-<slug>/ plus its supporting/
subfolder, and seeds decisions.md from the skill's template so the FORMAT
CONTRACT comment lands in every per-request decision log by construction.

Same-day collision rule: if the folder already exists (a re-run or
follow-up on the same slug today), appends -2, -3, ... and prints the path
actually created. The caller MUST use the printed path.

Usage:
    init_intake.py <intake-base> <slug> [--date YYYY-MM-DD]

Prints the created intake dir path on stdout. Exits non-zero without
creating anything on a validation problem (missing base, bad slug).
"""
import argparse
import datetime
import pathlib
import re
import shutil
import sys

TEMPLATE = pathlib.Path(__file__).parent.parent / "templates" / "decision-log.md"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def die(msg):
    sys.stderr.write(f"DECLINED (nothing created): {msg}\n")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("slug")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD; default today")
    args = ap.parse_args()

    base = pathlib.Path(args.base).expanduser()
    if not base.is_dir():
        die(f"intake base folder does not exist: {base}")
    if not SLUG_RE.match(args.slug):
        die(f"slug must be kebab-case ([a-z0-9-]): {args.slug!r}")
    if args.date:
        try:
            datetime.date.fromisoformat(args.date)
        except ValueError:
            die(f"bad --date: {args.date!r}")
        date = args.date
    else:
        date = datetime.date.today().isoformat()

    name = f"{date}-{args.slug}"
    target = base / "intake" / name
    n = 1
    while target.exists():
        n += 1
        target = base / "intake" / f"{name}-{n}"

    (target / "supporting").mkdir(parents=True)
    decisions = target / "decisions.md"
    if TEMPLATE.is_file():
        shutil.copy(TEMPLATE, decisions)
        text = decisions.read_text(encoding="utf-8")
        decisions.write_text(text.replace("<slug>", args.slug),
                             encoding="utf-8")
    else:
        # minimal seed so the file still exists with a parseable shape
        decisions.write_text(
            f"# Decision Log — {args.slug}\n\n"
            "> Seeded without template (template file missing).\n",
            encoding="utf-8")
        sys.stderr.write(f"WARNING: template missing at {TEMPLATE}; "
                         "seeded minimal decisions.md\n")

    print(target)


if __name__ == "__main__":
    main()

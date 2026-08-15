#!/usr/bin/env python3
"""
Canonical release-log row author -- the WRITE half of the script API for
release-log.md (either a project-named log per PROJECT-CONTEXT.md, or the
cross-project fallback at ~/.claude/skills/team-release/memory/release-log.md).

release-lead calls this instead of hand-typing a markdown table row, so the
row is correct by construction: exact column count matching the target
file's own header, every field's embedded `|` and newlines escaped, every
cell hard-capped at 300 chars (workflow-audit 2026-08-14: hand-typed rows
grew to 1,947-3,822 chars against a written "one-line row" contract,
duplicating the crosswalk's narrative -- the narrative belongs in the
crosswalk; the Notes cell points at it), and the Status cell restricted to
the mandated tokens `HOLD — <reason>` / `CLEARED` / `SENT YYYY-MM-DD` so
"has the client been told?" stays computable.

One row per release-lead pass; the latest row per version wins.

Supports BOTH live schemas:
  8 columns (project-named log, no Project column):
    Date | Version | Status | Items bundled | Repos / commit range |
    Notes cut/added (fact-check) | Release notes | Crosswalk
  9 columns (cross-project fallback, with Project):
    Date | Project | Version | Status | ... (same tail)
The schema is detected from the target file's own header row. Creating a new
file writes the 9-column fallback header if --project is given, else the
8-column project header.

After writing, the file is re-parsed and the run FAILS if the new row is not
exactly the header's column count (same discipline as team-qa's
add_qa_run_log_row.py / team-decisions' append_decision_log_row.py).

Usage:
    append_release_log_row.py <file> --date 2026-08-15 --version v0.7.12 \
        --status "HOLD — scope pending the user" \
        --items "uat-71726-topr-fixes, topr-settings-error-handling-gap" \
        --repos "fe 805b662..dab57b8; be ce939d6..17af253" \
        --notes "1 added / 2 cut — see crosswalk" \
        --notes-link "releases/v0.7.12/release-notes.md" \
        --crosswalk "releases/v0.7.12/release-crosswalk.md" \
        [--project my-app]
"""
import argparse
import os
import re
import sys

MAX_FIELD_LEN = 300  # chars; the row-grammar brake (workflow-audit QW6).

STATUS_RE = re.compile(
    r"^(HOLD\s*[—-]\s*\S.*|CLEARED|SENT\s+\d{4}-\d{2}-\d{2})$"
)

COLS_NO_PROJECT = ["Date", "Version", "Status", "Items bundled",
                   "Repos / commit range", "Notes cut/added (fact-check)",
                   "Release notes", "Crosswalk"]
COLS_WITH_PROJECT = ["Date", "Project", "Version", "Status", "Items bundled",
                     "Repos / commit range", "Notes cut/added (fact-check)",
                     "Release notes", "Crosswalk"]

HEADER_PROJECT_LOG = """# Release Log — every version cut by team-release

> Append-only ledger. **One row per release-lead pass; the latest row per
> version wins.** Rows are appended only via
> `~/.claude/skills/team-release/scripts/append_release_log_row.py` — never
> hand-typed. Cells capped at 300 chars; the verification narrative lives in
> each release's crosswalk (Crosswalk column). **Status** is a mandated
> token: `HOLD — <short reason>` / `CLEARED` / `SENT <YYYY-MM-DD>` — "has
> the client been told?" is answered by this column, never by prose.

| Date | Version | Status | Items bundled | Repos / commit range | Notes cut/added (fact-check) | Release notes | Crosswalk |
|------|---------|--------|----------------|------------------------|------------------------------|---------------|-----------|
"""

HEADER_FALLBACK_LOG = """# Release Log (cross-project fallback, append-only)

> `release-lead` appends here **only** when the project doesn't name its own
> release-log in `PROJECT-CONTEXT.md`. One row per release-lead pass; the
> latest row per version wins. Appended only via
> `append_release_log_row.py`; cells capped at 300 chars; Status is a
> mandated token (`HOLD — <reason>` / `CLEARED` / `SENT <YYYY-MM-DD>`).

| Date | Project | Version | Status | Items bundled | Repos / commit range | Notes cut/added (fact-check) | Release notes | Crosswalk |
|------|---------|---------|--------|----------------|------------------------|------------------------------|---------------|-----------|
"""


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written): {msg}\n")
    sys.exit(1)


def escape_cell(value):
    value = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    value = value.replace("|", "\\|")
    value = " ".join(value.split())
    if len(value) > MAX_FIELD_LEN:
        die(f"cell exceeds the {MAX_FIELD_LEN}-char cap ({len(value)} chars): "
            f"{value[:80]!r}… — trim it; the narrative belongs in the "
            f"crosswalk, not the log row")
    return value


def split_cells(line):
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    cells, current, i = [], "", 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            current += "|"
            i += 2
            continue
        if body[i] == "|":
            cells.append(current.strip())
            current = ""
            i += 1
            continue
        current += body[i]
        i += 1
    cells.append(current.strip())
    return cells


def find_header_cols(content):
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("|") and "Date" in s and "Version" in s:
            return split_cells(line)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--version", required=True)
    ap.add_argument("--status", required=True,
                    help='"HOLD — <short reason>" | "CLEARED" | "SENT YYYY-MM-DD"')
    ap.add_argument("--items", required=True,
                    help="item slugs only — no narrative")
    ap.add_argument("--repos", required=True,
                    help="compact per-repo ranges, e.g. 'fe a1b2c3d..e4f5a6b; be ...'")
    ap.add_argument("--notes", required=True,
                    help="terse tally pointing at the crosswalk, e.g. "
                         "'1 added / 2 cut — see crosswalk'")
    ap.add_argument("--notes-link", required=True, help="path to release-notes.md")
    ap.add_argument("--crosswalk", required=True, help="path to release-crosswalk.md")
    ap.add_argument("--project", help="only for the cross-project fallback log")
    args = ap.parse_args()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        die(f"--date must be YYYY-MM-DD, got {args.date!r}")
    if not STATUS_RE.match(args.status):
        die(f"--status must be 'HOLD — <reason>', 'CLEARED', or "
            f"'SENT YYYY-MM-DD'; got {args.status!r}")

    exists = os.path.exists(args.file)
    if exists:
        content = open(args.file, encoding="utf-8").read()
        cols = find_header_cols(content)
        if cols is None:
            die(f"{args.file} exists but has no recognizable release-log "
                f"header row")
    else:
        content = HEADER_FALLBACK_LOG if args.project else HEADER_PROJECT_LOG
        cols = split_cells(content.splitlines()[-2])

    has_project = "Project" in cols
    if has_project and not args.project:
        die("this log has a Project column — pass --project")
    if not has_project and args.project:
        die("this log has no Project column — drop --project")
    expected = COLS_WITH_PROJECT if has_project else COLS_NO_PROJECT
    if cols != expected:
        die(f"target header columns {cols!r} don't match the expected "
            f"schema {expected!r} — this script refuses to guess; migrate "
            f"the file's header first")

    values = {
        "Date": args.date, "Version": args.version, "Status": args.status,
        "Items bundled": args.items, "Repos / commit range": args.repos,
        "Notes cut/added (fact-check)": args.notes,
        "Release notes": args.notes_link, "Crosswalk": args.crosswalk,
    }
    if has_project:
        values["Project"] = args.project
    row = "| " + " | ".join(escape_cell(values[c]) for c in cols) + " |"

    if len(split_cells(row)) != len(cols):
        die(f"assembled row did not come out to {len(cols)} columns -- a "
            f"bug in this script, not your input: {row!r}")

    if not content.endswith("\n"):
        content += "\n"
    # Keep any trailing HTML example comment above the appended row? No —
    # the log convention is newest at the bottom; append at EOF.
    content += row + "\n"
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(content)

    written = open(args.file, encoding="utf-8").read()
    last_line = [ln for ln in written.splitlines() if ln.strip()][-1]
    if last_line != row or len(split_cells(last_line)) != len(cols):
        die(f"self-check FAILED after write -- inspect {args.file} "
            f"(expected last line {row!r}, found {last_line!r}); "
            f"the file WAS modified")

    print(f"Added row to {args.file} :: {args.date} / {args.version} / "
          f"{args.status} ({len(cols)} columns, self-check passed)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Deterministic write-back for ONE resolved decision block, for
/team-decisions Step 5.

The agent does 100% of the judgment (which option, the summary phrasing,
the one-line reason); this script only performs the mechanical patch --
and ONLY for the two status conventions the scanner actively recognizes:

  1. canonical field:   `- **Status:** PENDING`  (or PARKED)
  2. heading suffix:    `## QA-3 -- ... — PENDING`  (status after the last
                        em-dash, plain or bold, nothing else in that slot)

Everything else DECLINES LOUDLY and writes nothing -- by design, not as a
gap. Status folded into prose is exactly where substring patching risks
corrupting an ID reference like PENDING-CF-3, and a team-intake-authored
block (a `### Decision` subheading with a `**Chosen:** — (pending)`
placeholder) must be filled in place, not appended to. Those stay freehand
`Edit`, per templates/resolution-block.md.

Patch performed (mirrors templates/resolution-block.md exactly):
  - status token -> DECIDED, or DECIDED-AUTO for a team-decisions
    auto-resolution (in the field line or the heading suffix)
  - `**Decided:** —` / `**Decided by:** —` placeholders filled, if that
    line exists (skip-if-absent -- heading-shape blocks often carry none)
  - `**Chosen:** ...` (+ optional `**Note from decision-maker:** "..."`)
    appended at the end of the block's existing content

Usage:
    resolve_decision.py <file> <block-id> --chosen "B — <summary>" \
        [--note "<rationale>"] [--decided-by "team-decisions (auto)"] \
        [--status DECIDED-AUTO] [--date YYYY-MM-DD] [--parked-ok]

<block-id> is the leading ID token of the block's `## ` heading, as printed
by scan_decisions.py's queue (e.g. DEC-2, QA-3, PEND-RD-1).
"""
import argparse
import datetime
import re
import sys

STATUS_OPEN_RE = re.compile(r"\b(PENDING|PARKED)\b(?!-[A-Za-z0-9])")
# Canonical field line: the value must be JUST the open-status token,
# optionally bolded / trailing period -- anything richer is declined.
FIELD_LINE_RE = re.compile(
    r"^(\s*(?:-\s*)?\*\*(?:Status|Decision):?\*\*\s*:?\s*)"
    r"(\*\*)?(PENDING|PARKED)(\*\*)?(\.?\s*)$")
# Heading suffix: text after the LAST em-dash is just the token, plain or bold.
HEADING_SUFFIX_RE = re.compile(r"^(.*—\s*)(\*\*)?(PENDING|PARKED)(\*\*)?(\s*)$")
DECIDED_PLACEHOLDER_RE = re.compile(
    r"^(?P<pre>.*\*\*Raised:?\*\*\s*:?\s*[0-9]{4}-[0-9]{2}-[0-9]{2}\s*·\s*)"
    r"\*\*Decided:?\*\*\s*:?\s*—\s*·\s*\*\*Decided by:?\*\*\s*:?\s*—\s*$")
HEADING_ID_RE = re.compile(r"^([A-Za-z][A-Za-z0-9._-]*)\b")


def die(msg):
    sys.stderr.write(f"DECLINED (nothing written -- fall back to manual Edit): {msg}\n")
    sys.exit(1)


def find_block(lines, block_id):
    """Return [(heading_idx, end_idx)] -- end exclusive, stops at next ## or bare ---."""
    blocks = []
    for i, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        heading = line[3:].strip()
        m = HEADING_ID_RE.match(heading)
        hid = m.group(1) if m else heading[:20]
        if hid != block_id:
            continue
        end = len(lines)
        for j in range(i + 1, len(lines)):
            if lines[j].startswith("## ") or lines[j].strip() == "---":
                end = j
                break
        blocks.append((i, end))
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("block_id")
    ap.add_argument("--chosen", required=True, help='e.g. "B — one-line summary of what was chosen"')
    ap.add_argument("--note", default=None, help="one-line reason this option won; omit if the Recommendation reasoning already covers it")
    ap.add_argument("--decided-by", default="team-decisions (auto)")
    ap.add_argument("--status", default="DECIDED",
                    help="target terminal status token (default DECIDED; "
                         "pass DECIDED-AUTO for a no-human-input resolution)")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--parked-ok", action="store_true",
                    help="allow resolving a PARKED block (default declines so parking isn't undone by accident)")
    args = ap.parse_args()
    today = args.date or datetime.date.today().isoformat()

    try:
        content = open(args.file, encoding="utf-8").read()
    except OSError as e:
        die(f"can't read {args.file}: {e}")
    lines = content.splitlines()

    blocks = find_block(lines, args.block_id)
    if not blocks:
        die(f"no `## ` block with ID {args.block_id!r} in {args.file}")
    if len(blocks) > 1:
        die(f"{len(blocks)} blocks share ID {args.block_id!r} -- ambiguous")
    h_idx, end_idx = blocks[0]
    block_lines = lines[h_idx:end_idx]
    block_text = "\n".join(block_lines)

    # Refuse shapes that are freehand-only by design.
    if re.search(r"^###\s+Decision\b", block_text, re.MULTILINE):
        die("block uses team-intake's `### Decision` subheading shape -- fill its "
            "placeholder lines in place (see templates/resolution-block.md carve-out)")
    if re.search(r"\*\*Chosen:?\*\*", block_text):
        die("block already contains a **Chosen:** line -- looks resolved (or partially); inspect by hand")

    # Locate exactly one recognized open-status site.
    field_hits = [(i, FIELD_LINE_RE.match(block_lines[i])) for i in range(1, len(block_lines))]
    field_hits = [(i, m) for i, m in field_hits if m]
    heading_m = HEADING_SUFFIX_RE.match(block_lines[0])

    if len(field_hits) > 1:
        die("multiple canonical Status/Decision field lines in one block")
    if not field_hits and not heading_m:
        open_tokens = STATUS_OPEN_RE.findall(block_text)
        if open_tokens:
            die("block contains PENDING/PARKED only in prose or a non-canonical shape "
                "-- prose status stays freehand by design")
        die("no recognized open-status marker (canonical field or heading suffix) found")

    if field_hits:
        i, m = field_hits[0]
        token = m.group(3)
        target = ("field", i, m)
    else:
        token = heading_m.group(3)
        target = ("heading", 0, heading_m)

    if token == "PARKED" and not args.parked_ok:
        die("block is PARKED -- pass --parked-ok if un-parking it is the deliberate intent")

    # Patch 1: status token -> args.status (preserve bold/punctuation around it).
    kind, idx, m = target
    if kind == "field":
        block_lines[idx] = f"{m.group(1)}{m.group(2) or ''}{args.status}{m.group(4) or ''}{(m.group(5) or '').rstrip()}"
    else:
        block_lines[0] = f"{m.group(1)}{m.group(2) or ''}{args.status}{m.group(4) or ''}"

    # Patch 2 (skip-if-absent): fill the `**Decided:** — · **Decided by:** —` placeholder.
    placeholder_rows = [i for i in range(1, len(block_lines))
                       if DECIDED_PLACEHOLDER_RE.match(block_lines[i])]
    if len(placeholder_rows) > 1:
        die("multiple Raised/Decided placeholder lines in one block")
    if placeholder_rows:
        i = placeholder_rows[0]
        pm = DECIDED_PLACEHOLDER_RE.match(block_lines[i])
        block_lines[i] = (f"{pm.group('pre')}**Decided:** {today} · "
                          f"**Decided by:** {args.decided_by}")
    elif re.search(r"\*\*Decided:?\*\*", block_text):
        die("a **Decided:** line exists but doesn't match the `— · —` placeholder shape -- patch it by hand")

    # Patch 3: append Chosen (+ optional Note) after the last non-empty line.
    last = len(block_lines) - 1
    while last > 0 and not block_lines[last].strip():
        last -= 1
    appended = ["", f"**Chosen:** {args.chosen}"]
    if args.note:
        appended.append(f'**Note from decision-maker:** "{args.note}"')
    block_lines[last + 1:last + 1] = appended

    new_lines = lines[:h_idx] + block_lines + lines[end_idx:]
    new_content = "\n".join(new_lines)
    if content.endswith("\n") and not new_content.endswith("\n"):
        new_content += "\n"
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Patched {args.file} :: {args.block_id}: {token} -> {args.status}, Chosen appended"
          + (", Decided/Decided-by filled" if placeholder_rows else ", no Raised/Decided placeholder (skipped)"))


if __name__ == "__main__":
    main()

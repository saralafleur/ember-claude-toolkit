#!/usr/bin/env python3
"""
Shared parsing/format core for the team-decisions script family.

This is the ONE definition of what a decision block is, what statuses
exist, and what "canonical format" means. scan_decisions.py,
lint_decisions.py, normalize_decisions.py, and add_decision.py all import
from here, so "writable," "lintable," and "scannable" are the same fact by
construction and can never drift apart.

Status vocabulary (deliberately small and literal):
  Open (walkthrough queue):      PENDING, PARKED
  Live tripwires (index only):   WATCH, DEFERRED
  Terminal:                      DECIDED, DECIDED-AUTO, DECIDED-DEFAULT,
                                 SUPERSEDED, RESOLVED, DONE, RECORD
RECORD is the terminal home for blocks that live in decisions.md by
convention but were never decisions (scope boundaries, findings notes,
narrative) -- added in v2 so every block can be conformant.

Canonical status sites (the two shapes every tool recognizes):
  1. field line:      `- **Status:** PENDING`
  2. heading suffix:  `## QA-3 — ... — PENDING`  (after the last em-dash,
                      plain or bold)
A block is "conformant" when one of those two sites yields a vocabulary
token. Everything else is a format violation (for post-cutoff files) or
legacy debt (for older files, worked off by the normalization lane).

SCANNER_VERSION gates the seal manifest: bumping it invalidates every
cached file entry, forcing one full re-verify under the new parsing logic
-- so a parser blind spot can never stay frozen into old seals. Bump it on
ANY change to parsing/classification behavior in this file.
"""
import hashlib
import json
import os
import re

SCANNER_VERSION = "2.0.0"

MANIFEST_BASENAME = ".decisions-manifest.json"
INDEX_BASENAME = "OPEN-DECISIONS.md"
# Per-root opt-out for files that match *decisions.md but are NOT
# delivery-pipeline decision logs (e.g. a machine-generated product ledger).
# One fnmatch glob per line, relative to the root; # comments allowed.
IGNORE_BASENAME = ".decisions-scan-ignore"

# Filename filter already scopes to *decisions.md, so a genuine
# build-output/dist directory never matches anyway -- don't exclude "build"
# by name, since delivery-pipeline projects use build/ as a legitimate
# pipeline-stage folder full of hand-authored decisions.md files.
EXCLUDE_DIRS = {"node_modules", ".git", "vendor", "__pycache__"}

# Longest-token-first so DECIDED-AUTO / DECIDED-DEFAULT win over bare DECIDED.
STATUS_VOCAB = [
    "DECIDED-AUTO",
    "DECIDED-DEFAULT",
    "DECIDED",
    "PARKED",
    "PENDING",
    "SUPERSEDED",
    "RESOLVED",
    "DEFERRED",
    "WATCH",
    "DONE",
    "RECORD",
]
OPEN_STATUSES = ("PENDING", "PARKED")
TRIPWIRE_STATUSES = ("WATCH", "DEFERRED")
TERMINAL_STATUSES = ("DECIDED", "DECIDED-AUTO", "DECIDED-DEFAULT",
                     "SUPERSEDED", "RESOLVED", "DONE", "RECORD")

# Word-boundary match, and NOT followed by an ASCII hyphen+alnum -- that
# pattern is an ID reference like "PENDING-CF-1" or "PENDING-C", not a
# status word. (Heading separators use an em-dash "—", not "-", so this
# doesn't clip legitimate "... — DECIDED" suffixes.)
STATUS_TOKEN_RES = [(t, re.compile(r"\b" + re.escape(t) + r"\b(?!-[A-Za-z0-9])"))
                    for t in STATUS_VOCAB]

STATUS_FIELD_RE = re.compile(r"\*\*(?:Status|Decision):?\*\*\s*:?\s*(.+)", re.IGNORECASE)
# Text after the LAST em-dash in the heading line, bold or not -- covers
# "... — DECIDED", "... — **PARKED (note)**", etc.
HEADING_LAST_DASH_RE = re.compile(r"—\s*([^—]+)$")
RAISED_RE = re.compile(r"\*\*Raised(?:/Decided)?:?\*\*\s*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)
HEADING_ID_RE = re.compile(r"^([A-Za-z][A-Za-z0-9._-]*)\b")
PATH_DATE_RE = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})")
STRIKETHROUGH_RE = re.compile(r"~~[^~]*~~")


def _load_ignore_patterns(root):
    patterns = []
    try:
        with open(os.path.join(root, IGNORE_BASENAME), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    except OSError:
        pass
    return patterns


def find_decision_files(roots):
    import fnmatch
    files = []
    for root in roots:
        patterns = _load_ignore_patterns(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                if fn.endswith("decisions.md"):
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, root)
                    if any(fnmatch.fnmatch(rel, p) for p in patterns):
                        continue
                    files.append(full)
    return sorted(files)


def normalize_status(raw_text):
    """Find the earliest-occurring known status token (word-boundary, not an ID reference).

    Strikethrough spans (~~PENDING~~ -> DECIDED style amendments) are
    stripped first so a retracted old value can't outrank the real one.
    """
    upper = STRIKETHROUGH_RE.sub("", raw_text).upper()
    best = None
    for token, pattern in STATUS_TOKEN_RES:
        m = pattern.search(upper)
        if m and (best is None or m.start() < best[1]):
            best = (token, m.start())
    return best[0] if best else None


def split_blocks(content):
    """Yield (heading_line_text, body_text, heading_lineno_1based) for each
    ## block, stopping at the next ## or a bare --- line."""
    lines = content.splitlines()
    block_start = None
    heading = None
    heading_lineno = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            if heading is not None:
                yield heading, "\n".join(lines[block_start:i]), heading_lineno
            heading = line[3:].strip()
            heading_lineno = i + 1
            block_start = i + 1
        elif line.strip() == "---" and heading is not None:
            yield heading, "\n".join(lines[block_start:i]), heading_lineno
            heading = None
            block_start = None
            heading_lineno = None
    if heading is not None:
        yield heading, "\n".join(lines[block_start:]), heading_lineno


def parse_file(path):
    """Parse one decisions.md into block dicts. Returns (blocks, warnings)."""
    try:
        content = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError) as e:
        return [], [f"{path}: UNREADABLE ({e})"]

    blocks = []
    warnings = []
    for heading, body, lineno in split_blocks(content):
        block_id_match = HEADING_ID_RE.match(heading)
        block_id = block_id_match.group(1) if block_id_match else heading[:20]

        # Try, in order: an explicit **Status:**/**Decision:** field in the
        # body, then whatever trails the last em-dash in the heading. Use
        # whichever one actually contains a known vocab token; if neither
        # does, fall back to the field text (usually more descriptive) for
        # the "Other:" label.
        field_m = STATUS_FIELD_RE.search(body)
        field_raw = field_m.group(1).strip() if field_m else None
        heading_m = HEADING_LAST_DASH_RE.search(heading)
        heading_raw = heading_m.group(1).strip() if heading_m else None

        status_norm = None
        status_raw = None
        for candidate in (field_raw, heading_raw):
            if candidate and normalize_status(candidate):
                status_norm = normalize_status(candidate)
                status_raw = candidate
                break

        conformant = status_norm is not None
        if status_norm is None:
            status_raw = field_raw or heading_raw
            status_norm = "Other: " + (status_raw[:60] if status_raw else "(unparsed - no status field or heading suffix found)")

        raised = None
        raised_inferred = False
        rm = RAISED_RE.search(body)
        if rm:
            raised = rm.group(1)
        else:
            # Fall back to the cycle-slug date in the path (e.g.
            # .../2026-07-29-cloudflare-access-amendment/...) when the
            # block itself has no explicit Raised field -- an approximation
            # for ordering only, flagged as inferred.
            pm = PATH_DATE_RE.search(path)
            if pm:
                raised = pm.group(1)
                raised_inferred = True

        full_text_upper = (heading + "\n" + body).upper()

        blocks.append({
            "file": path,
            "id": block_id,
            "heading": heading,
            "heading_lineno": lineno,
            "status_raw": status_raw,
            "status": status_norm,
            "conformant": conformant,
            "raised": raised,
            "raised_inferred": raised_inferred,
            "body": body,
            "contains_pending_text": "PENDING" in full_text_upper,
            "contains_parked_text": "PARKED" in full_text_upper,
        })
    return blocks, warnings


def file_hash(path):
    # Manifest/hash/atomic-write here (this function, load_manifest,
    # save_manifest — was lines 227-265 as of commit 82a2a73, the point of
    # copy) was lifted verbatim into New Group's tools/catalog/catalog_lib.py
    # (WATCH-3, a knowing tracked exception: a shared module is impractical
    # across the repo boundary). Any fix here must be checked against that
    # copy.
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def path_cycle_date(path):
    """The LAST cycle-slug date in the path -- the innermost cycle folder wins
    (e.g. .../2026-07-20-coaching-web-portal/build/2026-08-13-x/decisions.md
    dates to 2026-08-13). None if the path carries no date at all."""
    dates = PATH_DATE_RE.findall(path)
    return dates[-1] if dates else None


def load_manifest(path):
    """Load a seal manifest; returns {} entries on any problem (missing,
    corrupt, or written by a different scanner version -- version mismatch
    bursts every seal by design)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"scanner_version": SCANNER_VERSION, "files": {}}
    if data.get("scanner_version") != SCANNER_VERSION:
        return {"scanner_version": SCANNER_VERSION, "files": {}}
    if not isinstance(data.get("files"), dict):
        return {"scanner_version": SCANNER_VERSION, "files": {}}
    return data


def save_manifest(path, manifest):
    manifest["scanner_version"] = SCANNER_VERSION
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def summarize_blocks_for_manifest(blocks):
    """The per-file cache entry payload: everything later runs need WITHOUT
    re-parsing the file. Open blocks keep full text (they feed the
    walkthrough queue); everything else is summarized."""
    status_counts = {}
    for b in blocks:
        status_counts[b["status"]] = status_counts.get(b["status"], 0) + 1
    return {
        "status_counts": status_counts,
        "open_blocks": [
            {k: b[k] for k in ("id", "heading", "status", "raised",
                               "raised_inferred", "body")}
            for b in blocks if b["status"] in OPEN_STATUSES
        ],
        "tripwire_blocks": [
            {"id": b["id"], "heading": b["heading"], "status": b["status"],
             "raised": b["raised"]}
            for b in blocks if b["status"] in TRIPWIRE_STATUSES
        ],
        "auto_ids": [b["id"] for b in blocks if b["status"] == "DECIDED-AUTO"],
        "suspect_ids": [
            {"id": b["id"], "status": b["status"]}
            for b in blocks
            if b["status"] not in OPEN_STATUSES
            and (b["contains_pending_text"] or b["contains_parked_text"])
        ],
        "violations": [
            {"id": b["id"], "lineno": b["heading_lineno"],
             "status_raw": b["status_raw"]}
            for b in blocks if not b["conformant"]
        ],
    }

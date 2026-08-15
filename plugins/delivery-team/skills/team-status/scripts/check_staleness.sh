#!/bin/bash
# check_staleness.sh -- team-status Step 0.5 cache-validity checklist as one
# deterministic script (workflow-audit 2026-08-14, structural 2/4; the
# LLM-executed checklist had demonstrably grown blind spots -- the 2026-08-14
# team-intake mtime addition -- so the checklist now lives here, centralized).
#
# Usage:
#   check_staleness.sh <target> [-r <repo-root>]... [-s <shared-doc-path>]...
#
#   <target>    folder holding status-report.md (the cache to validate)
#   -r <repo>   a git repo to check for commits/dirty state since LAST_RUN
#               (default: the git repo containing <target>, if any). Pass one
#               -r per product-code repo named in PROJECT-CONTEXT.md.
#   -s <path>   a shared cross-team doc/dir (decision-log, defect catalog,
#               release-log, ...) named by PROJECT-CONTEXT.md. Checked via
#               git when inside a repo, else by mtime.
#
# Always also mtime-checks the family's GLOBAL-FALLBACK ledgers (they live
# outside any git repo, so git checks can't see them): team-intake
# decision-log*, team-decisions decisions-log, team-release release-log,
# engineering-manager dispatch-run-log, team-build build-run-log parts,
# team-qa qa-run-log.
#
# Self-artifact filter (structural 8): commits whose changed paths are ALL
# team-status's own artifacts (status-report.md / status-decisions.md /
# .status-scratch/*) are ignored -- otherwise every Step 4.5 commit would
# poison the next run's cache check. The find check likewise excludes
# .status-scratch/, .em-state/, and status-decisions.md.
#
# Output: "UNCHANGED" (exit 0), "HIT: ..." lines (exit 1), or
# "NO-CACHE" (exit 2, no status-report.md -- first run).
set -u

TARGET="${1:-}"
[ -z "$TARGET" ] && { echo "usage: check_staleness.sh <target> [-r repo]... [-s shared]..." >&2; exit 3; }
shift
REPOS=()
SHARED=()
while [ $# -gt 0 ]; do
  case "$1" in
    -r) REPOS+=("$2"); shift 2 ;;
    -s) SHARED+=("$2"); shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 3 ;;
  esac
done

REPORT="$TARGET/status-report.md"
[ -f "$REPORT" ] || { echo "NO-CACHE"; exit 2; }

# LAST_RUN = the cached report's mtime, ISO format (BSD/macOS date -r).
LAST_RUN="$(date -r "$REPORT" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null)" || {
  LAST_RUN="$(stat -f '%Sm' -t '%Y-%m-%dT%H:%M:%S' "$REPORT")"; }

HITS=0
hit() { echo "HIT: $*"; HITS=1; }

# Default repo: the one containing the target.
if [ ${#REPOS[@]} -eq 0 ]; then
  R="$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null)" && REPOS+=("$R")
fi

# Does this commit touch anything besides team-status's own artifacts?
commit_touches_real_change() { # $1=repo $2=hash
  git -C "$1" show --name-only --format= "$2" 2>/dev/null | while IFS= read -r p; do
    [ -z "$p" ] && continue
    case "$p" in
      */status-report.md|status-report.md) continue ;;
      */status-decisions.md|status-decisions.md) continue ;;
      */.status-scratch/*|.status-scratch/*) continue ;;
      *) echo real; break ;;
    esac
  done | grep -q real
}

# 1+2. Committed + uncommitted changes per repo, scoped to the target.
for repo in ${REPOS[@]+"${REPOS[@]}"}; do
  if git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
    scope="$TARGET"
    case "$TARGET" in "$repo"*) : ;; *) scope="." ;; esac  # target outside repo -> whole repo
    for h in $(git -C "$repo" log --since="$LAST_RUN" --format='%H' -- "$scope" 2>/dev/null); do
      if commit_touches_real_change "$repo" "$h"; then
        hit "commit $(git -C "$repo" log -1 --format='%h %s' "$h") in $repo"
      fi
    done
    dirty="$(git -C "$repo" status --porcelain -- "$scope" 2>/dev/null | grep -v -e 'status-report\.md' -e 'status-decisions\.md' -e '\.status-scratch/' | head -3)"
    [ -n "$dirty" ] && hit "uncommitted changes in $repo: $(echo "$dirty" | head -1) ..."
  else
    hit "git unavailable in $repo -- treat all items as RESCAN-CANDIDATE"
  fi
done

# Untracked/newer files under the target (excluding this skill's own outputs).
newer="$(find "$TARGET" -newer "$REPORT" -not -path '*/.status-scratch/*' \
  -not -path '*/.em-state/*' -not -name 'status-decisions.md' \
  -not -name 'status-report.md' -type f 2>/dev/null | head -5)"
[ -n "$newer" ] && while IFS= read -r f; do hit "newer than report: $f"; done <<< "$newer"

# 3. Shared cross-team docs named by PROJECT-CONTEXT.md.
for p in ${SHARED[@]+"${SHARED[@]}"}; do
  [ -e "$p" ] || continue
  prepo="$(git -C "$(dirname "$p")" rev-parse --show-toplevel 2>/dev/null)"
  if [ -n "$prepo" ]; then
    c="$(git -C "$prepo" log --since="$LAST_RUN" --oneline -1 -- "$p" 2>/dev/null)"
    [ -n "$c" ] && hit "shared doc committed-change: $p ($c)"
    d="$(git -C "$prepo" status --porcelain -- "$p" 2>/dev/null)"
    [ -n "$d" ] && hit "shared doc uncommitted-change: $p"
  else
    n="$(find "$p" -newer "$REPORT" 2>/dev/null | head -1)"
    [ -n "$n" ] && hit "shared doc newer than report (mtime): $p"
  fi
done

# 4. Global-fallback ledgers (outside git; mtime only). Generalized from the
#    team-intake-only point-fix -- workflow-audit 2026-08-14 structural 4.
SK="$HOME/.claude/skills"
for pat in \
  "$SK/team-intake/memory/decision-log*.md" \
  "$SK/team-decisions/memory/decisions-log.md" \
  "$SK/team-release/memory/release-log.md" \
  "$SK/engineering-manager/memory/dispatch-run-log.md" \
  "$SK/team-build/memory/build-run-log-INDEX.md" \
  "$SK/team-build/memory/build-run-log/"*.md \
  "$SK/team-qa/memory/qa-run-log.md" \
; do
  for f in $pat; do
    [ -f "$f" ] || continue
    [ "$f" -nt "$REPORT" ] && hit "global-fallback ledger newer than report: $f"
  done
done

if [ "$HITS" -eq 0 ]; then echo "UNCHANGED"; exit 0; fi
exit 1

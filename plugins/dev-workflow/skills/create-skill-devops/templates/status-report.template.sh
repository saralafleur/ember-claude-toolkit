#!/usr/bin/env bash
# Read-only status report for {{PROJECT}}'s devops skill. Discovers every
# scripts/*-check.sh (each invoked bare = audit-only, per
# lifecycle-check.template.sh's contract), classifies a verdict per script,
# and prints the report shape from references/status.md. Commands that
# share one check script (the build/up/down/remove/restart lifecycle set)
# collapse into one section automatically, since discovery is per-script,
# not per-verb. Never installs, fixes, or changes anything. Exits 0 always.
#
# This script is close to fully generic -- it should rarely need editing
# beyond the {{PROJECT}} label. The one thing left to Claude on top of this
# script's output: if a row's DETAIL string doesn't answer a follow-up
# question the user asks, explain further -- that's the only judgment left in
# `status`.

shopt -s nullglob

SKILL_BASE="$(cd "$(dirname "$0")/.." && pwd)"
# Deliberately do NOT `cd` into $SKILL_BASE (or anywhere else) here -- some
# check scripts (the generic check.template.sh pattern, e.g. an xcodegen or
# project.yml presence check) resolve paths relative to the caller's own
# cwd rather than doing their own PROJECT_ROOT resolution, on the
# assumption they're invoked from the project root like any other /devops
# command. Changing directory here would silently break those checks even
# though this script itself only needs $SKILL_BASE to find scripts/*.

echo "## /devops status — {{PROJECT}}"
echo

declare -a summary_rows
details=""

for check in "$SKILL_BASE"/scripts/*-check.sh; do
  [ -e "$check" ] || continue
  name="$(basename "$check" | sed 's/-check\.sh$//')"
  output="$(zsh "$check" 2>&1)"

  if echo "$output" | grep -qE '\|\s*(MISSING|WRONG)\s*\|'; then
    verdict="🔴 not set up"
    fix="$(echo "$output" | grep -E '\|\s*(MISSING|WRONG)\s*\|' | head -1 | awk -F'|' '{print $3}' | sed 's/^ *//')"
  elif echo "$output" | grep -qE '\|\s*(NEEDED|LOW)\s*\|'; then
    verdict="🟡 partial"
    fix="$(echo "$output" | grep -E '\|\s*(NEEDED|LOW)\s*\|' | head -1 | awk -F'|' '{print $3}' | sed 's/^ *//')"
  else
    verdict="✅ ready"
    fix="—"
  fi

  summary_rows+=("| $name | $verdict | $fix |")
  details="${details}### ${name}

\`\`\`
${output}
\`\`\`

"
done

echo "| Command | Verdict | Fix |"
echo "|---|---|---|"
for row in "${summary_rows[@]}"; do
  echo "$row"
done
echo
echo "$details"

# --- Git worktree & branch status ---
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "### Git worktree & branch status"
  echo
  echo "| Location | Branch | vs \`origin\` | Working tree | Merged into default? |"
  echo "|---|---|---|---|---|"

  default_branch="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##')"
  if [ -z "$default_branch" ]; then
    # origin/HEAD isn't always set locally (e.g. never `git remote set-head`
    # run) -- fall back to whichever of these actually exists as a branch.
    for candidate in main master trunk; do
      if git show-ref --verify --quiet "refs/heads/$candidate"; then
        default_branch="$candidate"
        break
      fi
    done
  fi

  git worktree list --porcelain | awk '/^worktree /{print $2}' | while read -r wt; do
    branch="$(git -C "$wt" symbolic-ref --short -q HEAD 2>/dev/null || git -C "$wt" rev-parse --short HEAD 2>/dev/null)"
    upstream="$(git -C "$wt" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"
    if [ -n "$upstream" ]; then
      counts="$(git -C "$wt" rev-list --left-right --count "$upstream...HEAD" 2>/dev/null | awk '{print "behind "$1" / ahead "$2}')"
    else
      counts="no upstream"
    fi
    dirty_count="$(git -C "$wt" status --porcelain | wc -l | tr -d ' ')"
    if [ "$dirty_count" = "0" ]; then dirty="clean"; else dirty="$dirty_count changed"; fi
    if [ "$branch" = "$default_branch" ]; then
      merged="n/a — already default"
    else
      merged="$(git -C "$wt" branch --merged "$default_branch" 2>/dev/null | grep -qE "^\*? *${branch}\$" && echo yes || echo no)"
    fi
    echo "| \`$wt\` | \`$branch\` | $counts | $dirty | $merged |"
  done
fi

exit 0

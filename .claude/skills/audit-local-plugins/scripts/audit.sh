#!/usr/bin/env bash
# Read-only audit: compare Sara's local Claude Code / Cursor installs against
# the canonical plugin sources in this repo (ember-claude-toolkit).
#
# Usage:
#   bash .claude/skills/audit-local-plugins/scripts/audit.sh [plugin-name|all]
#
# Exit 0 always (report-only). Prints a human-readable drift report.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$REPO_ROOT"

CLAUDE_SKILLS="${HOME}/.claude/skills"
CLAUDE_AGENTS="${HOME}/.claude/agents"
CURSOR_SKILLS="${HOME}/.cursor/skills"
CURSOR_AGENTS="${HOME}/.cursor/agents"

SCOPE="${1:-all}"

# Count buckets for the summary footer
COUNT_LIVE=0
COUNT_SAME=0
COUNT_DRIFTED=0
COUNT_MISSING_LOCAL=0
COUNT_MISSING_KIT=0
COUNT_LOCAL_ONLY=0

# Collect mapped local skill names so we can spot local-only leftovers
declare -a MAPPED_SKILL_NAMES=()

is_under_repo() {
  local target="$1"
  case "$target" in
    "$REPO_ROOT"/*) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_link() {
  # macOS: readlink -f is not portable; prefer python for a realpath
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1" 2>/dev/null \
    || readlink "$1" 2>/dev/null \
    || echo "$1"
}

# Classify a local path relative to a kit path.
# Prints: STATUS<TAB>detail
# STATUS is one of: LIVE | SAME | DRIFTED | MISSING_LOCAL | MISSING_KIT
classify_pair() {
  local local_path="$1"
  local kit_path="$2"

  if [ ! -e "$kit_path" ]; then
    printf '%s\t%s\n' "MISSING_KIT" "kit path missing: $kit_path"
    return
  fi
  if [ ! -e "$local_path" ] && [ ! -L "$local_path" ]; then
    printf '%s\t%s\n' "MISSING_LOCAL" "no local install at $local_path"
    return
  fi

  if [ -L "$local_path" ]; then
    local target
    target="$(resolve_link "$local_path")"
    if is_under_repo "$target"; then
      # Symlink into this repo — live, whether or not it points at kit_path exactly
      # (plugin-root symlink covers nested skills/agents).
      printf '%s\t%s\n' "LIVE" "symlink → $target"
      return
    fi
    printf '%s\t%s\n' "DRIFTED" "symlink → $target (outside this repo)"
    return
  fi

  if diff -rq "$local_path" "$kit_path" >/dev/null 2>&1; then
    printf '%s\t%s\n' "SAME" "content identical"
    return
  fi

  local local_mtime kit_mtime
  local_mtime="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$local_path" 2>/dev/null || stat -c '%y' "$local_path" 2>/dev/null | cut -c1-16 || echo "?")"
  kit_mtime="$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$kit_path" 2>/dev/null || stat -c '%y' "$kit_path" 2>/dev/null | cut -c1-16 || echo "?")"
  printf '%s\t%s\n' "DRIFTED" "local mtime $local_mtime | kit mtime $kit_mtime"
}

# Print a compact file-level diff list (no content). Caps at 40 lines.
print_diff_files() {
  local local_path="$1"
  local kit_path="$2"
  local diff_out total
  # diff returns 1 when files differ — that is expected, not a script failure
  diff_out="$(diff -rq "$local_path" "$kit_path" 2>/dev/null || true)"
  total="$(printf '%s\n' "$diff_out" | grep -c . || true)"
  printf '%s\n' "$diff_out" | head -40 | while IFS= read -r line; do
    [ -n "$line" ] && echo "      $line"
  done
  if [ "${total:-0}" -gt 40 ]; then
    echo "      … and $((total - 40)) more"
  fi
}

bump() {
  case "$1" in
    LIVE) COUNT_LIVE=$((COUNT_LIVE + 1)) ;;
    SAME) COUNT_SAME=$((COUNT_SAME + 1)) ;;
    DRIFTED) COUNT_DRIFTED=$((COUNT_DRIFTED + 1)) ;;
    MISSING_LOCAL) COUNT_MISSING_LOCAL=$((COUNT_MISSING_LOCAL + 1)) ;;
    MISSING_KIT) COUNT_MISSING_KIT=$((COUNT_MISSING_KIT + 1)) ;;
  esac
}

report_pair() {
  local kind="$1"       # skill | agent | cursor-skill | cursor-agent
  local name="$2"
  local local_path="$3"
  local kit_path="$4"
  local result status detail
  result="$(classify_pair "$local_path" "$kit_path")"
  status="$(printf '%s\n' "$result" | cut -f1)"
  detail="$(printf '%s\n' "$result" | cut -f2-)"
  bump "$status"
  echo "  [$kind] $name"
  echo "    status: $status"
  echo "    local:  $local_path"
  echo "    kit:    $kit_path"
  [ -n "$detail" ] && echo "    note:   $detail"
  if [ "$status" = "DRIFTED" ] && [ -e "$local_path" ] && [ -e "$kit_path" ]; then
    echo "    files:"
    print_diff_files "$local_path" "$kit_path"
  fi
}

should_audit_plugin() {
  local name="$1"
  if [ "$SCOPE" = "all" ]; then
    return 0
  fi
  [ "$SCOPE" = "$name" ]
}

echo "repo:    $REPO_ROOT"
echo "scope:   $SCOPE"
echo "claude:  $CLAUDE_SKILLS  +  $CLAUDE_AGENTS"
echo "cursor:  $CURSOR_SKILLS  +  $CURSOR_AGENTS"
echo

for plugin_dir in "$REPO_ROOT"/plugins/*/; do
  [ -d "$plugin_dir" ] || continue
  plugin="$(basename "$plugin_dir")"
  should_audit_plugin "$plugin" || continue

  echo "== plugin: $plugin =="

  # --- plugin-root symlink (Claude @skills-dir style) ---
  # A real plugin-root install is either a symlink into this repo's
  # plugins/<name>, or a directory that looks like a plugin (has skills/
  # and/or .claude-plugin/). A flat skill folder that happens to share the
  # plugin's name (e.g. ~/.claude/skills/librarian with a SKILL.md) is NOT
  # a plugin-root install — that case is reported under [claude-skill].
  plugin_link="${CLAUDE_SKILLS}/${plugin}"
  if [ -L "$plugin_link" ] || [ -d "$plugin_link/skills" ] || [ -d "$plugin_link/.claude-plugin" ]; then
    result="$(classify_pair "$plugin_link" "$plugin_dir")"
    status="$(printf '%s\n' "$result" | cut -f1)"
    detail="$(printf '%s\n' "$result" | cut -f2-)"
    bump "$status"
    echo "  [plugin-link] ~/.claude/skills/${plugin}"
    echo "    status: $status"
    echo "    note:   $detail"
  elif [ -e "$plugin_link" ]; then
    echo "  [plugin-link] ~/.claude/skills/${plugin}"
    echo "    status: NOT_PLUGIN_ROOT"
    echo "    note:   local path exists but looks like a flat skill/copy, not a plugin-root install — see [claude-skill] rows"
  else
    echo "  [plugin-link] ~/.claude/skills/${plugin}"
    echo "    status: MISSING_LOCAL"
    echo "    note:   no plugin-root symlink/copy (flat skill installs may still exist)"
    bump "MISSING_LOCAL"
  fi

  # --- Claude canonical skills ---
  if [ -d "${plugin_dir}skills" ]; then
    for skill_dir in "${plugin_dir}skills"/*/; do
      [ -d "$skill_dir" ] || continue
      skill="$(basename "$skill_dir")"
      MAPPED_SKILL_NAMES+=("$skill")
      report_pair "claude-skill" "$skill" \
        "${CLAUDE_SKILLS}/${skill}" \
        "$skill_dir"
    done
  fi

  # --- Claude agents (flat files in ~/.claude/agents) ---
  if [ -d "${plugin_dir}agents" ]; then
    shopt -s nullglob
    for agent_file in "${plugin_dir}agents"/*.md; do
      agent="$(basename "$agent_file")"
      report_pair "claude-agent" "$agent" \
        "${CLAUDE_AGENTS}/${agent}" \
        "$agent_file"
    done
    shopt -u nullglob
  fi

  # --- Cursor port ---
  if [ -d "${plugin_dir}cursor" ]; then
    if [ -d "${plugin_dir}cursor/skills" ]; then
      for skill_dir in "${plugin_dir}cursor/skills"/*/; do
        [ -d "$skill_dir" ] || continue
        skill="$(basename "$skill_dir")"
        report_pair "cursor-skill" "$skill" \
          "${CURSOR_SKILLS}/${skill}" \
          "$skill_dir"
      done
    fi
    if [ -d "${plugin_dir}cursor/agents" ]; then
      shopt -s nullglob
      for agent_file in "${plugin_dir}cursor/agents"/*.md; do
        agent="$(basename "$agent_file")"
        # Cursor agents may be flat .md files in ~/.cursor/agents/
        report_pair "cursor-agent" "$agent" \
          "${CURSOR_AGENTS}/${agent}" \
          "$agent_file"
      done
      shopt -u nullglob
    fi
  else
    echo "  [cursor] no cursor/ port in this plugin"
  fi

  echo
done

# --- Local skills that are not part of any kit plugin ---
if [ "$SCOPE" = "all" ] && [ -d "$CLAUDE_SKILLS" ]; then
  echo "== local-only Claude skills (not mapped to any kit plugin) =="
  found_local_only=0
  for local_skill in "$CLAUDE_SKILLS"/*/; do
    [ -d "$local_skill" ] || [ -L "${local_skill%/}" ] || continue
    name="$(basename "$local_skill")"
    # Skip if it matches a plugin name (plugin-root link) or a mapped skill name
    mapped=0
    if [ -d "$REPO_ROOT/plugins/$name" ]; then
      mapped=1
    fi
    for s in "${MAPPED_SKILL_NAMES[@]+"${MAPPED_SKILL_NAMES[@]}"}"; do
      if [ "$s" = "$name" ]; then
        mapped=1
        break
      fi
    done
    if [ "$mapped" -eq 0 ]; then
      echo "  - $name"
      found_local_only=1
      COUNT_LOCAL_ONLY=$((COUNT_LOCAL_ONLY + 1))
    fi
  done
  if [ "$found_local_only" -eq 0 ]; then
    echo "  (none)"
  fi
  echo
fi

echo "== summary =="
echo "  LIVE (symlink into this repo):  $COUNT_LIVE"
echo "  SAME (identical copy):          $COUNT_SAME"
echo "  DRIFTED (content differs):      $COUNT_DRIFTED"
echo "  MISSING_LOCAL (kit has, local doesn't): $COUNT_MISSING_LOCAL"
echo "  MISSING_KIT (local has, kit doesn't — pair path): $COUNT_MISSING_KIT"
echo "  local-only skills (unmapped):   $COUNT_LOCAL_ONLY"
echo
if [ "$COUNT_DRIFTED" -gt 0 ]; then
  echo "action needed: review DRIFTED items with Sara — promote local→kit, reinstall kit→local, or skip."
else
  echo "no content drift detected for scoped plugins."
fi

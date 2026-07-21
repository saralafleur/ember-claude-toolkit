#!/usr/bin/env bash
# Read-only audit for the refresh-plugins skill.
# Reports, per plugin under plugins/<name>: whether it has uncommitted changes,
# whether its manifest validates, its current version, and its last release tag.
set -euo pipefail
cd "$(dirname "$0")/../../../.."

echo "== marketplace manifest =="
claude plugin validate . || true
echo

for plugin_dir in plugins/*/; do
  name=$(basename "$plugin_dir")
  manifest="${plugin_dir}.claude-plugin/plugin.json"
  [ -f "$manifest" ] || continue

  version=$(node -pe "require('./${manifest}').version" 2>/dev/null || echo "unknown")
  last_tag=$(git tag -l "${name}--v*" --sort=-v:refname | head -1)
  last_tag=${last_tag:-none}

  if git diff --quiet HEAD -- "$plugin_dir" 2>/dev/null && git diff --quiet --cached -- "$plugin_dir" 2>/dev/null; then
    dirty="clean"
  else
    dirty="CHANGED"
  fi

  echo "== plugin: $name =="
  echo "  version:    $version"
  echo "  last tag:   $last_tag"
  echo "  working tree: $dirty"
  claude plugin validate "$plugin_dir" 2>&1 | sed 's/^/  /'
  echo
done

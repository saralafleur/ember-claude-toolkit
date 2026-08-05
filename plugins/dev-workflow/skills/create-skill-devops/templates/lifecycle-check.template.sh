#!/usr/bin/env bash
# Read-only audit of build/run state for {{PROJECT}}'s lifecycle solutions.
# Shared by the build/up/down/remove commands. Prints one
# "KEY | STATUS | DETAIL" line per check; exits 0 always. Safe to run any
# time — changes nothing.

shopt -s nullglob

SKILL_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
PROJECT_ROOT="$SKILL_ROOT"

# Prefer the worktree we're actually invoked from (e.g. an isolated
# team-build effort worktree), not this skill's own checkout -- both share
# the same git-common-dir, so compare that rather than trusting $PWD alone.
if PWD_TOPLEVEL="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)"; then
  PWD_COMMON="$(cd "$PWD" && cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd)"
  SKILL_COMMON="$(cd "$SKILL_ROOT" && cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd)"
  [ -n "$PWD_COMMON" ] && [ "$PWD_COMMON" = "$SKILL_COMMON" ] && PROJECT_ROOT="$PWD_TOPLEVEL"
fi

cd "$PROJECT_ROOT" || exit 0

line() { printf '%-24s | %-8s | %s\n' "$1" "$2" "$3"; }

# --- One block per solution; pattern for a docker-compose service: ---
# NOTE: `docker compose images` only lists images tied to CREATED
# containers — it reports empty for a service that's been built but never
# run. Use `docker compose config --images` (reads the compose file, no
# container needed) + `docker image inspect` instead:
#
# is_built() {
#   local image
#   image="$(docker compose config --images "$1" 2>/dev/null)"
#   [ -n "$image" ] && docker image inspect "$image" >/dev/null 2>&1
# }
# is_running() { docker compose ps --services --status running 2>/dev/null | grep -qx "$1"; }
#
# if is_built {{service}}; then line "{{solution}}-image" "ok" "built"
# else line "{{solution}}-image" "absent" "not built yet — run: /devops build {{solution}}"; fi
#
# if is_running {{service}}; then line "{{solution}}-running" "info" "running ({{address}})"
# else line "{{solution}}-running" "info" "not running"; fi
#
# For solutions gated behind a compose profile, prefix compose calls with
# `docker compose --profile {{profile}} ...` so they resolve (needed for
# `ps`/`up`/`down`; `config --images` resolves profiled services either way).
# For a pulled (not locally built) image, check `docker images -q {{image:tag}}`
# directly instead of going through compose at all.

# --- One block per solution; pattern for a native process managed by a
# --- dev script with PID-file bookkeeping (e.g. scripts/dev.sh up/down):
#
# is_built() { [[ -x {{path to built binary, e.g. tools/x/x}} ]] && [[ -d {{venv dir, e.g. .venv}} ]]; }
# is_running() { [[ -f {{pidfile, e.g. .x-native.pid}} ]] && kill -0 "$(cat {{pidfile}})" 2>/dev/null; }
#
# if is_built; then line "{{solution}}-build" "ok" "built"
# else line "{{solution}}-build" "absent" "not built yet -- run: /devops build {{solution}}"; fi
#
# if is_running; then line "{{solution}}-running" "info" "running, PID $(cat {{pidfile}})"
# else line "{{solution}}-running" "info" "not running"; fi
#
# If the project already has its own status command (e.g. `scripts/dev.sh
# status`) that reads the same PID files, this block should read the PID
# files directly rather than shelling out to it -- keep the audit read-only
# and independent of the dev script's own output format.

exit 0

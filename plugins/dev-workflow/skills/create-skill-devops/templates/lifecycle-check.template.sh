#!/usr/bin/env bash
# Audit + action script for {{PROJECT}}'s lifecycle solutions.
# Bare invocation (no args): read-only audit, prints one "KEY | STATUS |
# DETAIL" line per solution, exits 0 always. Safe to run any time.
#
# With an action argument -- `<script> <action> <solution>` -- runs that
# action, then re-runs the audit so the caller sees the result:
#   build   <solution>            build the artifact, don't start anything
#   up      <solution>            start; blocks until healthy or times out
#   down    <solution>            stop; build artifact untouched
#   restart <solution>            down + up (same health wait/timeout as up)
#   remove  <solution> --plan     read-only: print what would be deleted
#   remove  <solution> --apply [--purge-data]   actually delete
#
# This script never asks a question -- the human gate on `remove` (and the
# data-purge sub-gate) is the calling agent's job, every run, BEFORE
# `--apply` is invoked. `--plan` is what the agent shows in that gate.
#
# On `up`/`restart` failure to become healthy, this script exits non-zero
# and dumps the tail of the relevant log to stderr -- the agent's job is to
# read and explain that dump, not to guess what to check.

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

# ============================================================================
# 1. Per-solution build/run checks -- one is_built()/is_running() pair per
#    solution. Unchanged from the audit-only version of this script.
# ============================================================================
#
# --- Docker Compose pattern ---
# NOTE: `docker compose images` only lists images tied to CREATED
# containers -- it reports empty for a service that's been built but never
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
# For solutions gated behind a compose profile, prefix compose calls with
# `docker compose --profile {{profile}} ...` so they resolve (needed for
# `ps`/`up`/`down`; `config --images` resolves profiled services either way).
# For a pulled (not locally built) image, check `docker images -q {{image:tag}}`
# directly instead of going through compose at all.
#
# --- Native PID-file pattern ---
# is_built() { [[ -x {{path to built binary, e.g. tools/x/x}} ]] && [[ -d {{venv dir, e.g. .venv}} ]]; }
# is_running() { [[ -f {{pidfile, e.g. .x-native.pid}} ]] && kill -0 "$(cat {{pidfile}})" 2>/dev/null; }

audit() {
  # One block per solution -- pattern:
  # if is_built {{service-or-check-arg}}; then line "{{solution}}-image" "ok" "built"
  # else line "{{solution}}-image" "absent" "not built yet — run: /devops build {{solution}}"; fi
  #
  # if is_running {{service-or-check-arg}}; then line "{{solution}}-running" "info" "running ({{address}})"
  # else line "{{solution}}-running" "info" "not running"; fi
  :
}

# ============================================================================
# 2. Action functions -- one set per solution. Fill in the same command a
#    human would type by hand; this is transcription of the commands that
#    used to live in references/lifecycle.md prose, not new logic. Keep the
#    dispatch section below (§3) as-is -- it's generic across projects.
# ============================================================================
#
# --- Docker Compose pattern ---
# do_build() { docker compose build "$1"; }
# do_up()    { docker compose up -d --build "$1"; }
# do_down()  { docker compose stop "$1"; }
# wait_healthy() {
#   for i in $(seq 1 {{N, e.g. 20}}); do
#     {{curl/health-check command for $1}} >/dev/null 2>&1 && return 0
#     sleep 1
#   done
#   return 1
# }
# dump_log_on_failure() { docker compose logs "$1" --tail={{N, e.g. 50}} >&2; }
# remove_plan() {
#   # Read-only: print the plan row(s) for $1 -- image name, re-acquire cost,
#   # any data outside the build artifact. Source from `audit`'s own state,
#   # not from memory of prose.
#   :
# }
# remove_apply() {
#   docker compose rm -f -s "$1"
#   docker image rm -f "$(docker compose config --images "$1" 2>/dev/null)" 2>/dev/null
#   # If $1 has data outside its build artifact and --purge-data was passed
#   # (checked in §3's dispatch), rm -rf that path here too.
# }
#
# --- Native PID-file pattern ---
# do_build() { {{build command}}; }
# do_up()    { {{start command, backgrounded, PID captured to pidfile}}; }
# do_down()  { {{kill "$(cat {{pidfile}})" 2>/dev/null; rm -f {{pidfile}}}}; }
# wait_healthy() {
#   for i in $(seq 1 {{N}}); do
#     {{curl/log-marker check}} >/dev/null 2>&1 && return 0
#     sleep 1
#   done
#   return 1
# }
# dump_log_on_failure() { tail -n {{N, e.g. 50}} {{log path}} >&2; }
# remove_plan() { :; }
# remove_apply() { rm -rf {{build artifact path, e.g. .venv, tools/x/binary}}; }

do_restart() {
  do_down "$1"
  do_up_and_wait "$1"
}

do_up_and_wait() {
  do_up "$1"
  if wait_healthy "$1"; then
    return 0
  else
    echo "--- $1 did not become healthy — last log output: ---" >&2
    dump_log_on_failure "$1"
    return 1
  fi
}

# ============================================================================
# 3. Dispatch -- generic, no per-project fill-in needed beyond the function
#    bodies above.
# ============================================================================
action="${1:-}"
solution="${2:-}"

case "$action" in
  "")
    audit
    ;;
  build)
    do_build "$solution"; rc=$?
    audit
    exit $rc
    ;;
  up)
    do_up_and_wait "$solution"; rc=$?
    audit
    exit $rc
    ;;
  down)
    do_down "$solution"; rc=$?
    audit
    exit $rc
    ;;
  restart)
    do_restart "$solution"; rc=$?
    audit
    exit $rc
    ;;
  remove)
    mode="${3:-}"
    case "$mode" in
      --plan)
        remove_plan "$solution"
        ;;
      --apply)
        purge="${4:-}"
        remove_apply "$solution" "$purge"; rc=$?
        audit
        exit $rc
        ;;
      *)
        echo "usage: $0 remove <solution> --plan|--apply [--purge-data]" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    echo "usage: $0 [build|up|down|remove|restart] <solution>" >&2
    exit 2
    ;;
esac

exit 0

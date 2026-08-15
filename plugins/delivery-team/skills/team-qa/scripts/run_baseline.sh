#!/usr/bin/env bash
# Runs a test command and extracts a structured pass/fail/skip count from its
# output, so qa-coverage-cartographer stops hand-transcribing suite output
# every run (workflow-audit 2026-08-14: this step executed identically every
# time per the run-log — a mechanical run-and-parse operation, not judgment).
#
# The agent still decides WHICH command to run (targeted vs. full, which
# suite is relevant) — that's real judgment and stays agent-side. This script
# only removes the transcription step.
#
# Usage: run_baseline.sh "<test command>"
# Prints the raw output, then a final line: BASELINE_RESULT: passed=<n> failed=<n> skipped=<n> xfailed=<n> raw_status=<exit code>
# Any count this script can't confidently extract from the given framework's
# output stays "unknown" rather than a guessed 0 — the agent should say so,
# not present "unknown" as a clean pass.

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 \"<test command>\"" >&2
  exit 2
fi

cmd="$1"
out="$(eval "$cmd" 2>&1)"
status=$?
printf '%s\n' "$out"

extract() {
  # $1 = regex, $2 = output var name via echo
  printf '%s\n' "$out" | grep -oE "$1" | tail -1
}

passed="unknown"; failed="unknown"; skipped="unknown"; xfailed="unknown"

# pytest: "12 passed, 3 failed, 1 skipped, 1 xfailed in 4.2s"
if printf '%s\n' "$out" | grep -qE '[0-9]+ passed'; then
  passed="$(printf '%s\n' "$out" | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '[0-9]+')"
  failed="$(printf '%s\n' "$out" | grep -oE '[0-9]+ failed' | tail -1 | grep -oE '[0-9]+')"; failed="${failed:-0}"
  skipped="$(printf '%s\n' "$out" | grep -oE '[0-9]+ skipped' | tail -1 | grep -oE '[0-9]+')"; skipped="${skipped:-0}"
  xfailed="$(printf '%s\n' "$out" | grep -oE '[0-9]+ xfailed' | tail -1 | grep -oE '[0-9]+')"; xfailed="${xfailed:-0}"

# jest/vitest: "Tests: 3 failed, 45 passed, 48 total" or "Tests  45 passed (48)"
elif printf '%s\n' "$out" | grep -qE 'Tests:? +[0-9]+ passed|Tests +[0-9]+ passed'; then
  passed="$(printf '%s\n' "$out" | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '[0-9]+')"
  failed="$(printf '%s\n' "$out" | grep -oE '[0-9]+ failed' | tail -1 | grep -oE '[0-9]+')"; failed="${failed:-0}"
  skipped="$(printf '%s\n' "$out" | grep -oE '[0-9]+ skipped' | tail -1 | grep -oE '[0-9]+')"; skipped="${skipped:-0}"

# go test: "ok  	pkg	0.5s" (pass) / "--- FAIL:" lines / "FAIL"
elif printf '%s\n' "$out" | grep -qE '^(ok|FAIL|---)'; then
  passed="$(printf '%s\n' "$out" | grep -cE '^--- PASS:')"
  failed="$(printf '%s\n' "$out" | grep -cE '^--- FAIL:')"
  skipped="$(printf '%s\n' "$out" | grep -cE '^--- SKIP:')"

# dotnet/xUnit: "Passed!  - Failed: 0, Passed: 45, Skipped: 1, Total: 46"
elif printf '%s\n' "$out" | grep -qE 'Passed: *[0-9]+'; then
  passed="$(printf '%s\n' "$out" | grep -oE 'Passed: *[0-9]+' | tail -1 | grep -oE '[0-9]+')"
  failed="$(printf '%s\n' "$out" | grep -oE 'Failed: *[0-9]+' | tail -1 | grep -oE '[0-9]+')"; failed="${failed:-0}"
  skipped="$(printf '%s\n' "$out" | grep -oE 'Skipped: *[0-9]+' | tail -1 | grep -oE '[0-9]+')"; skipped="${skipped:-0}"

# cargo test: "test result: ok. 12 passed; 0 failed; 1 ignored;"
elif printf '%s\n' "$out" | grep -qE 'test result:'; then
  passed="$(printf '%s\n' "$out" | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '[0-9]+')"
  failed="$(printf '%s\n' "$out" | grep -oE '[0-9]+ failed' | tail -1 | grep -oE '[0-9]+')"; failed="${failed:-0}"
  skipped="$(printf '%s\n' "$out" | grep -oE '[0-9]+ ignored' | tail -1 | grep -oE '[0-9]+')"; skipped="${skipped:-0}"
fi

echo "BASELINE_RESULT: passed=${passed} failed=${failed} skipped=${skipped} xfailed=${xfailed} raw_status=${status}"
exit "$status"

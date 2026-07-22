#!/bin/zsh
# Read-only audit of the {{environment name}} build environment.
# Prints one "KEY | STATUS | DETAIL" line per check; exits 0 always.
# Safe to run any time — changes nothing.

setopt null_glob

line() { printf '%-18s | %-8s | %s\n' "$1" "$2" "$3"; }

# Status vocabulary:
#   ok      — present and usable
#   info    — informational, no action implied
#   MISSING — required and absent (blocks the environment)
#   WRONG   — present but misconfigured
#   NEEDED  — a one-time action is pending (license, init, login)
#   LOW     — a resource is under its threshold (disk, memory)
#   absent  — optional tool not installed (no action required)

# --- OS / hardware context ---
line "os" "info" "$(sw_vers -productVersion 2>/dev/null || uname -sr) ($(uname -m))"

avail_gb=$(df -g / | awk 'NR==2 {print $4}')
if [ "$avail_gb" -ge {{MIN_DISK_GB}} ]; then disk_status="ok"; else disk_status="LOW"; fi
line "disk-free" "$disk_status" "${avail_gb} GB free (install needs ~{{MIN_DISK_GB}} GB free)"

# --- One block per prerequisite; pattern: ---
# if command -v {{tool}} >/dev/null 2>&1; then
#   line "{{audit-key}}" "ok" "$({{tool}} --version 2>/dev/null | head -1)"
# else
#   line "{{audit-key}}" "MISSING" "{{what it is / how it gets installed}}"
# fi

# --- Optional tools use "absent", not "MISSING": ---
# if command -v {{optional-tool}} >/dev/null 2>&1; then
#   line "{{key}}" "ok" "$({{optional-tool}} --version 2>/dev/null)"
# else
#   line "{{key}}" "absent" "not installed (optional — {{when it's wanted}})"
# fi

exit 0

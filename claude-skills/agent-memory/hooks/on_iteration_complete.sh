#!/usr/bin/env bash
# on_iteration_complete.sh - Shell wrapper for daemon/supervisor integration
#
# Called after a worker completes an iteration. Parses arguments and
# forwards them to save_worker_context.py.
#
# Usage:
#   on_iteration_complete.sh --od 75025 --task "fix-feed" --outcome success --summary "Done"
#
# Can also read from a status file:
#   on_iteration_complete.sh --from-file /tmp/worker_75025_status.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAVE_SCRIPT="${SCRIPT_DIR}/save_worker_context.py"

# If --from-file is provided, parse the JSON status file
if [[ "${1:-}" == "--from-file" ]]; then
    STATUS_FILE="${2:?ERROR: --from-file requires a path}"
    if [[ ! -f "$STATUS_FILE" ]]; then
        echo "ERROR: Status file not found: $STATUS_FILE" >&2
        exit 1
    fi

    # Parse JSON fields using python3 (available everywhere)
    eval "$(python3 -c "
import json, sys, shlex
with open('$STATUS_FILE') as f:
    d = json.load(f)
for k in ['od', 'task', 'outcome', 'summary', 'files_modified', 'diff', 'discoveries', 'failed_approaches', 'next_steps']:
    v = d.get(k, '')
    print(f'__{k}={shlex.quote(str(v))}')
")"

    python3 "$SAVE_SCRIPT" \
        --od "$__od" \
        --task "$__task" \
        --outcome "$__outcome" \
        --summary "$__summary" \
        ${__files_modified:+--files-modified "$__files_modified"} \
        ${__diff:+--diff "$__diff"} \
        ${__discoveries:+--discoveries "$__discoveries"} \
        ${__failed_approaches:+--failed-approaches "$__failed_approaches"} \
        ${__next_steps:+--next-steps "$__next_steps"}
else
    # Pass all args directly to save_worker_context.py
    python3 "$SAVE_SCRIPT" "$@"
fi

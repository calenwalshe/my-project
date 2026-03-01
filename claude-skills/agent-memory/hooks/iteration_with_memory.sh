#!/usr/bin/env bash
# iteration_with_memory.sh - Wraps iteration_daemon.py with agent-memory save
#
# Runs the standard Ralph Loop iteration daemon, then when it exits,
# parses the status file and saves worker context to agent memory.
#
# Usage (drop-in replacement for iteration_daemon.py in supervisor workflow):
#   ~/.claude/skills/agent-memory/hooks/iteration_with_memory.sh \
#     %<worker> %<supervisor> --worker-id <OD> --timeout 600
#
# The daemon args are passed through to iteration_daemon.py unchanged.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEMORY_DIR="$SCRIPT_DIR"
DAEMON_SCRIPT="$HOME/.claude/skills/tmux-orchestrator/iteration_daemon.py"

# Run the standard iteration daemon (foreground, blocks until done)
python3 "$DAEMON_SCRIPT" "$@"
DAEMON_EXIT=$?

# Extract worker-id from args
WORKER_ID=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --worker-id)
            WORKER_ID="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [[ -z "$WORKER_ID" ]]; then
    echo "WARNING: No --worker-id provided, skipping memory save" >&2
    exit $DAEMON_EXIT
fi

# Save context from the status file the daemon wrote
STATUS_FILE="/tmp/ralph-${WORKER_ID}-status.txt"
if [[ -f "$STATUS_FILE" ]]; then
    python3 "$MEMORY_DIR/save_from_status.py" --worker-id "$WORKER_ID" 2>&1 || {
        echo "WARNING: Memory save failed (non-fatal)" >&2
    }
else
    echo "WARNING: No status file at $STATUS_FILE, skipping memory save" >&2
fi

exit $DAEMON_EXIT

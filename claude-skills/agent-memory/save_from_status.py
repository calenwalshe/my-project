#!/usr/bin/env python3
"""Bridge: Parse a Ralph Loop status file and save to agent memory.

Reads /tmp/ralph-<worker_id>-status.txt (written by iteration_daemon.py)
and calls save_worker_context.py with the parsed fields.

Usage:
    python3 save_from_status.py --worker-id 94261
    python3 save_from_status.py --worker-id 94261 --status-file /tmp/ralph-94261-status.txt
    python3 save_from_status.py --worker-id 94261 --extra-discoveries "Found new pattern"
"""

import argparse
import os
import re
import subprocess
import sys


def parse_status_file(path):
    """Parse a Ralph Loop status file into a dict."""
    if not os.path.exists(path):
        print(f"ERROR: Status file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r") as f:
        content = f.read()

    fields = {}
    patterns = {
        "state": r"STATE:\s*(\S+)",
        "context": r"CONTEXT:\s*(\d+)%",
        "action": r"ACTION:\s*(.+)",
        "timestamp": r"TIMESTAMP:\s*(\S+)",
        "outcome": r"OUTCOME:\s*(\w+)",
        "task": r"TASK:\s*(.+)",
        "diff": r"DIFF:\s*(\S+)",
        "notes": r"NOTES:\s*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            fields[key] = match.group(1).strip()

    return fields


def main():
    parser = argparse.ArgumentParser(description="Save agent memory from Ralph Loop status file")
    parser.add_argument("--worker-id", required=True, help="Worker/OD identifier")
    parser.add_argument("--status-file", help="Path to status file (default: /tmp/ralph-<worker-id>-status.txt)")
    parser.add_argument("--extra-discoveries", help="Additional discoveries to append")
    parser.add_argument("--extra-failures", help="Additional failed approaches to append")
    parser.add_argument("--files-modified", help="Comma-separated list of files changed")
    args = parser.parse_args()

    status_file = args.status_file or f"/tmp/ralph-{args.worker_id}-status.txt"
    fields = parse_status_file(status_file)

    # Map status file fields to save_worker_context args
    outcome = fields.get("outcome", "partway")
    if outcome not in ("success", "partway", "blocked"):
        outcome = "partway"

    task = fields.get("task", "unknown-task")
    # Clean task name for use as slug (remove leading number + dash)
    task_slug = re.sub(r"^\d+\s*-\s*", "", task).strip()
    task_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", task_slug)[:50]

    summary = fields.get("notes", f"Iteration on {task}")
    diff = fields.get("diff", "")
    if diff == "none":
        diff = ""

    # Build save_worker_context command
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_script = os.path.join(script_dir, "save_worker_context.py")

    cmd = [
        sys.executable, save_script,
        "--od", args.worker_id,
        "--task", task_slug or "iteration",
        "--outcome", outcome,
        "--summary", summary,
    ]

    if diff:
        cmd.extend(["--diff", diff])

    if args.files_modified:
        cmd.extend(["--files-modified", args.files_modified])

    discoveries = args.extra_discoveries or ""
    if discoveries:
        cmd.extend(["--discoveries", discoveries])

    failures = args.extra_failures or ""
    if failures:
        cmd.extend(["--failed-approaches", failures])

    # Derive next steps from state
    state = fields.get("state", "IDLE")
    if outcome == "blocked":
        next_steps = f"Unblock: {summary}"
    elif outcome == "partway":
        next_steps = f"Continue: {task}"
    elif outcome == "success":
        next_steps = "Pick next task from spec"
    else:
        next_steps = "Check status"
    cmd.extend(["--next-steps", next_steps])

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

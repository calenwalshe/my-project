#!/usr/bin/env python3
"""Save worker context after task completion.

Updates memory.md, appends to events.jsonl, writes completion report,
and updates the global registry.

Usage:
    python3 save_worker_context.py \
      --od 75025 --task "fix-feed-tests" --outcome success \
      --summary "Fixed flaky FeedViewModel tests" \
      --files-modified "FeedViewModel.kt,FeedAdapter.kt" \
      --diff "D12345678" \
      --discoveries "Network mock requires explicit timeout" \
      --failed-approaches "PowerMock conflicts with Robolectric" \
      --next-steps "Run full test suite"
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def resolve_gdrive():
    """Resolve ~/gdrive/ to the correct path based on environment."""
    env_path = os.environ.get("GDRIVE_PATH")
    if env_path:
        return env_path

    mac_path = os.path.expanduser(
        "~/Library/CloudStorage/GoogleDrive-calenwalshe@meta.com/My Drive/claude"
    )
    if os.path.isdir(mac_path):
        return mac_path

    od_path = os.path.expanduser("~/gdrive")
    if os.path.isdir(od_path):
        return od_path

    print("ERROR: Cannot find gdrive. Set GDRIVE_PATH env var.", file=sys.stderr)
    sys.exit(1)


def atomic_write(path, content):
    """Write content to path atomically using temp file + rename."""
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.rename(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def write_memory(gdrive, args, now):
    """Write/overwrite the worker memory file (current state snapshot)."""
    worker_dir = os.path.join(gdrive, "orchestrator", "workers", args.od)
    os.makedirs(worker_dir, exist_ok=True)
    memory_path = os.path.join(worker_dir, "memory.md")

    files_list = ""
    if args.files_modified:
        files_list = "\n".join(f"- {f.strip()}" for f in args.files_modified.split(","))
    else:
        files_list = "- (none recorded)"

    content = f"""# Worker Memory: {args.od}

## Current State
- **Status:** {args.outcome}
- **Current Task:** {args.task}
- **Last Updated:** {now}

## Active Context
{args.summary}

## Key Discoveries
{args.discoveries or '(none)'}

## Failed Approaches (DO NOT RETRY)
{args.failed_approaches or '(none)'}

## Files Recently Modified
{files_list}

## Next Steps
{args.next_steps or '(none specified)'}

## Environment
- **OD:** {args.od}
- **Diff/PR:** {args.diff or '(none)'}
"""
    atomic_write(memory_path, content)
    return memory_path


def append_event(gdrive, args, now):
    """Append a single JSON line to the events log."""
    worker_dir = os.path.join(gdrive, "orchestrator", "workers", args.od)
    os.makedirs(worker_dir, exist_ok=True)
    events_path = os.path.join(worker_dir, "events.jsonl")

    event = {
        "type": "task_complete",
        "timestamp": now,
        "od": args.od,
        "task": args.task,
        "outcome": args.outcome,
        "summary": args.summary,
        "files_modified": [f.strip() for f in args.files_modified.split(",")] if args.files_modified else [],
        "diff": args.diff or "",
        "discoveries": args.discoveries or "",
        "failed_approaches": args.failed_approaches or "",
        "next_steps": args.next_steps or "",
    }

    with open(events_path, "a") as f:
        f.write(json.dumps(event) + "\n")

    return events_path


def write_completion(gdrive, args, now):
    """Write a structured completion report JSON."""
    date_str = now[:10]  # YYYY-MM-DD
    comp_dir = os.path.join(gdrive, "orchestrator", "completions", date_str)
    os.makedirs(comp_dir, exist_ok=True)

    # Find next sequence number for this worker+task
    prefix = f"w{args.od}-{args.task}-"
    existing = [f for f in os.listdir(comp_dir) if f.startswith(prefix)] if os.path.isdir(comp_dir) else []
    seq = len(existing) + 1

    filename = f"{prefix}{seq:03d}.json"
    comp_path = os.path.join(comp_dir, filename)

    report = {
        "od": args.od,
        "task": args.task,
        "outcome": args.outcome,
        "summary": args.summary,
        "timestamp": now,
        "files_modified": [f.strip() for f in args.files_modified.split(",")] if args.files_modified else [],
        "diff": args.diff or "",
        "discoveries": args.discoveries or "",
        "failed_approaches": args.failed_approaches or "",
        "next_steps": args.next_steps or "",
        "sequence": seq,
    }

    atomic_write(comp_path, json.dumps(report, indent=2) + "\n")
    return comp_path


def call_update_registry(args):
    """Call update_registry.py as a subprocess."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    registry_script = os.path.join(script_dir, "update_registry.py")

    cmd = [
        sys.executable, registry_script,
        "--od", args.od,
        "--status", "idle" if args.outcome == "success" else "active",
        "--current-task", args.task,
        "--last-outcome", args.outcome,
        "--summary", args.summary,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARNING: Registry update failed: {result.stderr}", file=sys.stderr)
    else:
        print(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description="Save worker context after task completion")
    parser.add_argument("--od", required=True, help="OD/worker identifier")
    parser.add_argument("--task", required=True, help="Task name/slug")
    parser.add_argument("--outcome", required=True, choices=["success", "partway", "blocked"],
                        help="Task outcome")
    parser.add_argument("--summary", required=True, help="One-line summary")
    parser.add_argument("--files-modified", help="Comma-separated list of files changed")
    parser.add_argument("--diff", help="Diff/PR identifier")
    parser.add_argument("--discoveries", help="Things learned during the task")
    parser.add_argument("--failed-approaches", help="Approaches that did not work")
    parser.add_argument("--next-steps", help="What should happen next")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).isoformat()
    gdrive = resolve_gdrive()

    # 1. Write memory (full rewrite)
    mem_path = write_memory(gdrive, args, now)
    print(f"Memory: {mem_path}")

    # 2. Append event
    evt_path = append_event(gdrive, args, now)
    print(f"Event appended: {evt_path}")

    # 3. Write completion report
    comp_path = write_completion(gdrive, args, now)
    print(f"Completion: {comp_path}")

    # 4. Update registry
    call_update_registry(args)

    print(f"\nContext saved for worker {args.od}, task '{args.task}' ({args.outcome})")


if __name__ == "__main__":
    main()

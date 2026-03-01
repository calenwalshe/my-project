#!/usr/bin/env python3
"""Generate a recovery prompt from saved worker state.

Reads memory.md, last 10 events, and latest completion report to produce
a formatted markdown prompt suitable for sending to a replacement worker.

Usage:
    python3 load_worker_context.py --od 75025
    python3 load_worker_context.py --od 75025 --task "fix-feed-tests"
"""

import argparse
import json
import os
import sys
from datetime import datetime


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


def read_memory(worker_dir):
    """Read the worker memory file."""
    memory_path = os.path.join(worker_dir, "memory.md")
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            return f.read().strip()
    return "(No memory file found)"


def read_recent_events(worker_dir, count=10):
    """Read the last N events from the events log."""
    events_path = os.path.join(worker_dir, "events.jsonl")
    if not os.path.exists(events_path):
        return "(No events log found)"

    lines = []
    with open(events_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)

    recent = lines[-count:]
    if not recent:
        return "(No events recorded)"

    formatted = []
    for line in recent:
        try:
            evt = json.loads(line)
            ts = evt.get("timestamp", "?")[:19]  # Trim to seconds
            task = evt.get("task", "?")
            outcome = evt.get("outcome", "?")
            summary = evt.get("summary", "")
            formatted.append(f"- [{ts}] {task}: {outcome} - {summary}")
        except json.JSONDecodeError:
            formatted.append(f"- (parse error: {line[:80]})")

    return "\n".join(formatted)


def read_latest_completion(gdrive, od, task=None):
    """Read the most recent completion report for this worker."""
    comp_base = os.path.join(gdrive, "orchestrator", "completions")
    if not os.path.isdir(comp_base):
        return "(No completions directory)"

    # Find most recent date directory
    dates = sorted([d for d in os.listdir(comp_base) if os.path.isdir(os.path.join(comp_base, d))],
                   reverse=True)

    for date_dir in dates:
        date_path = os.path.join(comp_base, date_dir)
        prefix = f"w{od}-"
        if task:
            prefix = f"w{od}-{task}-"

        matches = sorted([f for f in os.listdir(date_path) if f.startswith(prefix) and f.endswith(".json")],
                         reverse=True)
        if matches:
            comp_path = os.path.join(date_path, matches[0])
            with open(comp_path, "r") as f:
                report = json.load(f)

            lines = [
                f"**Task:** {report.get('task', '?')}",
                f"**Outcome:** {report.get('outcome', '?')}",
                f"**Summary:** {report.get('summary', '')}",
                f"**Time:** {report.get('timestamp', '?')[:19]}",
            ]
            if report.get("discoveries"):
                lines.append(f"**Discoveries:** {report['discoveries']}")
            if report.get("failed_approaches"):
                lines.append(f"**Failed Approaches:** {report['failed_approaches']}")
            if report.get("next_steps"):
                lines.append(f"**Next Steps:** {report['next_steps']}")
            if report.get("files_modified"):
                lines.append(f"**Files:** {', '.join(report['files_modified'])}")

            return "\n".join(lines)

    return "(No completion reports found)"


def format_recovery_prompt(od, memory_content, recent_events, latest_completion, next_steps=""):
    """Format the recovery prompt."""
    prompt = f"""# Recovery Prompt for Worker {od}

You are resuming work on OD {od}. Here is your saved context from the previous session.

## Last Known State
{memory_content}

## Recent Activity (last 10 events)
{recent_events}

## Latest Completion Report
{latest_completion}

---

**IMPORTANT:** Review the "Failed Approaches" section above before choosing your approach. Do NOT retry approaches that have already failed unless you have a specific reason to believe the root cause has changed.
"""

    if next_steps:
        prompt += f"\n**Resume from:** {next_steps}\n"

    return prompt


def main():
    parser = argparse.ArgumentParser(description="Generate recovery prompt from saved worker state")
    parser.add_argument("--od", required=True, help="OD/worker identifier")
    parser.add_argument("--task", help="Filter to specific task")
    args = parser.parse_args()

    gdrive = resolve_gdrive()
    worker_dir = os.path.join(gdrive, "orchestrator", "workers", args.od)

    if not os.path.isdir(worker_dir):
        print(f"WARNING: No saved state found for worker {args.od}", file=sys.stderr)
        print(f"# Recovery Prompt for Worker {args.od}\n\nNo previous context found. Starting fresh.")
        sys.exit(0)

    memory = read_memory(worker_dir)
    events = read_recent_events(worker_dir)
    completion = read_latest_completion(gdrive, args.od, args.task)

    # Extract next_steps from memory if present
    next_steps = ""
    for line in memory.split("\n"):
        if line.strip() and not line.startswith("#") and not line.startswith("-"):
            # Simple heuristic: look in the "Next Steps" section
            pass
    # Better: parse from latest completion
    comp_base = os.path.join(gdrive, "orchestrator", "completions")
    if os.path.isdir(comp_base):
        dates = sorted([d for d in os.listdir(comp_base) if os.path.isdir(os.path.join(comp_base, d))],
                       reverse=True)
        for date_dir in dates:
            date_path = os.path.join(comp_base, date_dir)
            prefix = f"w{args.od}-"
            matches = sorted([f for f in os.listdir(date_path) if f.startswith(prefix) and f.endswith(".json")],
                             reverse=True)
            if matches:
                with open(os.path.join(date_path, matches[0]), "r") as f:
                    report = json.load(f)
                next_steps = report.get("next_steps", "")
                break

    prompt = format_recovery_prompt(args.od, memory, events, completion, next_steps)
    print(prompt)


if __name__ == "__main__":
    main()

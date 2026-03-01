#!/usr/bin/env python3
"""Query completion history with filters.

Usage:
    python3 query_completions.py                          # All completions
    python3 query_completions.py --od 75025               # Filter by worker
    python3 query_completions.py --date 2026-02-08        # Filter by date
    python3 query_completions.py --task "fix-feed"        # Filter by task (substring)
    python3 query_completions.py --json                   # JSON output
    python3 query_completions.py --last 5                 # Last N completions
"""

import argparse
import json
import os
import sys


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


def load_all_completions(gdrive):
    """Load all completion reports from the completions directory."""
    comp_base = os.path.join(gdrive, "orchestrator", "completions")
    if not os.path.isdir(comp_base):
        return []

    completions = []
    for date_dir in sorted(os.listdir(comp_base)):
        date_path = os.path.join(comp_base, date_dir)
        if not os.path.isdir(date_path):
            continue
        for filename in sorted(os.listdir(date_path)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(date_path, filename)
            try:
                with open(filepath, "r") as f:
                    report = json.load(f)
                report["_file"] = filename
                report["_date_dir"] = date_dir
                completions.append(report)
            except (json.JSONDecodeError, IOError) as e:
                print(f"WARNING: Could not read {filepath}: {e}", file=sys.stderr)

    return completions


def filter_completions(completions, od=None, date=None, task=None):
    """Apply filters to completion list."""
    filtered = completions

    if od:
        filtered = [c for c in filtered if c.get("od") == od]

    if date:
        filtered = [c for c in filtered if c.get("timestamp", "").startswith(date)]

    if task:
        filtered = [c for c in filtered if task.lower() in c.get("task", "").lower()]

    return filtered


def print_table(completions):
    """Print completions as a formatted table."""
    if not completions:
        print("No completions found.")
        return

    # Header
    print(f"{'Timestamp':<20} {'OD':<8} {'Task':<25} {'Outcome':<10} {'Summary'}")
    print("-" * 100)

    for c in completions:
        ts = c.get("timestamp", "?")[:19]
        od = c.get("od", "?")
        task = c.get("task", "?")[:24]
        outcome = c.get("outcome", "?")
        summary = c.get("summary", "")[:40]
        print(f"{ts:<20} {od:<8} {task:<25} {outcome:<10} {summary}")

    print(f"\nTotal: {len(completions)} completion(s)")


def main():
    parser = argparse.ArgumentParser(description="Query completion history")
    parser.add_argument("--od", help="Filter by OD/worker identifier")
    parser.add_argument("--date", help="Filter by date (YYYY-MM-DD)")
    parser.add_argument("--task", help="Filter by task name (substring match)")
    parser.add_argument("--last", type=int, help="Show only the last N completions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    gdrive = resolve_gdrive()
    completions = load_all_completions(gdrive)
    completions = filter_completions(completions, od=args.od, date=args.date, task=args.task)

    # Sort by timestamp
    completions.sort(key=lambda c: c.get("timestamp", ""))

    if args.last:
        completions = completions[-args.last:]

    if args.json:
        # Remove internal fields
        clean = [{k: v for k, v in c.items() if not k.startswith("_")} for c in completions]
        print(json.dumps(clean, indent=2))
    else:
        print_table(completions)


if __name__ == "__main__":
    main()

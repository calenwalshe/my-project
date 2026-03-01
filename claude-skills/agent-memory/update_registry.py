#!/usr/bin/env python3
"""Atomic update of the global worker registry (registry.json).

Usage:
    python3 update_registry.py --od 75025 --status active --current-task "fix-feed" --last-outcome success
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone


def resolve_gdrive():
    """Resolve ~/gdrive/ to the correct path based on environment."""
    env_path = os.environ.get("GDRIVE_PATH")
    if env_path:
        return env_path

    # Mac (Google Drive desktop app)
    mac_path = os.path.expanduser(
        "~/Library/CloudStorage/GoogleDrive-calenwalshe@meta.com/My Drive/claude"
    )
    if os.path.isdir(mac_path):
        return mac_path

    # OD/devserver (mclone mount)
    od_path = os.path.expanduser("~/gdrive")
    if os.path.isdir(od_path):
        return od_path

    print(f"ERROR: Cannot find gdrive. Set GDRIVE_PATH env var.", file=sys.stderr)
    sys.exit(1)


def update_registry(od, status=None, current_task=None, last_outcome=None, summary=None):
    """Atomic read-modify-write of registry.json."""
    gdrive = resolve_gdrive()
    registry_path = os.path.join(gdrive, "orchestrator", "registry.json")

    # Read current registry
    if os.path.exists(registry_path):
        with open(registry_path, "r") as f:
            registry = json.load(f)
    else:
        registry = {"workers": {}, "last_updated": ""}

    # Ensure workers dict exists
    if "workers" not in registry:
        registry["workers"] = {}

    now = datetime.now(timezone.utc).isoformat()

    # Update or create worker entry
    if od not in registry["workers"]:
        registry["workers"][od] = {
            "first_seen": now,
            "status": "unknown",
        }

    worker = registry["workers"][od]
    worker["last_updated"] = now

    if status is not None:
        worker["status"] = status
    if current_task is not None:
        worker["current_task"] = current_task
    if last_outcome is not None:
        worker["last_outcome"] = last_outcome
    if summary is not None:
        worker["last_summary"] = summary

    registry["last_updated"] = now

    # Atomic write: temp file + rename
    dir_path = os.path.dirname(registry_path)
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(registry, f, indent=2)
            f.write("\n")
        os.rename(tmp_path, registry_path)
    except Exception:
        # Clean up temp file on error
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return registry


def main():
    parser = argparse.ArgumentParser(description="Update worker registry")
    parser.add_argument("--od", required=True, help="OD/worker identifier")
    parser.add_argument("--status", help="Worker status (active, idle, crashed, terminated)")
    parser.add_argument("--current-task", help="Current task name")
    parser.add_argument("--last-outcome", help="Last task outcome (success, partway, blocked)")
    parser.add_argument("--summary", help="Last task summary")
    args = parser.parse_args()

    registry = update_registry(
        od=args.od,
        status=args.status,
        current_task=args.current_task,
        last_outcome=args.last_outcome,
        summary=args.summary,
    )
    print(f"Registry updated: {len(registry['workers'])} workers tracked")


if __name__ == "__main__":
    main()

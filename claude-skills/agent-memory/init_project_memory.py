#!/usr/bin/env python3
"""Initialize .memory/ directory in a project with template files.

Usage:
    python3 init_project_memory.py --path ~/gdrive/feed-perf/ --name "Feed Performance"
"""

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "project-memory")

TEMPLATE_FILES = ["activeContext.md", "progress.md", "systemPatterns.md", "failures.md"]


def init_project_memory(project_path, project_name):
    """Create .memory/ directory with template files."""
    memory_dir = os.path.join(project_path, ".memory")
    os.makedirs(memory_dir, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    created = []
    skipped = []

    for template_file in TEMPLATE_FILES:
        dest_path = os.path.join(memory_dir, template_file)
        template_path = os.path.join(TEMPLATE_DIR, template_file)

        if os.path.exists(dest_path):
            skipped.append(template_file)
            continue

        if os.path.exists(template_path):
            with open(template_path, "r") as f:
                content = f.read()

            # Fill in template variables
            content = content.replace("{{PROJECT_NAME}}", project_name)
            content = content.replace("{{DATE}}", now)

            with open(dest_path, "w") as f:
                f.write(content)
            created.append(template_file)
        else:
            print(f"WARNING: Template not found: {template_path}", file=sys.stderr)

    return created, skipped


def main():
    parser = argparse.ArgumentParser(description="Initialize project memory directory")
    parser.add_argument("--path", required=True, help="Path to the project directory")
    parser.add_argument("--name", required=True, help="Human-readable project name")
    args = parser.parse_args()

    project_path = os.path.expanduser(args.path)
    if not os.path.isdir(project_path):
        print(f"ERROR: Directory does not exist: {project_path}", file=sys.stderr)
        sys.exit(1)

    created, skipped = init_project_memory(project_path, args.name)

    memory_dir = os.path.join(project_path, ".memory")
    print(f"Memory initialized: {memory_dir}")
    if created:
        print(f"  Created: {', '.join(created)}")
    if skipped:
        print(f"  Skipped (already exist): {', '.join(skipped)}")
    if not created and skipped:
        print("  (all files already existed, no changes made)")


if __name__ == "__main__":
    main()

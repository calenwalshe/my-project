# Agent Memory Skill

Persistent context layer for the tmux orchestrator. Workers, supervisors, and the orchestrator share state through files in `~/gdrive/orchestrator/`.

## Storage Layout

```
~/gdrive/orchestrator/
├── registry.json              ← Global worker index (who, where, what, status)
├── workers/<OD>/
│   ├── memory.md              ← Persistent worker state (current focus, ~2K tokens)
│   └── events.jsonl           ← Append-only action log (timestamped)
└── completions/<date>/
    └── w<OD>-<task>-<seq>.json  ← Structured completion reports

<project>/.memory/
├── activeContext.md            ← Current focus and open questions
├── progress.md                ← What's done / what's next
├── systemPatterns.md          ← Architecture notes and patterns discovered
└── failures.md                ← Failed approaches (prevents re-trying broken paths)
```

## Scripts

All scripts live in `~/.claude/skills/agent-memory/` and use Python 3 with no external dependencies.

### save_worker_context.py

Save worker state after task completion. Updates memory, events, completion report, and registry.

```bash
python3 ~/.claude/skills/agent-memory/save_worker_context.py \
  --od 75025 \
  --task "fix-feed-tests" \
  --outcome success \
  --summary "Fixed flaky FeedViewModel tests by mocking network layer" \
  --files-modified "FeedViewModel.kt,FeedAdapter.kt" \
  --diff "D12345678" \
  --discoveries "Network mock requires explicit timeout config" \
  --failed-approaches "Tried PowerMock but it conflicts with Robolectric" \
  --next-steps "Run full test suite, update CI config"
```

**Arguments:**
- `--od` (required): OD/worker identifier
- `--task` (required): Task name/slug
- `--outcome` (required): `success`, `partway`, or `blocked`
- `--summary` (required): One-line summary of what happened
- `--files-modified`: Comma-separated list of files changed
- `--diff`: Diff/PR identifier
- `--discoveries`: Things learned during the task
- `--failed-approaches`: Approaches that didn't work (critical for preventing loops)
- `--next-steps`: What should happen next

### load_worker_context.py

Generate a recovery prompt from saved state. Outputs formatted markdown to stdout.

```bash
# Full recovery prompt for a worker
python3 ~/.claude/skills/agent-memory/load_worker_context.py --od 75025

# Recovery for a specific task
python3 ~/.claude/skills/agent-memory/load_worker_context.py --od 75025 --task "fix-feed-tests"
```

**Usage with tmux orchestrator:**
```bash
RECOVERY=$(python3 ~/.claude/skills/agent-memory/load_worker_context.py --od 75025)
python3 ~/.claude/skills/tmux-orchestrator/send_prompt.py %5 "$RECOVERY"
```

### init_project_memory.py

Initialize `.memory/` directory in a project with template files.

```bash
python3 ~/.claude/skills/agent-memory/init_project_memory.py \
  --path ~/gdrive/feed-perf/ \
  --name "Feed Performance"
```

Idempotent — skips files that already exist.

### update_registry.py

Atomic update of the global worker registry. Called by save_worker_context.py automatically.

```bash
python3 ~/.claude/skills/agent-memory/update_registry.py \
  --od 75025 \
  --status active \
  --current-task "fix-feed-tests" \
  --last-outcome success
```

### query_completions.py

Query completion history with filters.

```bash
# All completions
python3 ~/.claude/skills/agent-memory/query_completions.py

# Filter by worker
python3 ~/.claude/skills/agent-memory/query_completions.py --od 75025

# Filter by date
python3 ~/.claude/skills/agent-memory/query_completions.py --date 2026-02-08

# Filter by task
python3 ~/.claude/skills/agent-memory/query_completions.py --task "fix-feed"

# JSON output
python3 ~/.claude/skills/agent-memory/query_completions.py --json
```

### save_from_status.py

Bridge script: reads a Ralph Loop status file (`/tmp/ralph-<id>-status.txt`) and saves to agent memory. Used by the daemon wrapper automatically.

```bash
python3 ~/.claude/skills/agent-memory/save_from_status.py --worker-id 94261
```

---

## Integration with Tmux Orchestrator

The tmux-orchestrator skill (`~/.claude/skills/tmux-orchestrator/`) is a system-installed skill that can't be modified. Agent memory integrates via wrapper scripts and explicit instructions for each role.

### Supervisor: BASIC Tactic

After a BASIC task completes (worker goes IDLE), save context:

```bash
# 1. Poll until done
python3 ~/.claude/skills/tmux-orchestrator/poll.py %<pane> --wait --timeout 600

# 2. Save context (fill in from your completion report)
python3 ~/.claude/skills/agent-memory/save_worker_context.py \
  --od <OD> --task "<task-slug>" --outcome success \
  --summary "<what was done>" \
  --files-modified "<file1,file2>" \
  --diff "<D number>" \
  --discoveries "<anything learned>" \
  --failed-approaches "<what didn't work>" \
  --next-steps "<what comes next>"

# 3. Report to orchestrator as normal
```

### Supervisor: Ralph Loop Tactic

**Replace `iteration_daemon.py` with the memory-enabled wrapper.** Drop-in replacement — same args, same behavior, plus auto-saves context when each iteration finishes.

```bash
# INSTEAD OF:
python3 ~/.claude/skills/tmux-orchestrator/iteration_daemon.py \
  %<worker> %<supervisor> --worker-id <OD> --timeout 600 &

# USE:
~/.claude/skills/agent-memory/hooks/iteration_with_memory.sh \
  %<worker> %<supervisor> --worker-id <OD> --timeout 600 &
```

The wrapper:
1. Runs the standard `iteration_daemon.py` (unchanged behavior)
2. When daemon exits, reads `/tmp/ralph-<OD>-status.txt`
3. Calls `save_from_status.py` to persist outcome, task, diff, notes to memory

**Manual fallback** (if you need to save context outside the daemon):
```bash
python3 ~/.claude/skills/agent-memory/save_from_status.py --worker-id <OD>
```

### Supervisor: Worker Recovery

When a worker crashes, times out, or gets a new session:

```bash
# 1. Load saved context as a recovery prompt
RECOVERY=$(python3 ~/.claude/skills/agent-memory/load_worker_context.py --od <OD>)

# 2. Send to replacement worker
python3 ~/.claude/skills/tmux-orchestrator/send_prompt.py %<pane> "$RECOVERY"
```

The recovery prompt includes:
- Last known state (task, outcome, status)
- Key discoveries and failed approaches (prevents re-trying broken paths)
- Recent events log (last 10 actions)
- Latest completion report details
- Next steps to resume from

### Supervisor: New Projects

```bash
python3 ~/.claude/skills/agent-memory/init_project_memory.py \
  --path ~/gdrive/new-project/ --name "New Project"
```

### Orchestrator: Startup / Scan

On startup or when asked to scan, read the registry for global state:

```bash
# Quick registry check
python3 -c "
import json, os
path = os.path.expanduser('~/gdrive/orchestrator/registry.json')
# Mac path fallback
if not os.path.exists(path):
    path = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-calenwalshe@meta.com/My Drive/claude/orchestrator/registry.json')
with open(path) as f:
    r = json.load(f)
if not r['workers']:
    print('No workers registered yet.')
else:
    for od, info in r['workers'].items():
        status = info.get('status', '?')
        task = info.get('current_task', 'idle')
        outcome = info.get('last_outcome', '?')
        print(f'  w{od}: {status} | last: {task} ({outcome})')
    print(f'Total: {len(r[\"workers\"])} workers | Updated: {r[\"last_updated\"][:19]}')
"
```

**Cross-reference with live tmux state:** The registry tells you what workers *were* doing. Combine with `poll.py` to check which are actually alive:

```bash
# Registry says worker 94261 exists — is it still running?
python3 ~/.claude/skills/tmux-orchestrator/poll.py %<pane>
# If IDLE/BUSY → alive. If no output → crashed, needs recovery.
```

### Orchestrator: Completion History

Query what's been done across all workers:

```bash
# Today's completions
python3 ~/.claude/skills/agent-memory/query_completions.py --date $(date +%Y-%m-%d)

# Last 10 across all workers
python3 ~/.claude/skills/agent-memory/query_completions.py --last 10

# Specific worker history
python3 ~/.claude/skills/agent-memory/query_completions.py --od 94261
```

### Worker Behavior

Workers should:
1. Read `.memory/` at session start if it exists in the project directory
2. Reference `failures.md` before trying approaches
3. Update `.memory/activeContext.md` when focus changes
4. Output structured END-OF-ITERATION reports that supervisors/daemon can parse

---

## Path Resolution

Scripts auto-resolve `~/gdrive/` to the correct path:
- **OD/devserver:** `~/gdrive/` (mclone mount)
- **Mac (Google Drive):** `~/Library/CloudStorage/GoogleDrive-calenwalshe@meta.com/My Drive/claude/`

The `GDRIVE_PATH` environment variable overrides auto-detection.

---

## Hooks

### on_iteration_complete.sh

Shell wrapper for direct daemon/cron integration:

```bash
~/.claude/skills/agent-memory/hooks/on_iteration_complete.sh \
  --od 75025 --task "fix-feed" --outcome success --summary "Done"

# Or from a JSON status file:
~/.claude/skills/agent-memory/hooks/on_iteration_complete.sh \
  --from-file /tmp/worker_75025_status.json
```

### iteration_with_memory.sh

Drop-in replacement for `iteration_daemon.py` that adds memory persistence:

```bash
~/.claude/skills/agent-memory/hooks/iteration_with_memory.sh \
  %<worker> %<supervisor> --worker-id <OD> --timeout 600 &
```

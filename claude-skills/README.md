# Claude Code Skills

Personal Claude Code skills and utilities. Drop these into `~/.claude/skills/` to use.

## Skills

| Skill | Description |
|-------|-------------|
| `github-cli/` | GitHub CLI (gh) reference, helper scripts for repo creation, quick PRs, releases |
| `agent-memory/` | Persistent context layer for multi-agent orchestration — saves/loads worker state, tracks completions, recovery prompts |
| `agent-showcase/` | Deploy and share static web projects to a showcase dashboard |
| `deploy-app/` | Quick deployment workflow for web apps to the showcase platform |
| `mckinsey/` | Transform documents into layered McKinsey-style strategic reports with auto-detected frameworks |
| `session-backup/` | Backup/restore Claude Code sessions across machines via Google Drive |
| `gdrive-sync-mac/` | Set up bidirectional Google Drive sync on macOS using rclone bisync + launchd |

## Utilities

| File | Description |
|------|-------------|
| `skill-sync.sh` | Sync skills between machines via Google Drive (push/pull/status) |

## Installation

```bash
# Copy all skills
cp -r claude-skills/* ~/.claude/skills/

# Or just one
cp -r claude-skills/mckinsey ~/.claude/skills/
```

## Requirements

- Claude Code CLI
- `gh` CLI (for github-cli skill)
- `rclone` (for gdrive-sync-mac)
- Python 3 (for agent-memory scripts)

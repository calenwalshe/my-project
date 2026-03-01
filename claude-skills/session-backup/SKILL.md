# Claude Session Backup (csb)

Backup and restore Claude Code sessions across OD instances via Google Drive.

## Commands

```bash
csb here      # Find/restore sessions for current directory
csb list      # List all backed up sessions  
csb status    # Check daemon status
csb sync      # Force immediate backup
csb restore <id>  # Restore a specific session
```

## Requirements

- gdrive mounted at ~/gdrive/
- Daemon auto-starts via .bashrc integration

## How it works

1. Daemon monitors ~/.claude/projects/ for new session files
2. Backs up to ~/gdrive/.claude-sessions/
3. On restore, copies back to local projects folder

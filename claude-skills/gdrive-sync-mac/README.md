# Google Drive Sync for macOS (Local Machine)

Sync Google Drive to a local folder on macOS using rclone bisync with automatic background syncing via launchd.

## When to Use

Use this skill when users ask to:
- Set up Google Drive sync on their local Mac
- Troubleshoot Google Drive sync issues
- Mount or sync Google Drive locally
- Set up automatic sync between local folder and Google Drive
- Replicate this setup on another Mac

## Current Setup (calenwalshe-mac)

| Component | Value |
|-----------|-------|
| Local folder | `/Users/calenwalshe/gdrive_mt` |
| Google Drive folder | `gdrive:ai_everywhere` |
| Sync method | `rclone bisync` (bidirectional) |
| Sync interval | Every 5 minutes |
| Config file | `~/.config/rclone/rclone.conf` |
| LaunchAgent | `~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist` |
| Log file | `~/.gdrive-sync.log` |

## Quick Reference Commands

### Check sync status
```bash
# See if sync agent is running
launchctl list | grep gdrive

# View recent sync logs
tail -20 ~/.gdrive-sync.log

# Check what's in local folder
ls -la ~/gdrive_mt

# Check what's in Google Drive
rclone ls gdrive:ai_everywhere
```

### Force manual sync
```bash
rclone bisync gdrive:ai_everywhere ~/gdrive_mt
```

### Restart sync service
```bash
launchctl unload ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
launchctl load ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
```

### Stop automatic sync
```bash
launchctl unload ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
```

## Troubleshooting

### Sync errors - "Must run --resync to recover"
This happens when bisync detects a mismatch. Fix with:
```bash
rclone bisync gdrive:ai_everywhere ~/gdrive_mt --resync
```

### Token expired
Refresh your Google auth:
```bash
rclone config reconnect gdrive:
```

### Check rclone config
```bash
rclone listremotes
rclone config show gdrive
```

### LaunchAgent "Input/output error" (launchctl load fails)

This is a known macOS issue that affects many services. Try these fixes in order:

**1. Reboot your Mac** (often fixes launchd issues)

**2. Delete and recreate the plist:**
```bash
rm ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
# Then recreate it (see Step 5 in Setup section)
launchctl load ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
```

**3. Try bootstrap instead of load:**
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
```

**4. Check for existing service and bootout first:**
```bash
launchctl bootout gui/$(id -u)/com.calenwalshe.gdrive-sync 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
```

**5. If all else fails - use manual sync:**
Since launchd can be unreliable on Meta-managed Macs, you can run manual syncs:
```bash
# Run sync manually when needed
rclone bisync gdrive:ai_everywhere ~/gdrive_mt
```

### LaunchAgent not loading - other checks
```bash
# Check plist syntax
plutil -lint ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist

# Check for errors
launchctl print gui/$(id -u)/com.calenwalshe.gdrive-sync
```

### Sync not working - check logs
```bash
tail -50 ~/.gdrive-sync.log
```

### Verify Google Drive connection
```bash
rclone lsd gdrive:
rclone ls gdrive:ai_everywhere
```

## Setup on a New Mac

### Prerequisites
- Homebrew installed
- rclone installed: `brew install rclone`

### Step 1: Copy rclone config
Copy `~/.config/rclone/rclone.conf` from existing machine, or configure fresh:
```bash
mkdir -p ~/.config/rclone
# Either copy existing config or run:
rclone config
# Choose: n (new) → gdrive → drive → defaults → y (auto config)
```

### Step 2: Create local folder
```bash
mkdir -p ~/gdrive_mt
```

### Step 3: Create ai_everywhere folder (if needed)
```bash
rclone mkdir gdrive:ai_everywhere
```

### Step 4: Initialize bisync
```bash
rclone bisync gdrive:ai_everywhere ~/gdrive_mt --resync
```

### Step 5: Create LaunchAgent
Create `~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.calenwalshe.gdrive-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/rclone</string>
        <string>bisync</string>
        <string>gdrive:ai_everywhere</string>
        <string>/Users/calenwalshe/gdrive_mt</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/calenwalshe/.gdrive-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/calenwalshe/.gdrive-sync.log</string>
</dict>
</plist>
```

**Note**: Update username in paths if different from `calenwalshe`.

### Step 6: Load the agent
```bash
launchctl load ~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist
```

### Step 7: Verify
```bash
launchctl list | grep gdrive
tail -f ~/.gdrive-sync.log
```

## Why Not Mount?

Real-time mounting (`rclone mount` or `rclone nfsmount`) requires either:
- **macFUSE** with kernel extension loaded, or
- **sudo** for NFS mounting

The bisync approach works without elevated privileges and is more reliable on modern macOS with its security restrictions.

## File Locations

| File | Purpose |
|------|---------|
| `~/.config/rclone/rclone.conf` | rclone remote configuration with Google auth token |
| `~/Library/LaunchAgents/com.calenwalshe.gdrive-sync.plist` | Auto-sync scheduler |
| `~/.gdrive-sync.log` | Sync operation logs |
| `~/gdrive_mt/` | Local synced folder |
| `~/.claude/skills/gdrive-sync-mac/` | This skill documentation |

## rclone.conf Template

```ini
[gdrive]
type = drive
scope = drive
token = {"access_token":"...","token_type":"Bearer","refresh_token":"...","expiry":"..."}
team_drive =
```

Token is auto-refreshed by rclone when it expires.

## Alternative Approaches (from Meta Deep Research)

Based on Meta internal documentation and workplace posts, here are alternative approaches:

### 1. Insync (Paid, Officially Approved)
Meta Security has officially approved Insync for Google Drive sync on Mac/Linux.
- **Pros**: Real-time sync, reliable, official approval
- **Cons**: Requires personal license purchase (~$30)
- **Install**: https://www.insynchq.com/
- **Source**: [Desktop Linux Users post](https://fb.workplace.com/groups/desktop.linux.users/permalink/27731793483109237/)

### 2. Google Drive Desktop App
Official Google solution, but has limitations on Meta-managed Macs.
- **Pros**: Official, stable, works in Finder
- **Cons**: Mirroring/local sync disabled by Meta security policy (streaming only)
- **Install**: https://workspace.google.com/products/drive/#download
- **Source**: [Productivity Apps post](https://fb.workplace.com/groups/1567397194032924/permalink/1617070649065578/)

### 3. Hazel (Paid, for file automation)
Mac app for automated file organization and syncing.
- **Pros**: Powerful rules, reliable scheduling
- **Cons**: Paid license, more complex setup
- **Source**: [e Social post](https://fb.workplace.com/groups/esocial/permalink/1446984648673756/)

### 4. Manual Sync Workflow
If automation fails, use manual sync when context matters:
```bash
# Quick alias for your .zshrc or .bashrc
alias gsync='rclone bisync gdrive:ai_everywhere ~/gdrive_mt'
```

## Meta Best Practices (from Satish Kumar's Workflow)

From the popular ["One Context to Rule Them All"](https://fb.workplace.com/groups/claude.code.community/permalink/848361331039322/) post:

1. **Use Google Drive as single source of truth** for AI context across surfaces
2. **Directory structure**:
   ```
   ~/gdrive_mt/
   ├── INSTRUCTIONS_TO_LLM.md     # Global AI instructions
   ├── worklog/
   │   ├── PROJECT_STATUS.md      # Dashboard of all projects
   │   ├── 2025-01-07.md          # Daily worklogs
   │   └── <project_name>/
   │       ├── README.md          # Project docs
   │       └── CHANGELOG.md       # Session tracking
   ```
3. **Claude Code SessionStart hook** can auto-load context from synced folder
4. **Sync lag**: 1-2 second delays are normal; Claude reads on startup so not an issue

## References

- [One Context to Rule Them All - Satish Kumar](https://fb.workplace.com/groups/claude.code.community/permalink/848361331039322/)
- [Google Drive sync client discussion](https://fb.workplace.com/groups/desktop.linux.users/permalink/27731793483109237/)
- [Tips for Developing on Laptops](https://www.internalfb.com/wiki/Client_Platform_Engineering/Developers/Tips_for_Developing_on_Laptops_%26_Desktops/)
- [launchd.info](https://launchd.info/) - Useful for launchd troubleshooting

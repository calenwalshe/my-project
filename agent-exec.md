# agent-exec — SSH Jump-Host Remote Execution Wrapper

## Purpose

A minimal bash wrapper that executes arbitrary shell commands on a remote target server through an SSH jump host (bastion). Designed for infrastructure management where the target server is not directly reachable from the operator's machine but is reachable from an intermediate jump host.

## Usage

```bash
agent-exec "<command>"
agent-exec 'cd ~/project && docker-compose ps'
agent-exec "ls -la /home/user"
```

All positional arguments are concatenated and treated as a single remote command string.

## Architecture

```
Operator Machine                Jump Host              Target Server
(Mac/Linux)        SSH #1       (bastion)   SSH #2     (agent-stack)
┌──────────┐  ──────────────>  ┌──────────┐ ────────> ┌──────────────┐
│ agent-exec│                  │          │           │ executes cmd │
└──────────┘  <──────────────  └──────────┘ <──────── └──────────────┘
               stdout/stderr                           stdout/stderr
```

The script performs a **nested SSH**: it SSHes into the jump host, which in turn SSHes into the target. The command is passed through both hops with proper shell escaping.

## Algorithm

1. Resolve `SCRIPT_DIR` to the directory containing the script (handles symlinks)
2. Derive `PROJECT_DIR` as parent of `SCRIPT_DIR`
3. Set configuration constants:
   - `KEY` = `$PROJECT_DIR/ssh_key` (path to SSH private key)
   - `JUMP_HOST` = `<user>@<jump-host-ip>` (intermediate bastion)
   - `TARGET` = `<user>@<target-ip>` (final destination)
   - `SSH_OPTS` = `-o StrictHostKeyChecking=no -o ConnectTimeout=10`
4. Construct the nested SSH command:
   ```
   ssh $SSH_OPTS -i "$KEY" "$JUMP_HOST" "ssh $SSH_OPTS $TARGET '<escaped_command>'"
   ```
5. Shell-escape single quotes in the command using:
   ```bash
   echo "$@" | sed "s/'/'\\\\''/g"
   ```
   This replaces each `'` with `'\''` to safely pass the command through the outer SSH layer.
6. Execute and stream stdout/stderr back to the caller.

## Configuration

All configuration is derived from file paths relative to the script location:

| Variable | Description | Default Pattern |
|----------|-------------|-----------------|
| `KEY` | Path to SSH private key | `$PROJECT_DIR/ssh_key` |
| `JUMP_HOST` | SSH user@host for bastion | `<user>@<bastion-ip>` |
| `TARGET` | SSH user@host for target | `<user>@<target-ip>` |
| `SSH_OPTS` | SSH connection options | `-o StrictHostKeyChecking=no -o ConnectTimeout=10` |

**No environment variables or config files are used.** All values are hardcoded in the script.

## Data Flow

```
Input: Command string (all positional args)
  ↓
Shell escape: sed replaces ' with '\''
  ↓
Outer SSH: Connect to jump host with key auth
  ↓
Inner SSH: Jump host connects to target (no key needed — agent forwarding or authorized_keys)
  ↓
Execute: Command runs on target
  ↓
Output: stdout/stderr stream back through both hops
```

## Error Handling

- **Connection timeout**: SSH will time out after 10 seconds per hop (`ConnectTimeout=10`)
- **Host key verification**: Disabled (`StrictHostKeyChecking=no`) for operational convenience
- **Key not found**: SSH will fail with "No such file" — the key must exist at the expected path
- **Key permissions**: SSH will refuse keys with overly permissive permissions (must be 600 or 400)
- **Quote escaping**: Single quotes in commands are escaped; double quotes pass through the outer SSH naturally

## Integration Points

- **SSH key**: Must be a valid private key at `$PROJECT_DIR/ssh_key`
- **Jump host**: Must accept key-based SSH from the operator machine
- **Target server**: Must accept SSH from the jump host (can use authorized_keys or agent forwarding)
- **Network**: Operator → Jump Host must be reachable; Jump Host → Target must be reachable

## Limitations

- Commands with complex quoting (nested single + double quotes) may require manual escaping
- No TTY allocation — interactive commands (vim, less) will not work
- No timeout on the remote command itself — only the SSH connection has a timeout
- Binary output may be corrupted by the double-hop SSH (use base64 encoding for binary transfers)
- No multiplexing or connection reuse — each invocation opens two fresh SSH connections

## Implementation Notes

- Total implementation: ~15 lines of bash
- No external dependencies beyond `ssh` and `sed`
- The script is intentionally minimal — no argument parsing, no flags, no help text
- All arguments (`$@`) are treated as a single command string via `echo "$@"`

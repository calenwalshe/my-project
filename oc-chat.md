# oc-chat -- WebSocket Chat Client

## Purpose

An interactive CLI client for communicating with an agent platform through its WebSocket API. Provides the same interface as messaging the agent via Telegram -- full access to tools, skills, command execution, web browsing, and persistent memory. Consists of a bash launcher script and an async Python client.

## Usage

```bash
oc-chat                              # Interactive REPL
oc-chat "your message here"          # One-shot (send and exit)
oc-chat --session test-1 "msg"       # Custom session key
oc-chat --telegram "msg"             # Bridge: also forward to Telegram
oc-chat --debug "msg"                # Print raw WebSocket frames
oc-chat --local                      # Connect via local SSH tunnel instead of remote execution
oc-chat --help                       # Show usage
```

## Architecture

### Two Execution Modes

**Default mode (remote execution):**
```
Mac                        Jump Host              Agent Stack
+----------+  base64 pipe  +----------+  SSH #2  +---------------+
| oc-chat   |-------------->| (bastion) |-------->| Python client |
| (bash)    |               |           |         | <> WebSocket  |
|           |               |           |         | Agent (18789) |
+----------+<--------------+----------+<--------+---------------+
             stdout/stderr
```

1. Bash wrapper base64-encodes the Python client script
2. Pipes it to the agent-stack via double-hop SSH
3. Decodes on the remote side into a temp file
4. Executes the Python client on agent-stack where WebSocket is localhost

**Local tunnel mode (`--local`):**
```
Mac                        Jump Host              Agent Stack
+--------------+  SSH -L   +----------+  tunnel  +--------------+
| Python client |---------->| (bastion) |-------->| Agent (18789)|
| ws://localhost|           |           |         |              |
|    :18789    |           |           |         |              |
+--------------+           +----------+         +--------------+
```

1. Opens SSH tunnel: `localhost:18789 -> agent-stack:18789` via jump host
2. Runs Python client locally, connecting to `ws://localhost:18789/`

### Component 1: Bash Launcher

**Arguments parsed:**
| Flag | Variable | Effect |
|------|----------|--------|
| `--local` | `LOCAL_MODE=true` | Use SSH tunnel instead of remote exec |
| `--session KEY`, `-s KEY` | `SESSION_ARGS` | Pass session key to Python client |
| `--debug`, `-d` | `DEBUG_ARGS` | Enable debug frame logging |
| `--telegram`, `-t` | `TG_ARGS` | Enable Telegram bridging |
| `--help`, `-h` | (exit) | Print usage and exit |
| `<positional>` | `MESSAGE` | One-shot message |

**Remote mode implementation:**
1. Base64-encode the Python client: `base64 -i "$CLIENT_SCRIPT"`
2. Pipe through double-hop SSH to decode on remote: `base64 -d > /tmp/oc-chat-client.py`
3. For one-shot: base64-encode the message too (avoids quoting issues through double SSH hop)
4. For interactive: allocate TTY with `ssh -t` on both hops

**Tunnel mode implementation:**
1. Open background SSH tunnel: `ssh -f -N -L 18789:<target-ip>:18789 <jump-host>`
2. Save tunnel PID, set trap for cleanup on exit
3. Wait 1 second for tunnel establishment
4. Run Python client with `--url ws://localhost:18789/`

### Component 2: Python WebSocket Client

**Dependencies:** `websockets` (async WebSocket library), Python 3.7+ stdlib

**Configuration (environment variables with defaults):**
| Variable | Purpose | Default (placeholder) |
|----------|---------|----------------------|
| `OPENCLAW_TOKEN` | Authentication token | `<auth-token>` |
| `TG_BOT_TOKEN` | Telegram Bot API token | `<bot-token>` |
| `TG_CHAT_ID` | Telegram chat/user ID | `<chat-id>` |

**CLI Arguments (Python):**
| Argument | Default | Purpose |
|----------|---------|---------|
| `message` (positional, optional) | None | One-shot message |
| `--session`, `-s` | `agent:main:main` | Session key |
| `--url` | `ws://localhost:18789/ws` | WebSocket URL |
| `--debug`, `-d` | false | Print raw frames to stderr |
| `--telegram`, `-t` | false | Bridge messages to Telegram |

**Global state:**
- `DEBUG: bool` -- controls debug output
- `TG_BRIDGE: bool` -- controls Telegram forwarding

## Protocol

See `openclaw-ws-protocol.md` for the full WebSocket protocol specification. The client implements:

1. **Connection**: Wait for `connect.challenge` -> send `connect` request with auth -> verify `ok: true`
2. **Chat**: Send `chat.send` request -> collect streaming events -> return on `chat` event with `state: final`
3. **Additional methods**: `health`, `status` (used in REPL mode)

### Connection Parameters

```json
{
  "type": "req",
  "id": "<8-char-uuid>",
  "method": "connect",
  "params": {
    "minProtocol": 3,
    "maxProtocol": 3,
    "client": {
      "id": "cli",
      "displayName": "test-harness",
      "version": "0.1",
      "platform": "linux",
      "mode": "cli"
    },
    "role": "operator",
    "scopes": ["operator.admin"],
    "auth": {"token": "<OPENCLAW_TOKEN>"}
  }
}
```

### WebSocket Configuration

| Parameter | Value |
|-----------|-------|
| Ping interval | 30 seconds |
| Ping timeout | 60 seconds |
| Max frame size | 10 MB |

## Key Functions

### `make_id() -> str`
Returns first 8 characters of a UUID4. Used for request IDs.

### `tg_send(text, prefix=None) -> bool`
Send a message to Telegram via Bot API.
- Prepends optional prefix with double newline
- Truncates to 4096 chars (Telegram limit), appending `[...]`
- Uses `urllib.request` (no external HTTP library)
- On Markdown parse failure (HTTP error), retries without `parse_mode`
- Returns True on success, False on any error

### `connect_and_chat(message, session_key, interactive, ws_url)`
Main entry point. Opens WebSocket, performs handshake, then either:
- Calls `send_and_collect()` for one-shot mode
- Calls `repl_loop()` for interactive mode

### `send_and_collect(ws, session_key, message) -> str`
Sends a message and collects the full response.

**Algorithm:**
1. Generate request ID and idempotency key
2. If Telegram bridge enabled, forward user message with prefix
3. Send `chat.send` request
4. Enter receive loop (300s timeout per frame):
   - `type: "res"` with matching ID -> check `ok`, extract status
   - `type: "event"`, `event: "agent"`:
     - `stream: "assistant"` -> accumulate `data.delta` text, print to stdout
     - `stream: "lifecycle"` -> debug log phase
     - `stream: "tool_call"` -> print tool name to stderr
     - `stream: "tool_result"` -> debug log
     - `stream: "thinking"` -> print indicator to stderr
   - `type: "event"`, `event: "chat"`:
     - `state: "final"` -> if no accumulated text, extract from `message.content[]` array; break
     - `state: "error"` -> extract error text from `message.content[]`; break
5. Print final newline
6. If Telegram bridge enabled, forward agent response with prefix
7. Return accumulated text

### `repl_loop(ws, session_key)`
Interactive REPL with these commands:
| Command | Action |
|---------|--------|
| `/quit` | Exit |
| `/session <key>` | Switch to different session key |
| `/health` | Send `health` method request, print JSON response |
| `/status` | Send `status` method request, print JSON response |
| Any other input | Send via `send_and_collect()` |

Uses `asyncio.get_event_loop().run_in_executor()` to read stdin without blocking the event loop.

## Telegram Bridge

When `--telegram` is enabled:
- User messages are forwarded with prefix: `You (via oc-chat):`
- Agent responses are forwarded with prefix: `Agent:`
- Messages are sent via Telegram Bot API `sendMessage` endpoint
- Parse mode: Markdown (with fallback to plain text on parse error)
- Web page preview: disabled
- Max length: 4096 characters (truncated with `[...]`)

## Output Format

**Interactive mode (stderr):**
```
[challenge received] [connected]
OpenClaw REPL (session: agent:main:main)
Type /quit to exit, /session <key> to switch sessions
---
you>
```

**During response (stdout + stderr):**
```
[queued]                          <- stderr: request status
[tool: exec]                     <- stderr: tool invocations
[thinking]                       <- stderr: reasoning indicator
The agent's response text here   <- stdout: streamed deltas
```

**One-shot mode:** Same as above, but exits after the first response.

## Error Handling

| Error | Handling |
|-------|----------|
| Challenge timeout (10s) | Print error, exit |
| Auth failure | Print `[connect failed]` with response JSON, exit |
| Request rejected | Print `[error]` with error message |
| Frame timeout (300s) | Print `[timeout waiting for response]`, break |
| WebSocket disconnect | Exception propagates, program exits |
| Telegram send failure | Silently ignored (returns False) |
| EOF/Ctrl+C in REPL | Print `[bye]`, exit cleanly |

## Implementation Notes

- Python client: ~335 lines
- Bash launcher: ~125 lines
- No external dependencies beyond `websockets` Python package
- The base64 transfer approach avoids SSH socket sandbox issues that break `scp`
- Message base64 encoding in one-shot mode prevents quote mangling through double SSH hop
- The `health` events from the server are explicitly filtered from debug output (too noisy)

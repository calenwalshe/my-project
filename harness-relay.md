# harness-relay — Interactive Telegram-to-Agent Relay

## Purpose

A simplified, relay-only bridge between Telegram DMs and the agent's WebSocket API. Unlike `harness-bot`, this tool has no scripted mode — it exclusively relays messages from Telegram to the agent and returns responses. Designed for manual testing and live interaction with the agent through Telegram.

## Usage

```bash
python3 harness_relay.py
# Then DM @<bot_username> on Telegram
# Ctrl+C to stop
```

No arguments. No flags.

## Architecture

```
Telegram User                   harness_relay           Agent (WS)
    │                               │                     │
    │  DM message                   │                     │
    ├──────────────────────────────>│                     │
    │                               │  "⏳ thinking..."   │
    │<──────────────────────────────┤                     │
    │                               │  chat.send via WS   │
    │                               ├───────────────────>│
    │                               │                     │
    │                               │  streaming response │
    │                               │<───────────────────┤
    │  Agent response               │                     │
    │<──────────────────────────────┤                     │
    │                               │                     │
    │  (30s long-poll cycle)        │                     │
```

Key difference from `harness-bot`: sends a "⏳ thinking..." indicator to Telegram immediately after receiving the user's message, before forwarding to the agent.

## Configuration

Hardcoded constants:

| Constant | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram Bot API token |
| `CHAT_ID` | Authorized Telegram chat ID |
| `WS_URL` | Agent WebSocket URL (`ws://localhost:18789/`) |
| `OC_TOKEN` | Agent authentication token |
| `SESSION_KEY` | `agent:main:harness-relay-<unix-timestamp>` |

Session key is generated once at module load time (not per-connection).

## Key Functions

### `make_id() → str`
First 8 chars of UUID4.

### `tg_send(text) → bool`
Telegram Bot API sendMessage. Truncates to 4096 chars. Timeout: 15s.

### `tg_get_updates(offset=None) → list`
Long-poll Telegram (30s timeout, 35s HTTP timeout). Returns list of updates.

### `ws_send_and_collect(ws, message) → str`
Send message via WebSocket (uses module-level `SESSION_KEY`), collect response.
- Timeout: 300s per frame
- Accumulates assistant deltas
- Waits for `chat` event with `state: final` or `state: error`
- Falls back to `message.content[]` extraction if no deltas accumulated
- Returns text or `[timeout waiting for response]` or `[error: <msg>]` or `[empty response]`

## Algorithm

```
1. Connect WebSocket (ping=30s, pong=60s, max=10MB)
2. Wait for connect.challenge (10s)
3. Send connect request with auth token
4. Verify ok: true
5. Log "Connected! Listening for Telegram messages..."
6. Send Telegram: "🟢 Harness relay connected. Send me a message..."
7. offset = None
8. Loop forever:
   a. Long-poll Telegram (run_in_executor to not block event loop)
   b. For each update:
      - Extract text and chat_id
      - Skip if wrong chat_id or empty text
      - Handle slash commands:
        /quit → send "🔴 Relay stopped.", return
        /session → send "Session: <key>", continue
        /start → skip
      - Log "User: <text>"
      - Send Telegram: "⏳ thinking..."
      - Forward to agent: ws_send_and_collect(ws, text)
      - Log "Agent: <response>"
      - Send response to Telegram
```

## Telegram Commands

| Command | Response |
|---------|----------|
| `/quit` | Sends "🔴 Relay stopped." and exits |
| `/session` | Sends current session key |
| `/start` | Silently ignored (Telegram bot auto-command) |

## Output Format

### Terminal
```
2026-02-24 12:00:00 Connecting to OpenClaw at ws://localhost:18789/ (session: agent:main:harness-relay-1708784400)
2026-02-24 12:00:01 Connected! Listening for Telegram messages...
2026-02-24 12:00:30 User: What is the weather today?
2026-02-24 12:01:05 Agent: Based on a web search, the current weather...
```

### Telegram
```
🟢 Harness relay connected. Send me a message and I'll forward it to the agent.
⏳ thinking...
[Agent's full response]
```

## Differences from harness-bot

| Feature | harness-relay | harness-bot |
|---------|---------------|-------------|
| Scripted mode | No | Yes (`--scripted`) |
| Thinking indicator | Yes ("⏳ thinking...") | No |
| Session key | Module-level (single session) | Generated in `ws_connect()` |
| Connection style | `async with` (context manager) | Separate connect function |
| Cleanup | Automatic via context manager | `finally` block |
| Slash command handling | In main loop (string matching) | In `run_interactive()` |
| Code structure | Single `main()` function | Modular (ws_connect, run_interactive, run_scripted) |
| Lines of code | ~209 | ~289 |

## Error Handling

| Error | Handling |
|-------|----------|
| Bad challenge | Log error, return |
| Auth failure | Log error, return |
| Response timeout | Returns `[timeout waiting for response]` |
| Telegram poll error | Log error, returns empty list, continues |
| Telegram send error | Log error, continues |
| Wrong chat ID | Silently ignored |

## Dependencies

- `websockets` Python package
- Python 3.7+ (`asyncio`, `json`, `logging`, `time`, `urllib.request`, `urllib.parse`, `urllib.error`, `uuid`)
- ~209 lines of Python

## Integration Points

- **Agent WebSocket API**: Port 18789
- **Telegram Bot API**: Polling + sending

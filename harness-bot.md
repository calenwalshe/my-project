# harness-bot -- Dual-Mode Telegram Relay + Scripted Conversation

## Purpose

A dual-mode agent testing tool that can either (1) act as an interactive relay between Telegram DMs and the agent's WebSocket API, or (2) run a scripted 20-message conversation test. In relay mode, it polls Telegram for incoming messages, forwards them to the agent, and sends responses back. In scripted mode, it runs the same conversation as `harness-chat` but with structured logging.

## Usage

```bash
# Interactive relay mode (poll Telegram -> forward to agent -> reply)
python3 harness_bot.py

# Scripted 20-message conversation
python3 harness_bot.py --scripted
```

## Architecture

### Interactive Relay Mode
```
Telegram User                   harness_bot             Agent
    |                               |                     |
    |  DM to @bot                   |                     |
    |------------------------------>|                     |
    |                               |  chat.send via WS   |
    |                               |-------------------->|
    |                               |                     |
    |                               |  streaming response |
    |                               |<--------------------|
    |  Bot reply                    |                     |
    |<------------------------------|                     |
    |                               |                     |
    |  (30s long-poll cycle)        |                     |
```

### Scripted Mode
```
harness_bot                Agent              Telegram
    |                        |                   |
    |  chat.send [1/20]      |                   |
    |----------------------->|                   |
    |                        |                   |
    |  response              |                   |
    |<-----------------------|                   |
    |                        |   relay output    |
    |----------------------------------------------->|
    |                        |                   |
    |  chat.send [2/20]      |                   |
    |----------------------->|                   |
    ...                                          |
```

## CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--scripted` | flag | false | Run scripted conversation instead of relay |

## Configuration

Hardcoded constants (replace with your own):

| Constant | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram Bot API token |
| `CHAT_ID` | Authorized Telegram chat ID |
| `WS_URL` | Agent WebSocket URL (`ws://localhost:18789/`) |
| `OC_TOKEN` | Agent authentication token |

## Session Key Generation

| Mode | Pattern |
|------|---------|
| Interactive | `agent:main:harness-<unix-timestamp>` |
| Scripted | Same key (generated at connection time) |

## Key Functions

### `make_id() -> str`
Returns first 8 characters of UUID4 for request IDs.

### `tg_send(text) -> bool`
Send message via Telegram Bot API.
- Truncates to 4096 chars
- URL-encoded form POST
- Timeout: 15s
- Returns True/False, logs errors

### `tg_get_updates(offset=None) -> list`
Long-poll Telegram for new messages.
- `GET /getUpdates?timeout=30&offset=<N>`
- HTTP timeout: 35s (longer than poll timeout)
- Returns list of update objects, empty list on error

### `ws_connect() -> (websocket, session_key)`
Establish WebSocket connection and authenticate.
1. Connect with ping=30s, timeout=60s, max_size=10MB
2. Wait for `connect.challenge` event (10s timeout)
3. Send `connect` request with auth token
4. Verify `ok: true` response
5. Return websocket and generated session key
6. Raises `ConnectionError` on failure

### `ws_send_and_collect(ws, session_key, message) -> str`
Send a message and collect the full response.
- Send `chat.send` with message + idempotency key
- Collect streaming `agent` events (accumulate `delta` text)
- Wait for `chat` event with `state: final` or `state: error`
- Timeout: 300s (5 minutes -- longer than harness-chat to allow complex operations)
- Returns response text or `[timeout waiting for response]` or `[error: <msg>]` or `[empty response]`

## Algorithm: Interactive Relay Mode

```
1. Send Telegram: "Harness relay connected. Send me a message..."
2. offset = None
3. Loop forever:
   a. Long-poll Telegram for updates (30s timeout)
   b. For each update:
      - Extract message text and chat ID
      - Skip if not from authorized CHAT_ID
      - Skip empty messages
      - Handle commands:
        /quit -> send "Relay stopped.", return
        /session -> send current session key, continue
        /start -> skip (Telegram bot auto-command)
      - Log "User: <text>" (truncated to 100 chars)
      - Forward message to agent via ws_send_and_collect
      - Log "Agent: <response>" (truncated to 100 chars)
      - Send response back to Telegram
```

## Algorithm: Scripted Mode

Uses the same 20-message conversation script as `harness-chat`:

```
1. Send Telegram header: "Starting N-message scripted conversation\nSession: <key>\n---"
2. For i = 1 to 20:
   a. tag = "[i/20]"
   b. Log "tag Sending: msg"
   c. Send Telegram: "person tag msg"
   d. Forward to agent via ws_send_and_collect
   e. Log "tag Response: response"
   f. Truncate response to 3000 chars
   g. Send Telegram: "robot tag response"
   h. Sleep 2 seconds
3. Send Telegram: "20-message conversation complete!"
4. Log "Scripted conversation done!"
```

### Scripted Message List

Same 20 messages as harness-chat (capabilities, tools, exec, file access, memory, creative tasks, etc.)

## Output Format

### Terminal (Interactive)
```
2026-02-24 12:00:00 Connected to OpenClaw (session: agent:main:harness-1708784400)
2026-02-24 12:00:30 User: What is the weather today?
2026-02-24 12:01:05 Agent: Based on a web search, the current weather...
```

### Terminal (Scripted)
```
2026-02-24 12:00:00 Connected to OpenClaw (session: agent:main:harness-1708784400)
2026-02-24 12:00:00 [1/20] Sending: Hey! What can you do?
2026-02-24 12:00:15 [1/20] Response: I can help you with a variety of tasks...
```

### Telegram (Interactive)
```
Harness relay connected.
Send me a message and I'll forward it to the agent.
/quit to stop
```
Then for each exchange, the raw agent response is sent.

### Telegram (Scripted)
```
Starting 20-message scripted conversation
Session: agent:main:harness-1708784400
------------------------------
[person] [1/20] Hey! What can you do?
[robot] [1/20] I can help you with a variety of tasks...
...
------------------------------
20-message conversation complete!
```

## Error Handling

| Error | Handling |
|-------|----------|
| WebSocket connection fails | `ConnectionError` raised, program exits |
| Bad challenge event | `ConnectionError` raised |
| Auth failure | `ConnectionError` raised |
| Response timeout (300s) | Returns `[timeout waiting for response]` |
| Telegram poll fails | Returns empty list, loop continues |
| Telegram send fails | Logs error, continues |
| Message from wrong chat | Silently ignored |
| KeyboardInterrupt | WebSocket closed in `finally` block |

## Differences from harness-chat

| Feature | harness-chat | harness-bot |
|---------|-------------|-------------|
| Interactive mode | No | Yes (default) |
| Scripted mode | Always | `--scripted` flag |
| Telegram polling | No | Yes |
| Response timeout | 120s | 300s |
| Logging | Print statements | `logging` module with timestamps |
| Connection reuse | Inline | Separate `ws_connect()` function |
| Session key | Module-level | Generated in `ws_connect()` |
| Cleanup | None | `finally` block closes WebSocket |

## Dependencies

- `websockets` Python package
- Python 3.7+ (`asyncio`, `argparse`, `json`, `logging`, `time`, `urllib.request`, `urllib.parse`, `uuid`)
- ~289 lines of Python

## Integration Points

- **Agent WebSocket API**: Port 18789
- **Telegram Bot API**: Polling for messages + sending responses
- **Telegram commands**: `/quit`, `/session`, `/start`

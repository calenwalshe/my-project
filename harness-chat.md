# harness-chat — Scripted 20-Message Conversation Test

## Purpose

A fire-and-forget test harness that sends a fixed sequence of 20 messages through the agent's WebSocket API and relays both prompts and responses to a Telegram channel. Tests the full agent pipeline: natural language, tool execution, file access, web search, memory operations, and creative generation. Designed to run unattended as a scheduled job or manual smoke test.

## Usage

```bash
python3 harness_chat.py
# No arguments. Runs the full 20-message conversation and exits.
```

## Architecture

```
┌──────────────────┐     WebSocket      ┌─────────────┐
│                  │ ──────────────────> │             │
│  harness_chat.py │                    │ Agent (WS)  │
│                  │ <────────────────── │ port 18789  │
└────────┬─────────┘                    └─────────────┘
         │
         │  Telegram Bot API
         v
┌──────────────────┐
│ Telegram Channel │
│ (monitoring)     │
└──────────────────┘
```

## Configuration

All hardcoded constants (replace with your own values):

| Constant | Description | Placeholder |
|----------|-------------|-------------|
| `BOT_TOKEN` | Telegram Bot API token | `<telegram-bot-token>` |
| `CHAT_ID` | Telegram chat/user ID for output | `<telegram-chat-id>` |
| `WS_URL` | WebSocket endpoint | `ws://localhost:18789/` |
| `OC_TOKEN` | Agent authentication token | `<agent-auth-token>` |
| `SESSION_KEY` | Unique session key | `agent:main:harness-chat-<timestamp>` |

Session key includes a Unix timestamp to ensure each run creates a fresh conversation.

## Conversation Script

The 20 messages test different agent capabilities:

| # | Message | Tests |
|---|---------|-------|
| 1 | "Hey! What can you do?" | Basic response, capability summary |
| 2 | "What model are you running on right now?" | Self-awareness / introspection |
| 3 | "Can you tell me a short joke?" | Creative generation |
| 4 | "What tools do you have access to?" | Tool enumeration |
| 5 | "Run uptime and tell me the result" | Command execution |
| 6 | "How much disk space is free on this machine?" | Command execution + parsing |
| 7 | "What files are in your workspace?" | File system access |
| 8 | "Write me a haiku about servers" | Creative constrained generation |
| 9 | "What is the capital of Mongolia?" | Knowledge retrieval |
| 10 | "Calculate 17 * 23 + 89" | Arithmetic |
| 11 | "What is the weather like today? Search the web if you can." | Web search |
| 12 | "Do you remember anything about me from memory?" | Memory retrieval |
| 13 | "Store this in memory: Calen prefers dark mode and drinks oat milk lattes" | Memory storage |
| 14 | "What did I just ask you to remember?" | Short-term recall |
| 15 | "Tell me something interesting about the number 42" | Knowledge + creativity |
| 16 | "Can you read the file /var/lib/openclaw/workspace/IDENTITY.md and show me what it says?" | File read |
| 17 | "Summarize that identity file in one sentence" | Context continuity |
| 18 | "What time is it in UTC right now?" | Real-time awareness |
| 19 | "Give me a motivational quote to end the day" | Creative generation |
| 20 | "Thanks for the chat! Say goodbye creatively." | Conversation closure |

## Protocol

Uses the standard OpenClaw WebSocket protocol (see `openclaw-ws-protocol.md`):

1. **Connect**: Wait for `connect.challenge` → send auth → verify `ok`
2. **For each message**: Send `chat.send` → collect streaming response → extract final text

### WebSocket Parameters

| Parameter | Value |
|-----------|-------|
| Ping interval | 30s |
| Ping timeout | 60s |
| Max frame size | 10 MB |
| Response timeout | 120s per message |

## Algorithm

```
1. Connect to WebSocket
2. Perform challenge/auth handshake
3. Send Telegram: "Starting 20-message conversation\nSession: <key>"
4. For i = 1 to 20:
   a. tag = "[i/20]"
   b. Print tag + message (truncated to 60 chars) to stdout
   c. Send tag + message to Telegram
   d. Send message via WebSocket, collect response
   e. Print tag + response (truncated to 80 chars) to stdout
   f. Truncate response to 3000 chars for Telegram
   g. Send tag + truncated response to Telegram
   h. Sleep 2 seconds
5. Send Telegram: "20-message conversation complete!"
6. Print "Done!"
```

### Response Collection (`ws_send_msg`)

```
Send chat.send request with message + session key
While True:
    Receive frame (timeout: 120s)
    If timeout → return "[timeout]"
    If error response → return "[error: <msg>]"
    If event "agent" with stream "assistant":
        Accumulate delta text
    If event "chat" with state "final" or "error":
        If no accumulated text, extract from message.content[]
        Break
Return accumulated text or "[empty]"
```

## Output Format

### Terminal Output
```
[1/20] Sending: Hey! What can you do?
[1/20] Response: I can help you with a variety of tasks! Here's what I can do:...
[2/20] Sending: What model are you running on right now?
[2/20] Response: I'm currently running on...
...
Done!
```

### Telegram Output
```
Starting 20-message conversation
Session: agent:main:harness-chat-1708784400
------------------------------
[1/20] Hey! What can you do?
[1/20] I can help you with a variety of tasks! Here's what I can do:...
[2/20] What model are you running on right now?
[2/20] I'm currently running on...
...
------------------------------
20-message conversation complete!
```

## Telegram Integration

### `tg_send(text) → bool`
- Sends via `POST https://api.telegram.org/bot<token>/sendMessage`
- Parameters: `chat_id`, `text` (URL-encoded form data)
- Truncates messages to 4096 characters (Telegram limit)
- Timeout: 15 seconds
- Returns True on success, False on error (logs error to stdout)

## Error Handling

| Error | Handling |
|-------|----------|
| WebSocket connection fails | Exception propagates, script exits |
| Auth handshake fails | Print "Connect failed", exit |
| Response timeout (120s) | Return `[timeout]` as response text |
| Request rejected by server | Return `[error: <message>]` |
| Empty response | Return `[empty]` |
| Telegram send fails | Log error, continue (non-fatal) |

## Dependencies

- `websockets` Python package (async WebSocket)
- Python 3.7+ standard library (`asyncio`, `json`, `uuid`, `time`, `urllib.request`, `urllib.parse`)
- ~148 lines of Python
- Runs directly as a script (no `if __name__` guard — uses `asyncio.run(main())` at module level)

## Integration Points

- **Agent WebSocket API**: Port 18789, standard OpenClaw protocol
- **Telegram Bot API**: For output relay to monitoring channel
- No return values or exit codes — success/failure is determined by reviewing the Telegram output

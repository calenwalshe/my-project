# OpenClaw WebSocket Protocol Reference

## Purpose

This document specifies the WebSocket protocol used by all harness and CLI tools to communicate with the agent platform. All tools in this toolkit (oc-chat, harness-chat, harness-bot, harness-relay, deep-conv, deep-explore, browse-batch, context-test, discogs-explore) implement this same protocol. This reference captures the shared connection handshake, message formats, streaming response collection, and Telegram bridging patterns.

## Connection

### Endpoint

```
ws://<host>:18789/ws     # Standard path (used by oc-chat)
ws://<host>:18789/       # Root path (used by all harness scripts)
```

Both paths are functionally equivalent. Port 18789 is the agent platform's WebSocket gateway.

### WebSocket Configuration

| Parameter | Typical Value | Notes |
|-----------|---------------|-------|
| Ping interval | 30-60s | Harnesses use 30s for chat, 60s for browser tasks |
| Ping timeout | 60-120s | Matches 2x ping interval |
| Max frame size | 10 MB (`10 * 1024 * 1024`) | Accommodates large responses with tool output |
| Open timeout | 30s | Only set by some harnesses |
| Close timeout | 10s | Only set by some harnesses |

## Handshake Protocol

### Step 1: Challenge (Server -> Client)

Immediately after WebSocket connection, the server sends:

```json
{
  "type": "event",
  "event": "connect.challenge"
}
```

The client MUST wait for this event before sending authentication. Timeout: 10 seconds.

### Step 2: Connect Request (Client -> Server)

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
      "displayName": "<tool-name>",
      "version": "0.1",
      "platform": "linux",
      "mode": "cli"
    },
    "role": "operator",
    "scopes": ["operator.admin"],
    "auth": {
      "token": "<AUTH_TOKEN>"
    }
  }
}
```

**Client identification** varies by tool:

| Tool | displayName |
|------|-------------|
| oc-chat | `test-harness` |
| harness-chat | `harness-chat` |
| harness-bot | `harness-bot` |
| harness-relay | `harness-relay` |
| deep-conv | `deep-conv` |
| deep-explore | `<batch-agent-name>` (alpha, beta, etc.) |
| browse-batch | `batch<N>` |
| context-test | `context-test` |
| discogs-explore | `discogs-explorer` |

### Step 3: Connect Response (Server -> Client)

```json
{
  "type": "res",
  "id": "<same-as-request>",
  "ok": true
}
```

If `ok` is false or missing, authentication has failed. The client should log the response and disconnect.

## Message Types

### Request (`type: "req"`)

Client-to-server messages. Used for:
- `connect` -- Authentication
- `chat.send` -- Send a user message
- `health` -- Health check (oc-chat REPL only)
- `status` -- Server status (oc-chat REPL only)

### Response (`type: "res"`)

Server acknowledgments for requests. Contains the same `id` as the request.

```json
{
  "type": "res",
  "id": "<request-id>",
  "ok": true,
  "payload": {
    "status": "queued"
  }
}
```

If `ok` is false:
```json
{
  "type": "res",
  "id": "<request-id>",
  "ok": false,
  "error": "error description"
}
```

### Event (`type: "event"`)

Server-to-client push messages. Sent during response generation.

## Chat Send Request

```json
{
  "type": "req",
  "id": "<8-char-uuid>",
  "method": "chat.send",
  "params": {
    "sessionKey": "<session-key>",
    "message": "<user-message-text>",
    "idempotencyKey": "<full-uuid>"
  }
}
```

### Session Key Format

```
agent:<agent-name>:<session-identifier>
```

Examples:
- `agent:main:main` -- Default persistent session
- `agent:main:harness-chat-1708784400` -- Timestamped test session
- `agent:main:explore-alpha-1708784400-a1b2c3d4` -- Batch exploration session
- `agent:main:discogs-1-1708784400-a1b2c3d4` -- Per-page isolated session

### Idempotency Key

A full UUID4 string. Prevents duplicate processing if the same message is sent twice.

### Request ID

An 8-character prefix of a UUID4:

```python
def make_id():
    return str(uuid.uuid4())[:8]
```

## Streaming Response Events

After sending `chat.send`, the client enters a receive loop collecting events until the conversation is complete.

### Agent Events (`event: "agent"`)

Streaming events from the agent during response generation:

```json
{
  "type": "event",
  "event": "agent",
  "payload": {
    "stream": "<stream-type>",
    "data": { ... }
  }
}
```

#### Stream: `assistant`
Incremental text output from the LLM:

```json
{
  "stream": "assistant",
  "data": {
    "delta": "partial response text"
  }
}
```

**Client behavior:** Accumulate `delta` values into the final response text. Print to stdout for real-time streaming display.

#### Stream: `lifecycle`
Phase transitions during agent processing:

```json
{
  "stream": "lifecycle",
  "data": {
    "phase": "thinking"
  }
}
```

Common phases: `thinking`, `executing`, `responding`

**Client behavior:** Debug log only.

#### Stream: `tool_call`
Agent is invoking a tool:

```json
{
  "stream": "tool_call",
  "data": {
    "name": "exec"
  }
}
```

**Client behavior:** Display tool name to stderr (oc-chat) or ignore (harnesses).

#### Stream: `tool_result`
Result from a tool invocation:

```json
{
  "stream": "tool_result",
  "data": { ... }
}
```

**Client behavior:** Debug log only.

#### Stream: `thinking`
Agent reasoning/thinking output:

**Client behavior:** Display indicator to stderr (oc-chat) or ignore.

### Chat Events (`event: "chat"`)

Session state changes:

#### State: `final`
Response is complete:

```json
{
  "type": "event",
  "event": "chat",
  "payload": {
    "state": "final",
    "message": {
      "content": [
        {
          "type": "text",
          "text": "complete response text"
        }
      ]
    }
  }
}
```

**Client behavior:** If no text was accumulated from `assistant` deltas, extract text from `message.content[]` array. This handles cases where the response was generated without streaming.

#### State: `error`
An error occurred:

```json
{
  "type": "event",
  "event": "chat",
  "payload": {
    "state": "error",
    "message": {
      "content": [
        {
          "type": "text",
          "text": "error description"
        }
      ]
    }
  }
}
```

**Client behavior:** Extract error text from content array, treat as final response.

### Health Events (`event: "health"`)

Periodic server health broadcasts. **Client behavior:** Ignore (filtered from debug output in oc-chat).

## Response Collection Algorithm

All tools implement the same pattern for collecting a complete response:

```python
async def collect_response(ws, req_id, timeout=120):
    final_text = ""

    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            return "[timeout]"

        frame = json.loads(raw)

        # Check for error response to our request
        if frame["type"] == "res" and frame["id"] == req_id:
            if not frame.get("ok"):
                return f"[error: {frame.get('error', '?')}]"

        # Process events
        if frame["type"] == "event":
            event = frame.get("event", "")
            payload = frame.get("payload", {})

            if event == "agent" and payload.get("stream") == "assistant":
                delta = payload.get("data", {}).get("delta", "")
                if delta:
                    final_text += delta

            elif event == "chat":
                state = payload.get("state", "")
                if state in ("final", "error"):
                    # Fallback: extract from content array
                    if not final_text:
                        for part in payload.get("message", {}).get("content", []):
                            if isinstance(part, dict) and part.get("type") == "text":
                                final_text += part.get("text", "")
                    break

    return final_text or "[empty]"
```

### Timeout Values by Tool

| Tool | Timeout | Rationale |
|------|---------|-----------|
| harness-chat | 120s | Simple chat messages |
| context-test | 120s | Simple recall questions |
| harness-bot | 300s | May invoke complex tools |
| harness-relay | 300s | User-driven, unpredictable |
| oc-chat | 300s | General purpose |
| deep-conv | 180s | Browser navigation per step |
| browse-batch | 300s | Browser navigation |
| deep-explore | 600s | Complex multi-step browser missions |
| discogs-explore | 600s | Cloudflare bypass + navigation |

## Telegram Bridging Pattern

All harness tools relay messages to Telegram using this shared pattern:

### `tg_send(text) -> bool`

```python
def tg_send(text):
    if len(text) > 4096:
        text = text[:4090] + "\n[...]"

    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
    }).encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read()).get("ok", False)
```

**Key properties:**
- Max message length: 4096 characters (Telegram limit)
- Truncation marker: `\n[...]`
- HTTP timeout: 15 seconds
- Uses `urllib.request` (no external HTTP library)
- Error handling: varies by tool (log + continue, or silently ignore)

### oc-chat Enhanced Telegram

The `oc-chat` client has additional Telegram features:
- Parse mode: Markdown (with fallback to plain text on parse error)
- Web page preview: disabled
- Configurable prefix per message

## Shared Utility: `make_id()`

All tools generate request IDs the same way:

```python
import uuid

def make_id():
    return str(uuid.uuid4())[:8]
```

Returns 8 characters, sufficient for request correlation within a single session.

## Error Handling Patterns

### Connection Errors

| Error | Common Handling |
|-------|----------------|
| Timeout waiting for challenge | Print error, exit |
| Auth rejected (`ok: false`) | Print response, exit |
| WebSocket connection refused | Exception propagates, exit |

### Response Errors

| Error | Common Handling |
|-------|----------------|
| Frame timeout | Return `[timeout]` or `[timeout after Ns]` |
| Request rejected | Return `[error: <message>]` |
| Empty response | Return `[empty]` or `[empty response]` |
| WebSocket disconnect | Exception propagates |

### Telegram Errors

All tools treat Telegram send failures as non-fatal. The test continues even if Telegram output fails.

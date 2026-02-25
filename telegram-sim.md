# telegram-sim -- Message Routing Simulator

## Purpose

A development/testing tool that simulates the message routing pipeline used when a Telegram message arrives at the agent system. It parses messages for model hints (e.g., `@codex`, `@smart`), auto-classifies untagged messages using heuristic pattern matching, routes to the appropriate LLM backend, and displays the full routing decision chain. Useful for testing routing logic without going through the actual Telegram bot.

## Usage

```bash
telegram-sim "your message here"                     # Simulate single message
telegram-sim "@smart explain quantum computing"       # With explicit model hint
telegram-sim --model gpt-5.2-codex-high "question"   # Force specific model
telegram-sim --batch                                  # Run predefined test suite
telegram-sim --list-models                            # Show all available models
telegram-sim --quiet "message"                        # JSON-only output
```

## Architecture

```
Input Message
     |
     v
+---------------------+
| 1. Extract @hint    |  regex pattern matching
|    (e.g., @codex)   |
+----------+----------+
           |
           v
      hint found?
     +-----+-----+
     yes         no
     |           |
     v           v
     use   +------------------+
     hint  | 2. Auto-classify |  heuristic scoring
           |    (code/reason/ |
           |     simple)      |
           +--------+---------+
                    |
                    v
           +----------------+
           | 3. Resolve     |  aliases -> canonical names
           |    model name  |
           +--------+-------+
                    |
                    v
           +----------------+
           | 4. Select      |  model -> backend URL
           |    backend     |
           +--------+-------+
                    |
                    v
           +----------------+
           | 5. Send HTTP   |  POST to backend
           |    request     |
           +--------+-------+
                    |
                    v
           Display result
```

## CLI Arguments

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `message` | -- | positional | None | Message to simulate |
| `--model` | `-m` | string | None | Force a specific model (bypass routing) |
| `--batch` | `-b` | flag | false | Run batch test suite |
| `--list-models` | `-l` | flag | false | List all models and aliases |
| `--quiet` | `-q` | flag | false | JSON output only (no verbose display) |

## Model Routing Configuration

### Backend Endpoints

Three internal LLM backend services, each serving different model families:

| Backend | Port | Models Served |
|---------|------|---------------|
| Codex Bridge | 9090 | GPT/Codex family (code-optimized) |
| LiteLLM Proxy | 4000 | DeepSeek family (chat/reasoning) |
| Gemini Bridge | 9091 | Gemini family (multimodal) |

All backends expose OpenAI-compatible `/v1/chat/completions` endpoints.

### Model -> Backend Mapping

| Model ID | Backend |
|----------|---------|
| `gpt-5.2-codex` | Codex Bridge |
| `gpt-5.2` | Codex Bridge |
| `gpt-5.2-codex-low` | Codex Bridge |
| `gpt-5.2-codex-high` | Codex Bridge |
| `gpt-5.2-codex-xhigh` | Codex Bridge |
| `codex` | Codex Bridge |
| `deepseek-chat` | LiteLLM |
| `deepseek-reasoner` | LiteLLM |
| `gemini-2.5-flash` | Gemini Bridge |
| `gemini-2.5-pro` | Gemini Bridge |
| `gemini-vision` | Gemini Bridge |

### Model Aliases

| Alias | Resolves To |
|-------|-------------|
| `fast` | `gpt-5.2-codex-low` |
| `smart` | `gpt-5.2-codex-high` |
| `max` | `gpt-5.2-codex-xhigh` |
| `codex` | `gpt-5.2-codex` |
| `chat` | `deepseek-chat` |
| `reasoner` | `deepseek-reasoner` |
| `gemini` | `gemini-2.5-flash` |
| `vision` | `gemini-vision` |

## Algorithm: Model Hint Extraction

`extract_model_hint(message) -> (clean_message, model_hint)`

Scans the message for `@model` mentions using ordered regex patterns. First match wins. The `@` prefix and model name are stripped from the returned clean message.

**Pattern priority (first match wins):**
1. `@(gpt-?5\.?2-?codex-?xhigh|xhigh|max)` -> `gpt-5.2-codex-xhigh`
2. `@(gpt-?5\.?2-?codex-?high|high|smart)` -> `gpt-5.2-codex-high`
3. `@(gpt-?5\.?2-?codex-?low|low|fast|quick)` -> `gpt-5.2-codex-low`
4. `@(gpt-?5\.?2-?codex|codex)` -> `gpt-5.2-codex`
5. `@(gpt-?5\.?2)` -> `gpt-5.2`
6. `@(deepseek-?reasoner|reasoner)` -> `deepseek-reasoner`
7. `@(deepseek-?chat|chat)` -> `deepseek-chat`
8. `@(gemini-?vision|vision)` -> `gemini-vision`
9. `@(gemini)` -> `gemini-2.5-flash`

All matching is case-insensitive. Patterns are checked in order from most-specific to least-specific to avoid ambiguous matches.

## Algorithm: Auto-Classification

`classify_message(message) -> (model, confidence, reason)`

When no `@hint` is found and no `--model` override is specified, the message is auto-classified using heuristic pattern scoring.

### Pattern Categories

**Coding patterns** (each match scores +1):
- `\b(write|create|implement|code|function|class|script|program)\b`
- `\b(debug|fix|refactor|optimize)\b`
- `\b(python|javascript|typescript|go|rust|java|c\+\+)\b`
- `` ``` `` (code fence -- scores +3, strong signal)

**Reasoning patterns** (each match scores +1):
- `\b(explain|analyze|compare|evaluate|think|reason)\b`
- `\b(why|how does|what if|pros and cons)\b`
- `\b(step by step|break down|elaborate)\b`

**Simple patterns** (each match scores +1):
- `^(hi|hello|hey|thanks|ok|yes|no)\b`
- `\b(what is|define|who is)\b`
- `^.{0,30}$` (very short messages)

### Scoring Adjustments

- Word count > 100: reasoning score +1
- Word count > 200: coding score +1
- Code fences (`` ``` ``): coding score +3

### Model Selection

| Highest Score Category | Selected Model | Reason String |
|----------------------|----------------|---------------|
| Coding | `gpt-5.2-codex` | `auto_gpt_5_2_codex` |
| Reasoning | `deepseek-reasoner` | `auto_deepseek_reasoner` |
| Simple | `deepseek-chat` | `auto_deepseek_chat` |
| All zero | `deepseek-chat` | `default_fallback` |

### Confidence Calculation

```
if best_score == 0:
    confidence = 0.5
else:
    confidence = min(0.95, 0.5 + (best_score / 6))
```

For forced model or explicit hints, confidence is always 1.0.

## HTTP Request Format

Sent to the selected backend's `/v1/chat/completions` endpoint:

```json
{
  "messages": [
    {"role": "user", "content": "<clean_message>"}
  ],
  "model": "<selected_model>"
}
```

- Content-Type: `application/json`
- Method: POST
- Timeout: 120 seconds

## Output Format

### Verbose Output (default)

```
============================================================
TELEGRAM SIMULATION - 2026-02-24 12:34:56
============================================================

[INCOMING MESSAGE]
  "your message here"

[MODEL HINT DETECTED]        <- only if @hint found
  Hint: @codex
  Clean message: "your message here"

[ROUTING DECISION]
  Model: gpt-5.2-codex
  Reason: explicit_hint
  Confidence: 100%
  Backend: localhost

[SENDING REQUEST...]

[RESPONSE RECEIVED]
  Latency: 1250ms
  Reasoning effort: N/A
  Attempts: 1

[ASSISTANT RESPONSE]
  The model's response text here (truncated to 500 chars)...

============================================================
```

### Quiet Output (`--quiet`)

Returns a JSON object:

```json
{
  "original_message": "the full input",
  "clean_message": "input with @hint removed",
  "model_hint": "@codex or empty string",
  "selected_model": "gpt-5.2-codex",
  "routing_reason": "explicit_hint",
  "confidence": 1.0,
  "backend_url": "http://localhost:9090/v1/chat/completions",
  "success": true,
  "response": "full response text",
  "latency_ms": 1250,
  "meta": {"reasoning_effort": "...", "attempts": 1},
  "error": null
}
```

### Batch Test Output

Runs 7 predefined test cases covering: simple greeting, coding task, fast/smart/max hints, reasoning task, and forced model override. Prints per-test verbose output plus a summary table:

```
TEST SUMMARY
===========
Description                                        Model                Status   Latency
------------------------------------------------------------------------------------------
Simple greeting - should route to chat              deepseek-chat        OK       450ms
Coding task - should route to codex                 gpt-5.2-codex       OK       1200ms
...

Total: 7/7 tests passed
```

### Model List Output

```
Available Models:
------------------------------------------------------------
Model ID                  Backend          Alias
------------------------------------------------------------
deepseek-chat             localhost        chat
deepseek-reasoner         localhost        reasoner
gemini-2.5-flash          localhost        gemini
...

Aliases:
------------------------------------------------------------
  @chat          -> deepseek-chat
  @codex         -> gpt-5.2-codex
  ...
```

## Error Handling

| Error | Handling |
|-------|----------|
| HTTP error from backend | Return `error: "HTTP <code>: <reason>"` |
| Connection refused | Return `error: "Connection failed: <reason>"` |
| Timeout (120s) | Return `error` with latency |
| No message provided | Print help |
| Invalid model name | Falls through to codex backend (default) |

## Dependencies

- Python 3 standard library only (`argparse`, `json`, `re`, `time`, `urllib.request`, `urllib.error`, `datetime`, `typing`)
- No external packages required
- ~403 lines of Python

## Integration Points

- **Codex Bridge** on port 9090 (OpenAI-compatible API)
- **LiteLLM Proxy** on port 4000 (OpenAI-compatible API)
- **Gemini Bridge** on port 9091 (OpenAI-compatible API)
- All backends are expected to be running on localhost within the Docker network

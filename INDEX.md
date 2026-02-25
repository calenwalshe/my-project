# Agent Stack Dev Tools — Implementation Specifications

This directory contains standalone implementation specifications for ~16 dev tools used to manage, test, and monitor an agent-stack infrastructure. Each spec is detailed enough to rebuild the tool from scratch without seeing the original source code.

**No credentials, IP addresses, or sensitive configuration are included.** All auth tokens, hostnames, and API keys are represented as placeholders.

## Quick Reference

| Spec | Tool | Category | Lines | Description |
|------|------|----------|-------|-------------|
| [agent-exec.md](agent-exec.md) | `agent-exec` | CLI | ~15 | SSH jump-host remote execution wrapper |
| [oc-chat.md](oc-chat.md) | `oc-chat` + `oc-chat-client.py` | CLI | ~460 | Interactive WebSocket chat client (bash + Python) |
| [telegram-sim.md](telegram-sim.md) | `telegram_sim.py` | CLI | ~403 | Message routing simulator with auto-classification |
| [watchdog.md](watchdog.md) | `watchdog.sh` | Monitoring | ~26 | Lightweight Docker container watchdog |
| [codex-health-monitor.md](codex-health-monitor.md) | `codex-health-monitor.py` | Monitoring | ~245 | Long-running health monitor daemon with metrics |
| [doctorclawd.md](doctorclawd.md) | `doctorclawd.py` | Diagnostics | ~624 | Comprehensive system diagnostics (tiered checks + smoke tests) |
| [harness-chat.md](harness-chat.md) | `harness_chat.py` | Test Harness | ~148 | Scripted 20-message conversation test |
| [harness-bot.md](harness-bot.md) | `harness_bot.py` | Test Harness | ~289 | Dual-mode: interactive Telegram relay + scripted conversation |
| [harness-relay.md](harness-relay.md) | `harness_relay.py` | Test Harness | ~209 | Interactive Telegram-to-agent relay |
| [deep-conv.md](deep-conv.md) | `deep_conv.py` | Test Harness | ~331 | Multi-turn browser navigation missions (20 sites × 3 steps) |
| [deep-explore.md](deep-explore.md) | `deep_explore.py` | Test Harness | ~402 | Batch browser exploration (6 batches, single-message missions) |
| [browse-batch.md](browse-batch.md) | `browse_batch.py` | Test Harness | ~199 | Simple batch browse test (4 batches × 5 sites) |
| [context-test.md](context-test.md) | `context_test.py` | Test Harness | ~268 | 30-message context retention test (6 phases, 22 checkpoints) |
| [discogs-explore.md](discogs-explore.md) | `discogs_explore.py` | Test Harness | ~235 | Cloudflare bypass verification via Discogs navigation |
| [openclaw-ws-protocol.md](openclaw-ws-protocol.md) | — | Protocol | — | Shared WebSocket protocol used by all harness tools |

## Architecture Overview

### Tool Categories

**CLI Tools** — Developer-facing command-line interfaces:
- `agent-exec`: Execute commands on a remote server through an SSH jump host
- `oc-chat`: Chat with the agent via WebSocket (same interface as Telegram)
- `telegram-sim`: Test the message routing pipeline (model hints, auto-classification)

**Monitoring & Diagnostics** — Keep infrastructure healthy:
- `watchdog`: Cron-friendly script that restarts crashed containers
- `codex-health-monitor`: Long-running daemon with failure tracking, auto-restart, and metrics export
- `doctorclawd`: On-demand diagnostic tool with tiered checks (quick/full/smoke/all)

**Test Harnesses** — Automated agent testing via WebSocket + Telegram relay:
- `harness-chat`: Fire-and-forget 20-message conversation
- `harness-bot`: Interactive relay OR scripted conversation (dual-mode)
- `harness-relay`: Interactive relay only (simplified)
- `deep-conv`: Multi-turn browser navigation (3 conversational steps per site)
- `deep-explore`: Single-prompt multi-step browser missions (6 parallel batches)
- `browse-batch`: Simple "go here, describe what you see" browser test (4 batches)
- `context-test`: Long-context retention across 30 messages with automated scoring
- `discogs-explore`: Cloudflare-protected site navigation (bypass verification)

### Shared Protocol

All WebSocket-based tools (everything except `agent-exec`, `telegram-sim`, `watchdog`, `codex-health-monitor`, and `doctorclawd`) implement the same protocol documented in [openclaw-ws-protocol.md](openclaw-ws-protocol.md):

1. **Challenge-response authentication** (connect.challenge → connect → ok)
2. **Chat message sending** (chat.send with session key + idempotency key)
3. **Streaming response collection** (agent events with deltas → chat.final)
4. **Telegram output relay** (truncated to 4096 chars)

### Dependency Map

```
agent-exec ──────────────────────> Remote server (SSH)
oc-chat ──┬── agent-exec (remote mode)
          └── SSH tunnel (local mode)
              └── oc-chat-client.py ──> Agent WS API
telegram-sim ──> Codex Bridge / LiteLLM / Gemini Bridge (HTTP)
watchdog ──> Docker daemon
codex-health-monitor ──> Service health endpoint + Docker
doctorclawd ──> Docker + HTTP endpoints + SQLite traces

harness-chat ──┐
harness-bot  ──┤
harness-relay ──┤
deep-conv    ──┤── Agent WS API (port 18789) + Telegram Bot API
deep-explore ──┤
browse-batch ──┤
context-test ──┤
discogs-explore┘
```

### Browser Harness Comparison

| Harness | Sites | Msgs/Site | Batches | Timeout | Focus |
|---------|-------|-----------|---------|---------|-------|
| `deep-conv` | 20 | 3 turns | 1 (sequential) | 180s/turn | Multi-turn navigation |
| `deep-explore` | 20 | 1 prompt | 6 (parallel) | 600s/prompt | Complex single-prompt missions |
| `browse-batch` | 20 | 1 prompt | 4 (parallel) | 300s/prompt | Simple "describe this page" |
| `discogs-explore` | 5 | 1 prompt | 1 (sequential) | 600s/prompt | Cloudflare bypass testing |

### Conversation Harness Comparison

| Harness | Messages | Modes | Scoring | Focus |
|---------|----------|-------|---------|-------|
| `harness-chat` | 20 | Scripted only | None | Basic pipeline test |
| `harness-bot` | 20 / unlimited | Scripted + Interactive | None | Flexible testing |
| `harness-relay` | unlimited | Interactive only | None | Live relay |
| `context-test` | 30 | Scripted only | 22 checkpoints | Memory retention |

## Spec Template

Each spec follows this structure:
- **Purpose** — What the tool does and why
- **Usage** — CLI arguments, modes, examples
- **Architecture** — Components and data flow
- **Configuration** — All settings with placeholder values
- **Algorithm** — Step-by-step logic
- **Data Structures** — Classes, enums, key state
- **Output Format** — Terminal, JSON, Telegram messages
- **Error Handling** — Timeouts, retries, failure modes
- **Dependencies** — Libraries and external tools
- **Integration Points** — Services, ports, endpoints

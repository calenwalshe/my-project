# deep-explore -- Batch Browser Exploration Harness

## Purpose

Tests the agent's browser navigation with single-message multi-step missions across 20 websites, split into 6 batches that can be run in parallel. Each mission is a complex prompt requiring 3-5 sequential actions (navigate, explore, extract, report). Unlike `deep-conv` which uses 3 separate conversational turns per site, this tool sends one comprehensive prompt per site and evaluates the response for depth of navigation.

## Usage

```bash
python3 deep_explore.py <batch>              # Run batch 1-6
python3 deep_explore.py <batch> <agent_name> # Custom agent display name
python3 deep_explore.py 1                    # Batch 1: sites 1-4 (agent alpha)
python3 deep_explore.py 3 gamma              # Batch 3: sites 9-12 (agent gamma)
```

## Architecture

```
deep_explore.py (batch N)
     |
     |  For each site in batch:
     |    Single multi-step mission prompt
     |
     +---------------> Agent (WebSocket)
     |                   |
     |                   +---> Browser tool (multiple navigations)
     |                   |
     |  <--------------- response (all steps in one reply)
     |
     +---------------> Telegram (relay + score)
     |
     +-- Batch summary
```

## Batch Distribution

| Batch | Agent Name | Sites | Count |
|-------|------------|-------|-------|
| 1 | alpha | 1-4 | 4 |
| 2 | beta | 5-8 | 4 |
| 3 | gamma | 9-12 | 4 |
| 4 | delta | 13-16 | 4 |
| 5 | epsilon | 17-18 | 2 |
| 6 | zeta | 19-20 | 2 |

Total: 20 sites across 6 batches. Each batch can run independently in a separate process.

## Configuration

| Constant | Value |
|----------|-------|
| `BOT_TOKEN` | Telegram bot token |
| `CHAT_ID` | Telegram chat ID |
| `WS_URL` | `ws://localhost:18789/` |
| `OC_TOKEN` | Agent auth token |
| Per-mission timeout | 600 seconds (10 minutes) |
| Delay between sites | 5 seconds |

Session key: `agent:main:explore-<agent_name>-<unix-timestamp>-<8-char-uuid>`

## Site Missions (20 total)

Each mission is a single prompt with 4-5 numbered steps:

### Batch 1 (alpha)
| # | Site | Key Tasks |
|---|------|-----------|
| 1 | Hacker News Top | Name #1 story -> click link -> extract first paragraph -> report domain |
| 2 | Wikipedia Random | Land on random -> click first blue link -> click another -> connect 3 articles |
| 3 | arXiv CS.AI | Name first paper -> click abstract -> extract first sentence + author |
| 4 | Lobste.rs | Find "programming" tagged story -> click comments -> extract comment + score |

### Batch 2 (beta)
| # | Site | Key Tasks |
|---|------|-----------|
| 5 | GitHub Trending | Name #1 repo -> click in -> README first line -> stars + language |
| 6 | Hacker News Ask | Find Ask HN -> click comments -> extract first comment -> total count |
| 7 | Product Hunt | Name #1 product -> click in -> tagline + maker + upvotes + review |
| 8 | Stack Overflow | #1 voted question -> click in -> vote score -> accepted answer |

### Batch 3 (gamma)
| # | Site | Key Tasks |
|---|------|-----------|
| 9 | BBC News | Lead story -> click in -> first paragraph -> related story |
| 10 | Lobste.rs | Same as #4 (different run context) |
| 11 | Bundlephobia | Search "react" -> click result -> sizes + download time + dependency |
| 12 | Wolfram Alpha | Population of Tokyo -> extract -> distance Tokyo-NY -> extract |

### Batch 4 (delta)
| # | Site | Key Tasks |
|---|------|-----------|
| 13 | Can I Use | Search CSS Grid -> global support % -> limited browser -> version details |
| 14 | DevDocs | Python 3 -> string methods -> str.split() -> signature + description |
| 15 | Wikidata Q42 | Identify Q42 -> interesting fact -> Wikipedia link -> first sentence |
| 16 | NPR | Top story -> click in -> byline -> first paragraph |

### Batch 5 (epsilon)
| # | Site | Key Tasks |
|---|------|-----------|
| 17 | Archive.org | NASA moon landing search -> click result -> media type -> upload info |
| 18 | Wiktionary | "serendipity" -> etymology -> origin language -> click etymology word |

### Batch 6 (zeta)
| # | Site | Key Tasks |
|---|------|-----------|
| 19 | OpenStreetMap | Search Colosseum Rome -> click result -> map description -> tags |
| 20 | Wayback Machine | Amazon circa 2000 -> describe -> find category -> click deeper |

## Depth Scoring Algorithm

After each mission response, classify the depth of navigation achieved:

```python
resp_lower = response.lower()

navigated = any(x in resp_lower for x in [
    "clicked", "navigated", "found", "i see", "shows", "page"
])

extracted = any(x in resp_lower for x in [
    "1.", "2.", "3.", "4.", "first", "title:", "author:", "---", "bullet"
])

failed = (
    "[timeout]" in response or
    "[empty]" in response or
    len(response) < 50
)

blocked = any(x in resp_lower for x in [
    "blocked", "captcha", "cloudflare", "access denied"
])
```

| Depth | Criteria |
|-------|----------|
| `DEEP` | navigated AND extracted AND NOT failed |
| `SHALLOW` | navigated AND NOT failed AND NOT extracted |
| `BLOCKED` | blocked keywords detected |
| `FAILED` | timeout, empty, or response < 50 chars |

## Algorithm

```
1. Parse batch number from argv[1] (default: 1)
2. Look up agent name from BATCH_NAMES map (or use "agent<N>")
3. Select missions for this batch from BATCHES map
4. Calculate global_offset (sum of sites in previous batches)
5. Generate session key: agent:main:explore-<name>-<ts>-<uuid8>
6. Connect WebSocket, authenticate
7. Send Telegram: "--- Agent <NAME> starting (sites N-M) ---"
8. For each mission:
   a. site_num = global_offset + local_index + 1
   b. tag = "[site_num/20]"
   c. Send Telegram: "person tag <site_name>\n<mission_prompt>"
   d. Record start time
   e. Send mission via WebSocket (600s timeout)
   f. Record elapsed time
   g. Print tag + elapsed + response preview
   h. Truncate response to 3000 chars for Telegram
   i. Send Telegram: "robot tag <site_name> (Ns)\n<response>"
   j. Score depth (DEEP/SHALLOW/BLOCKED/FAILED)
   k. Record result
   l. Sleep 5 seconds
9. Generate batch summary
10. Print + send to Telegram
```

### Batch Summary Format

```
Agent ALPHA results:
[D] Hacker News Top (45s)
[D] Wikipedia Random (62s)
[S] arXiv CS.AI (38s)
[F] Lobste.rs (600s)
```

Depth codes: D=DEEP, S=SHALLOW, X=BLOCKED, F=FAILED

## WebSocket Parameters

| Parameter | Value |
|-----------|-------|
| Ping interval | 60s |
| Ping timeout | 120s |
| Max frame size | 10 MB |
| Open timeout | 30s |
| Close timeout | 10s |
| Per-mission timeout | 600s (10 minutes) |

The 600s timeout is the longest of any harness -- complex browser missions with multiple navigation steps can take several minutes.

## Output Format

### Telegram
- Start: `--- Agent ALPHA starting (sites 1-4) ---`
- Per-site user: `person [N/20] <site>\n<full mission prompt>`
- Per-site agent: `robot [N/20] <site> (Ns)\n<response (max 3000 chars)>`
- Summary: Compact depth codes per site

### Terminal
```
[1/20] Hacker News Top
[1/20] 45 s: The #1 story on Hacker News today is...
[2/20] Wikipedia Random
[2/20] 62 s: I landed on the article "Magnetic North Pole"...
...
Agent ALPHA results:
[D] Hacker News Top (45s)
...
```

## Error Handling

| Error | Handling |
|-------|----------|
| Invalid batch number | Print error, exit |
| WebSocket timeout (600s) | Return `[timeout]` |
| Connection failure | Print "Connect failed", exit |
| Error response | Return `[error: <msg>]` |
| Telegram failure | Print error, continue |

## Dependencies

- `websockets` Python package
- Python 3.7+ stdlib (`asyncio`, `json`, `sys`, `time`, `urllib.request`, `urllib.parse`, `uuid`)
- ~402 lines of Python

## Integration Points

- **Agent WebSocket API**: Port 18789
- **Agent browser tool**: Required for site navigation
- **Telegram Bot API**: Progress relay
- **Parallel execution**: 6 instances can run simultaneously (one per batch)

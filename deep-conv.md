# deep-conv -- Multi-Turn Browser Navigation Missions

## Purpose

Tests the agent's browser navigation capability through multi-turn conversations. Unlike single-prompt exploration tools, this tool breaks each site mission into 3 sequential conversational steps (explore, navigate, extract), sending each as a separate message and waiting for the response before proceeding. This avoids LLM timeouts from overly complex single prompts while testing the agent's ability to maintain context across turns.

## Usage

```bash
python3 deep_conv.py
# No arguments. Runs all 20 site missions sequentially.
```

## Architecture

```
deep_conv.py
     |
     |  For each of 20 sites:
     |    Step 1 (explore): "Go to URL and describe..."
     |    Step 2 (navigate): "Click into... find..."
     |    Step 3 (extract): "Extract specific facts..."
     |
     +---------------> Agent (WebSocket)
     |                   |
     |                   +---> Browser tool
     |                   |      |
     |                   |      +---> Target website
     |                   |
     |  <--------------- response
     |
     +---------------> Telegram (relay output)
     |
     +-- Final report (per-site scoring)
```

## Configuration

| Constant | Value |
|----------|-------|
| `BOT_TOKEN` | Telegram bot token |
| `CHAT_ID` | Telegram chat ID |
| `WS_URL` | `ws://localhost:18789/` |
| `OC_TOKEN` | Agent auth token |
| Per-message timeout | 180 seconds |
| Delay between steps | 3 seconds |
| Delay between sites | 5 seconds |

Session key: `agent:main:deep-conv-<unix-timestamp>` (single session for all sites -- context carries over)

## Site Missions (20 sites x 3 steps)

| # | Site | Step 1 (explore) | Step 2 (navigate) | Step 3 (extract) |
|---|------|-------------------|--------------------|-------------------|
| 1 | GitHub Trending | Go to trending, name #1 repo | Click into repo, first line of README | Stars count, primary language |
| 2 | Hacker News Ask | Go to /ask, first Ask HN title | Click comments, count comments | First top-level comment text |
| 3 | Stack Overflow | Go to /questions?tab=Votes, #1 question | Click in, votes and views | First sentence of accepted answer |
| 4 | Wolfram Alpha | Search "population of Tokyo" | Search "distance from Tokyo to London" | Report distance shown |
| 5 | Wikidata Q42 | Go to Q42, identify who it is | Find interesting fact (birth, nationality) | Click Wikipedia link, first sentence |
| 6 | arXiv CS.AI | Go to recent list, first paper | Click abstract page | First sentence + first author |
| 7 | Lobste.rs | Find first "programming" tagged story | Click comments link | First comment + story score |
| 8 | Wikipedia Random | Land on random article, name it | Click first blue link, name new article | Click one more link, connect 3 articles |
| 9 | Product Hunt | Name #1 product of the day | Click in, tagline + upvotes | Find maker name |
| 10 | Bundlephobia | Search for "react" | Click top result, sizes | Download time on slow 3G |
| 11 | Can I Use | Search "CSS Grid" | Global browser support % | Browser with most limited support |
| 12 | DevDocs Python | Find Python 3 docs | Navigate to string methods, str.split() | Signature and description |
| 13 | NPR Text | List top 3 headlines | Click first headline | Byline and first paragraph |
| 14 | Internet Archive | Search NASA moon landing, first result | Click in, media type | Upload date and uploader |
| 15 | Wiktionary | Go to "serendipity", etymology section | Origin language | Click first etymology word |
| 16 | BBC Sport | Top sports headline | Click into story | First paragraph |
| 17 | OpenStreetMap | Search "Colosseum Rome" | Click top result | Map view description + tags |
| 18 | NASA APOD | Describe today's picture | Image title | Photographer + first explanation sentence |
| 19 | Wayback Machine | Amazon.com circa 2000 | Product categories listed | Click one category, describe deeper |
| 20 | DuckDuckGo | Search "history of the internet" | Click first organic result | Site name + first paragraph |

## Algorithm

```
1. Generate session key with timestamp
2. Connect WebSocket, authenticate
3. Send Telegram header: "DEEP CONVERSATIONAL EXPLORATION\n20 sites, 3 turns each"
4. site_num = 0
5. For each mission (20 total):
   a. site_num += 1
   b. Send Telegram: "--- Site N/20: <name> ---"
   c. For each step (3 per site):
      i.   tag = "[site_num.step_num]"
      ii.  Print tag + label + message
      iii. Send Telegram: "person tag message"
      iv.  Record start time
      v.   Send message via WebSocket (180s timeout)
      vi.  Record elapsed time
      vii. Print tag + elapsed + response preview (100 chars)
      viii.Truncate response to 2000 chars for Telegram
      ix.  Send Telegram: "robot tag (Ns)\nresponse"
      x.   Record step result: {step, elapsed, ok, preview}
      xi.  Sleep 3 seconds
   d. Record site result: {site, steps}
   e. Sleep 5 seconds
6. Generate final report
7. Send report to Telegram + stdout
```

### Step Success Criteria

A step is considered successful (`ok: True`) when ALL of:
- Response length > 30 characters
- Response does NOT contain "timeout"
- Response first 20 characters do NOT contain "error"

### Final Report Scoring

Per-site scoring:
| Result | Criteria |
|--------|----------|
| `PASS` | All 3 steps OK |
| `PARTIAL` | At least 1 step OK |
| `FAIL` | No steps OK |

Report format:
```
DEEP EXPLORATION REPORT
-----------------------------------

[PASS] GitHub Trending (3/3 steps)
  ok explore (12s): The #1 trending repo today is...
  ok navigate (8s): This repository is a...
  ok extract (5s): It has 2,345 stars and is written in...

[PARTIAL] Wolfram Alpha (2/3 steps)
  ok explore (10s): The population of Tokyo is...
  FAIL navigate (180s): [timeout after 180s]
  ok extract (6s): The distance shown is...

3/20 sites fully completed
```

## WebSocket Parameters

| Parameter | Value |
|-----------|-------|
| Ping interval | 60s (longer than other harnesses) |
| Ping timeout | 120s |
| Max frame size | 10 MB |
| Open timeout | 30s |
| Close timeout | 10s |
| Per-message timeout | 180s |

The longer ping interval and timeout accommodate browser navigation, which can take 30-60+ seconds per step.

## Output Format

### Telegram Tagging
- Site header: `--- Site N/20: <name> ---`
- User message: `[N.S] <message>`
- Agent response: `[N.S] (Xs)\n<response>`
- Report: Multi-line text with `[PASS]`/`[PARTIAL]`/`[FAIL]` per site

## Error Handling

| Error | Handling |
|-------|----------|
| WebSocket timeout (180s) | Return `[timeout after 180s]` |
| Connection failure | Print "Connect failed", exit |
| Error response | Return `[error: <msg>]` |
| Empty response | Return `[empty]` |
| Telegram failure | Print error, continue |

## Dependencies

- `websockets` Python package
- Python 3.7+ stdlib
- ~331 lines of Python

## Integration Points

- **Agent WebSocket API**: Port 18789 with browser/browse tool support
- **Telegram Bot API**: Progress relay and final report
- **Agent browser tool**: The agent must have access to a browser tool to navigate the test sites

# browse-batch -- Simple Batch Browse Test

## Purpose

A lightweight browser capability test that sends simple single-message browse commands to 20 websites across 4 batches of 5. Each message asks the agent to navigate to a URL and describe what it sees. Simpler than `deep-explore` -- no multi-step missions, just "go here, tell me what you see." Classifies each response into one of four statuses: BROWSED (used browser tool), ANSWERED (responded from knowledge), BLOCKED (site blocked access), BROWSER_ERR (browser not available), or FAILED.

## Usage

```bash
python3 browse_batch.py <batch>    # batch 1-4 (5 sites each)
python3 browse_batch.py 1          # Sites 1-5
python3 browse_batch.py 4          # Sites 16-20
```

## Architecture

```
browse_batch.py (batch N)
     |
     |  For each of 5 sites:
     |    "Go to <URL> and tell me <what>"
     |
     +---------------> Agent (WebSocket)
     |                   +---> Browser (maybe)
     |                   +---> Knowledge (fallback)
     |  <--------------- response
     |
     +---------------> Telegram
     |
     +-- Batch summary with status classification
```

## Configuration

| Constant | Value |
|----------|-------|
| `BOT_TOKEN` | Telegram bot token |
| `CHAT_ID` | Telegram chat ID |
| `WS_URL` | `ws://localhost:18789/` |
| `OC_TOKEN` | Agent auth token |
| Per-site timeout | 300 seconds |
| Delay between sites | 3 seconds |

Session key: `agent:main:browse-b<batch>-<unix-timestamp>`

## Site List (20 sites, 4 batches of 5)

### Batch 1 (sites 1-5)
| # | Prompt |
|---|--------|
| 1 | Go to https://www.reuters.com and tell me the top headline |
| 2 | Browse https://en.wikipedia.org/wiki/Mars and describe the page |
| 3 | Visit https://www.imdb.com/chart/top/ and list the top 3 movies |
| 4 | Navigate to https://www.weather.gov and tell me what you see |
| 5 | Open https://news.ycombinator.com/newest and list the first 3 stories |

### Batch 2 (sites 6-10)
| # | Prompt |
|---|--------|
| 6 | Go to https://www.craigslist.org and describe the homepage layout |
| 7 | Browse https://www.rust-lang.org and tell me what Rust is about |
| 8 | Visit https://archive.org and describe what the Internet Archive offers |
| 9 | Navigate to https://lite.cnn.com and list the top 3 headlines |
| 10 | Open https://lobste.rs and list the first 3 stories |

### Batch 3 (sites 11-15)
| # | Prompt |
|---|--------|
| 11 | Go to https://www.wolframalpha.com and describe the search page |
| 12 | Browse https://www.gutenberg.org and tell me what Project Gutenberg is |
| 13 | Visit https://xkcd.com and describe the current comic |
| 14 | Navigate to https://www.spacex.com and describe what you see |
| 15 | Open https://earthobservatory.nasa.gov and describe the featured image |

### Batch 4 (sites 16-20)
| # | Prompt |
|---|--------|
| 16 | Go to https://www.goodreads.com and describe the homepage |
| 17 | Browse https://www.nytimes.com and tell me the main headline |
| 18 | Visit https://gitlab.com/explore/projects/trending and list 3 trending projects |
| 19 | Navigate to https://www.bbc.co.uk/sport and tell me the top sports headline |
| 20 | Open https://duckduckgo.com/?q=what+is+the+speed+of+light and describe the search results |

## Status Classification Algorithm

After each response, classify how the agent handled the request:

```python
resp_lower = response.lower()

browser_err = any(x in resp_lower for x in [
    "don't have a connected browser",
    "chrome extension",
    "can't reach",
    "browser service",
])

blocked = any(x in resp_lower for x in [
    "blocked", "captcha", "cloudflare", "access denied",
    "pardner", "error page", "sorry",
])

used_browser = any(x in resp_lower for x in [
    "screenshot", "playwright", ".png", "the page shows",
])

has_content = len(response) > 80
```

**Classification priority (first match):**

| Priority | Status | Criteria |
|----------|--------|----------|
| 1 | `BROWSER_ERR` | Browser infrastructure not available |
| 2 | `BLOCKED` | Site blocked the browser (CF, captcha, etc.) |
| 3 | `BROWSED` | Browser was used (screenshots, Playwright references) |
| 4 | `ANSWERED` | Response >80 chars (answered from knowledge, no browser) |
| 5 | `FAILED` | Response <=80 chars or empty |

## Algorithm

```
1. Parse batch number from argv[1] (default: 1)
2. Select 5 sites: ALL_SITES[(batch-1)*5 : batch*5]
3. Generate session key
4. Connect WebSocket, authenticate
5. Send Telegram: "--- Batch N (sites X-Y) ---"
6. For each site:
   a. num = global index
   b. tag = "[num/20]"
   c. Print tag + prompt (60 chars)
   d. Send Telegram: "person tag prompt"
   e. Send via WebSocket (300s timeout)
   f. Print tag + response (100 chars)
   g. Truncate response to 3000 chars
   h. Send Telegram: "robot tag response"
   i. Classify response status
   j. Extract domain from URL
   k. Record: "domain -> STATUS"
   l. Print "  => STATUS"
   m. Sleep 3 seconds
7. Print + send batch summary
```

### Site Name Extraction

```python
site_name = msg.split("https://")[1].split()[0]  # e.g., "www.reuters.com"
```

## Output Format

### Terminal
```
[1/20] Go to https://www.reuters.com and tell me the top headline.
[1/20] The top headline on Reuters is "Fed Holds Rates Steady"...
  => ANSWERED
[2/20] Browse https://en.wikipedia.org/wiki/Mars and describe the...
[2/20] I navigated to the Wikipedia page for Mars. The page shows...
  => BROWSED
```

### Telegram
```
--- Batch 1 (sites 1-5) ---
person [1/20] Go to https://www.reuters.com and tell me the top headline.
robot [1/20] The top headline on Reuters is...
person [2/20] Browse https://en.wikipedia.org/wiki/Mars...
robot [2/20] I navigated to the Wikipedia page...
```

### Batch Summary
```
Batch 1 results:
www.reuters.com -> ANSWERED
en.wikipedia.org/wiki/Mars -> BROWSED
www.imdb.com/chart/top/ -> BROWSED
www.weather.gov -> BLOCKED
news.ycombinator.com/newest -> BROWSED
```

## WebSocket Parameters

| Parameter | Value |
|-----------|-------|
| Ping interval | 30s |
| Ping timeout | 60s |
| Max frame size | 10 MB |
| Per-site timeout | 300s |

## Error Handling

| Error | Handling |
|-------|----------|
| Auth failure | Print "CONNECT_FAIL", exit |
| Response timeout | Return `[timeout]`, classify as FAILED |
| Error response | Return `[error: <msg>]` |
| Empty response | Return `[empty]`, classify as FAILED |
| Telegram failure | Silently ignore |

## Dependencies

- `websockets` Python package
- Python 3.7+ stdlib
- ~199 lines of Python

## Integration Points

- **Agent WebSocket API**: Port 18789
- **Agent browser tool**: Optional -- tool determines BROWSED vs ANSWERED classification
- **Telegram Bot API**: Progress relay
- **Parallel execution**: 4 instances can run simultaneously

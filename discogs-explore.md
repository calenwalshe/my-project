# discogs-explore — Cloudflare Bypass Verification via Discogs Navigation

## Purpose

A specialized browser test harness that verifies the agent's Cloudflare bypass capability by navigating 5 different pages within Discogs.com — a site protected by Cloudflare's anti-bot challenge. Each page tests a different content type (homepage, search results, artist page, release page, label page) to ensure the bypass works consistently across the site. Uses fresh sessions per page to avoid context poisoning.

## Usage

```bash
python3 discogs_explore.py
# No arguments. Runs all 5 page missions sequentially.
```

## Architecture

```
discogs_explore.py
     │
     │  For each of 5 Discogs pages:
     │    Fresh session key per page
     │    "/browse <URL>" mission prompt
     │
     ├───────────────> Agent (WebSocket)
     │                   │
     │                   ├──> Browser tool
     │                   │      ├──> Cloudflare bypass cascade
     │                   │      └──> Discogs page
     │                   │
     │  <─────────────── response
     │
     ├───────────────> Telegram (relay + scores)
     │
     └── Final summary with depth scores + emoji indicators
```

## Configuration

| Constant | Value |
|----------|-------|
| `BOT_TOKEN` | Telegram bot token |
| `CHAT_ID` | Telegram chat ID |
| `WS_URL` | `ws://localhost:18789/` |
| `OC_TOKEN` | Agent auth token |
| Per-page timeout | 600 seconds (10 minutes) |
| Delay between pages | 30 seconds (longer than other harnesses) |

The 30-second delay between pages prevents rate-limiting by Cloudflare.

### Session Keys

Unlike other harnesses that use a single session, this tool creates a **fresh session per page** to avoid context from previous pages influencing the next:

```
agent:main:discogs-<page_num>-<unix-timestamp>-<8-char-uuid>
```

A main session key is also generated for the WebSocket connection itself:
```
agent:main:discogs-explore-<unix-timestamp>-<8-char-uuid>
```

## Page Missions (5 pages)

Each mission explicitly instructs the agent to use `/browse` (the browser tool command):

### Page 1: Discogs Homepage
**URL:** `https://www.discogs.com`
**Tasks:**
1. Describe the overall layout
2. Identify main navigation sections
3. Note featured/trending items
4. Report page title and notable content

### Page 2: Discogs Search (Most Collected Releases)
**URL:** `https://www.discogs.com/search/?type=release&sort=have%2Cdesc`
**Tasks:**
1. Describe what the page shows
2. Name the top 3 releases
3. Report artist name + release title for each
4. Note visible filters/sorting options

### Page 3: Artist Page — Radiohead
**URL:** `https://www.discogs.com/artist/3840-Radiohead`
**Tasks:**
1. Describe artist page layout
2. List first 3 releases in discography
3. Find bio/profile information
4. Report total release count if visible

### Page 4: Release — Dark Side of the Moon
**URL:** `https://www.discogs.com/master/10362-Pink-Floyd-The-Dark-Side-Of-The-Moon`
**Tasks:**
1. Report title, artist, year
2. List tracklist (or first 5 tracks)
3. Find average rating and rating count
4. Note marketplace info (price, for sale count)

### Page 5: Label — Blue Note Records
**URL:** `https://www.discogs.com/label/281-Blue-Note`
**Tasks:**
1. Describe label page
2. Find label profile/description
3. List first 3 releases under label
4. Report metadata (parent label, country, etc.)

## Depth Scoring Algorithm

```python
resp_lower = response.lower()

navigated = any(x in resp_lower for x in [
    "discogs", "page shows", "i see", "found", "layout", "navigation",
    "listed", "tracklist", "releases", "artist",
])

extracted = any(x in resp_lower for x in [
    "1.", "2.", "3.", "4.", "title", "track", "release", "rating",
])

failed = (
    "[timeout]" in response or
    "[empty]" in response or
    len(response) < 50
)

blocked = any(x in resp_lower for x in [
    "blocked", "captcha", "access denied", "just a moment",
    "can't access", "couldn't access", "still blocking",
]) and NOT any(x in resp_lower for x in [
    "let me through", "bypassed", "loaded", "bypass succeeded",
])
```

**Classification priority (order matters):**

| Priority | Depth | Criteria |
|----------|-------|----------|
| 1 | `BLOCKED` | Blocked keywords AND no bypass-success keywords |
| 2 | `FAILED` | Timeout, empty, or response < 50 chars |
| 3 | `DEEP` | Navigated AND extracted AND NOT failed |
| 4 | `SHALLOW` | Navigated only |
| 5 | `FAILED` | Default (nothing matched) |

Note the blocked-keyword exception: if the response mentions being blocked but also indicates success ("bypassed", "loaded"), it's NOT classified as BLOCKED. This handles responses like "Initially blocked by Cloudflare but the bypass succeeded."

## Algorithm

```
1. Generate main session key
2. Connect WebSocket, authenticate
3. Send Telegram: "--- DISCOGS DEEP EXPLORE (5 pages, UC bypass test) ---"
4. For each of 5 missions:
   a. tag = "[N/5]"
   b. Generate fresh session key for this page
   c. Print + Telegram: "🎵 tag <page_name>\n<mission_prompt>"
   d. Record start time
   e. Send mission via WebSocket using page-specific session (600s timeout)
   f. Record elapsed time
   g. Print tag + elapsed + response preview (200 chars)
   h. Truncate response to 3000 chars
   i. Telegram: "🤖 tag <page_name> (Ns)\n<response>"
   j. Score depth (DEEP/SHALLOW/BLOCKED/FAILED)
   k. Record result
   l. Sleep 30 seconds
5. Generate summary with emoji indicators
6. Print + send summary to Telegram
```

## Output Format

### Telegram — Per Page
```
🎵 [1/5] Discogs Homepage
Use /browse to navigate to https://www.discogs.com...

🤖 [1/5] Discogs Homepage (45s)
I navigated to Discogs.com. The homepage shows...
```

### Summary Report
```
DISCOGS EXPLORE RESULTS:
✅ Discogs Homepage (45s) — DEEP
✅ Discogs Explore (38s) — DEEP
⚠️ Discogs Artist — Radiohead (52s) — SHALLOW
❌ Discogs Release — Dark Side of the Moon (600s) — BLOCKED
❓ Discogs Label — Blue Note Records (5s) — FAILED

Score: 2 deep, 1 shallow, 1 blocked, 1 failed
```

### Emoji Legend
| Depth | Emoji |
|-------|-------|
| DEEP | ✅ |
| SHALLOW | ⚠️ |
| BLOCKED | ❌ |
| FAILED | ❓ |

## WebSocket Parameters

| Parameter | Value |
|-----------|-------|
| Ping interval | 60s |
| Ping timeout | 120s |
| Max frame size | 10 MB |
| Open timeout | 30s |
| Close timeout | 10s |
| Per-page timeout | 600s |

## Error Handling

| Error | Handling |
|-------|----------|
| WebSocket timeout (600s) | Return `[timeout]`, score as FAILED |
| Connection failure | Print "Connect failed", exit |
| Telegram failure | Print error, continue |

## Dependencies

- `websockets` Python package
- Python 3.7+ stdlib
- ~235 lines of Python

## Integration Points

- **Agent WebSocket API**: Port 18789
- **Agent browser tool** with Cloudflare bypass cascade (UC mode)
- **Telegram Bot API**: Progress relay + summary report
- **Discogs.com**: Target site behind Cloudflare protection

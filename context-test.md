# context-test — 30-Message Context Retention Test

## Purpose

Tests an agent's ability to retain, recall, correct, and cross-reference information across a long conversation. Sends 30 messages organized into 6 phases of increasing difficulty — from planting simple facts to demanding full recall of corrected information and creative cross-referencing. Includes automated scoring with 22 keyword-based checkpoints evaluated against specific turn responses.

## Usage

```bash
python3 context_test.py
# No arguments. Runs all 30 messages and produces a scored report.
```

## Architecture

```
context_test.py
     │
     │  Phase 1-6: 30 sequential messages
     │  (each waits for response before next)
     │
     ├───────────────> Agent (WebSocket)
     │  <─────────────── response
     │
     ├───────────────> Telegram (relay per message)
     │
     └── Scoring engine (22 keyword checks against specific turns)
         └── Report to Telegram + stdout
```

## Configuration

| Constant | Value |
|----------|-------|
| `BOT_TOKEN` | Telegram bot token |
| `CHAT_ID` | Telegram chat ID |
| `WS_URL` | `ws://localhost:18789/` |
| `OC_TOKEN` | Agent auth token |
| Per-message timeout | 120 seconds |
| Delay between messages | 2 seconds |

Session key: `agent:main:context-test-<unix-timestamp>`

## Test Phases (30 messages)

### Phase 1: Fact Planting (turns 1-5)

Plant core facts about a fictional persona ("Marcus"):

| Turn | Message | Facts Planted |
|------|---------|---------------|
| 1 | "My name is Marcus and I live in Portland, Oregon." | Name: Marcus, City: Portland |
| 2 | "I have a cat named Ziggy who is 4 years old and orange." | Cat: Ziggy, Age: 4, Color: orange |
| 3 | "I work as a marine biologist studying octopus intelligence." | Job: marine biologist |
| 4 | "My favorite number is 37 and my lucky color is teal." | Number: 37, Color: teal |
| 5 | "I'm planning a trip to Japan in October to visit Kyoto." | Trip: Japan, Month: October |

### Phase 2: Building on Facts (turns 6-10)

Questions that require referencing planted facts:

| Turn | Message | Tests |
|------|---------|-------|
| 6 | "What do you know about me so far? List everything." | Complete recall |
| 7 | "Ziggy has been acting weird..." | Reference cat by name |
| 8 | "For my Japan trip, I want to visit an aquarium..." | Combine trip + job |
| 9 | "I just found out my lucky number 37 is a prime number..." | Reference number |
| 10 | "If I combined my favorite color with my cat's color, what color would I get?" | Cross-reference teal + orange |

### Phase 3: Adding Complexity (turns 11-15)

Corrections, new facts, and synthesis:

| Turn | Message | Tests |
|------|---------|-------|
| 11 | "Actually, Ziggy is 5 years old, not 4. I miscounted. How old did I originally say?" | Correction (4→5), recall original |
| 12 | "My colleague Sarah is joining me on the Japan trip. She studies jellyfish..." | New fact: Sarah, jellyfish |
| 13 | "I'm thinking of getting a second cat. Name it after a number..." | Creative + recall preferences |
| 14 | "Write a very short story incorporating my name, job, cat, and travel plans." | Multi-fact synthesis |
| 15 | "What's the connection between octopus intelligence and the number 37?" | Creative cross-reference |

### Phase 4: Deep Callbacks (turns 16-20)

Direct recall without reminders:

| Turn | Message | Expected Recall |
|------|---------|-----------------|
| 16 | "Without me telling you again, where do I live?" | Portland |
| 17 | "What color is my cat? And what was the color mixing question?" | Orange + teal+orange question |
| 18 | "How old is Ziggy now, after the correction I made?" | 5 (corrected) |
| 19 | "Who is coming on my trip and what does she study?" | Sarah, jellyfish |
| 20 | "What were the first 3 facts I told you about myself, in order?" | Name/city, cat, job |

### Phase 5: Cross-Reference Stress (turns 21-25)

Creative combinations of stored facts:

| Turn | Message | Tests |
|------|---------|-------|
| 21 | "If Sarah and I each wrote a research paper about an animal, what would the two topics be?" | Octopus + jellyfish |
| 22 | "Create an acronym from: my city, cat's name, colleague's name, destination." | P-Z-S-J or similar |
| 23 | "I want a personalized license plate with 7 characters referencing 3+ things about me." | Multi-fact creativity |
| 24 | "Rank everything you know about me by how early I mentioned it." | Temporal ordering |
| 25 | "If I moved from my current city to my trip destination permanently..." | Portland→Japan + marine biology |

### Phase 6: Ultimate Recall (turns 26-30)

Full reconstruction and specific memory tests:

| Turn | Message | Tests |
|------|---------|-------|
| 26 | "Give me a complete profile of everything you know about me..." | Complete recall |
| 27 | "What's one thing I told you that I later corrected?" | Ziggy's age 4→5 |
| 28 | "Write my dating profile using only facts from this conversation." | Creative synthesis |
| 29 | "What question did I ask you in turn 10?" | Specific turn recall (color mixing) |
| 30 | "Final test: tell me my name, city, pet, corrected age, job, number, color, destination, month, colleague's name and field." | All 11 facts |

## Scoring System

### Checkpoint Definitions

22 keyword-based checks evaluated against specific turn responses:

**Phase 4 Checks (5 checks):**
| Check | Turn Index | Keyword | Label |
|-------|-----------|---------|-------|
| 1 | 15 (T16) | `portland` | T16: Recalls city |
| 2 | 16 (T17) | `orange` | T17: Recalls cat color |
| 3 | 17 (T18) | `5` | T18: Recalls corrected age |
| 4 | 18 (T19) | `sarah` | T19: Recalls colleague |
| 5 | 18 (T19) | `jellyfish` | T19: Recalls colleague's field |

**Phase 6 Ultimate Checks (11 checks against turn 30):**
| Check | Keyword | Label |
|-------|---------|-------|
| 6 | `marcus` | T30: Name |
| 7 | `portland` | T30: City |
| 8 | `ziggy` | T30: Cat |
| 9 | `5` | T30: Corrected age |
| 10 | `marine biolog` | T30: Job |
| 11 | `37` | T30: Fav number |
| 12 | `teal` | T30: Lucky color |
| 13 | `japan` | T30: Trip dest |
| 14 | `october` | T30: Trip month |
| 15 | `sarah` | T30: Colleague |
| 16 | `jellyfish` | T30: Colleague field |

**Correction Checks (2 checks):**
| Check | Turn Index | Keyword | Label |
|-------|-----------|---------|-------|
| 17 | 10 (T11) | `4` | T11: Remembers original age |
| 18 | 26 (T27) | `4` | T27: Recalls the corrected fact |

*Note: Checks 19-22 are the remaining Phase 6 checks. Total = 18 explicitly defined checks. The code has some overlap, but the check function accumulates up to ~18 checks.*

### Scoring Algorithm

```python
def check(turn_idx, keyword, label):
    resp = results[turn_idx]["response"].lower()
    passed = keyword.lower() in resp
    scores.append((label, passed))
    return passed
```

All checks use case-insensitive substring matching.

### Report Format

```
SCORING REPORT
-----------------------------------
pass  T16: Recalls city
pass  T17: Recalls cat color
FAIL  T18: Recalls corrected age
pass  T19: Recalls colleague
pass  T19: Recalls colleague's field
pass  T30: Name
pass  T30: City
...
FAIL  T27: Recalls the corrected fact
-----------------------------------
16/18 checks passed
```

## Algorithm

```
1. Connect WebSocket, authenticate
2. Define 6 phases with turn ranges
3. Send Telegram: "CONTEXT RETENTION TEST\n30 messages across 6 phases"
4. current_phase = 0
5. For i = 1 to 30:
   a. Check if entering new phase → send phase header to Telegram
   b. tag = "[i/30]"
   c. Print + send to Telegram: "🧑 tag message"
   d. Send via WebSocket (120s timeout)
   e. Print + send to Telegram: "🤖 tag response"
   f. Record {turn, prompt, response}
   g. Sleep 2 seconds
6. Send "TEST COMPLETE — 30 turns"
7. Run scoring checks against recorded responses
8. Generate + send scoring report
```

## Output Format

### Telegram — During Test
```
CONTEXT RETENTION TEST
30 messages across 6 phases
Session: agent:main:context-test-1708784400
-----------------------------------

--- Phase 1: Fact Planting ---
🧑 [1/30] My name is Marcus and I live in Portland, Oregon.
🤖 [1/30] Nice to meet you, Marcus! Portland is a great city...
...

--- Phase 4: Deep Callbacks ---
🧑 [16/30] Without me telling you again, where do I live?
🤖 [16/30] You live in Portland, Oregon!
...
```

### Telegram — Final Report
```
-----------------------------------
TEST COMPLETE — 30 turns

SCORING REPORT
-----------------------------------
pass  T16: Recalls city
pass  T17: Recalls cat color
...
-----------------------------------
16/18 checks passed
```

## Error Handling

| Error | Handling |
|-------|----------|
| WebSocket timeout (120s) | Return `[timeout]`, check will likely FAIL |
| Auth failure | Print "Connect failed", exit |
| Telegram failure | Log error, continue |

## Dependencies

- `websockets` Python package
- Python 3.7+ stdlib
- ~268 lines of Python

## Integration Points

- **Agent WebSocket API**: Port 18789
- **Telegram Bot API**: Progress relay + final report
- **Agent memory**: Tests may interact with agent's persistent memory system

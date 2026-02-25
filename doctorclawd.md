# doctorclawd -- Comprehensive System Diagnostics Tool

## Purpose

A tiered diagnostic tool for infrastructure health assessment. Runs checks across Docker containers, HTTP health endpoints, internal network connectivity, system resources, log analysis, routing statistics, and end-to-end smoke tests. Produces colored terminal output with pass/warn/fail status per check, organized into named categories. Designed to run directly on the server being diagnosed.

## Usage

```bash
doctorclawd              # Quick check (default)
doctorclawd full         # Comprehensive system check
doctorclawd smoke        # End-to-end smoke tests (requires quick to pass)
doctorclawd all          # Full + smoke tests
doctorclawd -q           # Only show failures
doctorclawd --no-banner  # Skip ASCII banner
```

Also has a bash wrapper script that invokes the Python implementation:
```bash
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
exec /usr/bin/python3 "$SCRIPT_DIR/doctorclawd.py" "$@"
```

## Architecture

```
doctorclawd
     |
 +----------+
 | Command  |  quick | full | smoke | all
 | Parser   |
 +----+-----+
      |
 +------------------------------------------+
 |         Check Runner                      |
 |                                           |
 |  quick:  Docker -> Core Svcs -> Health    |
 |  full:   quick + Optional -> Net -> Res -> Logs |
 |  smoke:  quick + Smoke Tests              |
 |  all:    full + Smoke Tests (if no fails) |
 +----+-------------------------------------+
      |
 +------------------+
 | Result Renderer   |  colored terminal output
 | (categories +     |  with summary counts
 |  check results)   |
 +------------------+
```

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `command` (positional) | `quick` | One of: `quick`, `full`, `smoke`, `all` |
| `-q`, `--quiet` | false | Only show failures |
| `--no-banner` | false | Skip decorative header |

## Data Structures

### `Status` Enum
```python
class Status(Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"
```

### `CheckResult` Dataclass
```python
@dataclass
class CheckResult:
    name: str              # Check identifier
    status: Status         # Result status
    message: str           # One-line summary
    details: str = None    # Optional multi-line details (max 5 lines shown)
    duration_ms: float = 0 # How long the check took
```

### `CheckCategory` Dataclass
```python
@dataclass
class CheckCategory:
    name: str                        # Category header
    checks: List[CheckResult] = []   # Results in this category
```

## Configuration

Hardcoded constants:

| Constant | Value | Description |
|----------|-------|-------------|
| `AGENT_STACK_DIR` | `~/agent-stack` | Project root directory |
| `GATEWAY_URL` | `http://localhost:9200` | Chat gateway base URL |
| `SMART_ROUTER_URL` | `http://localhost:9080` | Smart router base URL |
| `TRACE_DB_PATH` | `~/agent-stack/smart-router/data/traces.db` | SQLite trace database |

### Service Lists

**Core services** (required -- FAIL if missing):
`smart-router`, `chat-gateway`, `codex-bridge`, `gemini-bridge`, `litellm`, `postgres`

**Optional services** (SKIP if missing):
`openclaw`, `telegram-bridge`, `health-monitor`, `traefik`, `app-platform`

## Check Implementations

### Docker Check

| Check | Method | OK | FAIL |
|-------|--------|-----|------|
| Docker Daemon | `docker info --format '{{.ServerVersion}}'` | Version string | Not running |

### Container Status Check

For each service name:
1. `docker ps --filter name=^<name>$ --format '{{.Status}}'`
2. Parse status string:
   - Contains "unhealthy" -> WARN
   - Contains "up" -> OK (append "(healthy)" if present)
   - No output or not "up" -> FAIL (required) or SKIP (optional)

### Health Endpoint Checks

**Gateway Health** (`http://localhost:9200/health`):
- OK: Parse JSON, extract `sessions` count -> "Healthy, N sessions"
- WARN: Non-JSON response
- FAIL: HTTP error

**Router Health** (`http://localhost:9080/health`):
- OK: Parse JSON, extract `routellm_enabled` and model count -> "Healthy, RouteLLM enabled/disabled, N models"
- WARN: Non-JSON response
- FAIL: HTTP error

### Internal Network Connectivity

Tests reachability from inside the Docker network by executing curl from within the `smart-router` container:

```bash
docker exec smart-router curl -sf --max-time 5 http://<service>:<port>/health
```

Tested services:
| Service | Port | Path |
|---------|------|------|
| codex-bridge | 9090 | /health |
| gemini-bridge | 9091 | /health |
| litellm | 4000 | / |

### System Resource Checks

**Disk Space:**
1. Parse `df / | tail -1`
2. Extract usage percentage and available space
3. >90% -> FAIL, >80% -> WARN, else OK

**Memory:**
1. Read `/proc/meminfo`
2. Extract `MemTotal` and `MemAvailable`
3. Report used/total/free in GB

**System Load:**
1. Read `/proc/loadavg`
2. Extract 1-minute, 5-minute, 15-minute loads
3. Load1 > 4 -> WARN, else OK

### Log Analysis

**Recent Errors:**
1. `docker logs smart-router --since 5m 2>&1 | grep -ci error`
2. 0 errors -> OK, <5 -> WARN, >=5 -> FAIL

**Routing Stats:**
1. Query SQLite trace database:
```sql
SELECT routing_reason, COUNT(*)
FROM traces
WHERE created_at > datetime('now', '-1 hour')
GROUP BY routing_reason
```
2. Report total requests and top 3 routing reasons
3. SKIP if trace DB not found

### Smoke Tests

Smoke tests send real requests through the full stack and verify responses.

**Simple Query:**
- POST to `<GATEWAY_URL>/v1/chat/send`
- Body: `{"user_id": "doctor", "message": "What is 2+2? Reply with just the number."}`
- Timeout: 30s
- OK: Parse response JSON, report model used
- FAIL: Request failed

**Code Routing:**
- POST same endpoint with coding prompt: `"Write a Python function to calculate factorial recursively"`
- Timeout: 60s
- OK: Response model contains "codex" or "gpt-5"
- WARN: Routed to unexpected model
- FAIL: Request failed

**@gemini Override:**
- POST with message: `"@gemini Say hello"`
- Timeout: 30s
- OK: Response model contains "gemini"
- FAIL: Wrong model or request failed

## Command Modes

### `quick` -- Fast connectivity check
Categories: Docker -> Core Services -> Health Endpoints
Stops immediately if Docker daemon is not running.

### `full` -- Comprehensive check
Categories: Docker -> Core Services -> Health Endpoints -> Optional Services -> Internal Network -> System Resources -> Logs & Metrics
Stops immediately if Docker daemon is not running.

### `smoke` -- End-to-end tests
Runs `quick` first. If any FAIL results, skips smoke tests with warning message.
Categories: (quick categories) -> Smoke Tests

### `all` -- Everything
Runs `full` first. If no FAIL results, adds smoke tests.
Categories: (full categories) -> Smoke Tests (conditional)

## Output Format

### Banner
```
+===========================================================+
|  DoctorClawd - Agent Stack Diagnostics                    |
+===========================================================+
```

### Check Output
```
Running quick check at 2026-02-24 12:34:56

> Docker
  [ok]   Docker Daemon: Version 24.0.7

> Core Services
  [ok]   Container: smart-router: Running (healthy)
  [ok]   Container: chat-gateway: Running
  [FAIL] Container: codex-bridge: Not running

> Health Endpoints
  [ok]   Gateway Health: Healthy, 3 sessions
  [WARN] Router Health: Response not JSON

--------------------------------------------------
Summary: 4 passed, 1 warnings, 1 failed (2.3s)

System has issues that need attention!
```

### Status Icons
| Status | Icon | Color |
|--------|------|-------|
| OK | checkmark | Green |
| WARN | warning triangle | Yellow |
| FAIL | x-mark | Red |
| SKIP | circle | Dim |

### Exit Codes
| Condition | Exit Code |
|-----------|-----------|
| All OK (with or without warnings) | 0 |
| Any FAIL | 1 |

## Utility Functions

### `run_cmd(cmd, timeout=30) -> (returncode, stdout, stderr)`
Runs a shell command via `subprocess.run(shell=True)`. Returns (-1, "", error_msg) on timeout or exception.

### `http_get(url, timeout=10) -> (success, body)`
Uses `curl -sf --max-time <timeout>` via `run_cmd`. Returns `(True, response_body)` or `(False, error_message)`.

### `http_post(url, data, timeout=30) -> (success, body)`
Uses `curl -sf -X POST -H 'Content-Type: application/json' -d '<json>'` via `run_cmd`. JSON data is shell-escaped.

## Error Handling

| Error | Handling |
|-------|----------|
| Docker not running | Return immediately with FAIL for Docker Daemon |
| Container not found | FAIL (core) or SKIP (optional) |
| HTTP endpoint unreachable | FAIL with error message |
| JSON parse failure | WARN with raw response |
| SQLite DB not found | SKIP |
| /proc/meminfo not readable | WARN |
| Command timeout | Appropriate status + "timed out" message |

## Dependencies

- Python 3 standard library (`os`, `sys`, `json`, `time`, `argparse`, `subprocess`, `socket`, `sqlite3`, `datetime`, `dataclasses`, `enum`, `pathlib`, `typing`)
- External commands: `docker`, `curl`, `df`
- No external Python packages
- ~624 lines of Python + 6-line bash wrapper

## Integration Points

- **Docker daemon**: Direct CLI access required
- **Chat Gateway**: HTTP endpoint at configurable URL
- **Smart Router**: HTTP endpoint at configurable URL
- **SQLite trace DB**: Read access to routing trace database
- **Linux /proc**: Read access for memory and load information
- **Docker network**: Executes commands inside containers for network tests

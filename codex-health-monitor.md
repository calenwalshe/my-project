# codex-health-monitor -- Long-Running Health Monitor Daemon

## Purpose

A persistent watchdog daemon that continuously monitors a specific HTTP service (originally codex-bridge), tracking health over time with metrics collection, automatic restart on sustained failures, and cooldown-protected restart logic. Unlike the simple watchdog script, this runs as a long-lived process with state tracking, metrics export, and intelligent restart behavior.

## Usage

```bash
python3 codex-health-monitor.py
# Runs in foreground, Ctrl+C to stop
# Typically run via systemd, supervisor, or nohup
```

No CLI arguments. All configuration is hardcoded constants.

## Architecture

```
+---------------------------------------------------------+
|                Health Monitor Daemon                     |
|                                                         |
|  +--------------+    +----------------+    +----------+ |
|  | Health       |--->| Failure        |--->| Restart  | |
|  | Checker      |    | Counter        |    | Manager  | |
|  | (30s loop)   |    | (consecutive)  |    | (cooldown| |
|  +--------------+    +----------------+    +----------+ |
|        |                                        |       |
|        v                                        v       |
|  +----------+                            +----------+   |
|  | Metrics  |                            | Docker   |   |
|  | Writer   |                            | Compose  |   |
|  | (JSON)   |                            | / Docker |   |
|  +----------+                            +----------+   |
+---------------------------------------------------------+
```

## Configuration

All values are module-level constants:

| Constant | Value | Description |
|----------|-------|-------------|
| `HEALTH_URL` | `http://localhost:<port>/health` | Health endpoint URL |
| `METRICS_URL` | `http://localhost:<port>/metrics` | Detailed metrics endpoint |
| `CHECK_INTERVAL` | `30` | Seconds between health checks |
| `MAX_FAILURES` | `3` | Consecutive failures before restart |
| `RESTART_COOLDOWN` | `300` | Seconds between restart attempts (5 min) |
| `CONTAINER_NAME` | `<service-name>` | Docker container to monitor |
| `COMPOSE_DIR` | `<project-dir>` | Docker Compose project directory |
| `METRICS_FILE` | `<project-dir>/metrics/<service>-monitor.json` | Metrics output path |
| `LOG_FILE` | `<project-dir>/logs/<service>-monitor.log` | Log file path |

## Data Structures

### `HealthMonitor` Class

```python
class HealthMonitor:
    consecutive_failures: int = 0       # Reset on success
    total_checks: int = 0              # Monotonically increasing
    total_failures: int = 0            # Monotonically increasing
    total_restarts: int = 0            # Monotonically increasing
    last_restart: float = 0            # Timestamp of last restart
    response_times: list[float] = []   # Rolling window (last 1000)
    start_time: float                  # Monitor start timestamp
```

## Algorithm

### Main Loop (`run()`)

```
log("Starting health monitor")
while True:
    try:
        run_once()
        save_metrics()
    except KeyboardInterrupt:
        log("Shutting down")
        break
    except Exception as e:
        log(error, e)
    sleep(CHECK_INTERVAL)
```

### Single Check Cycle (`run_once() -> bool`)

```
total_checks += 1
success, response_ms, health_data = check_health()

if success:
    consecutive_failures = 0
    append response_ms to response_times (keep last 1000)
    log(debug, "passed in Nms")
    return True
else:
    consecutive_failures += 1
    total_failures += 1
    log(warning, "failed (N/MAX_FAILURES)")
    if consecutive_failures >= MAX_FAILURES:
        restart_container()
    return False
```

### Health Check (`check_health() -> (success, response_ms, health_data)`)

Uses `curl` via subprocess (not Python HTTP library):

```bash
curl -s -m 10 -w "%{http_code}" <HEALTH_URL>
```

1. Parse output: last 3 characters = HTTP status code, remainder = response body
2. If status code == "200":
   - Try to parse body as JSON -> return `(True, elapsed_ms, data)`
   - If JSON parse fails -> return `(True, elapsed_ms, None)`
3. If status code != "200" -> return `(False, elapsed_ms, None)`
4. On subprocess timeout (15s) -> return `(False, 10000, None)`
5. On any exception -> log error, return `(False, None, None)`

### Restart Logic (`restart_container() -> bool`)

```
if (now - last_restart) < RESTART_COOLDOWN:
    log("cooldown active, Ns remaining")
    return False

log("Restarting after N failures")

# Strategy 1: docker compose restart
result = subprocess.run(["docker", "compose", "restart", CONTAINER_NAME], cwd=COMPOSE_DIR, timeout=60)
if success:
    last_restart = now
    total_restarts += 1
    consecutive_failures = 0
    return True

# Strategy 2: docker restart (fallback)
result = subprocess.run(["docker", "restart", CONTAINER_NAME], timeout=60)
if success:
    last_restart = now
    total_restarts += 1
    consecutive_failures = 0
    return True

return False
```

### Metrics Export (`save_metrics()`)

Writes JSON file after every check cycle:

```json
{
  "monitor_uptime_seconds": 3600,
  "total_checks": 120,
  "total_failures": 5,
  "total_restarts": 1,
  "consecutive_failures": 0,
  "avg_response_time_ms": 45,
  "last_check": "2026-02-24T12:34:56.789012",
  "status": "healthy",
  "bridge": { "..." : "..." }
}
```

| Field | Computation |
|-------|-------------|
| `monitor_uptime_seconds` | `int(now - start_time)` |
| `avg_response_time_ms` | Average of last 100 response times |
| `status` | `"healthy"` if `consecutive_failures == 0`, else `"degraded"` |
| `bridge` | Full JSON from `METRICS_URL` if available, omitted otherwise |

### Logging (`log(level, message)`)

```
[2026-02-24 12:34:56] [INFO] Starting health monitor for codex-bridge
```

- Writes to both stdout and log file
- Log file is opened/closed per write (append mode)
- Silently ignores file write errors

## Output Format

### Console Output

Continuous timestamped log entries:

```
[2026-02-24 12:00:00] [INFO] Starting health monitor for codex-bridge
[2026-02-24 12:00:00] [INFO] Check interval: 30s, Max failures: 3
[2026-02-24 12:00:30] [DEBUG] Health check passed in 45ms
[2026-02-24 12:01:00] [DEBUG] Health check passed in 38ms
[2026-02-24 12:01:30] [WARNING] Health check failed (1/3)
[2026-02-24 12:02:00] [WARNING] Health check failed (2/3)
[2026-02-24 12:02:30] [WARNING] Health check failed (3/3)
[2026-02-24 12:02:30] [WARNING] Restarting codex-bridge after 3 failures
[2026-02-24 12:02:45] [INFO] Container codex-bridge restarted successfully
```

### Metrics File

JSON file updated every 30 seconds. Can be read by external monitoring systems, dashboards, or alerting tools.

## Error Handling

| Error | Handling |
|-------|----------|
| Health endpoint unreachable | Count as failure |
| Curl timeout (10s per check) | Count as failure, response_ms = 10000 |
| Subprocess timeout (15s) | Count as failure |
| Docker compose restart fails | Fallback to `docker restart` |
| Docker restart fails | Log error, do NOT reset failure counter |
| Metrics write fails | Log error, continue monitoring |
| Log write fails | Silently ignored |
| KeyboardInterrupt | Clean exit |
| Any other exception | Log, continue loop |

## Integration Points

- **Monitored service**: Any HTTP service with a `/health` endpoint returning HTTP 200
- **Optional metrics**: Service at `/metrics` endpoint returning JSON
- **Docker**: Both `docker compose` and `docker` CLI must be available
- **File system**: Needs write access to metrics and log directories (auto-created)

## Implementation Notes

- ~245 lines of Python
- No external dependencies (stdlib only: `json`, `os`, `subprocess`, `time`, `datetime`, `pathlib`)
- Directories for metrics and logs are created at import time via `Path.mkdir(parents=True, exist_ok=True)`
- Response time tracking uses a rolling window of 1000 samples
- The monitor runs in the foreground -- daemonization is left to the process supervisor

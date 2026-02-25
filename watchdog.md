# watchdog -- Lightweight Docker Container Watchdog

## Purpose

A minimal bash script that checks whether critical Docker containers are running and restarts any that have stopped. Also performs an HTTP health check on the LiteLLM service and restarts it if the health endpoint fails. Designed to be run periodically via cron.

## Usage

```bash
watchdog.sh           # Run all checks
# Typically invoked via crontab:
# */5 * * * * /path/to/watchdog.sh >> /var/log/watchdog.log 2>&1
```

No arguments. No flags. No configuration file.

## Architecture

```
watchdog.sh
     |
+-------------------------------------+
| For each service in SERVICES list:  |
|   docker ps -> is container listed? |
|   No -> docker start <service>      |
+-------------------------------------+
     |
+-------------------------------------+
| If litellm container is running:    |
|   curl health endpoint              |
|   Failed -> docker restart litellm  |
+-------------------------------------+
```

## Algorithm

### Phase 1: Container Presence Check

For each service in the monitored list:

1. Run `docker ps --format '{{.Names}}'` and grep for exact container name
2. If container is NOT in the running list:
   - Log timestamp and service name
   - Run `docker start <service>` (start a stopped container)
   - If start fails, log failure

**Monitored services:**
- `litellm` -- LLM proxy/gateway
- `openclaw` -- Agent platform
- `codex-bridge` -- Codex model bridge
- `caddy` -- Reverse proxy / TLS termination

### Phase 2: LiteLLM Health Check

Only runs if the litellm container is present in `docker ps`:

1. `curl -sf http://localhost:4000/health`
   - `-s`: silent mode
   - `-f`: fail on HTTP errors
   - Redirect stdout to `/dev/null`
2. If curl returns non-zero exit code:
   - Log "LiteLLM unhealthy, restarting..."
   - Run `docker restart litellm`

## Configuration

All configuration is hardcoded:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SERVICES` | `litellm openclaw codex-bridge caddy` | Space-separated container names |
| Health URL | `http://localhost:4000/health` | LiteLLM health endpoint |

## Output Format

All output goes to stdout (typically redirected to a log file):

```
Mon Feb 24 12:00:01 UTC 2026: codex-bridge is down, attempting restart...
Mon Feb 24 12:00:02 UTC 2026: Failed to start codex-bridge
Mon Feb 24 12:00:03 UTC 2026: LiteLLM unhealthy, restarting...
```

If all services are running and healthy, the script produces no output.

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Container stopped | `docker start` attempt, log on failure |
| Container does not exist | `docker start` will fail, error logged |
| LiteLLM health fails | `docker restart` (full stop + start cycle) |
| Docker daemon not running | All docker commands will fail with errors to stderr |
| curl not available | Health check will fail, script continues |

## Integration Points

- **Docker daemon**: Must be accessible to the user running the script
- **LiteLLM**: Expected on port 4000 with `/health` endpoint
- **Cron**: Typically scheduled every 5 minutes

## Implementation Notes

- ~26 lines of bash
- No external dependencies beyond `docker`, `curl`, `grep`, `date`
- Uses `docker start` (not `docker-compose up`) -- only restarts existing stopped containers, does not recreate
- The health check is specific to LiteLLM; other services are only checked for container presence
- Uses `2>/dev/null` on `docker start` to suppress Docker error messages
- No notification system -- relies on log file review or external log monitoring

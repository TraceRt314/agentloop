# AgentLoop Health Checks

## Quick Check

```bash
curl -s http://localhost:8080/healthz | python3 -m json.tool
```

## Deep Health Check

```bash
curl -s http://localhost:8080/api/v1/health | python3 -m json.tool
```

Returns status for:
- **database** — connection alive, agent count
- **mission_control** — MC API reachable
- **missions** — active count, stuck missions (failed steps with no pending)
- **agents** — active count, stale heartbeats (>10 min)
- **sse_streams** — active SSE board connections

Overall status: `healthy` | `warning` | `degraded`

## Periodic Monitoring (via ticker)

The ticker script (`scripts/ticker.sh`) calls the health endpoint every 10th tick (~2.5 min):

```
TICK % 10 == 0  →  GET /api/v1/health
```

If status != `healthy`, the response is logged to stderr.

## Manual Checks

### Services alive
```bash
curl -sf http://localhost:8080/healthz && echo "agentloop: ok"
curl -sf http://localhost:8002/healthz && echo "mc: ok"
```

### Stuck missions
```bash
curl -s http://localhost:8080/api/v1/health | python3 -c "
import sys, json
d = json.load(sys.stdin)
m = d['checks']['missions']
print(f'Active: {m[\"active\"]}, Stuck: {m[\"stuck\"]}')
if m['stuck'] > 0:
    print('WARNING: stuck missions detected — check /api/v1/missions?status=active')
"
```

### Agent heartbeats
```bash
curl -s http://localhost:8080/api/v1/health | python3 -c "
import sys, json
d = json.load(sys.stdin)
a = d['checks']['agents']
print(f'Active: {a[\"total_active\"]}')
if a['stale']:
    print(f'Stale agents: {a[\"stale\"]}')
"
```

### MC sync status
```bash
curl -s http://localhost:8080/api/v1/health | python3 -c "
import sys, json
d = json.load(sys.stdin)
mc = d['checks']['mission_control']
sse = d['checks']['sse_streams']
print(f'MC: {mc[\"status\"]}, SSE boards: {sse[\"active_boards\"]}')
"
```

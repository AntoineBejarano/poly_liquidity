# Monitoring and Observability

**Purpose**: Technical specification for metrics collection, logging, and observability infrastructure.

**Audience**: Engineers implementing monitoring, DevOps, operations team.

**Where this is used**: All modules, runtime supervisor, live control dashboard.

**Last updated**: 2025-01-XX

---

## Overview

The Metrics & Observability Layer provides infrastructure for:

1. **Monitoring** system state in real-time
2. **Recording historical metrics** of performance, risk, and execution
3. **Detecting anomalies** before they cause losses
4. **Feeding Runtime Supervisor** with latency and error data
5. **Feeding Live Control** with visual metrics
6. **Exposing observability data** for external dashboards (Grafana, Prometheus, etc.)

**Without metrics**, the bot would be a black box.  
**With metrics**, it's a professional operable platform.

---

## Metrics Categories

### 1. Internal System Metrics

- Main tick duration (ms)
- CPU, RAM (optional)
- Number of active watchers
- Number of active markets
- Loop latency (p50, p95, p99)
- Internal processing latency

### 2. Watch Engine Metrics

- Latency per event: time from checker query → state update
- Average call time per checker
- Errors per checker
- Detected delays in sports APIs
- Number of monitored events

### 3. Strategy Engine Metrics

- Number of intents created
- Number of intents approved
- Number of orders signed
- Number of orders sent
- Number of orders filled
- Conversion rate at each stage

### 4. Risk Engine Metrics

- Exposure per market
- Global exposure
- Number of active markets
- Number of rejected intents
- Rejection reasons

### 5. Execution Engine Metrics

- Signing latency (intent → signed)
- Sending latency (signed → sent)
- Acceptance latency (sent → accepted)
- End-to-end latency (intent → filled)
- Error rates by type

---

## Logging Configuration

### Default Levels

- **General level**: `INFO` (configurable from `settings.log_level`)
- **External libraries**: `WARNING` (only warnings and errors)

### Silenced Libraries

The following libraries are configured at `WARNING` level to reduce noise:

- `httpcore` - Low-level HTTP client
- `httpx` - Async HTTP client
- `urllib3` - HTTP client (used by requests)
- `asyncio` - Python event loop
- `uvicorn.access` - HTTP access logs
- `uvicorn` - ASGI server (INFO level)

### Configuration from Environment

Change logging level from `.env`:

```env
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Examples

**See only errors and warnings:**
```env
LOG_LEVEL=WARNING
```

**See everything (including application debug):**
```env
LOG_LEVEL=DEBUG
```

**Note**: Even with `DEBUG`, external libraries (`httpcore`, `httpx`, etc.) will remain at `WARNING` to keep logs readable.

---

## Structured Logging

All logs are structured JSON with:

- `timestamp`: ISO 8601 with timezone
- `level`: INFO, WARN, ERROR, DEBUG
- `trace_id`: UUID for correlation
- `component`: strategy, risk, execution, signer, order_monitor
- `event_type`: Type of event
- `message`: Human-readable message
- Context-specific fields (order_id, market_id, etc.)

### Example Log

```json
{
  "timestamp": "2025-01-25T20:15:30.123Z",
  "level": "INFO",
  "component": "execution",
  "event_type": "order_sent",
  "trace_id": "b3c1e7fc-2a5f-4b7a-9c90-1b...",
  "order_id": "order_xyz",
  "polymarket_order_id": "pm_order_123",
  "latency_ms": 183,
  "message": "Order sent to Polymarket trading API"
}
```

---

## Metrics Storage

### In-Memory Metrics

- Real-time metrics stored in memory
- Fast access for Runtime Supervisor
- Updated every tick

### Historical Metrics

- Stored in database (PostgreSQL)
- Time-series data
- Queryable for analysis

### External Export

- Prometheus metrics endpoint
- Grafana dashboards
- Custom alerting rules

---

## Anomaly Detection

### Latency Anomalies

- Detect when latency exceeds thresholds
- Alert if p95 > 500ms consistently
- Alert if p99 > 1000ms

### Error Rate Anomalies

- Detect spike in error rates
- Alert if error rate > 5% in 1 minute
- Alert if critical errors > 3 in 5 minutes

### Exposure Anomalies

- Detect unexpected exposure increases
- Alert if exposure grows > 20% in 1 hour
- Alert if exposure exceeds limits

---

## Integration Points

### Runtime Supervisor

- Receives real-time metrics
- Calculates Runtime Mode (GREEN/YELLOW/RED)
- Activates circuit breakers based on metrics

### Live Control

- Displays real-time metrics
- Visual dashboards
- Historical charts

### External Systems

- Prometheus scraping
- Grafana dashboards
- Alerting systems (Slack, PagerDuty)

---

## Related Documentation

- [`../risk/kill-switch.md`](../risk/kill-switch.md) - Circuit breakers
- [`../operations/runbook.md`](../operations/runbook.md) - Operations guide
- [`../infrastructure/secrets.md`](../infrastructure/secrets.md) - Configuration

---

## Open Questions

- What are the exact Prometheus metrics endpoints?
- How do we handle metrics retention?
- What is the procedure for alerting configuration?





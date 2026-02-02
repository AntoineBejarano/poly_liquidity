# Historical Data Replay

**Purpose**: Technical specification for historical event recording, querying, and replay system.

**Audience**: Engineers implementing audit and replay functionality, researchers running backtests.

**Where this is used**: Historical replay module, audit system, backtesting framework.

**Last updated**: 2025-01-XX

---

## Overview

The Historical Replay module enables:

1. **Recording complete history** of events, decisions, metrics, and fills
2. **Querying complete history** for audits or investigation
3. **Reconstructing system state** at a past moment
4. **Reproducing step-by-step** how the bot acted in a real event
5. **Comparing decisions taken** with decisions a new version would take
6. **Detecting logic failures**, latency, checker failures, or external errors

**Without this module**, a serious bot managing >100k EUR would be a dangerous black box.

**With it**, you have a professional financial system that is fully traceable.

---

## What is Recorded

The system generates **structured event logs** with precise timestamps.

**Everything critical is recorded:**

### Watch Engine Events

```json
{
  "type": "watcher_event_state",
  "event_id": "sports:nba:401585236",
  "state": "FINISHED_CONFIRMED",
  "confidence": 0.97,
  "sources": {
    "espn": "FINISHED",
    "flashscore": "FINISHED"
  },
  "timestamp": "2025-01-25T20:15:30.123Z",
  "trace_id": "b3c1e7fc-2a5f-4b7a-9c90-1b..."
}
```

### Strategy Intents

```json
{
  "type": "strategy_intent_created",
  "market_id": "pm555",
  "event_state": "FINISHED_CONFIRMED",
  "target_price": 0.979,
  "size": 5000,
  "reason": "event_finished_and_price_threshold_met",
  "timestamp": "2025-01-25T20:15:30.200Z",
  "trace_id": "b3c1e7fc-2a5f-4b7a-9c90-1b..."
}
```

### Risk Decisions

```json
{
  "type": "risk_intent_approved",
  "intent_id": "intent_xyz",
  "market_id": "pm555",
  "approved_size": 5000,
  "original_size": 5000,
  "adjustments": {},
  "timestamp": "2025-01-25T20:15:30.250Z",
  "trace_id": "b3c1e7fc-2a5f-4b7a-9c90-1b..."
}
```

### Execution Events

```json
{
  "type": "execution_order_sent",
  "order_id": "order_xyz",
  "polymarket_order_id": "pm_order_123",
  "market_id": "pm555",
  "price": 0.979,
  "size": 5000,
  "latency_ms": 183,
  "timestamp": "2025-01-25T20:15:30.300Z",
  "trace_id": "b3c1e7fc-2a5f-4b7a-9c90-1b..."
}
```

### Fill Events

```json
{
  "type": "execution_fill",
  "order_id": "order_xyz",
  "fill_id": "fill_001",
  "price": 0.979,
  "size": 2000,
  "remaining": 3000,
  "timestamp": "2025-01-25T20:16:00.123Z",
  "trace_id": "b3c1e7fc-2a5f-4b7a-9c90-1b..."
}
```

---

## Event Store

### Storage

**Primary Storage:**
- PostgreSQL database (structured queries)
- JSONL files (append-only, efficient writes)

**Structure:**
```sql
CREATE TABLE event_logs (
    id UUID PRIMARY KEY,
    type TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    trace_id UUID NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_event_logs_trace_id ON event_logs(trace_id);
CREATE INDEX idx_event_logs_timestamp ON event_logs(timestamp);
CREATE INDEX idx_event_logs_type ON event_logs(type);
```

### Query API

**By Trace ID:**
```python
GET /api/history/trace/{trace_id}
```

**By Time Range:**
```python
GET /api/history/range?start={start}&end={end}
```

**By Event Type:**
```python
GET /api/history/type/{event_type}?start={start}&end={end}
```

**By Market:**
```python
GET /api/history/market/{market_id}?start={start}&end={end}
```

---

## Replay Functionality

### State Reconstruction

**Reconstruct system state at a point in time:**
```python
POST /api/history/replay
{
  "timestamp": "2025-01-25T20:15:30.123Z",
  "market_id": "pm555"
}
```

**Returns:**
- Complete system state at that moment
- All events leading up to that moment
- Decisions made at that moment

### Step-by-Step Replay

**Replay events in sequence:**
```python
POST /api/history/replay/step
{
  "trace_id": "...",
  "from_timestamp": "...",
  "to_timestamp": "..."
}
```

**Returns:**
- Events in chronological order
- State changes at each step
- Decisions made at each step

### Strategy Comparison

**Compare decisions with new strategy version:**
```python
POST /api/history/compare
{
  "trace_id": "...",
  "strategy_version": "v2.0"
}
```

**Returns:**
- Original decisions
- New strategy decisions
- Differences and analysis

---

## Use Cases

### 1. Audit Trail

**Query all decisions for a specific order:**
```python
GET /api/history/trace/{trace_id}
```

**Returns complete chain:**
- Market scanned
- Event mapped
- Event finished detected
- Intent created
- Risk approved
- Order sent
- Fill received

### 2. Debugging

**Reconstruct what happened when something went wrong:**
```python
GET /api/history/range?start={incident_start}&end={incident_end}
```

**Analyze:**
- What events occurred
- What decisions were made
- What the system state was
- Why decisions were made

### 3. Backtesting

**Replay historical events with new strategy:**
```python
POST /api/history/replay/strategy
{
  "start": "...",
  "end": "...",
  "strategy_config": {...}
}
```

**Returns:**
- What new strategy would have done
- Performance comparison
- Decision differences

---

## Performance Considerations

### Efficient Storage

- Use JSONB for flexible querying
- Index on trace_id, timestamp, type
- Partition by time for large datasets
- Archive old events to cold storage

### Query Optimization

- Limit result sets
- Use time ranges
- Filter by type early
- Use indexes effectively

---

## Related Documentation

- [`framework.md`](framework.md) - Backtesting framework
- [`../operations/troubleshooting.md`](../operations/troubleshooting.md) - Debugging guide
- [`../architecture/data-flow.md`](../architecture/data-flow.md) - Event flow

---

## Open Questions

- What is the retention policy for event logs?
- How do we handle very large event logs?
- What is the procedure for archiving old events?





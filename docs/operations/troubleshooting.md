# Troubleshooting Guide

**Purpose**: Guide for debugging system issues, tracing decisions, and resolving common problems.

**Audience**: Engineers debugging issues, operations team, on-call engineers.

**Where this is used**: Debugging sessions, incident response, system maintenance.

**Last updated**: 2025-01-XX

---

## Decision Tracing

### Purpose

Track every bot decision completely for explainability, keeping the table efficient and not overloaded.

### Decision Trace Structure

**Main Fields:**
- `decision_stage`: Pipeline stage (`SCAN`, `EVENT_CONFIRMATION`, `STRATEGY`, `RISK`, `EXECUTION`)
- `input_data`: **BOUNDED** input data (see rules below)
- `output_data`: Output data
- `config_used`: Configuration used
- `reason`: Decision reason
- `trace_id`: UUID for correlating all decisions in a chain

### Critical Rule: Bounded input_data

**Objective:** Keep `input_data` < 2KB per record to maintain table efficiency.

#### ❌ DO NOT Include

1. **Complete orderbooks**
   - Do NOT include all orders in orderbook
   - Do NOT include complete price history
   - Do NOT include extensive historical data

2. **Redundant data**
   - Do NOT include information already in other tables (markets, events, etc.)
   - Do NOT include data that can be reconstructed from other sources

3. **Binary or very large data**
   - Do NOT include images, files, etc.

#### ✅ DO Include

1. **Summaries and key metrics:**
   ```json
   {
     "market_id": "uuid",
     "best_ask": 0.98,
     "best_bid": 0.97,
     "spread": 0.01,
     "midpoint": 0.975,
     "liquidity_at_price": 5000.0
   }
   ```

2. **Summarized states:**
   ```json
   {
     "event_state": "FINISHED_CONFIRMED",
     "confidence": 0.95,
     "checkers_used": 2,
     "quorum_used": 2,
     "quorum_required": 2
   }
   ```

3. **Hashes of large data:**
   ```json
   {
     "orderbook_hash": "sha256_hash_of_orderbook",
     "market_snapshot_hash": "sha256_hash_of_market_state"
   }
   ```

4. **Key metrics:**
   ```json
   {
     "exposure_current": 5000.0,
     "exposure_limit": 10000.0,
     "latency_status": "GREEN",
     "runtime_mode": "GREEN"
   }
   ```

### Decision Stages Detail

#### SCAN Stage

**When:** Scanner evaluates a market

**Typical input_data:**
```json
{
  "market_id": "uuid",
  "polymarket_id": "string",
  "category": "sports",
  "last_price": 0.98,
  "volume_24h": 100000.0,
  "liquidity": 50000.0,
  "status": "OPEN"
}
```

**Typical output_data:**
```json
{
  "decision": "CANDIDATE" | "REJECTED",
  "reason": "meets_criteria" | "price_too_low" | "insufficient_liquidity"
}
```

#### EVENT_CONFIRMATION Stage

**When:** EventEngine/StateAggregator determines event state

**Typical input_data:**
```json
{
  "event_id": "uuid",
  "checkers_available": 3,
  "checkers_healthy": 2,
  "quorum_base": 2,
  "quorum_effective": 2,
  "checker_results": [
    {
      "checker_name": "espn",
      "state": "FINISHED",
      "confidence": 0.95
    },
    {
      "checker_name": "flashscore",
      "state": "FINISHED",
      "confidence": 0.92
    }
  ]
}
```

**Typical output_data:**
```json
{
  "event_state": "FINISHED_CONFIRMED",
  "confidence": 0.935,
  "quorum_used": 2,
  "checkers_used": ["espn", "flashscore"],
  "trading_permitted": true
}
```

#### STRATEGY Stage

**When:** Strategy Engine decides to create an OrderIntent

**Typical input_data:**
```json
{
  "market_id": "uuid",
  "best_ask": 0.98,
  "best_bid": 0.97,
  "spread": 0.01,
  "event_state": "FINISHED_CONFIRMED",
  "event_confidence": 0.95,
  "current_exposure": 5000.0,
  "exposure_limit": 10000.0,
  "latency_status": "GREEN"
}
```

**Typical output_data:**
```json
{
  "order_intent": {
    "market_id": "uuid",
    "side": "BUY",
    "price": 0.979,
    "size": 5000.0,
    "reason": "conditions_met"
  }
}
```

#### RISK Stage

**When:** Risk Engine validates an OrderIntent

**Typical input_data:**
```json
{
  "order_intent": {
    "market_id": "uuid",
    "price": 0.979,
    "size": 5000.0
  },
  "current_market_exposure": 5000.0,
  "max_market_exposure": 10000.0,
  "current_global_exposure": 50000.0,
  "max_global_exposure": 200000.0,
  "active_markets": 5,
  "max_active_markets": 10
}
```

**Typical output_data:**
```json
{
  "decision": "APPROVED" | "REJECTED" | "ADJUSTED",
  "approved_intent": {
    "price": 0.979,
    "size": 5000.0,
    "original_size": 5000.0,
    "adjustments": {}
  },
  "reason": "all_limits_respected" | "exceeds_market_exposure" | "size_adjusted"
}
```

#### EXECUTION Stage

**When:** Execution Engine sends an order

**Typical input_data:**
```json
{
  "approved_intent": {
    "market_id": "uuid",
    "price": 0.979,
    "size": 5000.0
  },
  "execution_mode": "LIVE" | "PAPER" | "DRY_RUN",
  "wallet_address": "0x...",
  "nonce": 123
}
```

**Typical output_data:**
```json
{
  "order_id": "uuid",
  "polymarket_order_id": "0x...",
  "status": "PENDING" | "FILLED" | "CANCELLED",
  "execution_mode": "LIVE"
}
```

### Estimated input_data Size

**Target:** Keep `input_data` < 2KB per record

**Strategy:**
- Use hashes for large data
- Only include key metrics
- Do NOT include extensive arrays
- Compress JSON when possible

**Typical sizes:**
- SCAN: ~500 bytes
- EVENT_CONFIRMATION: ~800 bytes
- STRATEGY: ~600 bytes
- RISK: ~700 bytes
- EXECUTION: ~500 bytes

**Total per complete trace:** ~3KB (5 stages)

### Frontend Timeline Example

With `decision_stage`, frontend can display:

```
Decision Timeline (trace_id: abc-123)

[SCAN] 10:00:00.100
  → Market evaluated: "Lakers vs Warriors"
  → Decision: CANDIDATE
  → Reason: meets_criteria

[EVENT_CONFIRMATION] 10:00:00.200
  → Checkers available: 2
  → Quorum used: 2
  → Decision: FINISHED_CONFIRMED
  → Confidence: 0.95

[STRATEGY] 10:00:00.300
  → Target price: 0.979
  → Size: 5000.0
  → Decision: OrderIntent created

[RISK] 10:00:00.400
  → Validation: APPROVED
  → Final size: 5000.0
  → Reason: all_limits_respected

[EXECUTION] 10:00:00.500
  → Order sent: 0xabc123...
  → Status: PENDING
  → Mode: LIVE
```

---

## Common Issues

### Issue: No Orders Being Created

**Symptoms:**
- Strategy not generating intents
- No orders in system

**Debugging Steps:**

1. **Check Event States:**
   ```python
   GET /api/live/events
   ```
   - Verify events are `FINISHED_CONFIRMED`
   - Check confidence levels
   - Verify watchers are active

2. **Check Strategy Conditions:**
   - Review strategy configuration
   - Check price thresholds
   - Verify market conditions

3. **Check System State:**
   ```python
   GET /api/live/system
   ```
   - Verify `runtime_mode == GREEN`
   - Check no circuit breakers open
   - Review latency status

4. **Query Decision Traces:**
   ```python
   GET /api/history/trace/{trace_id}
   ```
   - Review why intents not created
   - Check rejection reasons

### Issue: Orders Not Filling

**Symptoms:**
- Orders sent but not filling
- Orders remain open

**Debugging Steps:**

1. **Check Order Status:**
   ```python
   GET /api/orders/{order_id}
   ```
   - Verify order in Polymarket
   - Check order price vs current market
   - Review order age

2. **Check Market State:**
   - Verify market still open
   - Check current prices
   - Review liquidity

3. **Check Execution Latency:**
   - Review execution metrics
   - Check for delays
   - Verify API connectivity

### Issue: High Latency

**Symptoms:**
- System in YELLOW or RED mode
- High tick duration
- Slow API responses

**Debugging Steps:**

1. **Check Latency Metrics:**
   ```python
   GET /api/metrics/latency
   ```
   - Identify slow components
   - Check API response times
   - Review checker latencies

2. **Check System Load:**
   - Review CPU usage
   - Check memory usage
   - Verify database performance

3. **Check External APIs:**
   - Verify API availability
   - Check rate limiting
   - Review network connectivity

### Issue: Checker Failures

**Symptoms:**
- Events not confirming
- Low confidence levels
- Checker errors

**Debugging Steps:**

1. **Check Checker Status:**
   ```python
   GET /api/checkers/status
   ```
   - Review checker health
   - Check error rates
   - Verify API connectivity

2. **Review Checker Results:**
   ```python
   GET /api/history/type/checker_result
   ```
   - Analyze recent results
   - Check for patterns
   - Review error messages

3. **Check Circuit Breakers:**
   - Verify no breakers open
   - Review breaker history
   - Check recovery procedures

---

## Querying Decision Traces

### By Trace ID

**Get complete decision chain:**
```python
GET /api/history/trace/{trace_id}
```

**Returns:**
- All events in chain
- All decisions made
- Complete context

### By Time Range

**Get all decisions in time period:**
```python
GET /api/history/range?start={start}&end={end}
```

**Use for:**
- Incident investigation
- Performance analysis
- Audit queries

### By Decision Stage

**Get decisions by stage:**
```python
GET /api/history/stage/{stage}?start={start}&end={end}
```

**Stages:**
- `SCAN` - Market scanning
- `EVENT_CONFIRMATION` - Event state determination
- `STRATEGY` - Intent creation
- `RISK` - Risk validation
- `EXECUTION` - Order execution

---

## Debugging Tools

### Live Control Dashboard

- Real-time system view
- Event monitoring
- Order tracking
- Metrics visualization

### Historical Replay

- Reconstruct past states
- Step-through debugging
- Compare decisions
- Analyze failures

### Logs

- Structured JSON logs
- Trace ID correlation
- Component-level filtering
- Time-range queries

---

## Related Documentation

- [`runbook.md`](runbook.md) - Operational procedures
- [`incident-response.md`](incident-response.md) - Incident response
- [`../backtesting/data-replay.md`](../backtesting/data-replay.md) - Historical replay
- [`../infrastructure/monitoring.md`](../infrastructure/monitoring.md) - Metrics

---

## Open Questions

- What are the exact log retention policies?
- How do we handle very large trace queries?
- What is the procedure for exporting traces?



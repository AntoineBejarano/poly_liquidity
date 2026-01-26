# Operations Runbook

**Purpose**: Operational procedures and real-time monitoring guide for the Live Control system.

**Audience**: Operations team, engineers monitoring the system, on-call engineers.

**Where this is used**: Live Control dashboard, real-time monitoring, operational procedures.

**Last updated**: 2025-01-XX

---

## Overview

The **Live Control** system provides a **real-time view** of bot behavior:

1. **What events** the system is monitoring
2. **What markets** are associated with each event
3. **LIVE/FINISHED states** according to checkers
4. **Watcher states** (active, stopped, error)
5. **Strategy signals** (intents generated)
6. **Risk Engine decisions** (approvals/rejections)
7. **Orders sent, fills, and executions**
8. **System latency and health checks**

**Live Control is the primary tool for:**
- ✅ **Operating the bot** in real-time
- ✅ **Monitoring system behavior**
- ✅ **Debugging live events** when something fails
- ✅ **Identifying failures** before they cause problems
- ✅ **Validating system decisions**
- ✅ **Auditing the system** for compliance

**Live Control is not optional:**  
> It's the bot's mission control tool.

---

## Live Control API

### REST Endpoints

#### `GET /live/events`

**Returns all events currently monitored:**

```json
[
  {
    "event_id": "sports:nba:401585236",
    "event_type": "sports",
    "status": "LIVE",
    "confidence": 0.94,
    "watcher_status": "active",
    "markets": ["pm123", "pm555"],
    "last_update": "2025-01-25T20:15:30.123Z"
  }
]
```

#### `GET /live/markets`

**Returns all markets with current state:**

```json
[
  {
    "market_id": "pm123",
    "question": "Will the Lakers win?",
    "best_yes_price": 0.98,
    "best_no_price": 0.02,
    "event_state": "FINISHED_CONFIRMED",
    "strategy_signals": ["intent_created"],
    "orders": ["order_xyz"]
  }
]
```

#### `GET /live/system`

**Returns system health status:**

```json
{
  "runtime_mode": "GREEN",
  "latency_status": "GREEN",
  "active_watchers": 45,
  "active_markets": 12,
  "open_orders": 3,
  "global_exposure": 15000.0,
  "last_tick_duration_ms": 42
}
```

### Server-Sent Events (SSE)

**Subscribe to real-time updates:**

```javascript
const eventSource = new EventSource('/live/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle update: event_state_changed, order_filled, etc.
};
```

**Event Types:**
- `event_state_changed` - Event state updated
- `intent_created` - Strategy created intent
- `intent_approved` - Risk approved intent
- `order_sent` - Order sent to Polymarket
- `order_filled` - Order filled
- `system_mode_changed` - Runtime mode changed

---

## Monitoring Procedures

### Daily Operations

1. **Check System Health**
   - Verify `runtime_mode == GREEN`
   - Check latency is acceptable
   - Verify no circuit breakers open

2. **Monitor Active Events**
   - Review active watchers
   - Check event states
   - Verify checker results

3. **Review Orders**
   - Check open orders
   - Monitor fills
   - Verify execution latency

4. **Check Exposure**
   - Verify global exposure within limits
   - Check per-market exposure
   - Review active markets count

### Incident Response

**If `runtime_mode == RED`:**

1. **Immediate Actions:**
   - Check kill switch status
   - Review recent errors
   - Check circuit breaker states

2. **Investigation:**
   - Query event logs for recent errors
   - Check latency metrics
   - Review checker failures

3. **Recovery:**
   - Fix underlying issue
   - Clear circuit breakers if appropriate
   - Resume trading gradually

**If orders not filling:**

1. **Check Order Status:**
   - Verify orders in Polymarket
   - Check order prices vs market
   - Review execution latency

2. **Check Market State:**
   - Verify market still open
   - Check liquidity
   - Review price movements

3. **Check System State:**
   - Verify no system pauses
   - Check risk limits
   - Review exposure

---

## Dashboard Views

### Events View

- List of all monitored events
- Current state (LIVE/FINISHED)
- Confidence levels
- Associated markets
- Watcher status

### Markets View

- All active markets
- Current prices
- Event states
- Strategy signals
- Open orders

### System View

- Runtime mode
- Latency metrics
- Circuit breaker states
- Exposure metrics
- Health checks

### Orders View

- All orders (open, filled, cancelled)
- Execution details
- Fill history
- Latency metrics

---

## Alerting

### Critical Alerts

- `runtime_mode == RED`
- Circuit breaker opened
- Exposure limit exceeded
- High error rate
- Latency spike

### Warning Alerts

- `runtime_mode == YELLOW`
- Latency elevated
- Checker failures
- Low confidence events

### Notification Channels

- Slack webhook
- Discord webhook
- Email
- SMS (for critical)

---

## Related Documentation

- [`../infrastructure/monitoring.md`](../infrastructure/monitoring.md) - Metrics collection
- [`../risk/kill-switch.md`](../risk/kill-switch.md) - Kill switch procedures
- [`incident-response.md`](incident-response.md) - Incident response
- [`troubleshooting.md`](troubleshooting.md) - Troubleshooting guide

---

## Open Questions

- What are the exact alert thresholds?
- How do we handle dashboard downtime?
- What is the procedure for manual intervention?




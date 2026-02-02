# Kill Switch and Circuit Breakers

**Purpose**: Technical specification for runtime supervisor, circuit breakers, and fail-safe mechanisms.

**Audience**: Engineers implementing safety mechanisms, operations team, risk managers.

**Where this is used**: Runtime supervisor, all modules for fail-safe activation.

**Last updated**: 2025-01-XX

---

## Overview

The **Runtime Supervisor** is the "mission controller" of the system. It:

1. **Monitors continuously** the health state of the system
2. **Calculates a global Runtime Mode**: `GREEN`, `YELLOW`, or `RED`
3. **Manages circuit breakers**: Trading, Checker, API
4. **Activates fail-safes**: Order cancellation, new entry deactivation, controlled watcher restarts
5. **Communicates state** to Risk Engine, Strategy Engine, Execution Engine, LiveControl

**Without Runtime Supervisor**, the system could continue operating even when:
- Latency is brutal
- External APIs fail
- Checkers are broken

**→ It would become dangerous.**

**With Runtime Supervisor**, the bot becomes a responsibly operable platform at "serious liquidity desk" level.

---

## Runtime Modes

### GREEN Mode

**Conditions:**
- All systems healthy
- Latency < thresholds
- Error rates < thresholds
- APIs responsive

**Actions:**
- Normal operation
- Full order sizes
- All strategies active

### YELLOW Mode

**Conditions:**
- Some systems degraded
- Latency elevated but acceptable
- Error rates slightly elevated
- Some APIs slow

**Actions:**
- Conservative operation
- Reduced order sizes
- Some strategies may pause
- Increased monitoring

### RED Mode

**Conditions:**
- Critical systems failing
- Latency very high
- High error rates
- APIs unresponsive

**Actions:**
- **Pause all trading**
- Cancel open orders
- Disable new entries
- Alert operators

---

## Circuit Breakers

### Trading Circuit Breaker

**Triggers:**
- > 5 failures in 60 seconds
- Latency > 5 seconds consistently
- Error rate > 10% in 1 minute

**Actions when OPEN:**
- No new orders
- Cancel open orders
- System alerts

### Checker Circuit Breaker

**Triggers:**
- > 5 checker failures in 60 seconds
- All checkers timeout
- Checker error rate > 20%

**Actions when OPEN:**
- Disable affected checkers
- Use alternative checkers if available
- Alert operators

### API Circuit Breaker

**Triggers:**
- > 10 API errors in 60 seconds
- Rate limit violations
- Timeout rate > 15%

**Actions when OPEN:**
- Back off API calls
- Use cached data
- Alert operators

---

## Fail-Safe Mechanisms

### Automatic Order Cancellation

**When activated:**
- System enters RED mode
- Manual kill switch activated
- Critical error detected

**Process:**
1. Identify all open orders
2. Cancel via Polymarket API
3. Update order states
4. Log all cancellations

### Entry Deactivation

**When activated:**
- YELLOW or RED mode
- Risk limits exceeded
- Manual pause

**Process:**
1. Stop Strategy Engine from creating new intents
2. Continue monitoring existing positions
3. Allow exits but not entries

### Watcher Restart

**When activated:**
- Watcher errors > 10 consecutive
- Watcher timeout
- Manual restart requested

**Process:**
1. Stop watcher gracefully
2. Clear state
3. Restart with fresh state
4. Resume monitoring

---

## Monitoring Inputs

### Latency Metrics

- Main loop latency
- API call latency
- Checker latency
- Execution latency

### Error Metrics

- Error rate by component
- Error rate by type
- Consecutive errors
- Critical errors

### System Health

- CPU usage
- Memory usage
- Active watchers
- Active markets
- Open orders

---

## State Communication

### To Risk Engine

- Current Runtime Mode
- Latency status
- System health metrics

### To Strategy Engine

- Whether to create new intents
- Size reduction factors
- Strategy activation status

### To Execution Engine

- Whether to send orders
- Order cancellation requests
- System pause status

### To LiveControl

- Real-time Runtime Mode
- Circuit breaker states
- System health dashboard

---

## Manual Kill Switch

### Activation

**Via API:**
```python
POST /api/admin/kill-switch/activate
{
  "reason": "manual_intervention",
  "cancel_orders": true
}
```

**Via LiveControl:**
- Emergency stop button
- Confirmation required
- Immediate activation

### Deactivation

**Via API:**
```python
POST /api/admin/kill-switch/deactivate
{
  "reason": "issue_resolved"
}
```

**Via LiveControl:**
- Resume button
- System health check required
- Gradual reactivation

---

## Related Documentation

- [`../infrastructure/monitoring.md`](../infrastructure/monitoring.md) - Metrics collection
- [`controls.md`](controls.md) - Risk controls
- [`policy.md`](policy.md) - Risk policy

---

## Open Questions

- What is the exact procedure for manual kill switch activation?
- How do we handle partial system failures?
- What is the recovery procedure after RED mode?





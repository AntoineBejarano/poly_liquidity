# Quorum Rules

**Purpose**: Technical specification for dynamic quorum calculation and event state confirmation rules.

**Audience**: Engineers implementing event state aggregation, checker system developers.

**Where this is used**: Event Watch Engine, Checker System, State Aggregator.

**Last updated**: 2025-01-XX

---

## Overview

Quorum rules determine when an event state can be confirmed as `FINISHED_CONFIRMED`. The system uses a **dynamic quorum** that adapts to the number of healthy checkers available.

---

## Critical Rule

**With 0 checkers, the system NEVER emits `FINISHED_CONFIRMED`.**

### Semantics of `allow_zero_checker`

#### `allow_zero_checker = true`

**Means:** Allow system to continue operating without checkers, but **WITHOUT confirming FINISHED** and **WITHOUT trading**.

**Behavior:**
- ✅ System continues evaluating markets
- ✅ Produces decision traces
- ✅ Maintains operational state
- ❌ **NEVER enters (NO TRADING)**
- ❌ **NEVER confirms FINISHED_CONFIRMED**
- ❌ Event state = `UNKNOWN` (never `FINISHED_CONFIRMED`)

#### `allow_zero_checker = false`

**Means:** If no checkers available, system enters DEGRADED/PAUSED state.

**Behavior:**
- ❌ System enters `DEGRADED` / `PAUSED` state
- ❌ Does not evaluate markets
- ❌ Does not produce decision traces
- ❌ No trading

---

## Dynamic Quorum Calculation

### Formula

```python
checkers_healthy = get_healthy_checkers(category)
checkers_available = len(checkers_healthy)

# CRITICAL RULE: With 0 checkers, NEVER confirm FINISHED
if checkers_available == 0:
    if allow_zero_checker:
        # System stays alive but without trading
        event_state = "UNKNOWN"
        effective_quorum = None  # No quorum possible
        trading_permitted = False
        system_status = "OPERATIONAL_NO_TRADING"
    else:
        # System in DEGRADED/PAUSED state
        event_state = "UNKNOWN"
        effective_quorum = None
        trading_permitted = False
        system_status = "DEGRADED"

elif checkers_available == 1:
    if allow_single_checker:
        effective_quorum = 1
        # Can confirm FINISHED_UNCONFIRMED
    else:
        effective_quorum = min(quorum_base, checkers_available)
        # Can confirm FINISHED_UNCONFIRMED if quorum_base is 1

else:  # checkers_available >= 2
    effective_quorum = min(quorum_base, checkers_available)
    # Can confirm FINISHED_CONFIRMED if enough checkers agree
```

### Checker Health Detection

A checker is considered "healthy" if:
- Enabled (`enabled = true`)
- Responded successfully in last N executions (configurable)
- Latency within acceptable limits
- Not in persistent error state

---

## Quorum States

### FINISHED_CONFIRMED

**Requirements:**
- `effective_quorum` checkers say `FINISHED`
- Each with confidence >= `min_confidence_threshold` (0.8)
- State stable for at least 2 consecutive cycles

**Usage:** Strategy can create orders with high confidence

### FINISHED_UNCONFIRMED

**Requirements:**
- 1 checker says `FINISHED` with confidence >= 0.8
- Other checkers say `UNKNOWN` or fail
- OR 2+ checkers say `FINISHED` but with confidence < 0.8

**Usage:** Strategy can create orders but with reduced size

### LIVE

**Requirements:**
- No checker detects `FINISHED`
- At least 1 checker says `LIVE`
- Event continues live according to checkers

**Usage:** Do not create orders, continue monitoring

### UNKNOWN

**Requirements:**
- All checkers fail
- Internal inconsistencies
- Insufficient data

**Usage:** Do not create orders, wait for more data

---

## Configuration

```python
class QuorumConfig:
    quorum_base: int = 2  # Base quorum requirement
    allow_single_checker: bool = False  # Allow quorum of 1
    allow_zero_checker: bool = False  # Allow operation without checkers (no trading)
    min_confidence_threshold: float = 0.8  # Minimum confidence per checker
    min_checkers_for_confirmed: int = 2  # Minimum for FINISHED_CONFIRMED
```

---

## Frontend Display

The frontend must clearly show:
- **Available checkers:** List of active and healthy checkers
- **Configured quorum:** Base configured value
- **Effective quorum:** Real value used in each decision
- **Decision reason:** Why an event was confirmed or not
- **Checkers used:** Which checkers participated in decision
- **Unavailable checkers:** Which checkers are inactive/failing

---

## Related Documentation

- [`../architecture/data-flow.md`](../architecture/data-flow.md) - Event Watch Engine
- [`../risk/policy.md`](../risk/policy.md) - Protected parameters

---

## Open Questions

- What is the exact health check algorithm?
- How do we handle checker recovery?
- What is the procedure for quorum adjustment?




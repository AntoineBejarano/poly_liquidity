# Config-Driven Architecture

**Purpose**: Technical specification for configuration-driven system design, allowing all operational parameters to be configurable from frontend without code changes.

**Audience**: Engineers implementing configuration system, frontend developers, operations team.

**Where this is used**: Configuration service, frontend settings, runtime parameter updates.

**Last updated**: 2025-01-XX

---

## Overview

Transform the system from code-driven to config-driven, allowing **ALL operational parameters** to be configurable from the frontend without modifying code.

---

## Configuration Categories

### 1. Risk Parameters

- `max_global_exposure` - Maximum global exposure
- `max_market_exposure` - Maximum exposure per market
- `max_markets_active` - Maximum active markets
- `max_order_size` - Maximum order size
- `min_order_size` - Minimum order size
- `exposure_method` - Exposure calculation method

### 2. Strategy Parameters

- `target_edge` - Target profit margin
- `safety_tick` - Safety tick for price calculation
- `latency_adjustment_factor` - Latency adjustment factor
- `min_price_threshold` - Minimum price threshold

### 3. Event Engine Parameters

- `quorum_base` - Base quorum requirement
- `allow_single_checker` - Allow quorum of 1
- `allow_zero_checker` - Allow operation without checkers
- `min_confidence_threshold` - Minimum confidence per checker

### 4. System Parameters

- `execution_mode` - Execution mode (LIVE/PAPER/SIMULATION)
- `latency_fail_mode` - Latency failure mode (strict/lenient)
- `cancel_on_red` - Cancel orders on RED mode
- `reduce_size_in_yellow` - Reduce size in YELLOW mode

---

## Protected Parameters

Some parameters require protection against human error:

### Critical (requires_confirmation = true)

1. **`allow_zero_checker`**
   - Affects security - allows system without checkers
   - Protection: `requires_confirmation = true`
   - Frontend: Show warning

2. **`execution_mode = LIVE`**
   - Change to LIVE activates real trading with real money
   - Protection: `requires_confirmation = true`
   - Frontend: Require typing "LIVE" as confirmation

3. **`latency_fail_mode`**
   - Affects system security behavior
   - Protection: `requires_confirmation = true`

4. **`quorum_base`**
   - Affects core EventEngine logic
   - Protection: `requires_confirmation = true`

5. **`min_feed_confidence`**
   - Affects decision reliability
   - Protection: `requires_confirmation = true`

### Important (requires_confirmation = true, but less critical)

6. **`max_global_exposure`**
   - Affects global risk limits
   - Protection: `requires_confirmation = true`
   - Frontend: Show current exposure vs new limit

7. **`max_market_exposure`**
   - Affects per-market risk limits
   - Protection: `requires_confirmation = true`

8. **`cancel_on_red`**
   - Affects behavior in high latency situations
   - Protection: `requires_confirmation = true`

---

## Configuration Storage

### Database Schema

```sql
CREATE TABLE system_config (
    id UUID PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value JSONB NOT NULL,
    category TEXT NOT NULL,
    is_readonly BOOLEAN NOT NULL DEFAULT FALSE,
    requires_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    updated_at TIMESTAMP NOT NULL,
    updated_by UUID
);
```

### Configuration Service

```python
class ConfigService:
    async def get(key: str) -> Any:
        """Get configuration value."""
        pass
    
    async def set(key: str, value: Any, *, requires_confirmation: bool = False) -> None:
        """Set configuration value."""
        pass
    
    async def list(category: str = None) -> List[ConfigItem]:
        """List configuration items."""
        pass
```

---

## Frontend Integration

### Configuration UI

- Display all configurable parameters
- Show current values
- Allow editing (with protection where needed)
- Show confirmation dialogs for protected parameters
- Display change history

### Protection Implementation

**For `requires_confirmation = true`:**
- Show confirmation dialog
- Require user to type confirmation token (e.g., "CONFIRM")
- Backend validates token before applying change
- Log all changes with audit trail

---

## Runtime Updates

### Hot Reload

- Configuration changes apply immediately
- No system restart required
- Changes logged and audited

### Validation

- Validate parameter ranges
- Check dependencies
- Verify system constraints
- Reject invalid configurations

---

## Related Documentation

- [`quorum.md`](quorum.md) - Quorum rules
- [`../risk/policy.md`](../risk/policy.md) - Protected parameters
- [`../infrastructure/secrets.md`](../infrastructure/secrets.md) - Secrets management

---

## Open Questions

- What is the exact validation logic for each parameter?
- How do we handle configuration conflicts?
- What is the rollback procedure for bad configurations?




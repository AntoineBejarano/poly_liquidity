# Risk Policy

**Purpose**: Risk management policies, rules, and protected parameters.

**Audience**: Risk managers, operations team, engineers implementing risk rules.

**Where this is used**: Risk engine configuration, policy enforcement.

**Last updated**: 2025-01-XX

---

## Overview

This document defines the risk management policies, trading rules validation, and protected parameters that require protection against human error.

---

## Trading Rules Validation

### Rule 1: Exposure Limits

**Market Exposure Limit:**
- Maximum exposure per market: 10,000 USDC (configurable)
- Enforced on every order intent
- Cannot be exceeded

**Global Exposure Limit:**
- Maximum global exposure: 200,000 USDC (configurable)
- Sum of all market exposures
- Cannot be exceeded

### Rule 2: Active Markets Limit

- Maximum active markets: 10 (configurable)
- Prevents over-diversification
- Enforced on order intent approval

### Rule 3: Order Size Limits

- Minimum order size: 100 USDC
- Maximum order size: 5,000 USDC
- Enforced on every order intent

### Rule 4: Latency-Based Restrictions

**GREEN Mode:**
- Full order sizes allowed
- All strategies active

**YELLOW Mode:**
- Reduced order sizes (50% reduction)
- Conservative operation

**RED Mode:**
- No new orders
- Cancel open orders

### Rule 5: System Health Checks

- System must be active (`system_active == True`)
- No circuit breakers open
- APIs must be responsive

---

## Protected Parameters

### Protection Types

**1. `is_readonly = true`**
- Parameter cannot be modified from frontend
- Only changed via migrations or controlled code changes
- Used for infrastructure parameters requiring architectural changes

**2. `requires_confirmation = true`**
- Parameter requires explicit confirmation before changing
- Frontend must show confirmation dialog
- User must provide `confirmation_token` (e.g., type "CONFIRM" or similar)
- Backend validates token before applying change

### Critical Parameters Requiring Protection

#### 🔴 Critical (requires_confirmation = true)

**1. `allow_zero_checker`**
- **Purpose:** Allows system operation without checkers (dangerous)
- **Default:** `False`
- **Protection:** `requires_confirmation = true`
- **Frontend Warning:** "Permitting system without checkers may result in unreliable decisions"
- **Impact:** Affects security - allows trading without event verification

**2. `execution_mode = LIVE`**
- **Purpose:** Enables real trading with real money
- **Default:** `DRY_RUN` or `PAPER`
- **Protection:** `requires_confirmation = true`
- **Frontend Warning:** 
  - Show large, clear warning
  - Require typing "LIVE" as confirmation_token
  - Show summary of current configuration before confirming
- **Impact:** Activates real trading - critical change

**3. `latency_fail_mode`**
- **Purpose:** Affects system security behavior
- **Protection:** `requires_confirmation = true`
- **Frontend:** Explain impact on fail-safes
- **Impact:** Changes how system handles latency issues

**4. `quorum_base`**
- **Purpose:** Base quorum for event confirmation
- **Protection:** `requires_confirmation = true`
- **Frontend:** Explain impact on event confirmation logic
- **Impact:** Affects core EventEngine logic

**5. `min_feed_confidence`**
- **Purpose:** Minimum confidence required from checkers
- **Protection:** `requires_confirmation = true`
- **Frontend:** Explain impact on decision reliability
- **Impact:** Affects reliability of trading signals

#### ⚠️ Important (requires_confirmation = true, less critical)

**6. `max_global_exposure`**
- **Purpose:** Maximum total exposure limit
- **Default:** 200,000 USDC
- **Protection:** `requires_confirmation = true`
- **Frontend:** Show current exposure vs new limit
- **Hard Limit:** 500,000 USDC (cannot exceed)
- **Impact:** Affects global risk limits

**7. `max_market_exposure`**
- **Purpose:** Maximum exposure per market
- **Default:** 10,000 USDC
- **Protection:** `requires_confirmation = true`
- **Frontend:** Show current exposure vs new limit
- **Hard Limit:** 50,000 USDC (cannot exceed)
- **Impact:** Affects per-market risk limits

**8. `cancel_on_red`**
- **Purpose:** Cancel orders when latency is RED
- **Protection:** `requires_confirmation = true`
- **Frontend:** Explain impact on order management
- **Impact:** Affects behavior during high latency situations

#### 📝 Normal (no special protection)

- `safety_tick`
- `target_margin`
- `min_entry_price`
- `max_order_size`
- `scan_interval_seconds`
- Other non-critical parameters

### Implementation

#### Backend: ConfigService

```python
def update_config(
    self, 
    key: str, 
    value: Any, 
    confirmation_token: Optional[str] = None
) -> bool:
    """
    Updates a configuration parameter.
    
    Args:
        key: Parameter key
        value: New value
        confirmation_token: Confirmation token (required if requires_confirmation = true)
    
    Returns:
        True if updated, False if validation failed
    """
    config = self._get_config(key)
    
    # Verify is_readonly
    if config.is_readonly:
        raise ValueError(f"Parameter {key} is readonly and cannot be modified")
    
    # Verify requires_confirmation
    if config.requires_confirmation:
        if not confirmation_token:
            raise ValueError(f"Parameter {key} requires confirmation token")
        if not self._validate_confirmation_token(key, confirmation_token):
            raise ValueError(f"Invalid confirmation token for {key}")
    
    # Validate value according to min/max
    if config.min_value and value < config.min_value:
        raise ValueError(f"Value {value} below minimum {config.min_value}")
    if config.max_value and value > config.max_value:
        raise ValueError(f"Value {value} above maximum {config.max_value}")
    
    # Update in DB
    # ...
    
    # Invalidate cache
    self.invalidate_cache(key)
    
    return True
```

#### Frontend: API Endpoint

**PUT** `/api/config/{key}`

**Request:**
```json
{
  "value": "LIVE",
  "value_type": "string",
  "confirmation_token": "LIVE"  // Required if requires_confirmation = true
}
```

**Response (if confirmation required but not provided):**
```json
{
  "error": "confirmation_required",
  "message": "This parameter requires confirmation",
  "requires_confirmation": true,
  "confirmation_prompt": "Type 'LIVE' to confirm changing execution mode to LIVE"
}
```

#### Frontend: Component Implementation

**For normal parameters:**
- Direct input
- Real-time validation
- Save immediately

**For parameters with requires_confirmation:**
- Input with "Change" button
- On click, show confirmation dialog
- Require typing confirmation_token
- Show clear warning of impact
- Only save after confirmation

**For parameters with is_readonly:**
- Show value but disabled
- Show "Read-only" badge
- Explain why it's readonly

### Default Values in Migration

When populating `system_config` with initial values:

```sql
-- Critical parameters
INSERT INTO system_config (key, value, value_type, category, is_readonly, requires_confirmation, description)
VALUES 
  ('allow_zero_checker', 'false', 'bool', 'event_engine', false, true, 'Allow system operation without checkers (no trading)'),
  ('execution_mode', 'DRY_RUN', 'string', 'system', false, true, 'Execution mode: DRY_RUN, PAPER, LIVE'),
  ('latency_fail_mode', 'strict', 'string', 'risk', false, true, 'Fail-safe mode for latency'),
  ('quorum_base', '2', 'int', 'event_engine', false, true, 'Base quorum for event confirmation'),
  ('min_feed_confidence', '0.8', 'float', 'event_engine', false, true, 'Minimum confidence required from checkers');
```

---

## Policy Enforcement

### Configuration Validation

**On Startup:**
- Validate all risk parameters
- Check for dangerous configurations
- Alert on protected parameter changes

**Runtime:**
- Monitor parameter changes
- Log all modifications
- Alert on dangerous changes

### Audit Trail

**All changes logged:**
- Who made the change
- When it was made
- What was changed
- Reason for change
- Approval status

---

## Risk Limits

### Hard Limits (Cannot be exceeded)

- Maximum global exposure: 500,000 USDC
- Maximum market exposure: 50,000 USDC
- Maximum order size: 10,000 USDC
- Maximum active markets: 20

### Soft Limits (Configurable with approval)

- Default global exposure: 200,000 USDC
- Default market exposure: 10,000 USDC
- Default order size: 5,000 USDC
- Default active markets: 10

---

## Related Documentation

- [`controls.md`](controls.md) - Risk controls implementation
- [`kill-switch.md`](kill-switch.md) - Circuit breakers
- [`../architecture/execution-engine.md`](../architecture/execution-engine.md) - Execution flow

---

## Open Questions

- What is the exact approval process for limit increases?
- How do we handle emergency limit adjustments?
- What is the audit retention policy?



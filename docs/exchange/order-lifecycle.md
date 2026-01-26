# Order Lifecycle

**Purpose**: Documentation of order states, transitions, and lifecycle management in Polymarket.

**Audience**: Engineers, operations team, traders.

**Where this is used**: Order execution, debugging, system operations.

**Last updated**: 2025-01-XX

---

## Order States

### State Machine

```
PENDING → SUBMITTED → OPEN → PARTIALLY_FILLED → FILLED
                              ↓
                         CANCELLED
                              ↓
                         FAILED
```

### State Descriptions

- **PENDING**: Order created, not yet submitted
- **SUBMITTED**: Order sent to Polymarket, awaiting confirmation
- **OPEN**: Order active in orderbook
- **PARTIALLY_FILLED**: Order partially executed
- **FILLED**: Order completely executed
- **CANCELLED**: Order cancelled before execution
- **FAILED**: Order submission failed

---

## Order Creation

### Process

1. Strategy generates intent
2. Risk engine validates
3. Execution engine creates order
4. Order signed (EIP-712)
5. Order submitted to Polymarket

### Order Payload

```json
{
  "market": "market-id",
  "side": "BUY",
  "outcome": "YES",
  "price": 0.98,
  "size": 1000,
  "signature": "0x...",
  "nonce": 12345
}
```

---

## Order Execution

### Fill Detection

- Polling: Periodic status checks
- WebSocket: Real-time updates (preferred)
- Callbacks: If supported by Polymarket

### Partial Fills

- Track filled size
- Update order status
- Continue monitoring for remaining size

---

## Order Cancellation

### Automatic Cancellation

- System pause
- Risk limit violation
- Market resolution
- Timeout expiration

### Manual Cancellation

```bash
curl -X POST /api/orders/{order_id}/cancel
```

---

## Error Handling

### Common Errors

- **Insufficient Balance**: Not enough funds
- **Invalid Market**: Market closed or invalid
- **Rate Limit**: Too many requests
- **Network Error**: Connection failure

### Retry Logic

- Exponential backoff
- Maximum retry attempts
- Error logging
- Alert on persistent failures

---

## Monitoring

### Metrics

- Order submission rate
- Fill rate
- Average fill time
- Cancellation rate
- Error rate

### Alerts

- High error rate
- Slow fill times
- Unusual cancellation patterns

---

## Open Questions

- What is the exact timeout for order submission?
- How do we handle order rejection by Polymarket?
- What is the procedure for orphaned orders?
- How do we reconcile order states?




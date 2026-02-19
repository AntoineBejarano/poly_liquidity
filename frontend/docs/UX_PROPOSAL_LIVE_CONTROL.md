# Live Control — Trading Desk Redesign

## Strategy Type Differentiation

| Type | Detection | Focus |
|------|-----------|-------|
| **Tipster** | `support_graphs` contains `telegram_listener` | Tips pipeline, intents from tips, stake per tip |
| **Surebet** | tags/name include surebet, arbitrage | Dual venue, arbitrage opps, execution pipeline |
| **Liquidity** | Default | Orderbook signals, execution feed |

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. STRATEGY HEADER                                                  │
│    Title · Status · Controls · Config link · lastUpdate             │
│    hairline separator                                               │
├─────────────────────────────────────────────────────────────────────┤
│ 2. KPI HORIZONTAL STRIP                                             │
│    PnL | Exposición [====    ] $2.1k/$5k | Intents | Win Rate | Δt  │
│    Dynamic PnL color (primary/destructive). Exposure bar.            │
│    hairline separator                                               │
├─────────────────────────────────────────────────────────────────────┤
│ 3. MODE/EVENTS ALERT (compact, when needed)                         │
├─────────────────────────────────────────────────────────────────────┤
│ 4. LIVE EXECUTION FEED (compact table)                              │
│    time | side | outcome | price | size | status | trace            │
│    dense rows, tabular-nums                                         │
├─────────────────────────────────────────────────────────────────────┤
│ 5. INCOMING SIGNALS (strategy-specific)                             │
│    Tipster: pending tips queue                                      │
│    Surebet: arbitrage opportunities                                 │
│    Liquidity: book imbalance, signals                               │
├─────────────────────────────────────────────────────────────────────┤
│ 6. EVENT PIPELINE (vertical state list)                             │
│    ○ waiting → ○ placed → ○ resolving                               │
│    or table when many items                                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Tailwind Class Examples

**Section separator (hairline):**
```
border-b border-[hsl(var(--border))]/40
```

**KPI strip item:**
```
px-4 py-2 border-r border-[hsl(var(--border))]/40 last:border-r-0
text-[13px] tabular-nums
```

**PnL dynamic:**
```
totalPnL >= 0 ? 'text-[hsl(var(--primary))]' : 'text-destructive'
```

**Exposure bar container:**
```
h-1.5 bg-muted/50 rounded-full overflow-hidden
```

**Dense table:**
```
text-[12px] py-1.5 px-3
```

**No cards:** use `bg-muted/30` or `bg-transparent` with hairline only.

---

## Layouts (by strategy type)

Tipster y Liquidity tienen **layouts diferentes por definición**.

### Tipster Live Layout
- Header · Mode/Events · KPI Strip · **Tips Pipeline** (TipsPipelineCompact) · Executions · External Confirmation · Risk Monitor · Activity Log
- **No** Signals Monitor (orderbook)
- **No** Event Pipeline (Polymarket)
- **No** Orderbook Health

### Liquidity Live Layout
- Header · Mode/Events · KPI Strip · Live Execution Feed · **Signals Monitor** (orderbook) · External Confirmation · Event Pipeline · Positions · Risk Monitor · Orderbook Health · Activity Log

### Component mapping

| Section | Tipster | Liquidity |
|---------|---------|-----------|
| Incoming data | TipsPipelineCompact | SignalsMonitor |
| Event pipeline | — | EventPipeline |
| Orderbook | — | Orderbook Health |

**Tipster detection:** `support_graphs` contains `telegram_listener`.

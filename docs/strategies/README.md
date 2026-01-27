# Strategies

**Purpose**: Define the strategy philosophy, design constraints, and supported strategy types for the PolyLiquidity trading platform.

**Audience**: Engineers, researchers, and traders configuring strategies.

**Where this is used**: Strategy configuration, system design decisions, and platform architecture.

**Last updated**: 2025-01-XX

---

# Strategy Philosophy and Design

## Objective

We are building a **strategy-driven trading platform** for Polymarket, designed for **professional traders**, not retail users.

The system must allow a trader to:

- Create multiple **independent strategies**
- Configure each strategy **without writing code**
- Attach **markets / events** to each strategy
- Configure **external data sources** (odds feeds, reference markets, proxies, APIs) **entirely from the frontend**
- Run multiple strategies **in parallel**, each with its own logic, risk, and targets

This is **not a single bot**, but a **strategy platform**.

---

## Core Non-Negotiable Principles

1. **Strategy is the root entity**, not markets or events.
2. **Event is the atomic execution unit**, not the market.
3. **Strategies do NOT call APIs directly**.
4. **External data sources are fully configurable from DB / frontend**.
5. **No external market names are hardcoded in backend logic**.
6. **Only the execution venue is fixed** (Polymarket).
7. **All other data sources are plugins, defined at runtime**.
8. **Strategies must be declarative, not hardcoded logic**.
9. **The trader configures strategies; the engine executes them**.

If any design violates one of these, it is wrong.

---

## Mental Model

### Hierarchy

```
Strategy
├── Configuration (rules, risk, sizing, timing)
├── External Data Sources (reference, hedge, confirmation)
└── Targets
└── Events (time-bucketed)
```

### What each concept means

- **Strategy**: A declarative definition of how to exploit an edge.
- **Event**: A concrete, time-bounded opportunity where the strategy can act.
- **Market**: A grouping mechanism for discovery only (never the execution unit).
- **External Data Source**: Any external feed (odds, prices, confirmations), fully configurable.
- **Execution Venue**: Where orders are sent (initially Polymarket only).

---

## Strategy Philosophy

A strategy is **not just a set of rules**.

A strategy defines:
- When to start observing an event
- How to validate real-world state
- How to validate market state
- Why an edge exists
- How much risk is acceptable
- What execution intent to produce

Strategies **do not place orders directly**.  
They generate **execution intents**.

---

## Supported Strategy Types

The system must support **multiple fundamentally different strategies**, such as:

- **Near-Resolution Liquidity Provision** - Provide liquidity when events have finished but markets haven't resolved
- **Resolution Drift Arbitrage** - Exploit pricing errors after events are decided
- **Delayed Resolution Hedging** - Reduce risk and free capital when Polymarket delays resolution
- **Surebet / Arbitrage strategies** - Multi-leg arbitrage opportunities
- **ValueBet strategies** - Value-based entry strategies
- **Liquidity Near End strategies** - Liquidity provision near market close

These strategies:
- Share infrastructure
- Do NOT share decision logic
- Must not interfere with each other

The system must be designed so **new strategy types can be added later** without refactoring existing ones.

---

## Strategy Theory: Systematic Strategies with Real Edge

### 1. Near-Resolution Liquidity Provider (Core Strategy)

**What it is**: Strategy that **provides unilateral liquidity** when an event **has already finished in the real world**, but **hasn't been resolved by Polymarket yet**.

**Edge exploited**:
- Polymarket resolves with **latency**
- Many users want to exit **before resolution**
- Market lacks professional liquidity providers
- Price converges to 0.99 / 0.01, but spreads are wide and liquidity is limited

**Example**:
- Event: "Will Team A win the game?"
- Game ends, Team A wins clearly
- External sources confirm result (sports API, multiple feeds)
- Polymarket state: YES bid: 0.95, YES ask: 0.99, low liquidity
- Bot action: Places large **unilateral bid**: BUY YES @ 0.98
- Users accept selling at 0.98 to cash out immediately
- Bot holds position until resolution
- Resolution → payout = 1.00
- **Result**: ~2% profit on capital used, minutes-hours exposure, low risk

**Key characteristics**:
- ✅ One-sided (not classic market making)
- ✅ Doesn't depend on rewards
- ✅ High ROI per time unit
- ✅ Scales with capital
- ❌ Doesn't work without fast event detection

**When bot does NOT enter**:
- Ambiguous result
- Event without cross-confirmation
- Polymarket already adjusted prices correctly
- Legal risk / market suspension

---

### 2. Resolution Drift Arbitrage (Complementary Strategy)

**What it is**: Strategy that **corrects pricing errors** that appear **after the event is decided**, but **before official resolution**.

**Edge exploited**:
- After event ends:
  - Market makers withdraw
  - Retail leaves "zombie" orders
  - Book can become inconsistent:
    - YES + NO > 1
    - Absurd spreads
    - Frozen prices far from real outcome
- Market is already dead, but not resolved yet

**Example**:
- Event finished, clear result
- Book in Polymarket: YES @ 0.97, NO @ 0.06
- (0.97 + 0.06 = 1.03 → logical error)
- Bot action: Buys the **incorrectly expensive or cheap side**
  - BUY NO @ 0.06 (if outcome is NO)
  - or BUY YES @ 0.97 (if incorrectly anchored)
- Holds until resolution

**Result**: Pure arbitrage, doesn't need to sell liquidity, doesn't depend on other users' behavior

**Key characteristics**:
- ✅ Very low risk (event already decided)
- ✅ Low capital required
- ✅ Less competition
- ✅ Complements main bot
- ❌ Less frequency
- ❌ Depends on book errors

---

### 3. Delayed Resolution Hedging (Infrastructure Strategy)

**What it is**: This bot **doesn't seek direct profit**, but **reduces risk and frees capital** when Polymarket delays resolving events.

**Problem it solves**:
- Polymarket can take **hours or days** to resolve
- Capital remains blocked
- Operational risk (cancellations, disputes, errors)
- Unclosed accounting exposure

Meanwhile:
- Other equivalent markets already reflect the result

**Example**:
- Political event resolved in reality
- Polymarket still hasn't resolved
- Other equivalent market:
  - is at 0.99
  - or already resolved
  - or is a clear proxy of the result
- Bot action: Buys correlated market or opens equivalent opposite position, freezes economic result

**Result**: Blocked PnL ≈ secured, risk reduced to almost 0, mental and accounting capital freed, allows continuing to operate other events

**Key characteristics**:
- ✅ Reduces drawdowns
- ✅ Improves capital efficiency
- ✅ Doesn't compete with anyone
- ✅ Very low risk
- ❌ Doesn't generate visible direct PnL
- ❌ Only useful with large volume

---

## Relationship Between Strategies

```
Event Detection Engine
↓
Market State Cache
↓
──────────────────────────────────
│  Strategy Layer               │
│                                │
│  1. Near-Resolution Liquidity  │
│  2. Resolution Drift Arb       │
│  3. Delayed Resolution Hedge   │
──────────────────────────────────
↓
Execution Engine
```

- Share **detection and data**
- Do NOT share decisions
- Do NOT mix orders
- Each has its own risk and logic

---

## External Data Sources

The backend must have **ZERO hardcoded knowledge** of:
- Pinnacle
- Bet365
- Any sportsbook, exchange, or feed

Instead:
- External data sources are defined dynamically
- Each data source uses a **connector definition**
- Each connector defines a **JSON schema** for its configuration
- Configuration includes: Base URLs, API keys, Headers, Proxies, Rate limits, Polling intervals

The trader must be able to:
- Add a new external data source from the UI
- Configure it fully
- Assign it to a strategy with a specific role (reference, hedge, confirmation)

---

## Backend Responsibilities

### Backend DOES:
- Load strategies from DB
- Load external data sources from DB
- Execute connector plugins generically
- Build a normalized `StrategyContext`
- Run strategy evaluation
- Send execution intents to the execution venue

### Backend DOES NOT:
- Know what Pinnacle or Bet365 is
- Contain `if source == X` logic
- Contain sportsbook-specific rules
- Contain strategy-specific hardcoding

---

## Database Philosophy

The database stores **configuration**, not behavior.

- Strategies are stored declaratively
- Strategy blocks are stored as JSON
- External data sources are stored as records
- Connector configurations are stored as JSON
- No DB migration should be needed to add:
  - A new strategy instance
  - A new external data source
  - A new connector config

---

## One-Sentence North Star

> Build a declarative, strategy-driven trading platform where professional traders configure how to exploit market inefficiencies, while the system executes those strategies using configurable external data sources and a fixed execution venue.

---

## Open Questions

- What is the maximum number of concurrent strategies?
- How are strategy conflicts resolved when multiple strategies target the same event?
- What is the strategy versioning and migration policy?
- How are strategy performance metrics collected and reported?





# Objective & Design Constraints — Strategy-Based Polymarket Bot Platform

## 1. Objective (What we are building)

We are building a **strategy-driven trading platform** for Polymarket, designed for **professional traders**, not retail users.

The system must allow a trader to:

- Create multiple **independent strategies**
- Configure each strategy **without writing code**
- Attach **markets / events** to each strategy
- Configure **external data sources** (odds feeds, reference markets, proxies, APIs) **entirely from the frontend**
- Run multiple strategies **in parallel**, each with its own logic, risk, and targets

This is **not a single bot**, but a **strategy platform**.

---

## 2. Core Non-Negotiable Principles

Cursor MUST respect these constraints at all times:

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

## 3. Mental Model (Correct Domain Model)

### Hierarchy

Strategy
├── Configuration (rules, risk, sizing, timing)
├── External Data Sources (reference, hedge, confirmation)
└── Targets
└── Events (time-bucketed)

yaml
Copiar código

### What each concept means

- **Strategy**  
  A declarative definition of how to exploit an edge.

- **Event**  
  A concrete, time-bounded opportunity where the strategy can act.

- **Market**  
  A grouping mechanism for discovery only (never the execution unit).

- **External Data Source**  
  Any external feed (odds, prices, confirmations), fully configurable.

- **Execution Venue**  
  Where orders are sent (initially Polymarket only).

---

## 4. Strategy Philosophy (Very Important)

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

## 5. Supported Strategy Types (Examples, not hardcoded logic)

The system must support **multiple fundamentally different strategies**, such as:

- Near-Resolution Liquidity Provision
- Resolution Drift Arbitrage
- Delayed Resolution Hedging
- Surebet / Arbitrage strategies
- ValueBet strategies
- Liquidity Near End strategies

These strategies:
- Share infrastructure
- Do NOT share decision logic
- Must not interfere with each other

The system must be designed so **new strategy types can be added later** without refactoring existing ones.

---

## 6. External Data Sources (Critical Requirement)

The backend must have **ZERO hardcoded knowledge** of:

- Pinnacle
- Bet365
- Any sportsbook, exchange, or feed

Instead:

- External data sources are defined dynamically
- Each data source uses a **connector definition**
- Each connector defines a **JSON schema** for its configuration
- Configuration includes:
  - Base URLs
  - API keys
  - Headers
  - Proxies
  - Rate limits
  - Polling intervals

The trader must be able to:
- Add a new external data source from the UI
- Configure it fully
- Assign it to a strategy with a specific role (reference, hedge, confirmation)

---

## 7. Backend Responsibilities (What the backend does and does NOT do)

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

## 8. Database Philosophy

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

## 9. Frontend & UX Philosophy

The frontend is a **strategy builder for professional traders**.

### UX Goals

- No irrelevant fields shown
- UI adapts to the selected strategy type
- External data sources are reusable
- Strategy creation feels like configuring a system, not filling a form

### Expected UX Flow

1. User opens platform → sees list of strategies
2. Clicks “Add Strategy”
3. Selects a strategy type (template)
4. Configures strategy-specific blocks
5. Selects external data sources (optional/required)
6. Adds markets / events as targets
7. Activates the strategy

---

## 10. What Cursor Is Expected To Produce

Based on this document, Cursor should produce:

1. A **build plan** (phases, order of implementation)
2. A **database schema** (Alembic migrations)
3. A **backend architecture** (services, engines, plugins)
4. A **frontend architecture** (views, flows, UX structure)
5. Clear separation of concerns
6. No hardcoded external integrations

---

## 11. Final Constraint (Very Important)

If at any point the design:

- Hardcodes an external market name
- Treats markets as the root entity
- Couples strategies to APIs
- Mixes decision logic across strategies

Then the design is incorrect and must be revised.

---

## 12. One-Sentence North Star

> Build a declarative, strategy-driven trading platform where professional traders configure how to exploit market inefficiencies, while the system executes those strategies using configurable external data sources and a fixed execution venue.

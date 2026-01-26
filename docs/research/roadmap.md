# Research Roadmap

**Purpose**: Research plans, implementation roadmaps, and future enhancements.

**Audience**: Researchers, engineers planning new features, product managers.

**Where this is used**: Planning sessions, feature development, research projects.

**Last updated**: 2025-01-XX

---

## Implementation Plans

### Series → Markets → Events → Outcomes

**Status:** Planning  
**Priority:** High

**Goal:** Implement proper hierarchy: Series → Markets → Events → Outcomes

**Current State:**
- ✅ Market model partially correct (missing `series_id`)
- ⚠️ Event model requires correction (`metadata` → `polymarket_payload`)
- ❌ Series model does not exist
- ❌ Tag model does not exist
- ❌ Scanner creates Markets directly, should discover Series → Markets → Events

**Required Changes:**
1. Create Series model (container/grouping, not tradeable)
2. Create Tag model (for market categorization)
3. Create MarketTag relationship table
4. Update Market model to include `series_id` (ForeignKey)
5. Update Event model:
   - Rename `metadata` → `polymarket_payload` (SQLAlchemy collision)
   - Rename `event_id` → `polymarket_event_id` (if String)
   - Use `id` (UUID) as internal identifier
6. Update Scanner to discover Series → Markets → Events
7. Verify Strategy/Execution operate only on Events

**Design Rules (Non-negotiable):**
- Series never activated for trading (UX/navigation only)
- Only Markets can be enabled/disabled by user
- Events discovered automatically from active Markets
- Strategy, Risk, Execution only operate on Events, never Series or Markets

**Implementation Phases:**
1. Database models (Series, Tag, MarketTag)
2. Scanner updates (discover hierarchy)
3. Frontend updates (show Series, enable/disable Markets)
4. API endpoints (Series, Tags)
5. Verification (Strategy/Execution on Events only)

---

### Advanced Indicators Engine

**Status:** Planning  
**Priority:** Medium

**Goal:** Implement modular advanced indicators engine supporting multiple strategy types

**Planned Features:**
- **Liquidity Provider Indicators:**
  - Book imbalance analysis
  - Liquidity depth metrics
  - Price momentum indicators
  - Volume analysis

- **Arbitrage/Surebet Indicators:**
  - Cross-market price comparison
  - Profit opportunity detection
  - Multi-leg arbitrage signals

**Implementation Structure:**
- Base abstract class `SignalProvider`
- Factory pattern for indicator instantiation
- Stale data protection (validate data freshness)
- Memoization system (avoid redundant calculations)
- Integration with Decision Graph nodes

**Phases:**
1. Base structure (`indicators/base.py`, `factory.py`)
2. Liquidity Provider indicators
3. Integration in Decision Engine
4. Arbitrage/Surebet indicators
5. Frontend SignalsMonitor
6. Testing and validation

---

### Latency and UX Improvements

**Status:** Planning  
**Priority:** Medium

**Goal:** Optimize latency monitoring and improve frontend UX

**Backend Improvements:**
- Redis client for distributed cache
- SWR (Stale-While-Revalidate) pattern
- Reduce Polymarket API calls
- Increase cache TTL (5s → 30s)
- Rate limiting and exponential backoff

**Frontend Improvements:**
- Remove unnecessary full-screen spinners
- Progressive loading (components load independently)
- Better loading states per component
- Granular error handling

**Implementation:**
- Backend: Optimize LatencyMonitor with Redis cache
- Frontend: Component-level data loaders
- Pattern: "One Component, One Data Loader"

---

### Component-Based Loading

**Status:** Planning  
**Priority:** Low

**Goal:** Implement independent loading for each component/section

**Benefits:**
- Progressive loading (components appear as data ready)
- No blocking (slow component doesn't block others)
- Better UX (user sees useful content immediately)
- Granular error handling (errors in one component don't affect others)

**Pattern:**
- Each visual component has its own `useDataLoader`
- No monolithic data loading
- Independent error states
- Independent loading states

**Pages to update:**
- `dashboard/capital`
- `dashboard/operations`
- `values/live`
- `strategies/[id]/live`

---

### Premium UX Improvements

**Status:** Planning  
**Priority:** Low

**Goal:** Enhance frontend user experience

**Planned Features:**
- Improved dashboard layouts
- Real-time visualizations
- Advanced filtering
- Customizable views
- Better mobile responsiveness

---

## Research Areas

### Strategy Research

- New strategy patterns
- Multi-leg strategies
- Arbitrage opportunities
- Market making improvements

### Data Research

- External data source integration
- Real-time data processing
- Historical data analysis
- Pattern recognition

### Risk Research

- Advanced risk models
- Dynamic position sizing
- Portfolio optimization
- Stress testing

---

## Future Enhancements

### Infrastructure

- Multi-region deployment
- High availability setup
- Advanced monitoring
- Automated scaling

### Features

- Multi-exchange support
- Advanced order types
- Portfolio management
- Performance analytics

---

## Related Documentation

- [`experiments.md`](experiments.md) - Experiment guidelines
- [`../architecture/system-overview.md`](../architecture/system-overview.md) - System architecture

---

## Open Questions

- What are the priorities for next features?
- How do we measure research success?
- What is the timeline for roadmap items?



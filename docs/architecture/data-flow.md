# Data Flow Architecture

**Purpose**: Technical specification for data ingestion, normalization, event mapping, and real-time monitoring of external events.

**Audience**: Engineers implementing or maintaining data ingestion, event mapping, and monitoring systems.

**Where this is used**: Scanner, Event Mapping Layer, Checker System, Event Watch Engine implementation.

**Last updated**: 2025-01-XX

---

## Overview

The data flow architecture consists of four main components that work together to:

1. **Scan** Polymarket for relevant markets
2. **Map** markets to real-world events
3. **Verify** event status using external checkers
4. **Monitor** events in real-time until completion

This pipeline enables the system to detect when real-world events finish before Polymarket resolves markets, creating trading opportunities.

---

## Architecture Flow

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Scanner   │ --> │ Event Mapping    │ --> │ Checker      │ --> │ Event Watch     │
│             │     │ Layer            │     │ System       │     │ Engine          │
└─────────────┘     └──────────────────┘     └──────────────┘     └─────────────────┘
     │                       │                        │                      │
     ▼                       ▼                        ▼                      ▼
Polymarket API      EventDescriptor          External APIs          EventState
```

---

## 1. Scanner Module

### Purpose

The Scanner is the entry point to the system. It:

1. **Downloads** active markets from Polymarket (public API)
2. **Filters** only relevant markets for the bot
3. **Normalizes** and enriches data for consistent processing
4. **Reduces API consumption** via caching and rate limiting
5. **Maintains complete traceability** of all decisions

### Critical Importance

**The Scanner is the gateway to the system.** If it fails, everything else fails. Therefore:

- Must be **robust and resilient** (never fail completely)
- Must be **efficient** (one request every 10-30 seconds is sufficient)
- Must have **complete traceability** (every discarded market must have explicit reason)
- **Does NOT decide anything** - only selects candidate markets

### Inputs

**Polymarket API:**
- Endpoint: `GET https://gamma-api.polymarket.com/events`
- Rate Limits: ~200 requests / 10 seconds
- Scanner makes **1 request per cycle** (every 10-30 seconds)

**Configuration:**
```python
class ScannerConfig:
    min_price_threshold: float = 0.97
    allowed_categories: List[str] = ["sports"]
    allowed_subcategories: List[str] = ["basketball", "football", "soccer"]
    scanner_cache_ttl: int = 5  # seconds
    scan_interval_seconds: int = 30
```

### Outputs

**CandidateMarket:**
```python
class CandidateMarket:
    market_id: UUID
    polymarket_id: str
    question: str
    category: str
    subcategory: str | None
    outcomes: List[Outcome]  # YES/NO with prices
    best_yes_price: float
    best_no_price: float
    spread: float
    status: str  # "OPEN", "CLOSED", "RESOLVED"
    event_metadata: EventMetadata  # Teams, dates, sport detected
    scanned_at: datetime
```

### Filtering Process

1. **Structural Filters:**
   - `status == "OPEN"`
   - `outcomes.length == 2` (binary markets only)
   - Outcomes have valid prices

2. **Category Filters:**
   - Category in `allowed_categories`
   - Subcategory in `allowed_subcategories` (if configured)

3. **Price Filters:**
   - `best_yes_price >= min_price_threshold`

4. **Temporal Filters:**
   - Extract event dates from market text
   - Filter markets with dates too far in future (optional)

### Caching Strategy

- **TTL:** 3-5 seconds
- **Key:** `scanner:markets_raw`
- **Fallback:** Use cache if API fails

### Rate Limiting

- Scanner makes **1 request per cycle**
- All watchers and other modules **DO NOT hit this endpoint**
- Handles 429 errors with exponential backoff
- Maximum 3 retries

### Logging

Each scan generates structured JSON logs:
```json
{
  "timestamp": "2025-01-18T10:25:00.123Z",
  "level": "INFO",
  "component": "scanner",
  "event_type": "scan_complete",
  "trace_id": "...",
  "found_markets": 124,
  "filtered_structural": 98,
  "filtered_category": 12,
  "filtered_price": 8,
  "candidates": 6,
  "cache_used": false,
  "latency_ms": 132
}
```

---

## 2. Event Mapping Layer

### Purpose

The Event Mapping Layer bridges:
> *"Textual market in Polymarket"* → *"Clearly defined and traceable real event"*

It:

1. **Reads information** from a Polymarket market (text, category, dates, etc.)
2. **Determines what type of real-world event** it represents (`sports`, `politics`, `crypto`, `finance`, `weather`, `custom`, etc.)
3. **Maps it, if possible**, to a concrete canonical event in an external source (ESPN, election APIs, on-chain data, Yahoo Finance, etc.)
4. **Returns a standardized EventDescriptor** that the rest of the system can understand and monitor

### Critical Importance

**If mapping fails or is ambiguous**, the market **does NOT enter the watchers/event engine pipeline**, and the strategy ignores it.

### Inputs

**CandidateMarket from Scanner:**
```python
class CandidateMarket:
    market_id: str
    question: str
    category: str
    subcategory: str | None
    close_time: datetime
    teams_detected: List[str] | None
    date_detected: datetime | None
    keywords: List[str] | None
```

### Outputs

**EventDescriptor:**
```python
class EventDescriptor:
    market_id: str
    mapped: bool
    event_type: str  # "sports", "politics", "crypto", etc.
    mapping_confidence: float  # 0.0 - 1.0
    canonical_event_id: str | None  # e.g., "sports:nba:401585236"
    sources: List[str]  # ["espn"], ["ap_news"], etc.
    metadata: Dict  # Schema depends on event_type
    reason: str | None  # Why not mapped or low confidence
    trace_id: UUID
```

### Mapping Phases

1. **Phase 1: Classify event_type**
   - Use heuristics based on category and text
   - Patterns: `vs`, `@`, `win`, `election`, `BTC`, `TSLA`, etc.

2. **Phase 2: Delegate to Type-Specific Mapper**
   - `sports` → SportsMapper
   - `politics` → PoliticsMapper
   - `crypto` → CryptoMapper
   - etc.

3. **Phase 3: Calculate Confidence**
   - Entity match score (teams, candidates, etc.)
   - Date match score
   - Source reliability score

### Sports Mapper (MVP Implementation)

**Steps:**

1. **Extract teams, competition, date**
   - Use regex + team alias dictionaries
   - Normalize aliases to canonical names

2. **Determine sport and league**
   - From category or team knowledge

3. **Search sports calendar**
   - Call ESPN (or equivalent) API
   - Search for events matching teams + date

4. **Match by teams + date**
   - Compare Polymarket teams with ESPN teams
   - Compare dates (within tolerance)

5. **Calculate confidence score**
   - Team match: 0.0 - 1.0
   - Date match: 0.0 - 1.0
   - League match: 0.0 - 1.0
   - Weighted average

### Confidence Thresholds

| Confidence | Level | Action |
|------------|-------|--------|
| `>= 0.85` | **MAPPED_STRONG** | Event Watch Engine can create watcher |
| `0.65 <= x < 0.85` | **MAPPED_WEAK** | Watcher can be created, but Strategy may require more confirmation |
| `< 0.65` | **NOT_MAPPED** | Market automatically ignored |

### Caching

- Cache mappings by `market_id`
- Invalidate on mapping rule changes
- Do not recalculate on every tick if market unchanged

---

## 3. Checker System

### Purpose

The Checker System is a modular layer for accessing external data that:

1. **Converts the real world into structured signals** the system can operate on
2. **Allows adding new sources** without touching core business logic
3. **Supports multiple event types** (sports, politics, crypto, finance, weather, etc.)
4. **Returns normalized results** (`LIVE`, `FINISHED`, `UNKNOWN`)
5. **Feeds Event Watch Engine** with consistent and reliable information
6. **Maintains complete traceability** of each external call

### Critical Importance

**It's the piece that converts "the real world" into structured signals.** Without checkers, the system cannot determine if an event has actually finished.

### Architecture

```
Event Watch Engine → Checker Runner → Checker Registry → BaseChecker Interface
                                                          ↓
                                                    [Sports Checkers]
                                                    [Politics Checkers]
                                                    [Crypto Checkers]
                                                    [Finance Checkers]
                                                    [Weather Checkers]
                                                          ↓
                                                    External APIs
```

### Data Model

**CheckerResult:**
```python
class CheckerResult:
    state: str  # "LIVE", "FINISHED", "UNKNOWN"
    confidence: float  # 0.0 - 1.0
    finished_at: datetime | None
    raw_payload: Dict  # Raw data for audit
    source: str  # Checker name (e.g., "espn_nba_scoreboard_v1")
    latency_ms: float
    error: str | None
    timestamp: datetime
```

### BaseChecker Interface

All checkers implement:
```python
class BaseChecker(ABC):
    name: str
    event_types: List[str]
    weight: float  # Importance in quorum (0-1)
    timeout_ms: int
    max_retries: int
    
    @abstractmethod
    async def check(
        self,
        external_event_id: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> CheckerResult:
        pass
```

### Checker Types

**Sports Checkers:**
- `ESPNScoreboardChecker` - ESPN Scoreboard API
- `AlternativeSportsChecker` - TheSportsDB, API-Sports, FlashScore
- `FlashScoreChecker` - FlashScore API

**Politics Checkers:**
- `APNewsElectionChecker` - Associated Press Elections API
- `NYTElectionChecker` - New York Times Elections API

**Crypto Checkers:**
- `EthereumForkChecker` - Ethereum RPC nodes
- `BitcoinHalvingChecker` - Bitcoin RPC nodes

**Finance Checkers:**
- `YahooFinanceCloseChecker` - Yahoo Finance API
- `CPIReleaseChecker` - Macro data releases

**Weather Checkers:**
- `OpenWeatherSnowChecker` - OpenWeather API

### Execution

**Parallel Execution:**
```python
async def run_checkers_for_event(event_descriptor: EventDescriptor) -> List[CheckerResult]:
    checkers = CHECKER_REGISTRY.list_by_event_type(event_descriptor.event_type)
    tasks = [checker.check(external_event_id) for checker in checkers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return normalize_results(results)
```

**Timeouts and Retries:**
- Each checker has own timeout: 1-5 seconds
- Limited retries: 2-3 attempts
- Exponential backoff between retries

**Error Normalization:**
- All errors return `CheckerResult` with `state="UNKNOWN"`
- Never throw exceptions

### Circuit Breaker

```python
class CheckerCircuitBreaker:
    failure_threshold: int = 5
    timeout: int = 60
    state: str  # "CLOSED", "OPEN", "HALF_OPEN"
```

**Actions when OPEN:**
- Disable checker temporarily
- Send alerts
- System continues with other checkers

---

## 4. Event Watch Engine

### Purpose

The Event Watch Engine is responsible for:

1. **Monitoring in real-time** the state of real-world events
2. **Integrating multiple external checkers** (ESPN, FlashScore, AP News, blockchain nodes, etc.)
3. **Determining with high precision** if an event is: `LIVE`, `FINISHED`, or `UNKNOWN`
4. **Emitting reliable states** for Strategy to decide whether to enter a market
5. **Avoiding duplicate watchers** by sharing watchers between markets that depend on the same event
6. **Managing hundreds of watchers simultaneously** without blocking the backend
7. **Guaranteeing complete traceability** for audit and debugging

### Critical Importance

**It's one of the most important modules** because it determines when a real-world event has actually finished, which triggers entry opportunities. Without this module, the system cannot detect finished events before Polymarket.

### Concept: Watcher per Event

**Key Architecture:**
- A watcher monitors **ONE real event**, not a market
- If 20 markets depend on the same NBA game:
  - Create **ONE SportsWatcher**
  - That watcher maintains an array of dependent markets
  - When watcher detects `FINISHED`, it updates all those markets

**This avoids:**
- ❌ Duplicate requests
- ❌ Unnecessary watchers
- ❌ Concurrency problems
- ❌ Excessive API consumption

### Inputs

**EventDescriptor from Mapping Layer:**
```python
class EventDescriptor:
    event_id: str  # External event ID (e.g., "401585236" from ESPN)
    event_type: str  # "sports", "politics", "crypto", etc.
    sport: str | None
    league: str | None
    teams: List[str]
    starts_at: datetime | None
    confidence: float
    markets: List[UUID]  # Markets that depend on this event
```

### Outputs

**EventState:**
```python
class EventState:
    event_id: str
    state: str  # "LIVE", "FINISHED_CONFIRMED", "FINISHED_UNCONFIRMED", "UNKNOWN"
    confidence: float  # 0.0 - 1.0
    sources: Dict[str, str]  # {"espn": "FINISHED", "flashscore": "FINISHED"}
    last_update: datetime
    finished_at: datetime | None
    checker_results: List[CheckerResult]
```

### Components

1. **Event Watch Coordinator**
   - Receives new `EventDescriptor` from Mapping Layer
   - Checks if watcher already exists for `event_id`
   - Creates new watcher or attaches markets to existing one
   - Stops watchers when no longer needed

2. **Watcher Lifecycle Manager**
   - Manages watcher lifecycle
   - States: `INITIALIZING`, `LIVE_MONITORING`, `FINISHED_DETECTED`, `FINISHED_CONFIRMED`, `TERMINATED`

3. **Checker Runner**
   - Executes checkers specific to event type
   - Runs checkers in parallel
   - Handles timeouts and retries

4. **Event State Aggregator**
   - Combines checker results using quorum rules
   - Weighted by reliability
   - Considers recency and state stability

### Quorum Rules

**FINISHED_CONFIRMED:**
- 2+ checkers say `FINISHED`
- Each with confidence >= `min_confidence_threshold` (0.8)
- State stable for at least 2 consecutive cycles

**FINISHED_UNCONFIRMED:**
- 1 checker says `FINISHED` with confidence >= 0.8
- Other checkers say `UNKNOWN` or fail
- OR 2+ checkers say `FINISHED` but with confidence < 0.8

**LIVE:**
- No checker detects `FINISHED`
- At least 1 checker says `LIVE`
- Event continues live according to checkers

**UNKNOWN:**
- All checkers fail
- Internal inconsistencies
- Insufficient data

### Update Frequencies

| Event Type | Frequency | Reason |
|------------|-----------|--------|
| **Sports** | Every 3-5s | Sports events change quickly |
| **Politics** | Every 60-120s | Political events are slower |
| **Crypto** | Every block (12s ETH) | Synchronized with blockchain |
| **Finance** | Every 60s | Financial data updates periodically |
| **Weather** | Every 10-15min | Weather events are slow |
| **Custom** | Configurable | According to specific needs |

### Watcher Lifecycle

```
EventDescriptor Received
  ↓
Does Watcher Exist?
  ├─ Yes → Attach Market
  └─ No → Create New Watcher
      ↓
State: INITIALIZING
  ↓
Load Checkers
  ↓
State: LIVE_MONITORING
  ↓
Execute Checkers in Parallel
  ↓
Aggregate Results
  ↓
Quorum FINISHED?
  ├─ Yes → State: FINISHED_DETECTED
  │         ↓
  │    Confirmed 2+ cycles?
  │         ├─ Yes → State: FINISHED_CONFIRMED
  │         │         ↓
  │         │    Notify Strategy
  │         │    Notify Execution
  │         │    Notify LiveControl
  │         │         ↓
  │         │    State: TERMINATED
  │         └─ No → Continue Monitoring
  └─ No → Continue Monitoring
```

### Termination Conditions

1. **Event Confirmed FINISHED** - State = `FINISHED_CONFIRMED`
2. **Market Closed in Polymarket** - All associated markets closed/resolved
3. **Maximum Timeout** - `watcher_max_duration_hours` exceeded
4. **Persistent Critical Error** - `check_failures` > 10 consecutive
5. **Manual Override** - User stops watcher from LiveControl

### Scalability

**Designed for:**
- **200-300 simultaneous watchers**
- **Without blocking main loop** (using asyncio)
- **With automatic API throttling** (rate limiting)
- **Checker pooling** (reuse connections)

**Optimizations:**
- Internal queues for managing requests
- Checker pooling (reuse checker instances)
- Latency control (prioritize fast checkers)
- Batching (group requests when possible)

### Logging

**Each watcher tick:**
```json
{
  "timestamp": "2025-01-25T20:00:05.123Z",
  "level": "INFO",
  "component": "event_watch_engine",
  "event_type": "watcher_tick",
  "trace_id": "...",
  "event_id": "401585236",
  "checker_results": {
    "espn": {"result": "FINISHED", "confidence": 0.95, "latency_ms": 340},
    "flashscore": {"result": "FINISHED", "confidence": 0.92, "latency_ms": 280}
  },
  "final_state": "FINISHED_CONFIRMED",
  "confidence": 0.94
}
```

---

## Integration Points

### Scanner → Event Mapping Layer

```
Scanner detects market → CandidateMarket → Event Mapping Layer
```

### Event Mapping Layer → Event Watch Engine

```
Event Mapping Layer → EventDescriptor → Event Watch Engine → Watcher
```

### Event Watch Engine → Checker System

```
Watch Engine → CheckerRunner → Checkers → External APIs
```

### Event Watch Engine → Strategy Engine

```
Watch Engine detects FINISHED_CONFIRMED → Notifies Strategy → Strategy reviews markets
```

---

## Related Documentation

- [`../exchange/polymarket-integration.md`](../exchange/polymarket-integration.md) - Polymarket API details
- [`../architecture/execution-engine.md`](../architecture/execution-engine.md) - Execution flow
- [`../risk/kill-switch.md`](../risk/kill-switch.md) - Circuit breakers

---

## Open Questions

- What are the exact ESPN API endpoints and authentication requirements?
- How do we handle rate limits across multiple checkers for the same API?
- What is the procedure for handling ambiguous mappings?
- How do we verify checker reliability over time?





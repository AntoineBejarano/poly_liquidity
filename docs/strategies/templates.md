# Strategy Templates Guide

**Purpose**: Guide for using pre-defined strategy templates and creating common strategies.

**Audience**: Traders configuring strategies, engineers setting up new strategy types.

**Where this is used**: Strategy creation, configuration, and setup.

**Last updated**: 2025-01-XX

---

## Available Templates

### 1. Near-Resolution Liquidity Provider

**What it does:**
- Detects when a real-world event has finished but hasn't been resolved by Polymarket yet
- Provides liquidity by buying from users who want to exit before resolution
- Captures price differential (e.g., buy at 0.98, resolves at 1.00 = 2% profit)

**When it enters:**
- Event finished and confirmed by external sources
- Price on Polymarket between 0.95 and 0.98
- Exposure within risk limits

**How to configure:**
1. Select "Near-Resolution Liquidity Provider" template
2. Configure external event confirmation source (Support Graph)
3. Adjust price limits and order size in `check_price_range` and `calculate_size` nodes
4. Assign events to the strategy

**Required Support Graph:**
- `confirm_event_result`: Gets event result confirmation from external source

---

### 2. Surebet Polymarket-Pinnacle

**What it does:**
- Detects price differences between Polymarket and Pinnacle
- Buys in cheaper market and sells in more expensive one
- Captures pure arbitrage

**When it enters:**
- Surebet opportunity exists (profit > 2%)
- Price on Polymarket different from Pinnacle
- Exposure within limits

**How to configure:**
1. Select "Surebet Polymarket-Pinnacle" template
2. Configure Pinnacle external source (Support Graph)
3. Adjust minimum profit percentage required
4. Configure order size as percentage of bank

**Required Support Graph:**
- `fetch_pinnacle_odds`: Gets Pinnacle odds every 10 seconds
- Calculates if surebet opportunity exists

---

## Creating a Strategy from a Template

### Step 1: Select Template
1. Go to `/strategies/create`
2. In step 0, select a template
3. Template automatically loads:
   - Complete Decision Graph
   - Required Support Graphs
   - Basic risk configuration
   - Name and description

### Step 2: Customize
1. **Basic Information**: Adjust name, description, and tags
2. **Decision Graph**: 
   - Review nodes and their conditions
   - Adjust check values (prices, percentages)
   - Modify order size if needed
3. **Support Graphs**:
   - Configure external sources (ExternalDataSource IDs)
   - Adjust triggers (intervals, conditions)
4. **Risk Config**: Adjust exposure limits and order size

### Step 3: Configure External Sources
Before activating the strategy, you need:
1. Create required External Data Sources:
   - For Liquidity Near End: event confirmation source
   - For Surebet: Pinnacle odds source
2. Get the IDs of these sources
3. Update Support Graphs with correct IDs

---

## Example: Configure Liquidity Near End

### 1. Create External Data Source for Confirmation

```json
{
  "name": "Sports API - Event Results",
  "connector_type": "custom_api",
  "connector_config": {
    "base_url": "https://api.sports.com",
    "api_key_name": "X-API-Key",
    "api_key_value": "tu-api-key",
    "method": "GET"
  }
}
```

### 2. Get Source ID
- Go to External Data Sources page
- Copy the ID of the created source

### 3. Update Support Graph
In the `confirm_event_result` Support Graph, update:
```json
{
  "source_id": "UUID-of-your-external-source",
  "endpoint": "/api/event/result",
  "params": {
    "event_id": "{{event.id}}"
  }
}
```

### 4. Adjust Decision Graph Conditions
In the `check_price_range` node, adjust limits:
```json
{
  "conditions": [
    {
      "field": "market_state.last_price",
      "operator": ">=",
      "value": 0.94  // Minimum price
    },
    {
      "field": "market_state.last_price",
      "operator": "<=",
      "value": 0.97  // Maximum price
    }
  ]
}
```

### 5. Configure Order Size
In the `calculate_size` node:
```json
{
  "method": "fixed_range",
  "min": 200,   // Minimum $200
  "max": 3000   // Maximum $3000
}
```

---

## Example: Configure Surebet Polymarket-Pinnacle

### 1. Create External Data Source for Pinnacle

```json
{
  "name": "Pinnacle Odds API",
  "connector_type": "custom_api",
  "connector_config": {
    "base_url": "https://api.pinnacle.com",
    "api_key_name": "Authorization",
    "api_key_value": "Bearer tu-token",
    "method": "GET"
  }
}
```

### 2. Update Support Graph
In `fetch_pinnacle_odds`, update:
```json
{
  "source_id": "UUID-of-pinnacle",
  "endpoint": "/v1/odds",
  "params": {
    "sportId": "29",
    "eventIds": "{{event.external_event_id}}"
  }
}
```

### 3. Adjust Minimum Profit
In the `check_surebet_opportunity` node:
```json
{
  "conditions": [
    {
      "field": "external_data.surebet_opportunity.profit_percentage",
      "operator": ">=",
      "value": 0.03  // Minimum 3% profit
    }
  ]
}
```

---

## Tips

1. **Start with templates**: Use templates as base, don't try to create from scratch
2. **Test with small events**: Activate strategy with low-value events first
3. **Monitor executions**: Review Graph Executions to see what's happening
4. **Adjust gradually**: Make small changes and test each one
5. **Document your changes**: Note what you modified and why

---

## Troubleshooting

### Strategy not generating intents
- Verify assigned events are in "ACTIVE" state
- Review Decision Graph conditions
- Verify State Cache has necessary data

### Support Graph not executing
- Verify trigger is configured correctly
- Review that external source is active
- Check Support Graph execution logs

### Error getting external data
- Verify External Data Source is configured correctly
- Review that API key is valid
- Verify endpoint is correct

---

## Related Documentation

- [`README.md`](README.md) - Strategy philosophy and concepts
- [`../architecture/execution-engine.md`](../architecture/execution-engine.md) - Execution engine details
- [`../infrastructure/secrets.md`](../infrastructure/secrets.md) - External data source configuration


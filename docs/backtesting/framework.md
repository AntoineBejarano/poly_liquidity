# Backtesting Framework

**Purpose**: Guide for running backtests, validating strategies, and analyzing historical performance.

**Audience**: Researchers, quantitative analysts, strategy developers.

**Where this is used**: Strategy development, performance validation, research.

**Last updated**: 2025-01-XX

---

## Overview

The backtesting framework allows you to:

- Replay historical events
- Test strategy changes
- Validate risk controls
- Analyze performance metrics
- Compare strategy variants

---

## Running a Backtest

### Prerequisites

- Historical data available
- Strategy configuration
- Risk parameters defined
- Market data loaded

### Basic Backtest

```python
from app.core.backtesting import BacktestRunner

runner = BacktestRunner(
    start_date="2025-01-01",
    end_date="2025-01-31",
    strategy_id="strategy-uuid",
    initial_capital=100000
)

results = runner.run()
```

### Backtest Configuration

```python
config = {
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "strategy_id": "strategy-uuid",
    "initial_capital": 100000,
    "slippage_model": "fixed",  # or "proportional"
    "slippage_bps": 5,  # 5 basis points
    "commission": 0.001,  # 0.1%
    "include_fees": True
}
```

---

## Historical Data

### Data Sources

- Historical market data from Polymarket
- Event state history
- Order execution history
- Market resolution data

### Data Requirements

- Market prices (OHLCV)
- Orderbook snapshots
- Event state transitions
- Execution fills

---

## Metrics

### Performance Metrics

- **Total Return**: Overall profit/loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Average Trade**: Mean profit per trade

### Risk Metrics

- **Exposure**: Maximum capital deployed
- **Leverage**: Capital efficiency
- **Volatility**: Return variability
- **VaR**: Value at Risk

---

## Strategy Comparison

### A/B Testing

Compare multiple strategy variants:

```python
strategies = [
    {"id": "strategy-v1", "name": "Baseline"},
    {"id": "strategy-v2", "name": "Optimized"}
]

comparison = runner.compare_strategies(strategies)
```

### Analysis

- Performance comparison
- Risk-adjusted returns
- Drawdown analysis
- Trade frequency

---

## Limitations

### Known Limitations

- Historical data may be incomplete
- Slippage models are approximations
- Market impact not fully modeled
- Latency effects simplified

### Best Practices

- Use multiple time periods
- Test different market conditions
- Validate with paper trading
- Consider out-of-sample testing

---

## Open Questions

- What is the minimum data requirement for reliable backtests?
- How should we handle missing historical data?
- What slippage model is most accurate?
- How do we validate backtest results against live trading?





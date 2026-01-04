# PolyCLI Wiki

A comprehensive guide to prediction market trading strategies, algorithms, and techniques implemented in PolyCLI.

## Table of Contents

### Core Concepts
- [Understanding Prediction Markets](./01-Understanding-Prediction-Markets.md)
- [Expected Value and Edge](./02-Expected-Value-and-Edge.md)

### Trading Strategies

| Module | Description | Key Techniques |
|--------|-------------|----------------|
| [Edge Finding](./03-Edge-Finding.md) | Finding information advantages | Wallet tracking, volume analysis, cross-referencing |
| [Position Sizing](./04-Position-Sizing.md) | Optimal bet sizing | Kelly Criterion, correlation management |
| [Market Selection](./05-Market-Selection.md) | Choosing what to trade | Liquidity analysis, resolution criteria |
| [Risk Management](./06-Risk-Management.md) | Protecting your bankroll | Hedging, drawdown limits, diversification |
| [Tools & Automation](./07-Tools-and-Automation.md) | Speed and efficiency | Alerts, order book analysis, execution |
| [Psychology](./08-Psychology.md) | Mental game | Journaling, variance, tilt management |
| [Advanced Techniques](./09-Advanced-Techniques.md) | Expert strategies | Arbitrage, synthetic positions, market making |

### Quick Reference
- [CLI Command Reference](./10-CLI-Reference.md)
- [Glossary of Terms](./11-Glossary.md)

---

## Philosophy

The core philosophy of successful prediction market trading:

1. **Edge First**: Never trade without a clearly articulated reason why the market is wrong
2. **Process Over Outcomes**: Judge decisions on process, not results
3. **Bankroll Preservation**: Survival is prerequisite to success
4. **Continuous Learning**: Every trade is data for improvement

## Getting Started

```bash
# Install PolyCLI
uv sync --all-extras

# See available commands
polycli --help

# Search for markets
polycli market search "election"

# Calculate position size
polycli position kelly --bankroll 10000 --win-prob 0.6 --market-price 0.45
```

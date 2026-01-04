# Understanding Prediction Markets

## What Are Prediction Markets?

Prediction markets are exchange-traded markets where participants buy and sell contracts that pay out based on the outcome of future events. The price of a contract reflects the market's collective probability estimate for that outcome.

### How They Work

```
Contract: "Will X happen by date Y?"

YES token: Pays $1.00 if X happens, $0.00 if not
NO token:  Pays $1.00 if X doesn't happen, $0.00 if it does

Current price of YES token: $0.65
Implied probability: 65%
```

### Key Properties

| Property | Description |
|----------|-------------|
| **Binary Outcomes** | Most markets resolve to Yes/No |
| **Price = Probability** | $0.65 = 65% implied probability |
| **Zero-Sum** | Every winner has a loser |
| **Market Efficiency** | Prices aggregate information |

## Why Trade Prediction Markets?

### Information Aggregation
Prediction markets are remarkably good at aggregating dispersed information. Studies show they often outperform polls and expert forecasts.

### Edge Opportunities
Despite efficiency, edges exist because:
- Information takes time to propagate
- Different traders have different information
- Behavioral biases create mispricings
- Low liquidity in niche markets

## Polymarket Specifics

### The CLOB (Central Limit Order Book)
Polymarket uses an order book model:

```
Example Order Book for "Trump wins 2024"

BIDS (buyers)          ASKS (sellers)
$0.52 - 5,000 shares   $0.53 - 3,000 shares
$0.51 - 8,000 shares   $0.54 - 4,500 shares
$0.50 - 12,000 shares  $0.55 - 6,000 shares

Spread: $0.01 (1.9%)
Mid price: $0.525
```

### Settlement
- Markets resolve based on predefined criteria
- Resolution sources are specified (AP, official announcements, etc.)
- Winning tokens pay $1.00, losing tokens pay $0.00

### Fees
- Polymarket charges fees on trades
- Consider fees when calculating edge

## Theoretical Framework

### Efficient Market Hypothesis (EMH)
Markets are "efficient" when prices reflect all available information. Prediction markets are semi-efficient:

- **Strong Form**: All information (public + private) reflected - rarely true
- **Semi-Strong**: All public information reflected - mostly true for liquid markets
- **Weak Form**: Historical prices reflected - generally true

### Finding Edge
Edge exists when your probability estimate differs from the market:

```
Your estimate: 70%
Market price:  55%
Edge: +15%

If you're right, this is a +EV (positive expected value) trade.
```

## Common Market Types

### Political Markets
- Elections (President, Senate, House)
- Policy outcomes (legislation, executive orders)
- Appointments and nominations

**Edge Sources**: Polling analysis, demographic modeling, insider information

### Economic Markets
- Fed decisions (rate hikes/cuts)
- Inflation data (CPI, PCE)
- GDP and employment numbers

**Edge Sources**: Economic modeling, Fed communication analysis, leading indicators

### Event Markets
- Court rulings
- Company announcements
- Sports outcomes

**Edge Sources**: Domain expertise, news speed, pattern recognition

## Risk vs. Reward

### Expected Value Calculation
```
EV = (P(win) × Profit if win) - (P(lose) × Loss if lose)

Example:
- Buy YES at $0.45
- Your P(win) estimate: 60%
- Profit if win: $0.55 (you get $1.00, paid $0.45)
- Loss if lose: $0.45 (you get $0.00, paid $0.45)

EV = (0.60 × $0.55) - (0.40 × $0.45)
EV = $0.33 - $0.18
EV = +$0.15 per share
```

### The Fundamental Challenge
Even with positive EV:
- You can still lose (variance)
- You might be wrong about your probability
- Timing and execution matter

This is why **position sizing** and **risk management** are crucial.

## CLI Usage

```bash
# List active markets
polycli market list --limit 50

# Search for specific topics
polycli market search "federal reserve"

# Get market details
polycli market info <condition_id>
```

---

**Next**: [Expected Value and Edge](./02-Expected-Value-and-Edge.md)

# Market Selection

## Choosing Where to Trade

Not all markets are worth trading. Market selection is about finding opportunities where:
- You have genuine edge
- The market structure allows you to profit from it
- Risk/reward justifies the position

## Liquidity vs. Edge Tradeoff

### The Fundamental Tension

```
High Liquidity Markets:
✓ Easy to enter/exit
✓ Tighter spreads
✗ More efficient (less edge)
✗ Smart money actively trades

Low Liquidity Markets:
✓ More inefficiencies
✓ Less competition
✗ Hard to size positions
✗ Wide spreads eat profits
✗ Exit risk
```

### Finding the Sweet Spot

```
Optimal Market:
- Enough liquidity to enter/exit your position
- Inefficient enough to have edge
- Resolution timeline fits your strategy

Rule of thumb:
Position size < 5% of daily volume
Position size < 10% of total liquidity
```

### Implementation

```python
from polycli.selection.liquidity import LiquidityAnalyzer

analyzer = LiquidityAnalyzer(client)

# Analyze a market's tradability
analysis = await analyzer.analyze(market_id="abc123")

print(f"Daily volume: ${analysis.daily_volume:,.0f}")
print(f"Total liquidity: ${analysis.total_liquidity:,.0f}")
print(f"Spread: {analysis.spread:.2%}")
print(f"Max recommended position: ${analysis.max_position:,.0f}")
print(f"Slippage at $1000: {analysis.slippage_estimate(1000):.2%}")
```

### Liquidity Scoring

```
Liquidity Score (0-100):

Score = (Volume_score × 0.4) + (Depth_score × 0.3) +
        (Spread_score × 0.2) + (Activity_score × 0.1)

Where:
Volume_score = min(100, daily_volume / 10000 × 100)
Depth_score = min(100, order_book_depth / 5000 × 100)
Spread_score = max(0, 100 - spread_pct × 1000)
Activity_score = min(100, trades_per_hour × 10)
```

### CLI Usage

```bash
# Analyze market liquidity
polycli market liquidity MARKET_ID

# Find markets with good liquidity
polycli market list --min-liquidity 10000 --min-volume 5000

# Calculate max position for a market
polycli position max-size MARKET_ID
```

---

## Avoiding Coin Flips

### The Problem with 50/50 Markets

Markets near 50% are dangerous because:
1. **Minimal edge possible**: Even correct analysis yields small edge
2. **High variance**: Outcome is nearly random
3. **Hard to be confident**: Genuinely uncertain events

### Edge Requirements by Market Price

```
Market Price    Minimum Useful Edge    Why
10-20%         5%                      Low price = high potential return
20-40%         7%                      Moderate
40-60%         10%+                    Near 50% = need larger edge
60-80%         7%                      Moderate
80-90%         5%                      Low price for NO side
```

### Implementation

```python
from polycli.selection.filters import MarketFilter

filter = MarketFilter()

# Filter out markets too close to 50%
filter.add_rule(
    name="avoid_coinflips",
    condition=lambda m: abs(m.price - 0.5) > 0.1,  # At least 10% from 50%
)

# Apply filters
tradeable = [m for m in markets if filter.passes(m)]
```

### When 50/50 IS Worth Trading

1. **You have strong informational edge** (insider knowledge)
2. **Arbitrage opportunity** (price differs across platforms)
3. **Market is about to resolve** (and you know the outcome)

---

## Time Decay Considerations

### Theory

As markets approach resolution, dynamics change:

```
Timeline Effects:

Far from resolution (weeks/months):
- Prices can move significantly
- Edge has time to materialize
- Can average into position

Near resolution (hours/days):
- Prices converge to truth
- Edge must be acted on immediately
- Limited time to exit if wrong
```

### Time-Adjusted Position Sizing

```
Position Size Multiplier based on time:

Days to Resolution    Multiplier
> 30 days            1.0 (full position)
14-30 days           1.0
7-14 days            0.8
3-7 days             0.6
1-3 days             0.4
< 1 day              0.25 (minimal position)
```

### Implementation

```python
from polycli.selection.time_decay import TimeDecayAnalyzer

analyzer = TimeDecayAnalyzer()

# Analyze time characteristics
analysis = analyzer.analyze(
    resolution_date=market.resolution_date,
    current_price=Decimal("0.45"),
)

print(f"Days to resolution: {analysis.days_remaining}")
print(f"Time decay factor: {analysis.decay_factor:.2f}")
print(f"Size multiplier: {analysis.size_multiplier:.2f}")
print(f"Recommended action: {analysis.recommendation}")
```

### CLI Usage

```bash
# Check time decay for a market
polycli market time-decay MARKET_ID

# List markets by resolution date
polycli market list --sort-by resolution --resolving-soon 7
```

---

## Resolution Criteria Analysis

### Why Resolution Matters

Ambiguous resolution criteria lead to:
- Disputed outcomes
- Delayed resolution
- Unexpected results

### Resolution Red Flags

```
🚩 Red Flags:
- Subjective language ("significant", "major", "notable")
- Unclear data sources
- Self-referential criteria
- Edge cases not addressed

✅ Good Resolution:
- Objective, verifiable criteria
- Specific data sources named
- Edge cases explicitly handled
- Clear timeline
```

### Resolution Risk Scoring

```python
from polycli.selection.resolution import ResolutionAnalyzer

analyzer = ResolutionAnalyzer()

# Analyze resolution criteria
risk = analyzer.analyze(
    resolution_text=market.resolution_source,
    market_question=market.question,
)

print(f"Clarity score: {risk.clarity_score}/10")
print(f"Objectivity score: {risk.objectivity_score}/10")
print(f"Source reliability: {risk.source_score}/10")
print(f"Overall risk: {risk.overall_risk}")  # low/medium/high
print(f"Concerns: {risk.concerns}")
```

### Common Resolution Issues

| Issue | Example | Risk |
|-------|---------|------|
| Subjective criteria | "Major policy change" | High |
| Unclear timeline | "Eventually" | Medium |
| Single source | "Per CNN" | Medium |
| Self-fulfilling | Market determines outcome | Critical |
| Edge cases | "What if X but also Y?" | Medium |

### CLI Usage

```bash
# Analyze resolution criteria
polycli market resolution MARKET_ID

# Flag markets with resolution concerns
polycli market list --resolution-risk low
```

---

## Public Data Advantages

### Theory

Markets resolved by public data are more predictable because:
1. **Data is accessible** to all participants
2. **Historical patterns** can be analyzed
3. **Models can be validated** before betting

### Types of Public Data Markets

```
Strong Public Data (easier to model):
- Economic indicators (GDP, CPI, unemployment)
- Sports statistics
- Weather data
- Election polling

Weak Public Data (harder to model):
- Political decisions
- Court rulings
- Scientific discoveries
- Corporate announcements
```

### Building Data Advantages

```python
from polycli.selection.data_edge import DataEdgeFinder

finder = DataEdgeFinder()

# Register data sources you can access
finder.register_source(
    name="BLS Employment",
    update_frequency="monthly",
    lead_time="minutes before market",
    reliability=0.99,
)

# Find markets where you have data edge
opportunities = await finder.find_opportunities()

for opp in opportunities:
    print(f"Market: {opp.market_question}")
    print(f"Data source: {opp.data_source}")
    print(f"Your advantage: {opp.advantage_description}")
```

### Data Latency Edge

```
Publication Timeline:
00:00 - Data released (BLS, Fed, etc.)
00:01 - Fast traders react
00:05 - Most traders aware
00:30 - Fully priced in

Edge Window: 0-5 minutes
Decay: Exponential

Strategy:
- Pre-position based on models
- Or react within seconds of release
```

---

## Market Selection Framework

### Scoring System

```
Market Attractiveness Score (0-100):

Score = (Edge_score × 0.35) +
        (Liquidity_score × 0.25) +
        (Resolution_score × 0.20) +
        (Time_score × 0.10) +
        (Data_score × 0.10)

Trade if: Score > 60 AND Edge > minimum threshold
```

### Implementation

```python
from polycli.selection.framework import MarketSelector

selector = MarketSelector(client)

# Configure selection criteria
selector.set_criteria(
    min_edge=Decimal("0.05"),
    min_liquidity=Decimal("5000"),
    max_resolution_risk="medium",
    min_days_to_resolution=1,
)

# Scan and rank markets
candidates = await selector.scan_and_rank()

for market in candidates[:10]:
    print(f"Score: {market.score:.0f}")
    print(f"Market: {market.question}")
    print(f"Edge: {market.estimated_edge:.1%}")
    print(f"Liquidity: ${market.liquidity:,.0f}")
    print("---")
```

### CLI Usage

```bash
# Scan for tradeable markets with full analysis
polycli market scan \
    --min-edge 0.05 \
    --min-liquidity 5000 \
    --max-resolution-risk medium

# Daily opportunity scan
polycli market opportunities

# Export candidates to review
polycli market scan --export opportunities.csv
```

---

## Market Selection Checklist

Before entering any market:

1. ☐ **Edge Verified**
   - Can articulate specific advantage
   - Edge > minimum threshold for price level

2. ☐ **Liquidity Adequate**
   - Position < 5% of daily volume
   - Spread acceptable
   - Can exit if needed

3. ☐ **Resolution Clear**
   - Objective criteria
   - Reliable source
   - Timeline defined

4. ☐ **Timing Appropriate**
   - Enough time for edge to materialize
   - Not too close to resolution

5. ☐ **Data Advantage** (if applicable)
   - Access to relevant data
   - Faster or better analysis

```bash
# Run full market selection checklist
polycli market check MARKET_ID \
    --your-prob 0.60 \
    --proposed-size 500
```

---

**Next**: [Risk Management](./06-Risk-Management.md)

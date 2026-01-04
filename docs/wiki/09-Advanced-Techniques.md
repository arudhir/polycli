# Advanced Techniques

## Sophisticated Strategies for Experienced Traders

This section covers advanced strategies that require deeper market understanding and more sophisticated execution. Master the basics before attempting these techniques.

## Cross-Platform Arbitrage

### Theory

Arbitrage exploits price differences for the same event across platforms. In prediction markets:

```
True Arbitrage (Risk-Free):
Platform A: YES at $0.45
Platform B: NO at $0.45 (same event)
Total cost: $0.90
Guaranteed payout: $1.00
Risk-free profit: $0.10 (11.1% return)
```

### Types of Arbitrage

```
1. PURE ARBITRAGE
   - Same event, guaranteed prices
   - Risk-free (if execution is perfect)
   - Rare in liquid markets

2. STATISTICAL ARBITRAGE
   - Similar events, historical relationship
   - Positive expected value, not risk-free
   - More common

3. TEMPORAL ARBITRAGE
   - Same platform, different times
   - Exploit delayed price updates
   - Requires speed
```

### Implementation

```python
from polycli.advanced.arbitrage import ArbitrageFinder

finder = ArbitrageFinder()

# Register platforms
finder.register_platform("polymarket", polymarket_client)
finder.register_platform("manifold", manifold_client)
finder.register_platform("kalshi", kalshi_client)

# Scan for pure arbitrage opportunities
opportunities = await finder.find_pure_arbitrage(
    min_profit=Decimal("0.02"),  # At least 2% profit
    max_slippage=Decimal("0.01"),  # Max 1% slippage tolerance
)

for opp in opportunities:
    print(f"\n=== ARBITRAGE FOUND ===")
    print(f"Event: {opp.event_description}")
    print(f"Platform A: {opp.platform_a} - {opp.side_a} at {opp.price_a}")
    print(f"Platform B: {opp.platform_b} - {opp.side_b} at {opp.price_b}")
    print(f"Profit: {opp.profit_pct:.1%} (${opp.profit_usd:.2f} per $100)")
    print(f"Execution risk: {opp.execution_risk}")

# Scan for statistical arbitrage
stat_arb = await finder.find_statistical_arbitrage(
    correlation_threshold=0.9,  # 90%+ correlated events
    min_spread=Decimal("0.05"),  # 5%+ price difference
)
```

### Execution Challenges

```
Challenge           Mitigation
────────────────────────────────────────────
Execution risk      Parallel execution, slippage buffers
Different fees      Factor fees into profit calculation
Liquidity limits    Size to minimum liquidity
Settlement risk     Use trusted platforms only
Capital lockup      Account for time value of money
```

### CLI Usage

```bash
# Scan for arbitrage opportunities
polycli advanced arbitrage-scan

# With filters
polycli advanced arbitrage-scan \
    --min-profit 0.03 \
    --platforms polymarket,manifold

# Execute arbitrage (careful!)
polycli advanced arbitrage-execute OPP_ID --size 500
```

---

## Synthetic Positions

### Theory

Synthetic positions replicate exposures that may not be directly available:

```
Synthetic Long YES = Long NO on opposite outcome
Synthetic Short = Sell existing long position

More complex:
Synthetic strangle = Long YES near current price + Long NO near current price
                   (Profits from large moves in either direction)
```

### Synthetic Constructions

```python
from polycli.advanced.synthetic import SyntheticBuilder

builder = SyntheticBuilder(client)

# Create synthetic exposure
synthetic = await builder.create_synthetic(
    target_exposure="long_volatility",
    market_id="abc123",
    notional=Decimal("1000"),
)

print(f"Synthetic position: {synthetic.name}")
print(f"Components:")
for leg in synthetic.legs:
    print(f"  {leg.side} {leg.size} shares at {leg.price}")
print(f"Net cost: ${synthetic.net_cost:.2f}")
print(f"Max profit: ${synthetic.max_profit:.2f}")
print(f"Max loss: ${synthetic.max_loss:.2f}")
```

### Common Synthetic Strategies

```
1. VOLATILITY PLAY (Straddle/Strangle)
   When: You expect big move but unsure of direction
   Construction: Long YES + Long NO at same strike
   Profit: If price moves far from 50%

   Example:
   Market at 50%
   Buy YES at 50%: Cost $500
   Buy NO at 50%: Cost $500
   Total cost: $1000

   Outcome YES wins: Get $1000 from YES
   Outcome NO wins: Get $1000 from NO
   Break-even: Already at break-even!
   Profit: If you can sell at better prices before resolution

2. RANGE PLAY
   When: You expect price to stay in a range
   Construction: Sell YES above range, sell NO below range
   Profit: If price stays in range (collect premium)

3. CALENDAR SPREAD (across resolution dates)
   When: Related markets with different timelines
   Construction: Long near-term, short far-term
   Profit: If near-term resolves favorably
```

### CLI Usage

```bash
# Analyze synthetic opportunities
polycli advanced synthetic-analyze MARKET_ID

# Create synthetic position
polycli advanced synthetic-create \
    --market MARKET_ID \
    --type straddle \
    --notional 1000

# List active synthetics
polycli advanced synthetic-list
```

---

## Liquidity Provision (Market Making)

### Theory

Market makers provide liquidity by posting both buy and sell orders, profiting from the spread:

```
Market Maker Posts:
Bid: Buy YES at $0.48
Ask: Sell YES at $0.52

When orders fill:
Buy from seller at $0.48
Sell to buyer at $0.52
Profit: $0.04 per share (spread capture)

Risk:
- Adverse selection (informed traders trade against you)
- Inventory risk (stuck with losing position)
- Volatility risk (prices move against your inventory)
```

### Market Making Mathematics

```
Expected Profit = (Spread × Volume) - (Adverse Selection Cost) - (Inventory Risk)

Optimal Spread Width:
Narrow spread → More volume, more adverse selection risk
Wide spread → Less volume, less risk

Factors in spread:
- Volatility (higher vol → wider spread)
- Inventory (more inventory → skew quotes)
- Competition (more MMs → tighter spreads)
- Time to resolution (closer → tighter)
```

### Implementation

```python
from polycli.advanced.market_making import MarketMaker

mm = MarketMaker(
    client=client,
    market_id="abc123",
    spread=Decimal("0.04"),  # 4% spread
    inventory_limit=Decimal("2000"),
)

# Set fair value estimate
mm.set_fair_value(Decimal("0.50"))

# Calculate optimal quotes
quotes = mm.calculate_quotes(
    current_inventory=Decimal("500"),  # Already long $500
)

print(f"Fair value: {mm.fair_value}")
print(f"Bid: {quotes.bid_price} ({quotes.bid_size} shares)")
print(f"Ask: {quotes.ask_price} ({quotes.ask_size} shares)")

# Skew explanation
print(f"Quote skew: {quotes.skew:+.2%}")  # Negative = lower bid (reduce long inventory)

# Start market making
await mm.start(
    max_orders=10,
    refresh_interval=60,
    stop_loss_pct=Decimal("0.10"),
)
```

### Inventory Management

```python
# Inventory risk management
from polycli.advanced.market_making import InventoryManager

inv_mgr = InventoryManager(
    target_inventory=Decimal("0"),
    max_inventory=Decimal("2000"),
    skew_factor=Decimal("0.5"),  # How much to skew quotes per unit inventory
)

# Calculate quote adjustments based on inventory
adjustment = inv_mgr.get_adjustment(current_inventory=Decimal("1000"))
print(f"Bid adjustment: {adjustment.bid_adjust:+.1%}")  # Lower bid to reduce longs
print(f"Ask adjustment: {adjustment.ask_adjust:+.1%}")  # No change or lower to sell
```

### CLI Usage

```bash
# Analyze market making opportunity
polycli advanced mm-analyze MARKET_ID

# Start market making (paper mode first!)
polycli advanced mm-start MARKET_ID \
    --spread 0.04 \
    --max-inventory 2000 \
    --paper-mode

# View market making P&L
polycli advanced mm-pnl

# Stop market making
polycli advanced mm-stop
```

---

## News Reaction Strategy

### Theory

React to breaking news faster than the market adjusts:

```
Timeline:
T+0s:   News breaks
T+5s:   Fast traders react
T+30s:  Most aware
T+300s: Fully priced in

Edge window: 0-30 seconds
Decay: Exponential
```

### News Categories

```
Category          Impact Speed    Predictability
──────────────────────────────────────────────────
Scheduled data    Immediate       High (known time)
Announcements     Immediate       Medium
Rumors            Gradual         Low
Trends            Slow            High
```

### Implementation

```python
from polycli.advanced.news import NewsReactor

reactor = NewsReactor()

# Configure news sources
reactor.add_source(
    name="Official Announcements",
    type="rss",
    url="https://...",
    keywords=["federal reserve", "interest rate"],
    priority=1,
)

reactor.add_source(
    name="Twitter Key Accounts",
    type="twitter",
    accounts=["@federalreserve", "@NickTimiraos"],
    priority=1,
)

# Define reaction rules
reactor.add_rule(
    trigger=lambda news: "rate hike" in news.text.lower(),
    action="check_fed_markets",
    markets=["fed_rate_decision"],
    urgency="high",
)

# Start monitoring
async for news_event in reactor.monitor():
    print(f"NEWS: {news_event.headline}")
    print(f"Affected markets: {news_event.affected_markets}")
    print(f"Suggested action: {news_event.suggested_action}")

    # Execute if conditions met
    if news_event.urgency == "high" and news_event.confidence > 0.8:
        await reactor.execute_action(news_event)
```

### Pre-Positioning Strategy

```python
from polycli.advanced.news import PrePositioner

positioner = PrePositioner(client)

# For scheduled events (earnings, data releases, etc.)
plan = positioner.create_plan(
    event="Fed Rate Decision",
    event_time="2024-01-30 14:00",
    scenarios=[
        {
            "name": "rate_hike",
            "probability": Decimal("0.30"),
            "market_impact": {"fed_funds": +Decimal("0.10")},
        },
        {
            "name": "hold",
            "probability": Decimal("0.60"),
            "market_impact": {"fed_funds": Decimal("0")},
        },
        {
            "name": "rate_cut",
            "probability": Decimal("0.10"),
            "market_impact": {"fed_funds": -Decimal("0.15")},
        },
    ],
)

print(f"Event: {plan.event}")
print(f"Expected value of pre-position: ${plan.ev:.2f}")
print(f"Recommended position: {plan.recommendation}")
```

### CLI Usage

```bash
# Monitor for breaking news
polycli advanced news-monitor

# Pre-position for scheduled event
polycli advanced pre-position \
    --event "Fed Decision" \
    --time "2024-01-30 14:00" \
    --scenarios fed_scenarios.json

# View news impact history
polycli advanced news-history
```

---

## Order Flow Analysis

### Theory

Order flow reveals trading intentions:

```
Signals in order flow:
- Large orders: Informed traders or whales
- Aggressive orders: Urgency, likely informed
- Passive orders: Market makers, less informative
- Order clustering: Coordinated activity
```

### Implementation

```python
from polycli.advanced.orderflow import OrderFlowAnalyzer

analyzer = OrderFlowAnalyzer(client)

# Analyze recent order flow
flow = await analyzer.analyze(
    market_id="abc123",
    lookback_minutes=60,
)

print(f"Net flow: {flow.net_direction} ${flow.net_amount:,.0f}")
print(f"Aggressor ratio: {flow.aggressor_ratio:.1%}")
print(f"Large order count: {flow.large_order_count}")
print(f"Imbalance: {flow.imbalance:+.2f}")

# Detect patterns
patterns = await analyzer.detect_patterns()
for pattern in patterns:
    print(f"Pattern: {pattern.name}")
    print(f"Confidence: {pattern.confidence:.0%}")
    print(f"Implication: {pattern.implication}")
```

### Order Flow Indicators

```
1. DELTA
   = Aggressive buys - Aggressive sells
   Positive delta → Buying pressure

2. CUMULATIVE DELTA
   = Running sum of delta
   Rising → Sustained buying

3. VOLUME PROFILE
   = Volume at each price level
   High volume nodes → Support/Resistance

4. IMBALANCE
   = (Bid size - Ask size) / (Bid size + Ask size)
   Range: -1 to +1
```

### CLI Usage

```bash
# Analyze order flow
polycli advanced orderflow MARKET_ID

# Real-time order flow monitor
polycli advanced orderflow-monitor MARKET_ID

# Historical order flow
polycli advanced orderflow-history MARKET_ID --hours 24
```

---

## Risk Considerations for Advanced Strategies

### Complexity Risk

```
More moving parts = More failure modes

Risks:
- Execution failures
- Model errors
- Platform issues
- Unexpected correlations
- Liquidity gaps
```

### Sizing Advanced Strategies

```
Rule: Size advanced strategies at 50% or less of normal

Reasons:
- Higher uncertainty
- More complex risks
- Need room for error
- Learning curve costs
```

### Paper Trading First

```python
from polycli.advanced.paper import PaperTrader

paper = PaperTrader()

# Simulate arbitrage strategy
results = await paper.simulate(
    strategy="arbitrage",
    duration_days=30,
    initial_capital=Decimal("10000"),
)

print(f"Strategy: {results.strategy}")
print(f"Trades: {results.total_trades}")
print(f"Profit: ${results.total_profit:.2f}")
print(f"Sharpe: {results.sharpe_ratio:.2f}")
print(f"Max drawdown: {results.max_drawdown:.1%}")
print(f"Issues encountered: {results.issues}")
```

### CLI Usage

```bash
# Enable paper trading mode
polycli config set mode paper

# Run strategy in paper mode
polycli advanced mm-start MARKET_ID --paper-mode

# View paper trading results
polycli paper-results
```

---

## When to Use Advanced Techniques

### Prerequisites

```
Before attempting advanced strategies:

☐ Consistent profitability with basic strategies
☐ Full understanding of the mechanics
☐ Proper tooling and automation
☐ Risk management in place
☐ Capital you can afford to lose on learning
☐ Paper traded the strategy successfully
```

### Strategy Selection Guide

```
Arbitrage:
- Good for: Capital efficiency, risk-averse
- Requires: Multi-platform access, fast execution
- Risk: Execution, capital lockup

Synthetic Positions:
- Good for: Expressing complex views
- Requires: Understanding of options-like payoffs
- Risk: Complexity, fees

Market Making:
- Good for: Consistent income, range-bound markets
- Requires: Automation, capital for inventory
- Risk: Adverse selection, inventory

News Reaction:
- Good for: Informed traders, fast execution
- Requires: News infrastructure, quick decision making
- Risk: Wrong interpretation, late reaction
```

---

**Previous**: [Psychology and Improvement](./08-Psychology.md)

**Return to**: [Home](./Home.md)

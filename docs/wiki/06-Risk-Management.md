# Risk Management

## Protecting Your Bankroll

Risk management isn't about avoiding risk—it's about taking the right risks in the right amounts. This section covers strategies to protect capital while maximizing returns.

## Asymmetric Hedging

### Theory

Most hedging eliminates upside along with downside. Asymmetric hedging maintains upside while limiting downside:

```
Traditional Hedge:
Long YES at 50%
Short YES at 50%
Net: Zero exposure, zero profit potential

Asymmetric Hedge:
Long YES at 50% (primary position)
Small Long NO at 50% (insurance)
Net: Capped downside, maintained upside
```

### The Mathematics

```
Position A: Long YES, $1000 at 50%
Position B: Long NO, $200 at 50%

Scenarios:
YES wins: +$1000 - $200 = $800 profit
NO wins:  -$1000 + $200 = -$800 loss

After hedge:
YES wins: +$1000 - $200 = $800 profit
NO wins:  -$1000 + $400 = -$600 loss

Cost of hedge: $200
Downside reduced: $200 (from -$800 to -$600)
Upside maintained: Most of original
```

### When to Hedge

```
Hedge when:
- Position is large relative to bankroll
- Uncertainty has increased
- Want to lock in partial profits
- Event has binary catastrophic outcome

Don't hedge when:
- Position is small
- Edge is strong and unchanged
- Hedge cost exceeds benefit
```

### Implementation

```python
from polycli.risk.hedging import HedgeCalculator

calc = HedgeCalculator()

# Calculate optimal hedge
hedge = calc.calculate_hedge(
    primary_position=Decimal("1000"),
    primary_side="yes",
    current_price=Decimal("0.60"),
    max_acceptable_loss=Decimal("500"),
)

print(f"Hedge size: ${hedge.hedge_size:.2f}")
print(f"Hedge cost: ${hedge.cost:.2f}")
print(f"Max loss after hedge: ${hedge.max_loss:.2f}")
print(f"Upside remaining: ${hedge.remaining_upside:.2f}")
print(f"Breakeven: {hedge.breakeven_price:.1%}")
```

### CLI Usage

```bash
# Calculate hedge for a position
polycli risk hedge \
    --position 1000 \
    --side yes \
    --current-price 0.60 \
    --max-loss 500

# View suggested hedges for all positions
polycli risk hedge-suggestions
```

---

## Limit Orders for Risk Control

### Theory

Limit orders provide risk control by:
1. **Locking in entries** at acceptable prices
2. **Automating exits** at profit targets
3. **Stopping losses** without emotion

### Order Types

```
Entry Orders:
- Limit Buy: Enter if price drops to target
- Scale-in: Multiple limits at decreasing prices

Exit Orders:
- Take Profit: Sell at profit target
- Stop Loss: Exit if price moves against
- Trailing Stop: Dynamic stop that follows price up
```

### Implementation

```python
from polycli.risk.orders import OrderManager

manager = OrderManager(client)

# Place a limit entry order
entry_order = await manager.place_limit_order(
    market_id="abc123",
    side="buy",
    price=Decimal("0.45"),
    size=Decimal("500"),
    time_in_force="GTC",  # Good til cancelled
)

# Set up take profit and stop loss
await manager.create_bracket(
    position_id=position.id,
    take_profit=Decimal("0.70"),  # Sell if YES reaches 70%
    stop_loss=Decimal("0.35"),    # Sell if YES drops to 35%
)

# Trailing stop
await manager.create_trailing_stop(
    position_id=position.id,
    trail_percent=Decimal("0.10"),  # 10% trailing stop
)
```

### Order Strategy Examples

```
Conservative Entry:
- Limit buy at 5% below current price
- Scale in: 33% at current, 33% at -5%, 34% at -10%

Profit Taking:
- 25% at 1.5x target
- 25% at 2x target
- 50% ride to resolution

Stop Loss:
- Hard stop at -20% from entry
- Or stop at price where thesis invalidated
```

### CLI Usage

```bash
# Place limit order
polycli order limit-buy \
    --market MARKET_ID \
    --price 0.45 \
    --size 500

# Set bracket orders (take profit + stop loss)
polycli order bracket \
    --position POSITION_ID \
    --take-profit 0.70 \
    --stop-loss 0.35

# View all open orders
polycli order list
```

---

## Drawdown Management

### Theory

Drawdown is the peak-to-trough decline in portfolio value. Managing drawdown:
- Preserves capital for future opportunities
- Maintains psychological stability
- Prevents catastrophic losses

### Drawdown Metrics

```
Current Drawdown = (Peak - Current) / Peak

Example:
Peak value: $10,000
Current value: $8,000
Drawdown: ($10,000 - $8,000) / $10,000 = 20%
```

### Maximum Acceptable Drawdown

```
Conservative: 15%
Moderate: 25%
Aggressive: 40%

Recovery requirements:
10% drawdown → Need 11% gain to recover
20% drawdown → Need 25% gain to recover
30% drawdown → Need 43% gain to recover
50% drawdown → Need 100% gain to recover
```

### Implementation

```python
from polycli.risk.drawdown import DrawdownManager

manager = DrawdownManager(
    peak_value=Decimal("10000"),
    max_acceptable_drawdown=Decimal("0.25"),
)

# Update with current value
current = Decimal("8500")
status = manager.update(current)

print(f"Current drawdown: {status.drawdown:.1%}")
print(f"Remaining until max: {status.remaining:.1%}")
print(f"Action required: {status.action_required}")

# Get position sizing multiplier
multiplier = manager.get_sizing_multiplier()
print(f"Size positions at: {multiplier:.0%} of normal")
```

### Drawdown Response Rules

```
Drawdown Level    Response
< 10%            Normal trading
10-15%           Reduce position sizes 25%
15-20%           Reduce position sizes 50%
20-25%           New positions only, no additions
> 25%            Stop trading, review strategy
```

### CLI Usage

```bash
# Check drawdown status
polycli risk drawdown \
    --portfolio-value 8500 \
    --peak-value 10000 \
    --max-acceptable 0.25

# View drawdown history
polycli risk drawdown-history

# Set drawdown alerts
polycli alerts drawdown --threshold 0.15
```

---

## Portfolio Diversification

### Theory

Diversification reduces risk without sacrificing expected return:

```
Single position risk: High variance
Multiple uncorrelated positions: Lower variance, same expected return

Portfolio variance = Σ(wi² × σi²) + Σ(wi × wj × σi × σj × ρij)

Where correlation ρ < 1, portfolio risk < sum of individual risks
```

### Diversification Dimensions

```
1. Event Type:
   - Political
   - Sports
   - Crypto
   - Economic

2. Geography:
   - US elections
   - EU policy
   - Global events

3. Timeframe:
   - Short-term (days)
   - Medium-term (weeks)
   - Long-term (months)

4. Correlation:
   - Uncorrelated events
   - Negatively correlated (natural hedges)
```

### Implementation

```python
from polycli.risk.diversification import DiversificationAnalyzer

analyzer = DiversificationAnalyzer()

# Analyze current portfolio
analysis = analyzer.analyze_portfolio(positions)

print(f"Concentration score: {analysis.concentration:.0f}/100")
print(f"Largest position: {analysis.largest_position_pct:.1%}")
print(f"Correlation risk: {analysis.correlation_risk}")

# By category
for category, pct in analysis.by_category.items():
    print(f"{category}: {pct:.1%}")

# Recommendations
for rec in analysis.recommendations:
    print(f"- {rec}")
```

### Diversification Rules

```
Position Limits:
- Single position: < 10% of portfolio
- Correlated group: < 20% of portfolio
- Single category: < 40% of portfolio

Minimum Positions:
- 5+ for minimal diversification
- 10+ for good diversification
- 20+ for excellent diversification
```

### CLI Usage

```bash
# Analyze portfolio diversification
polycli risk diversification

# Check if new position hurts diversification
polycli risk diversity-check --market MARKET_ID --size 500

# Suggest diversifying positions
polycli risk diversify-suggestions
```

---

## Exit Strategy

### Theory

Every entry should have a planned exit:

```
Exit Triggers:
1. Profit target reached
2. Stop loss triggered
3. Thesis invalidated
4. Better opportunity found
5. Time-based exit (resolution approaching)
6. Risk limit hit (drawdown, correlation)
```

### Exit Planning

```python
from polycli.risk.exit import ExitPlanner

planner = ExitPlanner()

# Create exit plan when entering position
exit_plan = planner.create_plan(
    entry_price=Decimal("0.45"),
    position_size=Decimal("1000"),
    thesis="Polling underweights demographic shift",
    # Profit targets
    target_1=Decimal("0.60"),  # Exit 33%
    target_2=Decimal("0.75"),  # Exit 33%
    target_3=None,             # Hold 34% to resolution
    # Stop loss
    stop_loss=Decimal("0.35"),
    # Thesis invalidation
    invalidation_conditions=[
        "New polling methodology accounts for demographic",
        "Candidate withdraws",
    ],
)

print(f"Exit plan ID: {exit_plan.id}")
print(f"Expected value: ${exit_plan.expected_value:.2f}")
```

### Exit Decision Framework

```
Should I exit?

1. Has thesis changed?
   YES → Exit or reduce
   NO → Continue

2. Has price reached target?
   YES → Take profits (at least partial)
   NO → Continue

3. Has stop loss triggered?
   YES → Exit (no exceptions)
   NO → Continue

4. Is there a better opportunity?
   YES → Compare EVs, reallocate if warranted
   NO → Hold

5. Is risk tolerance exceeded?
   YES → Reduce position
   NO → Hold
```

### CLI Usage

```bash
# Create exit plan for position
polycli position exit-plan \
    --position POSITION_ID \
    --targets 0.60,0.75 \
    --stop-loss 0.35

# Check if any exits are triggered
polycli position check-exits

# View all exit plans
polycli position exit-plans
```

---

## Risk Management Dashboard

### Real-Time Monitoring

```python
from polycli.tools.dashboard import RiskDashboard

dashboard = RiskDashboard(client)

# Get current risk snapshot
snapshot = await dashboard.get_snapshot()

print("=== RISK DASHBOARD ===")
print(f"Portfolio Value: ${snapshot.portfolio_value:,.2f}")
print(f"Current Drawdown: {snapshot.drawdown:.1%}")
print(f"At-Risk Amount: ${snapshot.at_risk:,.2f}")
print(f"Correlation Score: {snapshot.correlation_score:.0f}/100")
print(f"Diversification: {snapshot.diversification_score:.0f}/100")

print("\n=== ALERTS ===")
for alert in snapshot.alerts:
    print(f"⚠️ {alert.message}")

print("\n=== POSITIONS ===")
for pos in snapshot.positions:
    print(f"{pos.market[:30]}: {pos.side} ${pos.size:.0f} @ {pos.entry_price:.1%}")
```

### CLI Usage

```bash
# View risk dashboard
polycli risk dashboard

# Set up risk alerts
polycli alerts set \
    --drawdown 0.15 \
    --position-size 1000 \
    --correlation 0.8

# Continuous monitoring
polycli risk monitor --refresh 60
```

---

## Risk Management Checklist

Before trading:

1. ☐ **Drawdown Check**
   - Current drawdown within limits
   - Sizing adjusted for drawdown level

2. ☐ **Position Limits**
   - Single position < 10% portfolio
   - Correlated positions < 20%

3. ☐ **Exit Plan**
   - Profit targets defined
   - Stop loss set
   - Invalidation conditions listed

4. ☐ **Diversification**
   - Not overweight any category
   - Correlation analyzed

5. ☐ **Hedging** (if applicable)
   - Large positions hedged
   - Hedge cost acceptable

---

**Next**: [Tools and Automation](./07-Tools-and-Automation.md)

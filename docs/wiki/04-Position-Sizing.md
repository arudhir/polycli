# Position Sizing

## The Mathematics of Optimal Betting

Position sizing determines how much to risk on each trade. It's arguably more important than finding edge—poor sizing can turn a winning strategy into bankruptcy.

## The Kelly Criterion

### History and Theory

Developed by John Kelly at Bell Labs in 1956, the Kelly Criterion answers: "How much should I bet to maximize long-term wealth growth?"

The key insight: **Maximize the expected logarithm of wealth**, not expected wealth itself.

### Why Logarithm?

```
Linear utility: Treats $1M → $2M same as $0 → $1M
Log utility: Treats $1M → $2M same as $100 → $200 (doubling)

Log utility:
✓ Prevents ruin (ln(0) = -∞)
✓ Compounds optimally over time
✓ Matches human risk perception
```

### The Formula

For a binary bet with:
- `p` = probability of winning
- `q` = probability of losing (1 - p)
- `b` = odds (payout per unit bet if you win)

```
Kelly Fraction f* = (p × b - q) / b

Simplified for prediction markets where you buy at price m:
- Win payout: (1 - m) per share
- Odds b = (1 - m) / m

f* = (p - m) / (1 - m)

Where:
- p = your probability estimate
- m = market price (implied probability)
```

### Example Calculation

```
Market: "Will bill pass?" at $0.40 (40%)
Your estimate: 55%

f* = (0.55 - 0.40) / (1 - 0.40)
f* = 0.15 / 0.60
f* = 0.25 (25% of bankroll)

With $10,000 bankroll:
Bet size = $10,000 × 0.25 = $2,500
```

### Implementation

```python
from decimal import Decimal
from polycli.position.kelly import KellyCalculator, KellyFraction

# Initialize with bankroll
calc = KellyCalculator(bankroll=Decimal("10000"))

# Calculate optimal bet
result = calc.calculate(
    win_probability=Decimal("0.55"),
    market_price=Decimal("0.40"),
    kelly_fraction=KellyFraction.QUARTER,  # Use quarter Kelly
)

print(f"Edge: {result.edge:.1%}")                    # 15%
print(f"Full Kelly: {result.full_kelly_fraction:.1%}") # 25%
print(f"Quarter Kelly: {result.recommended_fraction:.1%}") # 6.25%
print(f"Bet size: ${result.recommended_bet_size:.2f}")  # $625
print(f"Expected value: ${result.expected_value:.2f}")
```

### CLI Usage

```bash
polycli position kelly \
    --bankroll 10000 \
    --win-prob 0.55 \
    --market-price 0.40 \
    --fraction quarter

# Output:
# Edge: 15.0%
# Full Kelly: 25.0%
# Recommended (quarter): 6.25%
# Bet size: $625.00
# Positive EV trade
```

---

## Fractional Kelly

### Why Not Full Kelly?

Full Kelly maximizes long-term growth but:
1. **Assumes perfect probability estimates** (you'll be wrong)
2. **High variance** in short term
3. **Psychological difficulty** of large drawdowns
4. **Model uncertainty** isn't accounted for

### Kelly Fractions

| Fraction | Multiplier | Use Case |
|----------|------------|----------|
| Full | 1.0 | Only with high-confidence edges |
| Half | 0.5 | Strong conviction, experienced |
| Quarter | 0.25 | **Recommended default** |
| Eighth | 0.125 | Uncertain estimates, learning |

### Mathematical Justification

```
Expected Growth Rate G(f) = p × ln(1 + f×b) + q × ln(1 - f)

At f* (full Kelly): G(f*) is maximized
At f*/2 (half Kelly): G(f*/2) ≈ 0.75 × G(f*)
At f*/4 (quarter Kelly): G(f*/4) ≈ 0.5 × G(f*)

Key insight: Half the bet size gives 75% of the growth rate
            with much lower variance and drawdown risk
```

### Implementation

```python
# Compare different Kelly fractions
for fraction in [KellyFraction.FULL, KellyFraction.HALF,
                 KellyFraction.QUARTER, KellyFraction.EIGHTH]:
    result = calc.calculate(
        win_probability=Decimal("0.60"),
        market_price=Decimal("0.45"),
        kelly_fraction=fraction,
    )
    print(f"{fraction.name}: {result.recommended_fraction:.1%} = ${result.recommended_bet_size:.0f}")
```

---

## Correlated Position Management

### The Problem

Standard Kelly assumes independent bets. In practice:
- Multiple bets on related outcomes
- Portfolio-level risk compounds
- Correlated losses can devastate

### Correlation-Adjusted Sizing

```python
from polycli.position.correlation import CorrelatedPositionManager

manager = CorrelatedPositionManager(bankroll=Decimal("10000"))

# Add positions with correlation estimates
manager.add_position(
    market_id="election_primary",
    size=Decimal("500"),
    side="yes",
    correlation_group="election",
)

manager.add_position(
    market_id="election_general",
    size=Decimal("500"),
    side="yes",
    correlation_group="election",  # Same group = correlated
)

# Check effective exposure
exposure = manager.calculate_effective_exposure()
print(f"Nominal exposure: ${exposure.nominal}")     # $1000
print(f"Effective exposure: ${exposure.effective}") # Higher due to correlation

# Get sizing recommendation
recommendation = manager.get_sizing_recommendation(
    new_market_id="election_policy",
    proposed_size=Decimal("500"),
    correlation_group="election",
)
print(f"Recommended size: ${recommendation.adjusted_size}")
```

### Correlation Groups

```
High Correlation (0.7-1.0):
- Same candidate, different races
- Related policy outcomes
- Same-day resolution markets

Medium Correlation (0.3-0.7):
- Same sector/theme
- Temporal dependencies

Low/No Correlation (0-0.3):
- Unrelated events
- Different domains
```

### CLI Usage

```bash
# Check correlation-adjusted exposure
polycli position exposure

# Get sizing with correlation adjustment
polycli position size-check \
    --market MARKET_ID \
    --proposed-size 500 \
    --correlation-group election
```

---

## Reserve Management

### Theory

Never bet your entire bankroll. Reserves:
- Protect against total loss
- Provide capital for future opportunities
- Enable averaging into positions

### Reserve Framework

```
Total Capital: $10,000
├── Trading Bankroll (70%): $7,000
│   ├── Active positions
│   └── Available for new trades
├── Opportunity Reserve (20%): $2,000
│   └── For exceptional edges (>20%)
└── Emergency Reserve (10%): $1,000
    └── Never trade with this
```

### Implementation

```python
from polycli.position.reserve import ReserveManager

reserves = ReserveManager(total_capital=Decimal("10000"))

# Configure reserve percentages
reserves.set_reserves(
    trading=Decimal("0.70"),      # 70% for regular trading
    opportunity=Decimal("0.20"),  # 20% for big opportunities
    emergency=Decimal("0.10"),    # 10% never touched
)

# Check available capital for a trade
available = reserves.get_available_capital(
    include_opportunity=False,  # Regular trade
)
print(f"Available: ${available}")  # $7,000

# For exceptional opportunity
big_available = reserves.get_available_capital(
    include_opportunity=True,
    edge_threshold_met=True,  # Edge > 20%
)
print(f"With opportunity reserve: ${big_available}")  # $9,000
```

### CLI Usage

```bash
# View reserve status
polycli position reserves

# Reconfigure reserves
polycli position set-reserves --trading 0.70 --opportunity 0.20 --emergency 0.10
```

---

## Scaling In and Out

### Theory

Rather than entering/exiting all at once:
- **Scaling in**: Build position over time, average entry price
- **Scaling out**: Lock in profits, let winners run

### Scaling Strategies

```
Scale In:
Entry 1: 33% at current price
Entry 2: 33% if price improves by 5%+
Entry 3: 34% if thesis confirmed

Scale Out:
Exit 1: 33% at 2x target
Exit 2: 33% at 3x target
Exit 3: 34% ride to resolution
```

### Implementation

```python
from polycli.position.scaling import ScalingStrategy

# Create a scaling plan
strategy = ScalingStrategy(
    total_position=Decimal("1000"),
    entries=3,
    exits=3,
)

# Define entry levels
strategy.set_entry_levels([
    {"percent": 33, "condition": "immediate"},
    {"percent": 33, "condition": "price_drop_5"},
    {"percent": 34, "condition": "thesis_confirmed"},
])

# Define exit levels
strategy.set_exit_levels([
    {"percent": 33, "price_target": Decimal("0.60")},
    {"percent": 33, "price_target": Decimal("0.75")},
    {"percent": 34, "condition": "resolution"},
])

# Get current action
action = strategy.get_next_action(current_price=Decimal("0.45"))
print(f"Action: {action.type} {action.size} shares")
```

---

## Expected Value Tracking

### Why Track EV Separately from P&L?

```
Scenario: You make 10 positive EV bets
Expected profit: $1,000
Actual results: -$200 (bad variance)

Without EV tracking: "My strategy is broken"
With EV tracking: "Running $1,200 below expectation—variance"

EV tracking separates:
- Decision quality (did you have edge?)
- Outcome quality (did you win?)
```

### Implementation

```python
from polycli.position.ev_tracker import EVTracker

tracker = EVTracker()

# Record decision BEFORE outcome known
decision_id = tracker.record_decision(
    market_id="abc123",
    market_question="Will X happen?",
    estimated_probability=Decimal("0.60"),
    market_price=Decimal("0.45"),
    position_size=Decimal("500"),
    confidence=7,
    thesis="Analysis suggests higher probability",
)

# Expected value calculated automatically
# EV = position_size × (est_prob - market_price) / (1 - market_price)

# After resolution
tracker.resolve_decision(
    decision_id=decision_id,
    outcome="win",  # or "lose"
    actual_pnl=Decimal("300"),
    post_mortem="Thesis was correct",
)

# Analyze performance
stats = tracker.get_stats()
print(f"Total EV expected: ${stats.total_ev_expected:.2f}")
print(f"Total actual P&L: ${stats.total_actual_pnl:.2f}")
print(f"Variance: ${stats.total_actual_pnl - stats.total_ev_expected:.2f}")
print(f"Positive EV accuracy: {stats.positive_ev_accuracy:.1%}")
```

### CLI Usage

```bash
# Record a new decision
polycli ev record \
    --market abc123 \
    --your-prob 0.60 \
    --market-price 0.45 \
    --size 500 \
    --thesis "Analysis suggests higher probability"

# Resolve after outcome known
polycli ev resolve DECISION_ID --outcome win --pnl 300

# View EV statistics
polycli ev stats

# Compare EV to actual performance
polycli ev variance-analysis
```

---

## Position Sizing Mistakes

### 1. Sizing on Conviction, Not Edge

```
Wrong: "I'm confident, so I'll bet big"
Right: "Edge is 15%, Kelly says 25%, I'll bet 6.25%"

Conviction without edge = gambling
```

### 2. Ignoring Correlation

```
Wrong: Five $1,000 bets on related outcomes
        Effective risk: ~$3,500 (correlated)
Right: Account for correlation, size down
```

### 3. No Reserves

```
Wrong: All capital in active positions
        New opportunity appears: can't act
Right: Keep 20-30% for opportunities
```

### 4. Emotional Sizing

```
Wrong: Double down after loss ("I'll win it back")
Right: Systematic sizing based on edge and bankroll
```

---

## Position Sizing Checklist

Before every trade:

1. ☐ Calculate edge (your prob - market price)
2. ☐ Run Kelly calculation
3. ☐ Apply fractional Kelly (start with 1/4)
4. ☐ Check correlation with existing positions
5. ☐ Verify sufficient reserves
6. ☐ Record EV before execution
7. ☐ Set scaling plan if applicable

```bash
# All-in-one sizing check
polycli position calculate \
    --market MARKET_ID \
    --your-prob 0.55 \
    --check-correlation \
    --check-reserves
```

---

**Next**: [Market Selection](./05-Market-Selection.md)

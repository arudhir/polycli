# Expected Value and Edge

## The Foundation of Profitable Trading

Expected Value (EV) is the mathematical foundation of all profitable trading. Understanding EV separates gamblers from traders.

## What is Expected Value?

Expected Value is the average outcome you'd expect over many repetitions of the same bet.

### Formula

```
EV = Σ (Probability × Outcome)

For binary markets:
EV = (P_win × Payout_win) + (P_lose × Payout_lose)
```

### Example Calculation

```
Market: "Will bill pass Congress?"
Market price: $0.40 (40% implied probability)
Your estimate: 55%

If you buy YES at $0.40:
- Win: You get $1.00, profit = $0.60
- Lose: You get $0.00, loss = $0.40

EV = (0.55 × $0.60) + (0.45 × -$0.40)
EV = $0.33 - $0.18
EV = +$0.15 per share

For a $1,000 position (2,500 shares):
Expected profit = 2,500 × $0.15 = $375
```

## What is Edge?

Edge is the difference between your probability estimate and the market's implied probability.

```
Edge = Your_Probability - Market_Price

Positive edge → Market underprices the outcome → BUY
Negative edge → Market overprices the outcome → SELL/SHORT
```

### Edge Categories

| Edge Size | Classification | Typical Action |
|-----------|---------------|----------------|
| < 3% | Noise | Don't trade (fees eat profit) |
| 3-7% | Small | Trade if high confidence |
| 7-15% | Medium | Core trading opportunity |
| 15-25% | Large | Size up (cautiously) |
| > 25% | Huge | Verify you're not missing something |

## Sources of Edge

### 1. Information Edge
You know something the market doesn't.

```python
# Example: Tracking insider wallet activity
from polycli.edge import WalletTracker

tracker = WalletTracker(client)
tracker.add_wallet("0x...", name="Smart Money 1", strategy="news_trader")

# When smart money moves before news breaks, you gain information edge
changes = await tracker.update_wallet("0x...")
if changes["new"]:
    print("Smart money entering new position!")
```

**Examples**:
- Insider trading (legal in prediction markets)
- Faster news access
- Domain expertise

### 2. Analytical Edge
You analyze public information better than others.

```python
# Example: Building a prediction model
from polycli.psychology import PredictionModelBuilder

builder = PredictionModelBuilder()
model = builder.create_model(
    name="Election Model",
    market_id="abc123",
    market_question="Will X win?",
    base_rate=Decimal("0.50"),
    factors=[
        {"name": "polling_avg", "weight": 0.20},
        {"name": "fundamentals", "weight": 0.15},
        {"name": "momentum", "weight": 0.10},
    ]
)
```

**Examples**:
- Better polling models
- Superior economic forecasting
- Pattern recognition

### 3. Behavioral Edge
You exploit others' psychological biases.

**Common Biases**:
- **Recency Bias**: Overweighting recent events
- **Confirmation Bias**: Seeking confirming information
- **Anchoring**: Fixating on initial prices
- **Overconfidence**: Underestimating uncertainty

### 4. Structural Edge
You exploit market structure inefficiencies.

```python
# Example: Finding volume spikes (potential insider activity)
from polycli.edge import VolumeMonitor

monitor = VolumeMonitor(client, spike_threshold=3.0)
await monitor.update_baselines()
spikes = await monitor.detect_spikes()

for spike in spikes:
    print(f"{spike.market.question}: {spike.spike_ratio}x normal volume")
```

**Examples**:
- Faster execution
- Cross-platform arbitrage
- Liquidity provision

## Edge Decay

Edge isn't permanent. It decays as information spreads.

```
Time after information:
0-5 minutes:   Full edge (if you're fast)
5-30 minutes:  Partial edge (others catching up)
30-60 minutes: Minimal edge (widely known)
1+ hours:      No edge (fully priced in)
```

### Implications
- Speed matters for information edge
- Analytical edge is more durable
- Structural edge requires infrastructure

## Calculating If You Have Edge

### The Honesty Test

Before trading, answer these questions:

1. **What do I know that the market doesn't?**
   - If nothing, you probably have no edge

2. **Why is the market wrong?**
   - Must have specific reason, not "feels off"

3. **Who is on the other side?**
   - Smart money? Retail? Market makers?

4. **What would change my mind?**
   - If nothing, you're probably overconfident

### CLI Implementation

```bash
# Calculate if trade has positive EV
polycli position kelly \
    --bankroll 10000 \
    --win-prob 0.60 \
    --market-price 0.45

# Output shows:
# - Edge: 15%
# - Expected Value: +$0.15/share
# - Recommended bet size
```

## The EV Tracker

Track your EV decisions separately from results:

```python
from polycli.position import EVTracker

tracker = EVTracker()

# Record decision BEFORE outcome
decision = tracker.record_decision(
    market_id="abc123",
    market_question="Will X happen?",
    estimated_probability=Decimal("0.60"),
    market_price=Decimal("0.45"),
    position_size=Decimal("500"),
    confidence=7,
    thesis="Polling underweights demographic shift"
)

# After resolution, record outcome
tracker.resolve_decision(
    decision_id=decision.id,
    outcome="win",  # or "lose"
    actual_pnl=Decimal("300"),
    post_mortem="Thesis was correct, demographic shift materialized"
)

# Analyze performance
stats = tracker.get_stats()
print(f"Total EV expected: ${stats.total_ev_expected}")
print(f"Total actual P&L: ${stats.total_actual_pnl}")
print(f"Positive EV accuracy: {stats.positive_ev_accuracy:.1%}")
```

## Common Mistakes

### 1. Confusing Results with Edge
```
Bad thinking: "I won, so I had edge"
Good thinking: "I had edge (verifiable reason), and I won"

You can:
- Have edge and lose (variance)
- Have no edge and win (luck)
```

### 2. Overestimating Edge
```
Warning signs:
- Edge > 20% on liquid market (you're probably wrong)
- Can't articulate specific information advantage
- "The market is stupid" (it usually isn't)
```

### 3. Ignoring Edge Decay
```
Bad: "I'll wait for better entry"
Reality: Edge might disappear while waiting
Better: Enter at acceptable price, don't chase perfection
```

### 4. Not Tracking EV
```
Problem: Only tracking P&L
Why it's bad: Can't distinguish skill from luck
Solution: Track every decision's expected value
```

## Practical Application

### Daily Workflow

1. **Morning**: Scan for opportunities with potential edge
   ```bash
   polycli edge cross-reference "your topic"
   polycli edge volume-spikes
   ```

2. **Before Trading**: Verify edge exists
   - Write thesis
   - Calculate EV
   - Check position sizing

3. **After Trading**: Record in journal
   ```bash
   polycli journal new --market X --thesis "..." --your-prob 0.6 --market-prob 0.5
   ```

4. **Weekly**: Review EV vs actual performance

---

**Next**: [Edge Finding](./03-Edge-Finding.md)

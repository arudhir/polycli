# Psychology and Continuous Improvement

## The Mental Game of Trading

Technical edge means nothing without psychological control. This section covers mental frameworks and practices for sustainable trading success.

## Trade Journaling

### Theory

Journaling transforms experience into learning:
- **Records decisions** before outcomes bias memory
- **Captures reasoning** for later analysis
- **Identifies patterns** in behavior
- **Separates luck from skill**

### What to Journal

```
Before Trade (Pre-Mortem):
1. Market and position details
2. Thesis (why you have edge)
3. Your probability estimate
4. Confidence level (1-10)
5. What would invalidate thesis
6. Exit plan

After Trade (Post-Mortem):
1. Actual outcome
2. Was thesis correct?
3. What did you learn?
4. Would you make same decision?
5. Behavioral notes (emotions, biases)
```

### Implementation

```python
from polycli.psychology.journal import TradeJournal

journal = TradeJournal()

# Create entry BEFORE taking position
entry = journal.create_entry(
    market_id="abc123",
    market_question="Will X win election?",
    thesis="Polling underweights youth turnout based on registration data",
    edge_source="analytical",  # information, analytical, behavioral, structural
    your_probability=Decimal("0.55"),
    market_probability=Decimal("0.45"),
    confidence=7,
    side="long",
    entry_price=Decimal("0.45"),
    position_size=Decimal("500"),
    invalidation_triggers=[
        "New polling methodology accounts for youth",
        "Registration data revised",
    ],
    exit_plan="Take 50% at 0.60, hold rest to resolution",
)

print(f"Journal entry: {entry.id}")

# After resolution
journal.close_entry(
    entry_id=entry.id,
    outcome="win",
    exit_price=Decimal("0.75"),
    pnl=Decimal("333"),
    post_mortem="Thesis was correct. Youth turnout 5% higher than polls predicted.",
    behavioral_notes="Felt urge to add at 0.50, correctly resisted.",
    lessons_learned="Trust registration data as leading indicator.",
)
```

### CLI Usage

```bash
# Create journal entry
polycli journal new \
    --market MARKET_ID \
    --thesis "Your thesis here" \
    --your-prob 0.55 \
    --market-prob 0.45 \
    --size 500 \
    --confidence 7

# Close entry after resolution
polycli journal close ENTRY_ID \
    --outcome win \
    --exit-price 0.75 \
    --pnl 333 \
    --post-mortem "What happened and why"

# Review entries
polycli journal list
polycli journal view ENTRY_ID

# Analyze patterns
polycli journal analyze
```

### Journal Analysis

```python
# Analyze trading patterns
analysis = journal.analyze()

print(f"Total trades: {analysis.total_trades}")
print(f"Win rate: {analysis.win_rate:.1%}")
print(f"Avg edge estimated: {analysis.avg_edge:.1%}")
print(f"Avg confidence: {analysis.avg_confidence:.1f}")

# Calibration
print(f"\nCalibration (70% confidence trades):")
print(f"Expected: 70% win rate")
print(f"Actual: {analysis.calibration_70:.1%}")

# Common patterns
print(f"\nPatterns identified:")
for pattern in analysis.patterns:
    print(f"- {pattern}")
```

---

## Understanding Variance

### Theory

Variance is the natural fluctuation around expected value:

```
Short-term: Variance dominates
Long-term: Skill emerges

Example:
- 100 +EV trades: Any outcome possible
- 1,000 +EV trades: Positive expectation more likely
- 10,000 +EV trades: Skill clearly evident
```

### Monte Carlo Simulation

Monte Carlo simulation helps visualize possible outcomes:

```python
from polycli.psychology.variance import VarianceAnalyzer

analyzer = VarianceAnalyzer()

# Simulate 1000 possible paths for your strategy
simulation = analyzer.monte_carlo(
    win_probability=Decimal("0.55"),
    average_bet=Decimal("100"),
    num_bets=100,
    num_simulations=1000,
)

print(f"Expected outcome: ${simulation.expected_value:,.0f}")
print(f"5th percentile: ${simulation.percentile_5:,.0f}")
print(f"50th percentile: ${simulation.percentile_50:,.0f}")
print(f"95th percentile: ${simulation.percentile_95:,.0f}")
print(f"Probability of loss: {simulation.loss_probability:.1%}")
print(f"Max drawdown (median): {simulation.median_max_drawdown:.1%}")
```

### Visualizing Uncertainty

```
Expected Value: +$500

Distribution of Outcomes (100 trades at 55% win rate):

     ████████████████████
    ███████████████████████████
   ██████████████████████████████████
  ████████████████████████████████████████
 ███████████████████████████████████████████████
████████████████████████████████████████████████████
-$300   -$100    $100    $300    $500    $700    $900

5% chance: Below -$100
50% chance: Around $400-$600
5% chance: Above $1,100
```

### CLI Usage

```bash
# Run variance simulation
polycli psychology variance \
    --win-prob 0.55 \
    --avg-bet 100 \
    --num-bets 100 \
    --simulations 1000

# Compare actual results to expected variance
polycli psychology variance-check
```

---

## Knowing When to Take Breaks

### Theory

Trading fatigue leads to:
- Overtrading
- Poor decisions
- Emotional reactions
- Larger position sizes

### Break Triggers

```
Take a break when:
1. Drawdown exceeds threshold
2. Consecutive losses (e.g., 5+)
3. Emotional decision made
4. Overtrading (too many positions)
5. Life stress affecting judgment
6. Extended session (4+ hours)
```

### Implementation

```python
from polycli.psychology.breaks import BreakManager

manager = BreakManager()

# Configure break rules
manager.set_rules(
    max_consecutive_losses=5,
    max_drawdown_before_break=Decimal("0.15"),
    max_session_hours=4,
    min_break_hours=24,
)

# Check if break is needed
status = manager.check()

if status.break_needed:
    print(f"🛑 Break recommended: {status.reason}")
    print(f"Resume after: {status.resume_time}")
else:
    print("✅ OK to continue trading")
```

### CLI Usage

```bash
# Check if break needed
polycli psychology break-check

# Log a break
polycli psychology log-break --reason "drawdown" --hours 24

# View break history
polycli psychology break-history
```

---

## Trade Forensics

### Theory

Forensics analyzes why trades succeeded or failed:
- **Was the thesis correct?** (Analysis quality)
- **Was sizing appropriate?** (Risk management)
- **Was entry/exit optimal?** (Execution)
- **Were there behavioral errors?** (Psychology)

### Forensic Framework

```python
from polycli.psychology.forensics import TradeForensics

forensics = TradeForensics(journal)

# Analyze a closed trade
analysis = forensics.analyze(entry_id="...")

print(f"Trade outcome: {analysis.outcome}")
print(f"\nBreakdown:")
print(f"  Thesis quality: {analysis.thesis_quality}/10")
print(f"  Size appropriateness: {analysis.sizing_quality}/10")
print(f"  Entry timing: {analysis.entry_quality}/10")
print(f"  Exit execution: {analysis.exit_quality}/10")
print(f"  Behavioral score: {analysis.behavioral_quality}/10")

print(f"\nKey findings:")
for finding in analysis.findings:
    print(f"  - {finding}")

print(f"\nRecommendations:")
for rec in analysis.recommendations:
    print(f"  - {rec}")
```

### Forensic Questions

```
1. THESIS
   - Was thesis well-defined?
   - Did thesis prove correct?
   - Were assumptions valid?

2. SIZING
   - Was position sized correctly for edge?
   - Did correlation impact results?
   - Were reserves maintained?

3. ENTRY
   - Did you get good entry price?
   - Was timing appropriate?
   - Did you scale in effectively?

4. EXIT
   - Did you follow exit plan?
   - Was exit timed well?
   - Did emotions affect exit?

5. BEHAVIOR
   - Any emotional decisions?
   - Did you deviate from plan?
   - What biases appeared?
```

### CLI Usage

```bash
# Analyze a trade
polycli psychology forensics ENTRY_ID

# Batch forensics on recent trades
polycli psychology forensics-batch --days 30

# View forensics summary
polycli psychology forensics-summary
```

---

## Prediction Model Building

### Theory

Building prediction models:
- **Forces clear thinking** about factors
- **Creates testable frameworks**
- **Enables calibration tracking**
- **Reduces emotional decisions**

### Model Structure

```
Prediction = Base Rate + Σ(Factor × Weight × Adjustment)

Example Election Model:
Base rate: 50%
Factors:
  - Polling average: +5% (polls show 55%)
  - Economic conditions: -2% (slight recession)
  - Incumbency: +3% (incumbent advantage)
  - Momentum: +1% (recent good news)

Prediction: 50% + 5% - 2% + 3% + 1% = 57%
```

### Implementation

```python
from polycli.psychology.models import PredictionModelBuilder

builder = PredictionModelBuilder()

# Create a model
model = builder.create_model(
    name="Election Predictor",
    market_id="abc123",
    market_question="Will candidate X win?",
    base_rate=Decimal("0.50"),
    factors=[
        {
            "name": "polling_average",
            "current_value": Decimal("0.55"),
            "weight": Decimal("0.25"),
            "notes": "538 aggregate",
        },
        {
            "name": "economic_index",
            "current_value": Decimal("-0.10"),
            "weight": Decimal("0.15"),
            "notes": "GDP growth below trend",
        },
        {
            "name": "incumbency",
            "current_value": Decimal("1.0"),  # Binary
            "weight": Decimal("0.05"),
            "notes": "Historical incumbent advantage",
        },
    ],
)

# Calculate prediction
prediction = model.calculate()
print(f"Model prediction: {prediction.probability:.1%}")
print(f"Confidence interval: {prediction.low:.1%} - {prediction.high:.1%}")

# Update factors over time
model.update_factor("polling_average", Decimal("0.58"))
new_prediction = model.calculate()
```

### Model Calibration

```python
# Track model performance over time
calibration = builder.get_calibration(model_id="...")

print(f"Predictions made: {calibration.total_predictions}")
print(f"Brier score: {calibration.brier_score:.3f}")  # Lower is better

print("\nCalibration by bucket:")
for bucket in calibration.buckets:
    print(f"Predicted {bucket.range}: Actual {bucket.actual_rate:.1%}")
```

### CLI Usage

```bash
# Create new model
polycli model create "Election Model" \
    --market MARKET_ID \
    --base-rate 0.50

# Add factors to model
polycli model add-factor MODEL_ID \
    --name "polling_average" \
    --value 0.55 \
    --weight 0.25

# Calculate prediction
polycli model calculate MODEL_ID

# Update factor
polycli model update-factor MODEL_ID polling_average 0.58

# View calibration
polycli model calibration MODEL_ID
```

---

## Common Psychological Biases

### Biases and Mitigations

| Bias | Description | Mitigation |
|------|-------------|------------|
| **Overconfidence** | Overestimating probability estimates | Use confidence intervals, track calibration |
| **Recency** | Overweighting recent events | Use longer baselines, model explicitly |
| **Confirmation** | Seeking confirming information | Actively seek disconfirming evidence |
| **Anchoring** | Fixating on initial prices | Focus on current evidence, not entry price |
| **Loss Aversion** | Holding losers, selling winners | Follow exit plan, use stops |
| **Sunk Cost** | Holding based on past investment | Evaluate each day as new decision |
| **Hindsight** | Believing you "knew it all along" | Journal predictions before outcomes |

### Bias Check

```python
from polycli.psychology.biases import BiasChecker

checker = BiasChecker()

# Check for biases in a decision
biases = checker.check(
    your_probability=Decimal("0.75"),
    market_probability=Decimal("0.50"),
    position_has_loss=True,
    days_held=30,
    thesis="Still valid...",
)

for bias in biases:
    print(f"⚠️ Potential {bias.name}: {bias.description}")
    print(f"   Mitigation: {bias.mitigation}")
```

---

## Building Good Habits

### Daily Practice

```
Morning:
1. Review overnight moves
2. Check open positions
3. Update predictions if needed
4. Scan for opportunities
5. Set day's trading limits

Before Each Trade:
1. Write thesis in journal
2. Verify edge exists
3. Calculate position size
4. Set exit plan
5. Check correlation/diversification

After Each Trade:
1. Log entry in journal
2. Set alerts if applicable
3. Verify within risk limits

Evening:
1. Review day's decisions
2. Update journal with observations
3. Check portfolio status
4. Plan for tomorrow
```

### CLI Workflow

```bash
# Morning routine
polycli workflow morning
polycli psychology limits --daily-loss 500 --max-positions 10

# Before trade
polycli journal new --market ... --thesis ...
polycli position kelly --bankroll ... --win-prob ... --market-price ...

# Evening review
polycli workflow evening
polycli journal entries --date today
polycli psychology break-check
```

---

## Continuous Improvement Loop

```
1. TRADE
   ↓
2. JOURNAL (record decision and reasoning)
   ↓
3. RESOLVE (record outcome)
   ↓
4. FORENSICS (analyze what happened)
   ↓
5. CALIBRATE (update models and beliefs)
   ↓
6. IMPROVE (adjust strategies)
   ↓
(repeat)
```

```python
# Weekly review script
from polycli.psychology import WeeklyReview

review = WeeklyReview()
report = await review.generate(week_ending="2024-01-07")

print(f"=== WEEKLY REVIEW ===")
print(f"Trades: {report.total_trades}")
print(f"Win rate: {report.win_rate:.1%}")
print(f"EV expected: ${report.ev_expected:+,.0f}")
print(f"Actual P&L: ${report.actual_pnl:+,.0f}")
print(f"Variance: ${report.variance:+,.0f}")

print(f"\nBehavioral notes:")
for note in report.behavioral_patterns:
    print(f"- {note}")

print(f"\nAreas for improvement:")
for area in report.improvement_areas:
    print(f"- {area}")
```

---

**Next**: [Advanced Techniques](./09-Advanced-Techniques.md)

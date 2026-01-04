# Edge Finding

## Finding Information Before the Crowd

Edge finding is about discovering information asymmetries—knowing something relevant before it's priced into the market. This section covers systematic approaches to finding tradeable edge.

## 1. Wallet Tracking (Smart Money Following)

### Theory

On-chain prediction markets leave a public trail. When experienced traders ("smart money") take positions, their transactions are visible on the blockchain. By monitoring wallets with strong track records, you can:

- Identify when informed traders are accumulating positions
- See position changes before they affect market prices significantly
- Build conviction based on alignment with proven traders

### The Mathematics

If a wallet has historical accuracy `A` (e.g., 0.65 = 65% accuracy), and the base rate for any given trade being correct is `B` (typically 0.50), we can calculate the informational value:

```
Lift = A / B
Information Value = (A - B) / (1 - B)

Example:
A = 0.65, B = 0.50
Lift = 0.65 / 0.50 = 1.30 (30% better than random)
Information Value = (0.65 - 0.50) / (1 - 0.50) = 0.30
```

### Implementation

```python
from polycli.edge import WalletTracker

# Initialize tracker
tracker = WalletTracker(client)

# Add wallets to monitor (discovered through on-chain analysis)
tracker.add_wallet(
    address="0x1234...",
    name="Whale A",
    strategy="news_trader",  # Their apparent strategy
    track_record=0.68,       # Historical accuracy if known
)

# Update and check for changes
changes = await tracker.update_wallet("0x1234...")

# React to new positions
for position in changes["new"]:
    print(f"New position: {position.market_question}")
    print(f"Side: {position.side}, Size: ${position.size}")
```

### CLI Usage

```bash
# Add a wallet to track
polycli edge wallet-add 0x1234... --name "Whale A" --strategy news_trader

# Check for position changes
polycli edge wallet-check 0x1234...

# View all tracked wallets
polycli edge wallet-list
```

### Practical Considerations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Front-running | Others may see the same signals | Act quickly, smaller size |
| Fake signals | Whales may manipulate | Track multiple wallets |
| Capacity | Large positions move markets | Scale position to your size |
| Latency | Blockchain confirmation delays | Monitor mempool if possible |

---

## 2. Volume Spike Detection

### Theory

Unusual trading volume often precedes price moves because:

1. **Informed traders** accumulate before news breaks
2. **Insider activity** creates detectable patterns
3. **Momentum** attracts more traders

Volume spikes can signal that someone knows something you don't.

### Statistical Framework

We use a rolling baseline to detect anomalies:

```
Baseline = Rolling average volume over N periods
Standard Deviation = σ of volume over same period
Z-Score = (Current Volume - Baseline) / σ

Spike Detected when: Z-Score > Threshold (typically 2-3)
```

### Implementation

```python
from polycli.edge.volume_monitor import VolumeMonitor

# Initialize with threshold
monitor = VolumeMonitor(client, spike_threshold=3.0)

# Build baseline from historical data
await monitor.update_baselines()

# Detect current spikes
spikes = await monitor.detect_spikes()

for spike in spikes:
    print(f"Market: {spike.market.question}")
    print(f"Volume: {spike.current_volume} ({spike.spike_ratio}x normal)")
    print(f"Z-Score: {spike.z_score:.2f}")

    # Higher spike ratios warrant more attention
    if spike.spike_ratio > 5.0:
        print("⚠️ MAJOR SPIKE - Investigate immediately")
```

### CLI Usage

```bash
# Detect volume spikes with default 3x threshold
polycli edge volume-spikes

# Use stricter threshold for fewer false positives
polycli edge volume-spikes --threshold 5.0

# Monitor continuously (background process)
polycli edge volume-monitor --interval 60
```

### Interpreting Spikes

| Spike Ratio | Z-Score | Interpretation |
|-------------|---------|----------------|
| 2-3x | 2-2.5 | Moderate interest, worth watching |
| 3-5x | 2.5-3 | Significant activity, investigate |
| 5-10x | 3-4 | Major event likely, act if thesis forms |
| >10x | >4 | Extraordinary—verify data, check news |

---

## 3. Cross-Platform Arbitrage

### Theory

The same event trades on multiple prediction markets:
- Polymarket
- Manifold Markets
- Metaculus
- PredictIt (US regulated)
- Kalshi

Price discrepancies arise from:
- Different liquidity pools
- Geographic restrictions
- Fee structures
- Information propagation delays

### Arbitrage Mathematics

For a binary event trading at different prices:

```
Platform A: 45% (YES at $0.45)
Platform B: 52% (YES at $0.52)

Arbitrage Opportunity:
Buy YES on A at $0.45
Sell YES on B at $0.52
Guaranteed profit: $0.07 per share (minus fees)

Profit = Price_B - Price_A - Fees_A - Fees_B
```

For non-simultaneous execution (soft arbitrage):

```
Expected Value = (P_true × Payout) - Cost

If Platform A is systematically more accurate:
Edge = P_A_historical_accuracy × (Price_B - Price_A)
```

### Implementation

```python
from polycli.edge.cross_reference import CrossReferenceFinder
from polycli.api.polymarket import PolymarketClient
from polycli.api.external import ManifoldClient, MetaculusClient

finder = CrossReferenceFinder()

# Register platforms
finder.register_platform("polymarket", PolymarketClient())
finder.register_platform("manifold", ManifoldClient())
finder.register_platform("metaculus", MetaculusClient())

# Find discrepancies for a topic
results = await finder.find_discrepancies(
    query="2024 election",
    min_spread=0.05,  # At least 5% difference
)

for match in results:
    print(f"Question: {match.question}")
    print(f"Polymarket: {match.prices['polymarket']:.1%}")
    print(f"Manifold: {match.prices['manifold']:.1%}")
    print(f"Spread: {match.max_spread:.1%}")
```

### CLI Usage

```bash
# Cross-reference a topic across platforms
polycli edge cross-reference "bitcoin ETF"

# Find arbitrage opportunities
polycli edge arbitrage --min-spread 0.05

# Monitor for new opportunities
polycli edge arbitrage-monitor --interval 300
```

### Platform Characteristics

| Platform | Liquidity | Fees | Speed | Best For |
|----------|-----------|------|-------|----------|
| Polymarket | High | 2% | Fast | Large positions |
| Manifold | Medium | 0% | Medium | Small positions, research |
| Metaculus | N/A (points) | N/A | Slow | Calibration reference |
| PredictIt | Medium | 10% | Slow | US-accessible |
| Kalshi | Medium | Varies | Fast | Regulated markets |

---

## 4. Twitter/Social Signal Detection

### Theory

Social media often leads market moves:
- Breaking news appears on Twitter before markets adjust
- Sentiment shifts precede price moves
- Key accounts have predictive value

### Signal Sources

1. **Official accounts**: Government, companies, candidates
2. **Journalists**: Breaking news reporters
3. **Domain experts**: Pollsters, analysts, insiders
4. **Aggregate sentiment**: Overall discussion volume and tone

### Implementation

```python
from polycli.edge.twitter_search import TwitterMonitor

monitor = TwitterMonitor(bearer_token="...")

# Add keywords and influential accounts
monitor.add_keyword("fed rate decision")
monitor.add_account("@federalreserve")
monitor.add_account("@NickTimiraos")  # Fed reporter

# Stream for relevant tweets
async for tweet in monitor.stream():
    relevance_score = await monitor.score_relevance(tweet)

    if relevance_score > 0.8:
        print(f"HIGH RELEVANCE: {tweet.text[:100]}")
        # Trigger market check or alert
```

### CLI Usage

```bash
# Search recent tweets about a topic
polycli edge twitter-search "fed meeting"

# Monitor accounts for breaking news
polycli edge twitter-monitor @federalreserve @NickTimiraos

# Analyze sentiment for a market topic
polycli edge sentiment "bitcoin regulation"
```

### Scoring Tweet Relevance

```
Relevance Score = Σ(Factor × Weight)

Factors:
- Account authority (verified, follower count, domain relevance)
- Keyword match strength
- Engagement velocity (likes/retweets per minute)
- Novelty (first mention vs. repeat)
```

---

## 5. Correlation Analysis

### Theory

Markets are interconnected. Understanding correlations helps:
- Find hidden relationships
- Avoid over-concentration
- Identify leading indicators

### Types of Correlation

1. **Direct correlation**: Markets on related outcomes
   - "Will candidate X win primary?" ↔ "Will X win general?"

2. **Inverse correlation**: Mutually exclusive outcomes
   - "Will X win?" ↔ "Will Y win?" (same race)

3. **Causal correlation**: One outcome affects another
   - "Will Fed raise rates?" → "Will recession occur?"

### Implementation

```python
from polycli.edge.correlation import CorrelationAnalyzer

analyzer = CorrelationAnalyzer(client)

# Analyze correlation between markets
correlation = await analyzer.analyze_pair(
    market_a="market_id_1",
    market_b="market_id_2",
    lookback_days=30,
)

print(f"Correlation: {correlation.coefficient:.2f}")
print(f"Lead/Lag: Market A leads by {correlation.lag_days} days")

# Find correlated markets for a given market
related = await analyzer.find_correlated(
    market_id="market_id_1",
    min_correlation=0.5,
)
```

### CLI Usage

```bash
# Analyze correlation between two markets
polycli edge correlation MARKET_ID_1 MARKET_ID_2

# Find markets correlated with a given market
polycli edge find-correlated MARKET_ID --min-corr 0.5

# Analyze portfolio correlation (for risk)
polycli risk correlation-matrix
```

### Correlation Matrix Example

```
              Market A  Market B  Market C
Market A        1.00      0.75     -0.30
Market B        0.75      1.00     -0.45
Market C       -0.30     -0.45      1.00

Interpretation:
- A and B: Strong positive correlation (likely related outcomes)
- A/B and C: Negative correlation (potential hedges)
```

---

## Edge Finding Workflow

### Daily Routine

```bash
# Morning scan
polycli edge volume-spikes                    # Check overnight activity
polycli edge cross-reference "your topics"    # Platform discrepancies
polycli edge wallet-check-all                 # Smart money moves

# Throughout day
polycli edge twitter-monitor @key_accounts    # Breaking news
polycli edge alerts                           # Custom alert triggers

# Evening review
polycli edge summary                          # Day's opportunities
polycli journal review --date today           # Log findings
```

### Building Your Edge Stack

1. **Start simple**: Pick one method and master it
2. **Build systematically**: Add methods as you validate edge
3. **Track everything**: Know which sources provide actual edge
4. **Stay current**: Markets adapt, so must your methods

---

**Next**: [Position Sizing](./04-Position-Sizing.md)

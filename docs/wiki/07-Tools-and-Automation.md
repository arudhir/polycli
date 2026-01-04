# Tools and Automation

## Building Your Trading Edge with Technology

Technology provides edge through speed, consistency, and scale. This section covers tools and automation strategies for prediction market trading.

## Alert Systems

### Theory

Alerts enable action without constant monitoring:
- **Price alerts**: Trigger when markets reach target prices
- **Volume alerts**: Detect unusual activity
- **News alerts**: React to breaking information
- **Risk alerts**: Warn of portfolio issues

### Alert Types

```
Price Alerts:
- Threshold: "Alert if YES < $0.40"
- Change: "Alert if price moves 10%"
- Cross: "Alert if YES crosses $0.50"

Volume Alerts:
- Spike: "Alert if volume > 3x baseline"
- Accumulation: "Alert if large orders detected"

Portfolio Alerts:
- Drawdown: "Alert if portfolio down 15%"
- Exposure: "Alert if total risk > $5000"
- Correlation: "Alert if correlation > 0.8"
```

### Implementation

```python
from polycli.tools.alerts import AlertManager, AlertType

manager = AlertManager()

# Price alert
manager.add_alert(
    alert_type=AlertType.PRICE_BELOW,
    market_id="abc123",
    threshold=Decimal("0.40"),
    callback=async def notify(alert):
        print(f"🔔 {alert.market_question} now at {alert.current_price}")
        # Could trigger auto-buy or send notification
)

# Volume spike alert
manager.add_alert(
    alert_type=AlertType.VOLUME_SPIKE,
    market_id="abc123",
    threshold=3.0,  # 3x normal volume
    callback=handle_volume_spike,
)

# Drawdown alert
manager.add_alert(
    alert_type=AlertType.DRAWDOWN,
    threshold=Decimal("0.15"),  # 15% drawdown
    callback=handle_drawdown,
)

# Start monitoring
await manager.start_monitoring(interval=30)  # Check every 30 seconds
```

### Notification Channels

```python
from polycli.tools.notifications import NotificationManager

notifier = NotificationManager()

# Configure channels
notifier.add_channel("console", ConsoleNotifier())
notifier.add_channel("discord", DiscordNotifier(webhook_url="..."))
notifier.add_channel("telegram", TelegramNotifier(bot_token="...", chat_id="..."))

# Route alerts to channels
manager.set_notifier(notifier, channels=["console", "discord"])
```

### CLI Usage

```bash
# Add price alert
polycli alerts add price \
    --market MARKET_ID \
    --condition below \
    --threshold 0.40

# Add volume alert
polycli alerts add volume \
    --market MARKET_ID \
    --threshold 3.0

# Add portfolio alert
polycli alerts add drawdown --threshold 0.15

# View active alerts
polycli alerts list

# Start alert monitoring
polycli alerts monitor

# Test notification channels
polycli alerts test-notification
```

---

## Order Book Analysis

### Theory

The order book reveals market structure:
- **Depth**: How much liquidity at each price level
- **Imbalance**: More bids vs asks suggests direction
- **Walls**: Large orders that act as support/resistance
- **Spread**: Cost of immediate execution

### Order Book Metrics

```
Bid-Ask Spread = Best Ask - Best Bid
Midpoint = (Best Ask + Best Bid) / 2

Imbalance = (Bid Volume - Ask Volume) / (Bid Volume + Ask Volume)
Range: -1 (all asks) to +1 (all bids)

Depth at Level = Cumulative volume within X% of midpoint
```

### Implementation

```python
from polycli.tools.orderbook import OrderBookAnalyzer

analyzer = OrderBookAnalyzer(client)

# Get current order book analysis
analysis = await analyzer.analyze(market_id="abc123")

print(f"Best Bid: {analysis.best_bid}")
print(f"Best Ask: {analysis.best_ask}")
print(f"Spread: {analysis.spread:.2%}")
print(f"Midpoint: {analysis.midpoint}")
print(f"Imbalance: {analysis.imbalance:+.2f}")

# Depth analysis
print(f"Bid depth (5%): ${analysis.bid_depth_5pct:,.0f}")
print(f"Ask depth (5%): ${analysis.ask_depth_5pct:,.0f}")

# Detect walls
for wall in analysis.walls:
    print(f"Wall at {wall.price}: ${wall.size:,.0f} ({wall.side})")

# Slippage estimation
slippage = await analyzer.estimate_slippage(
    side="buy",
    size=Decimal("1000"),
)
print(f"Slippage for $1000 buy: {slippage:.2%}")
```

### Order Book Visualization

```
Price    Bid Size    Ask Size    Cumulative
0.52                    2000        2000
0.51                    1500        3500
0.50                    ████  5000 (wall)    8500
0.49     3000
0.48     2000    ██████
0.47     5000    (wall)
0.46     1000

Spread: 0.49 - 0.50 = $0.01 (2%)
Imbalance: +0.15 (slightly more bids)
```

### CLI Usage

```bash
# View order book
polycli market orderbook MARKET_ID

# Analyze order book metrics
polycli market orderbook MARKET_ID --analyze

# Estimate slippage
polycli market slippage MARKET_ID --size 1000 --side buy

# Monitor order book changes
polycli market orderbook-monitor MARKET_ID
```

---

## Historical Odds Analysis

### Theory

Historical price data reveals:
- **Patterns**: How prices behave before events
- **Calibration**: Market accuracy over time
- **Volatility**: Expected price movement
- **Mean reversion**: Tendency to return to fair value

### Historical Metrics

```python
from polycli.tools.historical import HistoricalAnalyzer

analyzer = HistoricalAnalyzer(client)

# Get historical analysis
history = await analyzer.analyze(
    market_id="abc123",
    lookback_days=30,
)

print(f"Price range: {history.min_price:.1%} - {history.max_price:.1%}")
print(f"Volatility: {history.volatility:.2%} daily")
print(f"Trend: {history.trend}")  # up, down, sideways
print(f"Days since last move >5%: {history.days_since_big_move}")

# Similar market calibration
calibration = await analyzer.get_calibration(
    market_category="elections",
    price_range=(Decimal("0.40"), Decimal("0.60")),
)
print(f"Markets at 50% actually resolve YES: {calibration.resolution_rate:.1%}")
```

### Price Pattern Analysis

```python
# Detect patterns
patterns = await analyzer.detect_patterns(market_id="abc123")

for pattern in patterns:
    print(f"Pattern: {pattern.name}")
    print(f"Confidence: {pattern.confidence:.0%}")
    print(f"Expected move: {pattern.expected_direction} {pattern.expected_magnitude:.1%}")
```

### CLI Usage

```bash
# View price history
polycli market history MARKET_ID --days 30

# Analyze volatility
polycli market volatility MARKET_ID

# Check market calibration
polycli market calibration --category elections

# Export historical data
polycli market history MARKET_ID --export history.csv
```

---

## API-Powered Execution

### Theory

Programmatic execution provides:
- **Speed**: Sub-second order placement
- **Consistency**: No emotional decisions
- **Scale**: Manage many positions simultaneously
- **Automation**: Execute strategies automatically

### Execution Framework

```python
from polycli.tools.execution import ExecutionEngine

engine = ExecutionEngine(client)

# Market order (immediate execution)
result = await engine.market_order(
    market_id="abc123",
    side="buy",
    size=Decimal("500"),
)
print(f"Filled: {result.filled_size} at avg price {result.avg_price}")

# Limit order
order = await engine.limit_order(
    market_id="abc123",
    side="buy",
    price=Decimal("0.45"),
    size=Decimal("500"),
    time_in_force="GTC",
)
print(f"Order placed: {order.id}")

# TWAP (Time-Weighted Average Price) execution
# Spreads large order over time to minimize impact
result = await engine.twap_order(
    market_id="abc123",
    side="buy",
    total_size=Decimal("5000"),
    duration_minutes=60,
    slices=12,
)
```

### Strategy Automation

```python
from polycli.tools.strategies import StrategyRunner

runner = StrategyRunner(engine)

# Define a strategy
class MeanReversionStrategy:
    async def on_price_update(self, market, price):
        if price < market.fair_value * Decimal("0.95"):
            return {"action": "buy", "size": calculate_size()}
        elif price > market.fair_value * Decimal("1.05"):
            return {"action": "sell", "size": calculate_size()}
        return {"action": "hold"}

# Run strategy
await runner.run(
    strategy=MeanReversionStrategy(),
    markets=["abc123", "def456"],
)
```

### CLI Usage

```bash
# Place market order
polycli order market-buy --market MARKET_ID --size 500

# Place limit order
polycli order limit-buy --market MARKET_ID --price 0.45 --size 500

# TWAP order
polycli order twap --market MARKET_ID --side buy --size 5000 --duration 60

# View order status
polycli order status ORDER_ID

# Cancel order
polycli order cancel ORDER_ID
```

---

## Dashboard and Monitoring

### Unified Dashboard

```python
from polycli.tools.dashboard import Dashboard

dash = Dashboard(client)

# Generate dashboard view
view = await dash.generate()

print("=== PORTFOLIO ===")
print(f"Total Value: ${view.portfolio.total_value:,.2f}")
print(f"P&L Today: ${view.portfolio.daily_pnl:+,.2f}")
print(f"Open Positions: {view.portfolio.open_positions}")

print("\n=== WATCHLIST ===")
for market in view.watchlist:
    print(f"{market.question[:40]}: {market.price:.1%}")

print("\n=== ALERTS ===")
for alert in view.triggered_alerts:
    print(f"🔔 {alert.message}")

print("\n=== OPPORTUNITIES ===")
for opp in view.opportunities:
    print(f"Edge {opp.edge:.1%}: {opp.market_question[:40]}")
```

### Real-Time Monitoring

```python
from polycli.tools.monitor import RealtimeMonitor

monitor = RealtimeMonitor(client)

# Subscribe to updates
@monitor.on("price_update")
async def handle_price(market_id, new_price):
    print(f"Price update: {market_id} -> {new_price}")

@monitor.on("order_filled")
async def handle_fill(order):
    print(f"Order filled: {order.id}")

@monitor.on("alert_triggered")
async def handle_alert(alert):
    print(f"Alert: {alert.message}")

# Start monitoring
await monitor.start()
```

### CLI Usage

```bash
# View dashboard
polycli dashboard

# Live monitoring
polycli monitor --refresh 10

# Watchlist view
polycli watchlist

# Position summary
polycli positions
```

---

## Automation Workflows

### Morning Routine

```bash
#!/bin/bash
# morning_scan.sh

# Update market data
polycli market sync

# Check overnight volume spikes
polycli edge volume-spikes

# Cross-reference opportunities
polycli edge cross-reference "elections"
polycli edge cross-reference "crypto"

# Check smart money moves
polycli edge wallet-check-all

# Review portfolio
polycli risk dashboard

# Check triggered alerts
polycli alerts triggered
```

### Continuous Monitoring

```python
# continuous_monitor.py
import asyncio
from polycli.tools import AlertManager, RealtimeMonitor

async def main():
    alert_manager = AlertManager()
    monitor = RealtimeMonitor(client)

    # Load saved alerts
    await alert_manager.load_alerts()

    # Start monitoring
    await asyncio.gather(
        alert_manager.start_monitoring(),
        monitor.start(),
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### CLI Usage

```bash
# Run morning scan
polycli workflow morning

# Start continuous monitoring
polycli workflow monitor --daemon

# Evening review
polycli workflow evening
```

---

## Tool Configuration

### Settings

```python
from polycli.config import get_settings, update_settings

settings = get_settings()

# View current settings
print(f"Data directory: {settings.data_dir}")
print(f"Refresh interval: {settings.refresh_interval}s")
print(f"Alert channels: {settings.alert_channels}")

# Update settings
update_settings(
    refresh_interval=30,
    alert_channels=["console", "discord"],
)
```

### CLI Usage

```bash
# View configuration
polycli config

# Update settings
polycli config set refresh_interval 30
polycli config set alert_channels "console,discord"

# Configure API keys
polycli config set-api polymarket YOUR_API_KEY
polycli config set-api twitter YOUR_BEARER_TOKEN
```

---

## Automation Best Practices

### 1. Start Manual, Then Automate

```
Phase 1: Manual trading, learn the market
Phase 2: Semi-automated (alerts, manual execution)
Phase 3: Assisted automation (suggestions, confirm to execute)
Phase 4: Full automation (monitored)
```

### 2. Always Have Kill Switches

```python
# Emergency stop
engine.set_emergency_stop(
    max_daily_loss=Decimal("500"),
    max_position_size=Decimal("1000"),
    max_orders_per_hour=10,
)
```

### 3. Log Everything

```python
from polycli.tools.logging import TradingLogger

logger = TradingLogger()
logger.log_decision(decision)
logger.log_execution(order, result)
logger.log_alert(alert)
```

### 4. Test Before Live

```bash
# Paper trading mode
polycli config set mode paper

# Backtest strategy
polycli backtest strategy.py --from 2024-01-01 --to 2024-06-01
```

---

**Next**: [Psychology and Improvement](./08-Psychology.md)

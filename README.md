# PolyCLI

A command-line tool for Polymarket trading strategies and analysis.

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd polycli

# Install with uv
uv sync

# Install with dev dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

## Configuration

Create a `.env` file with your API credentials:

```env
POLYCLI_POLYMARKET_API_KEY=your_key
POLYCLI_POLYMARKET_API_SECRET=your_secret
POLYCLI_POLYMARKET_PASSPHRASE=your_passphrase
POLYCLI_TWITTER_BEARER_TOKEN=your_twitter_token
POLYCLI_TELEGRAM_BOT_TOKEN=your_telegram_token
POLYCLI_TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

```bash
# List markets
polycli market list

# Search markets
polycli market search "trump"

# Calculate position size with Kelly Criterion
polycli position kelly --bankroll 10000 --win-prob 0.6 --market-price 0.45

# Cross-reference prices across platforms
polycli edge cross-reference "election"

# Check drawdown risk
polycli risk drawdown --portfolio-value 10000 --at-risk 3000

# Create journal entry
polycli journal new --market abc123 --thesis "My thesis" --your-prob 0.6 --market-prob 0.5 --size 500

# Show dashboard
polycli dashboard
```

## Modules

### Edge Finding (`polycli.edge`)
- **Wallet Tracker**: Track smart wallets and their positions
- **Volume Monitor**: Detect unusual volume spikes
- **Cross Reference**: Compare prices across prediction platforms
- **Twitter Search**: Find early signals on Twitter
- **Correlation**: Analyze correlated markets

### Position Sizing (`polycli.position`)
- **Kelly Calculator**: Calculate optimal bet sizes
- **Correlation Check**: Avoid correlated position concentration
- **Reserve Manager**: Manage cash reserves
- **Scale Out**: Strategies for taking profits
- **EV Tracker**: Track expected value vs actual results

### Market Selection (`polycli.selection`)
- **Liquidity Analyzer**: Assess market liquidity
- **Coin Flip Detector**: Avoid pure gambling
- **Time Decay**: Consider resolution timing
- **Resolution Analyzer**: Check resolution criteria
- **Public Data Checker**: Find data-rich markets

### Risk Management (`polycli.risk`)
- **Hedging Calculator**: Asymmetric hedging strategies
- **Limit Order Strategy**: Aggressive limit order placement
- **Drawdown Calculator**: Analyze potential drawdowns
- **Diversification**: Diversify by topic/time/source
- **Exit Strategy**: Pre-define exit levels

### Tools & Automation (`polycli.tools`)
- **Alert Manager**: Price alerts via Telegram/Discord
- **Order Book Analyzer**: Analyze book depth
- **Historical Tracker**: Track historical odds
- **Order Executor**: Automated order execution
- **Dashboard**: Custom trading dashboards

### Psychology (`polycli.psychology`)
- **Trade Journal**: Document every trade decision
- **Variance Analyzer**: Separate skill from luck
- **Break Manager**: Enforce breaks after big wins/losses
- **Forensic Analyzer**: Investigate market movements
- **Prediction Models**: Build and track prediction models

### Advanced (`polycli.advanced`)
- **Arbitrage Finder**: Cross-platform arbitrage
- **Synthetic Positions**: Build synthetic exposures
- **Liquidity Provider**: Market making strategies
- **News Reactor**: Fast news reaction systems

## Development

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/polycli

# Format code
uv run ruff format .
```

## License

MIT

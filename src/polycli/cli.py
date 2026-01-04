"""Command-line interface for PolyCLI."""

import asyncio
from decimal import Decimal
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from polycli.config import get_settings

console = Console()


def async_command(f):  # type: ignore[no-untyped-def]
    """Decorator to run async click commands."""
    import functools

    @functools.wraps(f)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.group()
@click.version_option(version="0.1.0", prog_name="polycli")
def main() -> None:
    """PolyCLI - Polymarket trading strategies and analysis."""
    pass


# --- Market Commands ---


@main.group()
def market() -> None:
    """Market data and analysis commands."""
    pass


@market.command("list")
@click.option("--limit", default=20, help="Number of markets to show")
@click.option("--active/--closed", default=True, help="Filter by active status")
@async_command
async def market_list(limit: int, active: bool) -> None:
    """List available markets."""
    from polycli.api.polymarket import PolymarketClient

    async with PolymarketClient() as client:
        markets = await client.get_markets(limit=limit, active=active)

    table = Table(title="Markets")
    table.add_column("Question", style="cyan", max_width=50)
    table.add_column("Yes", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Liquidity", justify="right")

    for m in markets:
        yes_price = m.outcomes[0].price if m.outcomes else Decimal(0)
        table.add_row(
            m.question[:50] + "..." if len(m.question) > 50 else m.question,
            f"{yes_price:.1%}",
            f"${m.volume:,.0f}",
            f"${m.liquidity:,.0f}",
        )

    console.print(table)


@market.command("search")
@click.argument("query")
@click.option("--limit", default=10, help="Number of results")
@async_command
async def market_search(query: str, limit: int) -> None:
    """Search markets by query."""
    from polycli.api.polymarket import PolymarketClient

    async with PolymarketClient() as client:
        markets = await client.search_markets(query, limit=limit)

    table = Table(title=f"Search: {query}")
    table.add_column("Question", style="cyan", max_width=60)
    table.add_column("Yes", justify="right")
    table.add_column("Volume", justify="right")

    for m in markets:
        yes_price = m.outcomes[0].price if m.outcomes else Decimal(0)
        table.add_row(
            m.question[:60],
            f"{yes_price:.1%}",
            f"${m.volume:,.0f}",
        )

    console.print(table)


@market.command("info")
@click.argument("condition_id")
@async_command
async def market_info(condition_id: str) -> None:
    """Get detailed market information."""
    from polycli.api.polymarket import PolymarketClient

    async with PolymarketClient() as client:
        market = await client.get_market(condition_id)

    if not market:
        console.print(f"[red]Market {condition_id} not found[/red]")
        return

    console.print(f"\n[bold]{market.question}[/bold]\n")
    console.print(f"Condition ID: {market.condition_id}")
    console.print(f"Volume: ${market.volume:,.2f}")
    console.print(f"Liquidity: ${market.liquidity:,.2f}")
    console.print(f"Resolution: {market.resolution_source or 'Not specified'}")

    table = Table(title="Outcomes")
    table.add_column("Outcome")
    table.add_column("Price", justify="right")
    table.add_column("Token ID")

    for o in market.outcomes:
        table.add_row(o.outcome, f"{o.price:.1%}", o.token_id[:20] + "...")

    console.print(table)


# --- Position Sizing Commands ---


@main.group()
def position() -> None:
    """Position sizing and bankroll management."""
    pass


@position.command("kelly")
@click.option("--bankroll", required=True, type=float, help="Your total bankroll")
@click.option("--win-prob", required=True, type=float, help="Your estimated win probability (0-1)")
@click.option("--market-price", required=True, type=float, help="Current market price (0-1)")
@click.option("--fraction", default="quarter", type=click.Choice(["full", "half", "quarter", "eighth"]))
def kelly_calc(bankroll: float, win_prob: float, market_price: float, fraction: str) -> None:
    """Calculate Kelly Criterion bet size."""
    from polycli.position.kelly import KellyCalculator, KellyFraction

    fraction_map = {
        "full": KellyFraction.FULL,
        "half": KellyFraction.HALF,
        "quarter": KellyFraction.QUARTER,
        "eighth": KellyFraction.EIGHTH,
    }

    calc = KellyCalculator(Decimal(str(bankroll)))
    result = calc.calculate(
        win_probability=Decimal(str(win_prob)),
        market_price=Decimal(str(market_price)),
        kelly_fraction=fraction_map[fraction],
    )

    console.print(f"\n[bold]Kelly Calculation[/bold]")
    console.print(f"Your probability: {win_prob:.1%}")
    console.print(f"Market price: {market_price:.1%}")
    console.print(f"Edge: {result.edge:.1%}")
    console.print(f"Expected value: ${result.expected_value:.2f}")
    console.print(f"Full Kelly: {result.full_kelly_fraction:.1%}")
    console.print(f"Recommended ({fraction}): {result.recommended_fraction:.1%}")
    console.print(f"[bold]Bet size: ${result.recommended_bet_size:.2f}[/bold]")

    if result.is_positive_ev:
        console.print("[green]Positive EV trade[/green]")
    else:
        console.print("[red]Negative EV - do not trade[/red]")


# --- Edge Finding Commands ---


@main.group()
def edge() -> None:
    """Edge finding and analysis commands."""
    pass


@edge.command("cross-reference")
@click.argument("query")
@async_command
async def cross_reference(query: str) -> None:
    """Cross-reference markets across platforms."""
    from polycli.api.external import ManifoldClient, MetaculusClient
    from polycli.api.polymarket import PolymarketClient

    console.print(f"\n[bold]Cross-referencing: {query}[/bold]\n")

    results = {}

    async with PolymarketClient() as pm:
        markets = await pm.search_markets(query, limit=5)
        results["Polymarket"] = [
            (m.question[:50], m.outcomes[0].price if m.outcomes else Decimal(0))
            for m in markets
        ]

    async with ManifoldClient() as mf:
        markets = await mf.search_markets(query, limit=5)
        results["Manifold"] = [(m.question[:50], m.probability) for m in markets]

    async with MetaculusClient() as mc:
        markets = await mc.search_questions(query, limit=5)
        results["Metaculus"] = [(m.question[:50], m.probability) for m in markets]

    for platform, markets in results.items():
        if markets:
            console.print(f"\n[cyan]{platform}[/cyan]")
            for question, prob in markets:
                console.print(f"  {question}: {prob:.1%}")


@edge.command("volume-spikes")
@click.option("--threshold", default=3.0, help="Spike threshold multiplier")
@async_command
async def volume_spikes(threshold: float) -> None:
    """Find markets with volume spikes."""
    from polycli.api.polymarket import PolymarketClient
    from polycli.edge.volume_monitor import VolumeMonitor

    async with PolymarketClient() as client:
        monitor = VolumeMonitor(client, spike_threshold=threshold)
        await monitor.update_baselines()
        spikes = await monitor.detect_spikes()

    if not spikes:
        console.print("No volume spikes detected")
        return

    table = Table(title="Volume Spikes Detected")
    table.add_column("Market", style="cyan", max_width=40)
    table.add_column("Spike", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Liquidity", justify="right")

    for spike in spikes[:10]:
        table.add_row(
            spike.market.question[:40],
            f"{spike.spike_ratio:.1f}x",
            f"${spike.current_volume:,.0f}",
            f"${spike.liquidity:,.0f}",
        )

    console.print(table)


# --- Risk Commands ---


@main.group()
def risk() -> None:
    """Risk management commands."""
    pass


@risk.command("drawdown")
@click.option("--portfolio-value", required=True, type=float, help="Total portfolio value")
@click.option("--at-risk", required=True, type=float, help="Total amount at risk")
@click.option("--max-acceptable", default=0.25, type=float, help="Max acceptable drawdown")
def drawdown_check(portfolio_value: float, at_risk: float, max_acceptable: float) -> None:
    """Check drawdown risk."""
    current_drawdown = at_risk / portfolio_value if portfolio_value > 0 else 0

    console.print(f"\n[bold]Drawdown Analysis[/bold]")
    console.print(f"Portfolio value: ${portfolio_value:,.2f}")
    console.print(f"Amount at risk: ${at_risk:,.2f}")
    console.print(f"Max drawdown: {current_drawdown:.1%}")
    console.print(f"Acceptable limit: {max_acceptable:.1%}")

    if current_drawdown > max_acceptable:
        console.print(f"\n[red]WARNING: Above acceptable drawdown![/red]")
        reduce_by = at_risk - (portfolio_value * max_acceptable)
        console.print(f"Reduce exposure by: ${reduce_by:,.2f}")
    else:
        remaining = (portfolio_value * max_acceptable) - at_risk
        console.print(f"\n[green]Within limits[/green]")
        console.print(f"Room for additional risk: ${remaining:,.2f}")


# --- Journal Commands ---


@main.group()
def journal() -> None:
    """Trade journaling commands."""
    pass


@journal.command("new")
@click.option("--market", required=True, help="Market ID")
@click.option("--thesis", required=True, help="Your trade thesis")
@click.option("--your-prob", required=True, type=float, help="Your probability estimate")
@click.option("--market-prob", required=True, type=float, help="Market probability")
@click.option("--size", required=True, type=float, help="Position size")
@click.option("--confidence", default=5, type=int, help="Confidence 1-10")
def journal_new(
    market: str,
    thesis: str,
    your_prob: float,
    market_prob: float,
    size: float,
    confidence: int,
) -> None:
    """Create a new journal entry."""
    from polycli.psychology.journal import TradeJournal

    journal_mgr = TradeJournal()
    entry = journal_mgr.create_entry(
        market_id=market,
        market_question="",  # Would fetch from API
        thesis=thesis,
        edge_source="manual",
        your_probability=Decimal(str(your_prob)),
        market_probability=Decimal(str(market_prob)),
        confidence=confidence,
        side="long",
        entry_price=Decimal(str(market_prob)),
        position_size=Decimal(str(size)),
    )

    console.print(f"\n[green]Created journal entry: {entry.id}[/green]")
    console.print(f"Edge: {your_prob - market_prob:.1%}")


@journal.command("list")
@click.option("--open-only", is_flag=True, help="Show only open entries")
def journal_list(open_only: bool) -> None:
    """List journal entries."""
    from polycli.psychology.journal import TradeJournal

    journal_mgr = TradeJournal()

    if open_only:
        entries = journal_mgr.get_open_entries()
    else:
        entries = list(journal_mgr._entries.values())

    if not entries:
        console.print("No journal entries found")
        return

    table = Table(title="Journal Entries")
    table.add_column("ID")
    table.add_column("Date")
    table.add_column("Market")
    table.add_column("Edge", justify="right")
    table.add_column("Outcome")

    for e in entries[-20:]:
        table.add_row(
            e.id,
            e.created_at.strftime("%Y-%m-%d"),
            e.market_question[:30] if e.market_question else e.market_id[:20],
            f"{e.your_probability - e.market_probability:.1%}",
            e.outcome or "Open",
        )

    console.print(table)


# --- Dashboard Command ---


@main.command()
@async_command
async def dashboard() -> None:
    """Show trading dashboard."""
    from polycli.tools.dashboard import Dashboard

    dash = Dashboard()

    # Would load actual data in practice
    console.print("\n[bold]PolyCLI Dashboard[/bold]\n")
    console.print("Run with actual positions and watchlist for full dashboard.")
    console.print("\nAvailable commands:")
    console.print("  polycli market list    - List markets")
    console.print("  polycli market search  - Search markets")
    console.print("  polycli position kelly - Calculate position size")
    console.print("  polycli edge cross-reference - Cross-reference platforms")
    console.print("  polycli risk drawdown  - Check drawdown risk")
    console.print("  polycli journal new    - Create journal entry")


# --- Config Command ---


@main.command()
def config() -> None:
    """Show current configuration."""
    settings = get_settings()

    console.print("\n[bold]Configuration[/bold]\n")
    console.print(f"Data directory: {settings.data_dir}")
    console.print(f"Database: {settings.database_url}")
    console.print(f"Default Kelly fraction: {settings.default_kelly_fraction:.0%}")
    console.print(f"Reserve percentage: {settings.reserve_percentage:.0%}")

    api_configured = settings.polymarket_api_key is not None
    console.print(f"Polymarket API: {'Configured' if api_configured else 'Not configured'}")

    twitter_configured = settings.twitter_bearer_token is not None
    console.print(f"Twitter API: {'Configured' if twitter_configured else 'Not configured'}")


if __name__ == "__main__":
    main()

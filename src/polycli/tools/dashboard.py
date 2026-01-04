"""Create custom dashboards.

Don't rely on Polymarket UI - build views that show exactly what
you need to make decisions.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from polycli.models import Market, Position


@dataclass
class DashboardConfig:
    """Configuration for a dashboard view."""

    name: str
    widgets: list[str]
    refresh_interval: int = 60  # seconds
    filters: dict[str, Any] | None = None


class Dashboard:
    """Build custom dashboard views for trading decisions."""

    def __init__(self):
        """Initialize dashboard."""
        self._console = Console()
        self._configs: dict[str, DashboardConfig] = {}

    def create_config(
        self,
        name: str,
        widgets: list[str],
        refresh_interval: int = 60,
        filters: Optional[dict[str, Any]] = None,
    ) -> DashboardConfig:
        """Create a dashboard configuration.

        Args:
            name: Dashboard name
            widgets: List of widget types to include
            refresh_interval: Refresh interval in seconds
            filters: Optional filters to apply
        """
        config = DashboardConfig(
            name=name,
            widgets=widgets,
            refresh_interval=refresh_interval,
            filters=filters,
        )
        self._configs[name] = config
        return config

    def render_portfolio_summary(
        self,
        positions: list[Position],
        reserve_balance: Decimal,
    ) -> str:
        """Render portfolio summary view.

        Args:
            positions: Current positions
            reserve_balance: Cash reserves
        """
        table = Table(title="Portfolio Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        total_invested = sum(p.cost_basis for p in positions)
        total_value = sum(p.current_value for p in positions)
        total_pnl = sum(p.unrealized_pnl for p in positions)
        portfolio_value = total_value + reserve_balance

        table.add_row("Positions", str(len(positions)))
        table.add_row("Total Invested", f"${total_invested:,.2f}")
        table.add_row("Current Value", f"${total_value:,.2f}")
        table.add_row(
            "Unrealized P&L",
            f"${total_pnl:,.2f} ({total_pnl / total_invested * 100:.1f}%)"
            if total_invested > 0
            else "$0.00",
        )
        table.add_row("Reserves", f"${reserve_balance:,.2f}")
        table.add_row("Portfolio Value", f"${portfolio_value:,.2f}")

        # Render to string
        with self._console.capture() as capture:
            self._console.print(table)
        return capture.get()

    def render_positions_table(self, positions: list[Position]) -> str:
        """Render positions table.

        Args:
            positions: Positions to display
        """
        table = Table(title="Open Positions")
        table.add_column("Market", style="cyan", max_width=40)
        table.add_column("Side", style="magenta")
        table.add_column("Size", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("P&L", justify="right")
        table.add_column("P&L %", justify="right")

        for p in sorted(positions, key=lambda x: x.unrealized_pnl, reverse=True):
            pnl_style = "green" if p.unrealized_pnl >= 0 else "red"
            table.add_row(
                p.market_question[:40] + "..." if len(p.market_question) > 40 else p.market_question,
                p.outcome,
                f"${p.size:,.2f}",
                f"{p.avg_entry_price:.1%}",
                f"{p.current_price:.1%}",
                f"[{pnl_style}]${p.unrealized_pnl:,.2f}[/{pnl_style}]",
                f"[{pnl_style}]{p.unrealized_pnl_pct:,.1f}%[/{pnl_style}]",
            )

        with self._console.capture() as capture:
            self._console.print(table)
        return capture.get()

    def render_watchlist(self, markets: list[Market]) -> str:
        """Render market watchlist.

        Args:
            markets: Markets to watch
        """
        table = Table(title="Watchlist")
        table.add_column("Market", style="cyan", max_width=50)
        table.add_column("Yes", justify="right")
        table.add_column("No", justify="right")
        table.add_column("Volume", justify="right")
        table.add_column("Liquidity", justify="right")

        for m in markets:
            yes_price = "N/A"
            no_price = "N/A"
            for o in m.outcomes:
                if o.outcome.lower() in ["yes", "true", "1"]:
                    yes_price = f"{o.price:.1%}"
                elif o.outcome.lower() in ["no", "false", "0"]:
                    no_price = f"{o.price:.1%}"

            table.add_row(
                m.question[:50] + "..." if len(m.question) > 50 else m.question,
                yes_price,
                no_price,
                f"${m.volume:,.0f}",
                f"${m.liquidity:,.0f}",
            )

        with self._console.capture() as capture:
            self._console.print(table)
        return capture.get()

    def render_alerts_panel(self, alerts: list[dict]) -> str:
        """Render active alerts panel.

        Args:
            alerts: List of alert dictionaries
        """
        if not alerts:
            return "No active alerts"

        lines = []
        for alert in alerts:
            status = "🔔" if alert.get("triggered") else "⏳"
            lines.append(
                f"{status} {alert.get('market', 'Unknown')[:30]}: "
                f"{alert.get('type', 'price')} {alert.get('threshold', 'N/A')}"
            )

        panel = Panel("\n".join(lines), title="Alerts")

        with self._console.capture() as capture:
            self._console.print(panel)
        return capture.get()

    def render_risk_metrics(
        self,
        max_drawdown: Decimal,
        var_95: Decimal,
        diversification_score: float,
        correlated_exposure: Decimal,
    ) -> str:
        """Render risk metrics panel.

        Args:
            max_drawdown: Maximum potential drawdown
            var_95: Value at Risk (95%)
            diversification_score: Diversification score (0-100)
            correlated_exposure: Exposure in correlated positions
        """
        table = Table(title="Risk Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        table.add_column("Status", style="bold")

        # Max drawdown
        dd_status = "✅" if max_drawdown < Decimal("0.25") else "⚠️" if max_drawdown < Decimal("0.40") else "🚨"
        table.add_row("Max Drawdown", f"{max_drawdown:.1%}", dd_status)

        # VaR
        table.add_row("VaR (95%)", f"${var_95:,.2f}", "")

        # Diversification
        div_status = "✅" if diversification_score >= 70 else "⚠️" if diversification_score >= 50 else "🚨"
        table.add_row("Diversification", f"{diversification_score:.0f}/100", div_status)

        # Correlated exposure
        corr_status = "✅" if correlated_exposure < Decimal("5000") else "⚠️"
        table.add_row("Correlated Exposure", f"${correlated_exposure:,.2f}", corr_status)

        with self._console.capture() as capture:
            self._console.print(table)
        return capture.get()

    def render_opportunities(self, opportunities: list[dict]) -> str:
        """Render opportunities panel.

        Args:
            opportunities: List of trading opportunities
        """
        if not opportunities:
            return "No opportunities detected"

        table = Table(title="Trading Opportunities")
        table.add_column("Type", style="magenta")
        table.add_column("Market", style="cyan", max_width=40)
        table.add_column("Details", style="green")
        table.add_column("Score", justify="right")

        for opp in opportunities[:10]:
            table.add_row(
                opp.get("type", "Unknown"),
                opp.get("market", "")[:40],
                opp.get("details", ""),
                f"{opp.get('score', 0):.0f}",
            )

        with self._console.capture() as capture:
            self._console.print(table)
        return capture.get()

    def render_full_dashboard(
        self,
        positions: list[Position],
        reserve_balance: Decimal,
        watchlist: list[Market],
        alerts: list[dict],
        risk_metrics: dict,
        opportunities: list[dict],
    ) -> str:
        """Render full dashboard with all widgets.

        Args:
            positions: Current positions
            reserve_balance: Cash reserves
            watchlist: Markets being watched
            alerts: Active alerts
            risk_metrics: Risk metric values
            opportunities: Trading opportunities
        """
        output = []
        output.append(f"\n{'=' * 60}")
        output.append(f"  POLYCLI DASHBOARD - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        output.append(f"{'=' * 60}\n")

        # Portfolio summary
        output.append(self.render_portfolio_summary(positions, reserve_balance))
        output.append("")

        # Positions
        if positions:
            output.append(self.render_positions_table(positions))
            output.append("")

        # Risk metrics
        output.append(
            self.render_risk_metrics(
                max_drawdown=risk_metrics.get("max_drawdown", Decimal(0)),
                var_95=risk_metrics.get("var_95", Decimal(0)),
                diversification_score=risk_metrics.get("diversification_score", 0),
                correlated_exposure=risk_metrics.get("correlated_exposure", Decimal(0)),
            )
        )
        output.append("")

        # Watchlist
        if watchlist:
            output.append(self.render_watchlist(watchlist[:5]))
            output.append("")

        # Alerts
        output.append(self.render_alerts_panel(alerts))
        output.append("")

        # Opportunities
        if opportunities:
            output.append(self.render_opportunities(opportunities))

        return "\n".join(output)

    def print_dashboard(self, content: str) -> None:
        """Print dashboard to console.

        Args:
            content: Dashboard content to print
        """
        self._console.print(content)

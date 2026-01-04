"""Time decay consideration for market selection.

Markets resolving in 30+ days have more opportunity for your thesis
to play out vs binary next-day events.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from polycli.models import Market


@dataclass
class TimeDecayProfile:
    """Profile of a market's time characteristics."""

    market: Market
    days_to_resolution: Optional[int]
    category: str  # "immediate", "short", "medium", "long"
    thesis_time_adequate: bool
    recommended_for_research: bool
    time_value_factor: float  # 0-1, higher = more time value
    notes: list[str]


class TimeDecayAnalyzer:
    """Analyze time decay and recommend markets based on resolution timing."""

    # Time categories
    IMMEDIATE = timedelta(days=2)  # Resolves in 0-2 days
    SHORT_TERM = timedelta(days=14)  # Resolves in 3-14 days
    MEDIUM_TERM = timedelta(days=60)  # Resolves in 15-60 days
    # LONG_TERM is anything beyond 60 days

    def __init__(
        self,
        min_days_for_research_edge: int = 7,
        prefer_medium_term: bool = True,
    ):
        """Initialize time decay analyzer.

        Args:
            min_days_for_research_edge: Minimum days for research-based edge
            prefer_medium_term: Whether to prefer medium-term markets
        """
        self._min_research_days = min_days_for_research_edge
        self._prefer_medium = prefer_medium_term

    def analyze_market(self, market: Market) -> TimeDecayProfile:
        """Analyze a market's time characteristics.

        Args:
            market: Market to analyze
        """
        notes = []

        # Calculate days to resolution
        days = market.days_until_resolution

        # Determine category
        if days is None:
            category = "unknown"
            notes.append("No resolution date - be cautious")
            thesis_time = False
            time_value = 0.3
        elif days <= 2:
            category = "immediate"
            notes.append("Binary event - news trading only")
            notes.append("Limited time for thesis to develop")
            thesis_time = False
            time_value = 0.1
        elif days <= 14:
            category = "short"
            notes.append("Short-term market - momentum matters")
            thesis_time = days >= self._min_research_days
            time_value = 0.4
        elif days <= 60:
            category = "medium"
            notes.append("Medium-term - ideal for research-based edge")
            thesis_time = True
            time_value = 0.8
        else:
            category = "long"
            notes.append("Long-term market - consider opportunity cost")
            notes.append("Capital may be locked for extended period")
            thesis_time = True
            time_value = 0.6

        # Check for research recommendations
        recommend_research = thesis_time and category in ["medium", "long"]

        if category == "immediate":
            notes.append("Consider: Do you have information edge for next-day events?")

        if days is not None and days > 180:
            notes.append("Very long horizon - consider if better opportunities exist")

        return TimeDecayProfile(
            market=market,
            days_to_resolution=days,
            category=category,
            thesis_time_adequate=thesis_time,
            recommended_for_research=recommend_research,
            time_value_factor=time_value,
            notes=notes,
        )

    def filter_by_time_preference(
        self,
        markets: list[Market],
        min_days: Optional[int] = None,
        max_days: Optional[int] = None,
        category: Optional[str] = None,
    ) -> list[Market]:
        """Filter markets by time preferences.

        Args:
            markets: Markets to filter
            min_days: Minimum days to resolution
            max_days: Maximum days to resolution
            category: Specific category ("immediate", "short", "medium", "long")
        """
        filtered = []

        for market in markets:
            days = market.days_until_resolution

            if days is None:
                continue

            if min_days is not None and days < min_days:
                continue

            if max_days is not None and days > max_days:
                continue

            if category is not None:
                profile = self.analyze_market(market)
                if profile.category != category:
                    continue

            filtered.append(market)

        return filtered

    def rank_for_research_trading(
        self, markets: list[Market]
    ) -> list[tuple[Market, TimeDecayProfile]]:
        """Rank markets by suitability for research-based trading.

        Prefers medium-term markets where research edge can develop.
        """
        profiles = [(m, self.analyze_market(m)) for m in markets]

        # Filter to research-suitable markets
        suitable = [(m, p) for m, p in profiles if p.recommended_for_research]

        # Sort by time value factor
        suitable.sort(key=lambda x: x[1].time_value_factor, reverse=True)

        return suitable

    def find_imminent_resolution(
        self, markets: list[Market], within_days: int = 7
    ) -> list[tuple[Market, int]]:
        """Find markets resolving soon.

        Useful for monitoring positions or finding late-stage opportunities.
        """
        imminent = []

        for market in markets:
            days = market.days_until_resolution
            if days is not None and days <= within_days:
                imminent.append((market, days))

        # Sort by days remaining
        imminent.sort(key=lambda x: x[1])
        return imminent

    def calculate_time_weighted_ev(
        self,
        expected_value: Decimal,
        days_to_resolution: int,
        annual_opportunity_cost: Decimal = Decimal("0.05"),
    ) -> Decimal:
        """Calculate time-weighted expected value.

        Accounts for opportunity cost of capital being locked up.

        Args:
            expected_value: Raw expected value of trade
            days_to_resolution: Days until market resolves
            annual_opportunity_cost: Annual return from alternatives
        """
        if days_to_resolution <= 0:
            return expected_value

        # Calculate opportunity cost
        daily_cost = annual_opportunity_cost / Decimal(365)
        time_cost = daily_cost * days_to_resolution

        # Adjust EV for time
        time_adjusted_ev = expected_value - time_cost

        return time_adjusted_ev

    def get_entry_timing_advice(
        self, market: Market, your_conviction: int
    ) -> str:
        """Get advice on when to enter a position.

        Args:
            market: Market to analyze
            your_conviction: Your conviction level 1-10
        """
        days = market.days_until_resolution

        if days is None:
            return "Unknown resolution date - consider waiting for clarity"

        if days <= 2:
            if your_conviction >= 8:
                return "High conviction on imminent event - consider entering now"
            else:
                return "Imminent resolution with moderate conviction - be cautious about sizing"

        if days <= 14:
            return (
                "Short-term market. If you have edge, enter now. "
                "If waiting for catalysts, be specific about what you're waiting for."
            )

        if days <= 60:
            if your_conviction >= 7:
                return "Medium-term with good conviction - can build position gradually"
            else:
                return (
                    "Medium-term market - consider waiting for more conviction "
                    "or a better entry point"
                )

        # Long-term
        return (
            f"Long-term market ({days} days). Consider:\n"
            "- Is capital better deployed elsewhere in the meantime?\n"
            "- Will there be better entry points as resolution approaches?\n"
            "- Are there catalysts to watch for before entry?"
        )

    def suggest_position_duration(
        self, entry_days_out: int, market: Market
    ) -> dict:
        """Suggest how long to hold a position.

        Args:
            entry_days_out: Days to resolution when you entered
            market: The market
        """
        current_days = market.days_until_resolution or 0

        return {
            "entry_days_out": entry_days_out,
            "current_days_out": current_days,
            "days_held": entry_days_out - current_days,
            "hold_to_resolution": current_days <= 3,
            "consider_exit_early": current_days > 30 and entry_days_out - current_days > 60,
            "advice": self._get_duration_advice(entry_days_out, current_days),
        }

    def _get_duration_advice(self, entry_days: int, current_days: int) -> str:
        """Generate advice based on position duration."""
        held = entry_days - current_days

        if current_days <= 3:
            return "Approaching resolution - hold for outcome unless thesis changed"

        if held > 60 and current_days > 30:
            return (
                "Held for 60+ days with 30+ days remaining. "
                "Consider whether thesis still valid or if capital needed elsewhere."
            )

        if current_days > entry_days * 2:
            return "Market has been extended - reassess thesis"

        return "Position duration within normal range"

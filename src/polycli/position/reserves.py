"""Reserve management for opportunities.

Reserve 30-40% for opportunities - the best trades come when
everyone else is tapped out.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class ReserveLevel(Enum):
    """Reserve level categories."""

    CRITICAL = "critical"  # Below minimum
    LOW = "low"  # Below target
    OPTIMAL = "optimal"  # At target
    HIGH = "high"  # Above target


@dataclass
class ReserveStatus:
    """Current reserve status."""

    reserve_balance: Decimal
    reserve_pct: Decimal
    target_pct: Decimal
    min_pct: Decimal
    level: ReserveLevel
    available_for_positions: Decimal
    available_for_opportunities: Decimal


class ReserveManager:
    """Manage reserve allocation for the bankroll."""

    def __init__(
        self,
        bankroll: Decimal,
        reserve_target_pct: Decimal = Decimal("0.35"),
        reserve_min_pct: Decimal = Decimal("0.20"),
        opportunity_fund_pct: Decimal = Decimal("0.15"),
    ):
        """Initialize reserve manager.

        Args:
            bankroll: Total bankroll
            reserve_target_pct: Target reserve percentage (default 35%)
            reserve_min_pct: Minimum reserve percentage (default 20%)
            opportunity_fund_pct: Additional fund for exceptional opportunities
        """
        self._bankroll = bankroll
        self._target_pct = reserve_target_pct
        self._min_pct = reserve_min_pct
        self._opportunity_pct = opportunity_fund_pct
        self._reserve_balance = bankroll * reserve_target_pct
        self._opportunity_fund = Decimal(0)  # Built up from wins

    @property
    def bankroll(self) -> Decimal:
        """Total bankroll."""
        return self._bankroll

    @bankroll.setter
    def bankroll(self, value: Decimal) -> None:
        """Update bankroll and adjust reserves proportionally."""
        if value < 0:
            raise ValueError("Bankroll cannot be negative")

        # Maintain reserve percentage
        if self._bankroll > 0:
            reserve_pct = self._reserve_balance / self._bankroll
            self._reserve_balance = value * reserve_pct

        self._bankroll = value

    def get_status(self, deployed_capital: Decimal) -> ReserveStatus:
        """Get current reserve status.

        Args:
            deployed_capital: Total capital in positions
        """
        total = deployed_capital + self._reserve_balance + self._opportunity_fund
        reserve_pct = self._reserve_balance / total if total > 0 else Decimal(1)

        if reserve_pct < self._min_pct:
            level = ReserveLevel.CRITICAL
        elif reserve_pct < self._target_pct:
            level = ReserveLevel.LOW
        elif reserve_pct < self._target_pct + Decimal("0.1"):
            level = ReserveLevel.OPTIMAL
        else:
            level = ReserveLevel.HIGH

        # Calculate available amounts
        min_reserve = total * self._min_pct
        available_positions = max(Decimal(0), self._reserve_balance - min_reserve)
        available_opportunities = self._opportunity_fund

        return ReserveStatus(
            reserve_balance=self._reserve_balance,
            reserve_pct=reserve_pct,
            target_pct=self._target_pct,
            min_pct=self._min_pct,
            level=level,
            available_for_positions=available_positions,
            available_for_opportunities=available_opportunities,
        )

    def allocate_to_position(self, amount: Decimal) -> tuple[bool, str]:
        """Allocate reserves to a new position.

        Args:
            amount: Amount to allocate

        Returns:
            (success, message)
        """
        if amount <= 0:
            return False, "Amount must be positive"

        remaining = self._reserve_balance - amount
        remaining_pct = remaining / self._bankroll if self._bankroll > 0 else Decimal(0)

        if remaining_pct < self._min_pct:
            max_available = self._reserve_balance - (self._bankroll * self._min_pct)
            return False, (
                f"Would breach minimum reserve ({self._min_pct:.0%}). "
                f"Max available: ${max(Decimal(0), max_available):.2f}"
            )

        self._reserve_balance = remaining
        return True, f"Allocated ${amount:.2f}. New reserve: ${self._reserve_balance:.2f}"

    def return_to_reserve(
        self, amount: Decimal, from_profit: bool = False
    ) -> str:
        """Return capital to reserves (from closed position).

        Args:
            amount: Amount to return
            from_profit: Whether this is profit (adds to opportunity fund)
        """
        if from_profit:
            # Split profit between reserve and opportunity fund
            to_reserve = amount * Decimal("0.7")
            to_opportunity = amount * Decimal("0.3")
            self._reserve_balance += to_reserve
            self._opportunity_fund += to_opportunity
            return (
                f"Added ${to_reserve:.2f} to reserves, "
                f"${to_opportunity:.2f} to opportunity fund"
            )
        else:
            self._reserve_balance += amount
            return f"Returned ${amount:.2f} to reserves"

    def request_opportunity_allocation(
        self, amount: Decimal, reason: str
    ) -> tuple[bool, Decimal, str]:
        """Request allocation from opportunity fund for exceptional trade.

        The opportunity fund is for when you find exceptional edge
        and want to size up beyond normal allocation.

        Args:
            amount: Requested amount
            reason: Why this is an exceptional opportunity

        Returns:
            (approved, allocated_amount, message)
        """
        if amount <= 0:
            return False, Decimal(0), "Amount must be positive"

        # Max 50% of opportunity fund per trade
        max_allocation = self._opportunity_fund * Decimal("0.5")
        allocated = min(amount, max_allocation)

        if allocated <= 0:
            return False, Decimal(0), "Opportunity fund is empty"

        self._opportunity_fund -= allocated
        return True, allocated, (
            f"Allocated ${allocated:.2f} from opportunity fund. "
            f"Remaining: ${self._opportunity_fund:.2f}"
        )

    def rebalance(self, deployed_capital: Decimal) -> str:
        """Rebalance reserves to target percentage.

        Call this after significant portfolio changes.

        Args:
            deployed_capital: Current capital in positions
        """
        total = deployed_capital + self._reserve_balance + self._opportunity_fund
        target_reserve = total * self._target_pct
        current_reserve = self._reserve_balance

        diff = target_reserve - current_reserve
        action = "increased" if diff > 0 else "decreased"
        self._reserve_balance = target_reserve

        return (
            f"Reserves {action} by ${abs(diff):.2f} to ${target_reserve:.2f} "
            f"({self._target_pct:.0%} of ${total:.2f})"
        )

    def calculate_max_position_size(
        self, deployed_capital: Decimal
    ) -> Decimal:
        """Calculate maximum size for a single new position.

        This considers:
        1. Minimum reserve requirement
        2. Not exceeding remaining allocation
        """
        total = deployed_capital + self._reserve_balance
        min_reserve = total * self._min_pct
        available = self._reserve_balance - min_reserve

        # Also cap at reasonable percentage of bankroll
        max_pct = Decimal("0.15")  # Max 15% per position
        max_single = self._bankroll * max_pct

        return min(available, max_single)

    def get_deployment_recommendation(
        self, deployed_capital: Decimal
    ) -> str:
        """Get recommendation on current deployment level."""
        total = deployed_capital + self._reserve_balance + self._opportunity_fund
        deployed_pct = deployed_capital / total if total > 0 else Decimal(0)
        reserve_pct = self._reserve_balance / total if total > 0 else Decimal(0)

        if reserve_pct > self._target_pct + Decimal("0.15"):
            return (
                f"Reserves high ({reserve_pct:.0%}). Consider deploying capital "
                "into good opportunities."
            )
        elif reserve_pct < self._min_pct:
            return (
                f"Reserves critical ({reserve_pct:.0%})! Reduce positions to "
                f"restore minimum {self._min_pct:.0%} reserve."
            )
        elif reserve_pct < self._target_pct:
            return (
                f"Reserves below target ({reserve_pct:.0%} vs {self._target_pct:.0%}). "
                "Be selective with new positions."
            )
        else:
            return (
                f"Deployment balanced: {deployed_pct:.0%} deployed, "
                f"{reserve_pct:.0%} in reserve."
            )

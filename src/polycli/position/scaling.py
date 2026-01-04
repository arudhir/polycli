"""Scale out strategy for winners.

Take 25-50% profit when a position doubles, let the rest ride
with house money.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from polycli.models import Position


@dataclass
class ScaleOutTarget:
    """A target level for scaling out of a position."""

    profit_pct: Decimal  # e.g., 100% = doubled
    sell_pct: Decimal  # e.g., 50% = sell half
    triggered: bool = False
    triggered_at: Optional[datetime] = None


@dataclass
class ScaleOutPlan:
    """Plan for scaling out of a winning position."""

    position: Position
    targets: list[ScaleOutTarget]
    remaining_size: Decimal
    realized_profit: Decimal
    house_money_size: Decimal  # Size riding on house money


class ScaleOutStrategy:
    """Manage scaling out of winning positions."""

    # Default scale-out levels
    DEFAULT_TARGETS = [
        ScaleOutTarget(profit_pct=Decimal("1.0"), sell_pct=Decimal("0.25")),  # 100% gain: sell 25%
        ScaleOutTarget(profit_pct=Decimal("2.0"), sell_pct=Decimal("0.25")),  # 200% gain: sell 25%
        ScaleOutTarget(profit_pct=Decimal("3.0"), sell_pct=Decimal("0.25")),  # 300% gain: sell 25%
    ]

    def __init__(
        self,
        default_targets: Optional[list[ScaleOutTarget]] = None,
        min_profit_to_scale: Decimal = Decimal("0.5"),  # 50% min profit
    ):
        """Initialize scale-out strategy.

        Args:
            default_targets: Default scale-out targets
            min_profit_to_scale: Minimum profit % before scaling starts
        """
        self._default_targets = default_targets or self.DEFAULT_TARGETS.copy()
        self._min_profit = min_profit_to_scale
        self._plans: dict[str, ScaleOutPlan] = {}

    def create_plan(
        self,
        position: Position,
        targets: Optional[list[ScaleOutTarget]] = None,
    ) -> ScaleOutPlan:
        """Create a scale-out plan for a position.

        Args:
            position: The position to create plan for
            targets: Custom targets (uses defaults if None)
        """
        plan_targets = targets or [
            ScaleOutTarget(profit_pct=t.profit_pct, sell_pct=t.sell_pct)
            for t in self._default_targets
        ]

        plan = ScaleOutPlan(
            position=position,
            targets=plan_targets,
            remaining_size=position.size,
            realized_profit=Decimal(0),
            house_money_size=Decimal(0),
        )

        key = f"{position.market_id}:{position.token_id}"
        self._plans[key] = plan
        return plan

    def check_position(self, position: Position) -> Optional[dict]:
        """Check if position should be scaled out.

        Returns dict with scale-out instructions if triggered, None otherwise.
        """
        key = f"{position.market_id}:{position.token_id}"
        plan = self._plans.get(key)

        if not plan:
            # No plan exists, check if we should create one
            if position.unrealized_pnl_pct >= self._min_profit * 100:
                plan = self.create_plan(position)
            else:
                return None

        # Calculate current profit percentage
        profit_pct = (position.current_price - position.avg_entry_price) / position.avg_entry_price

        # Check each target
        for target in plan.targets:
            if target.triggered:
                continue

            if profit_pct >= target.profit_pct:
                # Target triggered
                sell_size = plan.remaining_size * target.sell_pct
                target.triggered = True
                target.triggered_at = datetime.utcnow()

                plan.remaining_size -= sell_size
                plan.realized_profit += sell_size * (position.current_price - position.avg_entry_price)

                # Update house money tracking
                cost_basis_recovered = sell_size * position.avg_entry_price
                if plan.realized_profit >= position.cost_basis:
                    plan.house_money_size = plan.remaining_size

                return {
                    "action": "scale_out",
                    "sell_size": sell_size,
                    "sell_price": position.current_price,
                    "profit_pct": profit_pct,
                    "target_hit": target.profit_pct,
                    "remaining_size": plan.remaining_size,
                    "realized_profit": plan.realized_profit,
                    "is_house_money": plan.realized_profit >= position.cost_basis,
                }

        return None

    def get_plan(self, position: Position) -> Optional[ScaleOutPlan]:
        """Get existing scale-out plan for a position."""
        key = f"{position.market_id}:{position.token_id}"
        return self._plans.get(key)

    def update_position_price(self, position: Position) -> Optional[dict]:
        """Update position price and check for scale-out triggers."""
        key = f"{position.market_id}:{position.token_id}"
        plan = self._plans.get(key)

        if plan:
            plan.position = position

        return self.check_position(position)

    def calculate_break_even_price(self, position: Position) -> Decimal:
        """Calculate price needed to break even after scaling out.

        If you've already taken some profit, the remaining position
        might already be 'free' (house money).
        """
        key = f"{position.market_id}:{position.token_id}"
        plan = self._plans.get(key)

        if not plan or plan.remaining_size == 0:
            return position.avg_entry_price

        # Cost basis minus realized profit
        remaining_cost = position.cost_basis - plan.realized_profit
        if remaining_cost <= 0:
            return Decimal(0)  # Already playing with house money

        return remaining_cost / plan.remaining_size

    def is_house_money(self, position: Position) -> bool:
        """Check if remaining position is playing with house money."""
        key = f"{position.market_id}:{position.token_id}"
        plan = self._plans.get(key)

        if not plan:
            return False

        return plan.realized_profit >= position.cost_basis

    def get_scaling_recommendation(self, position: Position) -> str:
        """Get recommendation for scaling this position."""
        profit_pct = position.unrealized_pnl_pct / 100

        if profit_pct < self._min_profit:
            return f"Hold - only {profit_pct:.0%} profit, need {self._min_profit:.0%} to start scaling"

        plan = self.get_plan(position)
        if not plan:
            return "Consider creating a scale-out plan for this winner"

        if self.is_house_money(position):
            return f"Playing with house money! Remaining {plan.remaining_size} shares are free"

        next_target = None
        for target in plan.targets:
            if not target.triggered:
                next_target = target
                break

        if next_target:
            return (
                f"Next target: {next_target.profit_pct:.0%} profit - "
                f"sell {next_target.sell_pct:.0%} of remaining position"
            )

        return "All scale-out targets hit. Let remainder ride or close entirely."

    def suggest_targets_for_edge(
        self,
        estimated_prob: Decimal,
        market_price: Decimal,
    ) -> list[ScaleOutTarget]:
        """Suggest scale-out targets based on perceived edge.

        Higher edge = more aggressive scaling (let winners run).
        Lower edge = take profits earlier.
        """
        edge = estimated_prob - market_price

        if edge > Decimal("0.2"):
            # High conviction - let it run longer
            return [
                ScaleOutTarget(profit_pct=Decimal("1.5"), sell_pct=Decimal("0.20")),
                ScaleOutTarget(profit_pct=Decimal("2.5"), sell_pct=Decimal("0.25")),
                ScaleOutTarget(profit_pct=Decimal("4.0"), sell_pct=Decimal("0.25")),
            ]
        elif edge > Decimal("0.1"):
            # Medium conviction - balanced approach
            return [
                ScaleOutTarget(profit_pct=Decimal("1.0"), sell_pct=Decimal("0.25")),
                ScaleOutTarget(profit_pct=Decimal("2.0"), sell_pct=Decimal("0.25")),
                ScaleOutTarget(profit_pct=Decimal("3.0"), sell_pct=Decimal("0.25")),
            ]
        else:
            # Lower conviction - take profits earlier
            return [
                ScaleOutTarget(profit_pct=Decimal("0.5"), sell_pct=Decimal("0.33")),
                ScaleOutTarget(profit_pct=Decimal("1.0"), sell_pct=Decimal("0.33")),
                ScaleOutTarget(profit_pct=Decimal("1.5"), sell_pct=Decimal("0.34")),
            ]

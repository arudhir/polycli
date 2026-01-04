"""Define exit strategy before entry.

Define stop-loss and take-profit levels before placing a trade,
then stick to them.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from polycli.models import Position


class ExitReason(str, Enum):
    """Reason for exiting a position."""

    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TIME_STOP = "time_stop"
    THESIS_INVALIDATED = "thesis_invalidated"
    REBALANCING = "rebalancing"
    MARKET_CLOSING = "market_closing"
    MANUAL = "manual"


@dataclass
class ExitPlan:
    """Exit plan for a position."""

    position_id: str
    stop_loss: Decimal
    take_profit: Decimal
    time_stop_date: Optional[datetime]
    thesis_checkpoints: list[str]
    created_at: datetime
    notes: str


@dataclass
class ExitSignal:
    """Signal that exit conditions have been met."""

    position: Position
    reason: ExitReason
    triggered_at: datetime
    exit_price: Decimal
    pnl: Decimal
    pnl_pct: Decimal
    notes: str


class ExitStrategyManager:
    """Manage exit strategies for positions."""

    def __init__(
        self,
        default_stop_loss_pct: Decimal = Decimal("0.30"),
        default_take_profit_pct: Decimal = Decimal("1.00"),
    ):
        """Initialize exit strategy manager.

        Args:
            default_stop_loss_pct: Default stop loss as % of entry (e.g., 30% loss)
            default_take_profit_pct: Default take profit as % gain (e.g., 100% gain)
        """
        self._default_stop = default_stop_loss_pct
        self._default_profit = default_take_profit_pct
        self._exit_plans: dict[str, ExitPlan] = {}

    def create_exit_plan(
        self,
        position: Position,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        time_stop_days: Optional[int] = None,
        thesis_checkpoints: Optional[list[str]] = None,
        notes: str = "",
    ) -> ExitPlan:
        """Create an exit plan for a position.

        Args:
            position: Position to create plan for
            stop_loss: Price to exit at loss (default calculated from entry)
            take_profit: Price to exit at profit (default calculated from entry)
            time_stop_days: Days after which to exit regardless
            thesis_checkpoints: Events that would invalidate thesis
            notes: Additional notes
        """
        # Calculate default levels
        if stop_loss is None:
            # Stop loss at X% below entry price
            stop_loss = position.avg_entry_price * (1 - self._default_stop)

        if take_profit is None:
            # Take profit when price indicates X% profit
            take_profit = min(
                Decimal("0.95"),  # Cap at 95c
                position.avg_entry_price + (position.avg_entry_price * self._default_profit)
            )

        time_stop = None
        if time_stop_days:
            time_stop = datetime.utcnow() + timedelta(days=time_stop_days)

        plan = ExitPlan(
            position_id=f"{position.market_id}:{position.token_id}",
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_stop_date=time_stop,
            thesis_checkpoints=thesis_checkpoints or [],
            created_at=datetime.utcnow(),
            notes=notes,
        )

        self._exit_plans[plan.position_id] = plan
        return plan

    def check_exit_signals(self, position: Position) -> Optional[ExitSignal]:
        """Check if any exit conditions are met.

        Args:
            position: Position to check
        """
        plan_id = f"{position.market_id}:{position.token_id}"
        plan = self._exit_plans.get(plan_id)

        if not plan:
            return None

        # Check stop loss
        if position.current_price <= plan.stop_loss:
            return ExitSignal(
                position=position,
                reason=ExitReason.STOP_LOSS,
                triggered_at=datetime.utcnow(),
                exit_price=position.current_price,
                pnl=position.unrealized_pnl,
                pnl_pct=position.unrealized_pnl_pct,
                notes=f"Price {position.current_price:.2%} hit stop loss {plan.stop_loss:.2%}",
            )

        # Check take profit
        if position.current_price >= plan.take_profit:
            return ExitSignal(
                position=position,
                reason=ExitReason.TAKE_PROFIT,
                triggered_at=datetime.utcnow(),
                exit_price=position.current_price,
                pnl=position.unrealized_pnl,
                pnl_pct=position.unrealized_pnl_pct,
                notes=f"Price {position.current_price:.2%} hit take profit {plan.take_profit:.2%}",
            )

        # Check time stop
        if plan.time_stop_date and datetime.utcnow() >= plan.time_stop_date:
            return ExitSignal(
                position=position,
                reason=ExitReason.TIME_STOP,
                triggered_at=datetime.utcnow(),
                exit_price=position.current_price,
                pnl=position.unrealized_pnl,
                pnl_pct=position.unrealized_pnl_pct,
                notes=f"Time stop reached ({plan.time_stop_date})",
            )

        return None

    def get_exit_plan(self, position: Position) -> Optional[ExitPlan]:
        """Get exit plan for a position."""
        plan_id = f"{position.market_id}:{position.token_id}"
        return self._exit_plans.get(plan_id)

    def update_exit_plan(
        self,
        position: Position,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> Optional[ExitPlan]:
        """Update exit levels for a position.

        Args:
            position: Position to update
            stop_loss: New stop loss level
            take_profit: New take profit level
        """
        plan_id = f"{position.market_id}:{position.token_id}"
        plan = self._exit_plans.get(plan_id)

        if not plan:
            return None

        if stop_loss is not None:
            plan.stop_loss = stop_loss
        if take_profit is not None:
            plan.take_profit = take_profit

        return plan

    def trail_stop_loss(
        self,
        position: Position,
        trail_pct: Decimal = Decimal("0.15"),
    ) -> Optional[ExitPlan]:
        """Move stop loss up as position profits (trailing stop).

        Args:
            position: Position to update
            trail_pct: Trail distance as % below current price
        """
        plan_id = f"{position.market_id}:{position.token_id}"
        plan = self._exit_plans.get(plan_id)

        if not plan:
            return None

        # Calculate trailing stop
        new_stop = position.current_price * (1 - trail_pct)

        # Only move stop up, never down
        if new_stop > plan.stop_loss:
            plan.stop_loss = new_stop
            plan.notes += f" | Trailed to {new_stop:.2%} on {datetime.utcnow().date()}"

        return plan

    def mark_thesis_invalidated(
        self,
        position: Position,
        reason: str,
    ) -> ExitSignal:
        """Mark position for exit due to thesis invalidation.

        Args:
            position: Position to exit
            reason: Why thesis is invalidated
        """
        return ExitSignal(
            position=position,
            reason=ExitReason.THESIS_INVALIDATED,
            triggered_at=datetime.utcnow(),
            exit_price=position.current_price,
            pnl=position.unrealized_pnl,
            pnl_pct=position.unrealized_pnl_pct,
            notes=f"Thesis invalidated: {reason}",
        )

    def calculate_exit_levels(
        self,
        entry_price: Decimal,
        your_probability: Decimal,
        risk_reward_ratio: Decimal = Decimal("2.0"),
    ) -> dict:
        """Calculate recommended exit levels based on edge.

        Args:
            entry_price: Price you're entering at
            your_probability: Your probability estimate
            risk_reward_ratio: Desired risk/reward ratio
        """
        # Calculate edge
        edge = your_probability - entry_price

        # Stop loss: Where edge becomes negative
        # If you think it's 60% and bought at 50%, stop at 40%
        stop_loss = your_probability - edge  # Back to market price

        # Take profit based on risk/reward
        # Risk = entry - stop loss
        # Reward = take profit - entry
        risk = entry_price - stop_loss
        reward = risk * risk_reward_ratio
        take_profit = entry_price + reward

        # Cap at reasonable levels
        stop_loss = max(Decimal("0.05"), stop_loss)
        take_profit = min(Decimal("0.95"), take_profit)

        return {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk": entry_price - stop_loss,
            "reward": take_profit - entry_price,
            "risk_reward": risk_reward_ratio,
            "edge": edge,
        }

    def get_pre_trade_checklist(self, entry_price: Decimal) -> list[str]:
        """Get checklist of exit strategy items to define before trading.

        Args:
            entry_price: Planned entry price
        """
        return [
            f"Stop loss level: At what price will you exit at a loss? (suggested: {entry_price * Decimal('0.7'):.2%})",
            f"Take profit level: At what price will you take profits? (suggested: {min(Decimal('0.95'), entry_price * Decimal('1.5')):.2%})",
            "Time stop: How long will you hold if nothing happens?",
            "Thesis checkpoints: What events would invalidate your thesis?",
            "Partial exit plan: Will you scale out on the way up?",
            "Worst case acceptance: Can you emotionally handle the max loss?",
        ]

    def remove_exit_plan(self, position: Position) -> bool:
        """Remove exit plan for a closed position."""
        plan_id = f"{position.market_id}:{position.token_id}"
        if plan_id in self._exit_plans:
            del self._exit_plans[plan_id]
            return True
        return False


from datetime import timedelta

"""Use limit orders aggressively.

Set limits at your edge threshold - if Trump hits 45c and you think
fair value is 52c, buy there, don't chase 48c.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrderStatus(str, Enum):
    """Status of a limit order."""

    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class LimitOrderPlan:
    """A planned limit order."""

    market_id: str
    token_id: str
    side: str  # "buy" or "sell"
    price: Decimal
    size: Decimal
    edge_at_price: Decimal
    expiry: Optional[datetime]
    notes: str


@dataclass
class LimitOrderAnalysis:
    """Analysis of where to set limit orders."""

    fair_value: Decimal
    current_price: Decimal
    edge: Decimal
    recommended_buy_limit: Decimal
    recommended_sell_limit: Decimal
    buy_size_at_limit: Decimal
    expected_fill_probability: float
    notes: list[str]


class LimitOrderStrategy:
    """Strategy for setting limit orders at edge thresholds."""

    def __init__(
        self,
        min_edge_to_trade: Decimal = Decimal("0.05"),
        default_order_size_pct: Decimal = Decimal("0.05"),
        bankroll: Decimal = Decimal("10000"),
    ):
        """Initialize limit order strategy.

        Args:
            min_edge_to_trade: Minimum edge required to place order
            default_order_size_pct: Default order size as % of bankroll
            bankroll: Total bankroll for sizing
        """
        self._min_edge = min_edge_to_trade
        self._default_size_pct = default_order_size_pct
        self._bankroll = bankroll
        self._pending_orders: dict[str, LimitOrderPlan] = {}

    def calculate_limit_prices(
        self,
        fair_value: Decimal,
        current_price: Decimal,
        volatility: Optional[float] = None,
    ) -> LimitOrderAnalysis:
        """Calculate optimal limit order prices based on fair value.

        Args:
            fair_value: Your estimated fair value
            current_price: Current market price
            volatility: Optional historical volatility estimate
        """
        edge = fair_value - current_price
        notes = []

        # Buy limit: price where you have minimum acceptable edge
        buy_limit = fair_value - self._min_edge

        # Sell limit: price where selling becomes attractive
        sell_limit = fair_value + self._min_edge

        # Adjust for volatility if provided
        if volatility and volatility > 0.2:
            # Higher volatility = wider limits (wait for better prices)
            vol_adjustment = Decimal(str(volatility * 0.1))
            buy_limit -= vol_adjustment
            sell_limit += vol_adjustment
            notes.append(f"Adjusted limits for high volatility ({volatility:.0%})")

        # Ensure limits are in valid range
        buy_limit = max(Decimal("0.01"), min(Decimal("0.99"), buy_limit))
        sell_limit = max(Decimal("0.01"), min(Decimal("0.99"), sell_limit))

        # Calculate size at limit
        edge_at_buy = fair_value - buy_limit
        size_at_limit = self._calculate_size_for_edge(edge_at_buy)

        # Estimate fill probability (rough heuristic)
        if current_price > buy_limit:
            price_gap = float(current_price - buy_limit)
            fill_prob = max(0.1, 0.8 - price_gap * 2)
        else:
            fill_prob = 0.9  # Already at or below limit

        # Add recommendations
        if edge > self._min_edge:
            notes.append("Current price has sufficient edge - consider market order")
        elif edge > 0:
            notes.append(f"Current edge ({edge:.1%}) below threshold - use limit order")
        else:
            notes.append("Market is at or above fair value - only sell or wait")

        if buy_limit < current_price * Decimal("0.9"):
            notes.append("Buy limit is far from current price - may not fill")

        return LimitOrderAnalysis(
            fair_value=fair_value,
            current_price=current_price,
            edge=edge,
            recommended_buy_limit=buy_limit,
            recommended_sell_limit=sell_limit,
            buy_size_at_limit=size_at_limit,
            expected_fill_probability=fill_prob,
            notes=notes,
        )

    def _calculate_size_for_edge(self, edge: Decimal) -> Decimal:
        """Calculate position size based on edge."""
        if edge <= 0:
            return Decimal(0)

        # Scale size with edge (more edge = larger size)
        edge_multiplier = min(Decimal(3), edge / self._min_edge)
        base_size = self._bankroll * self._default_size_pct
        return base_size * edge_multiplier

    def create_limit_order_plan(
        self,
        market_id: str,
        token_id: str,
        fair_value: Decimal,
        current_price: Decimal,
        side: str = "buy",
        custom_size: Optional[Decimal] = None,
        expiry_hours: Optional[int] = None,
    ) -> LimitOrderPlan:
        """Create a limit order plan.

        Args:
            market_id: Market identifier
            token_id: Token identifier
            fair_value: Your fair value estimate
            current_price: Current market price
            side: "buy" or "sell"
            custom_size: Override calculated size
            expiry_hours: Hours until order expires
        """
        analysis = self.calculate_limit_prices(fair_value, current_price)

        if side == "buy":
            price = analysis.recommended_buy_limit
            edge_at_price = fair_value - price
        else:
            price = analysis.recommended_sell_limit
            edge_at_price = price - fair_value

        size = custom_size or analysis.buy_size_at_limit
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours) if expiry_hours else None

        plan = LimitOrderPlan(
            market_id=market_id,
            token_id=token_id,
            side=side,
            price=price,
            size=size,
            edge_at_price=edge_at_price,
            expiry=expiry,
            notes=f"Fair value: {fair_value:.2%}, Edge at limit: {edge_at_price:.2%}",
        )

        # Store pending order
        order_key = f"{market_id}:{token_id}:{side}"
        self._pending_orders[order_key] = plan

        return plan

    def create_layered_orders(
        self,
        market_id: str,
        token_id: str,
        fair_value: Decimal,
        current_price: Decimal,
        num_layers: int = 3,
        total_size: Optional[Decimal] = None,
    ) -> list[LimitOrderPlan]:
        """Create layered limit orders at different price levels.

        Splits order into multiple levels to improve average fill price.

        Args:
            market_id: Market identifier
            token_id: Token identifier
            fair_value: Your fair value estimate
            current_price: Current market price
            num_layers: Number of order layers
            total_size: Total size across all layers
        """
        analysis = self.calculate_limit_prices(fair_value, current_price)
        total = total_size or analysis.buy_size_at_limit
        size_per_layer = total / num_layers

        orders = []
        base_limit = analysis.recommended_buy_limit

        for i in range(num_layers):
            # Each layer is progressively better price (for buyer)
            layer_discount = Decimal(str(i * 0.02))  # 2% between layers
            layer_price = base_limit - layer_discount

            if layer_price < Decimal("0.01"):
                continue

            order = LimitOrderPlan(
                market_id=market_id,
                token_id=token_id,
                side="buy",
                price=layer_price,
                size=size_per_layer,
                edge_at_price=fair_value - layer_price,
                expiry=None,
                notes=f"Layer {i+1}/{num_layers}",
            )
            orders.append(order)

        return orders

    def should_chase_price(
        self,
        fair_value: Decimal,
        current_price: Decimal,
        your_limit: Decimal,
        urgency: str = "low",
    ) -> dict:
        """Determine if you should raise your limit to chase price.

        Args:
            fair_value: Your fair value estimate
            current_price: Current market price
            your_limit: Your current limit price
            urgency: "low", "medium", "high" (e.g., imminent news)
        """
        edge_at_current = fair_value - current_price
        edge_at_limit = fair_value - your_limit

        result = {
            "should_chase": False,
            "recommended_action": "",
            "edge_sacrifice": edge_at_limit - edge_at_current,
        }

        if edge_at_current < self._min_edge / 2:
            result["recommended_action"] = "Don't chase - insufficient edge at current price"
            return result

        if urgency == "high" and edge_at_current >= self._min_edge:
            result["should_chase"] = True
            result["recommended_action"] = (
                f"Chase to {current_price:.2%} - urgent and still has "
                f"{edge_at_current:.1%} edge"
            )
        elif urgency == "medium" and edge_at_current >= self._min_edge * Decimal("1.5"):
            result["should_chase"] = True
            result["recommended_action"] = (
                f"Consider chasing to {current_price:.2%} - good edge "
                f"({edge_at_current:.1%}) justifies urgency"
            )
        else:
            result["recommended_action"] = (
                f"Keep limit at {your_limit:.2%} - don't sacrifice edge "
                f"({edge_at_limit:.1%} vs {edge_at_current:.1%})"
            )

        return result

    def get_pending_orders(self) -> list[LimitOrderPlan]:
        """Get all pending order plans."""
        return list(self._pending_orders.values())

    def cancel_order_plan(self, market_id: str, token_id: str, side: str) -> bool:
        """Cancel a pending order plan."""
        key = f"{market_id}:{token_id}:{side}"
        if key in self._pending_orders:
            del self._pending_orders[key]
            return True
        return False


# Need to import timedelta
from datetime import timedelta

"""Asymmetric hedging strategies.

If you're long on a 70% favorite, don't hedge 50/50 - buy cheap
insurance on the other side when it spikes to 85%+.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from polycli.models import Market, Position


@dataclass
class HedgeOpportunity:
    """An opportunity to hedge an existing position."""

    original_position: Position
    hedge_market: Market
    hedge_outcome: str
    hedge_price: Decimal
    recommended_hedge_size: Decimal
    hedge_cost: Decimal
    max_loss_after_hedge: Decimal
    risk_reduction_pct: float
    notes: list[str]


@dataclass
class HedgeAnalysis:
    """Analysis of hedging needs for a position."""

    position: Position
    current_risk: Decimal
    should_hedge: bool
    optimal_hedge_ratio: Decimal
    hedge_trigger_price: Decimal
    available_hedges: list[HedgeOpportunity]


class HedgingCalculator:
    """Calculate optimal hedging strategies."""

    def __init__(
        self,
        max_hedge_cost_pct: Decimal = Decimal("0.1"),
        hedge_trigger_confidence: Decimal = Decimal("0.85"),
        min_risk_reduction: float = 0.3,
    ):
        """Initialize hedging calculator.

        Args:
            max_hedge_cost_pct: Maximum hedge cost as % of position
            hedge_trigger_confidence: Price that triggers hedge consideration
            min_risk_reduction: Minimum risk reduction to recommend hedge
        """
        self._max_cost_pct = max_hedge_cost_pct
        self._trigger_confidence = hedge_trigger_confidence
        self._min_risk_reduction = min_risk_reduction

    def analyze_position(
        self,
        position: Position,
        related_markets: Optional[list[Market]] = None,
    ) -> HedgeAnalysis:
        """Analyze hedging needs for a position.

        Args:
            position: Position to analyze
            related_markets: Markets that could serve as hedges
        """
        # Calculate current risk (max loss)
        current_risk = position.cost_basis

        # Determine if hedging is appropriate
        # Only hedge when position has run up significantly
        should_hedge = position.current_price >= float(self._trigger_confidence)

        # Calculate optimal hedge ratio
        # Asymmetric: Don't hedge 50/50, hedge proportionally to confidence excess
        if position.current_price > Decimal("0.5"):
            excess_confidence = position.current_price - Decimal("0.5")
            optimal_ratio = min(Decimal("0.5"), excess_confidence)
        else:
            optimal_ratio = Decimal("0")

        # Calculate price that should trigger hedging
        trigger_price = self._trigger_confidence

        # Find available hedges
        hedges = []
        if related_markets:
            for market in related_markets:
                hedge = self._evaluate_hedge_market(position, market)
                if hedge:
                    hedges.append(hedge)

        return HedgeAnalysis(
            position=position,
            current_risk=current_risk,
            should_hedge=should_hedge,
            optimal_hedge_ratio=optimal_ratio,
            hedge_trigger_price=trigger_price,
            available_hedges=hedges,
        )

    def _evaluate_hedge_market(
        self,
        position: Position,
        hedge_market: Market,
    ) -> Optional[HedgeOpportunity]:
        """Evaluate a market as a potential hedge."""
        # Find opposite outcome
        hedge_outcome = None
        hedge_price = None

        for outcome in hedge_market.outcomes:
            # Look for NO or opposite outcome
            if outcome.outcome.lower() in ["no", "false", "0"]:
                hedge_outcome = outcome.outcome
                hedge_price = outcome.price
                break

        if not hedge_outcome or not hedge_price:
            return None

        # Calculate hedge size for insurance
        # Buy enough to cover potential loss if original position loses
        potential_loss = position.cost_basis
        hedge_payout = Decimal(1) - hedge_price  # What you get if hedge wins

        if hedge_payout <= 0:
            return None

        # Size hedge to recover some of potential loss
        hedge_size = (potential_loss * Decimal("0.5")) / hedge_payout
        hedge_cost = hedge_size * hedge_price

        # Check if hedge cost is acceptable
        if hedge_cost > position.cost_basis * self._max_cost_pct:
            hedge_size = (position.cost_basis * self._max_cost_pct) / hedge_price
            hedge_cost = hedge_size * hedge_price

        # Calculate max loss after hedge
        # Worst case: original loses, hedge wins
        max_loss = position.cost_basis - (hedge_size * hedge_payout)

        # Calculate risk reduction
        risk_reduction = float(1 - max_loss / position.cost_basis)

        notes = []
        if hedge_price < Decimal("0.15"):
            notes.append("Cheap insurance - consider larger hedge size")
        if hedge_price > Decimal("0.30"):
            notes.append("Expensive hedge - consider waiting for better price")
        if risk_reduction < self._min_risk_reduction:
            notes.append("Limited risk reduction - hedge may not be worth cost")

        return HedgeOpportunity(
            original_position=position,
            hedge_market=hedge_market,
            hedge_outcome=hedge_outcome,
            hedge_price=hedge_price,
            recommended_hedge_size=hedge_size,
            hedge_cost=hedge_cost,
            max_loss_after_hedge=max(Decimal(0), max_loss),
            risk_reduction_pct=risk_reduction,
            notes=notes,
        )

    def calculate_asymmetric_hedge(
        self,
        position: Position,
        hedge_price: Decimal,
        target_risk_reduction: Decimal = Decimal("0.5"),
    ) -> dict:
        """Calculate asymmetric hedge size.

        Don't hedge 50/50 - buy cheap insurance when the other side spikes.

        Args:
            position: Position to hedge
            hedge_price: Current price of hedge (insurance) outcome
            target_risk_reduction: Target % reduction in max loss
        """
        # Cost of full insurance
        hedge_payout = Decimal(1) - hedge_price
        potential_loss = position.cost_basis

        # Size needed for target risk reduction
        target_loss = potential_loss * (1 - target_risk_reduction)
        needed_recovery = potential_loss - target_loss

        if hedge_payout > 0:
            hedge_size = needed_recovery / hedge_payout
        else:
            hedge_size = Decimal(0)

        hedge_cost = hedge_size * hedge_price

        # Calculate effective odds
        # If position wins: gain from position, lose hedge cost
        # If position loses: lose position, gain from hedge
        position_win_profit = position.size - position.cost_basis - hedge_cost
        position_lose_loss = position.cost_basis - (hedge_size * hedge_payout)

        return {
            "hedge_size": hedge_size,
            "hedge_cost": hedge_cost,
            "max_loss_if_wrong": max(Decimal(0), position_lose_loss),
            "profit_if_right": position_win_profit,
            "risk_reduction": target_risk_reduction,
            "breakeven_hedge_price": self._calculate_hedge_breakeven(
                position, target_risk_reduction
            ),
            "recommendation": self._get_hedge_recommendation(
                position.current_price, hedge_price
            ),
        }

    def _calculate_hedge_breakeven(
        self,
        position: Position,
        risk_reduction: Decimal,
    ) -> Decimal:
        """Calculate price at which hedging becomes worthwhile."""
        # Breakeven is when hedge cost equals expected risk reduction value
        # This depends on your probability estimate
        # Simplified: hedge when price < (1 - position confidence) * risk_reduction
        return (1 - position.current_price) * risk_reduction

    def _get_hedge_recommendation(
        self,
        position_price: Decimal,
        hedge_price: Decimal,
    ) -> str:
        """Get recommendation on whether to hedge now."""
        if position_price < Decimal("0.7"):
            return "Position not confident enough to hedge yet - wait for it to run"

        if hedge_price > Decimal("0.25"):
            return "Hedge is expensive - wait for spike in your favor to get cheaper insurance"

        if position_price >= Decimal("0.85") and hedge_price <= Decimal("0.15"):
            return "Good time to hedge - position confident, insurance cheap"

        return "Consider partial hedge - position moderately confident"

    def find_hedge_timing(
        self,
        position: Position,
        price_history: list[dict],
    ) -> dict:
        """Analyze price history to find optimal hedge timing.

        Best time to hedge is when position is most confident
        (hedge is cheapest).
        """
        if not price_history:
            return {"error": "No price history available"}

        prices = [Decimal(str(p.get("price", 0))) for p in price_history]

        max_price = max(prices)
        min_hedge_price = Decimal(1) - max_price

        current_price = position.current_price
        current_hedge_price = Decimal(1) - current_price

        return {
            "current_position_price": current_price,
            "current_hedge_price": current_hedge_price,
            "best_historical_position_price": max_price,
            "cheapest_hedge_price_seen": min_hedge_price,
            "current_vs_best": float(current_price / max_price) if max_price > 0 else 0,
            "recommendation": (
                "Hedge now"
                if current_price >= max_price * Decimal("0.95")
                else f"Wait - position was as high as {max_price:.0%}"
            ),
        }

"""Create synthetic positions.

Use correlated markets to build exposures that aren't directly available.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from polycli.models import Market, Position


@dataclass
class SyntheticLeg:
    """A leg of a synthetic position."""

    market_id: str
    market_question: str
    token_id: str
    outcome: str
    side: str  # "long" or "short"
    weight: Decimal
    price: Decimal


@dataclass
class SyntheticPosition:
    """A synthetic position built from multiple markets."""

    name: str
    description: str
    legs: list[SyntheticLeg]
    target_exposure: str
    estimated_correlation: float
    total_cost: Decimal
    max_profit: Decimal
    max_loss: Decimal
    notes: list[str]


class SyntheticPositionBuilder:
    """Build synthetic positions from correlated markets."""

    def __init__(self):
        """Initialize synthetic position builder."""
        self._positions: dict[str, SyntheticPosition] = {}

    def create_spread(
        self,
        long_market: Market,
        short_market: Market,
        size: Decimal,
    ) -> SyntheticPosition:
        """Create a spread between two correlated markets.

        A spread profits from the relative performance, not absolute.

        Args:
            long_market: Market to go long
            short_market: Market to go short
            size: Position size per leg
        """
        if not long_market.outcomes or not short_market.outcomes:
            raise ValueError("Markets must have outcomes")

        long_price = long_market.outcomes[0].price
        short_price = short_market.outcomes[0].price

        legs = [
            SyntheticLeg(
                market_id=long_market.condition_id,
                market_question=long_market.question,
                token_id=long_market.outcomes[0].token_id,
                outcome=long_market.outcomes[0].outcome,
                side="long",
                weight=Decimal(1),
                price=long_price,
            ),
            SyntheticLeg(
                market_id=short_market.condition_id,
                market_question=short_market.question,
                token_id=short_market.outcomes[0].token_id,
                outcome=short_market.outcomes[0].outcome,
                side="short",
                weight=Decimal(1),
                price=short_price,
            ),
        ]

        total_cost = (long_price + (Decimal(1) - short_price)) * size

        # Max profit if long wins, short loses
        max_profit = (Decimal(1) - long_price + short_price) * size

        # Max loss if long loses, short wins
        max_loss = (long_price + (Decimal(1) - short_price)) * size

        return SyntheticPosition(
            name=f"Spread: {long_market.question[:30]} vs {short_market.question[:30]}",
            description=f"Long {long_market.question[:50]}, Short {short_market.question[:50]}",
            legs=legs,
            target_exposure="Relative outperformance",
            estimated_correlation=0.7,  # Would calculate from actual data
            total_cost=total_cost,
            max_profit=max_profit,
            max_loss=max_loss,
            notes=[
                "Profits if long market outperforms short market",
                "Reduces exposure to common factors",
            ],
        )

    def create_basket(
        self,
        markets: list[tuple[Market, Decimal]],
        basket_name: str,
    ) -> SyntheticPosition:
        """Create a basket position from multiple markets.

        A basket provides diversified exposure to a theme.

        Args:
            markets: List of (Market, weight) tuples
            basket_name: Name for the basket
        """
        legs = []
        total_cost = Decimal(0)

        for market, weight in markets:
            if not market.outcomes:
                continue

            price = market.outcomes[0].price
            legs.append(
                SyntheticLeg(
                    market_id=market.condition_id,
                    market_question=market.question,
                    token_id=market.outcomes[0].token_id,
                    outcome=market.outcomes[0].outcome,
                    side="long",
                    weight=weight,
                    price=price,
                )
            )
            total_cost += price * weight

        # Weighted average outcomes
        max_profit = sum((Decimal(1) - leg.price) * leg.weight for leg in legs)
        max_loss = sum(leg.price * leg.weight for leg in legs)

        return SyntheticPosition(
            name=basket_name,
            description=f"Basket of {len(legs)} markets",
            legs=legs,
            target_exposure=f"Diversified {basket_name} exposure",
            estimated_correlation=0.5,
            total_cost=total_cost,
            max_profit=max_profit,
            max_loss=max_loss,
            notes=[
                f"Basket contains {len(legs)} positions",
                "Reduces idiosyncratic risk through diversification",
            ],
        )

    def create_collar(
        self,
        base_position: Position,
        protection_market: Market,
        protection_amount: Decimal,
    ) -> SyntheticPosition:
        """Create a collar to limit downside on existing position.

        A collar adds protection by buying a correlated opposite position.

        Args:
            base_position: Existing position to protect
            protection_market: Market to use for protection
            protection_amount: Amount to spend on protection
        """
        if not protection_market.outcomes:
            raise ValueError("Protection market must have outcomes")

        # Find opposite outcome
        protection_outcome = None
        for outcome in protection_market.outcomes:
            if outcome.outcome.lower() in ["no", "false"]:
                protection_outcome = outcome
                break

        if not protection_outcome:
            protection_outcome = protection_market.outcomes[-1]

        protection_price = protection_outcome.price
        protection_size = protection_amount / protection_price

        legs = [
            SyntheticLeg(
                market_id=base_position.market_id,
                market_question=base_position.market_question,
                token_id=base_position.token_id,
                outcome=base_position.outcome,
                side="long",
                weight=Decimal(1),
                price=base_position.avg_entry_price,
            ),
            SyntheticLeg(
                market_id=protection_market.condition_id,
                market_question=protection_market.question,
                token_id=protection_outcome.token_id,
                outcome=protection_outcome.outcome,
                side="long",
                weight=protection_size / base_position.size,
                price=protection_price,
            ),
        ]

        return SyntheticPosition(
            name=f"Collar on {base_position.market_question[:30]}",
            description="Base position with downside protection",
            legs=legs,
            target_exposure="Limited downside with capped upside",
            estimated_correlation=-0.8,
            total_cost=base_position.cost_basis + protection_amount,
            max_profit=base_position.max_profit - protection_amount,
            max_loss=max(
                Decimal(0),
                base_position.max_loss - (protection_size * (Decimal(1) - protection_price))
            ),
            notes=[
                "Protection limits losses if base position fails",
                "Cost of protection reduces maximum profit",
                f"Protection cost: ${protection_amount}",
            ],
        )

    def calculate_synthetic_probability(
        self,
        positions: list[tuple[Decimal, Decimal]],
    ) -> Decimal:
        """Calculate implied probability of a synthetic event.

        Useful when the exact event isn't traded but related ones are.

        Args:
            positions: List of (probability, conditional_weight) tuples
        """
        # Weighted sum of probabilities
        total_weight = sum(w for _, w in positions)
        if total_weight == 0:
            return Decimal("0.5")

        weighted_prob = sum(p * w for p, w in positions) / total_weight
        return weighted_prob

    def find_replication_trades(
        self,
        target_event: str,
        available_markets: list[Market],
    ) -> Optional[SyntheticPosition]:
        """Find trades to replicate exposure to an event not directly traded.

        This is a heuristic approach based on keyword matching.

        Args:
            target_event: Description of event you want exposure to
            available_markets: Markets available to trade
        """
        # Find related markets by keyword matching
        target_words = set(target_event.lower().split())
        scored_markets = []

        for market in available_markets:
            market_words = set(market.question.lower().split())
            overlap = len(target_words & market_words)
            if overlap > 0:
                scored_markets.append((overlap, market))

        if not scored_markets:
            return None

        # Use top 3 most related markets
        scored_markets.sort(key=lambda x: x[0], reverse=True)
        top_markets = [m for _, m in scored_markets[:3]]

        # Create basket with equal weights
        markets_with_weights = [(m, Decimal("0.33")) for m in top_markets]

        return self.create_basket(markets_with_weights, f"Synthetic: {target_event[:30]}")

    def analyze_position_risk(
        self, position: SyntheticPosition
    ) -> dict:
        """Analyze risk characteristics of a synthetic position."""
        legs = position.legs

        return {
            "num_legs": len(legs),
            "total_cost": position.total_cost,
            "max_profit": position.max_profit,
            "max_loss": position.max_loss,
            "profit_loss_ratio": float(position.max_profit / position.max_loss)
            if position.max_loss > 0
            else float("inf"),
            "weighted_avg_price": sum(l.price * l.weight for l in legs)
            / sum(l.weight for l in legs)
            if legs
            else Decimal(0),
            "long_exposure": sum(l.weight for l in legs if l.side == "long"),
            "short_exposure": sum(l.weight for l in legs if l.side == "short"),
            "net_exposure": sum(
                l.weight if l.side == "long" else -l.weight for l in legs
            ),
        }

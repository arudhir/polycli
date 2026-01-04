"""Kelly Criterion with conservative fractional betting.

Use 1/4 or 1/2 Kelly to avoid overexposure - full Kelly is
theoretically optimal but practically ruins bankrolls.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class KellyFraction(Enum):
    """Standard Kelly fraction multipliers."""

    FULL = 1.0
    THREE_QUARTER = 0.75
    HALF = 0.5
    QUARTER = 0.25
    EIGHTH = 0.125


@dataclass
class KellyResult:
    """Result of a Kelly calculation."""

    full_kelly_fraction: Decimal
    recommended_fraction: Decimal
    recommended_bet_size: Decimal
    edge: Decimal
    expected_value: Decimal
    win_probability: Decimal
    market_odds: Decimal
    is_positive_ev: bool


class KellyCalculator:
    """Calculate optimal bet sizes using Kelly Criterion."""

    def __init__(
        self,
        bankroll: Decimal,
        default_fraction: KellyFraction = KellyFraction.QUARTER,
        max_bet_fraction: Decimal = Decimal("0.1"),
    ):
        """Initialize Kelly calculator.

        Args:
            bankroll: Total bankroll available for trading
            default_fraction: Default Kelly fraction to use (default 1/4)
            max_bet_fraction: Maximum fraction of bankroll per bet (default 10%)
        """
        self._bankroll = bankroll
        self._default_fraction = default_fraction
        self._max_bet_fraction = max_bet_fraction

    @property
    def bankroll(self) -> Decimal:
        """Current bankroll."""
        return self._bankroll

    @bankroll.setter
    def bankroll(self, value: Decimal) -> None:
        """Update bankroll."""
        if value < 0:
            raise ValueError("Bankroll cannot be negative")
        self._bankroll = value

    def calculate(
        self,
        win_probability: Decimal,
        market_price: Decimal,
        kelly_fraction: KellyFraction | None = None,
    ) -> KellyResult:
        """Calculate recommended bet size using Kelly Criterion.

        The Kelly formula for binary bets:
        f* = (p * b - q) / b

        Where:
        - f* = fraction of bankroll to bet
        - p = probability of winning
        - q = probability of losing (1 - p)
        - b = odds received (payout ratio - 1)

        For prediction markets where you buy at price P:
        - If you win, you get 1.0 (so profit = 1.0 - P)
        - b = (1 - P) / P

        Args:
            win_probability: Your estimated probability of winning
            market_price: Current market price (0-1)
            kelly_fraction: Override default fraction
        """
        fraction = kelly_fraction or self._default_fraction

        if not (0 < win_probability < 1):
            raise ValueError("Win probability must be between 0 and 1")
        if not (0 < market_price < 1):
            raise ValueError("Market price must be between 0 and 1")

        p = win_probability
        q = Decimal(1) - p
        price = market_price

        # Calculate odds (b)
        # If market price is 0.4, and you win, you get 1.0
        # So your profit is 0.6 on a 0.4 bet -> b = 0.6/0.4 = 1.5
        b = (Decimal(1) - price) / price

        # Full Kelly fraction
        # f* = (p * b - q) / b = (p * (1-P)/P - q) / ((1-P)/P)
        # Simplified: f* = p - (q * P) / (1 - P)
        numerator = p * b - q
        full_kelly = numerator / b if b > 0 else Decimal(0)

        # Calculate edge and EV
        edge = p - price  # Difference between your estimate and market
        expected_value = (p * (Decimal(1) - price)) - (q * price)

        is_positive = full_kelly > 0

        # Apply Kelly fraction
        recommended_fraction = max(Decimal(0), full_kelly * Decimal(str(fraction.value)))

        # Apply max bet cap
        recommended_fraction = min(recommended_fraction, self._max_bet_fraction)

        # Calculate actual bet size
        recommended_bet = self._bankroll * recommended_fraction

        return KellyResult(
            full_kelly_fraction=max(Decimal(0), full_kelly),
            recommended_fraction=recommended_fraction,
            recommended_bet_size=recommended_bet.quantize(Decimal("0.01")),
            edge=edge,
            expected_value=expected_value,
            win_probability=win_probability,
            market_odds=market_price,
            is_positive_ev=is_positive,
        )

    def calculate_for_short(
        self,
        lose_probability: Decimal,
        market_price: Decimal,
        kelly_fraction: KellyFraction | None = None,
    ) -> KellyResult:
        """Calculate bet size when betting against (shorting) an outcome.

        When shorting, you're betting the outcome WON'T happen.
        Market price is what you'd need to pay if you were buying.
        Your effective price is (1 - market_price).

        Args:
            lose_probability: Your estimated probability outcome loses (your win prob)
            market_price: Current market price of the YES token
            kelly_fraction: Override default fraction
        """
        # When shorting at price P, you're effectively buying NO at price (1-P)
        # If you win (outcome loses), you get 1.0
        effective_price = Decimal(1) - market_price

        return self.calculate(
            win_probability=lose_probability,
            market_price=effective_price,
            kelly_fraction=kelly_fraction,
        )

    def optimal_allocation(
        self,
        opportunities: list[tuple[Decimal, Decimal]],
        kelly_fraction: KellyFraction | None = None,
    ) -> list[tuple[int, Decimal]]:
        """Allocate bankroll across multiple independent opportunities.

        For multiple independent bets, Kelly suggests allocating
        proportionally to each bet's individual Kelly fraction.

        Args:
            opportunities: List of (win_probability, market_price) tuples
            kelly_fraction: Override default fraction

        Returns:
            List of (index, recommended_bet_size) tuples
        """
        # Calculate Kelly for each opportunity
        results = []
        total_kelly = Decimal(0)

        for i, (prob, price) in enumerate(opportunities):
            try:
                result = self.calculate(prob, price, kelly_fraction)
                if result.is_positive_ev:
                    results.append((i, result.recommended_fraction))
                    total_kelly += result.recommended_fraction
            except ValueError:
                continue

        if total_kelly == 0:
            return []

        # Normalize if total exceeds max allocation
        max_total = self._max_bet_fraction * len(opportunities)
        if total_kelly > max_total:
            scale = max_total / total_kelly
            results = [(i, frac * scale) for i, frac in results]
            total_kelly = max_total

        # Convert to bet sizes
        return [(i, self._bankroll * frac) for i, frac in results]

    def growth_rate(
        self,
        win_probability: Decimal,
        market_price: Decimal,
        bet_fraction: Decimal,
    ) -> Decimal:
        """Calculate expected logarithmic growth rate for a bet.

        This helps compare different bet sizes to see how they
        affect long-term bankroll growth.

        Args:
            win_probability: Probability of winning
            market_price: Price to enter position
            bet_fraction: Fraction of bankroll to bet
        """
        p = win_probability
        q = Decimal(1) - p
        f = bet_fraction

        # Return multiple if win
        win_return = Decimal(1) - market_price  # Profit per dollar risked
        win_multiple = Decimal(1) + (f * win_return / market_price)

        # Return multiple if lose
        lose_multiple = Decimal(1) - f

        # Expected log growth
        # g = p * ln(1 + f*b) + q * ln(1 - f)
        import math

        if win_multiple <= 0 or lose_multiple <= 0:
            return Decimal("-999")  # Represents -infinity (ruin)

        growth = (
            float(p) * math.log(float(win_multiple))
            + float(q) * math.log(float(lose_multiple))
        )

        return Decimal(str(growth))

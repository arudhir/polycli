"""Calculate maximum drawdown scenarios.

Know your worst-case before entering - if losing 40% of bankroll
would tilt you, size down.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from polycli.models import Position


@dataclass
class DrawdownScenario:
    """A potential drawdown scenario."""

    name: str
    description: str
    probability: Decimal
    portfolio_loss: Decimal
    loss_pct: Decimal
    positions_affected: list[Position]
    recovery_needed_pct: Decimal


@dataclass
class DrawdownAnalysis:
    """Complete drawdown analysis for a portfolio."""

    current_portfolio_value: Decimal
    max_theoretical_loss: Decimal
    max_theoretical_loss_pct: Decimal
    scenarios: list[DrawdownScenario]
    var_95: Decimal  # Value at Risk (95% confidence)
    var_99: Decimal  # Value at Risk (99% confidence)
    safe_to_add_more: bool
    recommendations: list[str]


class DrawdownCalculator:
    """Calculate and analyze potential drawdowns."""

    def __init__(
        self,
        max_acceptable_drawdown: Decimal = Decimal("0.25"),
        tilt_threshold: Decimal = Decimal("0.40"),
    ):
        """Initialize drawdown calculator.

        Args:
            max_acceptable_drawdown: Max drawdown before reducing risk
            tilt_threshold: Drawdown that would cause emotional tilt
        """
        self._max_drawdown = max_acceptable_drawdown
        self._tilt_threshold = tilt_threshold

    def analyze_portfolio(
        self,
        positions: list[Position],
        reserve_balance: Decimal,
    ) -> DrawdownAnalysis:
        """Analyze potential drawdowns for portfolio.

        Args:
            positions: All current positions
            reserve_balance: Cash reserves
        """
        portfolio_value = sum(p.current_value for p in positions) + reserve_balance
        total_at_risk = sum(p.cost_basis for p in positions)

        # Max theoretical loss (all positions lose)
        max_loss = total_at_risk
        max_loss_pct = max_loss / portfolio_value if portfolio_value > 0 else Decimal(0)

        # Generate scenarios
        scenarios = self._generate_scenarios(positions, portfolio_value)

        # Calculate VaR
        var_95 = self._calculate_var(positions, portfolio_value, Decimal("0.95"))
        var_99 = self._calculate_var(positions, portfolio_value, Decimal("0.99"))

        # Determine if safe to add more
        safe_to_add = max_loss_pct < self._max_drawdown

        # Generate recommendations
        recommendations = self._generate_recommendations(
            max_loss_pct, var_95 / portfolio_value, positions
        )

        return DrawdownAnalysis(
            current_portfolio_value=portfolio_value,
            max_theoretical_loss=max_loss,
            max_theoretical_loss_pct=max_loss_pct,
            scenarios=scenarios,
            var_95=var_95,
            var_99=var_99,
            safe_to_add_more=safe_to_add,
            recommendations=recommendations,
        )

    def _generate_scenarios(
        self,
        positions: list[Position],
        portfolio_value: Decimal,
    ) -> list[DrawdownScenario]:
        """Generate potential drawdown scenarios."""
        scenarios = []

        # Scenario 1: All positions lose
        if positions:
            total_loss = sum(p.cost_basis for p in positions)
            scenarios.append(
                DrawdownScenario(
                    name="Worst Case",
                    description="All positions resolve against you",
                    probability=self._estimate_all_lose_prob(positions),
                    portfolio_loss=total_loss,
                    loss_pct=total_loss / portfolio_value if portfolio_value > 0 else Decimal(0),
                    positions_affected=positions,
                    recovery_needed_pct=self._calc_recovery_needed(
                        total_loss / portfolio_value if portfolio_value > 0 else Decimal(0)
                    ),
                )
            )

        # Scenario 2: Largest position loses
        if positions:
            largest = max(positions, key=lambda p: p.cost_basis)
            scenarios.append(
                DrawdownScenario(
                    name="Largest Position Loss",
                    description=f"'{largest.market_question[:30]}...' loses",
                    probability=Decimal(1) - largest.current_price,
                    portfolio_loss=largest.cost_basis,
                    loss_pct=largest.cost_basis / portfolio_value if portfolio_value > 0 else Decimal(0),
                    positions_affected=[largest],
                    recovery_needed_pct=self._calc_recovery_needed(
                        largest.cost_basis / portfolio_value if portfolio_value > 0 else Decimal(0)
                    ),
                )
            )

        # Scenario 3: Correlated positions lose together
        correlated_groups = self._find_correlated_groups(positions)
        for group_name, group_positions in correlated_groups.items():
            if len(group_positions) > 1:
                group_loss = sum(p.cost_basis for p in group_positions)
                scenarios.append(
                    DrawdownScenario(
                        name=f"{group_name} Collapse",
                        description=f"All {group_name}-related positions lose",
                        probability=Decimal("0.15"),  # Rough estimate
                        portfolio_loss=group_loss,
                        loss_pct=group_loss / portfolio_value if portfolio_value > 0 else Decimal(0),
                        positions_affected=group_positions,
                        recovery_needed_pct=self._calc_recovery_needed(
                            group_loss / portfolio_value if portfolio_value > 0 else Decimal(0)
                        ),
                    )
                )

        # Sort by severity
        scenarios.sort(key=lambda s: s.loss_pct, reverse=True)
        return scenarios

    def _estimate_all_lose_prob(self, positions: list[Position]) -> Decimal:
        """Estimate probability of all positions losing."""
        if not positions:
            return Decimal(0)

        # Product of losing probabilities (assumes independence - not accurate but rough)
        prob = Decimal(1)
        for p in positions:
            lose_prob = Decimal(1) - p.current_price
            prob *= lose_prob

        return prob

    def _calc_recovery_needed(self, loss_pct: Decimal) -> Decimal:
        """Calculate % gain needed to recover from loss."""
        if loss_pct >= Decimal(1):
            return Decimal("999")  # Cannot recover
        return loss_pct / (Decimal(1) - loss_pct)

    def _find_correlated_groups(
        self, positions: list[Position]
    ) -> dict[str, list[Position]]:
        """Find groups of correlated positions."""
        groups: dict[str, list[Position]] = {}

        keywords = {
            "trump": "Political",
            "republican": "Political",
            "democrat": "Political",
            "election": "Political",
            "bitcoin": "Crypto",
            "ethereum": "Crypto",
            "crypto": "Crypto",
            "fed": "Economic",
            "inflation": "Economic",
            "rate": "Economic",
        }

        for position in positions:
            question_lower = position.market_question.lower()
            for keyword, group in keywords.items():
                if keyword in question_lower:
                    if group not in groups:
                        groups[group] = []
                    if position not in groups[group]:
                        groups[group].append(position)

        return groups

    def _calculate_var(
        self,
        positions: list[Position],
        portfolio_value: Decimal,
        confidence: Decimal,
    ) -> Decimal:
        """Calculate Value at Risk.

        Simplified VaR based on position probabilities.
        """
        if not positions:
            return Decimal(0)

        # For each position, loss * (1 - current_price) is expected if it loses
        expected_losses = []
        for p in positions:
            lose_prob = 1 - float(p.current_price)
            expected_losses.append((p.cost_basis, lose_prob))

        # Sort by expected loss contribution
        expected_losses.sort(key=lambda x: float(x[0]) * x[1], reverse=True)

        # Accumulate losses until we hit confidence threshold
        cumulative_prob = 0.0
        cumulative_loss = Decimal(0)
        target_prob = 1 - float(confidence)

        for loss, prob in expected_losses:
            if cumulative_prob >= target_prob:
                break
            cumulative_loss += loss
            cumulative_prob += prob * (1 - cumulative_prob)

        return cumulative_loss

    def _generate_recommendations(
        self,
        max_loss_pct: Decimal,
        var_pct: Decimal,
        positions: list[Position],
    ) -> list[str]:
        """Generate risk management recommendations."""
        recommendations = []

        if max_loss_pct > self._tilt_threshold:
            recommendations.append(
                f"CRITICAL: Max drawdown ({max_loss_pct:.0%}) exceeds tilt threshold "
                f"({self._tilt_threshold:.0%}). Reduce position sizes immediately."
            )

        if max_loss_pct > self._max_drawdown:
            recommendations.append(
                f"Max drawdown ({max_loss_pct:.0%}) exceeds target "
                f"({self._max_drawdown:.0%}). Consider reducing exposure."
            )

        if var_pct > self._max_drawdown * Decimal("0.7"):
            recommendations.append(
                f"VaR ({var_pct:.0%}) is high. Even likely scenarios could "
                "cause significant drawdown."
            )

        # Check concentration
        if positions:
            largest = max(positions, key=lambda p: p.cost_basis)
            total = sum(p.cost_basis for p in positions)
            if total > 0 and largest.cost_basis / total > Decimal("0.4"):
                recommendations.append(
                    f"Position in '{largest.market_question[:30]}...' is "
                    f"{largest.cost_basis / total:.0%} of portfolio. Consider diversifying."
                )

        if not recommendations:
            recommendations.append("Risk levels are within acceptable parameters.")

        return recommendations

    def check_new_position_impact(
        self,
        positions: list[Position],
        reserve_balance: Decimal,
        new_position_size: Decimal,
    ) -> dict:
        """Check how a new position would impact drawdown risk.

        Args:
            positions: Existing positions
            reserve_balance: Current reserves
            new_position_size: Size of potential new position
        """
        current_analysis = self.analyze_portfolio(positions, reserve_balance)

        # Simulate adding new position
        new_total_at_risk = sum(p.cost_basis for p in positions) + new_position_size
        new_portfolio = current_analysis.current_portfolio_value
        new_max_loss_pct = new_total_at_risk / new_portfolio if new_portfolio > 0 else Decimal(0)

        return {
            "current_max_drawdown": current_analysis.max_theoretical_loss_pct,
            "new_max_drawdown": new_max_loss_pct,
            "increase": new_max_loss_pct - current_analysis.max_theoretical_loss_pct,
            "still_acceptable": new_max_loss_pct <= self._max_drawdown,
            "would_cause_tilt": new_max_loss_pct > self._tilt_threshold,
            "recommendation": (
                "Safe to add" if new_max_loss_pct <= self._max_drawdown
                else f"Would exceed max drawdown target ({self._max_drawdown:.0%})"
            ),
        }

    def suggest_position_size(
        self,
        positions: list[Position],
        reserve_balance: Decimal,
        target_drawdown: Optional[Decimal] = None,
    ) -> Decimal:
        """Suggest maximum position size to stay within drawdown limits.

        Args:
            positions: Existing positions
            reserve_balance: Current reserves
            target_drawdown: Target max drawdown (uses default if None)
        """
        target = target_drawdown or self._max_drawdown
        portfolio_value = sum(p.current_value for p in positions) + reserve_balance
        current_at_risk = sum(p.cost_basis for p in positions)

        max_total_at_risk = portfolio_value * target
        available = max_total_at_risk - current_at_risk

        return max(Decimal(0), available)

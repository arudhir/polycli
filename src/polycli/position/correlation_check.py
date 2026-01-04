"""Check correlation between positions.

Never go all-in on correlated positions - if you're long Trump
AND long GOP Senate AND long Bitcoin, you're basically making
one giant bet.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import numpy as np

from polycli.models import Position


@dataclass
class CorrelationWarning:
    """Warning about correlated positions."""

    position1: Position
    position2: Position
    correlation: float
    combined_exposure: Decimal
    message: str


@dataclass
class PortfolioCorrelationReport:
    """Report on portfolio correlation risk."""

    warnings: list[CorrelationWarning]
    max_correlated_exposure: Decimal
    effective_positions: int
    diversification_score: float
    recommendations: list[str]


class PositionCorrelationChecker:
    """Check and manage correlation between positions."""

    # Known correlations between market types (estimate)
    KNOWN_CORRELATIONS = {
        ("trump", "republican"): 0.85,
        ("trump", "gop"): 0.85,
        ("trump", "senate republican"): 0.7,
        ("bitcoin", "crypto"): 0.95,
        ("bitcoin", "ethereum"): 0.8,
        ("fed", "inflation"): -0.6,
        ("fed", "rate"): 0.9,
        ("russia", "ukraine"): 0.7,
        ("china", "taiwan"): 0.6,
    }

    def __init__(
        self,
        max_correlation: float = 0.7,
        max_correlated_exposure: Decimal = Decimal("0.3"),
    ):
        """Initialize correlation checker.

        Args:
            max_correlation: Maximum acceptable correlation between positions
            max_correlated_exposure: Maximum total exposure for correlated positions
        """
        self._max_correlation = max_correlation
        self._max_correlated_exposure = max_correlated_exposure

    def estimate_correlation(
        self,
        position1: Position,
        position2: Position,
    ) -> float:
        """Estimate correlation between two positions based on keywords.

        In practice, you'd want to calculate actual price correlation
        from historical data. This is a heuristic fallback.
        """
        q1 = position1.market_question.lower()
        q2 = position2.market_question.lower()

        # Check known correlations
        for (k1, k2), corr in self.KNOWN_CORRELATIONS.items():
            if (k1 in q1 and k2 in q2) or (k1 in q2 and k2 in q1):
                return corr

        # Check same market (different outcomes)
        if position1.market_id == position2.market_id:
            return -1.0 if position1.outcome != position2.outcome else 1.0

        # Check keyword overlap as rough heuristic
        words1 = set(q1.split())
        words2 = set(q2.split())
        common = words1 & words2

        # Remove common stop words
        stop_words = {"the", "a", "an", "will", "be", "in", "to", "of", "and", "or", "?"}
        common = common - stop_words

        if len(common) > 3:
            return 0.5
        elif len(common) > 1:
            return 0.3

        return 0.0

    def check_portfolio(
        self,
        positions: list[Position],
        bankroll: Decimal,
    ) -> PortfolioCorrelationReport:
        """Analyze portfolio for correlation risk.

        Args:
            positions: All current positions
            bankroll: Total bankroll for exposure calculations
        """
        warnings = []
        correlated_groups: list[set[int]] = []

        # Check all pairs
        n = len(positions)
        correlation_matrix = np.zeros((n, n))

        for i in range(n):
            correlation_matrix[i, i] = 1.0
            for j in range(i + 1, n):
                corr = self.estimate_correlation(positions[i], positions[j])
                correlation_matrix[i, j] = corr
                correlation_matrix[j, i] = corr

                if abs(corr) > self._max_correlation:
                    combined = positions[i].cost_basis + positions[j].cost_basis
                    warnings.append(
                        CorrelationWarning(
                            position1=positions[i],
                            position2=positions[j],
                            correlation=corr,
                            combined_exposure=combined,
                            message=self._format_warning(positions[i], positions[j], corr),
                        )
                    )

                    # Track correlated groups
                    self._add_to_groups(correlated_groups, i, j)

        # Calculate max correlated exposure
        max_exposure = Decimal(0)
        for group in correlated_groups:
            group_exposure = sum(positions[i].cost_basis for i in group)
            max_exposure = max(max_exposure, group_exposure)

        # Calculate effective number of positions (accounting for correlation)
        effective_n = self._calculate_effective_positions(correlation_matrix)

        # Calculate diversification score (0-1, higher is better)
        div_score = effective_n / n if n > 0 else 1.0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            positions, warnings, max_exposure, bankroll, div_score
        )

        return PortfolioCorrelationReport(
            warnings=warnings,
            max_correlated_exposure=max_exposure,
            effective_positions=int(round(effective_n)),
            diversification_score=div_score,
            recommendations=recommendations,
        )

    def _format_warning(
        self, pos1: Position, pos2: Position, correlation: float
    ) -> str:
        """Format a correlation warning message."""
        direction = "positively" if correlation > 0 else "negatively"
        return (
            f"'{pos1.market_question[:40]}...' and "
            f"'{pos2.market_question[:40]}...' are {direction} correlated "
            f"({correlation:.1%}). Combined exposure: ${pos1.cost_basis + pos2.cost_basis:.2f}"
        )

    def _add_to_groups(
        self, groups: list[set[int]], i: int, j: int
    ) -> None:
        """Add a correlated pair to existing groups or create new one."""
        # Find existing groups containing either position
        containing_i = None
        containing_j = None

        for group in groups:
            if i in group:
                containing_i = group
            if j in group:
                containing_j = group

        if containing_i is None and containing_j is None:
            # New group
            groups.append({i, j})
        elif containing_i is containing_j:
            # Already in same group
            pass
        elif containing_i is None:
            containing_j.add(i)  # type: ignore
        elif containing_j is None:
            containing_i.add(j)
        else:
            # Merge groups
            containing_i.update(containing_j)
            groups.remove(containing_j)

    def _calculate_effective_positions(
        self, correlation_matrix: np.ndarray
    ) -> float:
        """Calculate effective number of independent positions.

        Uses eigenvalue decomposition of correlation matrix.
        """
        n = len(correlation_matrix)
        if n == 0:
            return 0

        if n == 1:
            return 1

        try:
            eigenvalues = np.linalg.eigvalsh(correlation_matrix)
            eigenvalues = np.maximum(eigenvalues, 0)  # Handle numerical issues
            total_var = np.sum(eigenvalues)
            if total_var == 0:
                return n
            # Effective number is inverse of concentration
            normalized = eigenvalues / total_var
            effective_n = 1 / np.sum(normalized**2)
            return min(effective_n, n)
        except Exception:
            return n

    def _generate_recommendations(
        self,
        positions: list[Position],
        warnings: list[CorrelationWarning],
        max_exposure: Decimal,
        bankroll: Decimal,
        div_score: float,
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if max_exposure > bankroll * self._max_correlated_exposure:
            recommendations.append(
                f"Reduce correlated exposure from ${max_exposure:.2f} to max "
                f"${bankroll * self._max_correlated_exposure:.2f} "
                f"({self._max_correlated_exposure:.0%} of bankroll)"
            )

        if div_score < 0.5:
            recommendations.append(
                "Portfolio is highly concentrated. Consider adding uncorrelated positions."
            )

        if len(warnings) > 3:
            recommendations.append(
                f"You have {len(warnings)} correlated position pairs. "
                "Consider treating them as a single bet for sizing purposes."
            )

        # Specific warnings about market types
        market_questions = " ".join(p.market_question.lower() for p in positions)
        if market_questions.count("trump") > 2 or market_questions.count("republican") > 2:
            recommendations.append(
                "Heavy exposure to US political outcomes. These markets often move together."
            )

        if not recommendations:
            recommendations.append("Portfolio diversification looks healthy.")

        return recommendations

    def suggest_sizing(
        self,
        new_position: Position,
        existing_positions: list[Position],
        proposed_size: Decimal,
        bankroll: Decimal,
    ) -> tuple[Decimal, list[str]]:
        """Suggest adjusted size for a new position based on correlations.

        Args:
            new_position: Position you want to add
            existing_positions: Current portfolio
            proposed_size: Size you want to add
            bankroll: Total bankroll

        Returns:
            (adjusted_size, list of reasons)
        """
        reasons = []
        adjusted = proposed_size

        # Find correlated existing positions
        correlated_exposure = Decimal(0)
        for pos in existing_positions:
            corr = self.estimate_correlation(new_position, pos)
            if abs(corr) > self._max_correlation:
                correlated_exposure += pos.cost_basis
                reasons.append(
                    f"Correlated with existing {pos.outcome} position (r={corr:.2f})"
                )

        # Calculate remaining allowed exposure
        max_allowed = bankroll * self._max_correlated_exposure
        remaining = max_allowed - correlated_exposure

        if remaining <= 0:
            adjusted = Decimal(0)
            reasons.append(
                f"Already at max correlated exposure (${correlated_exposure:.2f})"
            )
        elif proposed_size > remaining:
            adjusted = remaining
            reasons.append(
                f"Reduced from ${proposed_size:.2f} to ${adjusted:.2f} "
                "due to correlation limits"
            )

        return adjusted, reasons

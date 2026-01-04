"""Separate skill from variance.

Run Monte Carlo simulations on your strategy - are you actually
profitable or just lucky?
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import numpy as np


@dataclass
class SimulationResult:
    """Result of a Monte Carlo simulation."""

    num_simulations: int
    num_trades: int
    win_rate: float
    avg_win: Decimal
    avg_loss: Decimal

    # Distribution of outcomes
    mean_pnl: Decimal
    median_pnl: Decimal
    std_pnl: Decimal
    percentile_5: Decimal
    percentile_25: Decimal
    percentile_75: Decimal
    percentile_95: Decimal

    # Risk metrics
    probability_of_profit: float
    probability_of_ruin: float
    max_drawdown_mean: Decimal
    max_drawdown_95th: Decimal

    # Skill assessment
    skill_confidence: float  # 0-1
    likely_skill_contribution: float  # 0-1
    notes: list[str]


@dataclass
class VarianceDecomposition:
    """Decomposition of returns into skill and luck."""

    total_return: Decimal
    expected_return: Decimal
    variance_component: Decimal
    skill_estimate: float
    luck_estimate: float
    confidence_interval: tuple[float, float]


class VarianceAnalyzer:
    """Analyze variance and separate skill from luck."""

    def __init__(self, random_seed: Optional[int] = None):
        """Initialize variance analyzer.

        Args:
            random_seed: Seed for reproducible simulations
        """
        if random_seed is not None:
            np.random.seed(random_seed)

    def monte_carlo_simulation(
        self,
        win_rate: float,
        avg_win: Decimal,
        avg_loss: Decimal,
        num_trades: int,
        num_simulations: int = 10000,
        starting_bankroll: Decimal = Decimal("10000"),
        ruin_threshold: Decimal = Decimal("100"),
    ) -> SimulationResult:
        """Run Monte Carlo simulation on trading strategy.

        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount (positive number)
            num_trades: Number of trades to simulate
            num_simulations: Number of simulation runs
            starting_bankroll: Starting capital
            ruin_threshold: Bankroll level considered "ruin"
        """
        final_pnls = []
        max_drawdowns = []
        ruin_count = 0

        for _ in range(num_simulations):
            bankroll = float(starting_bankroll)
            peak = bankroll
            max_dd = 0.0

            for _ in range(num_trades):
                if np.random.random() < win_rate:
                    bankroll += float(avg_win)
                else:
                    bankroll -= float(avg_loss)

                if bankroll > peak:
                    peak = bankroll
                dd = (peak - bankroll) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)

                if bankroll < float(ruin_threshold):
                    ruin_count += 1
                    break

            final_pnls.append(bankroll - float(starting_bankroll))
            max_drawdowns.append(max_dd)

        pnl_array = np.array(final_pnls)
        dd_array = np.array(max_drawdowns)

        # Calculate skill confidence
        skill_conf, skill_contrib, notes = self._assess_skill(
            win_rate, float(avg_win), float(avg_loss), pnl_array
        )

        return SimulationResult(
            num_simulations=num_simulations,
            num_trades=num_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            mean_pnl=Decimal(str(np.mean(pnl_array))),
            median_pnl=Decimal(str(np.median(pnl_array))),
            std_pnl=Decimal(str(np.std(pnl_array))),
            percentile_5=Decimal(str(np.percentile(pnl_array, 5))),
            percentile_25=Decimal(str(np.percentile(pnl_array, 25))),
            percentile_75=Decimal(str(np.percentile(pnl_array, 75))),
            percentile_95=Decimal(str(np.percentile(pnl_array, 95))),
            probability_of_profit=float(np.mean(pnl_array > 0)),
            probability_of_ruin=ruin_count / num_simulations,
            max_drawdown_mean=Decimal(str(np.mean(dd_array))),
            max_drawdown_95th=Decimal(str(np.percentile(dd_array, 95))),
            skill_confidence=skill_conf,
            likely_skill_contribution=skill_contrib,
            notes=notes,
        )

    def _assess_skill(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        pnl_distribution: np.ndarray,
    ) -> tuple[float, float, list[str]]:
        """Assess skill vs luck from simulation results."""
        notes = []

        # Calculate expected value
        ev = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Calculate Sharpe-like ratio
        if np.std(pnl_distribution) > 0:
            sharpe = np.mean(pnl_distribution) / np.std(pnl_distribution)
        else:
            sharpe = 0

        # Skill confidence based on statistical significance
        # Using t-test like approach
        n = len(pnl_distribution)
        se = np.std(pnl_distribution) / np.sqrt(n)
        t_stat = np.mean(pnl_distribution) / se if se > 0 else 0

        # Convert to confidence (rough approximation)
        skill_confidence = min(0.99, 1 - 2 * (1 - self._norm_cdf(abs(t_stat))))

        # Estimate skill contribution
        if np.mean(pnl_distribution) > 0:
            # Positive expectation suggests skill
            variance_explained = 1 - (np.var(pnl_distribution) / (np.mean(pnl_distribution) ** 2 + np.var(pnl_distribution)))
            skill_contribution = max(0, min(1, variance_explained + 0.1 * sharpe))
        else:
            skill_contribution = 0

        # Generate notes
        if ev > 0:
            notes.append(f"Positive expected value (${ev:.2f}/trade) suggests edge")
        else:
            notes.append(f"Negative expected value (${ev:.2f}/trade) - no edge detected")

        if sharpe > 0.5:
            notes.append(f"Good risk-adjusted returns (Sharpe-like: {sharpe:.2f})")
        elif sharpe < 0:
            notes.append(f"Poor risk-adjusted returns (Sharpe-like: {sharpe:.2f})")

        if skill_confidence > 0.95:
            notes.append("Results are statistically significant (>95% confidence)")
        elif skill_confidence > 0.8:
            notes.append("Results are moderately significant (80-95% confidence)")
        else:
            notes.append("Results may be due to chance (<80% confidence)")

        return skill_confidence, skill_contribution, notes

    def _norm_cdf(self, x: float) -> float:
        """Approximate normal CDF."""
        return (1.0 + np.erf(x / np.sqrt(2.0))) / 2.0

    def decompose_variance(
        self,
        actual_returns: list[Decimal],
        expected_win_rate: float,
        expected_win_size: Decimal,
        expected_loss_size: Decimal,
    ) -> VarianceDecomposition:
        """Decompose actual returns into skill and luck components.

        Args:
            actual_returns: List of actual trade returns
            expected_win_rate: Expected win rate if no skill
            expected_win_size: Expected average win
            expected_loss_size: Expected average loss
        """
        if not actual_returns:
            return VarianceDecomposition(
                total_return=Decimal(0),
                expected_return=Decimal(0),
                variance_component=Decimal(0),
                skill_estimate=0.5,
                luck_estimate=0.5,
                confidence_interval=(0.0, 1.0),
            )

        actual = [float(r) for r in actual_returns]
        n = len(actual)

        total_return = sum(actual)

        # Expected return under random trading
        expected_per_trade = (
            expected_win_rate * float(expected_win_size)
            - (1 - expected_win_rate) * float(expected_loss_size)
        )
        expected_total = expected_per_trade * n

        # Variance component (deviation from expected)
        variance_component = total_return - expected_total

        # Calculate actual win rate
        actual_win_rate = sum(1 for r in actual if r > 0) / n if n > 0 else 0.5

        # Skill estimate (how much better than random)
        if actual_win_rate > expected_win_rate:
            skill = (actual_win_rate - expected_win_rate) / (1 - expected_win_rate)
        elif actual_win_rate < expected_win_rate:
            skill = (actual_win_rate - expected_win_rate) / expected_win_rate
        else:
            skill = 0.5

        skill = max(0, min(1, (skill + 1) / 2))  # Normalize to 0-1
        luck = 1 - skill

        # Confidence interval (based on binomial)
        se = np.sqrt(actual_win_rate * (1 - actual_win_rate) / n) if n > 0 else 0.5
        ci = (max(0, skill - 1.96 * se), min(1, skill + 1.96 * se))

        return VarianceDecomposition(
            total_return=Decimal(str(total_return)),
            expected_return=Decimal(str(expected_total)),
            variance_component=Decimal(str(variance_component)),
            skill_estimate=skill,
            luck_estimate=luck,
            confidence_interval=ci,
        )

    def calculate_required_sample_size(
        self,
        expected_win_rate: float,
        desired_confidence: float = 0.95,
        margin_of_error: float = 0.05,
    ) -> int:
        """Calculate trades needed to confidently assess skill.

        Args:
            expected_win_rate: Expected win rate
            desired_confidence: Confidence level (e.g., 0.95)
            margin_of_error: Acceptable margin of error
        """
        # Z-score for confidence level
        z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(desired_confidence, 1.96)

        # Sample size formula for proportion
        p = expected_win_rate
        n = (z ** 2 * p * (1 - p)) / (margin_of_error ** 2)

        return int(np.ceil(n))

    def analyze_trading_history(
        self,
        trades: list[dict],
    ) -> dict:
        """Analyze actual trading history for skill vs luck.

        Args:
            trades: List of trade dicts with 'pnl', 'size', 'win' keys
        """
        if not trades:
            return {"error": "No trades to analyze"}

        # Extract data
        pnls = [t.get("pnl", 0) for t in trades]
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) <= 0]

        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
        avg_loss = abs(np.mean([t["pnl"] for t in losses])) if losses else 0

        # Run simulation
        sim_result = self.monte_carlo_simulation(
            win_rate=win_rate,
            avg_win=Decimal(str(avg_win)),
            avg_loss=Decimal(str(avg_loss)),
            num_trades=len(trades),
            num_simulations=10000,
        )

        # Decompose variance
        decomp = self.decompose_variance(
            actual_returns=[Decimal(str(p)) for p in pnls],
            expected_win_rate=0.5,  # Random baseline
            expected_win_size=Decimal(str(avg_win)) if avg_win else Decimal(100),
            expected_loss_size=Decimal(str(avg_loss)) if avg_loss else Decimal(100),
        )

        return {
            "total_trades": len(trades),
            "win_rate": win_rate,
            "total_pnl": sum(pnls),
            "simulation_result": sim_result,
            "variance_decomposition": decomp,
            "sample_size_needed": self.calculate_required_sample_size(win_rate),
            "is_statistically_significant": sim_result.skill_confidence > 0.95,
            "recommendation": (
                "Strategy shows statistical edge"
                if sim_result.skill_confidence > 0.95 and sim_result.mean_pnl > 0
                else "Need more data or results may be due to luck"
            ),
        }

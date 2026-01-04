"""Track EV separately from P&L.

You can make +EV decisions and still lose - judge yourself
on process, not just results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class EVDecision:
    """A single trading decision with its EV calculation."""

    id: str
    timestamp: datetime
    market_id: str
    market_question: str

    # Your estimates
    estimated_probability: Decimal
    confidence: int  # 1-10

    # Market conditions
    market_price: Decimal
    position_size: Decimal
    direction: str  # "long" or "short"

    # Calculated EV
    edge: Decimal  # Your prob - market prob
    expected_value: Decimal  # Expected profit
    ev_per_dollar: Decimal  # EV / position_size

    # Actual outcome (filled after resolution)
    actual_outcome: Optional[str] = None  # "win", "lose"
    actual_pnl: Optional[Decimal] = None
    resolution_date: Optional[datetime] = None

    # Notes
    thesis: str = ""
    post_mortem: Optional[str] = None


@dataclass
class EVStats:
    """Statistics on EV tracking performance."""

    total_decisions: int
    resolved_decisions: int

    # EV metrics
    total_ev_expected: Decimal
    total_actual_pnl: Decimal
    ev_accuracy: float  # How close actual results are to EV predictions

    # Decision quality metrics
    avg_edge: Decimal
    avg_confidence: float
    win_rate: float
    positive_ev_accuracy: float  # % of +EV decisions that won

    # Breakdown by confidence
    high_confidence_ev: Decimal  # EV from conf >= 7
    high_confidence_pnl: Decimal
    low_confidence_ev: Decimal  # EV from conf < 7
    low_confidence_pnl: Decimal


class EVTracker:
    """Track expected value of decisions separately from P&L."""

    def __init__(self):
        self._decisions: dict[str, EVDecision] = {}
        self._next_id = 1

    def record_decision(
        self,
        market_id: str,
        market_question: str,
        estimated_probability: Decimal,
        market_price: Decimal,
        position_size: Decimal,
        direction: str = "long",
        confidence: int = 5,
        thesis: str = "",
    ) -> EVDecision:
        """Record a trading decision with its EV calculation.

        Args:
            market_id: Market identifier
            market_question: Human-readable market question
            estimated_probability: Your probability estimate
            market_price: Current market price
            position_size: Dollar amount of position
            direction: "long" or "short"
            confidence: Confidence level 1-10
            thesis: Your reasoning for the trade
        """
        decision_id = f"ev_{self._next_id:06d}"
        self._next_id += 1

        # Calculate EV based on direction
        if direction == "long":
            # Buying YES at market_price
            edge = estimated_probability - market_price
            # Win: get (1 - price) profit per share
            # Lose: lose price per share
            ev = (estimated_probability * (Decimal(1) - market_price)) - (
                (Decimal(1) - estimated_probability) * market_price
            )
        else:
            # Buying NO (shorting YES) at (1 - market_price)
            edge = (Decimal(1) - estimated_probability) - (Decimal(1) - market_price)
            ev = ((Decimal(1) - estimated_probability) * market_price) - (
                estimated_probability * (Decimal(1) - market_price)
            )

        ev_total = ev * position_size
        ev_per_dollar = ev

        decision = EVDecision(
            id=decision_id,
            timestamp=datetime.utcnow(),
            market_id=market_id,
            market_question=market_question,
            estimated_probability=estimated_probability,
            confidence=confidence,
            market_price=market_price,
            position_size=position_size,
            direction=direction,
            edge=edge,
            expected_value=ev_total,
            ev_per_dollar=ev_per_dollar,
            thesis=thesis,
        )

        self._decisions[decision_id] = decision
        return decision

    def resolve_decision(
        self,
        decision_id: str,
        outcome: str,
        actual_pnl: Decimal,
        post_mortem: str = "",
    ) -> EVDecision:
        """Record the actual outcome of a decision.

        Args:
            decision_id: ID of the decision
            outcome: "win" or "lose"
            actual_pnl: Actual profit/loss
            post_mortem: Lessons learned
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        decision.actual_outcome = outcome
        decision.actual_pnl = actual_pnl
        decision.resolution_date = datetime.utcnow()
        decision.post_mortem = post_mortem

        return decision

    def get_stats(self) -> EVStats:
        """Calculate overall statistics."""
        decisions = list(self._decisions.values())

        if not decisions:
            return EVStats(
                total_decisions=0,
                resolved_decisions=0,
                total_ev_expected=Decimal(0),
                total_actual_pnl=Decimal(0),
                ev_accuracy=0.0,
                avg_edge=Decimal(0),
                avg_confidence=0.0,
                win_rate=0.0,
                positive_ev_accuracy=0.0,
                high_confidence_ev=Decimal(0),
                high_confidence_pnl=Decimal(0),
                low_confidence_ev=Decimal(0),
                low_confidence_pnl=Decimal(0),
            )

        resolved = [d for d in decisions if d.actual_outcome is not None]

        total_ev = sum(d.expected_value for d in decisions)
        total_pnl = sum(d.actual_pnl or Decimal(0) for d in resolved)

        # Win rate
        wins = sum(1 for d in resolved if d.actual_outcome == "win")
        win_rate = wins / len(resolved) if resolved else 0.0

        # Positive EV accuracy
        positive_ev = [d for d in resolved if d.expected_value > 0]
        positive_ev_wins = sum(1 for d in positive_ev if d.actual_outcome == "win")
        pos_ev_accuracy = positive_ev_wins / len(positive_ev) if positive_ev else 0.0

        # EV accuracy (how close actual results are to predictions)
        if total_ev != 0:
            ev_accuracy = float(total_pnl / total_ev) if total_ev != 0 else 0.0
        else:
            ev_accuracy = 1.0 if total_pnl == 0 else 0.0

        # By confidence level
        high_conf = [d for d in decisions if d.confidence >= 7]
        low_conf = [d for d in decisions if d.confidence < 7]

        high_conf_ev = sum(d.expected_value for d in high_conf)
        high_conf_pnl = sum(d.actual_pnl or Decimal(0) for d in high_conf if d.actual_outcome)

        low_conf_ev = sum(d.expected_value for d in low_conf)
        low_conf_pnl = sum(d.actual_pnl or Decimal(0) for d in low_conf if d.actual_outcome)

        return EVStats(
            total_decisions=len(decisions),
            resolved_decisions=len(resolved),
            total_ev_expected=total_ev,
            total_actual_pnl=total_pnl,
            ev_accuracy=ev_accuracy,
            avg_edge=sum(d.edge for d in decisions) / len(decisions),
            avg_confidence=sum(d.confidence for d in decisions) / len(decisions),
            win_rate=win_rate,
            positive_ev_accuracy=pos_ev_accuracy,
            high_confidence_ev=high_conf_ev,
            high_confidence_pnl=high_conf_pnl,
            low_confidence_ev=low_conf_ev,
            low_confidence_pnl=low_conf_pnl,
        )

    def get_decision(self, decision_id: str) -> Optional[EVDecision]:
        """Get a specific decision by ID."""
        return self._decisions.get(decision_id)

    def get_decisions_by_market(self, market_id: str) -> list[EVDecision]:
        """Get all decisions for a specific market."""
        return [d for d in self._decisions.values() if d.market_id == market_id]

    def get_pending_decisions(self) -> list[EVDecision]:
        """Get decisions awaiting resolution."""
        return [d for d in self._decisions.values() if d.actual_outcome is None]

    def analyze_calibration(self) -> dict:
        """Analyze how well-calibrated your probability estimates are.

        Groups decisions by estimated probability ranges and checks
        actual win rates.
        """
        resolved = [d for d in self._decisions.values() if d.actual_outcome]

        if len(resolved) < 10:
            return {"error": "Need at least 10 resolved decisions for calibration"}

        # Group by probability buckets
        buckets = {
            "0.0-0.2": [],
            "0.2-0.4": [],
            "0.4-0.6": [],
            "0.6-0.8": [],
            "0.8-1.0": [],
        }

        for d in resolved:
            prob = float(d.estimated_probability)
            if prob < 0.2:
                buckets["0.0-0.2"].append(d)
            elif prob < 0.4:
                buckets["0.2-0.4"].append(d)
            elif prob < 0.6:
                buckets["0.4-0.6"].append(d)
            elif prob < 0.8:
                buckets["0.6-0.8"].append(d)
            else:
                buckets["0.8-1.0"].append(d)

        calibration = {}
        for bucket, decisions in buckets.items():
            if decisions:
                wins = sum(1 for d in decisions if d.actual_outcome == "win")
                actual_rate = wins / len(decisions)
                expected_rate = sum(float(d.estimated_probability) for d in decisions) / len(
                    decisions
                )
                calibration[bucket] = {
                    "count": len(decisions),
                    "expected_win_rate": expected_rate,
                    "actual_win_rate": actual_rate,
                    "calibration_error": abs(expected_rate - actual_rate),
                }

        # Overall calibration score
        total_error = sum(
            c["calibration_error"] * c["count"]
            for c in calibration.values()
        )
        total_count = sum(c["count"] for c in calibration.values())
        calibration["overall_error"] = total_error / total_count if total_count > 0 else 0

        return calibration

    def get_lessons_report(self) -> str:
        """Generate a report of lessons learned from decisions."""
        resolved = [d for d in self._decisions.values() if d.actual_outcome and d.post_mortem]

        if not resolved:
            return "No resolved decisions with post-mortems yet."

        report_lines = ["# EV Decision Lessons Learned\n"]

        # Wins with lessons
        wins = [d for d in resolved if d.actual_outcome == "win"]
        if wins:
            report_lines.append("## Successful Decisions\n")
            for d in wins[-5:]:  # Last 5 wins
                report_lines.append(
                    f"- **{d.market_question[:50]}** (Edge: {d.edge:.1%})\n"
                    f"  {d.post_mortem}\n"
                )

        # Losses with lessons
        losses = [d for d in resolved if d.actual_outcome == "lose"]
        if losses:
            report_lines.append("\n## Failed Decisions\n")
            for d in losses[-5:]:  # Last 5 losses
                report_lines.append(
                    f"- **{d.market_question[:50]}** (Edge: {d.edge:.1%})\n"
                    f"  {d.post_mortem}\n"
                )

        return "\n".join(report_lines)

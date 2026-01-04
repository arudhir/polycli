"""Avoid pure coin flips.

If you can't articulate why the market is wrong, you're gambling
not trading.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from polycli.models import Market


@dataclass
class CoinFlipAssessment:
    """Assessment of whether a market is a coin flip."""

    market: Market
    is_coin_flip: bool
    confidence: float  # 0-1, how confident we are in assessment
    reasons: list[str]
    edge_source: Optional[str]  # Where edge could come from


class CoinFlipDetector:
    """Detect markets that are essentially coin flips with no edge."""

    # Price ranges that suggest coin flip
    COIN_FLIP_RANGE = (Decimal("0.45"), Decimal("0.55"))

    # Keywords suggesting more randomness
    RANDOM_KEYWORDS = [
        "random",
        "lottery",
        "coin",
        "dice",
        "roulette",
        "first",
        "exact",
        "specific number",
        "weather",
        "temperature",
    ]

    # Keywords suggesting researchable edge
    EDGE_KEYWORDS = [
        "election",
        "policy",
        "law",
        "bill",
        "court",
        "fed",
        "inflation",
        "gdp",
        "company",
        "earnings",
        "approval",
        "poll",
    ]

    def __init__(
        self,
        coin_flip_range: tuple[Decimal, Decimal] = COIN_FLIP_RANGE,
        require_thesis: bool = True,
    ):
        """Initialize coin flip detector.

        Args:
            coin_flip_range: Price range considered "near 50/50"
            require_thesis: Whether to require an articulated thesis
        """
        self._flip_range = coin_flip_range
        self._require_thesis = require_thesis

    def assess_market(
        self,
        market: Market,
        your_thesis: Optional[str] = None,
        your_probability: Optional[Decimal] = None,
    ) -> CoinFlipAssessment:
        """Assess whether a market is a coin flip.

        Args:
            market: Market to assess
            your_thesis: Your reasoning (why market is wrong)
            your_probability: Your probability estimate
        """
        reasons = []
        edge_source = None
        is_flip = False
        confidence = 0.5

        if not market.is_binary:
            return CoinFlipAssessment(
                market=market,
                is_coin_flip=False,
                confidence=0.3,
                reasons=["Multi-outcome market - different analysis needed"],
                edge_source=None,
            )

        # Check market price
        market_price = market.outcomes[0].price if market.outcomes else Decimal("0.5")

        if self._flip_range[0] <= market_price <= self._flip_range[1]:
            reasons.append(
                f"Price ({market_price:.0%}) is near 50/50 - high uncertainty"
            )
            is_flip = True
            confidence += 0.2

        # Check for random keywords
        question_lower = market.question.lower()
        random_found = [k for k in self.RANDOM_KEYWORDS if k in question_lower]
        if random_found:
            reasons.append(f"Contains randomness indicators: {random_found}")
            is_flip = True
            confidence += 0.2

        # Check for edge keywords
        edge_found = [k for k in self.EDGE_KEYWORDS if k in question_lower]
        if edge_found:
            edge_source = f"Potential edge from: {', '.join(edge_found)}"
            confidence += 0.1

        # Check thesis
        if self._require_thesis and not your_thesis:
            reasons.append("No thesis provided - can you articulate why market is wrong?")
            is_flip = True
            confidence += 0.15

        # Check probability estimate
        if your_probability is not None:
            edge = abs(your_probability - market_price)
            if edge < Decimal("0.05"):
                reasons.append(
                    f"Your estimate ({your_probability:.0%}) is very close to market "
                    f"({market_price:.0%}) - minimal edge"
                )
                is_flip = True
            elif edge >= Decimal("0.1"):
                reasons.append(
                    f"Significant disagreement with market ({edge:.0%} edge)"
                )
                is_flip = False
                edge_source = edge_source or "Your probability estimate"

        # Final assessment
        confidence = min(1.0, confidence)

        return CoinFlipAssessment(
            market=market,
            is_coin_flip=is_flip,
            confidence=confidence,
            reasons=reasons,
            edge_source=edge_source,
        )

    def validate_trade_thesis(
        self,
        market: Market,
        thesis: str,
        probability_estimate: Decimal,
    ) -> tuple[bool, list[str]]:
        """Validate a trade thesis to ensure you're not gambling.

        Returns (is_valid, list of concerns/suggestions).
        """
        concerns = []

        # Check thesis length (too short = not thought through)
        if len(thesis) < 50:
            concerns.append("Thesis is very brief - can you elaborate on your reasoning?")

        # Check for specific reasoning
        vague_phrases = [
            "i think",
            "probably",
            "might",
            "maybe",
            "seems like",
            "gut feeling",
            "intuition",
        ]
        thesis_lower = thesis.lower()
        vague_found = [p for p in vague_phrases if p in thesis_lower]
        if vague_found:
            concerns.append(
                f"Thesis contains vague language ({vague_found[0]}). "
                "What specific information supports your view?"
            )

        # Check for information edge
        edge_indicators = [
            "data",
            "poll",
            "source",
            "insider",
            "news",
            "announcement",
            "analysis",
            "model",
            "historical",
            "pattern",
        ]
        has_edge = any(ind in thesis_lower for ind in edge_indicators)
        if not has_edge:
            concerns.append(
                "Thesis doesn't mention a specific information source. "
                "Where is your edge coming from?"
            )

        # Check probability confidence
        market_price = market.outcomes[0].price if market.outcomes else Decimal("0.5")
        edge = abs(probability_estimate - market_price)

        if edge < Decimal("0.05"):
            concerns.append(
                f"Edge ({edge:.1%}) is very small. Transaction costs may exceed expected value."
            )
        elif edge > Decimal("0.3"):
            concerns.append(
                f"Edge ({edge:.1%}) is very large. Are you sure the market is this wrong? "
                "Consider what you might be missing."
            )

        is_valid = len(concerns) == 0

        if not is_valid and len(concerns) < 3:
            concerns.append(
                "Consider: What would have to be true for the market to be right?"
            )

        return is_valid, concerns

    def get_trade_checklist(self, market: Market) -> list[str]:
        """Get a checklist of questions to answer before trading.

        If you can't answer these, you might be gambling.
        """
        return [
            f"What specific information do you have about '{market.question[:50]}...'?",
            "Why do you think the market is wrong?",
            "What is your probability estimate and how did you arrive at it?",
            "What would change your mind?",
            "What information might you be missing?",
            "Who is on the other side of this trade and why might they be right?",
            "If this were a coin flip, would you still want to trade it?",
            "What is your expected value calculation?",
            "Is this trade size appropriate for your edge confidence?",
            "What is your exit plan if you're wrong?",
        ]

    def suggest_research(self, market: Market) -> list[str]:
        """Suggest research to do before trading a market.

        Helps identify potential edge sources.
        """
        suggestions = []
        question_lower = market.question.lower()

        if any(k in question_lower for k in ["election", "president", "senator", "governor"]):
            suggestions.extend(
                [
                    "Check recent polling data (538, RealClearPolitics)",
                    "Review demographic trends in relevant regions",
                    "Check prediction market consensus (compare Polymarket vs Manifold)",
                    "Look for recent endorsements or campaign events",
                ]
            )

        if any(k in question_lower for k in ["fed", "rate", "inflation", "gdp"]):
            suggestions.extend(
                [
                    "Review Fed dot plots and meeting minutes",
                    "Check CME FedWatch tool for rate expectations",
                    "Review recent economic indicators",
                    "Look at bond market implied probabilities",
                ]
            )

        if any(k in question_lower for k in ["company", "stock", "earnings", "ceo"]):
            suggestions.extend(
                [
                    "Check SEC filings and earnings transcripts",
                    "Review analyst estimates and revisions",
                    "Look for insider trading patterns",
                    "Check news for recent developments",
                ]
            )

        if any(k in question_lower for k in ["court", "ruling", "case", "legal"]):
            suggestions.extend(
                [
                    "Review court documents and filings",
                    "Check legal expert commentary",
                    "Look at historical rulings from same judge/court",
                    "Review oral argument transcripts if available",
                ]
            )

        if not suggestions:
            suggestions = [
                "Search for recent news about this topic",
                "Check other prediction markets for comparison",
                "Look for expert commentary or analysis",
                "Review historical similar events",
                "Consider what insiders might know",
            ]

        return suggestions

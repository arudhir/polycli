"""Check resolution criteria obsessively.

Ambiguous criteria create edge but also massive risk - know exactly
what wins/loses.
"""

from dataclasses import dataclass
from typing import Optional

from polycli.models import Market


@dataclass
class ResolutionAnalysis:
    """Analysis of a market's resolution criteria."""

    market: Market
    clarity_score: float  # 0-1, higher = clearer
    ambiguity_risks: list[str]
    edge_opportunities: list[str]
    resolution_source: Optional[str]
    is_objective: bool  # Can be objectively determined
    recommended: bool
    warnings: list[str]


class ResolutionAnalyzer:
    """Analyze market resolution criteria for clarity and risk."""

    # Words that suggest ambiguity
    AMBIGUOUS_WORDS = [
        "significant",
        "substantial",
        "major",
        "meaningful",
        "approximately",
        "around",
        "roughly",
        "about",
        "likely",
        "probably",
        "reasonable",
        "adequate",
        "sufficient",
    ]

    # Words that suggest objectivity
    OBJECTIVE_WORDS = [
        "exactly",
        "precisely",
        "official",
        "certified",
        "announced",
        "reported",
        "confirmed",
        "according to",
        "per",
        "defined as",
    ]

    # Reliable resolution sources
    RELIABLE_SOURCES = [
        "ap",
        "associated press",
        "reuters",
        "official",
        "government",
        "sec",
        "federal reserve",
        "bls",
        "census",
        "whitehouse",
        "congress",
    ]

    def __init__(
        self,
        min_clarity_score: float = 0.6,
        allow_ambiguous_edge: bool = False,
    ):
        """Initialize resolution analyzer.

        Args:
            min_clarity_score: Minimum clarity for recommendation
            allow_ambiguous_edge: Whether to recommend ambiguous markets for edge
        """
        self._min_clarity = min_clarity_score
        self._allow_ambiguous = allow_ambiguous_edge

    def analyze_market(self, market: Market) -> ResolutionAnalysis:
        """Analyze a market's resolution criteria.

        Args:
            market: Market to analyze
        """
        question = market.question.lower()
        resolution = (market.resolution_source or "").lower()
        full_text = f"{question} {resolution}"

        ambiguity_risks = []
        edge_opportunities = []
        warnings = []

        # Check for ambiguous language
        ambiguous_found = [w for w in self.AMBIGUOUS_WORDS if w in full_text]
        if ambiguous_found:
            ambiguity_risks.append(
                f"Contains ambiguous terms: {', '.join(ambiguous_found)}"
            )

        # Check for objective language
        objective_found = [w for w in self.OBJECTIVE_WORDS if w in full_text]
        is_objective = len(objective_found) > 0 or len(ambiguous_found) == 0

        # Check resolution source
        has_reliable_source = any(s in resolution for s in self.RELIABLE_SOURCES)
        if has_reliable_source:
            edge_opportunities.append("Has reliable official resolution source")
        elif resolution:
            warnings.append("Resolution source may not be fully reliable")
        else:
            warnings.append("No explicit resolution source specified")

        # Check for specific numbers/dates
        has_specific = any(c.isdigit() for c in question)
        if has_specific:
            edge_opportunities.append("Contains specific numeric criteria")

        # Calculate clarity score
        clarity = self._calculate_clarity_score(
            len(ambiguous_found),
            len(objective_found),
            has_reliable_source,
            has_specific,
        )

        # Check for edge in ambiguity
        if len(ambiguous_found) > 0 and self._allow_ambiguous:
            edge_opportunities.append(
                "Ambiguity may create edge if you understand resolution better than market"
            )

        # Generate warnings
        if clarity < 0.4:
            warnings.append(
                "HIGH RISK: Resolution criteria are very ambiguous. "
                "Consider avoiding or deeply researching resolution process."
            )

        if "discretion" in full_text or "judgment" in full_text:
            warnings.append("Resolution may involve subjective judgment")

        # Determine recommendation
        recommended = clarity >= self._min_clarity
        if self._allow_ambiguous and clarity < self._min_clarity:
            if len(edge_opportunities) >= 2:
                recommended = True
                warnings.append("Recommended despite low clarity due to edge opportunity")

        return ResolutionAnalysis(
            market=market,
            clarity_score=clarity,
            ambiguity_risks=ambiguity_risks,
            edge_opportunities=edge_opportunities,
            resolution_source=market.resolution_source,
            is_objective=is_objective,
            recommended=recommended,
            warnings=warnings,
        )

    def _calculate_clarity_score(
        self,
        ambiguous_count: int,
        objective_count: int,
        has_source: bool,
        has_specific: bool,
    ) -> float:
        """Calculate clarity score from 0-1."""
        score = 0.5  # Base score

        # Penalize ambiguity
        score -= ambiguous_count * 0.1

        # Reward objectivity
        score += objective_count * 0.1

        # Reward reliable source
        if has_source:
            score += 0.2

        # Reward specific criteria
        if has_specific:
            score += 0.1

        return max(0.0, min(1.0, score))

    def get_resolution_questions(self, market: Market) -> list[str]:
        """Generate questions to research about resolution.

        These help ensure you understand what wins/loses.
        """
        questions = [
            f"What is the exact resolution source for '{market.question[:50]}...'?",
            "What specific event or data point triggers resolution?",
            "Who decides if the criteria are met?",
            "What happens in edge cases or ambiguous outcomes?",
            "What is the resolution timeline?",
            "Has this type of market resolved before? What were past outcomes?",
            "Are there any conditions that could void the market?",
        ]

        question_lower = market.question.lower()

        # Add specific questions based on market type
        if "election" in question_lower or "vote" in question_lower:
            questions.extend(
                [
                    "What counts as the official result (AP call, certified results, etc.)?",
                    "How are recounts or contested results handled?",
                    "What if the candidate drops out or is disqualified?",
                ]
            )

        if "price" in question_lower or "reach" in question_lower:
            questions.extend(
                [
                    "What price source is used?",
                    "Is it based on a specific time or any time during the period?",
                    "How is the exact price determined (bid, ask, last trade)?",
                ]
            )

        if "announcement" in question_lower or "announce" in question_lower:
            questions.extend(
                [
                    "What counts as an official announcement?",
                    "Does a leaked report count?",
                    "What if the announcement is later retracted?",
                ]
            )

        return questions

    def compare_similar_markets(
        self, markets: list[Market]
    ) -> list[tuple[Market, ResolutionAnalysis]]:
        """Compare resolution criteria across similar markets.

        Useful for finding the clearest market when multiple exist.
        """
        analyzed = [(m, self.analyze_market(m)) for m in markets]

        # Sort by clarity score
        analyzed.sort(key=lambda x: x[1].clarity_score, reverse=True)

        return analyzed

    def check_resolution_consistency(
        self, market: Market, your_interpretation: str
    ) -> dict:
        """Check if your interpretation aligns with likely resolution.

        Args:
            market: Market to check
            your_interpretation: How you think it resolves
        """
        analysis = self.analyze_market(market)

        concerns = []
        if not analysis.is_objective:
            concerns.append(
                "Resolution may be subjective - your interpretation may differ from resolver's"
            )

        if analysis.clarity_score < 0.5:
            concerns.append(
                "Low clarity score - higher chance of unexpected resolution"
            )

        if not analysis.resolution_source:
            concerns.append(
                "No clear resolution source - verify with market operator"
            )

        return {
            "your_interpretation": your_interpretation,
            "analysis": analysis,
            "concerns": concerns,
            "recommendation": (
                "Proceed with caution"
                if concerns
                else "Interpretation seems consistent with criteria"
            ),
        }

    def find_arbitrage_opportunities(
        self, market1: Market, market2: Market
    ) -> Optional[dict]:
        """Find if resolution differences create arbitrage between similar markets.

        Sometimes the same event has different markets with different
        resolution criteria, creating opportunity.
        """
        analysis1 = self.analyze_market(market1)
        analysis2 = self.analyze_market(market2)

        if analysis1.resolution_source == analysis2.resolution_source:
            return None

        return {
            "market1": {
                "question": market1.question,
                "source": analysis1.resolution_source,
                "clarity": analysis1.clarity_score,
            },
            "market2": {
                "question": market2.question,
                "source": analysis2.resolution_source,
                "clarity": analysis2.clarity_score,
            },
            "potential_arbitrage": True,
            "explanation": (
                "These markets may resolve differently despite similar questions. "
                "If you understand the resolution difference, there may be edge."
            ),
        }

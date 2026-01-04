"""Diversify by resolution type.

Mix markets resolving on different dates, different topics,
different information sources.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from polycli.models import Market, Position


@dataclass
class DiversificationScore:
    """Score measuring portfolio diversification."""

    overall_score: float  # 0-100
    time_diversity: float  # 0-100
    topic_diversity: float  # 0-100
    source_diversity: float  # 0-100
    concentration_risk: float  # 0-100 (higher = more concentrated = worse)
    recommendations: list[str]


@dataclass
class DiversificationOpportunity:
    """An opportunity to improve diversification."""

    market: Market
    would_improve_by: float
    category_need: str  # What diversity category it helps
    notes: str


class DiversificationAnalyzer:
    """Analyze and improve portfolio diversification."""

    # Topic categories
    TOPIC_KEYWORDS = {
        "politics_us": ["trump", "biden", "election", "senate", "congress", "republican", "democrat"],
        "politics_intl": ["ukraine", "russia", "china", "eu", "brexit"],
        "crypto": ["bitcoin", "ethereum", "crypto", "btc", "eth"],
        "economic": ["fed", "inflation", "gdp", "unemployment", "rate"],
        "tech": ["ai", "openai", "google", "apple", "microsoft", "meta"],
        "sports": ["game", "championship", "nba", "nfl", "soccer"],
        "entertainment": ["oscar", "grammy", "movie", "album"],
    }

    def __init__(
        self,
        target_time_buckets: int = 4,
        target_topic_count: int = 3,
        max_single_topic_pct: Decimal = Decimal("0.4"),
    ):
        """Initialize diversification analyzer.

        Args:
            target_time_buckets: Target number of resolution time buckets
            target_topic_count: Target number of different topics
            max_single_topic_pct: Max % of portfolio in single topic
        """
        self._target_time_buckets = target_time_buckets
        self._target_topics = target_topic_count
        self._max_topic_pct = max_single_topic_pct

    def analyze_portfolio(
        self, positions: list[Position]
    ) -> DiversificationScore:
        """Analyze portfolio diversification.

        Args:
            positions: All current positions
        """
        if not positions:
            return DiversificationScore(
                overall_score=0,
                time_diversity=0,
                topic_diversity=0,
                source_diversity=0,
                concentration_risk=0,
                recommendations=["No positions to analyze"],
            )

        # Calculate component scores
        time_score = self._calculate_time_diversity(positions)
        topic_score = self._calculate_topic_diversity(positions)
        source_score = self._calculate_source_diversity(positions)
        concentration = self._calculate_concentration_risk(positions)

        # Overall score (weighted average)
        overall = (
            time_score * 0.25 +
            topic_score * 0.35 +
            source_score * 0.20 +
            (100 - concentration) * 0.20
        )

        recommendations = self._generate_recommendations(
            time_score, topic_score, source_score, concentration, positions
        )

        return DiversificationScore(
            overall_score=overall,
            time_diversity=time_score,
            topic_diversity=topic_score,
            source_diversity=source_score,
            concentration_risk=concentration,
            recommendations=recommendations,
        )

    def _calculate_time_diversity(self, positions: list[Position]) -> float:
        """Calculate time-based diversification score."""
        # Group by resolution time bucket
        buckets = {
            "immediate": [],  # 0-7 days
            "short": [],  # 7-30 days
            "medium": [],  # 30-90 days
            "long": [],  # 90+ days
        }

        now = datetime.utcnow()

        for p in positions:
            # Estimate resolution from entry date + typical market duration
            # In practice, you'd want actual resolution date
            days_held = (now - p.entry_date).days
            estimated_remaining = max(0, 60 - days_held)  # Rough estimate

            if estimated_remaining <= 7:
                buckets["immediate"].append(p)
            elif estimated_remaining <= 30:
                buckets["short"].append(p)
            elif estimated_remaining <= 90:
                buckets["medium"].append(p)
            else:
                buckets["long"].append(p)

        # Score based on bucket distribution
        non_empty_buckets = sum(1 for b in buckets.values() if b)
        total_value = sum(p.cost_basis for p in positions)

        if total_value == 0:
            return 0

        # Penalize concentration in single bucket
        max_bucket_value = max(
            sum(p.cost_basis for p in bucket) for bucket in buckets.values()
        )
        concentration_penalty = float(max_bucket_value / total_value) * 50

        bucket_score = (non_empty_buckets / self._target_time_buckets) * 100
        return max(0, min(100, bucket_score - concentration_penalty))

    def _calculate_topic_diversity(self, positions: list[Position]) -> float:
        """Calculate topic-based diversification score."""
        topic_exposure: dict[str, Decimal] = {}
        total_value = Decimal(0)

        for p in positions:
            question_lower = p.market_question.lower()
            total_value += p.cost_basis

            # Identify topics
            for topic, keywords in self.TOPIC_KEYWORDS.items():
                if any(kw in question_lower for kw in keywords):
                    topic_exposure[topic] = topic_exposure.get(topic, Decimal(0)) + p.cost_basis

        if total_value == 0:
            return 0

        # Score based on number of topics and concentration
        num_topics = len(topic_exposure)
        topic_score = (num_topics / self._target_topics) * 60

        # Penalize over-concentration in single topic
        if topic_exposure:
            max_topic_pct = max(topic_exposure.values()) / total_value
            if max_topic_pct > self._max_topic_pct:
                concentration_penalty = float(max_topic_pct - self._max_topic_pct) * 100
            else:
                concentration_penalty = 0
        else:
            concentration_penalty = 0

        return max(0, min(100, topic_score + 40 - concentration_penalty))

    def _calculate_source_diversity(self, positions: list[Position]) -> float:
        """Calculate resolution source diversity score.

        Different resolution sources = different risk factors.
        """
        # Group by resolution source type (inferred from question)
        source_types = {
            "official_govt": ["government", "official", "congress", "fed"],
            "news_org": ["announced", "reported", "ap", "reuters"],
            "exchange": ["price", "btc", "eth", "market"],
            "sports": ["game", "match", "score"],
            "other": [],
        }

        source_exposure: dict[str, Decimal] = {}
        total_value = Decimal(0)

        for p in positions:
            question_lower = p.market_question.lower()
            total_value += p.cost_basis
            found_source = False

            for source, keywords in source_types.items():
                if keywords and any(kw in question_lower for kw in keywords):
                    source_exposure[source] = source_exposure.get(source, Decimal(0)) + p.cost_basis
                    found_source = True
                    break

            if not found_source:
                source_exposure["other"] = source_exposure.get("other", Decimal(0)) + p.cost_basis

        if total_value == 0:
            return 0

        # Score based on number of different sources
        num_sources = len(source_exposure)
        return min(100, num_sources * 25)

    def _calculate_concentration_risk(self, positions: list[Position]) -> float:
        """Calculate concentration risk (Herfindahl-like index)."""
        if not positions:
            return 0

        total_value = sum(p.cost_basis for p in positions)
        if total_value == 0:
            return 0

        # Calculate sum of squared market shares
        hhi = sum(
            float(p.cost_basis / total_value) ** 2
            for p in positions
        )

        # Convert to 0-100 scale (HHI ranges from 1/n to 1)
        # Higher HHI = more concentrated
        n = len(positions)
        min_hhi = 1 / n if n > 0 else 1
        max_hhi = 1

        if max_hhi == min_hhi:
            return 0

        normalized = (hhi - min_hhi) / (max_hhi - min_hhi)
        return normalized * 100

    def _generate_recommendations(
        self,
        time_score: float,
        topic_score: float,
        source_score: float,
        concentration: float,
        positions: list[Position],
    ) -> list[str]:
        """Generate diversification recommendations."""
        recommendations = []

        if time_score < 50:
            recommendations.append(
                "Time diversity is low. Consider adding positions with "
                "different resolution dates."
            )

        if topic_score < 50:
            recommendations.append(
                "Topic diversity is low. Consider exploring different "
                "market categories."
            )

        if source_score < 50:
            recommendations.append(
                "Resolution source diversity is low. Markets may have "
                "correlated resolution risks."
            )

        if concentration > 60:
            # Find the largest position
            if positions:
                largest = max(positions, key=lambda p: p.cost_basis)
                total = sum(p.cost_basis for p in positions)
                if total > 0:
                    pct = largest.cost_basis / total
                    recommendations.append(
                        f"Portfolio is concentrated. Largest position "
                        f"('{largest.market_question[:30]}...') is {pct:.0%} of portfolio."
                    )

        if not recommendations:
            recommendations.append("Portfolio diversification looks healthy.")

        return recommendations

    def find_diversifying_markets(
        self,
        current_positions: list[Position],
        candidate_markets: list[Market],
        top_n: int = 5,
    ) -> list[DiversificationOpportunity]:
        """Find markets that would improve diversification.

        Args:
            current_positions: Current portfolio positions
            candidate_markets: Markets to consider
            top_n: Number of opportunities to return
        """
        current_score = self.analyze_portfolio(current_positions)
        opportunities = []

        for market in candidate_markets:
            # Check if this market adds diversity
            topic = self._get_market_topic(market)
            current_topics = self._get_portfolio_topics(current_positions)

            improvement = 0
            category_need = ""

            # New topic?
            if topic and topic not in current_topics:
                improvement += 20
                category_need = f"new topic: {topic}"

            # Different time horizon?
            # (Would need resolution date from market)

            # Only include if it improves something
            if improvement > 0:
                opportunities.append(
                    DiversificationOpportunity(
                        market=market,
                        would_improve_by=improvement,
                        category_need=category_need,
                        notes=f"Current topics: {list(current_topics)}",
                    )
                )

        # Sort by improvement potential
        opportunities.sort(key=lambda o: o.would_improve_by, reverse=True)
        return opportunities[:top_n]

    def _get_market_topic(self, market: Market) -> Optional[str]:
        """Identify topic of a market."""
        question_lower = market.question.lower()
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in question_lower for kw in keywords):
                return topic
        return None

    def _get_portfolio_topics(self, positions: list[Position]) -> set[str]:
        """Get set of topics in portfolio."""
        topics = set()
        for p in positions:
            question_lower = p.market_question.lower()
            for topic, keywords in self.TOPIC_KEYWORDS.items():
                if any(kw in question_lower for kw in keywords):
                    topics.add(topic)
        return topics

    def suggest_rebalancing(
        self, positions: list[Position], target_diversification: float = 70
    ) -> list[str]:
        """Suggest rebalancing to improve diversification.

        Args:
            positions: Current positions
            target_diversification: Target overall score
        """
        current = self.analyze_portfolio(positions)

        if current.overall_score >= target_diversification:
            return ["Portfolio meets diversification target."]

        suggestions = []

        # Identify over-weighted topics
        topic_exposure: dict[str, Decimal] = {}
        total = sum(p.cost_basis for p in positions)

        for p in positions:
            question_lower = p.market_question.lower()
            for topic, keywords in self.TOPIC_KEYWORDS.items():
                if any(kw in question_lower for kw in keywords):
                    topic_exposure[topic] = topic_exposure.get(topic, Decimal(0)) + p.cost_basis

        if total > 0:
            for topic, exposure in topic_exposure.items():
                pct = exposure / total
                if pct > self._max_topic_pct:
                    suggestions.append(
                        f"Reduce {topic} exposure from {pct:.0%} to "
                        f"{self._max_topic_pct:.0%} (${exposure - total * self._max_topic_pct:.0f})"
                    )

        return suggestions if suggestions else ["No specific rebalancing needed."]

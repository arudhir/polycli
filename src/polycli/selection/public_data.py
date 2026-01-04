"""Prioritize markets with public data.

You want verifiable information advantages, not pure speculation.
"""

from dataclasses import dataclass
from typing import Optional

from polycli.models import Market


@dataclass
class PublicDataProfile:
    """Profile of available public data for a market."""

    market: Market
    data_sources: list[str]
    data_quality_score: float  # 0-1
    edge_type: str  # "analysis", "speed", "interpretation", "none"
    research_difficulty: str  # "easy", "medium", "hard", "expert"
    is_verifiable: bool
    notes: list[str]


class PublicDataChecker:
    """Check and evaluate public data availability for markets."""

    # Known data sources by topic
    DATA_SOURCES = {
        "election": [
            "FiveThirtyEight (538)",
            "RealClearPolitics",
            "Cook Political Report",
            "Sabato's Crystal Ball",
            "State election offices",
            "Census Bureau demographics",
        ],
        "economic": [
            "Federal Reserve FRED database",
            "Bureau of Labor Statistics",
            "Bureau of Economic Analysis",
            "Census Bureau",
            "CME FedWatch Tool",
            "Bloomberg Economic Calendar",
        ],
        "crypto": [
            "CoinGecko / CoinMarketCap",
            "Glassnode (on-chain data)",
            "DeFiLlama",
            "Etherscan / blockchain explorers",
            "Exchange order books",
            "Whale Alert",
        ],
        "company": [
            "SEC EDGAR filings",
            "Earnings call transcripts",
            "Yahoo Finance / Google Finance",
            "Company investor relations",
            "Industry reports",
            "Patent databases",
        ],
        "legal": [
            "PACER (court records)",
            "Supreme Court docket",
            "State court records",
            "Legal news (Law360, Reuters Legal)",
            "Expert legal commentary",
        ],
        "sports": [
            "Team statistics databases",
            "Injury reports",
            "Historical matchup data",
            "Betting line movement",
            "Weather forecasts",
        ],
    }

    # Keywords to topic mapping
    TOPIC_KEYWORDS = {
        "election": ["election", "vote", "poll", "president", "senate", "congress", "governor"],
        "economic": ["fed", "inflation", "gdp", "unemployment", "rate", "cpi", "jobs"],
        "crypto": ["bitcoin", "ethereum", "crypto", "btc", "eth", "token", "defi"],
        "company": ["company", "stock", "earnings", "ceo", "ipo", "acquisition", "revenue"],
        "legal": ["court", "ruling", "case", "trial", "judge", "lawsuit", "verdict"],
        "sports": ["game", "match", "championship", "team", "player", "score"],
    }

    def __init__(
        self,
        min_data_quality: float = 0.5,
        prefer_verifiable: bool = True,
    ):
        """Initialize public data checker.

        Args:
            min_data_quality: Minimum data quality score for recommendation
            prefer_verifiable: Whether to prefer verifiable data markets
        """
        self._min_quality = min_data_quality
        self._prefer_verifiable = prefer_verifiable

    def analyze_market(self, market: Market) -> PublicDataProfile:
        """Analyze public data availability for a market.

        Args:
            market: Market to analyze
        """
        question_lower = market.question.lower()
        notes = []

        # Identify topic
        topic = self._identify_topic(question_lower)
        data_sources = self.DATA_SOURCES.get(topic, [])

        if not data_sources:
            notes.append("No standard data sources identified for this market type")

        # Calculate data quality score
        quality = self._calculate_data_quality(topic, question_lower, data_sources)

        # Determine edge type
        edge_type = self._determine_edge_type(topic, quality)

        # Determine research difficulty
        difficulty = self._assess_research_difficulty(topic, question_lower)

        # Check verifiability
        is_verifiable = quality >= 0.5 and len(data_sources) > 0

        # Add notes based on analysis
        if quality >= 0.7:
            notes.append("Strong public data available - edge likely from analysis")
        elif quality >= 0.4:
            notes.append("Moderate public data - may need specialized sources")
        else:
            notes.append("Limited public data - consider if you have private information edge")

        if edge_type == "speed":
            notes.append("Edge may come from faster data access or processing")
        elif edge_type == "interpretation":
            notes.append("Edge may come from better interpretation of complex data")

        return PublicDataProfile(
            market=market,
            data_sources=data_sources,
            data_quality_score=quality,
            edge_type=edge_type,
            research_difficulty=difficulty,
            is_verifiable=is_verifiable,
            notes=notes,
        )

    def _identify_topic(self, question: str) -> Optional[str]:
        """Identify the topic of a market question."""
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in question for kw in keywords):
                return topic
        return None

    def _calculate_data_quality(
        self,
        topic: Optional[str],
        question: str,
        sources: list[str],
    ) -> float:
        """Calculate data quality score."""
        score = 0.3  # Base score

        # Topic with known sources
        if topic and sources:
            score += 0.3

        # Official/authoritative keywords
        if any(
            word in question
            for word in ["official", "announced", "reported", "published"]
        ):
            score += 0.2

        # Numeric criteria (more verifiable)
        if any(c.isdigit() for c in question):
            score += 0.1

        # Penalize vague topics
        if any(
            word in question
            for word in ["might", "could", "possibly", "rumor"]
        ):
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _determine_edge_type(self, topic: Optional[str], quality: float) -> str:
        """Determine what type of edge is possible."""
        if quality < 0.3:
            return "none"

        if topic in ["crypto", "sports"]:
            return "speed"  # Real-time data matters

        if topic in ["legal", "economic"]:
            return "interpretation"  # Complex data needs analysis

        if topic in ["election", "company"]:
            return "analysis"  # Research-based edge

        return "analysis"

    def _assess_research_difficulty(
        self, topic: Optional[str], question: str
    ) -> str:
        """Assess how difficult research would be."""
        if topic is None:
            return "hard"  # Unknown territory

        easy_topics = ["sports", "crypto"]
        hard_topics = ["legal"]
        expert_topics = []

        if topic in expert_topics:
            return "expert"
        if topic in hard_topics:
            return "hard"
        if topic in easy_topics:
            return "easy"

        return "medium"

    def get_research_plan(self, market: Market) -> dict:
        """Generate a research plan for a market.

        Args:
            market: Market to research
        """
        profile = self.analyze_market(market)

        plan = {
            "market": market.question,
            "primary_sources": profile.data_sources[:3] if profile.data_sources else [],
            "secondary_sources": profile.data_sources[3:] if len(profile.data_sources) > 3 else [],
            "edge_type": profile.edge_type,
            "estimated_difficulty": profile.research_difficulty,
            "research_steps": [],
            "verification_methods": [],
        }

        # Generate research steps based on topic
        topic = self._identify_topic(market.question.lower())

        if topic == "election":
            plan["research_steps"] = [
                "Check current polling averages (538, RCP)",
                "Review recent poll releases and methodology",
                "Analyze demographic trends",
                "Check early voting data if available",
                "Compare with prediction market consensus",
            ]
            plan["verification_methods"] = [
                "Cross-reference multiple pollsters",
                "Check pollster ratings and track records",
            ]

        elif topic == "economic":
            plan["research_steps"] = [
                "Review recent economic data releases",
                "Check Fed communications and dot plots",
                "Analyze market-implied probabilities",
                "Review economist forecasts",
                "Monitor leading indicators",
            ]
            plan["verification_methods"] = [
                "Compare multiple economic models",
                "Check historical prediction accuracy",
            ]

        elif topic == "crypto":
            plan["research_steps"] = [
                "Check current price and volume",
                "Analyze on-chain metrics",
                "Review whale movements",
                "Check derivatives market sentiment",
                "Monitor social sentiment",
            ]
            plan["verification_methods"] = [
                "Use multiple price sources",
                "Cross-reference on-chain data",
            ]

        else:
            plan["research_steps"] = [
                "Identify primary news sources",
                "Check for official announcements",
                "Review expert commentary",
                "Compare with similar past events",
                "Monitor for new developments",
            ]
            plan["verification_methods"] = [
                "Use multiple sources",
                "Prefer official over unofficial sources",
            ]

        return plan

    def find_data_rich_markets(
        self, markets: list[Market], min_quality: Optional[float] = None
    ) -> list[tuple[Market, PublicDataProfile]]:
        """Find markets with strong public data available.

        These are better for research-based trading.
        """
        quality_threshold = min_quality or self._min_quality

        analyzed = []
        for market in markets:
            profile = self.analyze_market(market)
            if profile.data_quality_score >= quality_threshold:
                analyzed.append((market, profile))

        # Sort by data quality
        analyzed.sort(key=lambda x: x[1].data_quality_score, reverse=True)
        return analyzed

    def compare_markets_by_data(
        self, markets: list[Market]
    ) -> list[tuple[Market, PublicDataProfile]]:
        """Compare markets by their data availability.

        Useful for choosing between similar markets.
        """
        profiles = [(m, self.analyze_market(m)) for m in markets]
        profiles.sort(key=lambda x: x[1].data_quality_score, reverse=True)
        return profiles

    def suggest_data_sources(self, market: Market) -> list[str]:
        """Suggest specific data sources for a market."""
        profile = self.analyze_market(market)

        suggestions = profile.data_sources.copy()

        # Add generic suggestions
        suggestions.extend(
            [
                "Google News (set alerts for relevant keywords)",
                "Twitter/X (follow relevant experts)",
                "Reddit (topic-specific subreddits)",
                "Other prediction markets (Manifold, Metaculus)",
            ]
        )

        return suggestions

"""Correlation analysis for related markets.

Markets move together - if Trump odds shift, immediately check
related markets (GOP Senate, specific policies) for slower-updating
opportunities.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

import numpy as np

from polycli.api.polymarket import PolymarketClient
from polycli.models import Market


@dataclass
class CorrelatedMarket:
    """A market correlated with a base market."""

    market: Market
    correlation: float
    price_history_aligned: bool
    lag_hours: int  # Positive means this market lags the base


@dataclass
class CorrelationOpportunity:
    """An opportunity where correlated market hasn't moved yet."""

    base_market: Market
    correlated_market: Market
    base_price_change: Decimal
    correlated_current_price: Decimal
    expected_price: Decimal
    opportunity_size: Decimal
    detected_at: datetime


class CorrelationAnalyzer:
    """Analyze correlations between markets to find opportunities."""

    # Common market groupings (customize based on your focus)
    MARKET_GROUPS = {
        "us_politics_2024": [
            "trump",
            "biden",
            "republican",
            "democrat",
            "senate",
            "house",
            "electoral",
        ],
        "crypto": ["bitcoin", "ethereum", "crypto", "btc", "eth"],
        "fed": ["fed", "fomc", "interest rate", "powell", "inflation"],
        "geopolitics": ["russia", "ukraine", "china", "taiwan", "war"],
    }

    def __init__(
        self,
        client: PolymarketClient,
        min_correlation: float = 0.6,
        lookback_periods: int = 30,
    ):
        """Initialize correlation analyzer.

        Args:
            client: Polymarket API client
            min_correlation: Minimum correlation to consider related
            lookback_periods: Number of price points to use for correlation
        """
        self._client = client
        self._min_correlation = min_correlation
        self._lookback = lookback_periods
        self._price_cache: dict[str, list[dict]] = {}

    async def get_price_history(self, token_id: str) -> list[dict]:
        """Fetch and cache price history for a token."""
        if token_id not in self._price_cache:
            history = await self._client.get_price_history(
                token_id, interval="1h", limit=self._lookback * 24
            )
            self._price_cache[token_id] = history
        return self._price_cache[token_id]

    def _calculate_correlation(
        self, prices1: list[float], prices2: list[float]
    ) -> float:
        """Calculate Pearson correlation between two price series."""
        if len(prices1) < 10 or len(prices2) < 10:
            return 0.0

        # Align lengths
        min_len = min(len(prices1), len(prices2))
        p1 = np.array(prices1[:min_len])
        p2 = np.array(prices2[:min_len])

        # Calculate returns instead of prices for better correlation
        if len(p1) < 2:
            return 0.0

        r1 = np.diff(p1) / (p1[:-1] + 1e-10)
        r2 = np.diff(p2) / (p2[:-1] + 1e-10)

        if np.std(r1) < 1e-10 or np.std(r2) < 1e-10:
            return 0.0

        correlation = np.corrcoef(r1, r2)[0, 1]
        return float(correlation) if not np.isnan(correlation) else 0.0

    async def find_correlated_markets(
        self, base_market: Market, candidate_markets: list[Market]
    ) -> list[CorrelatedMarket]:
        """Find markets correlated with a base market.

        Args:
            base_market: The market to find correlations for
            candidate_markets: Markets to check for correlation
        """
        if not base_market.outcomes:
            return []

        base_token = base_market.outcomes[0].token_id
        base_history = await self.get_price_history(base_token)
        base_prices = [float(h.get("price", 0)) for h in base_history]

        correlated = []
        for market in candidate_markets:
            if market.condition_id == base_market.condition_id:
                continue
            if not market.outcomes:
                continue

            token = market.outcomes[0].token_id
            history = await self.get_price_history(token)
            prices = [float(h.get("price", 0)) for h in history]

            correlation = self._calculate_correlation(base_prices, prices)

            if abs(correlation) >= self._min_correlation:
                correlated.append(
                    CorrelatedMarket(
                        market=market,
                        correlation=correlation,
                        price_history_aligned=len(base_prices) == len(prices),
                        lag_hours=0,  # Could calculate lag with cross-correlation
                    )
                )

        # Sort by correlation strength
        correlated.sort(key=lambda c: abs(c.correlation), reverse=True)
        return correlated

    async def find_related_by_keywords(
        self, market: Market, markets: Optional[list[Market]] = None
    ) -> list[Market]:
        """Find markets related by shared keywords/topics.

        This is a simpler heuristic that doesn't require price history.
        """
        if markets is None:
            markets = await self._client.get_markets(limit=500, active=True)

        # Extract keywords from base market
        base_words = set(market.question.lower().split())
        base_tags = set(t.lower() for t in market.tags)

        # Score other markets by keyword overlap
        scored = []
        for m in markets:
            if m.condition_id == market.condition_id:
                continue

            m_words = set(m.question.lower().split())
            m_tags = set(t.lower() for t in m.tags)

            # Calculate overlap
            word_overlap = len(base_words & m_words)
            tag_overlap = len(base_tags & m_tags)
            score = word_overlap + (tag_overlap * 3)  # Weight tags more

            if score > 2:  # Minimum relevance threshold
                scored.append((score, m))

        # Sort by score and return markets
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:20]]

    async def detect_lagging_opportunities(
        self,
        base_market: Market,
        price_change_threshold: Decimal = Decimal("0.05"),
    ) -> list[CorrelationOpportunity]:
        """Find opportunities where correlated markets haven't moved yet.

        When a base market moves significantly, check if correlated
        markets have adjusted. If not, there may be an opportunity.

        Args:
            base_market: Market that moved
            price_change_threshold: Minimum price move to trigger check
        """
        if not base_market.outcomes:
            return []

        # Get base market price history
        base_token = base_market.outcomes[0].token_id
        base_history = await self.get_price_history(base_token)

        if len(base_history) < 2:
            return []

        # Calculate recent price change
        current_price = Decimal(str(base_history[0].get("price", 0)))
        old_price = Decimal(str(base_history[-1].get("price", 0)))
        price_change = current_price - old_price

        if abs(price_change) < price_change_threshold:
            return []

        # Find correlated markets
        all_markets = await self._client.get_markets(limit=200, active=True)
        related = await self.find_related_by_keywords(base_market, all_markets)

        opportunities = []
        for market in related:
            if not market.outcomes:
                continue

            # Check if this market has moved similarly
            token = market.outcomes[0].token_id
            history = await self.get_price_history(token)

            if len(history) < 2:
                continue

            m_current = Decimal(str(history[0].get("price", 0)))
            m_old = Decimal(str(history[-1].get("price", 0)))
            m_change = m_current - m_old

            # If correlated market hasn't moved much, opportunity exists
            if abs(m_change) < abs(price_change) * Decimal("0.3"):
                expected_price = m_old + (price_change * Decimal("0.7"))
                expected_price = max(Decimal(0), min(Decimal(1), expected_price))

                opportunities.append(
                    CorrelationOpportunity(
                        base_market=base_market,
                        correlated_market=market,
                        base_price_change=price_change,
                        correlated_current_price=m_current,
                        expected_price=expected_price,
                        opportunity_size=abs(expected_price - m_current),
                        detected_at=datetime.utcnow(),
                    )
                )

        # Sort by opportunity size
        opportunities.sort(key=lambda o: o.opportunity_size, reverse=True)
        return opportunities

    def get_market_group(self, market: Market) -> Optional[str]:
        """Identify which predefined group a market belongs to."""
        question_lower = market.question.lower()

        for group_name, keywords in self.MARKET_GROUPS.items():
            for keyword in keywords:
                if keyword in question_lower:
                    return group_name

        return None

    async def analyze_group(self, group_name: str) -> dict:
        """Analyze correlations within a predefined market group."""
        if group_name not in self.MARKET_GROUPS:
            raise ValueError(f"Unknown group: {group_name}")

        keywords = self.MARKET_GROUPS[group_name]
        markets = []

        for keyword in keywords:
            results = await self._client.search_markets(keyword, limit=10)
            markets.extend(results)

        # Deduplicate
        seen = set()
        unique_markets = []
        for m in markets:
            if m.condition_id not in seen:
                seen.add(m.condition_id)
                unique_markets.append(m)

        # Find all pairwise correlations
        correlations = []
        for i, m1 in enumerate(unique_markets):
            for m2 in unique_markets[i + 1 :]:
                related = await self.find_correlated_markets(m1, [m2])
                if related:
                    correlations.append(
                        {
                            "market1": m1.question[:50],
                            "market2": m2.question[:50],
                            "correlation": related[0].correlation,
                        }
                    )

        return {
            "group": group_name,
            "market_count": len(unique_markets),
            "correlations": correlations,
        }

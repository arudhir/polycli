"""Cross-reference with prediction platforms.

When Manifold or Metaculus probabilities diverge significantly
from Polymarket, there's often mispricing to exploit.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from polycli.api.external import ManifoldClient, MetaculusClient, PredictionMarket
from polycli.api.polymarket import PolymarketClient
from polycli.models import Market


@dataclass
class PriceDiscrepancy:
    """A detected price discrepancy across platforms."""

    polymarket: Market
    other_platform: PredictionMarket
    polymarket_price: Decimal
    other_price: Decimal
    discrepancy: Decimal
    discrepancy_pct: float
    detected_at: datetime


class CrossReferenceFinder:
    """Find mispricings by comparing across prediction platforms."""

    def __init__(
        self,
        polymarket_client: PolymarketClient,
        manifold_client: Optional[ManifoldClient] = None,
        metaculus_client: Optional[MetaculusClient] = None,
        min_discrepancy: Decimal = Decimal("0.05"),
    ):
        """Initialize cross-reference finder.

        Args:
            polymarket_client: Polymarket API client
            manifold_client: Manifold Markets client (optional)
            metaculus_client: Metaculus client (optional)
            min_discrepancy: Minimum price difference to flag (default 5%)
        """
        self._pm = polymarket_client
        self._manifold = manifold_client
        self._metaculus = metaculus_client
        self._min_discrepancy = min_discrepancy

    async def find_discrepancies_for_market(
        self, market: Market, search_query: Optional[str] = None
    ) -> list[PriceDiscrepancy]:
        """Find price discrepancies for a specific Polymarket market.

        Args:
            market: The Polymarket market to check
            search_query: Custom search query (defaults to market question)
        """
        query = search_query or market.question[:100]
        discrepancies = []

        # Get Polymarket price (assuming binary Yes outcome)
        pm_price = None
        for outcome in market.outcomes:
            if outcome.outcome.lower() in ["yes", "true", "1"]:
                pm_price = outcome.price
                break

        if pm_price is None and market.is_binary:
            pm_price = market.outcomes[0].price

        if pm_price is None:
            return []

        # Check Manifold
        if self._manifold:
            try:
                manifold_markets = await self._manifold.search_markets(query, limit=5)
                for m in manifold_markets:
                    discrepancy = abs(pm_price - m.probability)
                    if discrepancy >= self._min_discrepancy:
                        discrepancies.append(
                            PriceDiscrepancy(
                                polymarket=market,
                                other_platform=m,
                                polymarket_price=pm_price,
                                other_price=m.probability,
                                discrepancy=discrepancy,
                                discrepancy_pct=float(discrepancy * 100),
                                detected_at=datetime.utcnow(),
                            )
                        )
            except Exception:
                pass  # Continue even if Manifold API fails

        # Check Metaculus
        if self._metaculus:
            try:
                metaculus_questions = await self._metaculus.search_questions(query, limit=5)
                for q in metaculus_questions:
                    discrepancy = abs(pm_price - q.probability)
                    if discrepancy >= self._min_discrepancy:
                        discrepancies.append(
                            PriceDiscrepancy(
                                polymarket=market,
                                other_platform=q,
                                polymarket_price=pm_price,
                                other_price=q.probability,
                                discrepancy=discrepancy,
                                discrepancy_pct=float(discrepancy * 100),
                                detected_at=datetime.utcnow(),
                            )
                        )
            except Exception:
                pass  # Continue even if Metaculus API fails

        # Sort by discrepancy size
        discrepancies.sort(key=lambda d: d.discrepancy, reverse=True)
        return discrepancies

    async def scan_markets(
        self, markets: Optional[list[Market]] = None, limit: int = 50
    ) -> list[PriceDiscrepancy]:
        """Scan multiple markets for price discrepancies.

        Args:
            markets: List of markets to check (fetches from API if None)
            limit: Maximum number of markets to scan
        """
        if markets is None:
            markets = await self._pm.get_markets(limit=limit, active=True)

        all_discrepancies = []

        for market in markets[:limit]:
            if not market.is_binary:
                continue

            discrepancies = await self.find_discrepancies_for_market(market)
            all_discrepancies.extend(discrepancies)

        # Sort by discrepancy size
        all_discrepancies.sort(key=lambda d: d.discrepancy, reverse=True)
        return all_discrepancies

    async def get_platform_comparison(
        self, query: str
    ) -> dict[str, list[PredictionMarket]]:
        """Get matching markets across all platforms for comparison.

        Args:
            query: Search query

        Returns:
            Dict mapping platform name to list of matching markets
        """
        results: dict[str, list[PredictionMarket]] = {"polymarket": []}

        # Get Polymarket results
        pm_markets = await self._pm.search_markets(query, limit=10)
        for m in pm_markets:
            if m.is_binary:
                price = m.outcomes[0].price if m.outcomes else Decimal(0)
                results["polymarket"].append(
                    PredictionMarket(
                        platform="polymarket",
                        question=m.question,
                        url=f"https://polymarket.com/event/{m.slug}",
                        probability=price,
                        volume=m.volume,
                    )
                )

        # Get Manifold results
        if self._manifold:
            try:
                results["manifold"] = await self._manifold.search_markets(query, limit=10)
            except Exception:
                results["manifold"] = []

        # Get Metaculus results
        if self._metaculus:
            try:
                results["metaculus"] = await self._metaculus.search_questions(query, limit=10)
            except Exception:
                results["metaculus"] = []

        return results

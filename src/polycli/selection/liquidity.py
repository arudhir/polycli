"""Liquidity vs edge tradeoff analysis.

High-liquidity markets are efficient but you can actually size positions.
Niche markets have more edge but you'll move the price.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from polycli.api.polymarket import PolymarketClient
from polycli.models import Market, OrderBook


@dataclass
class LiquidityProfile:
    """Profile of a market's liquidity characteristics."""

    market: Market
    bid_depth_5pct: Decimal  # How much you can buy moving price 5%
    ask_depth_5pct: Decimal  # How much you can sell moving price 5%
    spread_pct: float
    depth_imbalance: float  # >1 means more bids than asks
    estimated_slippage_1k: float  # Slippage for $1000 trade
    estimated_slippage_10k: float  # Slippage for $10000 trade
    liquidity_score: float  # 0-100


@dataclass
class SizeRecommendation:
    """Recommended position size based on liquidity."""

    max_size_low_impact: Decimal  # Max size with <1% impact
    max_size_medium_impact: Decimal  # Max size with <5% impact
    recommended_size: Decimal
    expected_slippage: float
    effective_price: Decimal
    warning: Optional[str] = None


class LiquidityAnalyzer:
    """Analyze market liquidity and recommend position sizes."""

    def __init__(
        self,
        client: PolymarketClient,
        max_acceptable_slippage: float = 0.02,  # 2%
        max_price_impact: float = 0.01,  # 1%
    ):
        """Initialize liquidity analyzer.

        Args:
            client: Polymarket API client
            max_acceptable_slippage: Maximum acceptable slippage
            max_price_impact: Maximum acceptable price impact
        """
        self._client = client
        self._max_slippage = max_acceptable_slippage
        self._max_impact = max_price_impact

    async def get_liquidity_profile(
        self, market: Market, token_id: Optional[str] = None
    ) -> LiquidityProfile:
        """Get detailed liquidity profile for a market.

        Args:
            market: Market to analyze
            token_id: Specific token (defaults to first outcome)
        """
        if token_id is None and market.outcomes:
            token_id = market.outcomes[0].token_id

        if not token_id:
            raise ValueError("No token_id available")

        order_book = await self._client.get_order_book(token_id)

        # Calculate depth at 5% from mid
        mid = order_book.mid_price or Decimal("0.5")
        bid_target = mid * Decimal("0.95")
        ask_target = mid * Decimal("1.05")

        bid_depth = order_book.depth_at_price(bid_target, "bid")
        ask_depth = order_book.depth_at_price(ask_target, "ask")

        # Calculate spread
        spread = order_book.spread or Decimal(0)
        spread_pct = float(spread / mid) if mid > 0 else 0

        # Calculate imbalance
        total_bids = sum(level.size for level in order_book.bids)
        total_asks = sum(level.size for level in order_book.asks)
        imbalance = float(total_bids / total_asks) if total_asks > 0 else 0

        # Estimate slippage
        slippage_1k = self._estimate_slippage(order_book, Decimal(1000), "buy")
        slippage_10k = self._estimate_slippage(order_book, Decimal(10000), "buy")

        # Calculate liquidity score (0-100)
        score = self._calculate_liquidity_score(
            market.liquidity, spread_pct, bid_depth + ask_depth
        )

        return LiquidityProfile(
            market=market,
            bid_depth_5pct=bid_depth,
            ask_depth_5pct=ask_depth,
            spread_pct=spread_pct,
            depth_imbalance=imbalance,
            estimated_slippage_1k=slippage_1k,
            estimated_slippage_10k=slippage_10k,
            liquidity_score=score,
        )

    def _estimate_slippage(
        self, order_book: OrderBook, size: Decimal, side: str
    ) -> float:
        """Estimate slippage for a given order size."""
        levels = order_book.asks if side == "buy" else order_book.bids
        if not levels:
            return 1.0  # 100% slippage (no liquidity)

        mid = order_book.mid_price or levels[0].price
        remaining = size
        total_cost = Decimal(0)

        for level in levels:
            if remaining <= 0:
                break
            fill = min(remaining, level.size)
            total_cost += fill * level.price
            remaining -= fill

        if remaining > 0:
            # Not enough liquidity
            return 1.0

        avg_price = total_cost / size
        slippage = abs(float((avg_price - mid) / mid)) if mid > 0 else 0
        return slippage

    def _calculate_liquidity_score(
        self,
        total_liquidity: Decimal,
        spread_pct: float,
        depth: Decimal,
    ) -> float:
        """Calculate a 0-100 liquidity score."""
        # Factors: total liquidity, spread, depth
        liquidity_factor = min(50, float(total_liquidity) / 10000 * 50)
        spread_factor = max(0, 25 - spread_pct * 500)  # Penalize wide spreads
        depth_factor = min(25, float(depth) / 5000 * 25)

        return liquidity_factor + spread_factor + depth_factor

    async def recommend_size(
        self,
        market: Market,
        desired_size: Decimal,
        side: str = "buy",
    ) -> SizeRecommendation:
        """Get size recommendation for a market.

        Args:
            market: Market to trade
            desired_size: Desired position size in dollars
            side: "buy" or "sell"
        """
        if not market.outcomes:
            raise ValueError("Market has no outcomes")

        token_id = market.outcomes[0].token_id
        order_book = await self._client.get_order_book(token_id)
        levels = order_book.asks if side == "buy" else order_book.bids

        if not levels:
            return SizeRecommendation(
                max_size_low_impact=Decimal(0),
                max_size_medium_impact=Decimal(0),
                recommended_size=Decimal(0),
                expected_slippage=1.0,
                effective_price=Decimal(0),
                warning="No liquidity available",
            )

        mid = order_book.mid_price or levels[0].price

        # Find max sizes for different impact thresholds
        max_low = self._find_max_size_for_impact(order_book, 0.01, side)
        max_medium = self._find_max_size_for_impact(order_book, 0.05, side)

        # Calculate slippage for desired size
        slippage = self._estimate_slippage(order_book, desired_size, side)
        effective_price = mid * Decimal(1 + slippage if side == "buy" else 1 - slippage)

        # Determine recommended size
        warning = None
        if desired_size > max_medium:
            recommended = max_medium
            warning = f"Reduced from ${desired_size} to ${max_medium} due to liquidity"
        elif desired_size > max_low:
            recommended = desired_size
            warning = f"Size exceeds low-impact threshold (${max_low})"
        else:
            recommended = desired_size

        return SizeRecommendation(
            max_size_low_impact=max_low,
            max_size_medium_impact=max_medium,
            recommended_size=recommended,
            expected_slippage=slippage,
            effective_price=effective_price,
            warning=warning,
        )

    def _find_max_size_for_impact(
        self,
        order_book: OrderBook,
        max_impact: float,
        side: str,
    ) -> Decimal:
        """Find maximum size that stays within impact threshold."""
        levels = order_book.asks if side == "buy" else order_book.bids
        if not levels:
            return Decimal(0)

        mid = order_book.mid_price or levels[0].price
        target_price = mid * Decimal(1 + max_impact if side == "buy" else 1 - max_impact)

        total_size = Decimal(0)
        for level in levels:
            if side == "buy" and level.price > target_price:
                break
            if side == "sell" and level.price < target_price:
                break
            total_size += level.size * level.price  # Convert to dollar value

        return total_size

    async def find_liquid_markets(
        self,
        min_liquidity: Decimal = Decimal("10000"),
        max_spread: float = 0.05,
        limit: int = 50,
    ) -> list[LiquidityProfile]:
        """Find markets meeting liquidity criteria.

        These are efficient markets where you can size positions.
        """
        markets = await self._client.get_markets(limit=200, active=True)

        profiles = []
        for market in markets:
            if market.liquidity < min_liquidity:
                continue

            try:
                profile = await self.get_liquidity_profile(market)
                if profile.spread_pct <= max_spread:
                    profiles.append(profile)
            except Exception:
                continue

            if len(profiles) >= limit:
                break

        profiles.sort(key=lambda p: p.liquidity_score, reverse=True)
        return profiles

    async def find_inefficient_markets(
        self,
        max_liquidity: Decimal = Decimal("10000"),
        min_volume: Decimal = Decimal("1000"),
        limit: int = 50,
    ) -> list[LiquidityProfile]:
        """Find low-liquidity markets that may have more edge.

        These are niche markets where efficiency is lower.
        """
        markets = await self._client.get_markets(limit=500, active=True)

        profiles = []
        for market in markets:
            if market.liquidity > max_liquidity:
                continue
            if market.volume < min_volume:
                continue

            try:
                profile = await self.get_liquidity_profile(market)
                profiles.append(profile)
            except Exception:
                continue

            if len(profiles) >= limit:
                break

        # Sort by volume (more volume = more interest = potential edge)
        profiles.sort(key=lambda p: p.market.volume, reverse=True)
        return profiles

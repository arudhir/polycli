"""Historical odds tracking.

Download and analyze past price movements to identify patterns
in how markets react to news.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import numpy as np

from polycli.api.polymarket import PolymarketClient


@dataclass
class PricePoint:
    """A single price point in history."""

    timestamp: datetime
    price: Decimal
    volume: Optional[Decimal] = None


@dataclass
class PriceMovement:
    """A significant price movement."""

    start_time: datetime
    end_time: datetime
    start_price: Decimal
    end_price: Decimal
    change_pct: float
    duration_hours: float
    volume_during: Optional[Decimal] = None


@dataclass
class PatternMatch:
    """A detected pattern in price history."""

    pattern_name: str
    confidence: float
    description: str
    historical_outcomes: list[str]
    suggested_action: str


class HistoricalOddsTracker:
    """Track and analyze historical odds movements."""

    def __init__(self, client: PolymarketClient):
        """Initialize historical odds tracker.

        Args:
            client: Polymarket API client
        """
        self._client = client
        self._cache: dict[str, list[PricePoint]] = {}

    async def fetch_history(
        self,
        token_id: str,
        interval: str = "1h",
        limit: int = 500,
    ) -> list[PricePoint]:
        """Fetch price history for a token.

        Args:
            token_id: Token to fetch history for
            interval: Time interval (1m, 5m, 1h, 1d)
            limit: Number of data points
        """
        history = await self._client.get_price_history(token_id, interval, limit)

        points = []
        for item in history:
            points.append(
                PricePoint(
                    timestamp=datetime.fromisoformat(item.get("t", "").replace("Z", "+00:00"))
                    if item.get("t")
                    else datetime.utcnow(),
                    price=Decimal(str(item.get("p", 0))),
                    volume=Decimal(str(item.get("v", 0))) if item.get("v") else None,
                )
            )

        # Sort by timestamp
        points.sort(key=lambda p: p.timestamp)

        # Cache for later analysis
        self._cache[token_id] = points

        return points

    def find_significant_moves(
        self,
        history: list[PricePoint],
        min_change_pct: float = 0.10,
        max_duration_hours: float = 24,
    ) -> list[PriceMovement]:
        """Find significant price movements in history.

        Args:
            history: Price history to analyze
            min_change_pct: Minimum % change to consider significant
            max_duration_hours: Maximum duration for a "move"
        """
        if len(history) < 2:
            return []

        movements = []

        for i, start in enumerate(history):
            for j in range(i + 1, len(history)):
                end = history[j]
                duration = (end.timestamp - start.timestamp).total_seconds() / 3600

                if duration > max_duration_hours:
                    break

                if start.price == 0:
                    continue

                change_pct = float((end.price - start.price) / start.price)

                if abs(change_pct) >= min_change_pct:
                    # Calculate volume during period
                    volume = sum(
                        p.volume or Decimal(0)
                        for p in history[i : j + 1]
                    )

                    movements.append(
                        PriceMovement(
                            start_time=start.timestamp,
                            end_time=end.timestamp,
                            start_price=start.price,
                            end_price=end.price,
                            change_pct=change_pct,
                            duration_hours=duration,
                            volume_during=volume,
                        )
                    )

        # Sort by change magnitude
        movements.sort(key=lambda m: abs(m.change_pct), reverse=True)

        # Remove overlapping movements (keep largest)
        filtered = []
        for move in movements:
            overlaps = False
            for existing in filtered:
                if (
                    move.start_time <= existing.end_time
                    and move.end_time >= existing.start_time
                ):
                    overlaps = True
                    break
            if not overlaps:
                filtered.append(move)

        return filtered[:20]  # Return top 20

    def detect_patterns(
        self, history: list[PricePoint]
    ) -> list[PatternMatch]:
        """Detect common patterns in price history.

        Args:
            history: Price history to analyze
        """
        patterns = []

        if len(history) < 10:
            return patterns

        prices = [float(p.price) for p in history]

        # Check for trending
        trend = self._detect_trend(prices)
        if trend:
            patterns.append(trend)

        # Check for mean reversion
        reversion = self._detect_mean_reversion(prices)
        if reversion:
            patterns.append(reversion)

        # Check for volatility spike
        volatility = self._detect_volatility_pattern(prices)
        if volatility:
            patterns.append(volatility)

        # Check for consolidation
        consolidation = self._detect_consolidation(prices)
        if consolidation:
            patterns.append(consolidation)

        return patterns

    def _detect_trend(self, prices: list[float]) -> Optional[PatternMatch]:
        """Detect trending pattern."""
        if len(prices) < 5:
            return None

        # Simple linear regression
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)

        # Normalize slope
        avg_price = np.mean(prices)
        normalized_slope = slope / avg_price if avg_price > 0 else 0

        if normalized_slope > 0.01:
            return PatternMatch(
                pattern_name="uptrend",
                confidence=min(0.9, abs(normalized_slope) * 10),
                description=f"Price trending up ({normalized_slope:.2%} per period)",
                historical_outcomes=[
                    "Uptrends often continue until news event",
                    "May indicate accumulation by informed traders",
                ],
                suggested_action="Consider buying on pullbacks if thesis supports",
            )
        elif normalized_slope < -0.01:
            return PatternMatch(
                pattern_name="downtrend",
                confidence=min(0.9, abs(normalized_slope) * 10),
                description=f"Price trending down ({normalized_slope:.2%} per period)",
                historical_outcomes=[
                    "Downtrends may indicate negative information flow",
                    "Could be profit-taking or distribution",
                ],
                suggested_action="Wait for stabilization before buying",
            )

        return None

    def _detect_mean_reversion(
        self, prices: list[float]
    ) -> Optional[PatternMatch]:
        """Detect mean reversion opportunity."""
        if len(prices) < 20:
            return None

        mean = np.mean(prices)
        std = np.std(prices)
        current = prices[-1]

        if std == 0:
            return None

        z_score = (current - mean) / std

        if z_score > 2:
            return PatternMatch(
                pattern_name="overbought",
                confidence=min(0.8, abs(z_score) / 4),
                description=f"Price {z_score:.1f} std devs above mean",
                historical_outcomes=[
                    "Extreme readings often revert to mean",
                    "But can stay extreme during news events",
                ],
                suggested_action="Consider selling if no fundamental catalyst",
            )
        elif z_score < -2:
            return PatternMatch(
                pattern_name="oversold",
                confidence=min(0.8, abs(z_score) / 4),
                description=f"Price {abs(z_score):.1f} std devs below mean",
                historical_outcomes=[
                    "May indicate panic selling",
                    "Could be buying opportunity if thesis intact",
                ],
                suggested_action="Consider buying if fundamental thesis unchanged",
            )

        return None

    def _detect_volatility_pattern(
        self, prices: list[float]
    ) -> Optional[PatternMatch]:
        """Detect volatility patterns."""
        if len(prices) < 20:
            return None

        # Calculate rolling volatility
        returns = np.diff(prices) / prices[:-1]
        recent_vol = np.std(returns[-10:]) if len(returns) >= 10 else 0
        historical_vol = np.std(returns) if len(returns) > 0 else 0

        if historical_vol == 0:
            return None

        vol_ratio = recent_vol / historical_vol

        if vol_ratio > 2:
            return PatternMatch(
                pattern_name="volatility_spike",
                confidence=min(0.85, vol_ratio / 4),
                description=f"Recent volatility {vol_ratio:.1f}x historical average",
                historical_outcomes=[
                    "High volatility often precedes resolution",
                    "May indicate new information entering market",
                ],
                suggested_action="Be cautious with size, use limit orders",
            )
        elif vol_ratio < 0.5:
            return PatternMatch(
                pattern_name="low_volatility",
                confidence=0.6,
                description=f"Recent volatility only {vol_ratio:.1f}x historical",
                historical_outcomes=[
                    "Low volatility periods often precede large moves",
                    "Market may be waiting for catalyst",
                ],
                suggested_action="Consider positioning before volatility returns",
            )

        return None

    def _detect_consolidation(
        self, prices: list[float]
    ) -> Optional[PatternMatch]:
        """Detect consolidation pattern."""
        if len(prices) < 10:
            return None

        recent = prices[-10:]
        price_range = max(recent) - min(recent)
        avg = np.mean(recent)

        if avg == 0:
            return None

        range_pct = price_range / avg

        if range_pct < 0.05:
            return PatternMatch(
                pattern_name="consolidation",
                confidence=0.7,
                description=f"Price range only {range_pct:.1%} recently",
                historical_outcomes=[
                    "Tight consolidation often breaks with significant move",
                    "Direction of break usually follows fundamentals",
                ],
                suggested_action="Wait for breakout or position small for both sides",
            )

        return None

    def analyze_news_reaction(
        self,
        history: list[PricePoint],
        event_time: datetime,
        window_hours: int = 4,
    ) -> dict:
        """Analyze how price reacted around a news event.

        Args:
            history: Price history
            event_time: When the news occurred
            window_hours: Hours before/after to analyze
        """
        # Find prices around event
        before_prices = []
        after_prices = []

        for point in history:
            hours_from_event = (point.timestamp - event_time).total_seconds() / 3600

            if -window_hours <= hours_from_event < 0:
                before_prices.append(point)
            elif 0 <= hours_from_event <= window_hours:
                after_prices.append(point)

        if not before_prices or not after_prices:
            return {"error": "Insufficient data around event"}

        pre_event_price = before_prices[-1].price
        post_event_price = after_prices[-1].price if after_prices else pre_event_price
        immediate_reaction = after_prices[0].price if after_prices else pre_event_price

        return {
            "event_time": event_time,
            "pre_event_price": pre_event_price,
            "immediate_reaction": immediate_reaction,
            "post_window_price": post_event_price,
            "immediate_change_pct": float(
                (immediate_reaction - pre_event_price) / pre_event_price
            )
            if pre_event_price > 0
            else 0,
            "total_change_pct": float(
                (post_event_price - pre_event_price) / pre_event_price
            )
            if pre_event_price > 0
            else 0,
            "reaction_type": self._categorize_reaction(
                pre_event_price, immediate_reaction, post_event_price
            ),
        }

    def _categorize_reaction(
        self,
        pre: Decimal,
        immediate: Decimal,
        final: Decimal,
    ) -> str:
        """Categorize the type of news reaction."""
        if pre == 0:
            return "unknown"

        immediate_change = (immediate - pre) / pre
        final_change = (final - pre) / pre

        if abs(immediate_change) < Decimal("0.02"):
            return "no_reaction"

        if immediate_change > 0 and final_change > 0:
            if final_change > immediate_change:
                return "rally_continuation"
            else:
                return "rally_fade"
        elif immediate_change < 0 and final_change < 0:
            if final_change < immediate_change:
                return "selloff_continuation"
            else:
                return "selloff_fade"
        elif immediate_change > 0 and final_change < 0:
            return "bull_trap"
        elif immediate_change < 0 and final_change > 0:
            return "bear_trap"

        return "mixed"

"""Monitor volume spikes on niche markets.

Unusual volume on low-liquidity markets often signals insider
activity 2-4 hours before news breaks.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from polycli.api.polymarket import PolymarketClient
from polycli.models import Market


@dataclass
class VolumeSpike:
    """Represents a detected volume spike."""

    market: Market
    current_volume: Decimal
    baseline_volume: Decimal
    spike_ratio: float
    detected_at: datetime
    liquidity: Decimal


class VolumeMonitor:
    """Monitor markets for unusual volume activity."""

    def __init__(
        self,
        client: PolymarketClient,
        spike_threshold: float = 3.0,
        min_volume_increase: Decimal = Decimal("1000"),
        max_liquidity: Optional[Decimal] = None,
    ):
        """Initialize volume monitor.

        Args:
            client: Polymarket API client
            spike_threshold: Multiple of baseline volume to trigger alert (default 3x)
            min_volume_increase: Minimum absolute volume increase to consider
            max_liquidity: Only monitor markets below this liquidity (niche markets)
        """
        self._client = client
        self._spike_threshold = spike_threshold
        self._min_volume_increase = min_volume_increase
        self._max_liquidity = max_liquidity or Decimal("50000")

        # Store baseline volumes: {condition_id: {"volume": Decimal, "timestamp": datetime}}
        self._baselines: dict[str, dict] = {}

    async def update_baselines(self, markets: Optional[list[Market]] = None) -> int:
        """Update baseline volumes for markets.

        Returns number of markets updated.
        """
        if markets is None:
            markets = await self._client.get_markets(limit=500, active=True)

        count = 0
        now = datetime.utcnow()

        for market in markets:
            if market.liquidity <= self._max_liquidity:
                self._baselines[market.condition_id] = {
                    "volume": market.volume,
                    "timestamp": now,
                }
                count += 1

        return count

    async def detect_spikes(
        self, markets: Optional[list[Market]] = None
    ) -> list[VolumeSpike]:
        """Detect volume spikes compared to baselines.

        Returns list of markets with unusual volume.
        """
        if markets is None:
            markets = await self._client.get_markets(limit=500, active=True)

        spikes = []
        now = datetime.utcnow()

        for market in markets:
            # Skip high-liquidity markets (not niche)
            if market.liquidity > self._max_liquidity:
                continue

            baseline = self._baselines.get(market.condition_id)
            if not baseline:
                continue

            baseline_volume = baseline["volume"]
            volume_increase = market.volume - baseline_volume

            # Check if spike conditions are met
            if volume_increase < self._min_volume_increase:
                continue

            if baseline_volume > 0:
                spike_ratio = float(market.volume / baseline_volume)
            else:
                spike_ratio = float("inf") if volume_increase > 0 else 1.0

            if spike_ratio >= self._spike_threshold:
                spikes.append(
                    VolumeSpike(
                        market=market,
                        current_volume=market.volume,
                        baseline_volume=baseline_volume,
                        spike_ratio=spike_ratio,
                        detected_at=now,
                        liquidity=market.liquidity,
                    )
                )

        # Sort by spike ratio (most unusual first)
        spikes.sort(key=lambda s: s.spike_ratio, reverse=True)
        return spikes

    async def get_low_liquidity_markets(
        self, max_liquidity: Optional[Decimal] = None
    ) -> list[Market]:
        """Get all markets below liquidity threshold."""
        threshold = max_liquidity or self._max_liquidity
        markets = await self._client.get_markets(limit=500, active=True)
        return [m for m in markets if m.liquidity <= threshold]

    async def monitor_market(
        self,
        condition_id: str,
        check_interval_hours: float = 1.0,
    ) -> Optional[VolumeSpike]:
        """Check a specific market for volume anomalies.

        Compares current volume to baseline, updates baseline if old.
        """
        market = await self._client.get_market(condition_id)
        if not market:
            return None

        baseline = self._baselines.get(condition_id)

        # If no baseline or baseline is stale, update and return None
        if not baseline:
            self._baselines[condition_id] = {
                "volume": market.volume,
                "timestamp": datetime.utcnow(),
            }
            return None

        baseline_age = datetime.utcnow() - baseline["timestamp"]
        if baseline_age > timedelta(hours=check_interval_hours * 24):
            self._baselines[condition_id] = {
                "volume": market.volume,
                "timestamp": datetime.utcnow(),
            }
            return None

        # Check for spike
        volume_increase = market.volume - baseline["volume"]
        if volume_increase < self._min_volume_increase:
            return None

        spike_ratio = float(market.volume / baseline["volume"]) if baseline["volume"] > 0 else 0

        if spike_ratio >= self._spike_threshold:
            return VolumeSpike(
                market=market,
                current_volume=market.volume,
                baseline_volume=baseline["volume"],
                spike_ratio=spike_ratio,
                detected_at=datetime.utcnow(),
                liquidity=market.liquidity,
            )

        return None

    def get_baseline(self, condition_id: str) -> Optional[dict]:
        """Get stored baseline for a market."""
        return self._baselines.get(condition_id)

    def clear_baselines(self) -> None:
        """Clear all stored baselines."""
        self._baselines.clear()

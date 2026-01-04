"""Learn from forensic analysis.

When markets move unexpectedly, investigate why - who knew what,
when did they know it?
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from polycli.api.polymarket import PolymarketClient


@dataclass
class PriceMovement:
    """A significant price movement to investigate."""

    market_id: str
    market_question: str
    start_time: datetime
    end_time: datetime
    start_price: Decimal
    end_price: Decimal
    change_pct: float
    volume_during: Decimal


@dataclass
class TradeCluster:
    """A cluster of trades that may indicate informed trading."""

    start_time: datetime
    end_time: datetime
    num_trades: int
    total_volume: Decimal
    direction: str  # "buy" or "sell"
    avg_price: Decimal
    unique_traders: int


@dataclass
class ForensicReport:
    """Report from forensic analysis of a market event."""

    market_id: str
    market_question: str
    event_description: str
    price_movement: PriceMovement
    pre_event_activity: list[TradeCluster]
    notable_trades: list[dict]
    likely_informed_traders: list[str]
    timeline: list[dict]
    conclusions: list[str]
    lessons: list[str]


class ForensicAnalyzer:
    """Analyze market movements to understand what happened."""

    def __init__(self, client: PolymarketClient):
        """Initialize forensic analyzer.

        Args:
            client: Polymarket API client
        """
        self._client = client

    async def investigate_movement(
        self,
        market_id: str,
        token_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> ForensicReport:
        """Investigate a significant price movement.

        Args:
            market_id: Market that moved
            token_id: Token that moved
            start_time: When movement started
            end_time: When movement ended
        """
        # Get market info
        market = await self._client.get_market(market_id)
        market_question = market.question if market else "Unknown"

        # Get price history
        price_history = await self._client.get_price_history(token_id, "1m", 1000)

        # Calculate price movement
        movement = self._calculate_movement(
            price_history, start_time, end_time, market_id, market_question
        )

        # Get trades during period
        trades = await self._client.get_trades(token_id=token_id, limit=500)

        # Analyze pre-event activity
        pre_event_start = start_time - timedelta(hours=4)
        pre_event_trades = self._filter_trades_by_time(trades, pre_event_start, start_time)
        pre_event_clusters = self._find_trade_clusters(pre_event_trades)

        # Find notable trades
        notable = self._find_notable_trades(trades, start_time, end_time)

        # Identify potentially informed traders
        informed = self._identify_informed_traders(pre_event_trades, movement)

        # Build timeline
        timeline = self._build_timeline(trades, price_history, start_time, end_time)

        # Generate conclusions
        conclusions = self._generate_conclusions(
            movement, pre_event_clusters, notable, informed
        )

        # Generate lessons
        lessons = self._generate_lessons(conclusions)

        return ForensicReport(
            market_id=market_id,
            market_question=market_question,
            event_description=f"Price moved {movement.change_pct:.1%} in {(end_time - start_time).total_seconds() / 60:.0f} minutes",
            price_movement=movement,
            pre_event_activity=pre_event_clusters,
            notable_trades=notable,
            likely_informed_traders=informed,
            timeline=timeline,
            conclusions=conclusions,
            lessons=lessons,
        )

    def _calculate_movement(
        self,
        price_history: list[dict],
        start_time: datetime,
        end_time: datetime,
        market_id: str,
        market_question: str,
    ) -> PriceMovement:
        """Calculate price movement metrics."""
        # Filter to relevant period
        relevant = [
            p for p in price_history
            if start_time <= datetime.fromisoformat(p.get("t", "").replace("Z", "+00:00")) <= end_time
        ]

        if not relevant:
            return PriceMovement(
                market_id=market_id,
                market_question=market_question,
                start_time=start_time,
                end_time=end_time,
                start_price=Decimal(0),
                end_price=Decimal(0),
                change_pct=0,
                volume_during=Decimal(0),
            )

        start_price = Decimal(str(relevant[0].get("p", 0)))
        end_price = Decimal(str(relevant[-1].get("p", 0)))
        change_pct = float((end_price - start_price) / start_price) if start_price > 0 else 0
        volume = sum(Decimal(str(p.get("v", 0))) for p in relevant)

        return PriceMovement(
            market_id=market_id,
            market_question=market_question,
            start_time=start_time,
            end_time=end_time,
            start_price=start_price,
            end_price=end_price,
            change_pct=change_pct,
            volume_during=volume,
        )

    def _filter_trades_by_time(
        self,
        trades: list[dict],
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        """Filter trades to a time window."""
        filtered = []
        for trade in trades:
            trade_time = trade.get("timestamp")
            if isinstance(trade_time, str):
                trade_time = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
            elif isinstance(trade_time, (int, float)):
                trade_time = datetime.fromtimestamp(trade_time)
            else:
                continue

            if start <= trade_time <= end:
                filtered.append(trade)

        return filtered

    def _find_trade_clusters(self, trades: list[dict]) -> list[TradeCluster]:
        """Find clusters of related trading activity."""
        if not trades:
            return []

        # Group trades by 15-minute windows
        clusters = []
        current_cluster: list[dict] = []
        cluster_start = None

        for trade in sorted(trades, key=lambda t: t.get("timestamp", 0)):
            trade_time = trade.get("timestamp")
            if isinstance(trade_time, str):
                trade_time = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
            elif isinstance(trade_time, (int, float)):
                trade_time = datetime.fromtimestamp(trade_time)
            else:
                continue

            if cluster_start is None:
                cluster_start = trade_time
                current_cluster = [trade]
            elif (trade_time - cluster_start).total_seconds() <= 900:  # 15 minutes
                current_cluster.append(trade)
            else:
                if len(current_cluster) >= 3:
                    clusters.append(self._summarize_cluster(current_cluster, cluster_start))
                cluster_start = trade_time
                current_cluster = [trade]

        if len(current_cluster) >= 3 and cluster_start:
            clusters.append(self._summarize_cluster(current_cluster, cluster_start))

        return clusters

    def _summarize_cluster(
        self, trades: list[dict], start_time: datetime
    ) -> TradeCluster:
        """Summarize a cluster of trades."""
        total_volume = sum(Decimal(str(t.get("size", 0))) for t in trades)
        avg_price = sum(Decimal(str(t.get("price", 0))) for t in trades) / len(trades)
        unique_traders = len(set(t.get("maker", "") for t in trades))

        # Determine direction
        buys = sum(1 for t in trades if t.get("side", "").lower() == "buy")
        direction = "buy" if buys > len(trades) / 2 else "sell"

        return TradeCluster(
            start_time=start_time,
            end_time=start_time + timedelta(minutes=15),
            num_trades=len(trades),
            total_volume=total_volume,
            direction=direction,
            avg_price=avg_price,
            unique_traders=unique_traders,
        )

    def _find_notable_trades(
        self,
        trades: list[dict],
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        """Find notably large or well-timed trades."""
        relevant = self._filter_trades_by_time(trades, start, end)
        if not relevant:
            return []

        # Calculate average size
        sizes = [float(t.get("size", 0)) for t in relevant]
        avg_size = sum(sizes) / len(sizes) if sizes else 0

        # Find trades > 3x average
        notable = []
        for trade in relevant:
            size = float(trade.get("size", 0))
            if size > avg_size * 3:
                notable.append({
                    "trader": trade.get("maker", "unknown"),
                    "size": size,
                    "price": trade.get("price"),
                    "side": trade.get("side"),
                    "relative_size": size / avg_size if avg_size > 0 else 0,
                    "timestamp": trade.get("timestamp"),
                })

        return sorted(notable, key=lambda x: x["size"], reverse=True)[:10]

    def _identify_informed_traders(
        self,
        pre_event_trades: list[dict],
        movement: PriceMovement,
    ) -> list[str]:
        """Identify traders who appear to have been informed."""
        if not pre_event_trades:
            return []

        # Group by trader
        trader_activity: dict[str, dict] = {}
        for trade in pre_event_trades:
            trader = trade.get("maker", "unknown")
            if trader not in trader_activity:
                trader_activity[trader] = {"buys": 0, "sells": 0, "volume": Decimal(0)}

            side = trade.get("side", "").lower()
            size = Decimal(str(trade.get("size", 0)))

            if side == "buy":
                trader_activity[trader]["buys"] += 1
            else:
                trader_activity[trader]["sells"] += 1
            trader_activity[trader]["volume"] += size

        # Find traders whose direction matched the eventual movement
        informed = []
        price_went_up = movement.change_pct > 0

        for trader, activity in trader_activity.items():
            was_buying = activity["buys"] > activity["sells"]

            # Trader was right
            if (price_went_up and was_buying) or (not price_went_up and not was_buying):
                if activity["volume"] > Decimal("1000"):  # Significant volume
                    informed.append(trader)

        return informed[:10]

    def _build_timeline(
        self,
        trades: list[dict],
        price_history: list[dict],
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        """Build a timeline of events."""
        timeline = []

        # Add price points
        for point in price_history:
            time_str = point.get("t", "")
            if time_str:
                t = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                if start <= t <= end:
                    timeline.append({
                        "time": t.isoformat(),
                        "type": "price",
                        "price": point.get("p"),
                    })

        # Add notable trades
        relevant_trades = self._filter_trades_by_time(trades, start, end)
        sizes = [float(t.get("size", 0)) for t in relevant_trades]
        threshold = (sum(sizes) / len(sizes)) * 2 if sizes else 0

        for trade in relevant_trades:
            if float(trade.get("size", 0)) > threshold:
                timeline.append({
                    "time": trade.get("timestamp"),
                    "type": "large_trade",
                    "size": trade.get("size"),
                    "side": trade.get("side"),
                    "trader": trade.get("maker"),
                })

        # Sort by time
        timeline.sort(key=lambda x: x.get("time", ""))
        return timeline

    def _generate_conclusions(
        self,
        movement: PriceMovement,
        clusters: list[TradeCluster],
        notable: list[dict],
        informed: list[str],
    ) -> list[str]:
        """Generate conclusions from analysis."""
        conclusions = []

        if movement.change_pct > 0.2 or movement.change_pct < -0.2:
            conclusions.append(f"Significant move of {movement.change_pct:.0%}")

        if clusters:
            pre_cluster_volume = sum(c.total_volume for c in clusters)
            conclusions.append(
                f"Found {len(clusters)} trade clusters before the move "
                f"(${pre_cluster_volume:.0f} volume)"
            )

        if informed:
            conclusions.append(
                f"{len(informed)} traders appear to have positioned correctly before the move"
            )

        if notable:
            conclusions.append(
                f"{len(notable)} notably large trades during the movement"
            )

        return conclusions

    def _generate_lessons(self, conclusions: list[str]) -> list[str]:
        """Generate actionable lessons from conclusions."""
        lessons = []

        lessons.append("Monitor trade flow for unusual pre-announcement activity")
        lessons.append("Large traders often know before public announcements")
        lessons.append("Set up alerts for volume spikes in your watched markets")
        lessons.append("Review who was right and track their future trades")

        return lessons

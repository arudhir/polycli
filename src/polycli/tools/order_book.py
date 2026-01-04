"""Scrape order book depth.

Thin order books signal opportunities to accumulate without
moving price too much.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from polycli.api.polymarket import PolymarketClient
from polycli.models import OrderBook


@dataclass
class OrderBookSnapshot:
    """Snapshot of order book state."""

    token_id: str
    timestamp: datetime
    best_bid: Decimal
    best_ask: Decimal
    spread: Decimal
    spread_pct: float
    bid_depth_1pct: Decimal
    ask_depth_1pct: Decimal
    bid_depth_5pct: Decimal
    ask_depth_5pct: Decimal
    total_bid_liquidity: Decimal
    total_ask_liquidity: Decimal
    imbalance: float  # Positive = more bids


@dataclass
class AccumulationOpportunity:
    """An opportunity to accumulate at a good price."""

    token_id: str
    side: str  # "buy" or "sell"
    size_available: Decimal
    avg_price: Decimal
    max_price_impact: float
    levels_to_fill: int
    notes: list[str]


class OrderBookAnalyzer:
    """Analyze order book depth for trading opportunities."""

    def __init__(self, client: PolymarketClient):
        """Initialize order book analyzer.

        Args:
            client: Polymarket API client
        """
        self._client = client
        self._snapshots: dict[str, list[OrderBookSnapshot]] = {}

    async def get_snapshot(self, token_id: str) -> OrderBookSnapshot:
        """Get current order book snapshot.

        Args:
            token_id: Token to analyze
        """
        order_book = await self._client.get_order_book(token_id)
        return self._analyze_order_book(order_book)

    def _analyze_order_book(self, book: OrderBook) -> OrderBookSnapshot:
        """Analyze order book and create snapshot."""
        best_bid = book.bids[0].price if book.bids else Decimal(0)
        best_ask = book.asks[0].price if book.asks else Decimal(1)
        spread = best_ask - best_bid
        mid = (best_ask + best_bid) / 2 if best_bid > 0 else best_ask
        spread_pct = float(spread / mid) if mid > 0 else 0

        # Calculate depth at various levels
        bid_depth_1pct = self._depth_within_pct(book, "bid", Decimal("0.01"))
        ask_depth_1pct = self._depth_within_pct(book, "ask", Decimal("0.01"))
        bid_depth_5pct = self._depth_within_pct(book, "bid", Decimal("0.05"))
        ask_depth_5pct = self._depth_within_pct(book, "ask", Decimal("0.05"))

        total_bids = sum(level.size for level in book.bids)
        total_asks = sum(level.size for level in book.asks)
        imbalance = float((total_bids - total_asks) / (total_bids + total_asks)) if (total_bids + total_asks) > 0 else 0

        snapshot = OrderBookSnapshot(
            token_id=book.token_id,
            timestamp=book.timestamp,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            spread_pct=spread_pct,
            bid_depth_1pct=bid_depth_1pct,
            ask_depth_1pct=ask_depth_1pct,
            bid_depth_5pct=bid_depth_5pct,
            ask_depth_5pct=ask_depth_5pct,
            total_bid_liquidity=total_bids,
            total_ask_liquidity=total_asks,
            imbalance=imbalance,
        )

        # Store snapshot history
        if book.token_id not in self._snapshots:
            self._snapshots[book.token_id] = []
        self._snapshots[book.token_id].append(snapshot)

        # Keep only last 100 snapshots
        if len(self._snapshots[book.token_id]) > 100:
            self._snapshots[book.token_id] = self._snapshots[book.token_id][-100:]

        return snapshot

    def _depth_within_pct(
        self, book: OrderBook, side: str, pct: Decimal
    ) -> Decimal:
        """Calculate total size available within percentage of mid."""
        mid = book.mid_price
        if not mid:
            return Decimal(0)

        levels = book.bids if side == "bid" else book.asks
        total = Decimal(0)

        for level in levels:
            if side == "bid":
                if level.price >= mid * (1 - pct):
                    total += level.size
            else:
                if level.price <= mid * (1 + pct):
                    total += level.size

        return total

    async def find_accumulation_opportunity(
        self,
        token_id: str,
        desired_size: Decimal,
        max_price_impact: float = 0.02,
    ) -> Optional[AccumulationOpportunity]:
        """Find opportunity to accumulate size with limited impact.

        Args:
            token_id: Token to accumulate
            desired_size: Size you want to buy
            max_price_impact: Maximum acceptable price impact
        """
        order_book = await self._client.get_order_book(token_id)

        if not order_book.asks:
            return None

        mid = order_book.mid_price or order_book.asks[0].price
        max_price = mid * (1 + Decimal(str(max_price_impact)))

        # Calculate how much we can get within impact limit
        total_size = Decimal(0)
        total_cost = Decimal(0)
        levels_filled = 0
        notes = []

        for level in order_book.asks:
            if level.price > max_price:
                break

            fill_size = min(level.size, desired_size - total_size)
            total_size += fill_size
            total_cost += fill_size * level.price
            levels_filled += 1

            if total_size >= desired_size:
                break

        if total_size == 0:
            return None

        avg_price = total_cost / total_size
        actual_impact = float((avg_price - mid) / mid) if mid > 0 else 0

        if total_size < desired_size:
            notes.append(
                f"Only {total_size} available within {max_price_impact:.1%} impact "
                f"(wanted {desired_size})"
            )

        if levels_filled > 3:
            notes.append(f"Would need to fill {levels_filled} price levels")

        if order_book.spread and order_book.spread > mid * Decimal("0.03"):
            notes.append("Wide spread - consider using limit orders")

        return AccumulationOpportunity(
            token_id=token_id,
            side="buy",
            size_available=total_size,
            avg_price=avg_price,
            max_price_impact=actual_impact,
            levels_to_fill=levels_filled,
            notes=notes,
        )

    async def find_thin_books(
        self,
        token_ids: list[str],
        max_depth: Decimal = Decimal("5000"),
    ) -> list[tuple[str, OrderBookSnapshot]]:
        """Find markets with thin order books (potential opportunities).

        Args:
            token_ids: Tokens to check
            max_depth: Maximum depth to consider "thin"
        """
        thin_books = []

        for token_id in token_ids:
            try:
                snapshot = await self.get_snapshot(token_id)
                total_liquidity = snapshot.total_bid_liquidity + snapshot.total_ask_liquidity

                if total_liquidity < max_depth:
                    thin_books.append((token_id, snapshot))
            except Exception:
                continue

        # Sort by liquidity (thinnest first)
        thin_books.sort(
            key=lambda x: x[1].total_bid_liquidity + x[1].total_ask_liquidity
        )
        return thin_books

    def get_snapshot_history(
        self, token_id: str
    ) -> list[OrderBookSnapshot]:
        """Get historical snapshots for a token."""
        return self._snapshots.get(token_id, [])

    async def monitor_book_changes(
        self,
        token_id: str,
        threshold_pct: float = 0.1,
    ) -> Optional[dict]:
        """Monitor for significant order book changes.

        Args:
            token_id: Token to monitor
            threshold_pct: Minimum change to report
        """
        history = self._snapshots.get(token_id, [])
        if len(history) < 2:
            return None

        current = await self.get_snapshot(token_id)
        previous = history[-2]

        changes = {}

        # Check spread change
        if previous.spread > 0:
            spread_change = float((current.spread - previous.spread) / previous.spread)
            if abs(spread_change) > threshold_pct:
                changes["spread"] = {
                    "previous": previous.spread,
                    "current": current.spread,
                    "change_pct": spread_change,
                }

        # Check liquidity change
        prev_liquidity = previous.total_bid_liquidity + previous.total_ask_liquidity
        curr_liquidity = current.total_bid_liquidity + current.total_ask_liquidity

        if prev_liquidity > 0:
            liquidity_change = float((curr_liquidity - prev_liquidity) / prev_liquidity)
            if abs(liquidity_change) > threshold_pct:
                changes["liquidity"] = {
                    "previous": prev_liquidity,
                    "current": curr_liquidity,
                    "change_pct": liquidity_change,
                }

        # Check imbalance change
        imbalance_change = current.imbalance - previous.imbalance
        if abs(imbalance_change) > threshold_pct:
            changes["imbalance"] = {
                "previous": previous.imbalance,
                "current": current.imbalance,
                "change": imbalance_change,
            }

        return changes if changes else None

    def suggest_order_strategy(
        self, snapshot: OrderBookSnapshot, desired_size: Decimal
    ) -> dict:
        """Suggest order strategy based on current book state.

        Args:
            snapshot: Current order book snapshot
            desired_size: Size you want to trade
        """
        total_liquidity = snapshot.total_bid_liquidity + snapshot.total_ask_liquidity

        # Calculate what % of book this order represents
        order_pct = float(desired_size / total_liquidity) if total_liquidity > 0 else 1

        strategy = {
            "spread_pct": snapshot.spread_pct,
            "order_as_pct_of_book": order_pct,
            "recommendation": "",
            "suggested_approach": [],
        }

        if order_pct > 0.5:
            strategy["recommendation"] = "Order is very large relative to book"
            strategy["suggested_approach"] = [
                "Split into multiple smaller orders",
                "Use TWAP (time-weighted average) over several hours",
                "Consider using limit orders at multiple levels",
            ]
        elif order_pct > 0.2:
            strategy["recommendation"] = "Order is significant relative to book"
            strategy["suggested_approach"] = [
                "Use limit orders to avoid slippage",
                "Consider splitting into 2-3 orders",
                "Monitor for large orders on other side",
            ]
        elif snapshot.spread_pct > 0.03:
            strategy["recommendation"] = "Wide spread - use limit orders"
            strategy["suggested_approach"] = [
                "Place limit order at mid price",
                "Be patient - wait for fill",
                "Consider improving the bid",
            ]
        else:
            strategy["recommendation"] = "Normal conditions"
            strategy["suggested_approach"] = [
                "Limit order slightly inside spread is optimal",
                "Market order acceptable for urgency",
            ]

        return strategy

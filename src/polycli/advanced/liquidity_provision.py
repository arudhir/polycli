"""Liquidity provision for fees.

In some markets, collecting fees from spreads beats directional trading.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from polycli.api.polymarket import PolymarketClient
from polycli.models import OrderBook


@dataclass
class LPPosition:
    """A liquidity provision position."""

    market_id: str
    token_id: str
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal
    ask_size: Decimal
    spread: Decimal
    expected_fee_rate: float
    created_at: datetime


@dataclass
class LPOpportunity:
    """An opportunity to provide liquidity."""

    market_id: str
    token_id: str
    market_question: str
    current_spread: Decimal
    spread_pct: float
    suggested_bid: Decimal
    suggested_ask: Decimal
    suggested_size: Decimal
    estimated_daily_fees: Decimal
    estimated_daily_pnl: Decimal
    inventory_risk: str
    notes: list[str]


@dataclass
class LPPerformance:
    """Performance metrics for LP activity."""

    total_volume: Decimal
    fees_earned: Decimal
    inventory_pnl: Decimal
    net_pnl: Decimal
    trades_made: int
    fill_rate: float
    avg_spread_captured: float


class LiquidityProvider:
    """Manage liquidity provision strategies."""

    def __init__(
        self,
        client: PolymarketClient,
        min_spread: Decimal = Decimal("0.02"),
        max_inventory: Decimal = Decimal("5000"),
    ):
        """Initialize liquidity provider.

        Args:
            client: Polymarket API client
            min_spread: Minimum spread to provide at
            max_inventory: Maximum inventory to hold
        """
        self._client = client
        self._min_spread = min_spread
        self._max_inventory = max_inventory
        self._positions: dict[str, LPPosition] = {}
        self._inventory: dict[str, Decimal] = {}  # token_id -> size

    async def find_opportunities(
        self,
        min_volume: Decimal = Decimal("10000"),
        limit: int = 20,
    ) -> list[LPOpportunity]:
        """Find markets suitable for liquidity provision.

        Args:
            min_volume: Minimum daily volume requirement
            limit: Maximum opportunities to return
        """
        markets = await self._client.get_markets(limit=200, active=True)
        opportunities = []

        for market in markets:
            if market.volume < min_volume:
                continue

            if not market.outcomes:
                continue

            token_id = market.outcomes[0].token_id

            try:
                book = await self._client.get_order_book(token_id)
                opp = self._analyze_lp_opportunity(market, book)
                if opp:
                    opportunities.append(opp)
            except Exception:
                continue

            if len(opportunities) >= limit:
                break

        # Sort by estimated daily PnL
        opportunities.sort(key=lambda o: o.estimated_daily_pnl, reverse=True)
        return opportunities

    def _analyze_lp_opportunity(
        self,
        market,
        book: OrderBook,
    ) -> Optional[LPOpportunity]:
        """Analyze a market for LP opportunity."""
        if not book.bids or not book.asks:
            return None

        spread = book.spread
        if spread is None or spread < self._min_spread:
            return None

        mid = book.mid_price or Decimal("0.5")
        spread_pct = float(spread / mid) if mid > 0 else 0

        # Calculate suggested quotes (improve by 0.01 inside spread)
        suggested_bid = book.bids[0].price + Decimal("0.01")
        suggested_ask = book.asks[0].price - Decimal("0.01")

        # Ensure we still capture minimum spread
        if suggested_ask - suggested_bid < self._min_spread:
            return None

        # Estimate daily fees based on volume
        # Assume we capture 10% of volume with our spread
        volume_capture_rate = Decimal("0.10")
        daily_volume = market.volume / Decimal(30)  # Rough daily estimate
        expected_volume = daily_volume * volume_capture_rate

        # Fee is half the spread on each side
        fee_per_unit = (suggested_ask - suggested_bid) / 2
        estimated_fees = expected_volume * fee_per_unit

        # Estimate inventory risk
        # Assume 50% of trades create inventory
        inventory_risk_multiplier = Decimal("0.5")
        expected_inventory = expected_volume * inventory_risk_multiplier
        inventory_risk = "low" if expected_inventory < Decimal("1000") else "medium" if expected_inventory < Decimal("5000") else "high"

        # Estimate PnL (fees minus expected inventory loss)
        # Assume 2% expected loss on inventory
        inventory_cost = expected_inventory * Decimal("0.02")
        estimated_pnl = estimated_fees - inventory_cost

        notes = []
        if spread_pct > 0.1:
            notes.append("Wide spread - good fee opportunity")
        if inventory_risk == "high":
            notes.append("High inventory risk - monitor closely")
        if market.liquidity < Decimal("5000"):
            notes.append("Low liquidity market - smaller size recommended")

        return LPOpportunity(
            market_id=market.condition_id,
            token_id=market.outcomes[0].token_id,
            market_question=market.question,
            current_spread=spread,
            spread_pct=spread_pct,
            suggested_bid=suggested_bid,
            suggested_ask=suggested_ask,
            suggested_size=min(Decimal("1000"), market.liquidity * Decimal("0.1")),
            estimated_daily_fees=estimated_fees,
            estimated_daily_pnl=estimated_pnl,
            inventory_risk=inventory_risk,
            notes=notes,
        )

    def create_position(
        self,
        market_id: str,
        token_id: str,
        bid_price: Decimal,
        ask_price: Decimal,
        size: Decimal,
    ) -> LPPosition:
        """Create an LP position (place bid and ask orders).

        Args:
            market_id: Market to provide liquidity in
            token_id: Token to quote
            bid_price: Price to bid
            ask_price: Price to ask
            size: Size on each side
        """
        spread = ask_price - bid_price

        position = LPPosition(
            market_id=market_id,
            token_id=token_id,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_size=size,
            ask_size=size,
            spread=spread,
            expected_fee_rate=float(spread / 2 / ((bid_price + ask_price) / 2)),
            created_at=datetime.utcnow(),
        )

        self._positions[f"{market_id}:{token_id}"] = position

        # In practice, you'd place actual orders here
        # self._client.place_limit_order(...)

        return position

    def update_quotes(
        self,
        position_key: str,
        new_bid: Decimal,
        new_ask: Decimal,
    ) -> Optional[LPPosition]:
        """Update quotes for an existing position.

        Args:
            position_key: Position identifier
            new_bid: New bid price
            new_ask: New ask price
        """
        position = self._positions.get(position_key)
        if not position:
            return None

        position.bid_price = new_bid
        position.ask_price = new_ask
        position.spread = new_ask - new_bid

        # In practice, cancel old orders and place new ones
        return position

    def handle_fill(
        self,
        token_id: str,
        side: str,
        size: Decimal,
        price: Decimal,
    ) -> dict:
        """Handle an order fill and update inventory.

        Args:
            token_id: Token that was filled
            side: "bid" or "ask"
            size: Size filled
            price: Fill price
        """
        current_inventory = self._inventory.get(token_id, Decimal(0))

        if side == "bid":
            # Bought tokens
            new_inventory = current_inventory + size
            cost = size * price
        else:
            # Sold tokens
            new_inventory = current_inventory - size
            cost = size * price

        self._inventory[token_id] = new_inventory

        return {
            "side": side,
            "size": size,
            "price": price,
            "previous_inventory": current_inventory,
            "new_inventory": new_inventory,
            "inventory_risk": (
                "high"
                if abs(new_inventory) > self._max_inventory
                else "medium"
                if abs(new_inventory) > self._max_inventory / 2
                else "low"
            ),
        }

    def get_inventory_status(self) -> dict[str, dict]:
        """Get current inventory status for all tokens."""
        return {
            token_id: {
                "size": size,
                "value": size * Decimal("0.5"),  # Rough estimate at mid
                "risk": (
                    "high"
                    if abs(size) > self._max_inventory
                    else "medium"
                    if abs(size) > self._max_inventory / 2
                    else "low"
                ),
            }
            for token_id, size in self._inventory.items()
        }

    def calculate_performance(
        self,
        fills: list[dict],
        current_prices: dict[str, Decimal],
    ) -> LPPerformance:
        """Calculate LP performance from fills.

        Args:
            fills: List of fill events
            current_prices: Current prices for PnL calculation
        """
        if not fills:
            return LPPerformance(
                total_volume=Decimal(0),
                fees_earned=Decimal(0),
                inventory_pnl=Decimal(0),
                net_pnl=Decimal(0),
                trades_made=0,
                fill_rate=0.0,
                avg_spread_captured=0.0,
            )

        total_volume = sum(Decimal(str(f.get("size", 0))) * Decimal(str(f.get("price", 0))) for f in fills)
        trades = len(fills)

        # Calculate fees (spread captured)
        fees = Decimal(0)
        for f in fills:
            # Estimate fee as half the spread at time of fill
            spread_estimate = Decimal("0.02")  # Would use actual spread
            fees += Decimal(str(f.get("size", 0))) * spread_estimate / 2

        # Calculate inventory PnL
        inventory_pnl = Decimal(0)
        for token_id, size in self._inventory.items():
            if token_id in current_prices:
                # Simple PnL based on current price vs assumed entry at mid
                entry_price = Decimal("0.5")  # Would track actual entry
                current = current_prices[token_id]
                inventory_pnl += size * (current - entry_price)

        return LPPerformance(
            total_volume=total_volume,
            fees_earned=fees,
            inventory_pnl=inventory_pnl,
            net_pnl=fees + inventory_pnl,
            trades_made=trades,
            fill_rate=0.5,  # Would calculate from actual data
            avg_spread_captured=float(fees / total_volume) if total_volume > 0 else 0,
        )

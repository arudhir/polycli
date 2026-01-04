"""Market-related models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class MarketOutcome(BaseModel):
    """A single outcome in a market."""

    token_id: str
    outcome: str
    price: Decimal = Field(ge=0, le=1)
    winner: Optional[bool] = None


class OrderBookLevel(BaseModel):
    """A single level in the order book."""

    price: Decimal = Field(ge=0, le=1)
    size: Decimal = Field(ge=0)


class OrderBook(BaseModel):
    """Order book for a market outcome."""

    token_id: str
    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if not self.bids or not self.asks:
            return None
        return self.asks[0].price - self.bids[0].price

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price."""
        if not self.bids or not self.asks:
            return None
        return (self.asks[0].price + self.bids[0].price) / 2

    def depth_at_price(self, price: Decimal, side: str) -> Decimal:
        """Calculate total size available up to a given price."""
        levels = self.bids if side == "bid" else self.asks
        total = Decimal(0)
        for level in levels:
            if side == "bid" and level.price >= price:
                total += level.size
            elif side == "ask" and level.price <= price:
                total += level.size
        return total


class Market(BaseModel):
    """A Polymarket market."""

    condition_id: str
    question: str
    slug: str
    outcomes: list[MarketOutcome]
    end_date: Optional[datetime] = None
    resolution_source: Optional[str] = None
    volume: Decimal = Field(default=Decimal(0))
    liquidity: Decimal = Field(default=Decimal(0))
    created_at: Optional[datetime] = None
    active: bool = True
    closed: bool = False
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    @property
    def is_binary(self) -> bool:
        """Check if market has exactly two outcomes."""
        return len(self.outcomes) == 2

    @property
    def days_until_resolution(self) -> Optional[int]:
        """Calculate days until market end date."""
        if not self.end_date:
            return None
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)

    def get_outcome_price(self, outcome: str) -> Optional[Decimal]:
        """Get price for a specific outcome."""
        for o in self.outcomes:
            if o.outcome.lower() == outcome.lower():
                return o.price
        return None

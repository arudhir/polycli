"""Trade-related models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TradeType(str, Enum):
    """Type of trade."""

    BUY = "buy"
    SELL = "sell"


class Trade(BaseModel):
    """A single trade execution."""

    trade_id: str
    market_id: str
    token_id: str
    outcome: str
    trade_type: TradeType
    size: Decimal = Field(ge=0)
    price: Decimal = Field(ge=0, le=1)
    fee: Decimal = Field(default=Decimal(0), ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    order_id: Optional[str] = None

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost including fees."""
        if self.trade_type == TradeType.BUY:
            return (self.size * self.price) + self.fee
        return (self.size * self.price) - self.fee


class TradeJournalEntry(BaseModel):
    """A journal entry for a trade decision."""

    id: Optional[int] = None
    market_id: str
    market_question: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Pre-trade analysis
    thesis: str = Field(description="Your reasoning for the trade")
    edge_source: str = Field(description="Where does your edge come from?")
    estimated_probability: Decimal = Field(ge=0, le=1)
    market_probability: Decimal = Field(ge=0, le=1)
    confidence_level: int = Field(ge=1, le=10)

    # Position details
    position_size: Decimal
    entry_price: Decimal
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None

    # Risk assessment
    max_loss_acceptable: bool = True
    correlated_positions: list[str] = Field(default_factory=list)

    # Resolution criteria
    resolution_source: str
    resolution_criteria_clear: bool = True
    criteria_notes: Optional[str] = None

    # Outcome tracking (filled after resolution)
    exit_price: Optional[Decimal] = None
    exit_date: Optional[datetime] = None
    outcome: Optional[str] = None
    realized_pnl: Optional[Decimal] = None
    post_mortem: Optional[str] = None
    lessons_learned: Optional[str] = None

    @property
    def perceived_edge(self) -> Decimal:
        """Calculate perceived edge as difference between estimates."""
        return self.estimated_probability - self.market_probability

    @property
    def expected_value(self) -> Decimal:
        """Calculate expected value of the trade."""
        # EV = (win_prob * win_amount) - (loss_prob * loss_amount)
        win_amount = (1 - self.entry_price) * self.position_size
        loss_amount = self.entry_price * self.position_size
        return (self.estimated_probability * win_amount) - (
            (1 - self.estimated_probability) * loss_amount
        )

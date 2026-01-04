"""Position-related models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class Position(BaseModel):
    """A position in a market."""

    market_id: str
    market_question: str
    token_id: str
    outcome: str
    size: Decimal = Field(ge=0)
    avg_entry_price: Decimal = Field(ge=0, le=1)
    current_price: Decimal = Field(ge=0, le=1)
    entry_date: datetime
    target_exit_price: Optional[Decimal] = Field(default=None, ge=0, le=1)
    stop_loss_price: Optional[Decimal] = Field(default=None, ge=0, le=1)

    @computed_field
    @property
    def cost_basis(self) -> Decimal:
        """Calculate total cost basis."""
        return self.size * self.avg_entry_price

    @computed_field
    @property
    def current_value(self) -> Decimal:
        """Calculate current value."""
        return self.size * self.current_price

    @computed_field
    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L."""
        return self.current_value - self.cost_basis

    @computed_field
    @property
    def unrealized_pnl_pct(self) -> Decimal:
        """Calculate unrealized P&L percentage."""
        if self.cost_basis == 0:
            return Decimal(0)
        return (self.unrealized_pnl / self.cost_basis) * 100

    @property
    def max_profit(self) -> Decimal:
        """Calculate maximum possible profit (if outcome wins)."""
        return self.size - self.cost_basis

    @property
    def max_loss(self) -> Decimal:
        """Calculate maximum possible loss (if outcome loses)."""
        return self.cost_basis


class PositionSummary(BaseModel):
    """Summary of all positions."""

    positions: list[Position] = Field(default_factory=list)
    total_invested: Decimal = Field(default=Decimal(0))
    total_current_value: Decimal = Field(default=Decimal(0))
    total_unrealized_pnl: Decimal = Field(default=Decimal(0))
    reserve_balance: Decimal = Field(default=Decimal(0))

    @computed_field
    @property
    def portfolio_value(self) -> Decimal:
        """Total portfolio value including reserves."""
        return self.total_current_value + self.reserve_balance

    @computed_field
    @property
    def position_count(self) -> int:
        """Number of open positions."""
        return len(self.positions)

    def positions_by_market(self, market_id: str) -> list[Position]:
        """Get all positions for a specific market."""
        return [p for p in self.positions if p.market_id == market_id]

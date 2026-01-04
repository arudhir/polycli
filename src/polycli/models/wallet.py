"""Wallet tracking models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class WalletPosition(BaseModel):
    """A position held by a tracked wallet."""

    market_id: str
    market_question: str
    token_id: str
    outcome: str
    size: Decimal
    avg_price: Decimal
    current_price: Decimal
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class WalletSnapshot(BaseModel):
    """Snapshot of a wallet's positions at a point in time."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    positions: list[WalletPosition] = Field(default_factory=list)
    total_value: Decimal = Field(default=Decimal(0))


class Wallet(BaseModel):
    """A tracked wallet."""

    address: str
    name: Optional[str] = None
    strategy: Optional[str] = Field(
        default=None,
        description="Observed trading strategy (e.g., 'news_trader', 'whale', 'arbitrageur')",
    )
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = None

    # Performance tracking
    win_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    avg_return: Optional[Decimal] = None
    total_volume: Decimal = Field(default=Decimal(0))

    # Current state
    current_positions: list[WalletPosition] = Field(default_factory=list)
    snapshots: list[WalletSnapshot] = Field(default_factory=list)

    def add_snapshot(self) -> None:
        """Create a snapshot of current positions."""
        total = sum(p.size * p.current_price for p in self.current_positions)
        snapshot = WalletSnapshot(
            positions=self.current_positions.copy(),
            total_value=total,
        )
        self.snapshots.append(snapshot)

    def position_changes(self, previous_snapshot: WalletSnapshot) -> dict:
        """Calculate position changes since a previous snapshot."""
        prev_positions = {p.token_id: p for p in previous_snapshot.positions}
        curr_positions = {p.token_id: p for p in self.current_positions}

        changes = {
            "new": [],
            "closed": [],
            "increased": [],
            "decreased": [],
        }

        for token_id, pos in curr_positions.items():
            if token_id not in prev_positions:
                changes["new"].append(pos)
            elif pos.size > prev_positions[token_id].size:
                changes["increased"].append(
                    {"position": pos, "delta": pos.size - prev_positions[token_id].size}
                )
            elif pos.size < prev_positions[token_id].size:
                changes["decreased"].append(
                    {"position": pos, "delta": prev_positions[token_id].size - pos.size}
                )

        for token_id, pos in prev_positions.items():
            if token_id not in curr_positions:
                changes["closed"].append(pos)

        return changes

"""Track smart wallets systematically.

Build a portfolio of 10-15 proven wallets with different strategies
and track their position changes in real-time.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional

from polycli.api.external import PolymarketSubgraphClient
from polycli.api.polymarket import PolymarketClient
from polycli.models import Wallet, WalletPosition, WalletSnapshot


class WalletTracker:
    """Track and analyze smart wallet activity."""

    def __init__(
        self,
        polymarket_client: PolymarketClient,
        subgraph_client: Optional[PolymarketSubgraphClient] = None,
    ):
        self._pm = polymarket_client
        self._subgraph = subgraph_client or PolymarketSubgraphClient()
        self._tracked_wallets: dict[str, Wallet] = {}

    def add_wallet(
        self,
        address: str,
        name: Optional[str] = None,
        strategy: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Wallet:
        """Add a wallet to track."""
        wallet = Wallet(
            address=address.lower(),
            name=name,
            strategy=strategy,
            tags=tags or [],
        )
        self._tracked_wallets[wallet.address] = wallet
        return wallet

    def remove_wallet(self, address: str) -> bool:
        """Remove a wallet from tracking."""
        address = address.lower()
        if address in self._tracked_wallets:
            del self._tracked_wallets[address]
            return True
        return False

    def get_wallet(self, address: str) -> Optional[Wallet]:
        """Get a tracked wallet by address."""
        return self._tracked_wallets.get(address.lower())

    def list_wallets(self) -> list[Wallet]:
        """List all tracked wallets."""
        return list(self._tracked_wallets.values())

    async def fetch_wallet_positions(self, address: str) -> list[WalletPosition]:
        """Fetch current positions for a wallet."""
        positions_data = await self._pm.get_wallet_positions(address)
        positions = []

        for pos in positions_data:
            positions.append(
                WalletPosition(
                    market_id=pos.get("conditionId", ""),
                    market_question=pos.get("title", ""),
                    token_id=pos.get("tokenId", ""),
                    outcome=pos.get("outcome", ""),
                    size=Decimal(str(pos.get("size", 0))),
                    avg_price=Decimal(str(pos.get("avgPrice", 0))),
                    current_price=Decimal(str(pos.get("currentPrice", 0))),
                )
            )
        return positions

    async def update_wallet(self, address: str) -> Optional[dict]:
        """Update wallet positions and detect changes."""
        wallet = self._tracked_wallets.get(address.lower())
        if not wallet:
            return None

        # Store previous snapshot
        previous_positions = wallet.current_positions.copy()
        previous_snapshot = WalletSnapshot(positions=previous_positions)

        # Fetch new positions
        new_positions = await self.fetch_wallet_positions(address)
        wallet.current_positions = new_positions
        wallet.last_activity = datetime.utcnow()

        # Add snapshot for history
        wallet.add_snapshot()

        # Calculate changes
        if previous_positions:
            changes = wallet.position_changes(previous_snapshot)
            return changes

        return {"new": new_positions, "closed": [], "increased": [], "decreased": []}

    async def update_all_wallets(self) -> dict[str, dict]:
        """Update all tracked wallets and return changes."""
        tasks = [self.update_wallet(addr) for addr in self._tracked_wallets]
        results = await asyncio.gather(*tasks)

        return {
            addr: result
            for addr, result in zip(self._tracked_wallets.keys(), results)
            if result
        }

    async def get_recent_activity(
        self, address: str, limit: int = 50
    ) -> list[dict]:
        """Get recent trading activity for a wallet from on-chain data."""
        return await self._subgraph.get_wallet_activity(address, first=limit)

    async def find_large_trades(
        self, min_amount: float = 10000, limit: int = 50
    ) -> list[dict]:
        """Find large trades that might indicate smart money movement."""
        return await self._subgraph.get_large_trades(min_amount, first=limit)

    def get_consensus_positions(self, min_wallets: int = 2) -> dict[str, list[Wallet]]:
        """Find markets where multiple tracked wallets have positions.

        Returns markets with at least min_wallets holding the same position.
        """
        market_positions: dict[str, dict[str, list[Wallet]]] = {}

        for wallet in self._tracked_wallets.values():
            for pos in wallet.current_positions:
                key = f"{pos.market_id}:{pos.outcome}"
                if pos.market_id not in market_positions:
                    market_positions[pos.market_id] = {}
                if key not in market_positions[pos.market_id]:
                    market_positions[pos.market_id][key] = []
                market_positions[pos.market_id][key].append(wallet)

        # Filter to positions held by multiple wallets
        consensus = {}
        for market_id, positions in market_positions.items():
            for position_key, wallets in positions.items():
                if len(wallets) >= min_wallets:
                    consensus[position_key] = wallets

        return consensus

    async def calculate_wallet_performance(self, address: str) -> dict:
        """Calculate historical performance metrics for a wallet."""
        activity = await self.get_recent_activity(address, limit=500)

        if not activity:
            return {"trades": 0, "volume": Decimal(0)}

        total_volume = sum(
            Decimal(str(t.get("collateralAmount", 0))) / Decimal("1e6")
            for t in activity
        )

        return {
            "trades": len(activity),
            "volume": total_volume,
            "first_trade": activity[-1].get("creationTimestamp") if activity else None,
            "last_trade": activity[0].get("creationTimestamp") if activity else None,
        }

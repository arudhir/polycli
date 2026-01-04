"""Polymarket API client using py-clob-client."""

from decimal import Decimal
from typing import Optional

import httpx
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from pydantic import SecretStr

from polycli.models import Market, MarketOutcome, OrderBook, OrderBookLevel


class PolymarketClient:
    """Client for interacting with Polymarket APIs."""

    GAMMA_API_URL = "https://gamma-api.polymarket.com"
    CLOB_API_URL = "https://clob.polymarket.com"

    def __init__(
        self,
        api_key: Optional[SecretStr] = None,
        api_secret: Optional[SecretStr] = None,
        passphrase: Optional[SecretStr] = None,
        private_key: Optional[SecretStr] = None,
        chain_id: int = 137,  # Polygon mainnet
    ):
        """Initialize the Polymarket client."""
        self._http = httpx.AsyncClient(timeout=30.0)
        self._clob: Optional[ClobClient] = None

        # Initialize CLOB client if credentials provided
        if private_key:
            self._clob = ClobClient(
                host=self.CLOB_API_URL,
                key=private_key.get_secret_value() if private_key else None,
                chain_id=chain_id,
            )
            if api_key and api_secret and passphrase:
                self._clob.set_api_creds(
                    ClobClient.derive_api_key(
                        api_key.get_secret_value(),
                        api_secret.get_secret_value(),
                        passphrase.get_secret_value(),
                    )
                )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> "PolymarketClient":
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore[no-untyped-def]
        await self.close()

    async def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
        closed: bool = False,
    ) -> list[Market]:
        """Fetch markets from Polymarket."""
        params = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        response = await self._http.get(f"{self.GAMMA_API_URL}/markets", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for item in data:
            outcomes = []
            for token in item.get("tokens", []):
                outcomes.append(
                    MarketOutcome(
                        token_id=token.get("token_id", ""),
                        outcome=token.get("outcome", ""),
                        price=Decimal(str(token.get("price", 0))),
                        winner=token.get("winner"),
                    )
                )

            markets.append(
                Market(
                    condition_id=item.get("condition_id", ""),
                    question=item.get("question", ""),
                    slug=item.get("slug", ""),
                    outcomes=outcomes,
                    volume=Decimal(str(item.get("volume", 0))),
                    liquidity=Decimal(str(item.get("liquidity", 0))),
                    active=item.get("active", True),
                    closed=item.get("closed", False),
                    category=item.get("category"),
                    tags=item.get("tags", []),
                )
            )
        return markets

    async def get_market(self, condition_id: str) -> Optional[Market]:
        """Fetch a specific market by condition ID."""
        response = await self._http.get(f"{self.GAMMA_API_URL}/markets/{condition_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        item = response.json()

        outcomes = []
        for token in item.get("tokens", []):
            outcomes.append(
                MarketOutcome(
                    token_id=token.get("token_id", ""),
                    outcome=token.get("outcome", ""),
                    price=Decimal(str(token.get("price", 0))),
                    winner=token.get("winner"),
                )
            )

        return Market(
            condition_id=item.get("condition_id", ""),
            question=item.get("question", ""),
            slug=item.get("slug", ""),
            outcomes=outcomes,
            volume=Decimal(str(item.get("volume", 0))),
            liquidity=Decimal(str(item.get("liquidity", 0))),
            active=item.get("active", True),
            closed=item.get("closed", False),
            resolution_source=item.get("resolution_source"),
            category=item.get("category"),
            tags=item.get("tags", []),
        )

    async def search_markets(self, query: str, limit: int = 20) -> list[Market]:
        """Search markets by query string."""
        params = {"_q": query, "limit": limit}
        response = await self._http.get(f"{self.GAMMA_API_URL}/markets", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for item in data:
            outcomes = []
            for token in item.get("tokens", []):
                outcomes.append(
                    MarketOutcome(
                        token_id=token.get("token_id", ""),
                        outcome=token.get("outcome", ""),
                        price=Decimal(str(token.get("price", 0))),
                    )
                )
            markets.append(
                Market(
                    condition_id=item.get("condition_id", ""),
                    question=item.get("question", ""),
                    slug=item.get("slug", ""),
                    outcomes=outcomes,
                    volume=Decimal(str(item.get("volume", 0))),
                    liquidity=Decimal(str(item.get("liquidity", 0))),
                    active=item.get("active", True),
                    closed=item.get("closed", False),
                )
            )
        return markets

    async def get_order_book(self, token_id: str) -> OrderBook:
        """Fetch order book for a token."""
        response = await self._http.get(
            f"{self.CLOB_API_URL}/book", params={"token_id": token_id}
        )
        response.raise_for_status()
        data = response.json()

        bids = [
            OrderBookLevel(price=Decimal(str(b["price"])), size=Decimal(str(b["size"])))
            for b in data.get("bids", [])
        ]
        asks = [
            OrderBookLevel(price=Decimal(str(a["price"])), size=Decimal(str(a["size"])))
            for a in data.get("asks", [])
        ]

        return OrderBook(token_id=token_id, bids=bids, asks=asks)

    async def get_price_history(
        self, token_id: str, interval: str = "1d", limit: int = 100
    ) -> list[dict]:
        """Fetch price history for a token."""
        params = {"market": token_id, "interval": interval, "limit": limit}
        response = await self._http.get(f"{self.CLOB_API_URL}/prices-history", params=params)
        response.raise_for_status()
        return response.json().get("history", [])

    async def get_trades(
        self, token_id: Optional[str] = None, maker: Optional[str] = None, limit: int = 100
    ) -> list[dict]:
        """Fetch recent trades, optionally filtered by token or maker."""
        params: dict = {"limit": limit}
        if token_id:
            params["market"] = token_id
        if maker:
            params["maker"] = maker

        response = await self._http.get(f"{self.CLOB_API_URL}/trades", params=params)
        response.raise_for_status()
        return response.json()

    def place_limit_order(
        self,
        token_id: str,
        price: Decimal,
        size: Decimal,
        side: str,
    ) -> Optional[dict]:
        """Place a limit order using the CLOB client."""
        if not self._clob:
            raise ValueError("CLOB client not initialized. Provide private key.")

        order_args = OrderArgs(
            token_id=token_id,
            price=float(price),
            size=float(size),
            side=side.upper(),
        )
        signed_order = self._clob.create_order(order_args)
        return self._clob.post_order(signed_order, OrderType.GTC)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self._clob:
            raise ValueError("CLOB client not initialized. Provide private key.")

        result = self._clob.cancel(order_id)
        return result.get("canceled", False)

    async def get_wallet_positions(self, address: str) -> list[dict]:
        """Fetch positions for a wallet address."""
        response = await self._http.get(
            f"{self.GAMMA_API_URL}/positions", params={"user": address}
        )
        response.raise_for_status()
        return response.json()

"""External API clients for cross-referencing."""

from decimal import Decimal
from typing import Optional

import httpx
from pydantic import BaseModel, Field, SecretStr


class PredictionMarket(BaseModel):
    """A prediction from an external platform."""

    platform: str
    question: str
    url: str
    probability: Decimal = Field(ge=0, le=1)
    volume: Optional[Decimal] = None
    num_traders: Optional[int] = None


class ManifoldClient:
    """Client for Manifold Markets API."""

    BASE_URL = "https://api.manifold.markets/v0"

    def __init__(self, api_key: Optional[SecretStr] = None):
        self._http = httpx.AsyncClient(timeout=30.0)
        self._api_key = api_key

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "ManifoldClient":
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore[no-untyped-def]
        await self.close()

    async def search_markets(self, query: str, limit: int = 20) -> list[PredictionMarket]:
        """Search for markets on Manifold."""
        params = {"term": query, "limit": limit}
        response = await self._http.get(f"{self.BASE_URL}/search-markets", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for item in data:
            if item.get("outcomeType") != "BINARY":
                continue

            markets.append(
                PredictionMarket(
                    platform="manifold",
                    question=item.get("question", ""),
                    url=f"https://manifold.markets/{item.get('creatorUsername')}/{item.get('slug')}",
                    probability=Decimal(str(item.get("probability", 0))),
                    volume=Decimal(str(item.get("volume", 0))),
                    num_traders=item.get("uniqueBettorCount"),
                )
            )
        return markets

    async def get_market(self, slug: str) -> Optional[PredictionMarket]:
        """Get a specific market by slug."""
        response = await self._http.get(f"{self.BASE_URL}/slug/{slug}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        item = response.json()

        return PredictionMarket(
            platform="manifold",
            question=item.get("question", ""),
            url=f"https://manifold.markets/{item.get('creatorUsername')}/{item.get('slug')}",
            probability=Decimal(str(item.get("probability", 0))),
            volume=Decimal(str(item.get("volume", 0))),
            num_traders=item.get("uniqueBettorCount"),
        )


class MetaculusClient:
    """Client for Metaculus API."""

    BASE_URL = "https://www.metaculus.com/api2"

    def __init__(self, api_key: Optional[SecretStr] = None):
        self._http = httpx.AsyncClient(timeout=30.0)
        headers = {}
        if api_key:
            headers["Authorization"] = f"Token {api_key.get_secret_value()}"
        self._http.headers.update(headers)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "MetaculusClient":
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore[no-untyped-def]
        await self.close()

    async def search_questions(self, query: str, limit: int = 20) -> list[PredictionMarket]:
        """Search for questions on Metaculus."""
        params = {"search": query, "limit": limit, "type": "forecast"}
        response = await self._http.get(f"{self.BASE_URL}/questions/", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for item in data.get("results", []):
            # Only include binary questions
            if item.get("possibilities", {}).get("type") != "binary":
                continue

            prediction = item.get("community_prediction", {})
            prob = prediction.get("full", {}).get("q2", 0.5) if prediction else 0.5

            markets.append(
                PredictionMarket(
                    platform="metaculus",
                    question=item.get("title", ""),
                    url=f"https://www.metaculus.com/questions/{item.get('id')}",
                    probability=Decimal(str(prob)),
                    num_traders=item.get("number_of_predictions"),
                )
            )
        return markets


class PolymarketSubgraphClient:
    """Client for Polymarket's subgraph to fetch on-chain data."""

    SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-5"

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._http.aclose()

    async def get_wallet_activity(
        self, address: str, first: int = 100
    ) -> list[dict]:
        """Fetch recent activity for a wallet from the subgraph."""
        query = """
        query GetWalletActivity($address: String!, $first: Int!) {
            fpmmTrades(
                where: { creator: $address }
                orderBy: creationTimestamp
                orderDirection: desc
                first: $first
            ) {
                id
                creator { id }
                fpmm { id question }
                outcomeIndex
                outcomeTokensTraded
                collateralAmount
                creationTimestamp
                transactionHash
            }
        }
        """
        variables = {"address": address.lower(), "first": first}
        response = await self._http.post(
            self.SUBGRAPH_URL,
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("fpmmTrades", [])

    async def get_large_trades(
        self, min_amount: float = 10000, first: int = 50
    ) -> list[dict]:
        """Fetch large trades across all markets."""
        query = """
        query GetLargeTrades($minAmount: BigInt!, $first: Int!) {
            fpmmTrades(
                where: { collateralAmount_gt: $minAmount }
                orderBy: creationTimestamp
                orderDirection: desc
                first: $first
            ) {
                id
                creator { id }
                fpmm { id question }
                outcomeIndex
                outcomeTokensTraded
                collateralAmount
                creationTimestamp
            }
        }
        """
        variables = {"minAmount": str(int(min_amount * 1e6)), "first": first}
        response = await self._http.post(
            self.SUBGRAPH_URL,
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("fpmmTrades", [])

"""Twitter/X advanced search for early signals.

Set up searches for key terms + "before:[date]" to find early signals
that haven't reached the crowd yet.

NOTE: Requires Twitter API v2 with elevated access (paid tier) for
search functionality. Basic tier is limited.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
from pydantic import SecretStr


@dataclass
class TweetSignal:
    """A tweet that may signal market-relevant information."""

    tweet_id: str
    text: str
    author: str
    author_followers: int
    created_at: datetime
    retweets: int
    likes: int
    url: str
    keywords_matched: list[str]


class TwitterSignalFinder:
    """Find early signals on Twitter before they hit prediction markets.

    NOTE: This requires Twitter API v2 elevated access (paid).
    The free tier has very limited search capabilities.
    """

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, bearer_token: Optional[SecretStr] = None):
        """Initialize Twitter client.

        Args:
            bearer_token: Twitter API v2 bearer token
        """
        self._token = bearer_token
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http is None:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token.get_secret_value()}"
            self._http = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._http

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None

    async def search_recent(
        self,
        query: str,
        max_results: int = 100,
        min_followers: int = 1000,
    ) -> list[TweetSignal]:
        """Search recent tweets (last 7 days) for signals.

        Args:
            query: Twitter search query (supports operators)
            max_results: Maximum number of results (10-100)
            min_followers: Minimum follower count filter
        """
        if not self._token:
            raise ValueError("Twitter bearer token required for search")

        client = await self._get_client()

        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username,public_metrics",
        }

        response = await client.get(
            f"{self.BASE_URL}/tweets/search/recent", params=params
        )
        response.raise_for_status()
        data = response.json()

        # Build author lookup
        authors = {}
        for user in data.get("includes", {}).get("users", []):
            authors[user["id"]] = {
                "username": user["username"],
                "followers": user.get("public_metrics", {}).get("followers_count", 0),
            }

        signals = []
        for tweet in data.get("data", []):
            author_id = tweet.get("author_id")
            author_info = authors.get(author_id, {})
            followers = author_info.get("followers", 0)

            # Filter by follower count
            if followers < min_followers:
                continue

            metrics = tweet.get("public_metrics", {})
            signals.append(
                TweetSignal(
                    tweet_id=tweet["id"],
                    text=tweet["text"],
                    author=f"@{author_info.get('username', 'unknown')}",
                    author_followers=followers,
                    created_at=datetime.fromisoformat(
                        tweet["created_at"].replace("Z", "+00:00")
                    ),
                    retweets=metrics.get("retweet_count", 0),
                    likes=metrics.get("like_count", 0),
                    url=f"https://twitter.com/i/web/status/{tweet['id']}",
                    keywords_matched=[],  # Filled by caller if needed
                )
            )

        # Sort by engagement
        signals.sort(key=lambda s: s.retweets + s.likes, reverse=True)
        return signals

    def build_market_query(
        self,
        keywords: list[str],
        exclude_keywords: Optional[list[str]] = None,
        before_date: Optional[datetime] = None,
        from_accounts: Optional[list[str]] = None,
        min_retweets: int = 0,
        min_likes: int = 0,
    ) -> str:
        """Build a Twitter search query for market-relevant signals.

        Args:
            keywords: Keywords to search for (OR'd together)
            exclude_keywords: Keywords to exclude
            before_date: Only tweets before this date
            from_accounts: Only from these accounts
            min_retweets: Minimum retweet count
            min_likes: Minimum like count

        Returns:
            Twitter search query string
        """
        parts = []

        # Main keywords (OR'd)
        if keywords:
            keyword_query = " OR ".join(f'"{k}"' if " " in k else k for k in keywords)
            parts.append(f"({keyword_query})")

        # Exclusions
        if exclude_keywords:
            for exc in exclude_keywords:
                parts.append(f'-"{exc}"' if " " in exc else f"-{exc}")

        # Date filter
        if before_date:
            date_str = before_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            parts.append(f"until:{date_str}")

        # Account filter
        if from_accounts:
            account_query = " OR ".join(f"from:{acc}" for acc in from_accounts)
            parts.append(f"({account_query})")

        # Engagement filters
        if min_retweets > 0:
            parts.append(f"min_retweets:{min_retweets}")
        if min_likes > 0:
            parts.append(f"min_faves:{min_likes}")

        # Exclude retweets for cleaner signals
        parts.append("-is:retweet")

        return " ".join(parts)

    async def monitor_keywords(
        self,
        keywords: list[str],
        lookback_hours: int = 24,
        min_followers: int = 5000,
    ) -> list[TweetSignal]:
        """Monitor keywords for recent high-signal tweets.

        Use this to find early signals about market-moving events.

        Args:
            keywords: Keywords related to your markets
            lookback_hours: How far back to search
            min_followers: Minimum author followers for credibility
        """
        query = self.build_market_query(
            keywords=keywords,
            min_retweets=5,  # Some engagement required
        )

        return await self.search_recent(
            query=query,
            max_results=100,
            min_followers=min_followers,
        )

    @staticmethod
    def get_insider_accounts() -> list[str]:
        """Get list of accounts often cited for breaking news.

        Returns accounts known for early/insider political/market news.
        Customize this based on your market focus.
        """
        return [
            # Political (customize based on markets you trade)
            "axios",
            "politico",
            "paborotnik",
            "igaborisov",
            # Crypto/Finance
            "tier10k",
            "whale_alert",
            "unusual_whales",
            # General breaking news
            "BNONews",
            "spectatorindex",
        ]

    async def find_pre_news_signals(
        self,
        market_keywords: list[str],
        hours_before: int = 4,
    ) -> list[TweetSignal]:
        """Find signals posted hours before news typically breaks.

        The thesis is that insiders/early knowers often tweet
        about events 2-4 hours before mainstream news picks up.

        Args:
            market_keywords: Keywords related to your market
            hours_before: Look for tweets posted this many hours ago
        """
        target_time = datetime.utcnow() - timedelta(hours=hours_before)

        query = self.build_market_query(
            keywords=market_keywords,
            from_accounts=self.get_insider_accounts(),
            before_date=datetime.utcnow() - timedelta(hours=1),  # Not too recent
        )

        signals = await self.search_recent(query=query, max_results=50, min_followers=10000)

        # Filter to tweets from the target window
        window_start = target_time - timedelta(hours=2)
        window_end = target_time + timedelta(hours=2)

        return [s for s in signals if window_start <= s.created_at <= window_end]

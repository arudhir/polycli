"""News reaction speed.

Have RSS feeds, Twitter lists, Discord alerts to react seconds after breaking news.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx
from pydantic import SecretStr


class NewsSource(str, Enum):
    """Types of news sources."""

    RSS = "rss"
    TWITTER = "twitter"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    API = "api"


@dataclass
class NewsItem:
    """A news item from any source."""

    source: NewsSource
    source_name: str
    title: str
    content: str
    url: Optional[str]
    timestamp: datetime
    keywords: list[str]
    relevance_score: float


@dataclass
class MarketReaction:
    """Suggested reaction to news."""

    news_item: NewsItem
    affected_markets: list[str]
    suggested_action: str
    urgency: str  # "immediate", "fast", "normal"
    confidence: float
    reasoning: str


@dataclass
class NewsAlert:
    """An alert configuration for news monitoring."""

    id: str
    keywords: list[str]
    sources: list[NewsSource]
    callback_url: Optional[str]
    telegram_chat_id: Optional[str]
    enabled: bool


class NewsReactor:
    """Monitor news sources and react quickly to breaking events."""

    # Keywords that often precede market-moving news
    BREAKING_INDICATORS = [
        "breaking",
        "just in",
        "urgent",
        "developing",
        "confirmed",
        "announced",
        "official",
    ]

    def __init__(
        self,
        telegram_token: Optional[SecretStr] = None,
    ):
        """Initialize news reactor.

        Args:
            telegram_token: Telegram bot token for alerts
        """
        self._telegram_token = telegram_token
        self._http = httpx.AsyncClient(timeout=10.0)
        self._alerts: dict[str, NewsAlert] = {}
        self._recent_news: list[NewsItem] = []
        self._market_keywords: dict[str, list[str]] = {}  # market_id -> keywords

    async def close(self) -> None:
        """Close HTTP client."""
        await self._http.aclose()

    def register_market(
        self,
        market_id: str,
        keywords: list[str],
    ) -> None:
        """Register a market with keywords to watch.

        Args:
            market_id: Market to watch
            keywords: Keywords that would affect this market
        """
        self._market_keywords[market_id] = [k.lower() for k in keywords]

    def create_alert(
        self,
        keywords: list[str],
        sources: Optional[list[NewsSource]] = None,
        callback_url: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ) -> NewsAlert:
        """Create a news alert.

        Args:
            keywords: Keywords to monitor
            sources: Sources to monitor (all if None)
            callback_url: Webhook URL for alerts
            telegram_chat_id: Telegram chat for alerts
        """
        alert_id = f"alert_{len(self._alerts) + 1:06d}"

        alert = NewsAlert(
            id=alert_id,
            keywords=[k.lower() for k in keywords],
            sources=sources or list(NewsSource),
            callback_url=callback_url,
            telegram_chat_id=telegram_chat_id,
            enabled=True,
        )

        self._alerts[alert_id] = alert
        return alert

    def process_news(self, news_item: NewsItem) -> list[MarketReaction]:
        """Process a news item and generate market reactions.

        Args:
            news_item: News to process
        """
        reactions = []

        # Check which markets are affected
        affected_markets = self._find_affected_markets(news_item)

        if not affected_markets:
            return []

        # Determine urgency
        urgency = self._determine_urgency(news_item)

        # Generate reaction for each affected market
        for market_id in affected_markets:
            reaction = self._generate_reaction(news_item, market_id, urgency)
            if reaction:
                reactions.append(reaction)

        # Store for reference
        self._recent_news.append(news_item)
        if len(self._recent_news) > 100:
            self._recent_news = self._recent_news[-100:]

        return reactions

    def _find_affected_markets(self, news_item: NewsItem) -> list[str]:
        """Find markets affected by news item."""
        affected = []
        news_text = f"{news_item.title} {news_item.content}".lower()

        for market_id, keywords in self._market_keywords.items():
            matches = sum(1 for kw in keywords if kw in news_text)
            if matches > 0:
                affected.append(market_id)

        return affected

    def _determine_urgency(self, news_item: NewsItem) -> str:
        """Determine urgency level of news."""
        text_lower = f"{news_item.title} {news_item.content}".lower()

        # Check for breaking indicators
        breaking_count = sum(
            1 for ind in self.BREAKING_INDICATORS if ind in text_lower
        )

        if breaking_count >= 2:
            return "immediate"
        elif breaking_count == 1:
            return "fast"
        else:
            return "normal"

    def _generate_reaction(
        self,
        news_item: NewsItem,
        market_id: str,
        urgency: str,
    ) -> Optional[MarketReaction]:
        """Generate suggested reaction for a market."""
        keywords = self._market_keywords.get(market_id, [])
        news_text = f"{news_item.title} {news_item.content}".lower()

        # Simple sentiment analysis
        positive_words = ["win", "success", "approve", "pass", "victory", "rise"]
        negative_words = ["fail", "reject", "lose", "defeat", "drop", "fall"]

        positive_count = sum(1 for w in positive_words if w in news_text)
        negative_count = sum(1 for w in negative_words if w in news_text)

        if positive_count > negative_count:
            action = "Consider buying YES"
            reasoning = "News sentiment appears positive"
        elif negative_count > positive_count:
            action = "Consider buying NO"
            reasoning = "News sentiment appears negative"
        else:
            action = "Monitor closely"
            reasoning = "News sentiment unclear"

        # Calculate confidence based on keyword matches
        keyword_matches = sum(1 for kw in keywords if kw in news_text)
        confidence = min(0.9, 0.3 + keyword_matches * 0.2)

        return MarketReaction(
            news_item=news_item,
            affected_markets=[market_id],
            suggested_action=action,
            urgency=urgency,
            confidence=confidence,
            reasoning=reasoning,
        )

    async def check_rss_feed(self, feed_url: str) -> list[NewsItem]:
        """Check an RSS feed for new items.

        Args:
            feed_url: URL of RSS feed
        """
        try:
            response = await self._http.get(feed_url)
            response.raise_for_status()
            # Would parse RSS XML here
            # This is a placeholder
            return []
        except Exception:
            return []

    async def send_telegram_alert(
        self,
        chat_id: str,
        message: str,
    ) -> bool:
        """Send alert via Telegram.

        Args:
            chat_id: Telegram chat ID
            message: Message to send
        """
        if not self._telegram_token:
            return False

        try:
            url = f"https://api.telegram.org/bot{self._telegram_token.get_secret_value()}/sendMessage"
            await self._http.post(
                url,
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            )
            return True
        except Exception:
            return False

    def get_news_feed_recommendations(self) -> dict[str, list[str]]:
        """Get recommended news feeds by category."""
        return {
            "politics_us": [
                "https://rss.politico.com/politics-news.xml",
                "https://feeds.feedburner.com/realclearpolitics/qlMj",
                "Twitter: @politicoalert, @axios",
            ],
            "economics": [
                "https://www.federalreserve.gov/feeds/press_all.xml",
                "https://feeds.a]reuters.com/reuters/businessNews",
                "Twitter: @business, @markets",
            ],
            "crypto": [
                "Twitter: @tier10k, @whale_alert",
                "Discord: Various alpha channels",
            ],
            "general_breaking": [
                "Twitter: @BNONews, @spectatorindex",
                "https://rss.ap.org/apf-topnews",
            ],
        }

    def setup_speed_optimizations(self) -> dict:
        """Get recommendations for fastest news reaction."""
        return {
            "twitter_setup": [
                "Use Twitter API v2 filtered stream for real-time",
                "Create a private list of breaking news accounts",
                "Enable push notifications on mobile for key accounts",
            ],
            "telegram_setup": [
                "Create a dedicated channel for news alerts",
                "Use telegram-bot for programmatic alerts",
                "Set notification sound to something distinct",
            ],
            "infrastructure": [
                "Run monitoring on low-latency cloud (us-east-1)",
                "Pre-authorize trading to avoid 2FA delays",
                "Keep browser tab open to Polymarket",
                "Have mobile app ready as backup",
            ],
            "process": [
                "Know your markets and expected moves",
                "Have limit orders pre-set at target levels",
                "Practice reaction time (paper trade breaking news)",
                "Accept you'll miss some - don't chase after 5+ minutes",
            ],
        }

    def calculate_reaction_window(
        self,
        news_time: datetime,
        market_move_time: datetime,
    ) -> dict:
        """Calculate how quickly market reacted to news.

        Args:
            news_time: When news broke
            market_move_time: When market moved
        """
        delta = (market_move_time - news_time).total_seconds()

        return {
            "reaction_seconds": delta,
            "reaction_minutes": delta / 60,
            "assessment": (
                "Instant (insider?)"
                if delta < 10
                else "Very fast"
                if delta < 60
                else "Fast"
                if delta < 300
                else "Normal"
                if delta < 900
                else "Slow"
            ),
            "was_tradeable": delta > 30,  # Need at least 30s to react
        }

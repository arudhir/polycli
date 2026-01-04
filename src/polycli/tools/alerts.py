"""Price alert bots.

Get Telegram notifications when markets hit specific thresholds -
speed matters when edge appears.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Optional

import httpx
from pydantic import SecretStr


class AlertType(str, Enum):
    """Type of price alert."""

    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CHANGE = "price_change"
    VOLUME_SPIKE = "volume_spike"


class AlertStatus(str, Enum):
    """Status of an alert."""

    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class PriceAlert:
    """A price alert configuration."""

    id: str
    market_id: str
    market_question: str
    token_id: str
    alert_type: AlertType
    threshold: Decimal
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    triggered_at: Optional[datetime] = None
    triggered_price: Optional[Decimal] = None
    notes: str = ""


@dataclass
class AlertNotification:
    """A notification to send."""

    alert: PriceAlert
    message: str
    current_price: Decimal
    timestamp: datetime


class AlertManager:
    """Manage price alerts and notifications."""

    def __init__(
        self,
        telegram_token: Optional[SecretStr] = None,
        telegram_chat_id: Optional[str] = None,
        discord_webhook: Optional[SecretStr] = None,
    ):
        """Initialize alert manager.

        Args:
            telegram_token: Telegram bot token for notifications
            telegram_chat_id: Telegram chat ID to send to
            discord_webhook: Discord webhook URL for notifications
        """
        self._telegram_token = telegram_token
        self._telegram_chat_id = telegram_chat_id
        self._discord_webhook = discord_webhook
        self._alerts: dict[str, PriceAlert] = {}
        self._alert_counter = 0
        self._callbacks: list[Callable[[AlertNotification], None]] = []

    def create_alert(
        self,
        market_id: str,
        market_question: str,
        token_id: str,
        alert_type: AlertType,
        threshold: Decimal,
        notes: str = "",
    ) -> PriceAlert:
        """Create a new price alert.

        Args:
            market_id: Market identifier
            market_question: Human-readable question
            token_id: Token to monitor
            alert_type: Type of alert
            threshold: Price/change threshold
            notes: Optional notes
        """
        self._alert_counter += 1
        alert_id = f"alert_{self._alert_counter:06d}"

        alert = PriceAlert(
            id=alert_id,
            market_id=market_id,
            market_question=market_question,
            token_id=token_id,
            alert_type=alert_type,
            threshold=threshold,
            notes=notes,
        )

        self._alerts[alert_id] = alert
        return alert

    def check_price(
        self,
        token_id: str,
        current_price: Decimal,
        previous_price: Optional[Decimal] = None,
    ) -> list[AlertNotification]:
        """Check if any alerts should trigger for a price update.

        Args:
            token_id: Token being updated
            current_price: Current price
            previous_price: Previous price (for change alerts)
        """
        notifications = []

        for alert in self._alerts.values():
            if alert.token_id != token_id:
                continue
            if alert.status != AlertStatus.ACTIVE:
                continue

            triggered = False
            message = ""

            if alert.alert_type == AlertType.PRICE_ABOVE:
                if current_price >= alert.threshold:
                    triggered = True
                    message = (
                        f"🔔 Price Alert: {alert.market_question[:50]}...\n"
                        f"Price hit {current_price:.2%} (above {alert.threshold:.2%})"
                    )

            elif alert.alert_type == AlertType.PRICE_BELOW:
                if current_price <= alert.threshold:
                    triggered = True
                    message = (
                        f"🔔 Price Alert: {alert.market_question[:50]}...\n"
                        f"Price hit {current_price:.2%} (below {alert.threshold:.2%})"
                    )

            elif alert.alert_type == AlertType.PRICE_CHANGE:
                if previous_price and previous_price > 0:
                    change = abs(current_price - previous_price) / previous_price
                    if change >= alert.threshold:
                        triggered = True
                        direction = "up" if current_price > previous_price else "down"
                        message = (
                            f"🔔 Price Change: {alert.market_question[:50]}...\n"
                            f"Price moved {direction} {change:.1%} "
                            f"({previous_price:.2%} → {current_price:.2%})"
                        )

            if triggered:
                alert.status = AlertStatus.TRIGGERED
                alert.triggered_at = datetime.utcnow()
                alert.triggered_price = current_price

                notification = AlertNotification(
                    alert=alert,
                    message=message,
                    current_price=current_price,
                    timestamp=datetime.utcnow(),
                )
                notifications.append(notification)

        return notifications

    async def send_notifications(
        self, notifications: list[AlertNotification]
    ) -> dict[str, bool]:
        """Send notifications through configured channels.

        Args:
            notifications: List of notifications to send
        """
        results = {"telegram": False, "discord": False, "callbacks": False}

        for notification in notifications:
            # Send to Telegram
            if self._telegram_token and self._telegram_chat_id:
                try:
                    await self._send_telegram(notification.message)
                    results["telegram"] = True
                except Exception:
                    pass

            # Send to Discord
            if self._discord_webhook:
                try:
                    await self._send_discord(notification.message)
                    results["discord"] = True
                except Exception:
                    pass

            # Call registered callbacks
            for callback in self._callbacks:
                try:
                    callback(notification)
                    results["callbacks"] = True
                except Exception:
                    pass

        return results

    async def _send_telegram(self, message: str) -> None:
        """Send message via Telegram."""
        if not self._telegram_token or not self._telegram_chat_id:
            return

        url = f"https://api.telegram.org/bot{self._telegram_token.get_secret_value()}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json={
                    "chat_id": self._telegram_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )

    async def _send_discord(self, message: str) -> None:
        """Send message via Discord webhook."""
        if not self._discord_webhook:
            return

        async with httpx.AsyncClient() as client:
            await client.post(
                self._discord_webhook.get_secret_value(),
                json={"content": message},
            )

    def register_callback(
        self, callback: Callable[[AlertNotification], None]
    ) -> None:
        """Register a callback function for notifications."""
        self._callbacks.append(callback)

    def get_active_alerts(self) -> list[PriceAlert]:
        """Get all active alerts."""
        return [a for a in self._alerts.values() if a.status == AlertStatus.ACTIVE]

    def get_triggered_alerts(self) -> list[PriceAlert]:
        """Get all triggered alerts."""
        return [a for a in self._alerts.values() if a.status == AlertStatus.TRIGGERED]

    def cancel_alert(self, alert_id: str) -> bool:
        """Cancel an alert."""
        if alert_id in self._alerts:
            self._alerts[alert_id].status = AlertStatus.CANCELLED
            return True
        return False

    def reactivate_alert(self, alert_id: str) -> bool:
        """Reactivate a triggered or cancelled alert."""
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.status = AlertStatus.ACTIVE
            alert.triggered_at = None
            alert.triggered_price = None
            return True
        return False

    def create_bracket_alerts(
        self,
        market_id: str,
        market_question: str,
        token_id: str,
        lower_bound: Decimal,
        upper_bound: Decimal,
    ) -> tuple[PriceAlert, PriceAlert]:
        """Create a pair of alerts for upper and lower bounds.

        Useful for monitoring a range.
        """
        lower_alert = self.create_alert(
            market_id=market_id,
            market_question=market_question,
            token_id=token_id,
            alert_type=AlertType.PRICE_BELOW,
            threshold=lower_bound,
            notes="Lower bracket",
        )

        upper_alert = self.create_alert(
            market_id=market_id,
            market_question=market_question,
            token_id=token_id,
            alert_type=AlertType.PRICE_ABOVE,
            threshold=upper_bound,
            notes="Upper bracket",
        )

        return lower_alert, upper_alert

"""Take breaks after big wins/losses.

Emotional trading destroys edges - if you're tilted, close the laptop.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional


class TiltLevel(str, Enum):
    """Level of emotional tilt."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TradingSession:
    """A trading session with emotional tracking."""

    start_time: datetime
    end_time: Optional[datetime]
    trades: int
    pnl: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    tilt_events: list[dict]
    forced_break: bool


@dataclass
class BreakRecommendation:
    """Recommendation for taking a break."""

    should_break: bool
    duration_minutes: int
    reason: str
    tilt_level: TiltLevel
    activities_suggested: list[str]


class BreakManager:
    """Manage trading breaks to prevent emotional decisions."""

    # Thresholds for break triggers
    BIG_WIN_THRESHOLD = Decimal("0.10")  # 10% of bankroll
    BIG_LOSS_THRESHOLD = Decimal("0.05")  # 5% of bankroll
    CONSECUTIVE_LOSS_LIMIT = 3
    SESSION_LOSS_LIMIT = Decimal("0.15")  # 15% of bankroll
    MAX_SESSION_HOURS = 4

    def __init__(
        self,
        bankroll: Decimal,
        big_win_threshold: Optional[Decimal] = None,
        big_loss_threshold: Optional[Decimal] = None,
    ):
        """Initialize break manager.

        Args:
            bankroll: Current bankroll for threshold calculations
            big_win_threshold: Override default big win threshold
            big_loss_threshold: Override default big loss threshold
        """
        self._bankroll = bankroll
        self._big_win = big_win_threshold or self.BIG_WIN_THRESHOLD
        self._big_loss = big_loss_threshold or self.BIG_LOSS_THRESHOLD
        self._current_session: Optional[TradingSession] = None
        self._consecutive_losses = 0
        self._session_history: list[TradingSession] = []

    def start_session(self) -> TradingSession:
        """Start a new trading session."""
        self._current_session = TradingSession(
            start_time=datetime.utcnow(),
            end_time=None,
            trades=0,
            pnl=Decimal(0),
            largest_win=Decimal(0),
            largest_loss=Decimal(0),
            tilt_events=[],
            forced_break=False,
        )
        self._consecutive_losses = 0
        return self._current_session

    def end_session(self) -> Optional[TradingSession]:
        """End the current trading session."""
        if self._current_session:
            self._current_session.end_time = datetime.utcnow()
            self._session_history.append(self._current_session)
            session = self._current_session
            self._current_session = None
            return session
        return None

    def record_trade(self, pnl: Decimal) -> BreakRecommendation:
        """Record a trade result and check if break is needed.

        Args:
            pnl: Profit/loss from the trade
        """
        if not self._current_session:
            self.start_session()

        session = self._current_session
        session.trades += 1
        session.pnl += pnl

        if pnl > session.largest_win:
            session.largest_win = pnl
        if pnl < session.largest_loss:
            session.largest_loss = pnl

        # Track consecutive losses
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        # Check for break triggers
        return self._check_break_needed(pnl)

    def _check_break_needed(self, latest_pnl: Decimal) -> BreakRecommendation:
        """Check if a break is needed based on current state."""
        session = self._current_session
        if not session:
            return BreakRecommendation(
                should_break=False,
                duration_minutes=0,
                reason="No active session",
                tilt_level=TiltLevel.NONE,
                activities_suggested=[],
            )

        reasons = []
        tilt_level = TiltLevel.NONE
        duration = 0

        # Check big win
        big_win_amount = self._bankroll * self._big_win
        if latest_pnl >= big_win_amount:
            reasons.append(f"Big win: ${latest_pnl:.2f}")
            tilt_level = max(tilt_level, TiltLevel.MEDIUM, key=lambda x: list(TiltLevel).index(x))
            duration = max(duration, 30)
            session.tilt_events.append({
                "type": "big_win",
                "amount": float(latest_pnl),
                "time": datetime.utcnow().isoformat(),
            })

        # Check big loss
        big_loss_amount = self._bankroll * self._big_loss
        if latest_pnl <= -big_loss_amount:
            reasons.append(f"Big loss: ${latest_pnl:.2f}")
            tilt_level = max(tilt_level, TiltLevel.HIGH, key=lambda x: list(TiltLevel).index(x))
            duration = max(duration, 60)
            session.tilt_events.append({
                "type": "big_loss",
                "amount": float(latest_pnl),
                "time": datetime.utcnow().isoformat(),
            })

        # Check consecutive losses
        if self._consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
            reasons.append(f"{self._consecutive_losses} consecutive losses")
            tilt_level = max(tilt_level, TiltLevel.HIGH, key=lambda x: list(TiltLevel).index(x))
            duration = max(duration, 45)

        # Check session loss
        session_loss_amount = self._bankroll * self.SESSION_LOSS_LIMIT
        if session.pnl <= -session_loss_amount:
            reasons.append(f"Session loss limit hit: ${session.pnl:.2f}")
            tilt_level = TiltLevel.CRITICAL
            duration = max(duration, 120)
            session.forced_break = True

        # Check session duration
        session_duration = (datetime.utcnow() - session.start_time).total_seconds() / 3600
        if session_duration >= self.MAX_SESSION_HOURS:
            reasons.append(f"Max session duration ({self.MAX_SESSION_HOURS}h)")
            tilt_level = max(tilt_level, TiltLevel.LOW, key=lambda x: list(TiltLevel).index(x))
            duration = max(duration, 30)

        should_break = len(reasons) > 0

        return BreakRecommendation(
            should_break=should_break,
            duration_minutes=duration,
            reason="; ".join(reasons) if reasons else "All clear",
            tilt_level=tilt_level,
            activities_suggested=self._get_break_activities(tilt_level),
        )

    def _get_break_activities(self, tilt_level: TiltLevel) -> list[str]:
        """Get suggested activities during break."""
        if tilt_level == TiltLevel.NONE:
            return []

        activities = [
            "Step away from screens",
            "Take a short walk",
            "Drink water",
            "Practice deep breathing",
        ]

        if tilt_level in [TiltLevel.HIGH, TiltLevel.CRITICAL]:
            activities.extend([
                "Do NOT check prices on phone",
                "Review your trading journal",
                "Talk to someone about non-trading topics",
                "Exercise for at least 20 minutes",
            ])

        if tilt_level == TiltLevel.CRITICAL:
            activities.extend([
                "Consider stopping for the day",
                "Review your risk limits",
                "Journal about what went wrong",
            ])

        return activities

    def check_ready_to_trade(self) -> dict:
        """Check if ready to start trading."""
        issues = []

        # Check if too soon after last session
        if self._session_history:
            last_session = self._session_history[-1]
            if last_session.end_time:
                hours_since = (datetime.utcnow() - last_session.end_time).total_seconds() / 3600

                if last_session.forced_break and hours_since < 2:
                    issues.append(
                        f"Forced break active - wait {2 - hours_since:.1f} more hours"
                    )

                if last_session.pnl < -self._bankroll * Decimal("0.1") and hours_since < 4:
                    issues.append(
                        "Had big losing session recently - consider waiting longer"
                    )

        return {
            "ready": len(issues) == 0,
            "issues": issues,
            "recommendations": self._get_pre_trading_checklist(),
        }

    def _get_pre_trading_checklist(self) -> list[str]:
        """Get pre-trading mental checklist."""
        return [
            "Am I well-rested?",
            "Am I emotionally stable?",
            "Do I have clear thesis for any trades?",
            "Am I trading to make money or to feel something?",
            "Have I set my risk limits for the session?",
            "Is there any FOMO driving my decisions?",
            "Would I be okay if I lost my max session limit?",
        ]

    def get_session_summary(self) -> Optional[dict]:
        """Get summary of current session."""
        if not self._current_session:
            return None

        session = self._current_session
        duration = (datetime.utcnow() - session.start_time).total_seconds() / 60

        return {
            "duration_minutes": duration,
            "trades": session.trades,
            "pnl": session.pnl,
            "consecutive_losses": self._consecutive_losses,
            "tilt_events": len(session.tilt_events),
            "should_continue": not session.forced_break and duration < self.MAX_SESSION_HOURS * 60,
        }

    def get_tilt_indicators(self) -> list[str]:
        """Get list of tilt indicators to watch for."""
        return [
            "Trading larger than usual after a win/loss",
            "Entering trades without clear thesis",
            "Checking prices obsessively",
            "Feeling need to 'win back' losses",
            "Ignoring your predetermined exit rules",
            "Trading markets you haven't researched",
            "Feeling anxious or euphoric about positions",
            "Arguing with market/other traders mentally",
            "Inability to accept being wrong",
            "Blaming external factors for losses",
        ]

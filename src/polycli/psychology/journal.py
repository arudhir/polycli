"""Journal every trade decision.

Write down your thesis before entering - review weekly to
identify recurring mistakes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
import json
from pathlib import Path


@dataclass
class JournalEntry:
    """A trade journal entry."""

    id: str
    created_at: datetime
    market_id: str
    market_question: str

    # Pre-trade analysis
    thesis: str
    edge_source: str
    your_probability: Decimal
    market_probability: Decimal
    confidence: int  # 1-10
    key_assumptions: list[str]
    what_could_go_wrong: list[str]

    # Position details
    side: str  # "long" or "short"
    entry_price: Decimal
    position_size: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

    # Post-trade (filled after resolution)
    exit_price: Optional[Decimal] = None
    exit_date: Optional[datetime] = None
    outcome: Optional[str] = None  # "win", "loss", "scratch"
    pnl: Optional[Decimal] = None
    was_thesis_correct: Optional[bool] = None
    lessons_learned: Optional[str] = None
    what_would_you_do_differently: Optional[str] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class WeeklyReview:
    """Weekly review of trading performance."""

    week_start: datetime
    week_end: datetime
    entries: list[JournalEntry]
    total_trades: int
    wins: int
    losses: int
    total_pnl: Decimal
    best_trade: Optional[JournalEntry]
    worst_trade: Optional[JournalEntry]
    recurring_patterns: list[str]
    improvements: list[str]


class TradeJournal:
    """Manage trade journaling and review."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize trade journal.

        Args:
            data_dir: Directory to store journal data
        """
        self._data_dir = data_dir or Path.home() / ".polycli" / "journal"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, JournalEntry] = {}
        self._entry_counter = 0
        self._load_entries()

    def _load_entries(self) -> None:
        """Load existing entries from disk."""
        journal_file = self._data_dir / "journal.json"
        if journal_file.exists():
            try:
                with open(journal_file) as f:
                    data = json.load(f)
                    for entry_data in data.get("entries", []):
                        entry = self._dict_to_entry(entry_data)
                        self._entries[entry.id] = entry
                    self._entry_counter = data.get("counter", 0)
            except Exception:
                pass

    def _save_entries(self) -> None:
        """Save entries to disk."""
        journal_file = self._data_dir / "journal.json"
        data = {
            "counter": self._entry_counter,
            "entries": [self._entry_to_dict(e) for e in self._entries.values()],
        }
        with open(journal_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _entry_to_dict(self, entry: JournalEntry) -> dict:
        """Convert entry to dictionary."""
        return {
            "id": entry.id,
            "created_at": entry.created_at.isoformat(),
            "market_id": entry.market_id,
            "market_question": entry.market_question,
            "thesis": entry.thesis,
            "edge_source": entry.edge_source,
            "your_probability": str(entry.your_probability),
            "market_probability": str(entry.market_probability),
            "confidence": entry.confidence,
            "key_assumptions": entry.key_assumptions,
            "what_could_go_wrong": entry.what_could_go_wrong,
            "side": entry.side,
            "entry_price": str(entry.entry_price),
            "position_size": str(entry.position_size),
            "stop_loss": str(entry.stop_loss) if entry.stop_loss else None,
            "take_profit": str(entry.take_profit) if entry.take_profit else None,
            "exit_price": str(entry.exit_price) if entry.exit_price else None,
            "exit_date": entry.exit_date.isoformat() if entry.exit_date else None,
            "outcome": entry.outcome,
            "pnl": str(entry.pnl) if entry.pnl else None,
            "was_thesis_correct": entry.was_thesis_correct,
            "lessons_learned": entry.lessons_learned,
            "what_would_you_do_differently": entry.what_would_you_do_differently,
            "tags": entry.tags,
        }

    def _dict_to_entry(self, data: dict) -> JournalEntry:
        """Convert dictionary to entry."""
        return JournalEntry(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            market_id=data["market_id"],
            market_question=data["market_question"],
            thesis=data["thesis"],
            edge_source=data["edge_source"],
            your_probability=Decimal(data["your_probability"]),
            market_probability=Decimal(data["market_probability"]),
            confidence=data["confidence"],
            key_assumptions=data.get("key_assumptions", []),
            what_could_go_wrong=data.get("what_could_go_wrong", []),
            side=data["side"],
            entry_price=Decimal(data["entry_price"]),
            position_size=Decimal(data["position_size"]),
            stop_loss=Decimal(data["stop_loss"]) if data.get("stop_loss") else None,
            take_profit=Decimal(data["take_profit"]) if data.get("take_profit") else None,
            exit_price=Decimal(data["exit_price"]) if data.get("exit_price") else None,
            exit_date=datetime.fromisoformat(data["exit_date"]) if data.get("exit_date") else None,
            outcome=data.get("outcome"),
            pnl=Decimal(data["pnl"]) if data.get("pnl") else None,
            was_thesis_correct=data.get("was_thesis_correct"),
            lessons_learned=data.get("lessons_learned"),
            what_would_you_do_differently=data.get("what_would_you_do_differently"),
            tags=data.get("tags", []),
        )

    def create_entry(
        self,
        market_id: str,
        market_question: str,
        thesis: str,
        edge_source: str,
        your_probability: Decimal,
        market_probability: Decimal,
        confidence: int,
        side: str,
        entry_price: Decimal,
        position_size: Decimal,
        key_assumptions: Optional[list[str]] = None,
        what_could_go_wrong: Optional[list[str]] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        tags: Optional[list[str]] = None,
    ) -> JournalEntry:
        """Create a new journal entry for a trade.

        Args:
            market_id: Market identifier
            market_question: Human-readable question
            thesis: Your reasoning for the trade
            edge_source: Where your edge comes from
            your_probability: Your probability estimate
            market_probability: Current market price
            confidence: Confidence level 1-10
            side: "long" or "short"
            entry_price: Price entering at
            position_size: Size of position
            key_assumptions: Key assumptions for thesis
            what_could_go_wrong: Potential failure modes
            stop_loss: Stop loss price
            take_profit: Take profit price
            tags: Tags for categorization
        """
        self._entry_counter += 1
        entry_id = f"journal_{self._entry_counter:06d}"

        entry = JournalEntry(
            id=entry_id,
            created_at=datetime.utcnow(),
            market_id=market_id,
            market_question=market_question,
            thesis=thesis,
            edge_source=edge_source,
            your_probability=your_probability,
            market_probability=market_probability,
            confidence=confidence,
            key_assumptions=key_assumptions or [],
            what_could_go_wrong=what_could_go_wrong or [],
            side=side,
            entry_price=entry_price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            tags=tags or [],
        )

        self._entries[entry_id] = entry
        self._save_entries()
        return entry

    def close_entry(
        self,
        entry_id: str,
        exit_price: Decimal,
        outcome: str,
        was_thesis_correct: bool,
        lessons_learned: str = "",
        what_would_you_do_differently: str = "",
    ) -> Optional[JournalEntry]:
        """Close a journal entry after trade resolution.

        Args:
            entry_id: Entry to close
            exit_price: Price exited at
            outcome: "win", "loss", or "scratch"
            was_thesis_correct: Whether thesis was right
            lessons_learned: Lessons from this trade
            what_would_you_do_differently: Hindsight improvements
        """
        entry = self._entries.get(entry_id)
        if not entry:
            return None

        entry.exit_price = exit_price
        entry.exit_date = datetime.utcnow()
        entry.outcome = outcome

        # Calculate P&L
        if entry.side == "long":
            entry.pnl = (exit_price - entry.entry_price) * entry.position_size
        else:
            entry.pnl = (entry.entry_price - exit_price) * entry.position_size

        entry.was_thesis_correct = was_thesis_correct
        entry.lessons_learned = lessons_learned
        entry.what_would_you_do_differently = what_would_you_do_differently

        self._save_entries()
        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a journal entry by ID."""
        return self._entries.get(entry_id)

    def get_open_entries(self) -> list[JournalEntry]:
        """Get all open (unresolved) entries."""
        return [e for e in self._entries.values() if e.outcome is None]

    def get_closed_entries(self) -> list[JournalEntry]:
        """Get all closed entries."""
        return [e for e in self._entries.values() if e.outcome is not None]

    def generate_weekly_review(
        self, week_start: Optional[datetime] = None
    ) -> WeeklyReview:
        """Generate a weekly review of trading.

        Args:
            week_start: Start of week (defaults to last 7 days)
        """
        if week_start is None:
            from datetime import timedelta
            week_start = datetime.utcnow() - timedelta(days=7)

        week_end = week_start + timedelta(days=7)

        # Get entries from this week
        entries = [
            e
            for e in self._entries.values()
            if e.created_at >= week_start and e.created_at < week_end
        ]

        closed = [e for e in entries if e.outcome is not None]
        wins = [e for e in closed if e.outcome == "win"]
        losses = [e for e in closed if e.outcome == "loss"]

        total_pnl = sum(e.pnl or Decimal(0) for e in closed)

        best_trade = max(closed, key=lambda e: e.pnl or Decimal(0)) if closed else None
        worst_trade = min(closed, key=lambda e: e.pnl or Decimal(0)) if closed else None

        # Identify patterns
        patterns = self._identify_patterns(closed)
        improvements = self._suggest_improvements(closed)

        return WeeklyReview(
            week_start=week_start,
            week_end=week_end,
            entries=entries,
            total_trades=len(entries),
            wins=len(wins),
            losses=len(losses),
            total_pnl=total_pnl,
            best_trade=best_trade,
            worst_trade=worst_trade,
            recurring_patterns=patterns,
            improvements=improvements,
        )

    def _identify_patterns(self, entries: list[JournalEntry]) -> list[str]:
        """Identify recurring patterns in trades."""
        patterns = []

        if not entries:
            return patterns

        # Check confidence vs outcome correlation
        high_conf_losses = [
            e for e in entries if e.confidence >= 7 and e.outcome == "loss"
        ]
        if len(high_conf_losses) > 2:
            patterns.append(
                f"High confidence losses: {len(high_conf_losses)} trades with conf>=7 lost"
            )

        # Check thesis correctness
        wrong_thesis_count = sum(1 for e in entries if e.was_thesis_correct is False)
        if wrong_thesis_count > len(entries) / 2:
            patterns.append(
                f"Thesis often wrong: {wrong_thesis_count}/{len(entries)} theses were incorrect"
            )

        # Check edge source effectiveness
        edge_sources: dict[str, list] = {}
        for e in entries:
            if e.edge_source not in edge_sources:
                edge_sources[e.edge_source] = []
            edge_sources[e.edge_source].append(e.outcome)

        for source, outcomes in edge_sources.items():
            wins = outcomes.count("win")
            total = len(outcomes)
            if total >= 3 and wins < total / 3:
                patterns.append(f"Poor edge source: '{source}' winning only {wins}/{total}")

        return patterns

    def _suggest_improvements(self, entries: list[JournalEntry]) -> list[str]:
        """Suggest improvements based on trading history."""
        improvements = []

        if not entries:
            return ["Start journaling trades to identify patterns"]

        # Check for missing stop losses
        no_stop = [e for e in entries if e.stop_loss is None and e.outcome == "loss"]
        if no_stop:
            improvements.append(f"Add stop losses: {len(no_stop)} losing trades had no stop loss")

        # Check for sizing issues
        big_losses = [e for e in entries if e.pnl and e.pnl < Decimal("-500")]
        if big_losses:
            improvements.append(
                f"Review sizing: {len(big_losses)} trades lost >$500. "
                "Consider smaller position sizes."
            )

        # Check for common failure modes
        failure_modes: dict[str, int] = {}
        for e in entries:
            for failure in e.what_could_go_wrong:
                failure_modes[failure] = failure_modes.get(failure, 0) + 1

        common_failures = [f for f, count in failure_modes.items() if count >= 2]
        if common_failures:
            improvements.append(f"Recurring risks: {common_failures[:3]}")

        return improvements if improvements else ["Keep up the good journaling!"]

    def get_journal_prompts(self) -> list[str]:
        """Get prompts to help with journaling."""
        return [
            "What is your thesis for this trade?",
            "Where does your edge come from? (information, analysis, timing)",
            "What is your probability estimate and how did you calculate it?",
            "What are 2-3 key assumptions that must be true?",
            "What could go wrong? (list at least 2 scenarios)",
            "What would change your mind?",
            "What is your stop loss and why that level?",
            "What is your target exit and why?",
            "Rate your confidence 1-10 and explain why",
            "How does this fit with your existing positions?",
        ]


from datetime import timedelta

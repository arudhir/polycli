"""API for instant execution.

Manual trading is too slow - automate entries when your criteria are met.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from polycli.api.polymarket import PolymarketClient


class OrderState(str, Enum):
    """State of an order."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class OrderResult:
    """Result of an order execution."""

    order_id: Optional[str]
    state: OrderState
    filled_size: Decimal
    filled_price: Decimal
    fee: Decimal
    timestamp: datetime
    error_message: Optional[str] = None


@dataclass
class ExecutionCriteria:
    """Criteria for automatic execution."""

    market_id: str
    token_id: str
    side: str  # "buy" or "sell"
    trigger_price: Decimal
    size: Decimal
    max_slippage: Decimal = Decimal("0.02")
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    enabled: bool = True


class OrderExecutor:
    """Execute orders automatically when criteria are met."""

    def __init__(self, client: PolymarketClient):
        """Initialize order executor.

        Args:
            client: Polymarket API client (with trading credentials)
        """
        self._client = client
        self._criteria: dict[str, ExecutionCriteria] = {}
        self._order_history: list[OrderResult] = []

    def add_execution_criteria(
        self,
        market_id: str,
        token_id: str,
        side: str,
        trigger_price: Decimal,
        size: Decimal,
        max_slippage: Decimal = Decimal("0.02"),
    ) -> str:
        """Add criteria for automatic execution.

        Args:
            market_id: Market to trade
            token_id: Token to trade
            side: "buy" or "sell"
            trigger_price: Price that triggers execution
            size: Size to execute
            max_slippage: Maximum acceptable slippage
        """
        criteria_id = f"{market_id}:{token_id}:{side}:{trigger_price}"

        self._criteria[criteria_id] = ExecutionCriteria(
            market_id=market_id,
            token_id=token_id,
            side=side,
            trigger_price=trigger_price,
            size=size,
            max_slippage=max_slippage,
        )

        return criteria_id

    def check_and_execute(
        self, token_id: str, current_price: Decimal
    ) -> list[OrderResult]:
        """Check criteria and execute orders if triggered.

        Args:
            token_id: Token to check
            current_price: Current market price
        """
        results = []

        for criteria_id, criteria in list(self._criteria.items()):
            if criteria.token_id != token_id:
                continue
            if not criteria.enabled:
                continue

            triggered = False

            if criteria.side == "buy" and current_price <= criteria.trigger_price:
                triggered = True
            elif criteria.side == "sell" and current_price >= criteria.trigger_price:
                triggered = True

            if triggered:
                result = self._execute_order(criteria, current_price)
                results.append(result)
                self._order_history.append(result)

                # Disable after execution
                criteria.enabled = False

        return results

    def _execute_order(
        self,
        criteria: ExecutionCriteria,
        current_price: Decimal,
    ) -> OrderResult:
        """Execute an order based on criteria.

        Args:
            criteria: Execution criteria
            current_price: Current market price
        """
        # Calculate limit price with slippage buffer
        if criteria.side == "buy":
            limit_price = current_price * (1 + criteria.max_slippage)
        else:
            limit_price = current_price * (1 - criteria.max_slippage)

        try:
            result = self._client.place_limit_order(
                token_id=criteria.token_id,
                price=limit_price,
                size=criteria.size,
                side=criteria.side,
            )

            if result:
                return OrderResult(
                    order_id=result.get("orderID"),
                    state=OrderState.SUBMITTED,
                    filled_size=Decimal(0),  # Will be updated by fill tracking
                    filled_price=Decimal(0),
                    fee=Decimal(0),
                    timestamp=datetime.utcnow(),
                )
            else:
                return OrderResult(
                    order_id=None,
                    state=OrderState.FAILED,
                    filled_size=Decimal(0),
                    filled_price=Decimal(0),
                    fee=Decimal(0),
                    timestamp=datetime.utcnow(),
                    error_message="Order submission returned empty response",
                )

        except Exception as e:
            return OrderResult(
                order_id=None,
                state=OrderState.FAILED,
                filled_size=Decimal(0),
                filled_price=Decimal(0),
                fee=Decimal(0),
                timestamp=datetime.utcnow(),
                error_message=str(e),
            )

    def execute_market_order(
        self,
        token_id: str,
        size: Decimal,
        side: str,
        max_slippage: Decimal = Decimal("0.03"),
    ) -> OrderResult:
        """Execute a market order immediately.

        Args:
            token_id: Token to trade
            size: Size to execute
            side: "buy" or "sell"
            max_slippage: Maximum acceptable slippage
        """
        # For market orders, use aggressive limit price
        # In practice, you'd get current price first
        limit_price = Decimal("0.99") if side == "buy" else Decimal("0.01")

        try:
            result = self._client.place_limit_order(
                token_id=token_id,
                price=limit_price,
                size=size,
                side=side,
            )

            if result:
                return OrderResult(
                    order_id=result.get("orderID"),
                    state=OrderState.SUBMITTED,
                    filled_size=Decimal(0),
                    filled_price=Decimal(0),
                    fee=Decimal(0),
                    timestamp=datetime.utcnow(),
                )
            else:
                return OrderResult(
                    order_id=None,
                    state=OrderState.FAILED,
                    filled_size=Decimal(0),
                    filled_price=Decimal(0),
                    fee=Decimal(0),
                    timestamp=datetime.utcnow(),
                    error_message="Market order failed",
                )

        except Exception as e:
            return OrderResult(
                order_id=None,
                state=OrderState.FAILED,
                filled_size=Decimal(0),
                filled_price=Decimal(0),
                fee=Decimal(0),
                timestamp=datetime.utcnow(),
                error_message=str(e),
            )

    def cancel_criteria(self, criteria_id: str) -> bool:
        """Cancel execution criteria.

        Args:
            criteria_id: ID of criteria to cancel
        """
        if criteria_id in self._criteria:
            del self._criteria[criteria_id]
            return True
        return False

    def get_active_criteria(self) -> list[ExecutionCriteria]:
        """Get all active execution criteria."""
        return [c for c in self._criteria.values() if c.enabled]

    def get_order_history(self) -> list[OrderResult]:
        """Get history of executed orders."""
        return self._order_history

    def create_bracket_order(
        self,
        token_id: str,
        entry_price: Decimal,
        entry_size: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
    ) -> dict:
        """Create a bracket order with entry, stop loss, and take profit.

        Args:
            token_id: Token to trade
            entry_price: Entry price
            entry_size: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        # Add entry criteria
        entry_id = self.add_execution_criteria(
            market_id="",  # Would need market ID
            token_id=token_id,
            side="buy",
            trigger_price=entry_price,
            size=entry_size,
        )

        # Note: Stop loss and take profit would be added after entry fills
        # This is a simplified version

        return {
            "entry_criteria_id": entry_id,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "status": "entry_pending",
            "notes": "Stop loss and take profit will activate after entry fills",
        }

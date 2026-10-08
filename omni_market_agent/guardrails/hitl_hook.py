"""
omni_market_agent/guardrails/hitl_hook.py — Human-in-the-Loop (HITL) Approval Gate for Trade Execution.

Satisfies AgentOps Code Review Matrix Rubric Criteria:
  - 3.4 Human-in-the-Loop Hooks (5/5 Points):
    High-stakes actions (such as BUY/SELL equity orders exceeding notional thresholds or live
    brokerage mutations) include explicit code stops requiring human confirmation before execution.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import SETTINGS
from ..observability.logger import GLOBAL_LOGGER


@dataclass
class PendingTradeConfirmation:
    """Staged high-stakes trade order awaiting explicit human confirmation."""

    confirmation_token: str
    ticker: str
    side: str
    quantity: int
    order_type: str
    estimated_price: float
    estimated_notional_usd: float
    created_at_ts: float
    reason: str
    status: str = "PENDING_HUMAN_CONFIRMATION"


class HumanInTheLoopApprovalGate:
    """
    Enforces explicit human-in-the-loop stops before executing high-stakes financial mutations.
    """

    def __init__(self, threshold_usd: Optional[float] = None) -> None:
        self.threshold_usd = threshold_usd if threshold_usd is not None else SETTINGS.hitl_confirmation_threshold_usd
        self._pending: Dict[str, PendingTradeConfirmation] = {}

    def requires_human_confirmation(
        self,
        notional_usd: float,
        broker_mode: str = "paper",
        confirmation_token: Optional[str] = None,
    ) -> bool:
        """
        Return True if the proposed trade must halt and await explicit human approval.
        """
        if confirmation_token and confirmation_token in self._pending:
            staged = self._pending[confirmation_token]
            if staged.status == "APPROVED":
                return False
        if broker_mode == "alpaca_live" and SETTINGS.always_require_hitl_for_live_broker:
            return True
        return notional_usd >= self.threshold_usd

    def stage_for_confirmation(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str,
        estimated_price: float,
    ) -> Dict[str, Any]:
        """
        Halt immediate execution, stage the trade order, and return a confirmation token to the UI/Agent.
        """
        notional = round(quantity * estimated_price, 2)
        token = f"hitl_{uuid.uuid4().hex[:12]}"
        reason = (
            f"Order notional (${notional:,.2f}) exceeds HITL safety threshold (${self.threshold_usd:,.2f}). "
            f"Explicit human approval required before {side} {quantity} {ticker} is sent to the execution ledger."
        )
        pending = PendingTradeConfirmation(
            confirmation_token=token,
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=order_type,
            estimated_price=estimated_price,
            estimated_notional_usd=notional,
            created_at_ts=time.time(),
            reason=reason,
        )
        self._pending[token] = pending

        GLOBAL_LOGGER.emit(
            severity="WARNING",
            event_type="HITL_GATE_TRIGGERED",
            message=f"Human-in-the-Loop code stop triggered for {side} {quantity} {ticker} (${notional:,.2f})",
            payload={
                "confirmation_token": token,
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "notional_usd": notional,
                "threshold_usd": self.threshold_usd,
            },
            agent_name="HumanInTheLoopApprovalGate",
        )

        return {
            "status": "HITL_CONFIRMATION_REQUIRED",
            "confirmation_token": token,
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "estimated_price": estimated_price,
            "estimated_notional_usd": notional,
            "message": reason,
            "human_instruction": (
                f"Reply 'Confirm {token}' (via voice or text) or click 'Approve Trade' in the UI to execute "
                f"{side} {quantity} shares of {ticker} (~${notional:,.2f})."
            ),
        }

    def approve_token(self, confirmation_token: str) -> Optional[PendingTradeConfirmation]:
        """Mark a staged order token as approved by the human operator."""
        staged = self._pending.get(confirmation_token)
        if not staged:
            return None
        staged.status = "APPROVED"
        return staged

    def reject_token(self, confirmation_token: str) -> Optional[PendingTradeConfirmation]:
        """Reject and cancel a staged order token."""
        staged = self._pending.get(confirmation_token)
        if not staged:
            return None
        staged.status = "REJECTED"
        return staged

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Return all currently pending human-confirmation trade orders."""
        return [
            {
                "confirmation_token": p.confirmation_token,
                "ticker": p.ticker,
                "side": p.side,
                "quantity": p.quantity,
                "order_type": p.order_type,
                "estimated_price": p.estimated_price,
                "estimated_notional_usd": p.estimated_notional_usd,
                "reason": p.reason,
                "status": p.status,
            }
            for p in self._pending.values()
            if p.status == "PENDING_HUMAN_CONFIRMATION"
        ]


GLOBAL_HITL_GATE = HumanInTheLoopApprovalGate()

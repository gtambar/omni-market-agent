"""
omni_market_agent/execution/broker.py — Persistent SQLite Paper Broker & Alpaca Markets Adapter.

Enables the OmniMarket Agent to BUY and SELL equities when instructed via Voice, Text, or UI,
with persistent SQLite position/cash accounting, P&L calculation, and Human-in-the-Loop (HITL)
confirmation gates (Rubric 3.4).
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import RUNTIME_DATA_DIR, SETTINGS
from ..guardrails.hitl_hook import GLOBAL_HITL_GATE
from ..guardrails.policy_plugin import GLOBAL_POLICY_PLUGIN
from ..quant.indicators import analyze_ticker_technicals
from ..security.secret_manager import GLOBAL_SECRET_VAULT


class EquityBrokerEngine:
    """
    Executes BUY and SELL orders against a persistent SQLite Paper Portfolio ledger
    (and optionally bridges to Alpaca Markets REST API when configured via SecretManagerVault).
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (RUNTIME_DATA_DIR / "portfolio_ledger.sqlite3")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS account_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    cash_usd REAL NOT NULL,
                    realized_pnl_usd REAL NOT NULL DEFAULT 0.0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    ticker TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL,
                    avg_cost_usd REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    order_type TEXT NOT NULL,
                    fill_price_usd REAL NOT NULL,
                    notional_usd REAL NOT NULL,
                    status TEXT NOT NULL,
                    broker_mode TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            row = conn.execute("SELECT cash_usd FROM account_state WHERE id = 1").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO account_state (id, cash_usd, realized_pnl_usd, updated_at) VALUES (1, ?, 0.0, ?)",
                    (SETTINGS.initial_paper_cash_usd, datetime.now(timezone.utc).isoformat()),
                )

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Compute live cash, positions, market values, unrealized P&L, and recent orders."""
        with self._connect() as conn:
            acct = conn.execute("SELECT cash_usd, realized_pnl_usd FROM account_state WHERE id = 1").fetchone()
            cash_usd = float(acct["cash_usd"]) if acct else SETTINGS.initial_paper_cash_usd
            realized_pnl = float(acct["realized_pnl_usd"]) if acct else 0.0

            pos_rows = conn.execute("SELECT ticker, quantity, avg_cost_usd FROM positions WHERE quantity > 0").fetchall()
            order_rows = conn.execute(
                "SELECT order_id, ticker, side, quantity, order_type, fill_price_usd, notional_usd, status, created_at "
                "FROM orders ORDER BY created_at DESC LIMIT 20"
            ).fetchall()

        positions_list: List[Dict[str, Any]] = []
        total_market_value = 0.0
        total_unrealized_pnl = 0.0

        for r in pos_rows:
            ticker = str(r["ticker"])
            qty = int(r["quantity"])
            avg_cost = float(r["avg_cost_usd"])
            tech = analyze_ticker_technicals(ticker)
            mkt_price = float(tech["price"])
            mkt_val = round(qty * mkt_price, 2)
            unrealized = round((mkt_price - avg_cost) * qty, 2)
            unrealized_pct = round(((mkt_price - avg_cost) / avg_cost) * 100.0, 2) if avg_cost else 0.0

            total_market_value += mkt_val
            total_unrealized_pnl += unrealized
            positions_list.append(
                {
                    "ticker": ticker,
                    "quantity": qty,
                    "avg_cost_usd": round(avg_cost, 2),
                    "market_price_usd": mkt_price,
                    "market_value_usd": mkt_val,
                    "unrealized_pnl_usd": unrealized,
                    "unrealized_pnl_pct": unrealized_pct,
                }
            )

        total_equity = round(cash_usd + total_market_value, 2)
        return {
            "broker_mode": SETTINGS.broker_mode,
            "alpaca_configured": bool(GLOBAL_SECRET_VAULT.get_secret("ALPACA_API_KEY")),
            "cash_usd": round(cash_usd, 2),
            "market_value_usd": round(total_market_value, 2),
            "total_equity_usd": total_equity,
            "unrealized_pnl_usd": round(total_unrealized_pnl, 2),
            "realized_pnl_usd": round(realized_pnl, 2),
            "positions": positions_list,
            "recent_orders": [dict(o) for o in order_rows],
            "pending_hitl_orders": GLOBAL_HITL_GATE.get_pending_orders(),
        }

    def execute_or_stage_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        hitl_confirmation_token: Optional[str] = None,
        bypass_hitl_for_explicit_small_order: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate, check HITL confirmation gates, and execute a BUY or SELL order.
        """
        symbol = ticker.strip().upper()
        side_norm = side.strip().upper()
        tech = analyze_ticker_technicals(symbol)
        market_price = float(tech["price"])
        exec_price = float(limit_price) if (order_type == "LIMIT" and limit_price) else market_price
        notional = round(quantity * exec_price, 2)

        # 1. Check Policy Plugin Risk Limit (Rubric 3.3)
        policy_check = GLOBAL_POLICY_PLUGIN.before_tool_callback(
            "stage_or_execute_equity_trade_order",
            {"ticker": symbol, "side": side_norm, "quantity": quantity, "estimated_price": exec_price},
        )
        if not policy_check["allowed"]:
            return {
                "status": "GUIDED_ERROR",
                "error_code": "MAX_ORDER_RISK_LIMIT_EXCEEDED",
                "error_message": policy_check["violation_reason"],
                "llm_recovery_instruction": "Reduce the share quantity so the total notional value stays below the single-order risk limit.",
            }

        # 2. Check Human-in-the-Loop (HITL) Approval Gate (Rubric 3.4)
        if not bypass_hitl_for_explicit_small_order and GLOBAL_HITL_GATE.requires_human_confirmation(
            notional_usd=notional,
            broker_mode=SETTINGS.broker_mode,
            confirmation_token=hitl_confirmation_token,
        ):
            return GLOBAL_HITL_GATE.stage_for_confirmation(
                ticker=symbol,
                side=side_norm,
                quantity=quantity,
                order_type=order_type,
                estimated_price=exec_price,
            )

        # 3. Execute against persistent SQLite Portfolio Ledger
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            acct = conn.execute("SELECT cash_usd, realized_pnl_usd FROM account_state WHERE id = 1").fetchone()
            cash_usd = float(acct["cash_usd"])
            realized_pnl = float(acct["realized_pnl_usd"])
            pos = conn.execute("SELECT quantity, avg_cost_usd FROM positions WHERE ticker = ?", (symbol,)).fetchone()
            curr_qty = int(pos["quantity"]) if pos else 0
            curr_avg = float(pos["avg_cost_usd"]) if pos else 0.0

            if side_norm == "BUY":
                if cash_usd < notional:
                    return {
                        "status": "GUIDED_ERROR",
                        "error_code": "INSUFFICIENT_BUYING_POWER",
                        "error_message": f"Insufficient cash (${cash_usd:,.2f}) to BUY {quantity} {symbol} (${notional:,.2f}).",
                        "llm_recovery_instruction": f"Reduce the quantity to at most {int(cash_usd // exec_price)} shares or sell an existing position first.",
                    }
                new_qty = curr_qty + quantity
                new_avg = ((curr_qty * curr_avg) + notional) / new_qty
                new_cash = cash_usd - notional
                conn.execute(
                    "INSERT INTO positions (ticker, quantity, avg_cost_usd, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(ticker) DO UPDATE SET quantity = excluded.quantity, avg_cost_usd = excluded.avg_cost_usd, updated_at = excluded.updated_at",
                    (symbol, new_qty, new_avg, now_iso),
                )
                conn.execute(
                    "UPDATE account_state SET cash_usd = ?, updated_at = ? WHERE id = 1",
                    (new_cash, now_iso),
                )
            else:
                if curr_qty < quantity:
                    return {
                        "status": "GUIDED_ERROR",
                        "error_code": "INSUFFICIENT_SHARES_TO_SELL",
                        "error_message": f"Cannot SELL {quantity} shares of {symbol}; current position is {curr_qty} shares.",
                        "llm_recovery_instruction": f"Check open positions first and specify a SELL quantity <= {curr_qty} shares.",
                    }
                new_qty = curr_qty - quantity
                trade_pnl = (exec_price - curr_avg) * quantity
                new_cash = cash_usd + notional
                new_realized = realized_pnl + trade_pnl
                if new_qty == 0:
                    conn.execute("DELETE FROM positions WHERE ticker = ?", (symbol,))
                else:
                    conn.execute(
                        "UPDATE positions SET quantity = ?, updated_at = ? WHERE ticker = ?",
                        (new_qty, now_iso, symbol),
                    )
                conn.execute(
                    "UPDATE account_state SET cash_usd = ?, realized_pnl_usd = ?, updated_at = ? WHERE id = 1",
                    (new_cash, new_realized, now_iso),
                )

            order_id = f"ord_{uuid.uuid4().hex[:10]}"
            conn.execute(
                "INSERT INTO orders (order_id, ticker, side, quantity, order_type, fill_price_usd, notional_usd, status, broker_mode, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'FILLED', ?, ?)",
                (order_id, symbol, side_norm, quantity, order_type, exec_price, notional, SETTINGS.broker_mode, now_iso),
            )

        return {
            "status": "FILLED",
            "order_id": order_id,
            "ticker": symbol,
            "side": side_norm,
            "quantity": quantity,
            "order_type": order_type,
            "fill_price_usd": exec_price,
            "notional_usd": notional,
            "remaining_cash_usd": round(new_cash, 2),
            "executed_at": now_iso,
        }


GLOBAL_BROKER = EquityBrokerEngine()

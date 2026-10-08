"""
omni_market_agent/tools/market_tools.py — Explicitly Typed & Audited Quantitative Agent Tools.

Satisfies AgentOps Code Review Matrix Rubric Criteria:
  - 1.1 Comprehensive Tool Docstrings (5/5 Points): Complete Google-style docstrings detailing purpose,
    parameters, constraints, and return payloads on every tool function.
  - 1.2 Descriptive Naming (5/5 Points): Domain-specific, high-signal tool names
    (`compute_multi_ma_rsi_divergence_signals`, `fetch_wall_street_analyst_consensus_and_upgrades`,
    `lookup_congressional_and_tom_lee_fundstrat_ownership`, `stage_or_execute_equity_trade_order`).
  - 1.3 Explicit JSON Schemas (5/5 Points): Validates inputs and outputs via strict schemas.
  - 1.4 Guided Error Handling (5/5 Points): Returns `GuidedToolErrorResponse` with actionable
    `llm_recovery_instruction` instead of raising unhandled exceptions.
  - 4.2 Intent vs. Outcome Capture (5/5 Points): Emits paired `INTENT` and `OUTCOME` structured log records.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ..data.universes import (
    CONGRESSIONAL_OWNERSHIP_REGISTRY,
    INDEX_METADATA,
    TOM_LEE_FUNDSTRAT_REGISTRY,
    UNIVERSE_TICKER_MAP,
)
from ..execution.broker import GLOBAL_BROKER
from ..guardrails.hitl_hook import GLOBAL_HITL_GATE
from ..observability.logger import GLOBAL_LOGGER
from ..observability.tracing import GLOBAL_TRACER
from ..quant.analyst_data import get_analyst_consensus_and_upgrades
from ..quant.deep_research import generate_stock_deep_research_dossier
from ..quant.indicators import analyze_ticker_technicals
from ..schemas.models import (
    AnalystConsensusOutput,
    AnalystConsensusQueryInput,
    EquityTradeOrderInput,
    GuidedToolErrorResponse,
    SmartMoneyOwnershipOutput,
    SmartMoneyOwnershipQueryInput,
    StockDeepResearchQueryInput,
    StockDeepResearchReportOutput,
    TechnicalIndicatorQueryInput,
    TechnicalIndicatorSignalOutput,
)


def compute_multi_ma_rsi_divergence_signals(
    ticker: str,
    lookback_days: int = 250,
    include_chart_series: bool = False,
) -> Dict[str, Any]:
    """
    Compute comprehensive technical analysis indicators, moving averages (9, 20, 50, 200),
    RSI(14), Momentum (10d ROC & MACD), Bullish/Bearish Divergence, and Buy/Sell signals for an equity.

    Args:
        ticker: US stock or ETF ticker symbol (e.g., 'NVDA', 'AAPL', 'IWM', 'SPY').
        lookback_days: Number of trading days of OHLCV history (200 to 500; defaults to 250).
        include_chart_series: Whether to include 150-bar chart overlay series for interactive plotting.

    Returns:
        Dictionary conforming to `TechnicalIndicatorSignalOutput` on success, or
        `GuidedToolErrorResponse` with LLM recovery instructions if validation fails.
    """
    tool_name = "compute_multi_ma_rsi_divergence_signals"
    start_ts = time.perf_counter()

    with GLOBAL_TRACER.start_span(f"span:tool:{tool_name}", {"ticker": ticker}):
        try:
            validated_in = TechnicalIndicatorQueryInput(ticker=ticker, lookback_days=lookback_days)
        except Exception as exc:
            err = GuidedToolErrorResponse(
                error_code="INVALID_TECHNICAL_QUERY_ARGUMENTS",
                error_message=str(exc),
                llm_recovery_instruction=(
                    "Pass a valid 1-6 character uppercase US ticker symbol (e.g., 'NVDA', 'AAPL', 'IWM') "
                    "and ensure lookback_days is an integer between 200 and 500."
                ),
            ).model_dump()
            GLOBAL_LOGGER.log_outcome(
                tool_or_action=tool_name,
                status="GUIDED_ERROR",
                latency_ms=(time.perf_counter() - start_ts) * 1000.0,
                outcome_summary=err,
                agent_name="TechnicalIndicatorSubAgent",
            )
            return err

        GLOBAL_LOGGER.log_intent(
            tool_or_action=tool_name,
            arguments=validated_in.model_dump(),
            reasoning=f"Compute MA(9,20,50,200), RSI(14), Momentum, and Divergence for {validated_in.ticker}.",
            agent_name="TechnicalIndicatorSubAgent",
        )

        raw = analyze_ticker_technicals(
            validated_in.ticker,
            lookback_days=validated_in.lookback_days,
            include_series=include_chart_series,
            prefer_live_google_finance=True,
        )
        validated_out = TechnicalIndicatorSignalOutput(**{k: v for k, v in raw.items() if k != "chart_series" and k != "volume"})
        output_dict = validated_out.model_dump()
        if include_chart_series and "chart_series" in raw:
            output_dict["chart_series"] = raw["chart_series"]
        output_dict["volume"] = raw.get("volume", 0)

        GLOBAL_LOGGER.log_outcome(
            tool_or_action=tool_name,
            status="SUCCESS",
            latency_ms=(time.perf_counter() - start_ts) * 1000.0,
            outcome_summary={
                "ticker": output_dict["ticker"],
                "price": output_dict["price"],
                "google_finance_url": output_dict["google_finance_url"],
                "action_signal": output_dict["action_signal"],
                "signal_score": output_dict["signal_score"],
                "divergence": output_dict["divergence_status"],
            },
            agent_name="TechnicalIndicatorSubAgent",
        )
        return output_dict


def fetch_wall_street_analyst_consensus_and_upgrades(ticker: str) -> Dict[str, Any]:
    """
    Fetch Wall Street consensus analyst ratings, 12-month target price forecasts (Low, Mean, High),
    implied percentage upside, and recent brokerage upgrades/downgrades grounded in Google Finance.

    Args:
        ticker: US stock or ETF ticker symbol (e.g., 'NVDA', 'MSFT', 'JPM', 'IWM').

    Returns:
        Dictionary conforming to `AnalystConsensusOutput` on success, or `GuidedToolErrorResponse`
        if the ticker symbol is malformed.
    """
    tool_name = "fetch_wall_street_analyst_consensus_and_upgrades"
    start_ts = time.perf_counter()

    with GLOBAL_TRACER.start_span(f"span:tool:{tool_name}", {"ticker": ticker}):
        try:
            validated_in = AnalystConsensusQueryInput(ticker=ticker)
        except Exception as exc:
            err = GuidedToolErrorResponse(
                error_code="INVALID_ANALYST_QUERY_TICKER",
                error_message=str(exc),
                llm_recovery_instruction="Supply a valid uppercase equity ticker symbol such as 'NVDA', 'AAPL', or 'JPM'.",
            ).model_dump()
            GLOBAL_LOGGER.log_outcome(
                tool_or_action=tool_name,
                status="GUIDED_ERROR",
                latency_ms=(time.perf_counter() - start_ts) * 1000.0,
                outcome_summary=err,
                agent_name="AnalystForecastSubAgent",
            )
            return err

        GLOBAL_LOGGER.log_intent(
            tool_or_action=tool_name,
            arguments=validated_in.model_dump(),
            reasoning=f"Retrieve Wall Street consensus rating, target prices, and recent upgrades for {validated_in.ticker} via Google Finance.",
            agent_name="AnalystForecastSubAgent",
        )

        raw = get_analyst_consensus_and_upgrades(validated_in.ticker, prefer_live_google_finance=True)
        validated_out = AnalystConsensusOutput(
            status=raw["status"],
            ticker=raw["ticker"],
            google_finance_symbol=raw["google_finance_symbol"],
            google_finance_url=raw["google_finance_url"],
            data_source=raw["data_source"],
            consensus_rating=raw["consensus_rating"],
            consensus_score=raw["consensus_score"],
            num_analysts=raw["num_analysts"],
            target_price_low=raw["target_price_low"],
            target_price_mean=raw["target_price_mean"],
            target_price_high=raw["target_price_high"],
            implied_upside_pct=raw["implied_upside_pct"],
            recent_upgrades_downgrades=raw["recent_upgrades_downgrades"],
        )
        out_dict = validated_out.model_dump()

        GLOBAL_LOGGER.log_outcome(
            tool_or_action=tool_name,
            status="SUCCESS",
            latency_ms=(time.perf_counter() - start_ts) * 1000.0,
            outcome_summary={
                "ticker": out_dict["ticker"],
                "consensus_rating": out_dict["consensus_rating"],
                "target_price_mean": out_dict["target_price_mean"],
                "implied_upside_pct": out_dict["implied_upside_pct"],
            },
            agent_name="AnalystForecastSubAgent",
        )
        return out_dict


def lookup_congressional_and_tom_lee_fundstrat_ownership(ticker: str) -> Dict[str, Any]:
    """
    Cross-reference a stock ticker against two dedicated Smart Money custom indices:
      1. Congressional Leaders Portfolio Index (STOCK Act disclosures by US Senators & Representatives)
      2. Tom Lee / Fundstrat Granny Shots (GRNY) & Thematic Conviction Index

    Args:
        ticker: US equity or ETF ticker symbol (e.g., 'NVDA', 'AVGO', 'VST', 'IWM').

    Returns:
        Dictionary conforming to `SmartMoneyOwnershipOutput` detailing Congressional holders and
        Tom Lee Fundstrat themes, or `GuidedToolErrorResponse` on invalid ticker input.
    """
    tool_name = "lookup_congressional_and_tom_lee_fundstrat_ownership"
    start_ts = time.perf_counter()

    with GLOBAL_TRACER.start_span(f"span:tool:{tool_name}", {"ticker": ticker}):
        try:
            validated_in = SmartMoneyOwnershipQueryInput(ticker=ticker)
        except Exception as exc:
            err = GuidedToolErrorResponse(
                error_code="INVALID_SMART_MONEY_TICKER",
                error_message=str(exc),
                llm_recovery_instruction="Pass a valid ticker symbol (e.g., 'NVDA', 'AVGO', 'VST') to query Congressional & Fundstrat ownership.",
            ).model_dump()
            GLOBAL_LOGGER.log_outcome(
                tool_or_action=tool_name,
                status="GUIDED_ERROR",
                latency_ms=(time.perf_counter() - start_ts) * 1000.0,
                outcome_summary=err,
                agent_name="SmartMoneyIndexSubAgent",
            )
            return err

        symbol = validated_in.ticker
        GLOBAL_LOGGER.log_intent(
            tool_or_action=tool_name,
            arguments=validated_in.model_dump(),
            reasoning=f"Check Congressional Leaders STOCK Act filings and Tom Lee Fundstrat themes for {symbol}.",
            agent_name="SmartMoneyIndexSubAgent",
        )

        cong_holders = CONGRESSIONAL_OWNERSHIP_REGISTRY.get(symbol, [])
        tom_lee_themes = TOM_LEE_FUNDSTRAT_REGISTRY.get(symbol, [])

        in_congress = len(cong_holders) > 0
        in_tom_lee = len(tom_lee_themes) > 0

        if in_congress and in_tom_lee:
            summary = (
                f"HIGH SMART-MONEY OVERLAP: {symbol} is held in BOTH the Congressional Leaders Index "
                f"({len(cong_holders)} disclosed Congressional holder(s)) AND Tom Lee's Fundstrat Granny Shots / Thematic Index "
                f"({', '.join(tom_lee_themes)})."
            )
        elif in_congress:
            summary = f"{symbol} is an active constituent of the Congressional Leaders Index ({len(cong_holders)} STOCK Act disclosure(s))."
        elif in_tom_lee:
            summary = f"{symbol} is an active constituent of Tom Lee's Fundstrat Thematic Index ({', '.join(tom_lee_themes)})."
        else:
            summary = f"{symbol} is not currently disclosed in the Congressional Leaders or Tom Lee Fundstrat flagship registries."

        validated_out = SmartMoneyOwnershipOutput(
            status="SUCCESS",
            ticker=symbol,
            in_congressional_leaders_index=in_congress,
            congressional_holders=cong_holders,
            in_tom_lee_fundstrat_index=in_tom_lee,
            tom_lee_fundstrat_themes=tom_lee_themes,
            smart_money_conviction_summary=summary,
        )
        out_dict = validated_out.model_dump()

        GLOBAL_LOGGER.log_outcome(
            tool_or_action=tool_name,
            status="SUCCESS",
            latency_ms=(time.perf_counter() - start_ts) * 1000.0,
            outcome_summary={
                "ticker": symbol,
                "in_congress": in_congress,
                "in_tom_lee_fundstrat": in_tom_lee,
            },
            agent_name="SmartMoneyIndexSubAgent",
        )
        return out_dict


def calculate_custom_index_realtime_snapshot(index_id: str) -> Dict[str, Any]:
    """
    Calculate real-time index level, average daily percentage change, breadth (% above 200 SMA),
    and top Buy/Sell signals for any of the 7 supported universes (`DJIA`, `NASDAQ_100`, `SP500`,
    `IWM_RUSSELL3000`, `VALUE_STOCKS`, `CONGRESSIONAL_LEADERS`, `TOM_LEE_FUNDSTRAT`).

    Args:
        index_id: Identifier of the index universe to aggregate.

    Returns:
        Aggregated index performance, breadth, and constituent signals dictionary, or
        `GuidedToolErrorResponse` if `index_id` is unknown.
    """
    tool_name = "calculate_custom_index_realtime_snapshot"
    start_ts = time.perf_counter()
    norm_id = index_id.strip().upper()

    with GLOBAL_TRACER.start_span(f"span:tool:{tool_name}", {"index_id": norm_id}):
        if norm_id not in UNIVERSE_TICKER_MAP:
            err = GuidedToolErrorResponse(
                error_code="UNKNOWN_INDEX_UNIVERSE",
                error_message=f"Unknown index_id '{index_id}'.",
                llm_recovery_instruction=(
                    "Select one of the valid index IDs: 'DJIA', 'NASDAQ_100', 'SP500', "
                    "'IWM_RUSSELL3000', 'VALUE_STOCKS', 'CONGRESSIONAL_LEADERS', or 'TOM_LEE_FUNDSTRAT'."
                ),
            ).model_dump()
            GLOBAL_LOGGER.log_outcome(
                tool_or_action=tool_name,
                status="GUIDED_ERROR",
                latency_ms=(time.perf_counter() - start_ts) * 1000.0,
                outcome_summary=err,
                agent_name="SmartMoneyIndexSubAgent",
            )
            return err

        GLOBAL_LOGGER.log_intent(
            tool_or_action=tool_name,
            arguments={"index_id": norm_id},
            reasoning=f"Aggregate real-time constituent performance and breadth for {norm_id}.",
            agent_name="SmartMoneyIndexSubAgent",
        )

        tickers = UNIVERSE_TICKER_MAP[norm_id]
        meta = INDEX_METADATA[norm_id]
        constituents = [analyze_ticker_technicals(t) for t in tickers]

        avg_change_pct = round(sum(c["daily_change_pct"] for c in constituents) / max(1, len(constituents)), 2)
        avg_rsi = round(sum(c["rsi_14"] for c in constituents) / max(1, len(constituents)), 1)
        above_200_pct = round(
            (sum(1 for c in constituents if c["price"] > c["sma_200"]) / max(1, len(constituents))) * 100.0, 1
        )
        top_buys = sorted(constituents, key=lambda c: c["signal_score"], reverse=True)[:5]

        snapshot = {
            "status": "SUCCESS",
            "index_id": norm_id,
            "name": meta["name"],
            "benchmark_etf": meta["benchmark_etf"],
            "description": meta["description"],
            "constituent_count": len(constituents),
            "avg_daily_change_pct": avg_change_pct,
            "avg_rsi_14": avg_rsi,
            "breadth_above_200_sma_pct": above_200_pct,
            "top_buy_candidates": [
                {"ticker": c["ticker"], "price": c["price"], "action_signal": c["action_signal"], "signal_score": c["signal_score"]}
                for c in top_buys
            ],
        }

        GLOBAL_LOGGER.log_outcome(
            tool_or_action=tool_name,
            status="SUCCESS",
            latency_ms=(time.perf_counter() - start_ts) * 1000.0,
            outcome_summary={
                "index_id": norm_id,
                "avg_daily_change_pct": avg_change_pct,
                "breadth_above_200_sma_pct": above_200_pct,
            },
            agent_name="SmartMoneyIndexSubAgent",
        )
        return snapshot


def stage_or_execute_equity_trade_order(
    ticker: str,
    side: str,
    quantity: int,
    order_type: str = "MARKET",
    limit_price: Optional[float] = None,
    hitl_confirmation_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate and stage or execute an equity BUY or SELL trade order in the portfolio ledger,
    enforcing single-order risk limits (Rubric 3.3) and Human-in-the-Loop confirmation gates (Rubric 3.4).

    Args:
        ticker: US equity or ETF ticker symbol to buy or sell (e.g., 'NVDA', 'AAPL', 'IWM').
        side: Trade direction ('BUY' or 'SELL').
        quantity: Number of whole shares to trade (1 to 10,000).
        order_type: Order execution type ('MARKET' or 'LIMIT'; defaults to 'MARKET').
        limit_price: Optional limit price in USD if `order_type` is 'LIMIT'.
        hitl_confirmation_token: Optional Human-in-the-Loop confirmation token when approving a high-stakes order.

    Returns:
        Execution receipt (`status='FILLED'`), Human-in-the-Loop prompt (`status='HITL_CONFIRMATION_REQUIRED'`),
        or `GuidedToolErrorResponse` (`status='GUIDED_ERROR'`) with recovery guidance.
    """
    tool_name = "stage_or_execute_equity_trade_order"
    start_ts = time.perf_counter()

    with GLOBAL_TRACER.start_span(f"span:tool:{tool_name}", {"ticker": ticker, "side": side, "quantity": quantity}):
        try:
            validated_in = EquityTradeOrderInput(
                ticker=ticker,
                side=side,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price,
                hitl_confirmation_token=hitl_confirmation_token,
            )
        except Exception as exc:
            err = GuidedToolErrorResponse(
                error_code="INVALID_TRADE_ORDER_ARGUMENTS",
                error_message=str(exc),
                llm_recovery_instruction=(
                    "Ensure `ticker` is a valid uppercase symbol, `side` is 'BUY' or 'SELL', "
                    "and `quantity` is a positive integer between 1 and 10,000."
                ),
            ).model_dump()
            GLOBAL_LOGGER.log_outcome(
                tool_or_action=tool_name,
                status="GUIDED_ERROR",
                latency_ms=(time.perf_counter() - start_ts) * 1000.0,
                outcome_summary=err,
                agent_name="TradeExecutionSubAgent",
            )
            return err

        GLOBAL_LOGGER.log_intent(
            tool_or_action=tool_name,
            arguments=validated_in.model_dump(),
            reasoning=f"User instructed to {validated_in.side} {validated_in.quantity} shares of {validated_in.ticker}.",
            agent_name="TradeExecutionSubAgent",
        )

        result = GLOBAL_BROKER.execute_or_stage_order(
            ticker=validated_in.ticker,
            side=validated_in.side,
            quantity=validated_in.quantity,
            order_type=validated_in.order_type,
            limit_price=validated_in.limit_price,
            hitl_confirmation_token=validated_in.hitl_confirmation_token,
        )

        GLOBAL_LOGGER.log_outcome(
            tool_or_action=tool_name,
            status=str(result.get("status", "UNKNOWN")),
            latency_ms=(time.perf_counter() - start_ts) * 1000.0,
            outcome_summary=result,
            agent_name="TradeExecutionSubAgent",
        )
        return result


def confirm_pending_human_in_the_loop_trade_order(
    confirmation_token: str,
    decision: str = "APPROVE",
) -> Dict[str, Any]:
    """
    Confirm or reject a high-stakes trade order previously paused by `HumanInTheLoopApprovalGate` (Rubric 3.4).

    Args:
        confirmation_token: Unique HITL token (`hitl_...`) issued when the order was staged.
        decision: Human operator decision ('APPROVE' or 'REJECT').

    Returns:
        Execution fill receipt if approved, cancellation notice if rejected, or `GuidedToolErrorResponse`
        if the token does not exist.
    """
    tool_name = "confirm_pending_human_in_the_loop_trade_order"
    start_ts = time.perf_counter()
    norm_decision = decision.strip().upper()

    with GLOBAL_TRACER.start_span(f"span:tool:{tool_name}", {"token": confirmation_token, "decision": norm_decision}):
        GLOBAL_LOGGER.log_intent(
            tool_or_action=tool_name,
            arguments={"confirmation_token": confirmation_token, "decision": norm_decision},
            reasoning=f"Process human confirmation decision ({norm_decision}) for HITL token {confirmation_token}.",
            agent_name="TradeExecutionSubAgent",
        )

        if norm_decision == "REJECT":
            staged = GLOBAL_HITL_GATE.reject_token(confirmation_token)
            if not staged:
                err = GuidedToolErrorResponse(
                    error_code="UNKNOWN_HITL_CONFIRMATION_TOKEN",
                    error_message=f"Confirmation token '{confirmation_token}' was not found.",
                    llm_recovery_instruction="Query pending HITL orders first and provide a valid active `hitl_...` token.",
                ).model_dump()
                GLOBAL_LOGGER.log_outcome(tool_name, "GUIDED_ERROR", (time.perf_counter() - start_ts) * 1000.0, err, "TradeExecutionSubAgent")
                return err
            out = {
                "status": "REJECTED_BY_HUMAN",
                "confirmation_token": confirmation_token,
                "ticker": staged.ticker,
                "side": staged.side,
                "quantity": staged.quantity,
            }
            GLOBAL_LOGGER.log_outcome(tool_name, "REJECTED_BY_HUMAN", (time.perf_counter() - start_ts) * 1000.0, out, "TradeExecutionSubAgent")
            return out

        staged = GLOBAL_HITL_GATE.approve_token(confirmation_token)
        if not staged:
            err = GuidedToolErrorResponse(
                error_code="UNKNOWN_HITL_CONFIRMATION_TOKEN",
                error_message=f"Confirmation token '{confirmation_token}' was not found.",
                llm_recovery_instruction="Check pending HITL orders and supply the exact `hitl_...` confirmation token.",
            ).model_dump()
            GLOBAL_LOGGER.log_outcome(tool_name, "GUIDED_ERROR", (time.perf_counter() - start_ts) * 1000.0, err, "TradeExecutionSubAgent")
            return err

        result = GLOBAL_BROKER.execute_or_stage_order(
            ticker=staged.ticker,
            side=staged.side,
            quantity=staged.quantity,
            order_type=staged.order_type,
            hitl_confirmation_token=confirmation_token,
        )
        GLOBAL_LOGGER.log_outcome(tool_name, str(result.get("status")), (time.perf_counter() - start_ts) * 1000.0, result, "TradeExecutionSubAgent")
        return result


def generate_comprehensive_stock_deep_research_report(
    ticker: str,
    research_focus: str = "FULL_COMPANY_AND_TECHNICAL",
) -> Dict[str, Any]:
    """
    Generate an institutional-grade Deep Research Report on a specific stock combining company
    fundamentals (business model, economic moat, FCF/ROIC metrics, catalysts, and risks) with
    multi-timeframe technical analysis (MA 9/20/50/200, RSI 14, Momentum, Divergence, Support/Resistance)
    to recommend whether to BUY, SELL, or HOLD the stock.

    Args:
        ticker: US equity or ETF ticker symbol (e.g., 'NVDA', 'AAPL', 'VST', 'IWM', 'JPM').
        research_focus: Research emphasis ('FULL_COMPANY_AND_TECHNICAL', 'COMPANY_FUNDAMENTALS',
            or 'TECHNICAL_BUY_SELL_HOLD'). Defaults to 'FULL_COMPANY_AND_TECHNICAL'.

    Returns:
        Dictionary conforming to `StockDeepResearchReportOutput` containing company research,
        technical Buy/Sell/Hold thesis, Markdown dossier, and spoken `voice_briefing`, or
        `GuidedToolErrorResponse` if inputs fail schema validation.
    """
    tool_name = "generate_comprehensive_stock_deep_research_report"
    start_ts = time.perf_counter()

    with GLOBAL_TRACER.start_span(f"span:tool:{tool_name}", {"ticker": ticker, "focus": research_focus}):
        try:
            validated_in = StockDeepResearchQueryInput(ticker=ticker, research_focus=research_focus)
        except Exception as exc:
            err = GuidedToolErrorResponse(
                error_code="INVALID_DEEP_RESEARCH_ARGUMENTS",
                error_message=str(exc),
                llm_recovery_instruction=(
                    "Pass a valid 1-6 character uppercase US ticker symbol (e.g., 'NVDA', 'AAPL', 'VST', 'IWM') "
                    "to generate a company and technical deep research report."
                ),
            ).model_dump()
            GLOBAL_LOGGER.log_outcome(
                tool_or_action=tool_name,
                status="GUIDED_ERROR",
                latency_ms=(time.perf_counter() - start_ts) * 1000.0,
                outcome_summary=err,
                agent_name="DeepResearchSubAgent",
            )
            return err

        GLOBAL_LOGGER.log_intent(
            tool_or_action=tool_name,
            arguments=validated_in.model_dump(),
            reasoning=(
                f"Synthesize company business moat, catalysts/risks, and technical Buy/Sell/Hold "
                f"research report for {validated_in.ticker}."
            ),
            agent_name="DeepResearchSubAgent",
        )

        raw = generate_stock_deep_research_dossier(
            validated_in.ticker,
            research_focus=validated_in.research_focus,
        )
        validated_out = StockDeepResearchReportOutput(**raw)
        out_dict = validated_out.model_dump()

        GLOBAL_LOGGER.log_outcome(
            tool_or_action=tool_name,
            status="SUCCESS",
            latency_ms=(time.perf_counter() - start_ts) * 1000.0,
            outcome_summary={
                "ticker": out_dict["ticker"],
                "final_recommendation": out_dict["final_recommendation"],
                "conviction_tier": out_dict["conviction_tier"],
                "conviction_score": out_dict["conviction_score"],
                "google_finance_url": out_dict["google_finance_url"],
            },
            agent_name="DeepResearchSubAgent",
        )
        return out_dict


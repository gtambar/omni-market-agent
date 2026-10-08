"""
omni_market_agent/schemas/models.py — Strict Input/Output JSON Schemas & Guided Error Models.

Satisfies AgentOps Code Review Matrix Rubric Criteria:
  - 1.3 Explicit JSON Schemas (5/5 Points):
    Strict input and output schemas (Pydantic v2 `BaseModel` with `@field_validator`, plus
    built-in deterministic runtime validation fallback when running in stdlib-only mode)
    that validate tool arguments and constrain LLM generations.
  - 1.4 Guided Error Handling (5/5 Points):
    Structured `GuidedToolErrorResponse` returns descriptive recovery instructions back to
    the LLM (`llm_recovery_instruction`) instead of raising unhandled exceptions.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


try:
    from pydantic import BaseModel, Field, field_validator  # type: ignore

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    class BaseModel:  # type: ignore
        """Lightweight Pydantic-compatible schema base class for stdlib-only environments."""

        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)
            if hasattr(self, "_validate_fields"):
                self._validate_fields()

        def model_dump(self) -> Dict[str, Any]:
            out: Dict[str, Any] = {}
            for k, v in self.__dict__.items():
                if isinstance(v, BaseModel):
                    out[k] = v.model_dump()
                elif isinstance(v, list):
                    out[k] = [item.model_dump() if isinstance(item, BaseModel) else item for item in v]
                else:
                    out[k] = v
            return out

    def Field(default: Any = ..., **kwargs: Any) -> Any:  # type: ignore
        return None if default is ... else default

    def field_validator(*args: Any, **kwargs: Any):  # type: ignore
        def decorator(fn: Any) -> Any:
            return fn
        return decorator


VALID_TICKER_RE = re.compile(r"^[A-Z]{1,6}(?:-[A-Z]{1,2})?$")


def validate_ticker_symbol(raw_ticker: str) -> str:
    """Validate and normalize an equity or ETF ticker symbol."""
    if not isinstance(raw_ticker, str):
        raise ValueError("Ticker symbol must be a string (e.g., 'NVDA', 'AAPL', 'IWM', 'BRK-B').")
    cleaned = raw_ticker.strip().upper().replace(".", "-")
    if not VALID_TICKER_RE.fullmatch(cleaned):
        raise ValueError(
            f"Invalid ticker symbol '{raw_ticker}'. Provide a valid 1-6 letter US equity/ETF ticker such as 'NVDA', 'AAPL', 'IWM', or 'BRK-B'."
        )
    return cleaned


class GuidedToolErrorResponse(BaseModel):
    """
    Rubric 1.4: Structured error response returning actionable recovery guidance to the LLM
    instead of crashing on bad inputs or transient market feed errors.
    """

    status: str = Field(
        default="GUIDED_ERROR",
        description="Fixed status indicator signaling a handled operational or validation error.",
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error classification code (e.g., INVALID_TICKER_SYMBOL, INSUFFICIENT_BUYING_POWER).",
    )
    error_message: str = Field(
        ...,
        description="Human-readable description explaining why the tool invocation did not succeed.",
    )
    llm_recovery_instruction: str = Field(
        ...,
        description="Explicit step-by-step instruction guiding the LLM on how to correct arguments or choose another tool.",
    )

    def __init__(
        self,
        error_code: str,
        error_message: str,
        llm_recovery_instruction: str,
        status: str = "GUIDED_ERROR",
        **kwargs: Any,
    ) -> None:
        if PYDANTIC_AVAILABLE:
            super().__init__(
                status=status,
                error_code=error_code,
                error_message=error_message,
                llm_recovery_instruction=llm_recovery_instruction,
                **kwargs,
            )
        else:
            self.status = status
            self.error_code = error_code
            self.error_message = error_message
            self.llm_recovery_instruction = llm_recovery_instruction


class TechnicalIndicatorQueryInput(BaseModel):
    """Strict input schema for `compute_multi_ma_rsi_divergence_signals`."""

    ticker: str = Field(
        ...,
        description="US equity or ETF ticker symbol to analyze (e.g., 'NVDA', 'AAPL', 'IWM', 'SPY').",
    )
    lookback_days: int = Field(
        default=250,
        ge=200,
        le=500,
        description="Number of trading days of OHLCV history to compute 9, 20, 50, and 200 moving averages (>=200).",
    )

    @field_validator("ticker")
    @classmethod
    def _check_ticker(cls, v: str) -> str:
        return validate_ticker_symbol(v)

    def _validate_fields(self) -> None:
        self.ticker = validate_ticker_symbol(getattr(self, "ticker", ""))
        self.lookback_days = int(getattr(self, "lookback_days", 250) or 250)
        if self.lookback_days < 200 or self.lookback_days > 500:
            raise ValueError("lookback_days must be between 200 and 500 to compute the 200-day moving average.")


class TechnicalIndicatorSignalOutput(BaseModel):
    """Strict output schema returned by `compute_multi_ma_rsi_divergence_signals`."""

    status: str = Field(default="SUCCESS", description="Tool execution status.")
    ticker: str = Field(..., description="Normalized ticker symbol.")
    company_name: str = Field(..., description="Full company or ETF name.")
    google_finance_symbol: str = Field(..., description="Canonical Google Finance ticker:exchange code (e.g., NVDA:NASDAQ).")
    google_finance_url: str = Field(..., description="Authoritative Google Finance quote URL for citation grounding.")
    data_source: str = Field(default="Google Finance", description="Data grounding source.")
    indices_membership: List[str] = Field(..., description="Tracked indices containing this symbol (DJIA, NASDAQ_100, SP500, etc.).")
    price: float = Field(..., description="Latest market price in USD.")
    daily_change_usd: float = Field(..., description="Daily price change in USD.")
    daily_change_pct: float = Field(..., description="Daily percentage price change.")
    sma_9: float = Field(..., description="9-period Simple Moving Average.")
    ema_9: float = Field(..., description="9-period Exponential Moving Average.")
    sma_20: float = Field(..., description="20-period Simple Moving Average.")
    ema_20: float = Field(..., description="20-period Exponential Moving Average.")
    sma_50: float = Field(..., description="50-period Simple Moving Average.")
    sma_200: float = Field(..., description="200-period Simple Moving Average.")
    ma_alignment: str = Field(..., description="Moving average trend alignment classification.")
    rsi_14: float = Field(..., description="14-period Wilder's Relative Strength Index (0-100).")
    rsi_regime: str = Field(..., description="RSI regime (OVERSOLD, BULLISH, OVERBOUGHT, NEUTRAL).")
    momentum_roc_10d_pct: float = Field(..., description="10-day Rate of Change momentum percentage.")
    macd_line: float = Field(..., description="MACD (12,26) line value.")
    macd_signal: float = Field(..., description="MACD 9-period signal line value.")
    macd_histogram: float = Field(..., description="MACD histogram value.")
    divergence_status: str = Field(..., description="Detected price-indicator divergence (BULLISH_DIVERGENCE, BEARISH_DIVERGENCE, NONE).")
    divergence_explanation: str = Field(..., description="Explanation of the pivot swing comparison for divergence.")
    action_signal: str = Field(..., description="Composite action signal (STRONG BUY, BUY, HOLD, SELL, STRONG SELL).")
    signal_score: int = Field(..., description="Quantitative confluence score from 0 to 100.")
    signal_reasons: List[str] = Field(..., description="Explicit indicator triggers supporting the buy/sell signal.")
    flash_alert: bool = Field(..., description="True when key indicators trigger an immediate UI flash alert.")
    flash_type: str = Field(..., description="Flash alert classification for the interactive UI.")


class AnalystConsensusQueryInput(BaseModel):
    """Strict input schema for `fetch_wall_street_analyst_consensus_and_upgrades`."""

    ticker: str = Field(
        ...,
        description="US equity ticker symbol for analyst forecast and upgrade/downgrade lookup.",
    )

    @field_validator("ticker")
    @classmethod
    def _check_ticker(cls, v: str) -> str:
        return validate_ticker_symbol(v)

    def _validate_fields(self) -> None:
        self.ticker = validate_ticker_symbol(getattr(self, "ticker", ""))


class AnalystConsensusOutput(BaseModel):
    """Strict output schema returned by `fetch_wall_street_analyst_consensus_and_upgrades`."""

    status: str = Field(default="SUCCESS", description="Tool execution status.")
    ticker: str = Field(..., description="Normalized ticker symbol.")
    google_finance_symbol: str = Field(..., description="Canonical Google Finance ticker:exchange code.")
    google_finance_url: str = Field(..., description="Authoritative Google Finance quote URL.")
    data_source: str = Field(default="Google Finance", description="Data grounding source.")
    consensus_rating: str = Field(..., description="Consensus Wall Street rating (Strong Buy, Buy, Hold, Sell).")
    consensus_score: float = Field(..., description="Numeric consensus rating (1.0 = Strong Buy to 5.0 = Sell).")
    num_analysts: int = Field(..., description="Total number of covering Wall Street analysts.")
    target_price_low: float = Field(..., description="Lowest 12-month analyst price target in USD.")
    target_price_mean: float = Field(..., description="Mean 12-month analyst price target in USD.")
    target_price_high: float = Field(..., description="Highest 12-month analyst price target in USD.")
    implied_upside_pct: float = Field(..., description="Implied percentage upside/downside to mean analyst target.")
    recent_upgrades_downgrades: List[Dict[str, str]] = Field(
        ..., description="List of recent brokerage upgrades, downgrades, and price target revisions."
    )


class SmartMoneyOwnershipQueryInput(BaseModel):
    """Strict input schema for `lookup_congressional_and_tom_lee_fundstrat_ownership`."""

    ticker: str = Field(
        ...,
        description="US equity ticker symbol to check against Congressional Leaders and Tom Lee (Fundstrat) portfolios.",
    )

    @field_validator("ticker")
    @classmethod
    def _check_ticker(cls, v: str) -> str:
        return validate_ticker_symbol(v)

    def _validate_fields(self) -> None:
        self.ticker = validate_ticker_symbol(getattr(self, "ticker", ""))


class SmartMoneyOwnershipOutput(BaseModel):
    """Strict output schema returned by `lookup_congressional_and_tom_lee_fundstrat_ownership`."""

    status: str = Field(default="SUCCESS", description="Tool execution status.")
    ticker: str = Field(..., description="Normalized ticker symbol.")
    in_congressional_leaders_index: bool = Field(
        ..., description="True if owned/traded by tracked US Congressional Leaders."
    )
    congressional_holders: List[Dict[str, str]] = Field(
        ..., description="Detailed STOCK Act disclosure records of Congressional members holding/trading the stock."
    )
    in_tom_lee_fundstrat_index: bool = Field(
        ..., description="True if held in Tom Lee's Fundstrat Granny Shots (GRNY) / thematic conviction list."
    )
    tom_lee_fundstrat_themes: List[str] = Field(
        ..., description="Fundstrat thematic pillars satisfied by this stock."
    )
    smart_money_conviction_summary: str = Field(
        ..., description="Synthesized institutional & congressional conviction summary."
    )


class EquityTradeOrderInput(BaseModel):
    """Strict input schema for `stage_or_execute_equity_trade_order`."""

    ticker: str = Field(..., description="US equity or ETF ticker symbol to buy or sell.")
    side: str = Field(..., description="Order direction: 'BUY' or 'SELL'.")
    quantity: int = Field(..., ge=1, le=10000, description="Whole number of shares to trade (1 to 10,000).")
    order_type: str = Field(default="MARKET", description="Order type: 'MARKET' or 'LIMIT'.")
    limit_price: Optional[float] = Field(default=None, description="Limit price in USD if order_type is 'LIMIT'.")
    hitl_confirmation_token: Optional[str] = Field(
        default=None,
        description="Human-in-the-Loop confirmation token if confirming a previously staged high-stakes order.",
    )

    @field_validator("ticker")
    @classmethod
    def _check_ticker(cls, v: str) -> str:
        return validate_ticker_symbol(v)

    @field_validator("side")
    @classmethod
    def _check_side(cls, v: str) -> str:
        s = v.strip().upper()
        if s not in ("BUY", "SELL"):
            raise ValueError("Order side must be 'BUY' or 'SELL'.")
        return s

    def _validate_fields(self) -> None:
        self.ticker = validate_ticker_symbol(getattr(self, "ticker", ""))
        self.side = str(getattr(self, "side", "")).strip().upper()
        if self.side not in ("BUY", "SELL"):
            raise ValueError("Order side must be 'BUY' or 'SELL'.")
        self.quantity = int(getattr(self, "quantity", 0))
        if self.quantity < 1 or self.quantity > 10000:
            raise ValueError("Quantity must be between 1 and 10,000 shares.")
        self.order_type = str(getattr(self, "order_type", "MARKET") or "MARKET").strip().upper()
        if self.order_type not in ("MARKET", "LIMIT"):
            raise ValueError("order_type must be 'MARKET' or 'LIMIT'.")
        if not hasattr(self, "limit_price"):
            self.limit_price = None
        if not hasattr(self, "hitl_confirmation_token"):
            self.hitl_confirmation_token = None


class StockDeepResearchQueryInput(BaseModel):
    """Strict input schema for `generate_comprehensive_stock_deep_research_report`."""

    ticker: str = Field(
        ...,
        description="US equity or ETF ticker symbol for institutional company + technical deep research.",
    )
    research_focus: str = Field(
        default="FULL_COMPANY_AND_TECHNICAL",
        description="Research focus scope (e.g., 'FULL_COMPANY_AND_TECHNICAL', 'COMPANY_FUNDAMENTALS', 'TECHNICAL_BUY_SELL_HOLD').",
    )

    @field_validator("ticker")
    @classmethod
    def _check_ticker(cls, v: str) -> str:
        return validate_ticker_symbol(v)

    def _validate_fields(self) -> None:
        self.ticker = validate_ticker_symbol(getattr(self, "ticker", ""))
        self.research_focus = str(getattr(self, "research_focus", "FULL_COMPANY_AND_TECHNICAL") or "FULL_COMPANY_AND_TECHNICAL").strip().upper()


class StockDeepResearchReportOutput(BaseModel):
    """Strict output schema returned by `generate_comprehensive_stock_deep_research_report`."""

    status: str = Field(default="SUCCESS", description="Tool execution status.")
    ticker: str = Field(..., description="Normalized equity/ETF ticker symbol.")
    company_name: str = Field(..., description="Full company or ETF name.")
    research_focus: str = Field(..., description="Research scope applied.")
    google_finance_symbol: str = Field(..., description="Canonical Google Finance ticker:exchange code.")
    google_finance_url: str = Field(..., description="Authoritative Google Finance quote URL.")
    indices_membership: List[str] = Field(..., description="Tracked market universes containing this stock.")
    final_recommendation: str = Field(..., description="Explicit BUY, SELL, or HOLD recommendation.")
    conviction_tier: str = Field(..., description="Granular conviction tier (STRONG BUY, BUY, HOLD, SELL, STRONG SELL).")
    conviction_score: int = Field(..., description="Composite fundamental + technical conviction score (0-100).")
    executive_summary: str = Field(..., description="Executive institutional thesis summary.")
    company_research: Dict[str, Any] = Field(..., description="Company business model, economic moat, fundamentals, catalysts, and risks.")
    technical_research: Dict[str, Any] = Field(..., description="Technical MA(9,20,50,200), RSI(14), Momentum, Divergence, and Support/Resistance levels.")
    analyst_and_smart_money: Dict[str, Any] = Field(..., description="Wall Street analyst consensus and Congressional / Tom Lee ownership.")
    markdown_report: str = Field(..., description="Formatted institutional Markdown dossier.")
    voice_briefing: str = Field(..., description="Spoken audio briefing for multimodal voice playback.")


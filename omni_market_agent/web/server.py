"""
omni_market_agent/web/server.py — Dual-Mode FastAPI + Built-In HTTP Server for Interactive Multimodal UI.

Serves:
  - `GET /` : Interactive Terminal UI (Candlestick + MA 9/20/50/200 chart, Flashing Indicators, Voice/Text Agent)
  - `GET /api/dashboard` : Full 24/7 screener state, custom indices (Congressional & Tom Lee), flashing alerts
  - `GET /api/chart/{ticker}` : 150-bar OHLCV + MA(9,20,50,200) + RSI(14) + MACD chart series + Analyst data
  - `GET /api/portfolio` : Cash, open positions, P&L, order book, and pending HITL confirmations
  - `POST /api/agent/chat` : Multi-modal (Voice + Text) multi-agent query endpoint grounded in sub-agents
  - `POST /api/trade/order` : Direct BUY/SELL instruction endpoint with HITL confirmation gate
  - `POST /api/trade/confirm` : Approve or reject a staged Human-in-the-Loop trade token
  - `POST /api/daemon/refresh` : Force an immediate 3-minute market update cycle
  - `GET /api/observability` : Live OpenTelemetry spans, structured JSON logs, and secret vault status
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from ..agents.orchestrator import GLOBAL_ORCHESTRATOR
from ..config import SETTINGS
from ..daemon.scheduler import GLOBAL_DAEMON
from ..execution.broker import GLOBAL_BROKER
from ..observability.logger import GLOBAL_LOGGER
from ..observability.tracing import GLOBAL_TRACER
from ..quant.analyst_data import get_analyst_consensus_and_upgrades
from ..security.secret_manager import GLOBAL_SECRET_VAULT
from ..tools.market_tools import (
    compute_multi_ma_rsi_divergence_signals,
    confirm_pending_human_in_the_loop_trade_order,
    lookup_congressional_and_tom_lee_fundstrat_ownership,
    stage_or_execute_equity_trade_order,
)


STATIC_DIR = Path(__file__).resolve().parent / "static"


def build_chart_payload(ticker: str) -> Dict[str, Any]:
    """Build complete interactive chart + technical + analyst + smart-money payload for `ticker`."""
    tech = compute_multi_ma_rsi_divergence_signals(ticker, lookback_days=250, include_chart_series=True)
    if tech.get("status") == "GUIDED_ERROR":
        return tech
    analyst = get_analyst_consensus_and_upgrades(tech["ticker"], prefer_live_google_finance=True)
    smart = lookup_congressional_and_tom_lee_fundstrat_ownership(tech["ticker"])
    GLOBAL_DAEMON.sync_single_ticker_snapshot(tech, analyst)
    return {
        "status": "SUCCESS",
        "ticker": tech["ticker"],
        "price": tech.get("price"),
        "sma_9": tech.get("sma_9"),
        "sma_20": tech.get("sma_20"),
        "sma_50": tech.get("sma_50"),
        "sma_200": tech.get("sma_200"),
        "rsi_14": tech.get("rsi_14"),
        "momentum_roc_10d_pct": tech.get("momentum_roc_10d_pct"),
        "divergence_status": tech.get("divergence_status"),
        "divergence_explanation": tech.get("divergence_explanation"),
        "chart_series": tech.get("chart_series", []),
        "technical": tech,
        "analyst": analyst,
        "smart_money": smart,
    }


def create_fastapi_app() -> Any:
    """Create and configure the FastAPI application when `fastapi` is installed."""
    from fastapi import FastAPI, Request  # type: ignore
    from fastapi.responses import FileResponse, JSONResponse  # type: ignore
    from fastapi.staticfiles import StaticFiles  # type: ignore

    app = FastAPI(
        title="OmniMarket Agent — 24/7 Multi-Modal Quantitative Platform",
        version="1.0.0",
    )

    @app.on_event("startup")
    async def _on_startup() -> None:
        GLOBAL_DAEMON.start_background_24x7_loop()

    @app.get("/api/dashboard")
    async def api_dashboard(index: Optional[str] = None) -> JSONResponse:
        return JSONResponse(GLOBAL_DAEMON.get_dashboard_state(index_filter=index))

    @app.get("/api/chart/{ticker}")
    async def api_chart(ticker: str) -> JSONResponse:
        return JSONResponse(build_chart_payload(ticker))

    @app.get("/api/portfolio")
    async def api_portfolio() -> JSONResponse:
        return JSONResponse(GLOBAL_BROKER.get_portfolio_summary())

    @app.post("/api/daemon/refresh")
    async def api_refresh() -> JSONResponse:
        return JSONResponse(GLOBAL_DAEMON.refresh_all_now())

    @app.post("/api/agent/chat")
    async def api_agent_chat(request: Request) -> JSONResponse:
        body = await request.json()
        result = await GLOBAL_ORCHESTRATOR.handle_user_request(
            user_query=str(body.get("query", "")),
            session_id=str(body.get("session_id", "web_session")),
            modality=str(body.get("modality", "text")),
            ui_selected_ticker=body.get("selected_ticker"),
        )
        return JSONResponse(result)

    @app.get("/api/research/deep/{ticker}")
    async def api_deep_research_get(ticker: str) -> JSONResponse:
        result = await GLOBAL_ORCHESTRATOR.run_deep_stock_research(
            query_or_ticker=ticker,
            modality="text",
            session_id="deep_research_session",
            fallback_ticker=ticker,
        )
        return JSONResponse(result)

    @app.post("/api/research/deep")
    async def api_deep_research_post(request: Request) -> JSONResponse:
        body = await request.json()
        result = await GLOBAL_ORCHESTRATOR.run_deep_stock_research(
            query_or_ticker=str(body.get("query", body.get("ticker", "NVDA"))),
            modality=str(body.get("modality", "text")),
            session_id=str(body.get("session_id", "deep_research_session")),
            fallback_ticker=str(body.get("selected_ticker", "NVDA")),
        )
        return JSONResponse(result)

    @app.post("/api/trade/order")
    async def api_trade_order(request: Request) -> JSONResponse:
        body = await request.json()
        res = stage_or_execute_equity_trade_order(
            ticker=str(body.get("ticker", "NVDA")),
            side=str(body.get("side", "BUY")),
            quantity=int(body.get("quantity", 1)),
            order_type=str(body.get("order_type", "MARKET")),
            limit_price=body.get("limit_price"),
            hitl_confirmation_token=body.get("hitl_confirmation_token"),
        )
        return JSONResponse({"trade_result": res, "portfolio": GLOBAL_BROKER.get_portfolio_summary()})

    @app.post("/api/trade/confirm")
    async def api_trade_confirm(request: Request) -> JSONResponse:
        body = await request.json()
        res = confirm_pending_human_in_the_loop_trade_order(
            confirmation_token=str(body.get("confirmation_token", "")),
            decision=str(body.get("decision", "APPROVE")),
        )
        return JSONResponse({"trade_result": res, "portfolio": GLOBAL_BROKER.get_portfolio_summary()})

    @app.get("/api/observability")
    async def api_observability() -> JSONResponse:
        return JSONResponse(
            {
                "traces": GLOBAL_TRACER.get_recent_spans(limit=30),
                "structured_logs": GLOBAL_LOGGER.get_recent_logs(limit=30),
                "secret_vault": GLOBAL_SECRET_VAULT.health_status(),
            }
        )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def root_index() -> FileResponse:
        return FileResponse(str(STATIC_DIR / "index.html"))

    return app


class StdlibOmniRequestHandler(BaseHTTPRequestHandler):
    """Zero-dependency stdlib HTTP fallback handler serving the exact same REST API and UI."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress default stderr HTTP prints; all telemetry goes through StructuredAgentLogger
        pass

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _serve_static(self, file_path: Path) -> None:
        if not file_path.is_file():
            self._send_json({"error": "File not found"}, status=404)
            return
        ctype, _ = mimetypes.guess_type(str(file_path))
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            return self._serve_static(STATIC_DIR / "index.html")
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            return self._serve_static(STATIC_DIR / rel)
        if path == "/api/dashboard":
            idx = qs.get("index", [None])[0]
            return self._send_json(GLOBAL_DAEMON.get_dashboard_state(index_filter=idx))
        if path.startswith("/api/chart/"):
            ticker = path.split("/api/chart/", 1)[1]
            return self._send_json(build_chart_payload(ticker))
        if path.startswith("/api/research/deep/"):
            ticker = path.split("/api/research/deep/", 1)[1]
            res = asyncio.run(
                GLOBAL_ORCHESTRATOR.run_deep_stock_research(
                    query_or_ticker=ticker,
                    modality="text",
                    session_id="deep_research_session",
                    fallback_ticker=ticker,
                )
            )
            return self._send_json(res)
        if path == "/api/portfolio":
            return self._send_json(GLOBAL_BROKER.get_portfolio_summary())
        if path == "/api/observability":
            return self._send_json(
                {
                    "traces": GLOBAL_TRACER.get_recent_spans(limit=30),
                    "structured_logs": GLOBAL_LOGGER.get_recent_logs(limit=30),
                    "secret_vault": GLOBAL_SECRET_VAULT.health_status(),
                }
            )
        self._send_json({"error": f"Unknown endpoint {path}"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if path == "/api/daemon/refresh":
            return self._send_json(GLOBAL_DAEMON.refresh_all_now())
        if path == "/api/agent/chat":
            res = asyncio.run(
                GLOBAL_ORCHESTRATOR.handle_user_request(
                    user_query=str(body.get("query", "")),
                    session_id=str(body.get("session_id", "web_session")),
                    modality=str(body.get("modality", "text")),
                    ui_selected_ticker=body.get("selected_ticker"),
                )
            )
            return self._send_json(res)
        if path == "/api/research/deep":
            res = asyncio.run(
                GLOBAL_ORCHESTRATOR.run_deep_stock_research(
                    query_or_ticker=str(body.get("query", body.get("ticker", "NVDA"))),
                    modality=str(body.get("modality", "text")),
                    session_id=str(body.get("session_id", "deep_research_session")),
                    fallback_ticker=str(body.get("selected_ticker", "NVDA")),
                )
            )
            return self._send_json(res)
        if path == "/api/trade/order":
            res = stage_or_execute_equity_trade_order(
                ticker=str(body.get("ticker", "NVDA")),
                side=str(body.get("side", "BUY")),
                quantity=int(body.get("quantity", 1)),
                order_type=str(body.get("order_type", "MARKET")),
                limit_price=body.get("limit_price"),
                hitl_confirmation_token=body.get("hitl_confirmation_token"),
            )
            return self._send_json({"trade_result": res, "portfolio": GLOBAL_BROKER.get_portfolio_summary()})
        if path == "/api/trade/confirm":
            res = confirm_pending_human_in_the_loop_trade_order(
                confirmation_token=str(body.get("confirmation_token", "")),
                decision=str(body.get("decision", "APPROVE")),
            )
            return self._send_json({"trade_result": res, "portfolio": GLOBAL_BROKER.get_portfolio_summary()})
        self._send_json({"error": f"Unknown POST endpoint {path}"}, status=404)


def run_server(host: str = SETTINGS.host, port: int = SETTINGS.port) -> None:
    """Start the 24/7 daemon and run FastAPI/Uvicorn (if installed) or the ThreadingHTTPServer fallback."""
    GLOBAL_DAEMON.start_background_24x7_loop()
    try:
        import uvicorn  # type: ignore

        app = create_fastapi_app()
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        server = ThreadingHTTPServer((host, port), StdlibOmniRequestHandler)
        GLOBAL_LOGGER.emit(
            severity="INFO",
            event_type="WEB_SERVER_STARTED",
            message=f"OmniMarket Agent server listening on http://{host}:{port} (stdlib HTTP mode)",
            payload={"host": host, "port": port},
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
            GLOBAL_DAEMON.stop()

"""
omni_market_agent/daemon/scheduler.py — 24/7 Continuous 3-Minute Market & Indicator Refresh Daemon.

Runs continuously 24x7, bulk-fetching live Google Finance quotes across all 7 stock universes
(`DJIA`, `NASDAQ_100`, `SP500`, `IWM_RUSSELL3000`, `VALUE_STOCKS`, `CONGRESSIONAL_LEADERS`,
`TOM_LEE_FUNDSTRAT`), recomputing MA(9,20,50,200), RSI(14), Momentum, Divergences, Analyst Forecasts,
and emitting flashing UI alerts every 3 minutes (180 seconds).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..config import SETTINGS
from ..data.google_finance import GLOBAL_GOOGLE_FINANCE
from ..data.market_feed import GLOBAL_MARKET_FEED
from ..data.universes import (
    CONGRESSIONAL_OWNERSHIP_REGISTRY,
    INDEX_METADATA,
    TOM_LEE_FUNDSTRAT_REGISTRY,
    UNIVERSE_TICKER_MAP,
    get_all_unique_tickers,
)
from ..observability.logger import GLOBAL_LOGGER
from ..quant.analyst_data import get_analyst_consensus_and_upgrades
from ..quant.indicators import analyze_ticker_technicals


class MarketScannerDaemon24x7:
    """
    24/7 background scheduler refreshing all market universes and indicators every 3 minutes (180s).
    """

    def __init__(self, refresh_interval_seconds: int = SETTINGS.refresh_interval_seconds) -> None:
        self.refresh_interval_seconds = refresh_interval_seconds
        self.last_refresh_epoch: float = 0.0
        self.last_refresh_iso: str = ""
        self.cycle_count: int = 0
        self._lock = threading.Lock()
        self._snapshot_cache: Dict[str, Dict[str, Any]] = {}
        self._index_summaries: Dict[str, Dict[str, Any]] = {}
        self._flashing_alerts: List[Dict[str, Any]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def refresh_all_now(self) -> Dict[str, Any]:
        """
        Execute a complete 3-minute refresh cycle across all tracked equities and 7 indices,
        grounded in live Google Finance bulk quotes (`FinHubUi/data/batchexecute?rpcids=eJnF6e`).
        """
        start_ts = time.perf_counter()
        GLOBAL_MARKET_FEED.bump_3min_cycle()
        all_tickers = get_all_unique_tickers()

        # Bulk-warm live Google Finance prices, daily $ change, and daily % change across all tickers
        if GLOBAL_GOOGLE_FINANCE.live_fetch_enabled:
            GLOBAL_GOOGLE_FINANCE.fetch_bulk_live_quotes(all_tickers)

        new_snapshots: Dict[str, Dict[str, Any]] = {}
        new_flashes: List[Dict[str, Any]] = []

        for ticker in all_tickers:
            tech = analyze_ticker_technicals(ticker, lookback_days=250, include_series=False)
            analyst = get_analyst_consensus_and_upgrades(ticker)
            in_congress = ticker in CONGRESSIONAL_OWNERSHIP_REGISTRY
            in_tom_lee = ticker in TOM_LEE_FUNDSTRAT_REGISTRY

            combined = {
                **tech,
                "consensus_rating": analyst["consensus_rating"],
                "target_price_mean": analyst["target_price_mean"],
                "implied_upside_pct": analyst["implied_upside_pct"],
                "latest_upgrade": analyst["recent_upgrades_downgrades"][0] if analyst["recent_upgrades_downgrades"] else None,
                "in_congressional_leaders": in_congress,
                "congressional_holders_count": len(CONGRESSIONAL_OWNERSHIP_REGISTRY.get(ticker, [])),
                "in_tom_lee_fundstrat": in_tom_lee,
                "tom_lee_themes": TOM_LEE_FUNDSTRAT_REGISTRY.get(ticker, []),
            }
            new_snapshots[ticker] = combined

            if combined["flash_alert"]:
                new_flashes.append(
                    {
                        "ticker": ticker,
                        "price": combined["price"],
                        "daily_change_pct": combined["daily_change_pct"],
                        "action_signal": combined["action_signal"],
                        "flash_type": combined["flash_type"],
                        "divergence_status": combined["divergence_status"],
                        "rsi_14": combined["rsi_14"],
                    }
                )

        new_indices = self._compute_index_summaries(new_snapshots)

        now_epoch = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._snapshot_cache = new_snapshots
            self._index_summaries = new_indices
            self._flashing_alerts = sorted(new_flashes, key=lambda x: abs(x["daily_change_pct"]), reverse=True)[:18]
            self.last_refresh_epoch = now_epoch
            self.last_refresh_iso = now_iso
            self.cycle_count += 1

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        GLOBAL_LOGGER.emit(
            severity="INFO",
            event_type="DAEMON_3MIN_MARKET_REFRESH",
            message=f"Completed 24/7 3-minute refresh cycle #{self.cycle_count} across {len(all_tickers)} equities in {elapsed_ms:.1f}ms.",
            payload={
                "cycle_count": self.cycle_count,
                "tickers_refreshed": len(all_tickers),
                "flashing_alerts_count": len(self._flashing_alerts),
                "latency_ms": round(elapsed_ms, 2),
            },
            agent_name="MarketScannerDaemon24x7",
        )
        return self.get_dashboard_state()

    @staticmethod
    def _compute_index_summaries(snapshots: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Aggregate index-level daily changes, buy signal counts, and 200-SMA breadth."""
        new_indices: Dict[str, Dict[str, Any]] = {}
        for index_id, tickers in UNIVERSE_TICKER_MAP.items():
            meta = INDEX_METADATA[index_id]
            members = [snapshots[t] for t in tickers if t in snapshots]
            avg_chg = round(sum(m["daily_change_pct"] for m in members) / max(1, len(members)), 2)
            buy_count = sum(1 for m in members if m["action_signal"] in ("BUY", "STRONG BUY"))
            above_200 = round(
                (sum(1 for m in members if m["price"] > m["sma_200"]) / max(1, len(members))) * 100.0, 1
            )
            new_indices[index_id] = {
                "index_id": index_id,
                "name": meta["name"],
                "benchmark_etf": meta["benchmark_etf"],
                "constituent_count": len(members),
                "avg_daily_change_pct": avg_chg,
                "buy_signal_count": buy_count,
                "breadth_above_200_sma_pct": above_200,
            }
        return new_indices

    def sync_single_ticker_snapshot(
        self, tech: Dict[str, Any], analyst: Dict[str, Any]
    ) -> None:
        """
        Update a single ticker's cached screener row immediately when its full 250-day Google Finance
        chart or Deep Research report is loaded, keeping the Screener Table 100% synchronized with the Chart.
        """
        ticker = tech.get("ticker", "").upper()
        if not ticker:
            return
        in_congress = ticker in CONGRESSIONAL_OWNERSHIP_REGISTRY
        in_tom_lee = ticker in TOM_LEE_FUNDSTRAT_REGISTRY
        clean_tech = {k: v for k, v in tech.items() if k != "chart_series"}
        combined = {
            **clean_tech,
            "consensus_rating": analyst.get("consensus_rating", "Buy"),
            "target_price_mean": analyst.get("target_price_mean", tech.get("price", 0.0)),
            "implied_upside_pct": analyst.get("implied_upside_pct", 0.0),
            "latest_upgrade": (analyst.get("recent_upgrades_downgrades") or [None])[0],
            "in_congressional_leaders": in_congress,
            "congressional_holders_count": len(CONGRESSIONAL_OWNERSHIP_REGISTRY.get(ticker, [])),
            "in_tom_lee_fundstrat": in_tom_lee,
            "tom_lee_themes": TOM_LEE_FUNDSTRAT_REGISTRY.get(ticker, []),
        }
        with self._lock:
            self._snapshot_cache[ticker] = combined

    def ensure_initialized(self) -> None:
        """Ensure initial market snapshot is populated immediately on startup."""
        if self.cycle_count == 0:
            self.refresh_all_now()

    def start_background_24x7_loop(self) -> None:
        """Start background daemon thread executing `refresh_all_now()` every 3 minutes (180s) 24/7."""
        if self._running:
            return
        self.ensure_initialized()
        self._running = True

        def _worker() -> None:
            while self._running:
                time.sleep(self.refresh_interval_seconds)
                if not self._running:
                    break
                try:
                    self.refresh_all_now()
                except Exception as exc:
                    GLOBAL_LOGGER.emit(
                        severity="ERROR",
                        event_type="DAEMON_REFRESH_ERROR",
                        message=f"24/7 scheduler encountered error: {exc}",
                        agent_name="MarketScannerDaemon24x7",
                    )

        self._thread = threading.Thread(target=_worker, name="OmniMarket24x7Daemon", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Gracefully stop the background daemon."""
        self._running = False

    def get_dashboard_state(self, index_filter: Optional[str] = None) -> Dict[str, Any]:
        """Return current cached screener rows, index cards, and 3-minute countdown metadata."""
        self.ensure_initialized()
        with self._lock:
            snapshots = dict(self._snapshot_cache)
            indices = dict(self._index_summaries)
            flashes = list(self._flashing_alerts)
            last_epoch = self.last_refresh_epoch
            last_iso = self.last_refresh_iso
            cycle = self.cycle_count

        if index_filter and index_filter.upper() in UNIVERSE_TICKER_MAP:
            rows = [snapshots[t] for t in UNIVERSE_TICKER_MAP[index_filter.upper()] if t in snapshots]
        elif index_filter and index_filter.upper() == "BUY_SIGNALS":
            rows = [s for s in snapshots.values() if s["action_signal"] in ("STRONG BUY", "BUY")]
            rows.sort(key=lambda r: r["signal_score"], reverse=True)
        else:
            rows = list(snapshots.values())
            rows.sort(key=lambda r: r["signal_score"], reverse=True)

        next_refresh_in = max(0, int(self.refresh_interval_seconds - (time.time() - last_epoch)))
        return {
            "daemon_status": "RUNNING_24X7",
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "seconds_until_next_refresh": next_refresh_in,
            "last_refresh_iso": last_iso,
            "cycle_count": cycle,
            "indices": indices,
            "flashing_alerts": flashes,
            "equities": rows,
        }


GLOBAL_DAEMON = MarketScannerDaemon24x7()

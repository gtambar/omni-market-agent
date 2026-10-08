#!/usr/bin/env python3
"""
run.py — Entrypoint for OmniMarket Agent (Web Terminal, CLI Query, or Deep Stock Research).

Usage:
  1. Start 24/7 Light-Mode Web Terminal & 3-Min Auto-Refresh Daemon:
     python3 run.py --host 127.0.0.1 --port 8080

  2. Run a single Multi-Agent CLI Query:
     python3 run.py --query "Analyze NVDA technicals and smart money ownership"

  3. Run a Deep Stock Research Dossier (Company + Technical Buy/Sell/Hold):
     python3 run.py --deep-research NVDA
"""

from __future__ import annotations

import argparse
import asyncio
import json

from omni_market_agent.agents.orchestrator import GLOBAL_ORCHESTRATOR
from omni_market_agent.config import SETTINGS
from omni_market_agent.web.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniMarket 24/7 Multi-Modal Stock Market & Deep Research Agent")
    parser.add_argument("--host", default=SETTINGS.host, help="HTTP server bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=SETTINGS.port, help="HTTP server port (default: 8080)")
    parser.add_argument("--query", help="Execute a one-shot grounded multi-agent query and print JSON output")
    parser.add_argument("--deep-research", help="Generate a full Company + Technical Buy/Sell/Hold Deep Research Dossier")
    args = parser.parse_args()

    if args.deep_research:
        result = asyncio.run(GLOBAL_ORCHESTRATOR.run_deep_stock_research(args.deep_research, modality="text"))
        print(json.dumps(result, indent=2))
        return

    if args.query:
        result = asyncio.run(GLOBAL_ORCHESTRATOR.handle_user_request(args.query, modality="text"))
        print(json.dumps(result, indent=2))
        return

    print(f"🚀 Starting OmniMarket Agent (Light Mode Interactive UI) on http://{args.host}:{args.port} ...")
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()

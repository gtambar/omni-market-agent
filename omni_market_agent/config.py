"""
Centralized configuration for OmniMarket Agent.

All sensitive credentials (Gemini, OpenAI, Alpaca, GCP) are retrieved dynamically at runtime
via `SecretManagerVault` (Rubric 5.3 — Secure Secret Management). Zero API keys are hardcoded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
RUNTIME_DATA_DIR = Path(os.environ.get("OMNI_RUNTIME_DIR", str(REPO_ROOT / "runtime_data")))


@dataclass(frozen=True)
class AgentSettings:
    """Immutable runtime settings for the 24/7 OmniMarket Agent daemon and orchestrator."""

    # 24/7 Scheduler settings (updates every 3 minutes = 180 seconds)
    refresh_interval_seconds: int = int(os.environ.get("OMNI_REFRESH_SECONDS", "180"))
    run_24_7_enabled: bool = os.environ.get("OMNI_RUN_24_7", "true").lower() == "true"

    # Strategic Model Routing Tiers (Rubric 3.2)
    fast_model_tier: str = os.environ.get("OMNI_FAST_MODEL", "gemini-2.5-flash")
    reasoning_model_tier: str = os.environ.get("OMNI_REASONING_MODEL", "gemini-2.5-pro")

    # Context & Memory Compaction settings (Rubric 2.2)
    max_history_tokens: int = int(os.environ.get("OMNI_MAX_HISTORY_TOKENS", "4096"))
    sliding_window_turns: int = int(os.environ.get("OMNI_SLIDING_WINDOW_TURNS", "6"))
    vertex_context_cache_ttl_seconds: int = 3600

    # Trade Execution & Human-in-the-Loop (HITL) Guardrails (Rubric 3.3 & 3.4)
    initial_paper_cash_usd: float = float(os.environ.get("OMNI_INITIAL_CASH_USD", "100000.0"))
    hitl_confirmation_threshold_usd: float = float(os.environ.get("OMNI_HITL_THRESHOLD_USD", "2500.0"))
    max_single_order_usd: float = float(os.environ.get("OMNI_MAX_ORDER_USD", "50000.0"))
    always_require_hitl_for_live_broker: bool = True
    broker_mode: str = os.environ.get("OMNI_BROKER_MODE", "paper")  # "paper" or "alpaca_live"

    # Guardrail Self-Evaluation threshold (Rubric 3.3)
    min_self_eval_groundedness_score: float = 0.90

    # GCP Project & Region for Secret Manager / Cloud DLP / Vertex AI
    gcp_project_id: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    gcp_region: str = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

    # Web Server settings
    host: str = os.environ.get("OMNI_HOST", "0.0.0.0")
    port: int = int(os.environ.get("OMNI_PORT", "8080"))


SETTINGS = AgentSettings()

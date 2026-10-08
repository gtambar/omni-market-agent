"""Multi-agent orchestration, constitutional system prompts, and strategic model routing."""
from .constitution import CONSTITUTIONAL_SYSTEM_INSTRUCTION, SUBAGENT_SYSTEM_PROMPTS
from .model_router import GLOBAL_MODEL_ROUTER, StrategicModelRouter
from .orchestrator import GLOBAL_ORCHESTRATOR, OmniMarketMultiAgentOrchestrator, build_google_adk_agent_hierarchy

__all__ = [
    "CONSTITUTIONAL_SYSTEM_INSTRUCTION",
    "SUBAGENT_SYSTEM_PROMPTS",
    "GLOBAL_MODEL_ROUTER",
    "StrategicModelRouter",
    "GLOBAL_ORCHESTRATOR",
    "OmniMarketMultiAgentOrchestrator",
    "build_google_adk_agent_hierarchy",
]

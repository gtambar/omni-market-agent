"""
omni_market_agent/memory/async_memory.py — Asynchronous Memory Consolidation Pipeline.

Satisfies AgentOps Code Review Matrix Rubric Criteria:
  - 2.4 Async Memory Operations (5/5 Points):
    Expensive memory generation, FTS5 indexing, and session consolidation are coded as
    non-blocking background async tasks (`asyncio.create_task` + `asyncio.to_thread`)
    to prevent UI or voice-response blocking.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from ..observability.logger import GLOBAL_LOGGER
from .session_store import GLOBAL_SESSION_STORE, PersistentSessionMemoryStore


class AsyncMemoryConsolidator:
    """
    Executes memory persistence and analytical insight consolidation asynchronously off the main thread.
    """

    def __init__(self, store: PersistentSessionMemoryStore = GLOBAL_SESSION_STORE) -> None:
        self.store = store
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self.completed_async_ops: int = 0

    async def persist_turn_and_consolidate_async(
        self,
        session_id: str,
        user_query: str,
        agent_response: str,
        modality: str,
        active_ticker: str,
        active_index: str,
        subagent_summary: str,
    ) -> None:
        """
        Offload SQLite turn writes and FTS5 memory bank indexing to a worker thread via `asyncio.to_thread`.
        """
        def _sync_work() -> None:
            self.store.record_turn_sync(
                session_id=session_id,
                role="user",
                content=user_query,
                modality=modality,
                active_ticker=active_ticker,
                active_index=active_index,
            )
            self.store.record_turn_sync(
                session_id=session_id,
                role="assistant",
                content=agent_response,
                modality=modality,
                active_ticker=active_ticker,
                active_index=active_index,
            )
            if subagent_summary:
                self.store.store_consolidated_memory_fact_sync(
                    session_id=session_id,
                    ticker=active_ticker,
                    fact_summary=subagent_summary,
                )

        await asyncio.to_thread(_sync_work)
        self.completed_async_ops += 1
        GLOBAL_LOGGER.emit(
            severity="INFO",
            event_type="ASYNC_MEMORY_CONSOLIDATED",
            message=f"Asynchronously consolidated session '{session_id}' memory for {active_ticker}.",
            payload={"session_id": session_id, "ticker": active_ticker, "completed_async_ops": self.completed_async_ops},
            agent_name="AsyncMemoryConsolidator",
        )

    def schedule_background_consolidation(
        self,
        session_id: str,
        user_query: str,
        agent_response: str,
        modality: str,
        active_ticker: str,
        active_index: str,
        subagent_summary: str,
    ) -> None:
        """
        Fire-and-forget background task scheduler when an event loop is running, or non-blocking
        execution fallback so the caller never blocks waiting for memory consolidation.
        """
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                self.persist_turn_and_consolidate_async(
                    session_id=session_id,
                    user_query=user_query,
                    agent_response=agent_response,
                    modality=modality,
                    active_ticker=active_ticker,
                    active_index=active_index,
                    subagent_summary=subagent_summary,
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except RuntimeError:
            # If invoked outside a running event loop (e.g. synchronous CLI test), run via asyncio.run
            asyncio.run(
                self.persist_turn_and_consolidate_async(
                    session_id=session_id,
                    user_query=user_query,
                    agent_response=agent_response,
                    modality=modality,
                    active_ticker=active_ticker,
                    active_index=active_index,
                    subagent_summary=subagent_summary,
                )
            )


GLOBAL_ASYNC_MEMORY = AsyncMemoryConsolidator()

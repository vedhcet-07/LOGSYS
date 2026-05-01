"""
LogMind – Base Agent
Lightweight base class for all LogMind agents.
Provides standardised trace recording without requiring ADK runner complexity.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


class BaseAgent(ABC):
    """
    Abstract base for all LogMind agents.
    Subclasses implement run() and call _trace() to record what they did.
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"logmind.agent.{name}")
        self._trace_log: list[dict[str, Any]] = []

    # ── Trace helpers ────────────────────────────────────────────────────────

    def _trace(self, action: str, result: str) -> dict[str, Any]:
        """Record a trace event and return it as a dict."""
        event: dict[str, Any] = {
            "agent":     self.name,
            "action":    action,
            "result":    result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._trace_log.append(event)
        self.logger.debug("[%s] %s → %s", self.name, action, result[:120])
        return event

    def get_trace(self) -> list[dict[str, Any]]:
        return list(self._trace_log)

    def clear_trace(self) -> None:
        self._trace_log.clear()

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with given inputs and return outputs dict."""
        raise NotImplementedError

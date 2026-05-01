"""
LogMind – Orchestrator Agent
Coordinates the full query pipeline:
  1. Retrieval Agent  → multi-modal evidence + graph context
  2. RCA Agent        → LLM-synthesised root cause analysis
  3. Merge agent traces for frontend transparency
  4. Return a complete RCAOutput
"""
from __future__ import annotations

import logging
from typing import Any

from models import RCAOutput

logger = logging.getLogger("logmind.agent.orchestrator")


class Orchestrator:
    """
    Top-level coordinator for the LogMind query pipeline.
    Does not extend BaseAgent — it holds references to sub-agents
    and assembles the final response.
    """

    def __init__(self):
        from agents.retrieval_agent import RetrievalAgent
        from agents.rca_agent import RCAAgent

        self.retrieval = RetrievalAgent()
        self.rca       = RCAAgent()
        self.logger    = logging.getLogger("logmind.orchestrator")

    def run(self, query: str, session_id: str | None = None) -> RCAOutput:
        """
        Execute the full retrieval → analysis pipeline.

        Args:
            query:      Natural-language incident question from the user.
            session_id: Optional session ID — scopes retrieval to session graph/vectors.
                        None uses the global graph (backward-compatible).

        Returns:
            Fully populated RCAOutput (matches /api/query response schema).
        """
        self.logger.info("Orchestrator: handling query [session=%s] → %s",
                         session_id[:8] + "..." if session_id else "global",
                         query[:80])
        merged_trace: list[dict[str, Any]] = []

        # ── Step 1: Retrieval ─────────────────────────────────────────────
        self.logger.info("  → calling RetrievalAgent ...")
        retrieval_result = self.retrieval.run({"query": query, "session_id": session_id})
        evidence    = retrieval_result.get("evidence", [])
        graph_nodes = retrieval_result.get("graph_nodes", [])
        merged_trace.extend(retrieval_result.get("trace", []))

        self.logger.info("  → Retrieval done: %d evidence, %d graph nodes",
                         len(evidence), len(graph_nodes))

        # ── Step 2: RCA ────────────────────────────────────────────────────
        self.logger.info("  → calling RCAAgent ...")
        rca_result = self.rca.run({
            "query":       query,
            "evidence":    evidence,
            "graph_nodes": graph_nodes,
        })
        rca_output: RCAOutput = rca_result["rca"]
        merged_trace.extend(rca_result.get("trace", []))

        # Attach the merged agent trace to the output
        rca_output.agent_trace = merged_trace

        self.logger.info("  → Orchestrator complete. confidence=%s, services=%s",
                         rca_output.confidence,
                         rca_output.affected_services[:3])
        return rca_output

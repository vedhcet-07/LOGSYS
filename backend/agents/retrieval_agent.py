"""
LogMind – Retrieval Agent
Responsibilities:
  1. Embed the user query
  2. Query Pinecone for top-K similar chunks
  3. Extract seed entities from results + query text
  4. Traverse the NetworkX knowledge graph for related evidence
  5. Fallback: load demo files directly if Pinecone is empty (no API key demo mode)
"""
from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config import DEMO_DIR

logger = logging.getLogger("logmind.agent.retrieval")

# Patterns to extract entity names from a query string
_HYPHEN_RE  = re.compile(r'\b([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)+)\b')   # auth-service, user-db
_CAMEL_RE   = re.compile(r'\b([A-Z][a-zA-Z]*(?:Exception|Error|Timeout))\b')


def _entities_from_query(query: str) -> list[str]:
    """Extract likely entity names (services, errors) from the user query."""
    found = _HYPHEN_RE.findall(query) + _CAMEL_RE.findall(query)
    return list(dict.fromkeys(found))  # dedupe preserving order


def _load_demo_fallback() -> list[dict[str, Any]]:
    """
    When Pinecone has no data (no API key configured), load demo files directly
    and return them as mock evidence. Keeps the system demo-able without any API keys.
    """
    evidence: list[dict[str, Any]] = []
    if not DEMO_DIR.exists():
        return evidence

    try:
        from services.log_parser import parse_log_file
        from services.metrics_parser import parse_metrics_file

        for f in sorted(DEMO_DIR.glob("*")):
            if f.suffix in (".log", ".txt"):
                chunks = parse_log_file(f)
                for c in chunks[:2]:
                    evidence.append({
                        "id":       c.chunk_id,
                        "score":    0.6,
                        "metadata": {"modality": "log", "source_file": f.name, **c.metadata},
                        "snippet":  c.text[:500],
                    })
            elif f.suffix in (".json", ".csv"):
                chunks = parse_metrics_file(f)
                for c in chunks:
                    evidence.append({
                        "id":       c.chunk_id,
                        "score":    0.6,
                        "metadata": {"modality": "metrics", "source_file": f.name, **c.metadata},
                        "snippet":  c.text[:500],
                    })
            elif f.suffix in (".png", ".jpg", ".jpeg"):
                # Use cached vision result if available
                cache = f.with_suffix(".vision_cache.txt")
                if cache.exists():
                    summary = cache.read_text(encoding="utf-8").strip()
                else:
                    summary = f"Dashboard screenshot: {f.name}"
                evidence.append({
                    "id":       str(f.name),
                    "score":    0.5,
                    "metadata": {"modality": "image", "source_file": f.name},
                    "snippet":  summary[:500],
                })
    except Exception as exc:
        logger.warning("Demo fallback load failed: %s", exc)

    return evidence


class RetrievalAgent(BaseAgent):
    """
    Retrieves multi-modal evidence for a user query via vector search + graph traversal.
    Falls back to loading demo data directly when Pinecone is not configured.
    """

    def __init__(self):
        super().__init__("retrieval_agent")

    def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Args:
            inputs: {"query": str}
        Returns:
            {"evidence": list[dict], "graph_nodes": list[dict], "trace": list[dict]}
        """
        query = inputs.get("query", "")
        self.clear_trace()

        # ── Step 1: Embed query ────────────────────────────────────────────
        from services.embedder import embed_query
        qvec = embed_query(query)
        self._trace("embed_query", f"Generated {len(qvec)}-dim query vector")

        # ── Step 2: Pinecone vector search ─────────────────────────────────
        from services.pinecone_store import query as pinecone_query
        matches = pinecone_query(qvec, top_k=5)
        self._trace("pinecone_search", f"Retrieved {len(matches)} vector matches")

        # ── Step 3: Demo fallback if Pinecone empty ────────────────────────
        if not matches:
            self._trace("fallback_triggered", "Pinecone empty — loading demo data directly")
            matches = _load_demo_fallback()
            self._trace("demo_fallback", f"Loaded {len(matches)} evidence items from demo files")

        # ── Step 4: Extract seed entities from results + query ─────────────
        entities: set[str] = set(_entities_from_query(query))
        for m in matches:
            meta = m.get("metadata", {})
            service = meta.get("service", "")
            if service:
                entities.add(service)
            # also check services list stored as comma-separated
            svcs = meta.get("services", "")
            if isinstance(svcs, str):
                for s in svcs.split(","):
                    s = s.strip()
                    if s:
                        entities.add(s)

        self._trace("entity_extraction", f"Seed entities: {list(entities)[:10]}")

        # ── Step 5: Knowledge graph traversal ─────────────────────────────
        from services.graph_store import get_neighbors, get_graph_json
        graph_nodes: list[dict[str, Any]] = []

        if entities:
            for entity in list(entities)[:5]:  # limit to 5 seeds
                neighbors = get_neighbors(entity, depth=2)
                graph_nodes.extend(neighbors)
        else:
            # No entities found — return full graph as context
            gj = get_graph_json()
            graph_nodes = [{"node": n["id"], "attrs": n} for n in gj.get("nodes", [])[:20]]

        # Deduplicate graph nodes
        seen: set[str] = set()
        unique_graph: list[dict[str, Any]] = []
        for gn in graph_nodes:
            key = gn.get("node", "")
            if key not in seen:
                seen.add(key)
                unique_graph.append(gn)

        self._trace("graph_traversal", f"Found {len(unique_graph)} related graph nodes from {len(entities)} entities")

        return {
            "evidence":    matches,
            "graph_nodes": unique_graph,
            "trace":       self.get_trace(),
        }

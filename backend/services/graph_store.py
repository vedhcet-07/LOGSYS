"""
LogMind – Knowledge Graph Store (NetworkX)

Supports two modes:
  - Global graph (session_id=None) — backward-compatible, used by old API routes
  - Session graph (session_id=str) — isolated per-session graph via session_store
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import networkx as nx

logger = logging.getLogger("logmind.graph_store")

# ── Global graph (backward-compat) ───────────────────────────────────────────
_graph: nx.DiGraph = nx.DiGraph()
_GRAPH_PATH = Path(__file__).parent.parent / "data" / "graph.gpickle"


# ── Global graph persistence ──────────────────────────────────────────────────

def load_graph() -> None:
    """Load the global graph singleton from disk."""
    global _graph
    if _GRAPH_PATH.exists():
        try:
            with open(_GRAPH_PATH, "rb") as fh:
                _graph = pickle.load(fh)
            logger.info(
                "Graph loaded: %d nodes, %d edges",
                _graph.number_of_nodes(),
                _graph.number_of_edges(),
            )
        except Exception as exc:
            logger.warning("Could not load graph (%s). Starting fresh.", exc)
            _graph = nx.DiGraph()
    else:
        logger.info("No persisted graph found. Starting with empty graph.")
        _graph = nx.DiGraph()


def save_graph() -> None:
    """Persist the global graph to disk."""
    _GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_GRAPH_PATH, "wb") as fh:
        pickle.dump(_graph, fh)
    logger.debug(
        "Graph saved: %d nodes, %d edges",
        _graph.number_of_nodes(),
        _graph.number_of_edges(),
    )


# ── Graph resolver ────────────────────────────────────────────────────────────

def _resolve_graph(session_id: str | None) -> tuple[nx.DiGraph, bool]:
    """
    Return (graph, is_session_graph).
    If session_id is given, loads the session's isolated graph.
    If session_id is None, returns the global singleton.
    """
    if session_id is not None:
        from services.session_store import get_session_graph
        return get_session_graph(session_id), True
    return _graph, False


def _persist(graph: nx.DiGraph, session_id: str | None) -> None:
    """Save graph to the right place depending on mode."""
    if session_id is not None:
        from services.session_store import save_session_graph
        save_session_graph(session_id, graph)
    else:
        save_graph()


# ── Graph mutation helpers ────────────────────────────────────────────────────

def add_entity(
    name: str,
    entity_type: str,
    session_id: str | None = None,
    **attrs: Any,
) -> None:
    """Add or update a node. Writes to session graph if session_id given."""
    graph, is_session = _resolve_graph(session_id)
    graph.add_node(name, type=entity_type, **attrs)
    _persist(graph, session_id)


def add_relationship(
    src: str,
    dst: str,
    rel_type: str,
    session_id: str | None = None,
    **attrs: Any,
) -> None:
    """Add a directed edge. Writes to session graph if session_id given."""
    graph, is_session = _resolve_graph(session_id)
    graph.add_edge(src, dst, rel=rel_type, **attrs)
    _persist(graph, session_id)


def get_neighbors(
    entity: str,
    depth: int = 2,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return nodes reachable from entity within depth hops."""
    graph, _ = _resolve_graph(session_id)
    if entity not in graph:
        return []
    subgraph_nodes = nx.single_source_shortest_path(graph, entity, cutoff=depth)
    return [
        {"node": node, "path": path, "attrs": dict(graph.nodes[node])}
        for node, path in subgraph_nodes.items()
    ]


# ── Serialization for API ─────────────────────────────────────────────────────

def get_graph_json(session_id: str | None = None) -> dict[str, Any]:
    """Serialize graph to JSON-safe dict. Uses session graph if session_id given."""
    if session_id is not None:
        from services.session_store import get_session_graph_json
        return get_session_graph_json(session_id)
    g = _graph
    return {
        "nodes": [{"id": n, **data} for n, data in g.nodes(data=True)],
        "edges": [{"source": u, "target": v, **data} for u, v, data in g.edges(data=True)],
    }


def get_stats(session_id: str | None = None) -> dict[str, int]:
    """Return node/edge counts for the global or session graph."""
    graph, _ = _resolve_graph(session_id)
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }

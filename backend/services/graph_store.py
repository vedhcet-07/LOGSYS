"""
LogMind – Knowledge Graph Store (NetworkX)
Phase 0: skeleton with load/save/get_graph_json stubs.
Full implementation in Phase 1.
"""

import json
import logging
import os
import pickle
from pathlib import Path
from typing import Any

import networkx as nx

logger = logging.getLogger("logmind.graph_store")

# ---------------------------------------------------------------------------
# Graph singleton
# ---------------------------------------------------------------------------
_graph: nx.DiGraph = nx.DiGraph()

# Persist to the data/ directory so Docker volume survives restarts
_GRAPH_PATH = Path(__file__).parent.parent / "data" / "graph.gpickle"


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def load_graph() -> None:
    """Load persisted graph from disk into the module-level singleton."""
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
    """Persist the current in-memory graph to disk."""
    _GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_GRAPH_PATH, "wb") as fh:
        pickle.dump(_graph, fh)
    logger.debug("Graph saved: %d nodes, %d edges",
                 _graph.number_of_nodes(), _graph.number_of_edges())


# ---------------------------------------------------------------------------
# Graph mutation helpers  (Phase 1 will flesh these out)
# ---------------------------------------------------------------------------
def add_entity(name: str, entity_type: str, **attrs: Any) -> None:
    """Add or update a node in the knowledge graph."""
    _graph.add_node(name, type=entity_type, **attrs)
    save_graph()


def add_relationship(src: str, dst: str, rel_type: str, **attrs: Any) -> None:
    """Add a directed edge between two entities."""
    _graph.add_edge(src, dst, rel=rel_type, **attrs)
    save_graph()


def get_neighbors(entity: str, depth: int = 2) -> list[dict[str, Any]]:
    """Return nodes reachable from *entity* within *depth* hops."""
    if entity not in _graph:
        return []
    subgraph_nodes = nx.single_source_shortest_path(_graph, entity, cutoff=depth)
    results = []
    for node, path in subgraph_nodes.items():
        results.append({"node": node, "path": path, "attrs": _graph.nodes[node]})
    return results


# ---------------------------------------------------------------------------
# Serialization for API  (GET /api/graph)
# ---------------------------------------------------------------------------
def get_graph_json() -> dict[str, Any]:
    """Serialize the graph to a JSON-safe dict for the frontend."""
    nodes = [
        {"id": n, **data}
        for n, data in _graph.nodes(data=True)
    ]
    edges = [
        {"source": u, "target": v, **data}
        for u, v, data in _graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


def get_stats() -> dict[str, int]:
    return {
        "nodes": _graph.number_of_nodes(),
        "edges": _graph.number_of_edges(),
    }

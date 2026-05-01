"""
LogMind – Session Store (Phase 4A)

Each session is a fully isolated analysis context:
  - Its own NetworkX knowledge graph  (graph.gpickle)
  - Its own Pinecone namespace         (namespace = session_id)
  - Its own chat history               (chat_history.json)
  - Metadata persisted in meta.json and the top-level index.json

Storage layout:
  backend/data/sessions/
    index.json                  ← summary list of all sessions
    {session_id}/
      meta.json                 ← id, name, created_at, files, node_count, edge_count
      graph.gpickle             ← isolated NetworkX DiGraph
      chat_history.json         ← [{role, content, timestamp}, ...]
"""
from __future__ import annotations

import json
import logging
import pickle
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx

logger = logging.getLogger("logmind.session_store")

# ── Storage root ──────────────────────────────────────────────────────────────
_SESSIONS_DIR = Path(__file__).parent.parent / "data" / "sessions"
_INDEX_PATH   = _SESSIONS_DIR / "index.json"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _session_dir(session_id: str) -> Path:
    return _SESSIONS_DIR / session_id


def _meta_path(session_id: str) -> Path:
    return _session_dir(session_id) / "meta.json"


def _graph_path(session_id: str) -> Path:
    return _session_dir(session_id) / "graph.gpickle"


def _chat_path(session_id: str) -> Path:
    return _session_dir(session_id) / "chat_history.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_index() -> list[dict]:
    """Load the sessions index.json (creates empty file if missing)."""
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not _INDEX_PATH.exists():
        _INDEX_PATH.write_text("[]", encoding="utf-8")
    try:
        return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_index(entries: list[dict]) -> None:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _INDEX_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _load_meta(session_id: str) -> dict | None:
    p = _meta_path(session_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_meta(meta: dict) -> None:
    sid = meta["id"]
    _session_dir(sid).mkdir(parents=True, exist_ok=True)
    _meta_path(sid).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    # Sync into index
    index = _load_index()
    summary = {
        "id":         meta["id"],
        "name":       meta["name"],
        "created_at": meta["created_at"],
        "files":      meta.get("files", []),
        "node_count": meta.get("node_count", 0),
        "edge_count": meta.get("edge_count", 0),
    }
    index = [e for e in index if e["id"] != meta["id"]]
    index.insert(0, summary)
    _save_index(index)


# ── Public CRUD ───────────────────────────────────────────────────────────────

def create_session(name: str | None = None) -> dict:
    """
    Create a new isolated session.

    Returns:
        Session metadata dict.
    """
    session_id = str(uuid.uuid4())
    now        = _now_iso()
    meta = {
        "id":         session_id,
        "name":       name or f"Session {now[:10]}",
        "created_at": now,
        "files":      [],
        "node_count": 0,
        "edge_count": 0,
    }
    _save_meta(meta)
    # Initialise an empty graph on disk
    save_session_graph(session_id, nx.DiGraph())
    # Initialise empty chat history
    _chat_path(session_id).write_text("[]", encoding="utf-8")
    logger.info("Session created: %s (%s)", session_id, meta["name"])
    return meta


def get_session(session_id: str) -> dict | None:
    """Return session metadata or None if not found."""
    return _load_meta(session_id)


def list_sessions() -> list[dict]:
    """Return all sessions sorted newest-first."""
    return _load_index()


def update_session(session_id: str, **kwargs: Any) -> dict | None:
    """
    Update mutable fields on a session (name, files, node_count, edge_count).
    Returns updated metadata or None if session not found.
    """
    meta = _load_meta(session_id)
    if meta is None:
        logger.warning("update_session: session %s not found", session_id)
        return None
    for key, val in kwargs.items():
        meta[key] = val
    _save_meta(meta)
    return meta


def delete_session(session_id: str) -> bool:
    """
    Delete a session and ALL its data (graph, chat history, metadata).
    Returns True on success, False if session not found.
    """
    if _load_meta(session_id) is None:
        return False

    # Remove directory tree
    import shutil
    shutil.rmtree(_session_dir(session_id), ignore_errors=True)

    # Remove from index
    index = [e for e in _load_index() if e["id"] != session_id]
    _save_index(index)
    logger.info("Session deleted: %s", session_id)
    return True


# ── Graph helpers ─────────────────────────────────────────────────────────────

def get_session_graph(session_id: str) -> nx.DiGraph:
    """
    Load and return the NetworkX DiGraph for this session.
    Returns an empty DiGraph if the session has no graph yet.
    """
    p = _graph_path(session_id)
    if p.exists():
        try:
            with open(p, "rb") as fh:
                return pickle.load(fh)
        except Exception as exc:
            logger.warning("Could not load session graph %s: %s", session_id, exc)
    return nx.DiGraph()


def save_session_graph(session_id: str, graph: nx.DiGraph) -> None:
    """Persist the graph for a session and sync node/edge counts to meta."""
    _session_dir(session_id).mkdir(parents=True, exist_ok=True)
    with open(_graph_path(session_id), "wb") as fh:
        pickle.dump(graph, fh)
    # Sync counts
    meta = _load_meta(session_id)
    if meta:
        meta["node_count"] = graph.number_of_nodes()
        meta["edge_count"] = graph.number_of_edges()
        _save_meta(meta)
    logger.debug(
        "Session graph saved: %s | %d nodes, %d edges",
        session_id, graph.number_of_nodes(), graph.number_of_edges(),
    )


def get_session_graph_json(session_id: str) -> dict[str, Any]:
    """Return graph serialised to JSON-safe dict for the frontend."""
    g = get_session_graph(session_id)
    return {
        "nodes": [{"id": n, **data} for n, data in g.nodes(data=True)],
        "edges": [{"source": u, "target": v, **data} for u, v, data in g.edges(data=True)],
    }


# ── Chat history helpers ──────────────────────────────────────────────────────

def get_session_chat(session_id: str) -> list[dict]:
    """Return the full chat history for a session (list of {role, content, timestamp})."""
    p = _chat_path(session_id)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def append_session_chat(session_id: str, entry: dict) -> None:
    """
    Append a single chat turn to the session's history.

    Args:
        entry: {role: "user"|"assistant", content: str|dict, timestamp?: str}
    """
    if "timestamp" not in entry:
        entry["timestamp"] = _now_iso()
    history = get_session_chat(session_id)
    history.append(entry)
    _chat_path(session_id).write_text(
        json.dumps(history, indent=2, default=str), encoding="utf-8"
    )


def clear_session_chat(session_id: str) -> None:
    """Wipe the chat history for a session."""
    _chat_path(session_id).write_text("[]", encoding="utf-8")

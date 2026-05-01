"""
LogMind API Router – Phase 4B: session-aware routes.

New endpoints:
  POST   /api/sessions                     create a session
  GET    /api/sessions                     list all sessions
  GET    /api/sessions/{id}                get session metadata
  DELETE /api/sessions/{id}                delete session
  POST   /api/sessions/{id}/ingest         ingest files to session
  POST   /api/sessions/{id}/query          query session
  GET    /api/sessions/{id}/graph          session knowledge graph
  GET    /api/sessions/{id}/chat           session chat history

Backward-compat (global graph, no session):
  POST   /api/ingest                       (unchanged)
  POST   /api/query                        (unchanged)
  GET    /api/graph                        (unchanged)
  GET    /api/health                       (unchanged)
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models import BaseChunk, IngestResult, RCAOutput, Session, CreateSessionRequest

logger = logging.getLogger("logmind.api")

router = APIRouter()

# ── Request models ────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str


# ── File extension sets ───────────────────────────────────────────────────────
_LOG_EXTS     = {".log", ".txt"}
_IMAGE_EXTS   = {".png", ".jpg", ".jpeg", ".webp"}
_METRICS_EXTS = {".csv", ".json"}
_ALL_EXTS     = _LOG_EXTS | _IMAGE_EXTS | _METRICS_EXTS


def _detect_modality(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in _LOG_EXTS:     return "log"
    if ext in _IMAGE_EXTS:   return "image"
    if ext in _METRICS_EXTS: return "metrics"
    return "unknown"


# ── Internal ingest helper ────────────────────────────────────────────────────

async def _run_ingest(
    files: list[UploadFile],
    session_id: str | None = None,
) -> IngestResult:
    """
    Core ingest logic shared by global and session-scoped routes.
    Pass session_id=None for the global (backward-compat) pipeline.
    """
    from services import log_parser, image_analyzer, metrics_parser, embedder, pinecone_store
    from services.graph_store import add_entity, add_relationship, get_stats

    result     = IngestResult()
    all_chunks: list[BaseChunk] = []
    errors: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        for upload in files:
            fname = upload.filename or "upload"
            ext   = Path(fname).suffix.lower()

            if ext not in _ALL_EXTS:
                errors.append(f"Skipped {fname}: unsupported extension {ext}")
                continue

            dest    = tmp_path / fname
            content = await upload.read()
            dest.write_bytes(content)
            result.files_processed += 1

            modality = _detect_modality(fname)
            logger.info("Processing %s as %s (session=%s)", fname, modality, session_id or "global")

            try:
                if modality == "log":
                    chunks = log_parser.parse_log_file(dest)
                elif modality == "image":
                    chunks = [image_analyzer.analyze_image(dest)]
                elif modality == "metrics":
                    chunks = metrics_parser.parse_metrics_file(dest)
                else:
                    continue

                all_chunks.extend(chunks)

                # Update knowledge graph (session-scoped or global)
                for chunk in chunks:
                    meta = chunk.metadata
                    add_entity(fname, "file", session_id=session_id, modality=modality)

                    services   = meta.get("services",   [])
                    exceptions = meta.get("exceptions", [])
                    databases  = meta.get("databases",  [])

                    if isinstance(services,   str): services   = [s.strip() for s in services.split(",")   if s.strip()]
                    if isinstance(exceptions, str): exceptions = [e.strip() for e in exceptions.split(",") if e.strip()]
                    if isinstance(databases,  str): databases  = [d.strip() for d in databases.split(",")  if d.strip()]

                    for svc in services:
                        if svc:
                            add_entity(svc, "service", session_id=session_id)
                            add_relationship(fname, svc, "observed_in", session_id=session_id)
                    for exc in exceptions:
                        if exc:
                            add_entity(exc, "error", session_id=session_id)
                            add_relationship(exc, fname, "observed_in", session_id=session_id)
                    for db in databases:
                        if db:
                            add_entity(db, "database", session_id=session_id)
                            add_relationship(fname, db, "observed_in", session_id=session_id)

            except Exception as exc:
                msg = f"Error processing {fname}: {exc}"
                logger.error(msg)
                errors.append(msg)

    # Embed + upsert (namespace = session_id for isolation)
    if all_chunks:
        logger.info("Embedding %d chunks ...", len(all_chunks))
        embeddings  = embedder.embed_batch([c.text for c in all_chunks])
        upsert_info = pinecone_store.upsert_chunks(all_chunks, embeddings, namespace=session_id)
        result.chunks_indexed = upsert_info.get("upserted", 0)
    else:
        result.chunks_indexed = 0

    g = get_stats(session_id=session_id)
    result.graph_nodes = g["nodes"]
    result.graph_edges = g["edges"]
    result.errors      = errors
    result.status      = "success" if not errors else "partial"

    logger.info("Ingest [session=%s]: %d files → %d chunks → %d nodes / %d edges",
                session_id or "global",
                result.files_processed, result.chunks_indexed,
                result.graph_nodes, result.graph_edges)

    # Sync counts back to session metadata
    if session_id:
        from services.session_store import update_session
        update_session(
            session_id,
            node_count=result.graph_nodes,
            edge_count=result.graph_edges,
        )

    return result


# ── Health ────────────────────────────────────────────────────────────────────
@router.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "logmind-backend"}


# ═══════════════════════════════════════════════════════════════════════════════
# Session management endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sessions", response_model=Session, tags=["Sessions"])
async def create_session(request: CreateSessionRequest = CreateSessionRequest()):
    """Create a new isolated analysis session."""
    from services.session_store import create_session as _create
    meta = _create(name=request.name)
    return Session(**meta)


@router.get("/sessions", tags=["Sessions"])
async def list_sessions():
    """List all sessions (newest first)."""
    from services.session_store import list_sessions as _list
    return {"sessions": _list()}


@router.get("/sessions/{session_id}", response_model=Session, tags=["Sessions"])
async def get_session(session_id: str):
    """Get metadata for a single session."""
    from services.session_store import get_session as _get
    meta = _get(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return Session(**meta)


@router.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    """Delete a session and all its data (graph, chat, vectors not deleted from Pinecone)."""
    from services.session_store import delete_session as _delete, get_session as _get
    if _get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    _delete(session_id)
    return {"deleted": True, "session_id": session_id}


# ── Session — Ingest ──────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/ingest", response_model=IngestResult, tags=["Sessions"])
async def session_ingest(session_id: str, files: list[UploadFile] = File(...)):
    """
    Ingest files into a specific session's knowledge graph.
    All parsed chunks are stored with namespace=session_id in Pinecone.
    """
    from services.session_store import get_session as _get, update_session
    meta = _get(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    result = await _run_ingest(files, session_id=session_id)

    # Track uploaded filenames in session metadata
    existing_files = meta.get("files", [])
    new_files = [f.filename for f in files if f.filename and f.filename not in existing_files]
    update_session(session_id, files=existing_files + new_files)

    return result


# ── Session — Query ───────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/query", response_model=RCAOutput, tags=["Sessions"])
async def session_query(session_id: str, request: QueryRequest):
    """
    Run incident analysis scoped to a specific session.
    Only evidence from this session's files and graph is used.
    The Q&A is saved to the session's chat history.
    """
    from services.session_store import get_session as _get, append_session_chat
    meta = _get(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info("Session query [%s]: %s", session_id[:8], request.query)

    try:
        from agents.orchestrator import Orchestrator
        result = Orchestrator().run(request.query, session_id=session_id)

        # Persist Q&A to chat history
        append_session_chat(session_id, {"role": "user",      "content": request.query})
        append_session_chat(session_id, {"role": "assistant", "content": result.model_dump()})

        return result

    except Exception as exc:
        logger.error("Session query error [%s]: %s", session_id[:8], exc, exc_info=True)
        return RCAOutput(
            answer     = f"Analysis error: {exc}",
            root_cause = "Analysis failed — check server logs.",
            confidence = "low",
            agent_trace=[{"agent": "orchestrator", "action": "error", "result": str(exc)}],
        )


# ── Session — Graph ───────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/graph", tags=["Sessions"])
async def session_graph(session_id: str):
    """Return the session's knowledge graph as node/edge JSON."""
    from services.session_store import get_session as _get
    if _get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    from services.graph_store import get_graph_json
    return JSONResponse(content=get_graph_json(session_id=session_id))


# ── Session — Chat history ────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/chat", tags=["Sessions"])
async def session_chat_history(session_id: str):
    """Return the full chat history for a session."""
    from services.session_store import get_session as _get, get_session_chat
    if _get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"session_id": session_id, "history": get_session_chat(session_id)}


@router.delete("/sessions/{session_id}/chat", tags=["Sessions"])
async def clear_session_chat(session_id: str):
    """Clear the chat history for a session (keeps graph and files)."""
    from services.session_store import get_session as _get, clear_session_chat as _clear
    if _get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    _clear(session_id)
    return {"cleared": True, "session_id": session_id}


# ═══════════════════════════════════════════════════════════════════════════════
# Global (backward-compatible) endpoints — no session isolation
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/ingest", response_model=IngestResult, tags=["Pipeline"])
async def ingest_files(files: list[UploadFile] = File(...)):
    """Global ingest — adds to the shared knowledge graph (backward-compat)."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    return await _run_ingest(files, session_id=None)


@router.post("/query", response_model=RCAOutput, tags=["Pipeline"])
async def query_incident(request: QueryRequest):
    """Global query — uses the shared knowledge graph (backward-compat)."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    logger.info("Global query: %s", request.query)
    try:
        from agents.orchestrator import Orchestrator
        return Orchestrator().run(request.query, session_id=None)
    except Exception as exc:
        logger.error("Orchestrator error: %s", exc, exc_info=True)
        return RCAOutput(
            answer     = f"An error occurred: {exc}",
            root_cause = "Analysis failed — check server logs.",
            confidence = "low",
            agent_trace=[{"agent": "orchestrator", "action": "error", "result": str(exc)}],
        )


@router.get("/graph", tags=["Pipeline"])
async def get_graph():
    """Global knowledge graph (backward-compat)."""
    from services.graph_store import get_graph_json
    return JSONResponse(content=get_graph_json(session_id=None))

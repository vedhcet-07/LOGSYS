"""
LogMind API Router – Phase 2: fully wired ingestion + query pipeline.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models import BaseChunk, IngestResult, RCAOutput, EvidenceItem
from services.graph_store import get_graph_json, get_stats as graph_stats, add_entity, add_relationship

logger = logging.getLogger("logmind.api")

router = APIRouter()

# ── Request models ─────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str


# ── Upload extension sets ──────────────────────────────────────────────────────
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


# ── Health ─────────────────────────────────────────────────────────────────────
@router.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "logmind-backend"}


# ── Ingest ─────────────────────────────────────────────────────────────────────
@router.post("/ingest", response_model=IngestResult, tags=["Pipeline"])
async def ingest_files(files: list[UploadFile] = File(...)):
    """
    Upload log files, dashboard images, and/or metrics CSV/JSON.
    Runs the full ingestion pipeline: parse → embed → Pinecone → knowledge graph.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    from services import log_parser, image_analyzer, metrics_parser, embedder, pinecone_store

    result = IngestResult()
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
            logger.info("Processing %s as %s", fname, modality)

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

                # Update knowledge graph
                for chunk in chunks:
                    meta = chunk.metadata
                    add_entity(fname, "file", modality=modality)

                    services   = meta.get("services", [])
                    exceptions = meta.get("exceptions", [])
                    databases  = meta.get("databases", [])

                    if isinstance(services, str):
                        services = [s.strip() for s in services.split(",") if s.strip()]
                    if isinstance(exceptions, str):
                        exceptions = [e.strip() for e in exceptions.split(",") if e.strip()]
                    if isinstance(databases, str):
                        databases = [d.strip() for d in databases.split(",") if d.strip()]

                    for svc in services:
                        if svc:
                            add_entity(svc, "service")
                            add_relationship(fname, svc, "observed_in")
                    for exc in exceptions:
                        if exc:
                            add_entity(exc, "error")
                            add_relationship(exc, fname, "observed_in")
                    for db in databases:
                        if db:
                            add_entity(db, "database")
                            add_relationship(fname, db, "observed_in")

            except Exception as exc:
                msg = f"Error processing {fname}: {exc}"
                logger.error(msg)
                errors.append(msg)

    # Embed + upsert to Pinecone
    if all_chunks:
        logger.info("Embedding %d chunks ...", len(all_chunks))
        embeddings  = embedder.embed_batch([c.text for c in all_chunks])
        upsert_info = pinecone_store.upsert_chunks(all_chunks, embeddings)
        result.chunks_indexed = upsert_info.get("upserted", 0)
    else:
        result.chunks_indexed = 0

    g = graph_stats()
    result.graph_nodes = g["nodes"]
    result.graph_edges = g["edges"]
    result.errors      = errors
    result.status      = "success" if not errors else "partial"

    logger.info("Ingest: %d files → %d chunks → %d nodes / %d edges",
                result.files_processed, result.chunks_indexed,
                result.graph_nodes, result.graph_edges)
    return result


# ── Query ──────────────────────────────────────────────────────────────────────
@router.post("/query", response_model=RCAOutput, tags=["Pipeline"])
async def query_incident(request: QueryRequest):
    """
    Accept a natural-language incident question.
    Runs: RetrievalAgent → RCAAgent via Orchestrator.
    Returns structured RCA with evidence, timeline, recommendations, and agent trace.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info("Query: %s", request.query)

    try:
        from agents.orchestrator import Orchestrator
        orch   = Orchestrator()
        result = orch.run(request.query)
        return result
    except Exception as exc:
        logger.error("Orchestrator error: %s", exc, exc_info=True)
        # Return a safe error response instead of 500
        return RCAOutput(
            answer     = f"An error occurred during analysis: {exc}",
            root_cause = "Analysis failed — check server logs.",
            confidence = "low",
            agent_trace=[{"agent": "orchestrator", "action": "error", "result": str(exc)}],
        )


# ── Graph ──────────────────────────────────────────────────────────────────────
@router.get("/graph", tags=["Pipeline"])
async def get_graph():
    """Return knowledge graph as node/edge JSON for frontend visualization."""
    return JSONResponse(content=get_graph_json())

"""
LogMind API Router – wired for Phase 1 ingestion pipeline.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from models import BaseChunk, IngestResult, RCAOutput, EvidenceItem
from services.graph_store import get_graph_json, get_stats as graph_stats, add_entity, add_relationship

logger = logging.getLogger("logmind.api")

router = APIRouter()

# ── Allowed upload extensions ─────────────────────────────────────────────────
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
    Runs the full ingestion pipeline: parse → embed → Pinecone → graph.
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

            # Save to temp dir
            dest = tmp_path / fname
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

                # Update knowledge graph from entities
                for chunk in chunks:
                    meta = chunk.metadata
                    # Add file node
                    add_entity(fname, "file", modality=modality)
                    # services / exceptions are lists in chunk.metadata
                    services   = meta.get("services", [])
                    exceptions = meta.get("exceptions", [])
                    if isinstance(services, str):   services   = [s for s in services.split(",") if s.strip()]
                    if isinstance(exceptions, str): exceptions = [e for e in exceptions.split(",") if e.strip()]
                    for svc in services:
                        svc = svc.strip()
                        if svc:
                            add_entity(svc, "service")
                            add_relationship(fname, svc, "observed_in")
                    for exc in exceptions:
                        exc = exc.strip()
                        if exc:
                            add_entity(exc, "error")
                            add_relationship(exc, fname, "observed_in")

            except Exception as exc:
                msg = f"Error processing {fname}: {exc}"
                logger.error(msg)
                errors.append(msg)

    # Embed all chunks and upsert to Pinecone
    if all_chunks:
        logger.info("Embedding %d chunks ...", len(all_chunks))
        embeddings = embedder.embed_batch([c.text for c in all_chunks])
        upsert_result = pinecone_store.upsert_chunks(all_chunks, embeddings)
        result.chunks_indexed = upsert_result.get("upserted", len(all_chunks))
    else:
        result.chunks_indexed = 0

    g = graph_stats()
    result.graph_nodes  = g["nodes"]
    result.graph_edges  = g["edges"]
    result.errors       = errors
    result.status       = "success" if not errors else "partial"

    logger.info("Ingest complete: %d files, %d chunks, %d nodes, %d edges",
                result.files_processed, result.chunks_indexed,
                result.graph_nodes, result.graph_edges)
    return result


# ── Query (stub – Phase 2 wires agents) ──────────────────────────────────────
@router.post("/query", response_model=RCAOutput, tags=["Pipeline"])
async def query_incident(body: dict):
    """Accept a natural-language query. Agents wired in Phase 2."""
    question = body.get("query", "")
    logger.info("Query received: %s", question)
    return RCAOutput(
        answer="[Phase 2 stub] Agents not yet wired.",
        root_cause="Pending Phase 2 agent implementation.",
        confidence="low",
    )


# ── Graph ──────────────────────────────────────────────────────────────────────
@router.get("/graph", tags=["Pipeline"])
async def get_graph():
    """Return knowledge graph as node/edge JSON for frontend visualization."""
    return JSONResponse(content=get_graph_json())

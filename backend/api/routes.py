"""
LogMind API Router – stub endpoints for all phases.
Agents will be wired in Phase 2; these stubs keep the server healthy now.
"""

import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("logmind.api")

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str


class IngestResponse(BaseModel):
    status: str
    files_processed: int
    chunks_indexed: int
    graph_nodes: int
    graph_edges: int


class QueryResponse(BaseModel):
    answer: str
    root_cause: str
    evidence: list[dict[str, Any]]
    timeline: list[str]
    recommendations: list[str]
    confidence: str
    agent_trace: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@router.get("/health", tags=["System"])
async def health():
    """Liveness probe used by Docker and CI."""
    return {"status": "ok", "service": "logmind-backend"}


# ---------------------------------------------------------------------------
# Ingest  (Phase 1 / 2 will replace the body with real pipeline)
# ---------------------------------------------------------------------------
@router.post("/ingest", response_model=IngestResponse, tags=["Pipeline"])
async def ingest_files(files: list[UploadFile] = File(...)):
    """
    Accept multipart file upload (logs, images, metrics).
    Stub: validates files received and returns placeholder counts.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    logger.info("Ingest endpoint hit with %d file(s): %s",
                len(files), [f.filename for f in files])

    # TODO (Phase 2): route each file through IngestionAgent
    return IngestResponse(
        status="stub_ok",
        files_processed=len(files),
        chunks_indexed=0,
        graph_nodes=0,
        graph_edges=0,
    )


# ---------------------------------------------------------------------------
# Query  (Phase 2 will wire OrchestratorAgent here)
# ---------------------------------------------------------------------------
@router.post("/query", response_model=QueryResponse, tags=["Pipeline"])
async def query_incident(request: QueryRequest):
    """
    Accept a natural-language incident question and return RCA output.
    Stub: echoes the query and returns placeholder structure.
    """
    logger.info("Query received: %s", request.query)

    # TODO (Phase 2): call OrchestratorAgent
    return QueryResponse(
        answer="[Stub] Agents not yet wired. Check back after Phase 2.",
        root_cause="[Stub]",
        evidence=[],
        timeline=[],
        recommendations=[],
        confidence="low",
        agent_trace=[{"agent": "orchestrator", "action": "stub", "result": "ok"}],
    )


# ---------------------------------------------------------------------------
# Graph  (Phase 2 will return real NetworkX data)
# ---------------------------------------------------------------------------
@router.get("/graph", tags=["Pipeline"])
async def get_graph():
    """Return knowledge graph as node/edge JSON for frontend visualization."""
    from services.graph_store import get_graph_json

    # TODO (Phase 2): populate graph during ingestion
    return JSONResponse(content=get_graph_json())

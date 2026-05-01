"""
LogMind – Shared Pydantic models used across all services.
"""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


class BaseChunk(BaseModel):
    """A single unit of indexed content — log window, metric summary, or image summary."""
    chunk_id: str = Field(default_factory=_new_id)
    source_file: str
    modality: str          # "log" | "metrics" | "image"
    text: str              # Text that will be embedded
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResult(BaseModel):
    status: str = "success"
    files_processed: int = 0
    chunks_indexed: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    errors: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    type: str              # modality
    source: str            # filename
    snippet: str
    score: float = 0.0


class RCAOutput(BaseModel):
    root_cause: str = ""
    summary: str = ""
    timeline: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: str = "low"
    evidence: list[EvidenceItem] = Field(default_factory=list)
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    answer: str = ""


# ── Session models (Phase 4A) ─────────────────────────────────────────────────

class Session(BaseModel):
    """Full session metadata."""
    id: str
    name: str
    created_at: str
    files: list[str] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class SessionList(BaseModel):
    sessions: list[Session]


class ChatEntry(BaseModel):
    """A single turn in a session's chat history."""
    role: str                   # "user" | "assistant"
    content: Any                # str for user, RCAOutput-dict for assistant
    timestamp: str = Field(default_factory=lambda: "")


class CreateSessionRequest(BaseModel):
    name: str | None = None     # optional custom name; auto-generated if omitted


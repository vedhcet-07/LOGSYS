"""
LogMind – Pinecone Vector Store (v3+ API, compatible with pinecone >= 3.x)
Handles index creation, batch upsert, and semantic search.
Initializes lazily so the app starts cleanly even without API keys.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from models import BaseChunk
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME, EMBEDDING_DIM

logger = logging.getLogger("logmind.pinecone_store")

# ── Module state ──────────────────────────────────────────────────────────────
_index = None          # Pinecone Index object
_initialized = False   # True once we've successfully connected


def _get_index():
    """Lazy-init: connect to Pinecone and return the Index object."""
    global _index, _initialized

    if _initialized:
        return _index

    if not PINECONE_API_KEY:
        logger.warning("PINECONE_API_KEY not set — vector store disabled.")
        _initialized = True
        return None

    try:
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=PINECONE_API_KEY)

        # Create index if it doesn't exist
        existing = [idx.name for idx in pc.list_indexes()]
        if PINECONE_INDEX_NAME not in existing:
            logger.info("Creating Pinecone index '%s' (dim=%d) …", PINECONE_INDEX_NAME, EMBEDDING_DIM)
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        _index = pc.Index(PINECONE_INDEX_NAME)
        _initialized = True
        logger.info("Pinecone index '%s' ready.", PINECONE_INDEX_NAME)

    except Exception as exc:
        logger.error("Pinecone init failed: %s — vector store disabled.", exc)
        _initialized = True  # prevent retry storms

    return _index


# ── Public API ────────────────────────────────────────────────────────────────

def upsert_chunks(chunks: list[BaseChunk], embeddings: list[list[float]]) -> dict[str, int]:
    """
    Upsert a list of BaseChunk objects with their pre-computed embeddings.

    Args:
        chunks:     List of BaseChunk objects.
        embeddings: Corresponding embedding vectors (same length as chunks).

    Returns:
        {"upserted": N}
    """
    index = _get_index()
    if index is None:
        logger.warning("Pinecone not available — skipping upsert of %d chunks.", len(chunks))
        return {"upserted": 0}

    if len(chunks) != len(embeddings):
        raise ValueError(f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must match")

    vectors = []
    for chunk, emb in zip(chunks, embeddings):
        # Pinecone metadata values must be str, int, float, or bool (not lists)
        meta: dict[str, Any] = {}
        for k, v in chunk.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                meta[k] = v
            elif isinstance(v, list):
                # Flatten lists to comma-separated string
                meta[k] = ", ".join(str(x) for x in v)
            else:
                meta[k] = str(v)
        meta["text_snippet"] = chunk.text[:500]  # store snippet for retrieval

        vectors.append({
            "id":     chunk.chunk_id,
            "values": emb,
            "metadata": meta,
        })

    # Upsert in batches of 100 (Pinecone limit)
    BATCH = 100
    total_upserted = 0
    for i in range(0, len(vectors), BATCH):
        batch = vectors[i : i + BATCH]
        try:
            index.upsert(vectors=batch)
            total_upserted += len(batch)
            logger.debug("Upserted batch %d/%d (%d vectors)", i // BATCH + 1, (len(vectors) - 1) // BATCH + 1, len(batch))
        except Exception as exc:
            logger.error("Upsert batch failed: %s", exc)

    logger.info("Upserted %d vectors to Pinecone.", total_upserted)
    return {"upserted": total_upserted}


def query(
    embedding: list[float],
    top_k: int = 5,
    filter_dict: Optional[dict] = None,
) -> list[dict[str, Any]]:
    """
    Query Pinecone for the top-K most similar vectors.

    Returns:
        List of dicts with keys: id, score, metadata, snippet.
    """
    index = _get_index()
    if index is None:
        logger.warning("Pinecone not available — returning empty results.")
        return []

    try:
        kwargs: dict[str, Any] = {
            "vector":          embedding,
            "top_k":           top_k,
            "include_metadata": True,
        }
        if filter_dict:
            kwargs["filter"] = filter_dict

        response = index.query(**kwargs)
        results = []
        for match in response.matches:
            results.append({
                "id":       match.id,
                "score":    round(match.score, 4),
                "metadata": match.metadata or {},
                "snippet":  (match.metadata or {}).get("text_snippet", ""),
            })
        return results

    except Exception as exc:
        logger.error("Pinecone query failed: %s", exc)
        return []


def get_stats() -> dict[str, Any]:
    """Return index stats (vector count, etc.)."""
    index = _get_index()
    if index is None:
        return {"status": "disabled"}
    try:
        stats = index.describe_index_stats()
        return {
            "total_vector_count": stats.total_vector_count,
            "dimension":          stats.dimension,
            "index_name":         PINECONE_INDEX_NAME,
        }
    except Exception as exc:
        return {"error": str(exc)}

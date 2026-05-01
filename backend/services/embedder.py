"""
LogMind – Embedder Service
Single interface for generating text embeddings.
Primary: Gemini text-embedding-004 (dim=768)
Fallback: sentence-transformers all-MiniLM-L6-v2 (dim=384 – requires separate Pinecone index)
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from config import GEMINI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIM

LLM_MODEL = "gemini-2.0-flash"

logger = logging.getLogger("logmind.embedder")

# Max chars to send in a single embed call (Gemini limit ~36k tokens)
_MAX_TEXT_CHARS = 25_000

# ── Internal state ────────────────────────────────────────────────────────────
_genai_configured = False


def _configure_genai() -> bool:
    global _genai_configured
    if _genai_configured:
        return True
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — embedder will use fallback zeros.")
        return False
    try:
        from google import genai  # noqa: F401 – just verify import works
        _genai_configured = True
        return True
    except ImportError:
        logger.warning("google-genai not installed. Run: pip install google-genai")
        return False


def _embed_gemini(text: str, task_type: str = "retrieval_document") -> list[float]:
    """Call Gemini embedding model and return a 768-dim vector."""
    from google import genai
    from google.genai import types as gtypes
    if len(text) > _MAX_TEXT_CHARS:
        text = text[:_MAX_TEXT_CHARS]
    client = genai.Client(api_key=GEMINI_API_KEY)
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=gtypes.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIM,  # 768 — Matryoshka truncation
        ),
    )
    return result.embeddings[0].values


def _embed_fallback(text: str) -> list[float]:
    """Zero vector fallback when no embedding provider is available."""
    logger.debug("Returning zero vector fallback for embedding.")
    return [0.0] * EMBEDDING_DIM


# ── Public API ────────────────────────────────────────────────────────────────

def embed(text: str, task_type: str = "retrieval_document") -> list[float]:
    """
    Embed a single text string.

    Args:
        text:      Text to embed.
        task_type: Gemini task type ("retrieval_document" or "retrieval_query").

    Returns:
        Embedding vector as list[float].
    """
    if not text or not text.strip():
        return _embed_fallback("")

    if _configure_genai():
        for attempt in range(3):
            try:
                return _embed_gemini(text, task_type)
            except Exception as exc:
                wait = 2 ** attempt
                logger.warning("Embed attempt %d failed: %s — retrying in %ds", attempt + 1, exc, wait)
                time.sleep(wait)
        logger.error("All embed attempts failed — returning zero vector.")

    return _embed_fallback(text)


def embed_query(text: str) -> list[float]:
    """Embed a user query (uses retrieval_query task type for better recall)."""
    return embed(text, task_type="retrieval_query")


def embed_batch(texts: list[str], delay: float = 0.1) -> list[list[float]]:
    """
    Embed a list of texts sequentially.
    Small delay between calls to respect rate limits.
    """
    results = []
    for i, text in enumerate(texts):
        results.append(embed(text))
        if i < len(texts) - 1:
            time.sleep(delay)
    return results

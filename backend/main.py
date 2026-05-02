"""
LogMind – FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from services.graph_store import load_graph

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("logmind")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load persisted graph on startup; clean up on shutdown."""
    logger.info("LogMind backend starting …")
    load_graph()          # rehydrate NetworkX graph from disk (no-op if missing)
    yield
    logger.info("LogMind backend shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LogMind API",
    description="Multi-Modal Graph RAG Incident Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS – allow all origins so Railway/Render/cloud frontends work
# In production you can restrict this to your frontend domain
import os as _os
_ALLOWED_ORIGIN = _os.getenv("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # wildcard — safe because API keys live server-side
    allow_credentials=False,       # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes (prefix /api)
app.include_router(router, prefix="/api")

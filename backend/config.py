"""
LogMind – Centralised configuration loaded from environment variables.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env — try project root first, then backend dir, then skip silently
# On Railway/cloud, env vars are injected directly — no .env file needed
_root    = Path(__file__).parent.parent
_backend = Path(__file__).parent
for _env_path in [_root / ".env", _backend / ".env"]:
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
        break

# ── LLM / Vision ─────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ── Pinecone ──────────────────────────────────────────────────────────────────
PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "logmind-index")

# ── LLM model ─────────────────────────────────────────────────────────────────
LLM_MODEL: str    = os.getenv("LLM_MODEL",    "gemini-2.0-flash")   # text RCA (Groq or Gemini)
VISION_MODEL: str = os.getenv("VISION_MODEL", "gemini-2.0-flash")   # vision/image — always Gemini

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "768"))
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "")

# ── App ───────────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
DATA_DIR: Path = Path(__file__).parent / "data"
DEMO_DIR: Path = DATA_DIR / "demo"

# Chunking
LOG_CHUNK_SIZE: int = 50    # lines per chunk
LOG_CHUNK_OVERLAP: int = 10  # overlap lines

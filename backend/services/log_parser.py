"""
LogMind – Log Parser Service
Supports Python logging, JSON logs, Apache/nginx, and generic timestamp formats.
Chunks logs into overlapping windows and extracts entities for the knowledge graph.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from models import BaseChunk
from config import LOG_CHUNK_SIZE, LOG_CHUNK_OVERLAP

logger = logging.getLogger("logmind.log_parser")

# ── Regex patterns ────────────────────────────────────────────────────────────
_PYTHON_LOG = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.\d]*)"
    r"[\s|–-]+"
    r"(?P<service>[^\s|–-][^\s|–-]*?)"
    r"[\s|–-]+"
    r"(?P<severity>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL)"
    r"[\s|–-]+"
    r"(?P<message>.*)",
    re.IGNORECASE,
)
_GENERIC_TS = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.\d]*Z?)"
    r".*?(?P<severity>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL)",
    re.IGNORECASE,
)
_APACHE_LOG = re.compile(
    r'(?P<ip>[\d.]+)\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<request>[^"]+)"\s+(?P<status>\d{3})'
)

_EXCEPTION_RE = re.compile(r"\b([A-Z][a-zA-Z]*(?:Exception|Error|Timeout|Failure))\b")
_HTTP_RE      = re.compile(r"\b([45]\d{2})\b")
_ENDPOINT_RE  = re.compile(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s"\']+)', re.IGNORECASE)
_SERVICE_RE   = re.compile(r'(?:service|component|module|app)[=:\s"\']+([a-zA-Z0-9_-]+)', re.IGNORECASE)
_DB_RE        = re.compile(
    r'\b(mysql|postgres(?:ql)?|redis|mongodb|sqlite|elasticsearch|cassandra|dynamodb|user-db|auth-db)\b',
    re.IGNORECASE,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_line(line: str) -> dict[str, Any]:
    """Parse a single log line into a structured dict."""
    line = line.strip()
    if not line:
        return {"raw": line}

    # Try JSON first
    if line.startswith("{"):
        try:
            rec = json.loads(line)
            return {
                "timestamp": rec.get("timestamp") or rec.get("time") or rec.get("ts", ""),
                "severity":  (rec.get("level") or rec.get("severity") or rec.get("lvl", "INFO")).upper(),
                "service":   rec.get("service") or rec.get("logger") or rec.get("name", ""),
                "message":   rec.get("message") or rec.get("msg") or rec.get("text", line),
                "raw":       line,
            }
        except json.JSONDecodeError:
            pass

    # Try Python logging format
    m = _PYTHON_LOG.match(line)
    if m:
        return {
            "timestamp": m.group("timestamp"),
            "severity":  m.group("severity").upper(),
            "service":   m.group("service"),
            "message":   m.group("message"),
            "raw":       line,
        }

    # Try Apache/nginx
    m = _APACHE_LOG.match(line)
    if m:
        return {
            "timestamp": m.group("timestamp"),
            "severity":  "ERROR" if int(m.group("status")) >= 500 else "INFO",
            "service":   "http-server",
            "message":   m.group("request") + " " + m.group("status"),
            "raw":       line,
        }

    # Generic – just grab timestamp + severity if present
    m = _GENERIC_TS.match(line)
    if m:
        return {
            "timestamp": m.group("timestamp"),
            "severity":  m.group("severity").upper(),
            "service":   "",
            "message":   line,
            "raw":       line,
        }

    return {"raw": line, "message": line, "severity": "INFO", "timestamp": "", "service": ""}


def _extract_entities(lines: list[dict]) -> dict[str, list[str]]:
    """Extract entity lists from a window of parsed log lines."""
    combined = " ".join(l.get("raw", "") for l in lines)
    return {
        "exceptions": list(set(_EXCEPTION_RE.findall(combined))),
        "http_codes":  list(set(_HTTP_RE.findall(combined))),
        "endpoints":   list(set(_ENDPOINT_RE.findall(combined))),
        "services":    list(set(filter(None, [l.get("service", "") for l in lines]))),
        "databases":   list(set(_DB_RE.findall(combined))),
    }


def _chunk_lines(parsed: list[dict], source_file: str) -> list[BaseChunk]:
    """Slide a window over parsed lines and create BaseChunk objects."""
    chunks: list[BaseChunk] = []
    step = max(1, LOG_CHUNK_SIZE - LOG_CHUNK_OVERLAP)
    total = len(parsed)

    for start in range(0, total, step):
        end = min(start + LOG_CHUNK_SIZE, total)
        window = parsed[start:end]
        if not window:
            break

        text_lines = [l.get("raw", "") for l in window]
        text = "\n".join(text_lines)

        entities = _extract_entities(window)
        first_ts  = next((l["timestamp"] for l in window if l.get("timestamp")), "")
        last_ts   = next((l["timestamp"] for l in reversed(window) if l.get("timestamp")), "")
        severity  = "ERROR" if any(l.get("severity") in ("ERROR", "CRITICAL") for l in window) else "INFO"

        metadata: dict[str, Any] = {
            "modality":    "log",
            "source_file": source_file,
            "start_line":  start + 1,
            "end_line":    end,
            "timestamp":   first_ts,
            "time_range":  f"{first_ts} – {last_ts}" if last_ts else first_ts,
            "severity":    severity,
            **entities,
        }
        # Flatten service list to single string for Pinecone metadata filtering
        if entities["services"]:
            metadata["service"] = entities["services"][0]

        chunks.append(BaseChunk(
            source_file=source_file,
            modality="log",
            text=text,
            metadata=metadata,
        ))

        if end >= total:
            break

    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def parse_log_file(file_path: str | Path) -> list[BaseChunk]:
    """
    Parse a log file into a list of BaseChunk objects ready for embedding.

    Args:
        file_path: Path to the .log or .txt file.

    Returns:
        List of BaseChunk objects (one per window).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    logger.info("Parsing log file: %s", path.name)
    try:
        raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as exc:
        logger.error("Failed to read %s: %s", path, exc)
        return []

    parsed = [_parse_line(line) for line in raw_lines]
    chunks = _chunk_lines(parsed, path.name)

    logger.info("  → %d lines → %d chunks", len(raw_lines), len(chunks))
    return chunks

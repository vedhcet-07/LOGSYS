"""
LogMind – Image Analyzer Service
Uses Gemini Vision to extract structured incident observations from dashboard screenshots.
Results are cached to a .txt sidecar file to avoid repeated API calls.
"""
from __future__ import annotations

import logging
from pathlib import Path

from models import BaseChunk
from config import GEMINI_API_KEY, VISION_MODEL

logger = logging.getLogger("logmind.image_analyzer")

_VISION_PROMPT = """You are an SRE analyzing a system monitoring dashboard screenshot.
Describe what you observe in structured form:
1. Which services or components are shown?
2. Are there any visible anomalies, spikes, or drops in metrics?
3. What time window does the dashboard cover?
4. What specific metric values are abnormal (CPU%, latency ms, error rate, etc.)?
5. What is the likely operational impact?

Be specific with numbers when visible. Output a concise incident summary paragraph."""


def _get_cache_path(image_path: Path) -> Path:
    return image_path.with_suffix(".vision_cache.txt")


def _call_gemini_vision(image_path: Path) -> str:
    """
    Call Gemini Vision API to analyse a dashboard screenshot.
    Always uses VISION_MODEL (Gemini) — Groq does not support image input.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — vision analysis unavailable.")
        return f"[Vision unavailable] Set GEMINI_API_KEY to enable dashboard analysis: {image_path.name}"
    try:
        import io
        from google import genai
        from google.genai import types as gtypes
        from PIL import Image as PILImage

        client = genai.Client(api_key=GEMINI_API_KEY)
        img    = PILImage.open(image_path)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                _VISION_PROMPT,
                gtypes.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            ],
        )
        return response.text.strip()
    except ImportError:
        logger.warning("google-genai or pillow not installed.")
        return f"[Vision unavailable] Dashboard screenshot: {image_path.name}"
    except Exception as exc:
        logger.error("Gemini Vision call failed for %s: %s", image_path.name, exc)
        return f"[Vision error] Could not analyze {image_path.name}: {exc}"



def analyze_image(file_path: str | Path) -> BaseChunk:
    """
    Analyze a dashboard screenshot using Gemini Vision.
    Results are cached to avoid repeated API calls during demos.

    Args:
        file_path: Path to the .png or .jpg file.

    Returns:
        A BaseChunk with the vision-extracted text summary.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    cache_path = _get_cache_path(path)

    # Use cache if available
    if cache_path.exists():
        summary = cache_path.read_text(encoding="utf-8").strip()
        logger.info("Loaded cached vision summary for %s", path.name)
    else:
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set — returning placeholder for %s", path.name)
            summary = f"[No API key] Dashboard screenshot: {path.name}. Set GEMINI_API_KEY to enable vision analysis."
        else:
            logger.info("Calling Gemini Vision for %s ...", path.name)
            summary = _call_gemini_vision(path)
            # Cache the result
            cache_path.write_text(summary, encoding="utf-8")
            logger.info("Vision summary cached to %s", cache_path.name)

    return BaseChunk(
        source_file=path.name,
        modality="image",
        text=summary,
        metadata={
            "modality":    "image",
            "source_file": path.name,
            "cached":      cache_path.exists(),
        },
    )

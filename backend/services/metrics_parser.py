"""
LogMind – Metrics Parser Service
Loads CSV / JSON time-series data, detects anomalies (spikes + threshold breaches),
and converts findings into text summaries for embedding.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from models import BaseChunk

logger = logging.getLogger("logmind.metrics_parser")

# Absolute thresholds for common metrics
_THRESHOLDS: dict[str, float] = {
    "cpu_percent":     80.0,
    "cpu":             80.0,
    "memory_percent":  85.0,
    "memory":          85.0,
    "error_rate":       0.05,
    "db_latency_ms":  500.0,
    "api_latency_ms": 1000.0,
    "latency_ms":     1000.0,
    "latency":        1000.0,
}


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    # {"metrics": [...]} or {"data": [...]}
    for key in ("metrics", "data", "records", "rows"):
        if isinstance(raw.get(key), list):
            return raw[key]
    # Columnar format: {"cpu": [...], "timestamps": [...]}
    keys = list(raw.keys())
    ts_key = next((k for k in keys if "time" in k.lower()), None)
    if ts_key:
        n = len(raw[ts_key])
        records = []
        for i in range(n):
            rec: dict[str, Any] = {}
            for k in keys:
                if isinstance(raw[k], list) and i < len(raw[k]):
                    rec[k] = raw[k][i]
            records.append(rec)
        return records
    return [raw]


def _load_csv(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
        df = pd.read_csv(path)
        return df.to_dict(orient="records")
    except Exception as exc:
        logger.error("CSV load failed for %s: %s", path.name, exc)
        return []


# ── Anomaly detection ─────────────────────────────────────────────────────────

def _detect_anomalies(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Detect spikes using rolling z-score (window=5) and absolute thresholds.
    Returns a list of anomaly dicts with field, value, threshold/zscore, and timestamp.
    """
    if not records:
        return []

    anomalies: list[dict[str, Any]] = []
    numeric_keys = [
        k for k in records[0].keys()
        if k.lower() not in ("timestamp", "time", "ts", "date")
        and isinstance(records[0][k], (int, float))
    ]

    WINDOW = 5

    for key in numeric_keys:
        values = [r.get(key) for r in records]
        values_clean = [v for v in values if v is not None]
        if len(values_clean) < 2:
            continue

        mean = sum(values_clean) / len(values_clean)
        variance = sum((v - mean) ** 2 for v in values_clean) / len(values_clean)
        std = variance ** 0.5

        for i, rec in enumerate(records):
            val = rec.get(key)
            if val is None:
                continue
            ts = rec.get("timestamp") or rec.get("time") or rec.get("ts") or f"index_{i}"

            # Z-score spike (rolling window)
            window_vals = values_clean[max(0, i - WINDOW): i + 1]
            if len(window_vals) >= 2:
                w_mean = sum(window_vals) / len(window_vals)
                w_var  = sum((v - w_mean) ** 2 for v in window_vals) / len(window_vals)
                w_std  = w_var ** 0.5
                zscore = abs(val - w_mean) / (w_std + 1e-9)
                if zscore > 2.5:
                    anomalies.append({
                        "field": key, "value": val, "timestamp": ts,
                        "reason": f"z-score spike ({zscore:.1f}σ above rolling mean {w_mean:.1f})",
                    })
                    continue

            # Absolute threshold breach
            thresh = _THRESHOLDS.get(key.lower())
            if thresh is not None and val > thresh:
                anomalies.append({
                    "field": key, "value": val, "timestamp": ts,
                    "reason": f"threshold breach (value={val:.1f}, threshold={thresh})",
                })

    return anomalies


def _records_to_text(records: list[dict], anomalies: list[dict], source_file: str) -> str:
    """Convert metric records + anomaly list into a human-readable text summary."""
    lines = [f"Metrics file: {source_file}"]
    lines.append(f"Total data points: {len(records)}")

    if records:
        keys = [k for k in records[0].keys() if k.lower() not in ("timestamp", "time", "ts")]
        lines.append(f"Metrics tracked: {', '.join(keys)}")

        ts_key = next((k for k in records[0].keys() if "time" in k.lower()), None)
        if ts_key:
            first = records[0].get(ts_key, "")
            last  = records[-1].get(ts_key, "")
            lines.append(f"Time range: {first} to {last}")

    if anomalies:
        lines.append(f"\nAnomalies detected ({len(anomalies)}):")
        for a in anomalies:
            lines.append(f"  - [{a['timestamp']}] {a['field']} = {a['value']}: {a['reason']}")
    else:
        lines.append("\nNo significant anomalies detected.")

    return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def parse_metrics_file(file_path: str | Path) -> list[BaseChunk]:
    """
    Parse a CSV or JSON metrics file into BaseChunk objects.

    Args:
        file_path: Path to the .csv or .json file.

    Returns:
        List of BaseChunk objects (typically 1–3 chunks per file).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found: {path}")

    logger.info("Parsing metrics file: %s", path.name)

    suffix = path.suffix.lower()
    if suffix == ".json":
        records = _load_json(path)
    elif suffix == ".csv":
        records = _load_csv(path)
    else:
        logger.warning("Unknown extension %s — trying JSON", suffix)
        try:
            records = _load_json(path)
        except Exception:
            records = _load_csv(path)

    if not records:
        logger.warning("No records loaded from %s", path.name)
        return []

    anomalies = _detect_anomalies(records)
    summary_text = _records_to_text(records, anomalies, path.name)

    metadata: dict[str, Any] = {
        "modality":        "metrics",
        "source_file":     path.name,
        "record_count":    len(records),
        "anomaly_count":   len(anomalies),
        "anomaly_fields":  list({a["field"] for a in anomalies}),
    }

    chunk = BaseChunk(
        source_file=path.name,
        modality="metrics",
        text=summary_text,
        metadata=metadata,
    )

    logger.info("  → %d records, %d anomalies, 1 chunk", len(records), len(anomalies))
    return [chunk]

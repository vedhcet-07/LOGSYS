"""
LogMind – RCA Agent
Responsibilities:
  1. Build a structured context from retrieved evidence + graph nodes
  2. Call Gemini LLM with an SRE-focused RCA prompt
  3. Parse structured JSON output
  4. Fallback: template-based RCA from evidence when no API key is configured
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from agents.base_agent import BaseAgent
from config import GEMINI_API_KEY
from models import RCAOutput, EvidenceItem

logger = logging.getLogger("logmind.agent.rca")

# ── Prompt ────────────────────────────────────────────────────────────────────
_RCA_PROMPT = """You are an expert SRE (Site Reliability Engineer) performing root cause analysis on a production incident.

Analyze the following evidence retrieved from logs, metrics, and dashboard screenshots, then answer the user's question.

== User Question ==
{query}

== Retrieved Evidence ==
{evidence_text}

== Knowledge Graph Context ==
{graph_text}

== Instructions ==
- Answer ONLY based on the provided evidence. Do not invent facts.
- Identify the most likely root cause and explain the chain of events.
- If evidence is incomplete, state your confidence level accordingly.
- Provide a chronological timeline of events.
- List all affected services.
- Give 2-4 specific, actionable recommendations.
- Cite which modality (log / metrics / image) supports each key finding.

Respond with ONLY valid JSON — no markdown, no explanation outside the JSON:
{{
  "root_cause": "One-sentence root cause statement",
  "summary": "2-3 sentence incident summary citing evidence sources",
  "timeline": ["HH:MM event 1 [source]", "HH:MM event 2 [source]"],
  "affected_services": ["service1", "service2"],
  "recommendations": ["Specific recommendation 1", "Specific recommendation 2"],
  "confidence": "high|medium|low",
  "answer": "Full natural-language answer to the user's specific question"
}}"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_evidence(evidence: list[dict]) -> str:
    if not evidence:
        return "No evidence retrieved."
    lines = []
    for i, e in enumerate(evidence[:8], 1):
        meta     = e.get("metadata", {})
        modality = meta.get("modality", "unknown").upper()
        source   = meta.get("source_file", "unknown")
        score    = e.get("score", 0.0)
        snippet  = e.get("snippet", "")[:400]
        lines.append(f"[{i}] [{modality}] {source} (relevance={score:.2f})\n{snippet}")
    return "\n\n".join(lines)


def _format_graph(graph_nodes: list[dict]) -> str:
    if not graph_nodes:
        return "No graph context available."
    lines = []
    for gn in graph_nodes[:15]:
        node  = gn.get("node", "?")
        attrs = gn.get("attrs", {})
        ntype = attrs.get("type", "entity")
        path  = gn.get("path", [])
        if len(path) > 1:
            lines.append(f"  {node} ({ntype}) — reachable via: {' → '.join(str(p) for p in path)}")
        else:
            lines.append(f"  {node} ({ntype})")
    return "Related knowledge graph entities:\n" + "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM response (handles markdown fences)."""
    text = text.strip()

    # Direct JSON
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # JSON inside ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Greedy JSON object extraction
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass

    return {}


def _template_rca(query: str, evidence: list[dict], graph_nodes: list[dict]) -> dict:
    """
    Template-based RCA used when GEMINI_API_KEY is not set.
    Produces a reasonable answer purely from the retrieved evidence.
    """
    services  = list({e.get("metadata", {}).get("service", "") for e in evidence if e.get("metadata", {}).get("service")})
    anomalies = [e for e in evidence if e.get("metadata", {}).get("anomaly_count", 0)]

    # Try to extract error lines from log snippets
    error_lines: list[str] = []
    for e in evidence:
        snippet = e.get("snippet", "")
        for line in snippet.splitlines():
            if any(kw in line.upper() for kw in ("ERROR", "CRITICAL", "TIMEOUT", "EXHAUSTED")):
                error_lines.append(line.strip()[:120])
    error_lines = error_lines[:5]

    graph_types = {}
    for gn in graph_nodes:
        t = gn.get("attrs", {}).get("type", "entity")
        graph_types.setdefault(t, []).append(gn.get("node", "?"))

    root_cause = (
        f"Based on retrieved logs and metrics: {error_lines[0]}"
        if error_lines else "Unable to determine root cause — please set GEMINI_API_KEY for LLM analysis."
    )

    recommendations = [
        "Review database connection pool configuration and set appropriate limits.",
        "Implement circuit breakers on all downstream service calls.",
        "Add health check probes and auto-restart policies for critical services.",
        "Set up alerting on connection pool utilization (>70% threshold).",
    ]

    return {
        "root_cause":        root_cause,
        "summary":           f"Analysis based on {len(evidence)} evidence items across logs and metrics. {len(error_lines)} error events detected. Affected services: {', '.join(services) if services else 'unknown'}.",
        "timeline":          [line[:100] for line in error_lines],
        "affected_services": services or ["unknown"],
        "recommendations":   recommendations,
        "confidence":        "medium" if evidence else "low",
        "answer":            f"[Template mode — set GEMINI_API_KEY for full LLM analysis]\n\nQuery: {query}\n\nTop errors found:\n" + "\n".join(f"- {l}" for l in error_lines),
    }


# ── Agent class ───────────────────────────────────────────────────────────────

class RCAAgent(BaseAgent):
    """
    Generates a structured Root Cause Analysis by calling Gemini with
    the retrieved evidence and graph context. Falls back to a template
    response when no API key is configured.
    """

    def __init__(self):
        super().__init__("rca_agent")

    def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Args:
            inputs: {
                "query": str,
                "evidence": list[dict],
                "graph_nodes": list[dict]
            }
        Returns:
            {"rca": RCAOutput, "trace": list[dict]}
        """
        query       = inputs.get("query", "")
        evidence    = inputs.get("evidence", [])
        graph_nodes = inputs.get("graph_nodes", [])
        self.clear_trace()

        evidence_text = _format_evidence(evidence)
        graph_text    = _format_graph(graph_nodes)

        self._trace("context_build", f"Built context: {len(evidence)} evidence items, {len(graph_nodes)} graph nodes")

        # ── LLM call ──────────────────────────────────────────────────────
        rca_dict: dict = {}

        if not GEMINI_API_KEY:
            self._trace("llm_skip", "No GEMINI_API_KEY — using template RCA")
            rca_dict = _template_rca(query, evidence, graph_nodes)
        else:
            prompt = _RCA_PROMPT.format(
                query=query,
                evidence_text=evidence_text,
                graph_text=graph_text,
            )
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                model    = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                raw_text = response.text
                self._trace("llm_call", f"Gemini response received ({len(raw_text)} chars)")

                rca_dict = _extract_json(raw_text)
                if not rca_dict:
                    self._trace("json_parse_fail", "Could not extract JSON — falling back to template")
                    rca_dict = _template_rca(query, evidence, graph_nodes)
                else:
                    self._trace("json_parse_ok", f"Confidence: {rca_dict.get('confidence', 'unknown')}")

            except Exception as exc:
                logger.error("LLM call failed: %s", exc)
                self._trace("llm_error", f"Error: {exc} — falling back to template")
                rca_dict = _template_rca(query, evidence, graph_nodes)

        # ── Build EvidenceItem list ───────────────────────────────────────
        evidence_items = [
            EvidenceItem(
                type=e.get("metadata", {}).get("modality", "unknown"),
                source=e.get("metadata", {}).get("source_file", "unknown"),
                snippet=e.get("snippet", "")[:300],
                score=e.get("score", 0.0),
            )
            for e in evidence[:6]
        ]

        rca_output = RCAOutput(
            root_cause        = rca_dict.get("root_cause", ""),
            summary           = rca_dict.get("summary", ""),
            timeline          = rca_dict.get("timeline", []),
            affected_services = rca_dict.get("affected_services", []),
            recommendations   = rca_dict.get("recommendations", []),
            confidence        = rca_dict.get("confidence", "low"),
            answer            = rca_dict.get("answer", rca_dict.get("summary", "")),
            evidence          = evidence_items,
        )

        self._trace("rca_complete", f"RCA generated. Confidence={rca_output.confidence}, Services={rca_output.affected_services[:3]}")

        return {"rca": rca_output, "trace": self.get_trace()}

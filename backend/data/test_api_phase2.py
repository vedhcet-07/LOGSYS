"""Full Phase 2 live API test."""
import httpx, json, sys

BASE = "http://localhost:8000/api"

# ── 1. Health ──────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/health")
assert r.status_code == 200
print("[PASS] GET /api/health ->", r.json())

# ── 2. Ingest all 3 demo files ─────────────────────────────────────────────
demo = "backend/data/demo"
files = [
    ("files", ("demo_app.log",       open(f"{demo}/demo_app.log",       "rb"), "text/plain")),
    ("files", ("demo_metrics.json",  open(f"{demo}/demo_metrics.json",  "rb"), "application/json")),
    ("files", ("demo_dashboard.png", open(f"{demo}/demo_dashboard.png", "rb"), "image/png")),
]
r = httpx.post(f"{BASE}/ingest", files=files, timeout=60)
assert r.status_code == 200, f"Ingest failed: {r.text}"
ingest = r.json()
print("[PASS] POST /api/ingest ->", ingest)
assert ingest["files_processed"] == 3
assert not ingest["errors"], f"Ingest errors: {ingest['errors']}"

# ── 3. Query ───────────────────────────────────────────────────────────────
r = httpx.post(f"{BASE}/query", json={"query": "Why did auth-service fail around 2:31 AM?"}, timeout=60)
assert r.status_code == 200, f"Query failed: {r.text}"
qdata = r.json()

print()
print("[PASS] POST /api/query")
print("  root_cause       :", qdata.get("root_cause", "")[:100])
print("  confidence       :", qdata.get("confidence"))
print("  affected_services:", qdata.get("affected_services"))
print("  recommendations  :", len(qdata.get("recommendations", [])))
print("  evidence items   :", len(qdata.get("evidence", [])))
print("  agent_trace evts :", len(qdata.get("agent_trace", [])))
print("  answer (preview) :", str(qdata.get("answer", ""))[:100])

# Validate schema
assert "root_cause"   in qdata
assert "confidence"   in qdata
assert "evidence"     in qdata
assert "agent_trace"  in qdata
assert len(qdata["agent_trace"]) >= 3  # at least retrieval + rca events

# ── 4. Graph ───────────────────────────────────────────────────────────────
r = httpx.get(f"{BASE}/graph")
assert r.status_code == 200
gdata = r.json()
print()
print("[PASS] GET /api/graph ->", len(gdata["nodes"]), "nodes,", len(gdata["edges"]), "edges")

print()
print("=" * 50)
print("PHASE 2 LIVE API TEST: ALL PASSED")
print("=" * 50)

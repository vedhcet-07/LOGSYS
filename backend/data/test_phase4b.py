"""
Phase 4B Live API Test — Session-Aware Ingest + Query + Graph + Chat
Requires backend running: uvicorn main:app --port 8000 --app-dir backend
Run: .venv\Scripts\python backend\data\test_phase4b.py
"""
import sys
import json
import time

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE = "http://localhost:8000/api"
DEMO = "backend/data/demo"

PASS = "[PASS]"
FAIL = "[FAIL]"
errors = []


def check(label, condition, detail=""):
    if condition:
        print(f"{PASS} {label}")
    else:
        msg = f"{FAIL} {label}" + (f"  ({detail})" if detail else "")
        print(msg)
        errors.append(msg)


def j(r):
    try:
        return r.json()
    except Exception:
        return {}


print("=" * 60)
print("Phase 4B: Session-Aware API Test Suite")
print("=" * 60)
print()

client = httpx.Client(timeout=60)

# ── 0. Health ─────────────────────────────────────────────────────────────────
r = client.get(f"{BASE}/health")
check("GET /health", r.status_code == 200 and j(r).get("status") == "ok")

# ── 1. Create two sessions ─────────────────────────────────────────────────────
r1 = client.post(f"{BASE}/sessions", json={"name": "4B Test — Auth Incident"})
check("POST /sessions (s1)", r1.status_code == 200, j(r1))
s1 = j(r1)
s1_id = s1.get("id", "")

r2 = client.post(f"{BASE}/sessions", json={"name": "4B Test — DB Outage"})
check("POST /sessions (s2)", r2.status_code == 200, j(r2))
s2 = j(r2)
s2_id = s2.get("id", "")

check("Session s1 has id",   bool(s1_id))
check("Session s2 has id",   bool(s2_id))
check("Sessions have different ids", s1_id != s2_id)

# ── 2. List sessions ───────────────────────────────────────────────────────────
r = client.get(f"{BASE}/sessions")
check("GET /sessions", r.status_code == 200)
sessions = j(r).get("sessions", [])
ids = [s["id"] for s in sessions]
check("Both sessions in list", s1_id in ids and s2_id in ids)

# ── 3. GET single session ──────────────────────────────────────────────────────
r = client.get(f"{BASE}/sessions/{s1_id}")
check("GET /sessions/{id}", r.status_code == 200 and j(r).get("id") == s1_id)

r = client.get(f"{BASE}/sessions/nonexistent-id")
check("GET /sessions/{id} 404 for missing", r.status_code == 404)

# ── 4. Ingest files to session 1 ──────────────────────────────────────────────
import os
demo_files = [
    ("files", ("demo_app.log",       open(f"{DEMO}/demo_app.log",       "rb"), "text/plain")),
    ("files", ("demo_metrics.json",  open(f"{DEMO}/demo_metrics.json",  "rb"), "application/json")),
]
r = client.post(f"{BASE}/sessions/{s1_id}/ingest", files=demo_files, timeout=120)
check("POST /sessions/{id}/ingest", r.status_code == 200, j(r).get("errors"))
ingest1 = j(r)
check("s1 ingest: files_processed >= 2", ingest1.get("files_processed", 0) >= 2)
check("s1 ingest: graph_nodes > 0",      ingest1.get("graph_nodes", 0) > 0)
s1_nodes = ingest1.get("graph_nodes", 0)
print(f"        s1 nodes={s1_nodes}, edges={ingest1.get('graph_edges',0)}")

# ── 5. Session 2 graph should be EMPTY (isolation check) ─────────────────────
r = client.get(f"{BASE}/sessions/{s2_id}/graph")
check("GET /sessions/{id}/graph (s2)", r.status_code == 200)
g2 = j(r)
check("s2 graph EMPTY before ingest (isolation)", len(g2.get("nodes", [])) == 0,
      f"got {len(g2.get('nodes',[]))} nodes")

# ── 6. Session 1 graph should have nodes ──────────────────────────────────────
r = client.get(f"{BASE}/sessions/{s1_id}/graph")
check("GET /sessions/{id}/graph (s1)", r.status_code == 200)
g1 = j(r)
check("s1 graph has nodes after ingest", len(g1.get("nodes", [])) > 0,
      f"got {len(g1.get('nodes',[]))} nodes")

# ── 7. Query session 1 ────────────────────────────────────────────────────────
r = client.post(
    f"{BASE}/sessions/{s1_id}/query",
    json={"query": "Why did auth-service fail around 2:31 AM?"},
    timeout=120,
)
check("POST /sessions/{id}/query", r.status_code == 200, str(j(r))[:100])
rca = j(r)
check("Query returns root_cause", bool(rca.get("root_cause")))
check("Query returns confidence",  rca.get("confidence") in ("high", "medium", "low"))
check("Query returns agent_trace", len(rca.get("agent_trace", [])) > 0)
print(f"        confidence={rca.get('confidence')}, trace_events={len(rca.get('agent_trace',[]))}")

# ── 8. Chat history persisted ─────────────────────────────────────────────────
r = client.get(f"{BASE}/sessions/{s1_id}/chat")
check("GET /sessions/{id}/chat", r.status_code == 200)
chat = j(r).get("history", [])
check("Chat history has 2 entries (user + assistant)", len(chat) == 2,
      f"got {len(chat)}")
check("First entry role=user",      chat[0]["role"] == "user"      if chat else False)
check("Second entry role=assistant", chat[1]["role"] == "assistant" if len(chat) > 1 else False)

# ── 9. Query session 2 (should NOT see session 1 data) ───────────────────────
r = client.post(
    f"{BASE}/sessions/{s2_id}/query",
    json={"query": "Why did auth-service fail around 2:31 AM?"},
    timeout=120,
)
check("POST /sessions/{id}/query (s2)", r.status_code == 200)
rca2 = j(r)
# Session 2 has no data — should still return an answer (template or empty)
check("s2 query returns answer field", "answer" in rca2)

# ── 10. Global backward-compat routes still work ─────────────────────────────
r = client.get(f"{BASE}/graph")
check("GET /graph (global, backward-compat)", r.status_code == 200)

r = client.post(f"{BASE}/query", json={"query": "test"}, timeout=60)
check("POST /query (global, backward-compat)", r.status_code == 200)

# ── 11. Clear chat history ────────────────────────────────────────────────────
r = client.delete(f"{BASE}/sessions/{s1_id}/chat")
check("DELETE /sessions/{id}/chat", r.status_code == 200 and j(r).get("cleared"))
r = client.get(f"{BASE}/sessions/{s1_id}/chat")
check("Chat history empty after clear", len(j(r).get("history", [])) == 0)

# ── 12. Delete sessions ───────────────────────────────────────────────────────
r = client.delete(f"{BASE}/sessions/{s1_id}")
check("DELETE /sessions/{id} (s1)", r.status_code == 200 and j(r).get("deleted"))
r = client.delete(f"{BASE}/sessions/{s2_id}")
check("DELETE /sessions/{id} (s2)", r.status_code == 200 and j(r).get("deleted"))

r = client.get(f"{BASE}/sessions")
remaining_ids = [s["id"] for s in j(r).get("sessions", [])]
check("Sessions removed from list", s1_id not in remaining_ids and s2_id not in remaining_ids)

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 60)
if errors:
    print(f"PHASE 4B: {len(errors)} FAILURE(S)")
    for e in errors:
        print("  ", e)
    sys.exit(1)
else:
    print("PHASE 4B: ALL TESTS PASSED [OK]")
    print("=" * 60)
